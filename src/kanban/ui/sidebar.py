"""The sidebar: board navigation, creation, rename, and deletion."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
)

from kanban.models import Board
from kanban.ui import icons
from kanban.ui.label_panel import LabelPanel


class Sidebar(QFrame):
    """Lists the user's boards and lets them create, rename, and delete one.

    A board is renamed by double-clicking it (or the ✎ button) and editing it
    inline; deletion is requested with the ✕ button. Both emit
    :attr:`board_renamed` and :attr:`board_deleted` respectively.
    """

    board_selected = Signal(int)  # board_id
    board_added = Signal(str)  # name
    board_renamed = Signal(int, str)  # board_id, new_name
    board_deleted = Signal(int)  # board_id
    column_added = Signal(str)  # title
    label_added = Signal(str, str)  # name, color
    label_deleted = Signal(int)  # label_id
    help_requested = Signal()
    about_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("sidebar")
        self.setFixedWidth(220)
        self._renaming = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        header = QLabel("Boards")
        header.setObjectName("sidebarHeader")
        layout.addWidget(header)

        self._list = QListWidget()
        self._list.currentItemChanged.connect(self._on_current_changed)
        self._list.itemChanged.connect(self._on_item_changed)
        self._list.itemDoubleClicked.connect(self._start_rename)
        self._list.setEditTriggers(QListWidget.EditTrigger.DoubleClicked)
        layout.addWidget(self._list, 1)

        action_row = QHBoxLayout()
        rename_button = QPushButton()
        rename_button.setIcon(icons.icon("pencil"))
        rename_button.setFixedWidth(28)
        rename_button.setAccessibleName("Rename board")
        rename_button.setToolTip("Rename board")
        rename_button.clicked.connect(self._start_rename)
        action_row.addWidget(rename_button)
        delete_button = QPushButton()
        delete_button.setIcon(icons.icon("trash"))
        delete_button.setFixedWidth(28)
        delete_button.setAccessibleName("Delete board")
        delete_button.setToolTip("Delete board")
        delete_button.clicked.connect(self._delete_board)
        action_row.addWidget(delete_button)
        action_row.addStretch(1)
        layout.addLayout(action_row)

        add_row = QHBoxLayout()
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("New board…")
        self._name_edit.returnPressed.connect(self._submit_new_board)
        add_row.addWidget(self._name_edit)
        add_button = QPushButton()
        add_button.setIcon(icons.icon("plus"))
        add_button.setFixedWidth(28)
        add_button.setAccessibleName("Add board")
        add_button.setToolTip("Add board")
        add_button.clicked.connect(self._submit_new_board)
        add_row.addWidget(add_button)
        layout.addLayout(add_row)

        columns_header = QLabel("Columns")
        columns_header.setObjectName("sidebarHeader")
        layout.addWidget(columns_header)

        column_row = QHBoxLayout()
        self._column_edit = QLineEdit()
        self._column_edit.setPlaceholderText("New column…")
        self._column_edit.returnPressed.connect(self._submit_new_column)
        column_row.addWidget(self._column_edit)
        column_button = QPushButton()
        column_button.setIcon(icons.icon("plus"))
        column_button.setFixedWidth(28)
        column_button.setAccessibleName("Add column")
        column_button.setToolTip("Add a new column")
        column_button.clicked.connect(self._submit_new_column)
        column_row.addWidget(column_button)
        layout.addLayout(column_row)

        self._label_panel = LabelPanel()
        self._label_panel.label_added.connect(self.label_added)
        self._label_panel.label_deleted.connect(self.label_deleted)
        layout.addWidget(self._label_panel, 1)

        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(6)
        self._help_button = self._make_small_button("help", "Help", self.help_requested.emit)
        self._about_button = self._make_small_button("info", "About", self.about_requested.emit)
        bottom_row.addWidget(self._help_button)
        bottom_row.addWidget(self._about_button)
        layout.addLayout(bottom_row)

    @staticmethod
    def _make_small_button(icon_name: str, text: str, slot: object) -> QPushButton:
        """Build a compact icon+text button for the sidebar's bottom row.

        Each button is roughly half the width of the full-width label buttons
        so the two fit side by side in a single row, with a reduced height and
        smaller padding/font to read as a secondary action.
        """
        button = QPushButton(text)
        button.setIcon(icons.icon(icon_name))
        button.setAccessibleName(text)
        button.setToolTip(text)
        button.setStyleSheet(
            "QPushButton { padding: 3px 6px; font-size: 11px; }"
        )
        button.clicked.connect(slot)
        return button

    def _on_current_changed(self, current: QListWidgetItem | None, _previous: object) -> None:
        """Emit the selected board id when the current item changes."""
        if current is not None:
            board_id = current.data(Qt.ItemDataRole.UserRole)
            if isinstance(board_id, int):
                self.board_selected.emit(board_id)

    def _on_item_changed(self, item: QListWidgetItem) -> None:
        """Commit an inline rename when the edited item's text changes."""
        if not self._renaming:
            return
        self._renaming = False
        name = item.text().strip()
        board_id = item.data(Qt.ItemDataRole.UserRole)
        if name and isinstance(board_id, int):
            self.board_renamed.emit(board_id, name)

    def _start_rename(self, _item: QListWidgetItem | None = None) -> None:
        """Enter inline rename mode for the current board."""
        item: QListWidgetItem | None = self._list.currentItem()
        if item is None:
            return
        self._renaming = True
        self._list.editItem(item)

    def _delete_board(self) -> None:
        """Request deletion of the current board."""
        item: QListWidgetItem | None = self._list.currentItem()
        if item is None:
            return
        board_id = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(board_id, int):
            self.board_deleted.emit(board_id)

    def _submit_new_board(self) -> None:
        """Emit a new-board request if the name field is non-empty."""
        name = self._name_edit.text().strip()
        if not name:
            return
        self.board_added.emit(name)
        self._name_edit.clear()

    def _submit_new_column(self) -> None:
        """Emit a new-column request if the field is non-empty."""
        title = self._column_edit.text().strip()
        if not title:
            return
        self.column_added.emit(title)
        self._column_edit.clear()

    def load_labels(self, labels: list[tuple[int, str, str | None]]) -> None:
        """Populate the embedded label panel with the board's labels."""
        self._label_panel.load_labels(labels)

    def load_boards(self, boards: list[Board], selected_id: int | None = None) -> None:
        """Populate the board list and optionally select one."""
        self._renaming = False
        self._list.blockSignals(True)
        self._list.clear()
        for board in boards:
            item = QListWidgetItem(board.name)
            item.setData(Qt.ItemDataRole.UserRole, board.id)
            # Qt 6.11+ no longer marks list items editable by default, and
            # editItem() refuses to open an editor without this flag.
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
            self._list.addItem(item)
        if selected_id is not None:
            for i in range(self._list.count()):
                if self._list.item(i).data(Qt.ItemDataRole.UserRole) == selected_id:
                    self._list.setCurrentRow(i)
                    break
        elif self._list.count() > 0:
            self._list.setCurrentRow(0)
        self._list.blockSignals(False)
