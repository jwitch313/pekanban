"""Tests for task dependencies (Step 7, Slice 1, F-20)."""

from __future__ import annotations

import pytest

from kanban.services.database import Database
from kanban.services.dependency_service import DependencyService
from kanban.services.task_service import TaskService


@pytest.fixture
def service(database: Database) -> DependencyService:
    return DependencyService(database)


@pytest.fixture
def task_service(database: Database) -> TaskService:
    return TaskService(database)


def _task(task_service: TaskService, title: str) -> int:
    board = task_service.create_board(f"Board {title}")
    return task_service.create_task(board.columns[0].id, title).id


def test_add_and_list_blocking(service: DependencyService, task_service: TaskService) -> None:
    a = _task(task_service, "a")
    b = _task(task_service, "b")

    dep = service.add_dependency(a, b)

    assert dep.task_id == a
    assert dep.depends_on_id == b
    blockers = service.blocking_tasks(a)
    assert [t.id for t in blockers] == [b]
    assert [t.id for t in service.blocked_tasks(b)] == [a]


def test_add_dependency_idempotent(service: DependencyService, task_service: TaskService) -> None:
    a = _task(task_service, "a")
    b = _task(task_service, "b")
    first = service.add_dependency(a, b)
    second = service.add_dependency(a, b)
    assert first.id == second.id


def test_add_dependency_self_raises(service: DependencyService, task_service: TaskService) -> None:
    a = _task(task_service, "a")
    with pytest.raises(ValueError):
        service.add_dependency(a, a)


def test_add_dependency_cycle_raises(service: DependencyService, task_service: TaskService) -> None:
    a = _task(task_service, "a")
    b = _task(task_service, "b")
    c = _task(task_service, "c")
    service.add_dependency(a, b)  # a blocked by b
    service.add_dependency(b, c)  # b blocked by c
    with pytest.raises(ValueError):
        service.add_dependency(c, a)  # would close the loop


def test_add_dependency_missing_task_raises(
    service: DependencyService, task_service: TaskService
) -> None:
    a = _task(task_service, "a")
    with pytest.raises(LookupError):
        service.add_dependency(a, 9999)
    with pytest.raises(LookupError):
        service.add_dependency(9999, a)


def test_remove_dependency(service: DependencyService, task_service: TaskService) -> None:
    a = _task(task_service, "a")
    b = _task(task_service, "b")
    service.add_dependency(a, b)

    service.remove_dependency(a, b)

    assert service.blocking_tasks(a) == []
    with pytest.raises(LookupError):
        service.remove_dependency(a, b)


def test_is_blocked_by_completion(service: DependencyService, task_service: TaskService) -> None:
    a = _task(task_service, "a")
    b = _task(task_service, "b")
    service.add_dependency(a, b)

    assert service.is_blocked(a) is True
    task_service.update_task(b, completed=True)
    assert service.is_blocked(a) is False


def test_blocking_tasks_missing_task_raises(service: DependencyService) -> None:
    with pytest.raises(LookupError):
        service.blocking_tasks(9999)
