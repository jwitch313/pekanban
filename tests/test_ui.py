"""Offscreen UI tests for the main window and its CRUD wiring."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from kanban.main_window import MainWindow
from kanban.services.database import create_database


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    """Provide a single offscreen QApplication for the whole session."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def window(qapp, tmp_path) -> MainWindow:
    """Provide a main window backed by a throwaway database."""
    db = create_database(tmp_path / "ui.db")
    win = MainWindow(database=db)
    yield win
    win.close()
    db.dispose()


def test_default_board_created(window: MainWindow) -> None:
    assert window._current_board_id is not None
    assert len(window._service.list_boards()) == 1


def test_add_board(window: MainWindow) -> None:
    window._on_board_added("Second Board")
    boards = window._service.list_boards()
    assert len(boards) == 2
    assert any(b.name == "Second Board" for b in boards)


def test_add_column_and_task(window: MainWindow) -> None:
    board_id = window._current_board_id
    assert board_id is not None
    window._on_column_added("In Progress")
    board = window._service.get_board_full(board_id)
    assert board is not None
    assert [c.title for c in board.columns] == ["To Do", "In Progress"]

    doing = board.columns[1]
    window._on_task_added(doing.id, "Ship it")
    board = window._service.get_board_full(board_id)
    assert board is not None
    assert [t.title for t in board.columns[1].tasks] == ["Ship it"]


def test_delete_task(window: MainWindow) -> None:
    board = window._service.get_board_full(window._current_board_id)
    assert board is not None
    column = board.columns[0]
    window._on_task_added(column.id, "Temp task")
    board = window._service.get_board_full(window._current_board_id)
    assert board is not None
    task = board.columns[0].tasks[0]
    window._on_task_deleted(task.id)
    board = window._service.get_board_full(window._current_board_id)
    assert board is not None
    assert board.columns[0].tasks == []


def test_board_view_reflects_columns(window: MainWindow) -> None:
    board = window._service.get_board_full(window._current_board_id)
    assert board is not None
    window._board_view.load_board(board)
    container = window._board_view.widget()
    assert container is not None
    # Count column widgets present in the layout.
    from kanban.ui.column_widget import ColumnWidget

    columns = list(container.findChildren(ColumnWidget))
    assert len(columns) == len(board.columns)
