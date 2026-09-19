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


# -- Column controls (rename / move / delete) -----------------------------
def test_column_rename_emits_signal(qapp) -> None:
    column = ColumnWidget(5, "To Do", [], index=0)
    captured: list[tuple[int, str]] = []
    column.column_renamed.connect(lambda *a: captured.append(a))

    column._start_rename()
    assert not column._rename_edit.isHidden()
    column._rename_edit.setText("Backlog")
    column._commit_rename()

    assert captured == [(5, "Backlog")]
    assert column._title_label.text() == "Backlog"
    assert column._rename_edit.isHidden()


def test_column_rename_blank_is_ignored(qapp) -> None:
    column = ColumnWidget(5, "To Do", [], index=0)
    captured: list[tuple[int, str]] = []
    column.column_renamed.connect(lambda *a: captured.append(a))

    column._start_rename()
    column._rename_edit.setText("   ")
    column._commit_rename()

    assert captured == []
    assert column._title_label.text() == "To Do"


def test_column_move_buttons_emit_index(qapp) -> None:
    column = ColumnWidget(5, "To Do", [], index=2)
    captured: list[tuple[int, int]] = []
    column.column_moved.connect(lambda *a: captured.append(a))

    column._move_left()
    column._move_right()
    assert captured == [(5, 1), (5, 3)]


def test_column_delete_emits_signal(qapp) -> None:
    column = ColumnWidget(5, "To Do", [], index=0)
    captured: list[int] = []
    column.column_deleted.connect(lambda v: captured.append(v))

    column._delete_column()
    assert captured == [5]


def test_board_view_forwards_column_signals(qapp) -> None:
    view = BoardView()
    renamed: list[tuple[int, str]] = []
    moved: list[tuple[int, int]] = []
    deleted: list[int] = []
    view.column_renamed.connect(lambda *a: renamed.append(a))
    view.column_moved.connect(lambda *a: moved.append(a))
    view.column_deleted.connect(lambda v: deleted.append(v))

    column = ColumnWidget(9, "To Do", [], index=0)
    view.add_column_widget(column)
    column.column_renamed.emit(9, "New")
    column.column_moved.emit(9, 1)
    column.column_deleted.emit(9)

    assert renamed == [(9, "New")]
    assert moved == [(9, 1)]
    assert deleted == [9]


def test_window_rename_column(window: MainWindow) -> None:
    board = window._service.get_board_full(window._current_board_id)
    assert board is not None
    column = board.columns[0]
    window._on_column_renamed(column.id, "Backlog")
    board = window._service.get_board_full(window._current_board_id)
    assert board is not None
    assert board.columns[0].title == "Backlog"


def test_window_move_column(window: MainWindow) -> None:
    board_id = window._current_board_id
    assert board_id is not None
    window._on_column_added("B")
    window._on_column_added("C")
    board = window._service.get_board_full(board_id)
    assert board is not None
    first = board.columns[0]

    window._on_column_moved(first.id, 2)
    board = window._service.get_board_full(board_id)
    assert board is not None
    assert [c.title for c in board.columns] == ["B", "C", "To Do"]


def test_window_delete_column(window: MainWindow) -> None:
    board_id = window._current_board_id
    assert board_id is not None
    window._on_column_added("In Progress")
    board = window._service.get_board_full(board_id)
    assert board is not None
    column = board.columns[1]

    window._on_column_deleted(column.id)
    board = window._service.get_board_full(board_id)
    assert board is not None
    assert [c.title for c in board.columns] == ["To Do"]


# -- Board controls (rename / delete) -------------------------------------
def test_sidebar_rename_emits_signal(qapp) -> None:
    from kanban.models import Board
    from kanban.ui.sidebar import Sidebar

    sidebar = Sidebar()
    captured: list[tuple[int, str]] = []
    sidebar.board_renamed.connect(lambda *a: captured.append(a))
    sidebar.load_boards([Board(id=1, name="A"), Board(id=2, name="B")])
    sidebar._list.setCurrentRow(0)
    item = sidebar._list.currentItem()
    assert item is not None
    sidebar._start_rename()
    item.setText("Renamed")
    assert captured == [(1, "Renamed")]


def test_sidebar_rename_blank_is_ignored(qapp) -> None:
    from kanban.models import Board
    from kanban.ui.sidebar import Sidebar

    sidebar = Sidebar()
    captured: list[tuple[int, str]] = []
    sidebar.board_renamed.connect(lambda *a: captured.append(a))
    sidebar.load_boards([Board(id=1, name="A")])
    sidebar._list.setCurrentRow(0)
    item = sidebar._list.currentItem()
    assert item is not None
    sidebar._start_rename()
    item.setText("   ")
    assert captured == []


def test_sidebar_delete_emits_signal(qapp) -> None:
    from kanban.models import Board
    from kanban.ui.sidebar import Sidebar

    sidebar = Sidebar()
    captured: list[int] = []
    sidebar.board_deleted.connect(lambda v: captured.append(v))
    sidebar.load_boards([Board(id=1, name="A"), Board(id=2, name="B")])
    sidebar._list.setCurrentRow(1)
    sidebar._delete_board()
    assert captured == [2]


def test_window_rename_board(window: MainWindow) -> None:
    board_id = window._current_board_id
    assert board_id is not None
    window._on_board_renamed(board_id, "Renamed Board")
    board = window._service.get_board(board_id)
    assert board is not None
    assert board.name == "Renamed Board"


def test_window_delete_board_switches_to_remaining(window: MainWindow) -> None:
    window._on_board_added("Second")
    first_id = window._current_board_id
    assert first_id is not None
    window._on_board_deleted(first_id)
    assert window._current_board_id != first_id
    assert len(window._service.list_boards()) == 1


def test_window_delete_last_board_creates_default(window: MainWindow) -> None:
    board_id = window._current_board_id
    assert board_id is not None
    window._on_board_deleted(board_id)
    assert window._current_board_id is not None
    boards = window._service.list_boards()
    assert len(boards) == 1
    assert boards[0].name == "My Board"
    assert window._current_board_id == boards[0].id
