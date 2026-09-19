"""Dashboard / statistics service (F-17).

Aggregates quick-overview metrics: overdue count, tasks due this week,
completion rate, and time spent per column.

Pure business logic with no GUI dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from kanban.models import BoardColumn, Task, TimeEntry
from kanban.services.database import Database


@dataclass(frozen=True)
class ColumnTime:
    """Tracked time for one column, for chart rendering."""

    column_id: int
    title: str
    seconds: float


@dataclass(frozen=True)
class DashboardSummary:
    """A point-in-time snapshot of the board's key metrics."""

    total_tasks: int
    completed_tasks: int
    overdue_count: int
    due_this_week: int
    completion_rate: float


class DashboardService:
    """Read-only aggregate statistics over tasks and time entries."""

    def __init__(self, database: Database) -> None:
        self._db = database

    def total_tasks(self) -> int:
        """Count all tasks across all boards."""
        with self._db.session() as session:
            return session.query(Task).count()

    def overdue_count(self, today: date) -> int:
        """Count incomplete tasks whose due date is before ``today``."""
        with self._db.session() as session:
            return (
                session.query(Task)
                .filter(Task.completed.is_(False), Task.due_date < today)
                .count()
            )

    def due_this_week(self, today: date) -> int:
        """Count incomplete tasks due within the next 7 days (inclusive)."""
        end = today + timedelta(days=6)
        with self._db.session() as session:
            return (
                session.query(Task)
                .filter(
                    Task.completed.is_(False),
                    Task.due_date >= today,
                    Task.due_date <= end,
                )
                .count()
            )

    def completion_rate(self) -> float:
        """Fraction of all tasks that are completed (0.0 when there are none)."""
        with self._db.session() as session:
            total = session.query(Task).count()
            if total == 0:
                return 0.0
            done = session.query(Task).filter(Task.completed.is_(True)).count()
            return done / total

    def time_spent_by_column(self) -> list[ColumnTime]:
        """Total tracked seconds per column, ordered by column id."""
        with self._db.session() as session:
            entries = (
                session.query(TimeEntry)
                .join(Task, TimeEntry.task_id == Task.id)
                .filter(TimeEntry.ended_at.isnot(None))
                .all()
            )
            totals: dict[int, float] = {}
            for entry in entries:
                column_id = entry.task.column_id
                totals[column_id] = totals.get(column_id, 0.0) + entry.duration_seconds
            columns = session.query(BoardColumn).all()
            return [
                ColumnTime(column_id=column.id, title=column.title, seconds=seconds)
                for column, seconds in sorted(
                    ((c, totals[c.id]) for c in columns if c.id in totals),
                    key=lambda pair: pair[0].id,
                )
            ]

    def summary(self, today: date) -> DashboardSummary:
        """Return all headline metrics in one snapshot."""
        with self._db.session() as session:
            total = session.query(Task).count()
            completed = session.query(Task).filter(Task.completed.is_(True)).count()
        return DashboardSummary(
            total_tasks=total,
            completed_tasks=completed,
            overdue_count=self.overdue_count(today),
            due_this_week=self.due_this_week(today),
            completion_rate=completed / total if total else 0.0,
        )
