"""Offscreen UI tests for the main window and its CRUD wiring."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from datetime import date, timedelta

import pytest
from PySide6.QtCore import QMimeData, QPoint, Qt
from PySide6.QtGui import QDropEvent
from PySide6.QtWidgets import QApplication

from kanban.main_window import MainWindow
from kanban.models import Priority
from kanban.services.database import create_database
from kanban.ui.board_view import BoardView
from kanban.ui.card_widget import KANBAN_TASK_MIME, PRIORITY_COLORS, CardWidget
from kanban.ui.column_widget import ColumnWidget


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


def test_card_make_mime_data(qapp) -> None:
    card = CardWidget(7, "Task", Priority.HIGH, None)
    mime = card.make_mime_data()
    assert mime.hasFormat(KANBAN_TASK_MIME)
    assert bytes(mime.data(KANBAN_TASK_MIME)).decode("utf-8") == "7"


def test_card_should_start_drag(qapp) -> None:
    card = CardWidget(1, "Task", Priority.LOW, None)
    # No drag has been initiated yet.
    assert card._should_start_drag(QPoint(100, 100)) is False
    card._drag_start = QPoint(0, 0)
    # Within the drag threshold.
    assert card._should_start_drag(QPoint(3, 3)) is False
    # Beyond the drag threshold.
    assert card._should_start_drag(QPoint(10, 0)) is True


def test_card_overdue_highlighting(qapp) -> None:
    past = date.today() - timedelta(days=1)
    future = date.today() + timedelta(days=1)
    assert CardWidget(1, "Old", Priority.LOW, past).overdue is True
    assert CardWidget(2, "New", Priority.LOW, future).overdue is False
    assert CardWidget(3, "No due", Priority.LOW, None).overdue is False


def test_priority_colors_cover_all_priorities(qapp) -> None:
    assert set(PRIORITY_COLORS) == set(Priority)


def test_column_accepts_drop_and_emits_task_moved(qapp) -> None:
    column = ColumnWidget(
        5, "To Do", [(10, "A", Priority.LOW, None), (11, "B", Priority.HIGH, None)]
    )
    captured: list[tuple[int, int, int]] = []
    column.task_moved.connect(lambda *a: captured.append(a))

    mime = QMimeData()
    mime.setData(KANBAN_TASK_MIME, b"42")
    drop = QDropEvent(
        QPoint(10, 10),
        Qt.DropAction.CopyAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    column.dropEvent(drop)
    assert captured == [(42, 5, 0)]


def test_column_drop_index_boundaries(qapp) -> None:
    column = ColumnWidget(
        5, "To Do", [(10, "A", Priority.LOW, None), (11, "B", Priority.HIGH, None)]
    )
    # Dropping above the first card yields index 0.
    assert column._drop_index_at(QPoint(0, 0)) == 0
    # Dropping below every card yields the number of cards.
    assert column._drop_index_at(QPoint(0, 100000)) == 2


def test_board_view_forwards_task_moved(qapp) -> None:
    view = BoardView()
    captured: list[tuple[int, int, int]] = []
    view.task_moved.connect(lambda *a: captured.append(a))
    column = ColumnWidget(9, "To Do", [])
    view.add_column_widget(column)
    column.task_moved.emit(1, 9, 0)
    assert captured == [(1, 9, 0)]


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
