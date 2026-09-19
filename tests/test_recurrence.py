"""Tests for recurring tasks (Step 5, Slice 2, F-09)."""

from __future__ import annotations

from datetime import datetime

import pytest

from kanban.models import Priority, RecurrencePattern
from kanban.services.database import Database
from kanban.services.recurrence_service import RecurrenceService
from kanban.services.task_service import TaskService


@pytest.fixture
def service(database: Database) -> RecurrenceService:
    return RecurrenceService(database)


def _task(database: Database) -> tuple[int, int]:
    """Create a board with one task; return (board_id, task_id)."""
    task_service = TaskService(database)
    board = task_service.create_board("Work")
    task = task_service.create_task(board.columns[0].id, "Recurring")
    return board.id, task.id


def test_set_and_get_recurrence(service: RecurrenceService, database: Database) -> None:
    _, task_id = _task(database)
    rec = service.set_recurrence(task_id, RecurrencePattern.DAILY)
    assert rec.id is not None
    assert rec.pattern is RecurrencePattern.DAILY

    fetched = service.get_recurrence(task_id)
    assert fetched is not None
    assert fetched.pattern is RecurrencePattern.DAILY


def test_set_recurrence_missing_task_raises(service: RecurrenceService) -> None:
    with pytest.raises(LookupError):
        service.set_recurrence(9999, RecurrencePattern.DAILY)


def test_custom_requires_explicit_next_run(service: RecurrenceService, database: Database) -> None:
    _, task_id = _task(database)
    with pytest.raises(ValueError):
        service.set_recurrence(task_id, RecurrencePattern.CUSTOM)

    rec = service.set_recurrence(
        task_id, RecurrencePattern.CUSTOM, next_run=datetime(2026, 1, 1, 9, 0)
    )
    assert rec.next_run == datetime(2026, 1, 1, 9, 0)


def test_update_existing_recurrence(service: RecurrenceService, database: Database) -> None:
    _, task_id = _task(database)
    first = service.set_recurrence(task_id, RecurrencePattern.DAILY)
    second = service.set_recurrence(task_id, RecurrencePattern.WEEKLY)
    # Same rule object is updated in place, not duplicated.
    assert first.id == second.id
    assert second.pattern is RecurrencePattern.WEEKLY


def test_clear_recurrence(service: RecurrenceService, database: Database) -> None:
    _, task_id = _task(database)
    service.set_recurrence(task_id, RecurrencePattern.DAILY)
    service.clear_recurrence(task_id)
    assert service.get_recurrence(task_id) is None


def test_compute_next_run_daily(service: RecurrenceService) -> None:
    base = datetime(2026, 3, 15, 9, 30)
    assert service.compute_next_run(RecurrencePattern.DAILY, base) == datetime(2026, 3, 16, 9, 30)


def test_compute_next_run_weekly(service: RecurrenceService) -> None:
    base = datetime(2026, 3, 15, 9, 30)
    assert service.compute_next_run(RecurrencePattern.WEEKLY, base) == datetime(2026, 3, 22, 9, 30)


def test_compute_next_run_monthly_clamps_day(service: RecurrenceService) -> None:
    # Jan 31 -> Feb 28 (non-leap year).
    base = datetime(2026, 1, 31, 8, 0)
    assert service.compute_next_run(RecurrencePattern.MONTHLY, base) == datetime(2026, 2, 28, 8, 0)


def test_compute_next_run_custom_raises(service: RecurrenceService) -> None:
    with pytest.raises(ValueError):
        service.compute_next_run(RecurrencePattern.CUSTOM, datetime(2026, 1, 1))


def test_process_due_creates_occurrence_and_advances(
    service: RecurrenceService, database: Database
) -> None:
    _, task_id = _task(database)
    due = datetime(2026, 3, 1, 9, 0)
    service.set_recurrence(task_id, RecurrencePattern.DAILY, next_run=due)

    created = service.process_due_recurrences(now=datetime(2026, 3, 1, 9, 30))

    assert len(created) == 1
    assert created[0].id != task_id
    assert created[0].title == "Recurring"
    assert created[0].priority is Priority.MEDIUM

    # The rule advanced to the next day.
    rec = service.get_recurrence(task_id)
    assert rec is not None
    assert rec.next_run == datetime(2026, 3, 2, 9, 0)


def test_process_due_ignores_future_recurrences(
    service: RecurrenceService, database: Database
) -> None:
    _, task_id = _task(database)
    service.set_recurrence(task_id, RecurrencePattern.DAILY, next_run=datetime(2027, 1, 1))

    created = service.process_due_recurrences(now=datetime(2026, 3, 1))
    assert created == []


def test_process_due_custom_clears_next_run(
    service: RecurrenceService, database: Database
) -> None:
    _, task_id = _task(database)
    service.set_recurrence(task_id, RecurrencePattern.CUSTOM, next_run=datetime(2026, 3, 1, 9, 0))

    created = service.process_due_recurrences(now=datetime(2026, 3, 1, 9, 30))
    assert len(created) == 1
    rec = service.get_recurrence(task_id)
    assert rec is not None
    assert rec.next_run is None
