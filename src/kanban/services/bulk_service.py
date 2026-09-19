"""Bulk operations service (F-22).

Apply one action to a selection of tasks at once: move, batch-edit, or
delete. All operations validate the whole selection before mutating.

Pure business logic with no GUI dependencies.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from kanban.models import BoardColumn, Task
from kanban.services.database import Database

_MUTABLE_FIELDS = frozenset(
    {"title", "description", "priority", "due_date", "status_color", "completed"}
)


class BulkService:
    """Move, update, or delete many tasks in a single transaction."""

    def __init__(self, database: Database) -> None:
        self._db = database

    def move_tasks(self, task_ids: list[int], target_column_id: int) -> list[Task]:
        """Move all selected tasks to the target column, appended in selection order.

        Source columns are renumbered to close the gaps left behind.
        """
        unique_ids = self._validate_tasks(task_ids)
        with self._db.session() as session:
            target = session.get(BoardColumn, target_column_id)
            if target is None:
                raise LookupError(f"Column {target_column_id} does not exist")
            tasks = [self._get_task(session, tid) for tid in unique_ids]

            source_ids = {t.column_id for t in tasks if t.column_id != target.id}
            staying = [t for t in target.tasks if t.id not in set(unique_ids)]
            for new_idx, task in enumerate(staying + tasks):
                task.column_id = target.id
                task.order_idx = new_idx
            for source_id in source_ids:
                self._renumber(session, source_id, exclude=set(unique_ids))
            session.flush()
            return tasks

    def update_tasks(self, task_ids: list[int], **fields: Any) -> list[Task]:
        """Apply the same field updates to every selected task."""
        if not fields:
            raise ValueError("No fields to update")
        for key in fields:
            if key not in _MUTABLE_FIELDS:
                raise ValueError(f"Task has no mutable field {key!r}")
        unique_ids = self._validate_tasks(task_ids)
        with self._db.session() as session:
            tasks = [self._get_task(session, tid) for tid in unique_ids]
            for task in tasks:
                for key, value in fields.items():
                    setattr(task, key, value)
            session.flush()
            return tasks

    def delete_tasks(self, task_ids: list[int]) -> int:
        """Delete every selected task; returns the number deleted."""
        unique_ids = self._validate_tasks(task_ids)
        with self._db.session() as session:
            tasks = [self._get_task(session, tid) for tid in unique_ids]
            affected = {t.column_id for t in tasks}
            for task in tasks:
                session.delete(task)
            for column_id in affected:
                self._renumber(session, column_id, exclude=set(unique_ids))
            session.flush()
            return len(tasks)

    # -- Helpers ----------------------------------------------------------
    @staticmethod
    def _get_task(session: Session, task_id: int) -> Task:
        task = session.get(Task, task_id)
        if task is None:
            raise LookupError(f"Task {task_id} does not exist")
        return task

    def _validate_tasks(self, task_ids: list[int]) -> list[int]:
        """Deduplicate (preserving order) and verify every task exists."""
        if not task_ids:
            raise ValueError("No tasks selected")
        unique: dict[int, None] = {}
        for tid in task_ids:
            unique.setdefault(tid, None)
        with self._db.session() as session:
            for tid in unique:
                if session.get(Task, tid) is None:
                    raise LookupError(f"Task {tid} does not exist")
        return list(unique)

    @staticmethod
    def _renumber(session: Any, column_id: int, exclude: set[int]) -> None:
        column = session.get(BoardColumn, column_id)
        if column is None:
            return
        for new_idx, task in enumerate(t for t in column.tasks if t.id not in exclude):
            task.order_idx = new_idx
