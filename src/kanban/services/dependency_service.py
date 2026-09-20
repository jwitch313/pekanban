"""Task dependency service (F-20).

Manages "A blocks B" edges between tasks: add/remove dependencies, query
what blocks a task and what it blocks, and detect cycles so the graph stays
a DAG.

Pure business logic with no GUI dependencies.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from kanban.models import Dependency, Task
from kanban.services.database import Database


class DependencyService:
    """Add, remove, and query task dependencies (blocking relationships)."""

    def __init__(self, database: Database) -> None:
        self._db = database

    def add_dependency(self, task_id: int, depends_on_id: int) -> Dependency:
        """Record that ``task_id`` is blocked by ``depends_on_id``.

        Raises ``ValueError`` for self-dependencies or cycles, and
        ``LookupError`` when either task does not exist.
        """
        if task_id == depends_on_id:
            raise ValueError("A task cannot depend on itself")
        with self._db.session() as session:
            if session.get(Task, task_id) is None:
                raise LookupError(f"Task {task_id} does not exist")
            if session.get(Task, depends_on_id) is None:
                raise LookupError(f"Task {depends_on_id} does not exist")
            if self._would_create_cycle(session, task_id, depends_on_id):
                raise ValueError("Adding this dependency would create a cycle")
            existing = (
                session.query(Dependency)
                .filter(Dependency.task_id == task_id, Dependency.depends_on_id == depends_on_id)
                .first()
            )
            if existing is not None:
                return existing
            dependency = Dependency(task_id=task_id, depends_on_id=depends_on_id)
            session.add(dependency)
            session.flush()
            return dependency

    def remove_dependency(self, task_id: int, depends_on_id: int) -> None:
        """Remove the edge where ``task_id`` is blocked by ``depends_on_id``."""
        with self._db.session() as session:
            dependency = (
                session.query(Dependency)
                .filter(Dependency.task_id == task_id, Dependency.depends_on_id == depends_on_id)
                .first()
            )
            if dependency is None:
                raise LookupError(f"No dependency from {task_id} to {depends_on_id}")
            session.delete(dependency)
            session.flush()

    def blocking_tasks(self, task_id: int) -> list[Task]:
        """Tasks that block ``task_id`` (its direct dependencies)."""
        with self._db.session() as session:
            if session.get(Task, task_id) is None:
                raise LookupError(f"Task {task_id} does not exist")
            rows = (
                session.query(Dependency)
                .filter(Dependency.task_id == task_id)
                .order_by(Dependency.id)
                .all()
            )
            return [self._get_task(session, row.depends_on_id) for row in rows]

    def blocked_tasks(self, task_id: int) -> list[Task]:
        """Tasks that ``task_id`` blocks (its direct dependents)."""
        with self._db.session() as session:
            if session.get(Task, task_id) is None:
                raise LookupError(f"Task {task_id} does not exist")
            rows = (
                session.query(Dependency)
                .filter(Dependency.depends_on_id == task_id)
                .order_by(Dependency.id)
                .all()
            )
            return [self._get_task(session, row.task_id) for row in rows]

    def is_blocked(self, task_id: int) -> bool:
        """Whether ``task_id`` has any incomplete blocking task."""
        return any(not t.completed for t in self.blocking_tasks(task_id))

    # -- Helpers ----------------------------------------------------------
    @staticmethod
    def _get_task(session: Session, task_id: int) -> Task:
        task = session.get(Task, task_id)
        if task is None:
            raise LookupError(f"Task {task_id} does not exist")
        return task

    @staticmethod
    def _would_create_cycle(session: Session, task_id: int, depends_on_id: int) -> bool:
        """True if ``task_id`` is already (transitively) reachable from ``depends_on_id``."""
        visited: set[int] = set()
        frontier = [depends_on_id]
        while frontier:
            current = frontier.pop()
            if current == task_id:
                return True
            if current in visited:
                continue
            visited.add(current)
            rows = session.execute(
                select(Dependency.depends_on_id).where(Dependency.task_id == current)
            ).all()
            frontier.extend(row[0] for row in rows)
        return False
