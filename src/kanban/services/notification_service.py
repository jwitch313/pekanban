"""Notification service (F-24).

Detects tasks that need a local notification (overdue, due today, due soon)
and supports snoozing a task by pushing its due date forward. The actual
Windows toast delivery is a UI concern; this service produces the messages.

Pure business logic with no GUI dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from kanban.models import Task
from kanban.services.database import Database


@dataclass(frozen=True)
class Notification:
    """A single notification message ready for toast delivery."""

    task_id: int
    title: str
    body: str
    kind: str  # "overdue" | "due_today" | "due_soon"


class NotificationService:
    """Query due-date notifications and snooze tasks."""

    def __init__(self, database: Database) -> None:
        self._db = database

    def overdue(self, today: date) -> list[Task]:
        """Incomplete tasks whose due date is before ``today``."""
        with self._db.session() as session:
            tasks = (
                session.query(Task)
                .filter(Task.completed.is_(False), Task.due_date < today)
                .order_by(Task.due_date, Task.id)
                .all()
            )
            return tasks

    def due_today(self, today: date) -> list[Task]:
        """Incomplete tasks due exactly on ``today``."""
        with self._db.session() as session:
            tasks = (
                session.query(Task)
                .filter(Task.completed.is_(False), Task.due_date == today)
                .order_by(Task.id)
                .all()
            )
            return tasks

    def due_soon(self, today: date, ahead_days: int = 3) -> list[Task]:
        """Incomplete tasks due after today within the next ``ahead_days`` days."""
        if ahead_days < 1:
            raise ValueError("ahead_days must be at least 1")
        end = today + timedelta(days=ahead_days)
        with self._db.session() as session:
            tasks = (
                session.query(Task)
                .filter(
                    Task.completed.is_(False),
                    Task.due_date > today,
                    Task.due_date <= end,
                )
                .order_by(Task.due_date, Task.id)
                .all()
            )
            return tasks

    def snooze(self, task_id: int, days: int, today: date | None = None) -> Task:
        """Push a task's due date forward by ``days``.

        Tasks without a due date are snoozed from ``today``.
        """
        if days < 1:
            raise ValueError("days must be at least 1")
        today = today or date.today()
        with self._db.session() as session:
            task = session.get(Task, task_id)
            if task is None:
                raise LookupError(f"Task {task_id} does not exist")
            base = task.due_date or today
            task.due_date = base + timedelta(days=days)
            session.flush()
            return task

    def collect(self, today: date, ahead_days: int = 3) -> list[Notification]:
        """Build the full notification list for ``today``, most urgent first."""
        notifications: list[Notification] = []
        for task in self.overdue(today):
            assert task.due_date is not None
            notifications.append(
                Notification(
                    task_id=task.id,
                    title=f"Overdue: {task.title}",
                    body=f"Was due {task.due_date.isoformat()}",
                    kind="overdue",
                )
            )
        for task in self.due_today(today):
            notifications.append(
                Notification(
                    task_id=task.id,
                    title=f"Due today: {task.title}",
                    body="This task is due today",
                    kind="due_today",
                )
            )
        for task in self.due_soon(today, ahead_days):
            assert task.due_date is not None
            notifications.append(
                Notification(
                    task_id=task.id,
                    title=f"Due soon: {task.title}",
                    body=f"Due {task.due_date.isoformat()}",
                    kind="due_soon",
                )
            )
        return notifications
