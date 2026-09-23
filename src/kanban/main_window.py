"""The application main window.

Composes the sidebar (board navigation) and the board view (columns and
cards), and routes user actions to the :class:`TaskService`.
"""

from __future__ import annotations

from datetime import date
from typing import cast

from PySide6.QtGui import QCloseEvent, QIcon, QKeySequence, QShortcut, QShowEvent
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLineEdit,
    QMainWindow,
    QVBoxLayout,
    QWidget,
)

from kanban.assets import asset_path
from kanban.models import Board, Priority
from kanban.services.database import Database, create_database
from kanban.services.settings_service import SettingsService
from kanban.services.task_service import TaskService
from kanban.services.undo_redo import (
    CreateTaskCommand,
    DeleteTaskCommand,
    MoveTaskCommand,
    UndoRedoService,
)
from kanban.ui.board_view import BoardView
from kanban.ui.search_bar import Filters, SearchBar
from kanban.ui.sidebar import Sidebar
from kanban.ui.theme import ThemeMode, apply_theme, resolve_theme_mode, title_bar_color
from kanban.ui.titlebar import set_title_bar_color


class MainWindow(QMainWindow):
    """Top-level window for the PeKanBan application."""

    def __init__(self, database: Database | None = None) -> None:
        super().__init__()
        self._database = database if database is not None else create_database()
        self._database.init_db()
        self._service = TaskService(self._database)
        self._undo = UndoRedoService(self._service)
        self._settings = SettingsService(self._database)
        self._current_board_id: int | None = None
        self._filters: Filters = {}
        self._resolved_theme: ThemeMode | None = None
        self._viewing_archive = False

        self.setWindowTitle("PeKanBan")
        self.resize(1100, 700)
        self._apply_theme(self._settings.theme_mode())

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
        self._sidebar.column_added.connect(self._on_column_added)
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
        self._board_view.subtask_added.connect(self._on_subtask_added)
        self._board_view.subtask_toggled.connect(self._on_subtask_toggled)
        self._board_view.subtask_deleted.connect(self._on_subtask_deleted)
        self._board_view.priority_changed.connect(self._on_priority_changed)
        self._board_view.due_date_changed.connect(self._on_due_date_changed)
        self._board_view.description_changed.connect(self._on_description_changed)
        self._board_view.title_changed.connect(self._on_title_changed)
        self._board_view.archive_requested.connect(self._on_task_archived)
        self._board_view.restore_requested.connect(self._on_task_restored)
        self._search_bar.filters_changed.connect(self._apply_filters)
        self._search_bar.theme_selected.connect(self._on_theme_selected)
        self._search_bar.view_archive_requested.connect(self._on_view_archive_toggled)
        self._search_bar.set_theme_mode(self._settings.theme_mode())

        self._setup_shortcuts()

        self._refresh_sidebar()
        self._ensure_default_board()

    def _ensure_default_board(self) -> None:
        """Select an existing board, or create a starter board if none exist."""
        if self._current_board_id is None:
            boards = self._service.list_boards()
            if boards:
                self._current_board_id = boards[0].id
            else:
                self._current_board_id = self._service.create_board("My Board").id
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
            if self._viewing_archive:
                self._board_view.load_archived(
                    self._service.list_archived_tasks(self._current_board_id),
                    board_labels=[(label.id, label.name, label.color) for label in board.labels],
                )
            else:
                visible = self._compute_visible_task_ids(board)
                self._board_view.load_board(board, visible)
            self._refresh_labels()
            self._search_bar.load_columns([(column.id, column.title) for column in board.columns])
            self._search_bar.load_labels([(label.id, label.name) for label in board.labels])

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
        self._exit_archive_view()
        self._reset_filters()
        self._load_current_board()

    def _on_board_added(self, name: str) -> None:
        """Create a new board and switch to it."""
        board = self._service.create_board(name)
        self._current_board_id = board.id
        self._refresh_sidebar()
        self._exit_archive_view()
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
        self._exit_archive_view()
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
        """Add a task to a column and refresh (undoable)."""
        self._undo.execute(CreateTaskCommand(self._service, column_id, title))
        self._load_current_board()

    def _on_task_deleted(self, task_id: int) -> None:
        """Delete a task and refresh (undoable)."""
        self._undo.execute(DeleteTaskCommand(self._service, task_id))
        self._load_current_board()

    def _on_task_moved(self, task_id: int, column_id: int, index: int) -> None:
        """Move a task to a new column/position (drag-and-drop) and refresh."""
        self._undo.execute(MoveTaskCommand(self._service, task_id, column_id, index))
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

    def _on_subtask_added(self, task_id: int, title: str) -> None:
        """Add a sub-task to a task and refresh."""
        self._service.add_subtask(task_id, title)
        self._load_current_board()

    def _on_subtask_toggled(self, subtask_id: int) -> None:
        """Toggle a sub-task's completed state and refresh."""
        self._service.toggle_subtask(subtask_id)
        self._load_current_board()

    def _on_subtask_deleted(self, subtask_id: int) -> None:
        """Delete a sub-task and refresh."""
        self._service.delete_subtask(subtask_id)
        self._load_current_board()

    def _on_priority_changed(self, task_id: int, priority: object) -> None:
        """Change a task's priority and refresh."""
        self._service.update_task(task_id, priority=priority)
        self._load_current_board()

    def _on_due_date_changed(self, task_id: int, due_date: object) -> None:
        """Set or clear a task's due date and refresh."""
        self._service.update_task(task_id, due_date=due_date)
        self._load_current_board()

    def _on_description_changed(self, task_id: int, description: object) -> None:
        """Set or clear a task's description and refresh."""
        self._service.update_task(task_id, description=description)
        self._load_current_board()

    def _on_title_changed(self, task_id: int, title: str) -> None:
        """Rename a task's title and refresh."""
        self._service.update_task(task_id, title=title)
        self._load_current_board()

    def _on_task_archived(self, task_id: int) -> None:
        """Archive a task and refresh the current view."""
        self._service.archive_task(task_id)
        self._load_current_board()

    def _on_task_restored(self, task_id: int) -> None:
        """Restore an archived task and refresh the current view."""
        self._service.restore_task(task_id)
        self._load_current_board()

    def _on_view_archive_toggled(self) -> None:
        """Toggle between the normal board view and the archive view."""
        self._viewing_archive = not self._viewing_archive
        self._search_bar.set_viewing_archive(self._viewing_archive)
        self._load_current_board()

    def _exit_archive_view(self) -> None:
        """Return to the normal board view (used when switching boards)."""
        if self._viewing_archive:
            self._viewing_archive = False
            self._search_bar.set_viewing_archive(False)

    def _reset_filters(self) -> None:
        """Clear the active filters and reset the search bar (no re-render)."""
        self._filters = {}
        self._search_bar.reset()

    # -- Theme ------------------------------------------------------------
    def _apply_theme(self, mode: str) -> None:
        """Resolve a stored theme preference and apply it to the app."""
        resolved = resolve_theme_mode(mode)
        self._resolved_theme = resolved
        app = QApplication.instance()
        if app is not None:
            apply_theme(cast("QApplication", app), resolved)
        self._apply_window_icon(resolved)
        self._apply_title_bar_color()

    def _apply_window_icon(self, resolved: ThemeMode) -> None:
        """Use the light-grey logo on dark backgrounds and the brown one on light."""
        name = "logo-icon-dark.svg" if resolved is ThemeMode.DARK else "logo-icon.svg"
        self.setWindowIcon(QIcon(str(asset_path(name))))

    def _apply_title_bar_color(self) -> None:
        """Recolor the native Windows title bar to match the active theme.

        A no-op on other platforms or when the DWM API is unavailable.
        """
        if self._resolved_theme is None:
            return
        set_title_bar_color(int(self.winId()), title_bar_color(self._resolved_theme))

    def showEvent(self, event: QShowEvent) -> None:  # noqa: N802 - Qt naming
        """Re-apply the title-bar color once the native window exists."""
        super().showEvent(event)
        self._apply_title_bar_color()

    def _on_theme_selected(self, mode: str) -> None:
        """Persist the chosen theme preference and re-apply it immediately."""
        self._settings.set_theme_mode(mode)
        self._apply_theme(mode)
        self._search_bar.set_theme_mode(mode)

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

        undo = QShortcut(QKeySequence("Ctrl+Z"), self)
        undo.activated.connect(self._shortcut_undo)

        redo = QShortcut(QKeySequence("Ctrl+Y"), self)
        redo.activated.connect(self._shortcut_redo)

        self._shortcuts = [new_column, new_task, cancel, undo, redo]

    def _shortcut_new_column(self) -> None:
        """Focus the sidebar's add-column field."""
        self._sidebar._column_edit.setFocus()

    def _shortcut_new_task(self) -> None:
        """Focus the first column's inline add-task field."""
        self._board_view.focus_first_task_input()

    def _shortcut_cancel(self) -> None:
        """Clear the currently focused inline edit field, if any."""
        focus = QApplication.focusWidget()
        if isinstance(focus, QLineEdit):
            focus.clear()

    def _shortcut_undo(self) -> None:
        """Undo the most recent task action and refresh the board."""
        if self._undo.can_undo():
            self._undo.undo()
            self._load_current_board()

    def _shortcut_redo(self) -> None:
        """Redo the most recently undone task action and refresh the board."""
        if self._undo.can_redo():
            self._undo.redo()
            self._load_current_board()

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802 - Qt naming
        """Dispose of the database engine when the window closes."""
        self._database.dispose()
        super().closeEvent(event)
