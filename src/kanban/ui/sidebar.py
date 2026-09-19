"""The sidebar: board navigation and board creation."""

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


class Sidebar(QFrame):
    """Lists the user's boards and lets them create a new one."""

    board_selected = Signal(int)  # board_id
    board_added = Signal(str)  # name

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("sidebar")
        self.setFixedWidth(220)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        header = QLabel("Boards")
        header.setObjectName("sidebarHeader")
        layout.addWidget(header)

        self._list = QListWidget()
        self._list.currentItemChanged.connect(self._on_current_changed)
        layout.addWidget(self._list, 1)

        add_row = QHBoxLayout()
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("New board…")
        self._name_edit.returnPressed.connect(self._submit_new_board)
        add_row.addWidget(self._name_edit)
        add_button = QPushButton("+")
        add_button.setFixedWidth(28)
        add_button.setAccessibleName("Add board")
        add_button.clicked.connect(self._submit_new_board)
        add_row.addWidget(add_button)
        layout.addLayout(add_row)

    def _on_current_changed(self, current: QListWidgetItem | None, _previous: object) -> None:
        """Emit the selected board id when the current item changes."""
        if current is not None:
            board_id = current.data(Qt.ItemDataRole.UserRole)
            if isinstance(board_id, int):
                self.board_selected.emit(board_id)

    def _submit_new_board(self) -> None:
        """Emit a new-board request if the name field is non-empty."""
        name = self._name_edit.text().strip()
        if not name:
            return
        self.board_added.emit(name)
        self._name_edit.clear()

    def load_boards(self, boards: list[Board], selected_id: int | None = None) -> None:
        """Populate the board list and optionally select one."""
        self._list.blockSignals(True)
        self._list.clear()
        for board in boards:
            item = QListWidgetItem(board.name)
            item.setData(Qt.ItemDataRole.UserRole, board.id)
            self._list.addItem(item)
        if selected_id is not None:
            for i in range(self._list.count()):
                if self._list.item(i).data(Qt.ItemDataRole.UserRole) == selected_id:
                    self._list.setCurrentRow(i)
                    break
        elif self._list.count() > 0:
            self._list.setCurrentRow(0)
        self._list.blockSignals(False)
