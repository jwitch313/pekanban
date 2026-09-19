"""The application main window.

Composes the sidebar (board navigation) and the board view (columns and
cards), and routes user actions to the :class:`TaskService`.
"""

from __future__ import annotations

from datetime import date
from typing import cast

from PySide6.QtGui import QCloseEvent, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLineEdit,
    QMainWindow,
    QVBoxLayout,
    QWidget,
)

from kanban.models import Board, Priority
from kanban.services.database import Database, create_database
from kanban.services.task_service import TaskService
from kanban.ui.board_view import BoardView
from kanban.ui.search_bar import Filters, SearchBar
from kanban.ui.sidebar import Sidebar


class MainWindow(QMainWindow):
    """Top-level window for the KanBan application."""

    def __init__(self, database: Database | None = None) -> None:
        super().__init__()
        self._database = database if database is not None else create_database()
        self._database.init_db()
        self._service = TaskService(self._database)
        self._current_board_id: int | None = None
        self._filters: Filters = {}

        self.setWindowTitle("KanBan")
        self.resize(1100, 700)

        central = QWidget()
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._sidebar = Sidebar()
        self._search_bar = SearchBar()
        self._board_view = BoardView()
        layout.addWidget(self._sidebar)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        right_layout.addWidget(self._search_bar)
        right_layout.addWidget(self._board_view, 1)
        layout.addWidget(right, 1)
        self.setCentralWidget(central)

        self._sidebar.board_selected.connect(self._on_board_selected)
        self._sidebar.board_added.connect(self._on_board_added)
        self._sidebar.board_renamed.connect(self._on_board_renamed)
        self._sidebar.board_deleted.connect(self._on_board_deleted)
        self._board_view.column_added.connect(self._on_column_added)
        self._board_view.column_renamed.connect(self._on_column_renamed)
        self._board_view.column_moved.connect(self._on_column_moved)
        self._board_view.column_deleted.connect(self._on_column_deleted)
        self._board_view.task_added.connect(self._on_task_added)
        self._board_view.task_deleted.connect(self._on_task_deleted)
        self._board_view.task_moved.connect(self._on_task_moved)
        self._sidebar.label_added.connect(self._on_label_added)
        self._sidebar.label_deleted.connect(self._on_label_deleted)
        self._board_view.label_assign_requested.connect(self._on_label_assigned)
        self._board_view.label_unassign_requested.connect(self._on_label_unassigned)
        self._search_bar.filters_changed.connect(self._apply_filters)

        self._setup_shortcuts()

        self._refresh_sidebar()
        self._ensure_default_board()

    def _ensure_default_board(self) -> None:
        """Create a starter board if the user has none yet."""
        if self._current_board_id is None:
            board = self._service.create_board("My Board")
            self._current_board_id = board.id
        self._refresh_sidebar()
        self._load_current_board()

    def _refresh_sidebar(self) -> None:
        """Reload the board list in the sidebar."""
        boards = self._service.list_boards()
        self._sidebar.load_boards(boards, self._current_board_id)

    def _load_current_board(self) -> None:
        """Load the currently selected board into the board view."""
        if self._current_board_id is None:
            return
        board = self._service.get_board_full(self._current_board_id)
        if board is not None:
            visible = self._compute_visible_task_ids(board)
            self._board_view.load_board(board, visible)
            self._refresh_labels()
            self._search_bar.load_columns(
                [(column.id, column.title) for column in board.columns]
            )
            self._search_bar.load_labels(
                [(label.id, label.name) for label in board.labels]
            )

    def _is_active(self, filters: Filters) -> bool:
        """Return True if any filter in ``filters`` is set to a non-default value."""
        return bool(
            filters.get("query")
            or filters.get("priority") is not None
            or filters.get("column_id") is not None
            or filters.get("label_id") is not None
            or filters.get("due_before") is not None
            or filters.get("due_after") is not None
        )

    def _compute_visible_task_ids(self, board: Board) -> set[int] | None:
        """Return the set of task ids to render, or ``None`` to show all.

        When no filter is active every card is shown. Otherwise the board's
        tasks are filtered through :meth:`TaskService.search_tasks`.
        """
        if not self._is_active(self._filters):
            return None
        board_id = self._current_board_id
        if board_id is None:
            return None
        filters = self._filters
        tasks = self._service.search_tasks(
            board_id,
            query=cast(str, filters.get("query") or ""),
            priority=cast("Priority | None", filters.get("priority")),
            column_id=cast("int | None", filters.get("column_id")),
            label_id=cast("int | None", filters.get("label_id")),
            due_before=cast("date | None", filters.get("due_before")),
            due_after=cast("date | None", filters.get("due_after")),
        )
        return {task.id for task in tasks}

    def _refresh_labels(self) -> None:
        """Reload the current board's labels into the sidebar label panel."""
        if self._current_board_id is None:
            return
        labels = self._service.list_labels(self._current_board_id)
        self._sidebar.load_labels([(label.id, label.name, label.color) for label in labels])

    # -- Slots ------------------------------------------------------------
    def _apply_filters(self, filters: Filters) -> None:
        """Store the active filters and re-render the board."""
        self._filters = filters
        self._load_current_board()

    def _on_board_selected(self, board_id: int) -> None:
        """Switch to the selected board."""
        self._current_board_id = board_id
        self._reset_filters()
        self._load_current_board()

    def _on_board_added(self, name: str) -> None:
        """Create a new board and switch to it."""
        board = self._service.create_board(name)
        self._current_board_id = board.id
        self._refresh_sidebar()
        self._reset_filters()
        self._load_current_board()

    def _on_board_renamed(self, board_id: int, name: str) -> None:
        """Rename a board and refresh the sidebar."""
        self._service.rename_board(board_id, name)
        self._refresh_sidebar()

    def _on_board_deleted(self, board_id: int) -> None:
        """Delete a board, switching to another board if it was the current one."""
        self._service.delete_board(board_id)
        if board_id == self._current_board_id:
            self._current_board_id = None
            boards = self._service.list_boards()
            if boards:
                self._current_board_id = boards[0].id
            else:
                self._current_board_id = self._service.create_board("My Board").id
        self._refresh_sidebar()
        self._reset_filters()
        self._load_current_board()

    def _on_column_added(self, title: str) -> None:
        """Add a column to the current board and refresh."""
        if self._current_board_id is not None:
            self._service.create_column(self._current_board_id, title)
            self._load_current_board()

    def _on_column_renamed(self, column_id: int, title: str) -> None:
        """Rename a column and refresh."""
        self._service.rename_column(column_id, title)
        self._load_current_board()

    def _on_column_moved(self, column_id: int, index: int) -> None:
        """Move a column to a new position and refresh."""
        self._service.move_column(column_id, index)
        self._load_current_board()

    def _on_column_deleted(self, column_id: int) -> None:
        """Delete a column and refresh."""
        self._service.delete_column(column_id)
        self._load_current_board()

    def _on_task_added(self, column_id: int, title: str) -> None:
        """Add a task to a column and refresh."""
        self._service.create_task(column_id, title)
        self._load_current_board()

    def _on_task_deleted(self, task_id: int) -> None:
        """Delete a task and refresh."""
        self._service.delete_task(task_id)
        self._load_current_board()

    def _on_task_moved(self, task_id: int, column_id: int, index: int) -> None:
        """Move a task to a new column/position (drag-and-drop) and refresh."""
        self._service.move_task(task_id, column_id, index)
        self._load_current_board()

    def _on_label_added(self, name: str, color: str) -> None:
        """Create a label on the current board and refresh."""
        if self._current_board_id is not None:
            self._service.create_label(self._current_board_id, name, color)
            self._load_current_board()

    def _on_label_deleted(self, label_id: int) -> None:
        """Delete a label and refresh."""
        self._service.delete_label(label_id)
        self._load_current_board()

    def _on_label_assigned(self, task_id: int, label_id: int) -> None:
        """Assign a label to a task and refresh."""
        self._service.assign_label(task_id, label_id)
        self._load_current_board()

    def _on_label_unassigned(self, task_id: int, label_id: int) -> None:
        """Remove a label from a task and refresh."""
        self._service.unassign_label(task_id, label_id)
        self._load_current_board()

    def _reset_filters(self) -> None:
        """Clear the active filters and reset the search bar (no re-render)."""
        self._filters = {}
        self._search_bar.reset()

    # -- Keyboard shortcuts ----------------------------------------------
    def _setup_shortcuts(self) -> None:
        """Register application-wide keyboard shortcuts.

        ``Ctrl+N`` focuses the add-column field, ``Ctrl+T`` focuses the first
        column's add-task field, and ``Esc`` clears the focused inline edit.
        """
        new_column = QShortcut(QKeySequence("Ctrl+N"), self)
        new_column.activated.connect(self._shortcut_new_column)

        new_task = QShortcut(QKeySequence("Ctrl+T"), self)
        new_task.activated.connect(self._shortcut_new_task)

        cancel = QShortcut(QKeySequence("Esc"), self)
        cancel.activated.connect(self._shortcut_cancel)

        self._shortcuts = [new_column, new_task, cancel]

    def _shortcut_new_column(self) -> None:
        """Focus the inline add-column field."""
        self._board_view.focus_add_column()

    def _shortcut_new_task(self) -> None:
        """Focus the first column's inline add-task field."""
        self._board_view.focus_first_task_input()

    def _shortcut_cancel(self) -> None:
        """Clear the currently focused inline edit field, if any."""
        focus = QApplication.focusWidget()
        if isinstance(focus, QLineEdit):
            focus.clear()

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802 - Qt naming
        """Dispose of the database engine when the window closes."""
        self._database.dispose()
        super().closeEvent(event)
