"""Tests for dashboard statistics (Step 6, Slice 2, F-17)."""

from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest

from kanban.services.dashboard_service import (
    ColumnTime,
    DashboardService,
    DashboardSummary,
)
from kanban.services.database import Database
from kanban.services.task_service import TaskService
from kanban.services.time_tracking_service import TimeTrackingService

TODAY = date(2026, 3, 10)


@pytest.fixture
def service(database: Database) -> DashboardService:
    return DashboardService(database)


@pytest.fixture
def task_service(database: Database) -> TaskService:
    return TaskService(database)


@pytest.fixture
def timer(database: Database) -> TimeTrackingService:
    return TimeTrackingService(database)


def _task(task_service: TaskService, title: str, **kwargs) -> int:
    board = task_service.create_board(f"Board {title}")
    task = task_service.create_task(board.columns[0].id, title, **kwargs)
    return task.id


def test_total_tasks(service: DashboardService, task_service: TaskService) -> None:
    assert service.total_tasks() == 0
    _task(task_service, "one")
    _task(task_service, "two")
    assert service.total_tasks() == 2


def test_overdue_count(service: DashboardService, task_service: TaskService) -> None:
    _task(task_service, "overdue", due_date=TODAY - timedelta(days=1))
    _task(task_service, "due today", due_date=TODAY)
    _task(task_service, "future", due_date=TODAY + timedelta(days=1))
    done = _task(task_service, "done overdue", due_date=TODAY - timedelta(days=2))
    task_service.update_task(done, completed=True)

    assert service.overdue_count(TODAY) == 1


def test_due_this_week(service: DashboardService, task_service: TaskService) -> None:
    _task(task_service, "today", due_date=TODAY)
    _task(task_service, "in week", due_date=TODAY + timedelta(days=6))
    _task(task_service, "just after", due_date=TODAY + timedelta(days=7))
    _task(task_service, "past", due_date=TODAY - timedelta(days=1))
    done = _task(task_service, "done this week", due_date=TODAY)
    task_service.update_task(done, completed=True)

    assert service.due_this_week(TODAY) == 2


def test_completion_rate_empty(service: DashboardService) -> None:
    assert service.completion_rate() == 0.0


def test_completion_rate(service: DashboardService, task_service: TaskService) -> None:
    _task(task_service, "a")
    done = _task(task_service, "b")
    task_service.update_task(done, completed=True)
    assert service.completion_rate() == pytest.approx(0.5)


def test_time_spent_by_column(
    service: DashboardService, task_service: TaskService, timer: TimeTrackingService
) -> None:
    t1 = _task(task_service, "timed")
    t2 = _task(task_service, "untimed")
    start = datetime(2026, 3, 1, 9, 0, 0)
    timer.start_timer(t1, now=start)
    timer.stop_timer(t1, now=start.replace(hour=10))  # 3600s
    timer.start_timer(t2, now=start)  # still running: excluded

    rows = service.time_spent_by_column()

    assert len(rows) == 1
    assert isinstance(rows[0], ColumnTime)
    assert rows[0].seconds == 3600.0
    assert rows[0].title == "To Do"


def test_summary(service: DashboardService, task_service: TaskService) -> None:
    _task(task_service, "overdue", due_date=TODAY - timedelta(days=1))
    _task(task_service, "this week", due_date=TODAY)
    done = _task(task_service, "done")
    task_service.update_task(done, completed=True)

    summary = service.summary(TODAY)

    assert isinstance(summary, DashboardSummary)
    assert summary.total_tasks == 3
    assert summary.completed_tasks == 1
    assert summary.overdue_count == 1
    assert summary.due_this_week == 1
    assert summary.completion_rate == pytest.approx(1 / 3)
