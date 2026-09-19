"""The application main window.

Composes the sidebar (board navigation) and the board view (columns and
cards), and routes user actions to the :class:`TaskService`.
"""

from __future__ import annotations

from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QHBoxLayout, QMainWindow, QWidget

from kanban.services.database import Database, create_database
from kanban.services.task_service import TaskService
from kanban.ui.board_view import BoardView
from kanban.ui.sidebar import Sidebar


class MainWindow(QMainWindow):
    """Top-level window for the KanBan application."""

    def __init__(self, database: Database | None = None) -> None:
        super().__init__()
        self._database = database if database is not None else create_database()
        self._database.init_db()
        self._service = TaskService(self._database)
        self._current_board_id: int | None = None

        self.setWindowTitle("KanBan")
        self.resize(1100, 700)

        central = QWidget()
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._sidebar = Sidebar()
        self._board_view = BoardView()
        layout.addWidget(self._sidebar)
        layout.addWidget(self._board_view, 1)
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
            self._board_view.load_board(board)

    # -- Slots ------------------------------------------------------------
    def _on_board_selected(self, board_id: int) -> None:
        """Switch to the selected board."""
        self._current_board_id = board_id
        self._load_current_board()

    def _on_board_added(self, name: str) -> None:
        """Create a new board and switch to it."""
        board = self._service.create_board(name)
        self._current_board_id = board.id
        self._refresh_sidebar()
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

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802 - Qt naming
        """Dispose of the database engine when the window closes."""
        self._database.dispose()
        super().closeEvent(event)
