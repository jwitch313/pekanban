"""Tests for the calendar view service (Step 6, Slice 1, F-15)."""

from __future__ import annotations

from datetime import date

import pytest

from kanban.services.calendar_service import CalendarDay, CalendarService
from kanban.services.database import Database
from kanban.services.task_service import TaskService


@pytest.fixture
def service(database: Database) -> CalendarService:
    return CalendarService(database)


@pytest.fixture
def task_service(database: Database) -> TaskService:
    return TaskService(database)


def _task_with_due(task_service: TaskService, title: str, due: date | None) -> int:
    board = task_service.create_board(f"Board {title}")
    task = task_service.create_task(board.columns[0].id, title, due_date=due)
    return task.id


def test_tasks_for_date(service: CalendarService, task_service: TaskService) -> None:
    _task_with_due(task_service, "today", date(2026, 3, 10))
    _task_with_due(task_service, "other", date(2026, 3, 11))
    _task_with_due(task_service, "no date", None)

    tasks = service.tasks_for_date(date(2026, 3, 10))

    assert [t.title for t in tasks] == ["today"]


def test_tasks_for_date_empty(service: CalendarService) -> None:
    assert service.tasks_for_date(date(2030, 1, 1)) == []


def test_tasks_in_range_inclusive(service: CalendarService, task_service: TaskService) -> None:
    _task_with_due(task_service, "before", date(2026, 3, 9))
    _task_with_due(task_service, "start", date(2026, 3, 10))
    _task_with_due(task_service, "middle", date(2026, 3, 12))
    _task_with_due(task_service, "end", date(2026, 3, 15))
    _task_with_due(task_service, "after", date(2026, 3, 16))

    tasks = service.tasks_in_range(date(2026, 3, 10), date(2026, 3, 15))

    assert [t.title for t in tasks] == ["start", "middle", "end"]


def test_tasks_in_range_invalid(service: CalendarService) -> None:
    with pytest.raises(ValueError):
        service.tasks_in_range(date(2026, 3, 15), date(2026, 3, 10))


def test_month_overview(service: CalendarService, task_service: TaskService) -> None:
    _task_with_due(task_service, "a", date(2026, 3, 1))
    _task_with_due(task_service, "b", date(2026, 3, 15))
    _task_with_due(task_service, "c", date(2026, 3, 15))
    _task_with_due(task_service, "outside", date(2026, 4, 1))

    days = service.month_overview(2026, 3)

    assert [d.day for d in days] == [date(2026, 3, 1), date(2026, 3, 15)]
    assert all(isinstance(d, CalendarDay) for d in days)
    assert [t.title for t in days[1].tasks] == ["b", "c"]


def test_month_overview_empty_month(service: CalendarService) -> None:
    assert service.month_overview(2026, 12) == []


def test_month_overview_invalid_month(service: CalendarService) -> None:
    with pytest.raises(ValueError):
        service.month_overview(2026, 13)
