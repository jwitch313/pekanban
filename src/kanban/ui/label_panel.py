"""A panel for managing a board's labels: create and delete them.

The panel is presentational only: it lists the board's labels (each with a
color swatch), lets the user create a new label with a chosen color, and
request deletion of the selected label. It emits :attr:`label_added` and
:attr:`label_deleted` for the :class:`~kanban.main_window.MainWindow` to route
to the :class:`~kanban.services.task_service.TaskService`.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
)

from kanban.ui import icons

#: Preset label colors offered in the color picker (hex values, used as data).
PRESET_COLORS: list[str] = [
    "#d9534f",  # red
    "#e07b39",  # orange
    "#e0a800",  # amber
    "#5cb85c",  # green
    "#16a085",  # teal
    "#4a90d9",  # blue
    "#5c6bc0",  # indigo
    "#9b59b6",  # purple
    "#e91e8c",  # pink
    "#888888",  # gray
]

#: Human-readable names shown in the picker, aligned with ``PRESET_COLORS``.
PRESET_COLOR_NAMES: list[str] = [
    "Red",
    "Orange",
    "Amber",
    "Green",
    "Teal",
    "Blue",
    "Indigo",
    "Purple",
    "Pink",
    "Gray",
]


class LabelPanel(QFrame):
    """Create and delete labels scoped to the current board."""

    label_added = Signal(str, str)  # name, color
    label_deleted = Signal(int)  # label_id

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("labelPanel")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        header = QLabel("Labels")
        header.setObjectName("sidebarHeader")
        layout.addWidget(header)

        self._list = QListWidget()
        self._list.setAccessibleName("Label list")
        layout.addWidget(self._list, 1)

        add_row = QHBoxLayout()
        add_row.setSpacing(4)
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("New label…")
        self._name_edit.setAccessibleName("New label name")
        self._name_edit.returnPressed.connect(self._submit_new_label)
        add_row.addWidget(self._name_edit, 1)

        self._color_combo = QComboBox()
        self._color_combo.setAccessibleName("Label color")
        for name, color in zip(PRESET_COLOR_NAMES, PRESET_COLORS):
            self._color_combo.addItem(self._swatch_icon(color), name, color)
        self._color_combo.setStyleSheet(
            "QComboBox { padding: 2px; }"
            "QComboBox QAbstractItemView { background-color: #ffffff; }"
        )
        add_row.addWidget(self._color_combo)

        add_button = QPushButton()
        add_button.setIcon(icons.icon("plus"))
        add_button.setFixedWidth(28)
        add_button.setAccessibleName("Add label")
        add_button.setToolTip("Add label")
        add_button.clicked.connect(self._submit_new_label)
        add_row.addWidget(add_button)
        layout.addLayout(add_row)

        delete_button = QPushButton("Delete label")
        delete_button.setIcon(icons.icon("trash"))
        delete_button.setAccessibleName("Delete label")
        delete_button.setToolTip("Delete label")
        delete_button.clicked.connect(self._delete_label)
        layout.addWidget(delete_button)

    def _submit_new_label(self) -> None:
        """Emit a new-label request if the name field is non-empty."""
        name = self._name_edit.text().strip()
        if not name:
            return
        color = self._color_combo.currentData()
        self.label_added.emit(name, color)
        self._name_edit.clear()

    def _delete_label(self) -> None:
        """Request deletion of the currently selected label."""
        item: QListWidgetItem | None = self._list.currentItem()
        if item is None:
            return
        label_id = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(label_id, int):
            self.label_deleted.emit(label_id)

    def load_labels(self, labels: list[tuple[int, str, str | None]]) -> None:
        """Populate the label list from ``(id, name, color)`` tuples.

        Each row shows the label name (in the default, readable foreground)
        alongside a small color swatch icon so the color is visible at a glance.
        """
        self._list.blockSignals(True)
        self._list.clear()
        for label_id, name, color in labels:
            item = QListWidgetItem(name)
            item.setData(Qt.ItemDataRole.UserRole, label_id)
            swatch = color if color else "#888888"
            item.setIcon(self._swatch_icon(swatch))
            self._list.addItem(item)
        self._list.blockSignals(False)

    @staticmethod
    def _swatch_icon(color: str) -> QIcon:
        """Build a small rounded color swatch icon for the given hex color."""
        pixmap = QPixmap(14, 14)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor("#8a8f98"), 1))
        painter.setBrush(QColor(color))
        painter.drawRoundedRect(1, 1, 12, 12, 3, 3)
        painter.end()
        return QIcon(pixmap)
