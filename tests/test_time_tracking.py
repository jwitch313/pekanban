"""Tests for time tracking (Step 5, Slice 3, F-12)."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from kanban.services.database import Database
from kanban.services.task_service import TaskService
from kanban.services.time_tracking_service import TimeTrackingService


@pytest.fixture
def service(database: Database) -> TimeTrackingService:
    return TimeTrackingService(database)


def _task(database: Database) -> int:
    task_service = TaskService(database)
    board = task_service.create_board("Work")
    task = task_service.create_task(board.columns[0].id, "Timed")
    return task.id


def _two_tasks(database: Database) -> tuple[int, int]:
    task_service = TaskService(database)
    board = task_service.create_board("Work")
    a = task_service.create_task(board.columns[0].id, "A")
    b = task_service.create_task(board.columns[0].id, "B")
    return a.id, b.id


T0 = datetime(2026, 3, 1, 9, 0, 0)


def test_start_timer_creates_open_entry(service: TimeTrackingService, database: Database) -> None:
    task_id = _task(database)
    entry = service.start_timer(task_id, now=T0)
    assert entry.id is not None
    assert entry.started_at == T0
    assert entry.ended_at is None
    assert entry.is_running


def test_start_timer_missing_task_raises(service: TimeTrackingService) -> None:
    with pytest.raises(LookupError):
        service.start_timer(9999, now=T0)


def test_start_new_timer_closes_previous(service: TimeTrackingService, database: Database) -> None:
    a_id, b_id = _two_tasks(database)
    service.start_timer(a_id, now=T0)
    service.start_timer(b_id, now=T0 + timedelta(minutes=5))

    active = service.active_timer()
    assert active is not None
    assert active.task_id == b_id
    # Only one open entry remains.
    assert service.total_for_task(a_id) == 300.0


def test_pause_closes_interval_as_paused(service: TimeTrackingService, database: Database) -> None:
    task_id = _task(database)
    service.start_timer(task_id, now=T0)
    paused = service.pause_timer(task_id, now=T0 + timedelta(minutes=10))
    assert paused.ended_at == T0 + timedelta(minutes=10)
    assert paused.paused is True
    assert service.active_timer() is None


def test_pause_without_running_raises(service: TimeTrackingService, database: Database) -> None:
    task_id = _task(database)
    with pytest.raises(LookupError):
        service.pause_timer(task_id, now=T0)


def test_resume_opens_new_interval(service: TimeTrackingService, database: Database) -> None:
    task_id = _task(database)
    service.start_timer(task_id, now=T0)
    service.pause_timer(task_id, now=T0 + timedelta(minutes=10))
    resumed = service.resume_timer(task_id, now=T0 + timedelta(minutes=15))
    assert resumed.is_running
    assert resumed.started_at == T0 + timedelta(minutes=15)


def test_stop_closes_interval(service: TimeTrackingService, database: Database) -> None:
    task_id = _task(database)
    service.start_timer(task_id, now=T0)
    stopped = service.stop_timer(task_id, now=T0 + timedelta(minutes=30))
    assert stopped.ended_at == T0 + timedelta(minutes=30)
    assert stopped.paused is False
    assert service.active_timer() is None


def test_stop_without_running_raises(service: TimeTrackingService, database: Database) -> None:
    task_id = _task(database)
    with pytest.raises(LookupError):
        service.stop_timer(task_id, now=T0)


def test_total_for_task_sums_closed_intervals(
    service: TimeTrackingService, database: Database
) -> None:
    task_id = _task(database)
    service.start_timer(task_id, now=T0)
    service.stop_timer(task_id, now=T0 + timedelta(minutes=10))  # 600s
    service.start_timer(task_id, now=T0 + timedelta(minutes=20))
    service.stop_timer(task_id, now=T0 + timedelta(minutes=25))  # 300s
    assert service.total_for_task(task_id) == 900.0


def test_total_for_task_running_not_counted(
    service: TimeTrackingService, database: Database
) -> None:
    task_id = _task(database)
    service.start_timer(task_id, now=T0)
    # Open interval contributes nothing to the total.
    assert service.total_for_task(task_id) == 0.0


def test_total_for_task_missing_raises(service: TimeTrackingService) -> None:
    with pytest.raises(LookupError):
        service.total_for_task(9999)


def test_total_for_column_aggregates_tasks(
    service: TimeTrackingService, database: Database
) -> None:
    a_id, b_id = _two_tasks(database)
    service.start_timer(a_id, now=T0)
    service.stop_timer(a_id, now=T0 + timedelta(minutes=10))  # 600s
    service.start_timer(b_id, now=T0)
    service.stop_timer(b_id, now=T0 + timedelta(minutes=5))  # 300s

    task_service = TaskService(database)
    board = task_service.list_boards()[0]
    column_id = task_service.get_board_full(board.id).columns[0].id
    assert service.total_for_column(column_id) == 900.0


def test_total_for_column_missing_raises(service: TimeTrackingService) -> None:
    with pytest.raises(LookupError):
        service.total_for_column(9999)
