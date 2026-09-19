"""A single draggable task card widget.

The card is presentational only: it displays a task's title, priority badge,
and due date, and emits signals when the user requests an action.
"""

from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from kanban.models import Priority

PRIORITY_COLORS: dict[Priority, str] = {
    Priority.LOW: "#4a90d9",
    Priority.MEDIUM: "#e0a800",
    Priority.HIGH: "#e07b39",
    Priority.URGENT: "#d9534f",
}


class CardWidget(QFrame):
    """A Kanban card representing a single task."""

    delete_requested = Signal(int)

    def __init__(self, task_id: int, title: str, priority: Priority, due_date: date | None) -> None:
        super().__init__()
        self._task_id = task_id
        self.setObjectName("card")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setAccessibleName(f"Task: {title}")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        title_label = QLabel(title)
        title_label.setWordWrap(True)
        title_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(title_label)

        meta_row = QHBoxLayout()
        meta_row.setSpacing(6)
        badge = QLabel(priority.value.capitalize())
        badge.setObjectName("priorityBadge")
        badge.setStyleSheet(f"color: {PRIORITY_COLORS[priority]}; font-weight: bold;")
        meta_row.addWidget(badge)

        if due_date is not None:
            due_label = QLabel(f"Due {due_date.isoformat()}")
            due_label.setObjectName("dueDate")
            meta_row.addWidget(due_label)

        meta_row.addStretch(1)
        delete_button = QPushButton("✕")
        delete_button.setFixedWidth(24)
        delete_button.setAccessibleName("Delete task")
        delete_button.clicked.connect(lambda: self.delete_requested.emit(self._task_id))
        meta_row.addWidget(delete_button)

        layout.addLayout(meta_row)

    @property
    def task_id(self) -> int:
        """The database id of the task this card represents."""
        return self._task_id
