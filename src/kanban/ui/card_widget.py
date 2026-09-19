"""A single draggable task card widget.

The card is presentational only: it displays a task's title, priority badge,
and due date, and emits signals when the user requests an action. It also
supports being dragged out of its column (F-01) and highlights overdue due
dates (F-04).
"""

from __future__ import annotations

from datetime import date

from PySide6.QtCore import QMimeData, QPoint, Qt, Signal
from PySide6.QtGui import QDrag, QMouseEvent
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from kanban.models import Priority

#: MIME type used to identify a Kanban task during a drag operation.
KANBAN_TASK_MIME = "application/x-kanban-task"

#: Minimum pointer travel (px, Manhattan distance) before a press becomes a drag.
_DRAG_THRESHOLD = 8

PRIORITY_COLORS: dict[Priority, str] = {
    Priority.LOW: "#4a90d9",
    Priority.MEDIUM: "#e0a800",
    Priority.HIGH: "#e07b39",
    Priority.URGENT: "#d9534f",
}

OVERDUE_COLOR = "#d9534f"


class CardWidget(QFrame):
    """A Kanban card representing a single task."""

    delete_requested = Signal(int)

    def __init__(self, task_id: int, title: str, priority: Priority, due_date: date | None) -> None:
        super().__init__()
        self._task_id = task_id
        self._drag_start: QPoint | None = None
        self._overdue = False
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
            if due_date < date.today():
                self._overdue = True
                due_label.setStyleSheet(f"color: {OVERDUE_COLOR}; font-weight: bold;")
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

    @property
    def overdue(self) -> bool:
        """Whether the task's due date is in the past."""
        return self._overdue

    # -- Drag-and-drop ----------------------------------------------------
    def make_mime_data(self) -> QMimeData:
        """Build the MIME payload identifying this card's task for a drag."""
        mime = QMimeData()
        mime.setData(KANBAN_TASK_MIME, str(self._task_id).encode("utf-8"))
        return mime

    def _should_start_drag(self, current: QPoint) -> bool:
        """Return ``True`` once the pointer has moved past the drag threshold."""
        if self._drag_start is None:
            return False
        return (current - self._drag_start).manhattanLength() > _DRAG_THRESHOLD

    def _start_drag(self) -> None:
        """Begin a Qt drag carrying this card's task id."""
        drag = QDrag(self)
        drag.setMimeData(self.make_mime_data())
        drag.exec(Qt.DropAction.MoveAction)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt naming
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt naming
        if event.buttons() & Qt.MouseButton.LeftButton and self._should_start_drag(
            event.position().toPoint()
        ):
            self._start_drag()
        super().mouseMoveEvent(event)
