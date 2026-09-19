"""A Kanban column widget: a titled lane containing task cards.

The column is a drop target for dragged cards (F-01): it accepts drops that
carry the Kanban task MIME type and emits :attr:`task_moved` with the dropped
task id, this column's id, and the insertion index.
"""

from __future__ import annotations

from datetime import date

from PySide6.QtCore import QMimeData, QPoint, Signal
from PySide6.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent, QMouseEvent
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from kanban.models import Priority
from kanban.ui.card_widget import KANBAN_TASK_MIME, CardWidget, LabelSpec


class _DoubleClickableLabel(QLabel):
    """A label that emits a signal when double-clicked (used for rename)."""

    double_clicked = Signal()

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt naming
        self.double_clicked.emit()
        super().mouseDoubleClickEvent(event)


class ColumnWidget(QFrame):
    """A single board column with its cards and an inline add-task field.

    The header exposes rename (double-click the title), move left/right, and
    delete controls that emit :attr:`column_renamed`, :attr:`column_moved`,
    and :attr:`column_deleted` respectively.
    """

    task_added = Signal(int, str)  # column_id, title
    task_deleted = Signal(int)  # task_id
    task_moved = Signal(int, int, int)  # task_id, target_column_id, index
    column_renamed = Signal(int, str)  # column_id, new_title
    column_moved = Signal(int, int)  # column_id, new_index
    column_deleted = Signal(int)  # column_id
    label_assign_requested = Signal(int, int)  # task_id, label_id
    label_unassign_requested = Signal(int, int)  # task_id, label_id

    def __init__(
        self,
        column_id: int,
        title: str,
        tasks: list[tuple[int, str, Priority, date | None, list[LabelSpec]]],
        index: int = 0,
        board_labels: list[LabelSpec] | None = None,
    ) -> None:
        super().__init__()
        self._column_id = column_id
        self._index = index
        self._board_labels = list(board_labels or [])
        self.setObjectName("column")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setAcceptDrops(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        header = QHBoxLayout()
        self._title_label = _DoubleClickableLabel(title)
        self._title_label.setObjectName("columnTitle")
        self._title_label.double_clicked.connect(self._start_rename)
        header.addWidget(self._title_label)

        self._rename_edit = QLineEdit()
        self._rename_edit.setAccessibleName("Rename column")
        self._rename_edit.setFixedWidth(160)
        self._rename_edit.hide()
        self._rename_edit.returnPressed.connect(self._commit_rename)
        self._rename_edit.editingFinished.connect(self._commit_rename)
        header.addWidget(self._rename_edit)

        header.addStretch(1)

        left_button = QPushButton("◀")
        left_button.setFixedWidth(24)
        left_button.setAccessibleName("Move column left")
        left_button.clicked.connect(self._move_left)
        header.addWidget(left_button)

        right_button = QPushButton("▶")
        right_button.setFixedWidth(24)
        right_button.setAccessibleName("Move column right")
        right_button.clicked.connect(self._move_right)
        header.addWidget(right_button)

        delete_button = QPushButton("✕")
        delete_button.setFixedWidth(24)
        delete_button.setAccessibleName("Delete column")
        delete_button.clicked.connect(self._delete_column)
        header.addWidget(delete_button)

        layout.addLayout(header)

        self._card_layout = QVBoxLayout()
        self._card_layout.setSpacing(6)
        for task_id, task_title, priority, due_date, labels in tasks:
            card = CardWidget(
                task_id,
                task_title,
                priority,
                due_date,
                labels=labels,
                board_labels=self._board_labels,
            )
            card.delete_requested.connect(self.task_deleted)
            card.label_assign_requested.connect(self.label_assign_requested)
            card.label_unassign_requested.connect(self.label_unassign_requested)
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

    @property
    def index(self) -> int:
        """The column's position within its board (0-based)."""
        return self._index

    # -- Column controls --------------------------------------------------
    def _start_rename(self) -> None:
        """Swap the title label for an inline edit field."""
        if not self._rename_edit.isHidden():
            return
        self._rename_edit.setText(self._title_label.text())
        self._title_label.hide()
        self._rename_edit.show()
        self._rename_edit.setFocus()
        self._rename_edit.selectAll()

    def _commit_rename(self) -> None:
        """Commit an inline rename, emitting a signal if the title changed."""
        if self._rename_edit.isHidden():
            return
        new_title = self._rename_edit.text().strip()
        self._rename_edit.hide()
        self._title_label.show()
        if new_title:
            self._title_label.setText(new_title)
            self.column_renamed.emit(self._column_id, new_title)

    def _move_left(self) -> None:
        """Request moving this column one position to the left."""
        self.column_moved.emit(self._column_id, self._index - 1)

    def _move_right(self) -> None:
        """Request moving this column one position to the right."""
        self.column_moved.emit(self._column_id, self._index + 1)

    def _delete_column(self) -> None:
        """Request deleting this column."""
        self.column_deleted.emit(self._column_id)

    def _submit_new_task(self) -> None:
        """Emit a new-task request if the inline field is non-empty."""
        title = self._add_edit.text().strip()
        if not title:
            return
        self.task_added.emit(self._column_id, title)
        self._add_edit.clear()

    def focus_add_task(self) -> None:
        """Give keyboard focus to the inline add-task field."""
        self._add_edit.setFocus()

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
