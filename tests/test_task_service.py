"""Tests for the task CRUD service."""

from __future__ import annotations

from datetime import date

import pytest

from kanban.models import Priority
from kanban.services.database import Database
from kanban.services.task_service import TaskService


@pytest.fixture
def service(database: Database) -> TaskService:
    return TaskService(database)


def test_create_board_with_default_column(service: TaskService) -> None:
    board = service.create_board("Work")
    assert board.id is not None
    assert [c.title for c in board.columns] == ["To Do"]


def test_create_and_get_task(service: TaskService) -> None:
    board = service.create_board("Work")
    column = board.columns[0]
    task = service.create_task(column.id, "Write tests", priority=Priority.HIGH)
    assert task.id is not None

    fetched = service.get_task(task.id)
    assert fetched is not None
    assert fetched.title == "Write tests"
    assert fetched.priority is Priority.HIGH


def test_create_task_in_missing_column_raises(service: TaskService) -> None:
    with pytest.raises(LookupError):
        service.create_task(9999, "nope")


def test_update_task(service: TaskService) -> None:
    board = service.create_board("Work")
    task = service.create_task(board.columns[0].id, "Original")
    updated = service.update_task(task.id, title="Renamed", due_date=date(2025, 12, 1))
    assert updated.title == "Renamed"
    assert updated.due_date == date(2025, 12, 1)


def test_update_task_unknown_field_raises(service: TaskService) -> None:
    board = service.create_board("Work")
    task = service.create_task(board.columns[0].id, "Original")
    with pytest.raises(ValueError):
        service.update_task(task.id, not_a_field="x")


def test_move_task_between_columns(service: TaskService) -> None:
    board = service.create_board("Work")
    todo = board.columns[0]
    doing = service.create_column(board.id, "In Progress")
    task = service.create_task(todo.id, "Move me")

    service.move_task(task.id, doing.id, 0)
    assert service.list_tasks_in_column(todo.id) == []
    assert [t.id for t in service.list_tasks_in_column(doing.id)] == [task.id]


def test_move_task_renumbers_target_column(service: TaskService) -> None:
    board = service.create_board("Work")
    doing = service.create_column(board.id, "In Progress")
    a = service.create_task(doing.id, "A")
    service.create_task(doing.id, "B")
    service.create_task(doing.id, "C")

    # Move A to the end of the same column; order should become B, C, A.
    service.move_task(a.id, doing.id, 3)
    assert [t.title for t in service.list_tasks_in_column(doing.id)] == ["B", "C", "A"]


def test_move_task_renumbers_source_column(service: TaskService) -> None:
    board = service.create_board("Work")
    todo = board.columns[0]
    doing = service.create_column(board.id, "In Progress")
    a = service.create_task(todo.id, "A")
    service.create_task(todo.id, "B")
    service.create_task(todo.id, "C")

    service.move_task(a.id, doing.id, 0)
    assert [t.title for t in service.list_tasks_in_column(todo.id)] == ["B", "C"]
    assert [t.title for t in service.list_tasks_in_column(doing.id)] == ["A"]


def test_move_task_clamps_out_of_range_index(service: TaskService) -> None:
    board = service.create_board("Work")
    todo = board.columns[0]
    doing = service.create_column(board.id, "In Progress")
    a = service.create_task(todo.id, "A")
    service.create_task(todo.id, "B")

    # An index beyond the end should clamp to the end of the target column.
    service.move_task(a.id, doing.id, 99)
    assert [t.title for t in service.list_tasks_in_column(doing.id)] == ["A"]
    assert [t.title for t in service.list_tasks_in_column(todo.id)] == ["B"]


def test_move_task_reorder_within_column(service: TaskService) -> None:
    board = service.create_board("Work")
    todo = board.columns[0]
    service.create_task(todo.id, "A")
    service.create_task(todo.id, "B")
    c = service.create_task(todo.id, "C")

    # Move C to the front of the same column.
    service.move_task(c.id, todo.id, 0)
    assert [t.title for t in service.list_tasks_in_column(todo.id)] == ["C", "A", "B"]


def test_delete_task(service: TaskService) -> None:
    board = service.create_board("Work")
    task = service.create_task(board.columns[0].id, "Delete me")
    service.delete_task(task.id)
    assert service.get_task(task.id) is None


def test_delete_missing_task_raises(service: TaskService) -> None:
    with pytest.raises(LookupError):
        service.delete_task(9999)
