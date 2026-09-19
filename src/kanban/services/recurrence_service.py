"""Recurring-task service (F-09).

Lets a task carry a recurrence rule (daily / weekly / monthly / custom) and
auto-creates a new occurrence in the same column once the rule's ``next_run``
has passed. The recurrence stays attached to the original task, which acts as
the recurring template; each pass advances ``next_run`` to the following
occurrence.

Pure business logic with no GUI dependencies.
"""

from __future__ import annotations

import calendar
from datetime import datetime, timedelta

from sqlalchemy import select

from kanban.models import Recurrence, RecurrencePattern, Task
from kanban.services.database import Database


def _add_months(dt: datetime, months: int) -> datetime:
    """Add calendar months, clamping the day to the target month's length."""
    total = dt.month - 1 + months
    year = dt.year + total // 12
    month = total % 12 + 1
    day = min(dt.day, calendar.monthrange(year, month)[1])
    return dt.replace(year=year, month=month, day=day)


class RecurrenceService:
    """Manage recurrence rules and the auto-creation of due occurrences."""

    def __init__(self, database: Database) -> None:
        self._db = database

    # -- Rule management --------------------------------------------------
    def set_recurrence(
        self,
        task_id: int,
        pattern: RecurrencePattern,
        next_run: datetime | None = None,
    ) -> Recurrence:
        """Create or update the recurrence rule for a task.

        ``CUSTOM`` patterns have no stored interval, so an explicit
        ``next_run`` is required.
        """
        if pattern is RecurrencePattern.CUSTOM and next_run is None:
            raise ValueError("CUSTOM recurrence requires an explicit next_run")
        with self._db.session() as session:
            task = session.get(Task, task_id)
            if task is None:
                raise LookupError(f"Task {task_id} does not exist")
            rec = task.recurrence
            if rec is None:
                rec = Recurrence(task_id=task_id, pattern=pattern, next_run=next_run)
                session.add(rec)
            else:
                rec.pattern = pattern
                rec.next_run = next_run
            session.flush()
            return rec

    def get_recurrence(self, task_id: int) -> Recurrence | None:
        """Return a task's recurrence rule, or ``None`` if it has none."""
        with self._db.session() as session:
            task = session.get(Task, task_id)
            if task is None:
                raise LookupError(f"Task {task_id} does not exist")
            return task.recurrence

    def clear_recurrence(self, task_id: int) -> None:
        """Remove a task's recurrence rule, if any."""
        with self._db.session() as session:
            task = session.get(Task, task_id)
            if task is None:
                raise LookupError(f"Task {task_id} does not exist")
            if task.recurrence is not None:
                session.delete(task.recurrence)
                session.flush()

    # -- Scheduling -------------------------------------------------------
    def compute_next_run(self, pattern: RecurrencePattern, from_dt: datetime) -> datetime:
        """Compute the next occurrence after ``from_dt`` for a standard pattern.

        ``CUSTOM`` has no stored interval and therefore cannot be advanced
        automatically; callers must supply an explicit ``next_run``.
        """
        if pattern is RecurrencePattern.DAILY:
            return from_dt + timedelta(days=1)
        if pattern is RecurrencePattern.WEEKLY:
            return from_dt + timedelta(weeks=1)
        if pattern is RecurrencePattern.MONTHLY:
            return _add_months(from_dt, 1)
        raise ValueError("CUSTOM recurrence requires an explicit next_run")

    def process_due_recurrences(self, now: datetime | None = None) -> list[Task]:
        """Create a new occurrence for every recurrence whose time has come.

        For each due rule a copy of the source task is appended to the same
        column and the rule's ``next_run`` is advanced (or cleared for
        ``CUSTOM``). Returns the newly created tasks.
        """
        now = now or datetime.now()
        created: list[Task] = []
        with self._db.session() as session:
            due = (
                session.execute(select(Recurrence).where(Recurrence.next_run <= now))
                .scalars()
                .all()
            )
            for rec in due:
                task = session.get(Task, rec.task_id)
                if task is None:
                    continue
                column = task.column
                new_task = Task(
                    column_id=column.id,
                    title=task.title,
                    description=task.description,
                    priority=task.priority,
                    due_date=task.due_date,
                    status_color=task.status_color,
                    order_idx=len(column.tasks),
                )
                session.add(new_task)
                session.flush()
                if rec.pattern is RecurrencePattern.CUSTOM:
                    rec.next_run = None
                else:
                    rec.next_run = self.compute_next_run(rec.pattern, rec.next_run or now)
                created.append(new_task)
            session.flush()
        return created
