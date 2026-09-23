"""Tests for the undo/redo service (Step 4, Slice 5)."""

from __future__ import annotations

import os
from datetime import date

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtGui import QKeySequence

from kanban.main_window import MainWindow
from kanban.models import Priority
from kanban.services.database import Database
from kanban.services.task_service import TaskService
from kanban.services.undo_redo import (
    CreateTaskCommand,
    DeleteTaskCommand,
    EditTaskCommand,
    MoveTaskCommand,
    UndoRedoService,
)


@pytest.fixture
def service(database: Database) -> TaskService:
    return TaskService(database)


@pytest.fixture
def undo(service: TaskService) -> UndoRedoService:
    return UndoRedoService(service)


def test_create_task_undo_removes_it(service: TaskService, undo: UndoRedoService) -> None:
    board = service.create_board("Work")
    column = board.columns[0]

    undo.execute(CreateTaskCommand(service, column.id, "New task"))
    assert [t.title for t in service.list_tasks_in_column(column.id)] == ["New task"]

    undo.undo()
    assert service.list_tasks_in_column(column.id) == []


def test_create_task_redo_restores_it(service: TaskService, undo: UndoRedoService) -> None:
    board = service.create_board("Work")
    column = board.columns[0]

    undo.execute(CreateTaskCommand(service, column.id, "New task"))
    undo.undo()
    assert service.list_tasks_in_column(column.id) == []

    undo.redo()
    assert [t.title for t in service.list_tasks_in_column(column.id)] == ["New task"]


def test_delete_task_undo_restores_it(service: TaskService, undo: UndoRedoService) -> None:
    board = service.create_board("Work")
    column = board.columns[0]
    task = service.create_task(column.id, "Doomed", priority=Priority.HIGH)

    undo.execute(DeleteTaskCommand(service, task.id))
    assert service.list_tasks_in_column(column.id) == []

    undo.undo()
    restored = service.list_tasks_in_column(column.id)
    assert len(restored) == 1
    assert restored[0].title == "Doomed"
    assert restored[0].priority is Priority.HIGH


def test_delete_task_undo_restores_labels(
    service: TaskService, undo: UndoRedoService
) -> None:
    board = service.create_board("Work")
    column = board.columns[0]
    label = service.create_label(board.id, "Urgent", "#ff0000")
    task = service.create_task(column.id, "Tagged")
    service.assign_label(task.id, label.id)

    undo.execute(DeleteTaskCommand(service, task.id))
    undo.undo()

    restored_id = service.list_tasks_in_column(column.id)[0].id
    restored = service.get_task(restored_id)
    assert restored is not None
    assert [lbl.id for lbl in restored.labels] == [label.id]


def test_move_task_undo_restores_origin(service: TaskService, undo: UndoRedoService) -> None:
    board = service.create_board("Work")
    todo = board.columns[0]
    doing = service.create_column(board.id, "In Progress")
    task = service.create_task(todo.id, "Move me")

    undo.execute(MoveTaskCommand(service, task.id, doing.id, 0))
    assert [t.id for t in service.list_tasks_in_column(doing.id)] == [task.id]
    assert service.list_tasks_in_column(todo.id) == []

    undo.undo()
    assert [t.id for t in service.list_tasks_in_column(todo.id)] == [task.id]
    assert service.list_tasks_in_column(doing.id) == []


def test_edit_task_undo_restores_fields(service: TaskService, undo: UndoRedoService) -> None:
    board = service.create_board("Work")
    column = board.columns[0]
    task = service.create_task(column.id, "Original")

    undo.execute(
        EditTaskCommand(
            service,
            task.id,
            {"title": "Renamed", "due_date": date(2025, 12, 1)},
        )
    )
    assert service.get_task(task.id).title == "Renamed"

    undo.undo()
    restored = service.get_task(task.id)
    assert restored is not None
    assert restored.title == "Original"
    assert restored.due_date is None


def test_execute_clears_redo_stack(service: TaskService, undo: UndoRedoService) -> None:
    board = service.create_board("Work")
    column = board.columns[0]

    undo.execute(CreateTaskCommand(service, column.id, "A"))
    undo.undo()
    assert undo.can_redo()

    undo.execute(CreateTaskCommand(service, column.id, "B"))
    assert not undo.can_redo()


def test_max_depth_limits_history(service: TaskService) -> None:
    board = service.create_board("Work")
    column = board.columns[0]
    limited = UndoRedoService(service, max_depth=2)

    for i in range(4):
        limited.execute(CreateTaskCommand(service, column.id, f"Task {i}"))

    # Only the two most recent actions are retained.
    limited.undo()
    limited.undo()
    assert not limited.can_undo()


def test_invalid_max_depth_raises(service: TaskService) -> None:
    with pytest.raises(ValueError):
        UndoRedoService(service, max_depth=0)


def test_clear_discards_history(service: TaskService, undo: UndoRedoService) -> None:
    board = service.create_board("Work")
    column = board.columns[0]

    undo.execute(CreateTaskCommand(service, column.id, "A"))
    undo.undo()
    undo.clear()

    assert not undo.can_undo()
    assert not undo.can_redo()


def test_undo_redo_noop_when_empty(undo: UndoRedoService) -> None:
    assert not undo.can_undo()
    assert not undo.can_redo()
    undo.undo()
    undo.redo()


def test_window_shortcuts_registered(window: MainWindow) -> None:
    keys = {shortcut.key().toString() for shortcut in window._shortcuts}
    assert QKeySequence("Ctrl+Z").toString() in keys
    assert QKeySequence("Ctrl+Y").toString() in keys


def test_window_undo_redo_roundtrip(window: MainWindow) -> None:
    window._on_column_added("Temp")
    board = window._service.get_board_full(window._current_board_id)
    assert board is not None
    column = board.columns[-1]

    window._on_task_added(column.id, "Undoable")
    assert len(window._service.list_tasks_in_column(column.id)) == 1

    window._shortcut_undo()
    assert window._service.list_tasks_in_column(column.id) == []

    window._shortcut_redo()
    assert len(window._service.list_tasks_in_column(column.id)) == 1
