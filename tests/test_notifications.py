"""Tests for notifications (Step 6, Slice 4, F-24)."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from kanban.services.database import Database
from kanban.services.notification_service import (
    Notification,
    NotificationService,
)
from kanban.services.task_service import TaskService

TODAY = date(2026, 3, 10)


@pytest.fixture
def service(database: Database) -> NotificationService:
    return NotificationService(database)


@pytest.fixture
def task_service(database: Database) -> TaskService:
    return TaskService(database)


def _task(task_service: TaskService, title: str, due: date | None = None) -> int:
    board = task_service.create_board(f"Board {title}")
    return task_service.create_task(board.columns[0].id, title, due_date=due).id


def test_overdue(service: NotificationService, task_service: TaskService) -> None:
    _task(task_service, "late", due=TODAY - timedelta(days=2))
    _task(task_service, "today", due=TODAY)
    done = _task(task_service, "done late", due=TODAY - timedelta(days=1))
    task_service.update_task(done, completed=True)

    tasks = service.overdue(TODAY)

    assert [t.title for t in tasks] == ["late"]


def test_due_today(service: NotificationService, task_service: TaskService) -> None:
    _task(task_service, "today", due=TODAY)
    _task(task_service, "tomorrow", due=TODAY + timedelta(days=1))
    done = _task(task_service, "done today", due=TODAY)
    task_service.update_task(done, completed=True)

    assert [t.title for t in service.due_today(TODAY)] == ["today"]


def test_due_soon_excludes_today(
    service: NotificationService, task_service: TaskService
) -> None:
    _task(task_service, "today", due=TODAY)
    _task(task_service, "soon", due=TODAY + timedelta(days=2))
    _task(task_service, "beyond", due=TODAY + timedelta(days=4))

    assert [t.title for t in service.due_soon(TODAY, ahead_days=3)] == ["soon"]


def test_due_soon_invalid_ahead(service: NotificationService) -> None:
    with pytest.raises(ValueError):
        service.due_soon(TODAY, ahead_days=0)


def test_snooze_pushes_due_date_forward(
    service: NotificationService, task_service: TaskService
) -> None:
    tid = _task(task_service, "snoozable", due=TODAY)

    task = service.snooze(tid, 3, today=TODAY)

    assert task.due_date == TODAY + timedelta(days=3)


def test_snooze_without_due_date_uses_today(
    service: NotificationService, task_service: TaskService
) -> None:
    tid = _task(task_service, "no date")

    task = service.snooze(tid, 2, today=TODAY)

    assert task.due_date == TODAY + timedelta(days=2)


def test_snooze_invalid_days(service: NotificationService, task_service: TaskService) -> None:
    tid = _task(task_service, "x")
    with pytest.raises(ValueError):
        service.snooze(tid, 0, today=TODAY)


def test_snooze_missing_task(service: NotificationService) -> None:
    with pytest.raises(LookupError):
        service.snooze(9999, 1, today=TODAY)


def test_collect_orders_most_urgent_first(
    service: NotificationService, task_service: TaskService
) -> None:
    _task(task_service, "overdue", due=TODAY - timedelta(days=1))
    _task(task_service, "today", due=TODAY)
    _task(task_service, "soon", due=TODAY + timedelta(days=1))
    _task(task_service, "irrelevant", due=TODAY + timedelta(days=10))

    notifications = service.collect(TODAY, ahead_days=3)

    assert [n.kind for n in notifications] == ["overdue", "due_today", "due_soon"]
    assert all(isinstance(n, Notification) for n in notifications)
    assert notifications[0].title == "Overdue: overdue"
    assert notifications[1].body == "This task is due today"
    assert notifications[2].body == f"Due {(TODAY + timedelta(days=1)).isoformat()}"
