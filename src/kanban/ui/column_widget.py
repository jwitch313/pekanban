"""A Kanban column widget: a titled lane containing task cards.

The column is a drop target for dragged cards (F-01): it accepts drops that
carry the Kanban task MIME type and emits :attr:`task_moved` with the dropped
task id, this column's id, and the insertion index.
"""

from __future__ import annotations

from datetime import date

from PySide6.QtCore import QMimeData, QPoint, Signal
from PySide6.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from kanban.models import Priority
from kanban.ui.card_widget import KANBAN_TASK_MIME, CardWidget


class ColumnWidget(QFrame):
    """A single board column with its cards and an inline add-task field."""

    task_added = Signal(int, str)  # column_id, title
    task_deleted = Signal(int)  # task_id
    task_moved = Signal(int, int, int)  # task_id, target_column_id, index

    def __init__(
        self,
        column_id: int,
        title: str,
        tasks: list[tuple[int, str, Priority, date | None]],
    ) -> None:
        super().__init__()
        self._column_id = column_id
        self.setObjectName("column")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setAcceptDrops(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        header = QHBoxLayout()
        title_label = QLabel(title)
        title_label.setObjectName("columnTitle")
        header.addWidget(title_label)
        header.addStretch(1)
        layout.addLayout(header)

        self._card_layout = QVBoxLayout()
        self._card_layout.setSpacing(6)
        for task_id, task_title, priority, due_date in tasks:
            card = CardWidget(task_id, task_title, priority, due_date)
            card.delete_requested.connect(self.task_deleted)
            self._card_layout.addWidget(card)
        layout.addLayout(self._card_layout)

        add_row = QHBoxLayout()
        self._add_edit = QLineEdit()
        self._add_edit.setPlaceholderText("Add a task…")
        self._add_edit.returnPressed.connect(self._submit_new_task)
        add_row.addWidget(self._add_edit)
        add_button = QPushButton("+")
        add_button.setFixedWidth(28)
        add_button.setAccessibleName("Add task")
        add_button.clicked.connect(self._submit_new_task)
        add_row.addWidget(add_button)
        layout.addLayout(add_row)

    @property
    def column_id(self) -> int:
        """The database id of this column."""
        return self._column_id

    def _submit_new_task(self) -> None:
        """Emit a new-task request if the inline field is non-empty."""
        title = self._add_edit.text().strip()
        if not title:
            return
        self.task_added.emit(self._column_id, title)
        self._add_edit.clear()

    # -- Drop target ------------------------------------------------------
    def _drop_index_at(self, pos: QPoint) -> int:
        """Return the card index a drop at ``pos`` (local coords) should insert at.

        The index is the number of cards whose vertical center is above the
        drop point, clamped to ``[0, card_count]``.
        """
        index = 0
        for i in range(self._card_layout.count()):
            item = self._card_layout.itemAt(i)
            if item is None:
                continue
            widget = item.widget()
            if not isinstance(widget, CardWidget):
                continue
            center = widget.mapTo(self, widget.rect().center())
            if pos.y() > center.y():
                index += 1
        return index

    def _is_kanban_drop(self, mime_data: QMimeData) -> bool:
        """Return ``True`` if the MIME data carries a Kanban task id."""
        return bool(mime_data.hasFormat(KANBAN_TASK_MIME))

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802 - Qt naming
        if self._is_kanban_drop(event.mimeData()):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:  # noqa: N802 - Qt naming
        if self._is_kanban_drop(event.mimeData()):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802 - Qt naming
        if not self._is_kanban_drop(event.mimeData()):
            event.ignore()
            return
        raw = event.mimeData().data(KANBAN_TASK_MIME)
        try:
            task_id = int(bytes(raw.data()).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            event.ignore()
            return
        index = self._drop_index_at(event.position().toPoint())
        event.acceptProposedAction()
        self.task_moved.emit(task_id, self._column_id, index)
