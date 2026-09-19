"""Tests for sub-task operations (Step 5, Slice 1)."""

from __future__ import annotations

import pytest

from kanban.services.database import Database
from kanban.services.task_service import TaskService


@pytest.fixture
def service(database: Database) -> TaskService:
    return TaskService(database)


def _task(service: TaskService) -> int:
    board = service.create_board("Work")
    task = service.create_task(board.columns[0].id, "Parent")
    return task.id


def test_add_subtask(service: TaskService) -> None:
    task_id = _task(service)
    subtask = service.add_subtask(task_id, "First step")
    assert subtask.id is not None
    assert subtask.title == "First step"
    assert subtask.completed is False
    assert subtask.order_idx == 0


def test_add_subtask_missing_task_raises(service: TaskService) -> None:
    with pytest.raises(LookupError):
        service.add_subtask(9999, "nope")


def test_subtasks_ordered_by_position(service: TaskService) -> None:
    task_id = _task(service)
    service.add_subtask(task_id, "A")
    service.add_subtask(task_id, "B")
    service.add_subtask(task_id, "C")
    assert [s.title for s in service.list_subtasks(task_id)] == ["A", "B", "C"]


def test_toggle_subtask(service: TaskService) -> None:
    task_id = _task(service)
    subtask = service.add_subtask(task_id, "Step")
    assert subtask.completed is False

    toggled = service.toggle_subtask(subtask.id)
    assert toggled.completed is True

    toggled_back = service.toggle_subtask(subtask.id)
    assert toggled_back.completed is False


def test_toggle_subtask_missing_raises(service: TaskService) -> None:
    with pytest.raises(LookupError):
        service.toggle_subtask(9999)


def test_delete_subtask_renumbers(service: TaskService) -> None:
    task_id = _task(service)
    a = service.add_subtask(task_id, "A")
    b = service.add_subtask(task_id, "B")
    service.add_subtask(task_id, "C")

    service.delete_subtask(b.id)

    remaining = service.list_subtasks(task_id)
    assert [s.title for s in remaining] == ["A", "C"]
    assert [s.order_idx for s in remaining] == [0, 1]
    assert a.id in {s.id for s in remaining}


def test_delete_subtask_missing_raises(service: TaskService) -> None:
    with pytest.raises(LookupError):
        service.delete_subtask(9999)


def test_delete_task_cascades_subtasks(service: TaskService) -> None:
    task_id = _task(service)
    subtask = service.add_subtask(task_id, "Step")
    service.delete_task(task_id)
    # The sub-task row should be gone; querying it raises.
    with pytest.raises(LookupError):
        service.toggle_subtask(subtask.id)
