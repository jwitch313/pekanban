"""Calendar view service (F-15).

Queries tasks by due date so the UI can render a calendar alongside the
Kanban columns: tasks for a single day, a date range, and a month overview.

Pure business logic with no GUI dependencies.
"""

from __future__ import annotations

from calendar import monthrange
from collections import defaultdict
from dataclasses import dataclass
from datetime import date

from kanban.models import Task
from kanban.services.database import Database


@dataclass(frozen=True)
class CalendarDay:
    """A single day in the calendar with its due tasks."""

    day: date
    tasks: tuple[Task, ...]


class CalendarService:
    """Read-only queries over task due dates for calendar rendering."""

    def __init__(self, database: Database) -> None:
        self._db = database

    def tasks_for_date(self, day: date) -> list[Task]:
        """Return tasks due on the given day, ordered by id."""
        with self._db.session() as session:
            tasks = (
                session.query(Task)
                .filter(Task.due_date == day)
                .order_by(Task.id)
                .all()
            )
            session.expunge_all()
            return tasks

    def tasks_in_range(self, start: date, end: date) -> list[Task]:
        """Return tasks due between ``start`` and ``end`` (inclusive)."""
        if start > end:
            raise ValueError("start must be on or before end")
        with self._db.session() as session:
            tasks = (
                session.query(Task)
                .filter(Task.due_date >= start, Task.due_date <= end)
                .order_by(Task.due_date, Task.id)
                .all()
            )
            session.expunge_all()
            return tasks

    def month_overview(self, year: int, month: int) -> list[CalendarDay]:
        """Return one ``CalendarDay`` per day of the month that has due tasks.

        Days without due tasks are omitted; the result is ordered by day.
        """
        if not 1 <= month <= 12:
            raise ValueError(f"month must be 1-12, got {month}")
        last_day = monthrange(year, month)[1]
        start = date(year, month, 1)
        end = date(year, month, last_day)
        by_day: dict[date, list[Task]] = defaultdict(list)
        for task in self.tasks_in_range(start, end):
            assert task.due_date is not None
            by_day[task.due_date].append(task)
        return [
            CalendarDay(day=day, tasks=tuple(tasks))
            for day, tasks in sorted(by_day.items())
        ]
