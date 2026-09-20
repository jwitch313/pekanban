"""Gantt chart service (F-16).

Builds the data the UI needs to render a timeline: task bars with start/end
dates and progress, plus the dependency edges to draw as arrows.

Pure business logic with no GUI dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from kanban.models import Dependency, Task
from kanban.services.database import Database


@dataclass(frozen=True)
class GanttBar:
    """A single task's bar on the Gantt timeline."""

    task_id: int
    title: str
    start: date
    end: date
    progress: float  # 0.0 (none) .. 1.0 (done)
    completed: bool


@dataclass(frozen=True)
class DependencyEdge:
    """A directed dependency edge for arrow rendering.

    ``blocked`` cannot complete until ``blocking`` does.
    """

    blocked_id: int
    blocking_id: int


class GanttService:
    """Read-only queries that produce Gantt timeline data."""

    def __init__(self, database: Database) -> None:
        self._db = database

    def progress(self, task_id: int) -> float:
        """Progress of a task as a fraction in ``[0.0, 1.0]``.

        With sub-tasks this is the completed fraction of sub-tasks; without
        sub-tasks it is ``1.0`` when the task is completed and ``0.0``
        otherwise.
        """
        with self._db.session() as session:
            task = session.get(Task, task_id)
            if task is None:
                raise LookupError(f"Task {task_id} does not exist")
            return self._progress(task)

    def timeline(self, start: date, end: date) -> list[GanttBar]:
        """Bars for tasks due between ``start`` and ``end`` (inclusive).

        Each bar spans from the earlier of the task's creation date and its
        due date to the due date, so ``start <= end`` always holds.
        """
        if start > end:
            raise ValueError("start must be on or before end")
        with self._db.session() as session:
            tasks = (
                session.query(Task)
                .filter(Task.due_date >= start, Task.due_date <= end)
                .order_by(Task.due_date, Task.id)
                .all()
            )
            bars = []
            for task in tasks:
                assert task.due_date is not None
                bars.append(
                    GanttBar(
                        task_id=task.id,
                        title=task.title,
                        start=min(task.created_at.date(), task.due_date),
                        end=task.due_date,
                        progress=self._progress(task),
                        completed=task.completed,
                    )
                )
            return bars

    def dependencies(self, task_id: int) -> list[DependencyEdge]:
        """Direct dependency edges touching ``task_id`` (as blocked or blocking)."""
        with self._db.session() as session:
            if session.get(Task, task_id) is None:
                raise LookupError(f"Task {task_id} does not exist")
            rows = (
                session.query(Dependency)
                .filter(
                    (Dependency.task_id == task_id)
                    | (Dependency.depends_on_id == task_id)
                )
                .order_by(Dependency.id)
                .all()
            )
            return [
                DependencyEdge(blocked_id=row.task_id, blocking_id=row.depends_on_id)
                for row in rows
            ]

    @staticmethod
    def timeline_bounds(bars: list[GanttBar]) -> tuple[date, date] | None:
        """Return ``(min start, max end)`` across bars, or ``None`` if empty."""
        if not bars:
            return None
        return (min(bar.start for bar in bars), max(bar.end for bar in bars))

    # -- Helpers ----------------------------------------------------------
    @staticmethod
    def _progress(task: Task) -> float:
        subtasks = task.subtasks
        if subtasks:
            done = sum(1 for subtask in subtasks if subtask.completed)
            return done / len(subtasks)
        return 1.0 if task.completed else 0.0
