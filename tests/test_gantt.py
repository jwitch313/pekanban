"""Tests for the Gantt chart service (Step 7, Slice 2, F-16)."""

from __future__ import annotations

from datetime import date

import pytest

from kanban.services.database import Database
from kanban.services.dependency_service import DependencyService
from kanban.services.gantt_service import GanttService
from kanban.services.task_service import TaskService


@pytest.fixture
def service(database: Database) -> GanttService:
    return GanttService(database)


@pytest.fixture
def task_service(database: Database) -> TaskService:
    return TaskService(database)


@pytest.fixture
def dep_service(database: Database) -> DependencyService:
    return DependencyService(database)


def _task(task_service: TaskService, title: str, due: date | None = None) -> int:
    board = task_service.create_board(f"Board {title}")
    return task_service.create_task(board.columns[0].id, title, due_date=due).id


def test_progress_no_subtasks(service: GanttService, task_service: TaskService) -> None:
    a = _task(task_service, "a")
    assert service.progress(a) == 0.0
    task_service.update_task(a, completed=True)
    assert service.progress(a) == 1.0


def test_progress_from_subtasks(service: GanttService, task_service: TaskService) -> None:
    a = _task(task_service, "a")
    s1 = task_service.add_subtask(a, "s1")
    s2 = task_service.add_subtask(a, "s2")
    s3 = task_service.add_subtask(a, "s3")

    assert service.progress(a) == 0.0
    task_service.toggle_subtask(s1.id)
    assert service.progress(a) == pytest.approx(1 / 3)
    task_service.toggle_subtask(s2.id)
    task_service.toggle_subtask(s3.id)
    assert service.progress(a) == 1.0


def test_progress_missing_task_raises(service: GanttService) -> None:
    with pytest.raises(LookupError):
        service.progress(9999)


def test_timeline_filters_by_due_date(service: GanttService, task_service: TaskService) -> None:
    in_range = _task(task_service, "in", due=date(2026, 3, 10))
    excluded = {
        _task(task_service, "before", due=date(2026, 3, 1)),
        _task(task_service, "after", due=date(2026, 3, 20)),
        _task(task_service, "nodue"),
    }

    bars = service.timeline(date(2026, 3, 5), date(2026, 3, 15))

    assert [b.task_id for b in bars] == [in_range]
    assert bars[0].end == date(2026, 3, 10)
    assert bars[0].start <= bars[0].end
    assert not excluded & {b.task_id for b in bars}


def test_timeline_invalid_range_raises(service: GanttService) -> None:
    with pytest.raises(ValueError):
        service.timeline(date(2026, 3, 15), date(2026, 3, 5))


def test_timeline_progress_and_completed(
    service: GanttService, task_service: TaskService
) -> None:
    a = _task(task_service, "a", due=date(2026, 4, 1))
    sub = task_service.add_subtask(a, "s")
    task_service.toggle_subtask(sub.id)

    bar = service.timeline(date(2026, 4, 1), date(2026, 4, 1))[0]

    assert bar.progress == 1.0
    assert bar.completed is False


def test_dependencies_edges(service: GanttService, task_service: TaskService,
                            dep_service: DependencyService) -> None:
    a = _task(task_service, "a")
    b = _task(task_service, "b")
    dep_service.add_dependency(a, b)  # a blocked by b

    edges = service.dependencies(a)

    assert [(e.blocked_id, e.blocking_id) for e in edges] == [(a, b)]
    # b sees the same edge from the other side
    assert [(e.blocked_id, e.blocking_id) for e in service.dependencies(b)] == [(a, b)]


def test_dependencies_missing_task_raises(service: GanttService) -> None:
    with pytest.raises(LookupError):
        service.dependencies(9999)


def test_timeline_bounds(service: GanttService, task_service: TaskService) -> None:
    assert service.timeline_bounds([]) is None
    _task(task_service, "a", due=date(2026, 5, 1))
    _task(task_service, "b", due=date(2026, 5, 9))
    bars = service.timeline(date(2026, 5, 1), date(2026, 5, 9))
    bounds = service.timeline_bounds(bars)
    assert bounds is not None
    assert bounds[1] == date(2026, 5, 9)
    assert bounds[0] <= bounds[1]
