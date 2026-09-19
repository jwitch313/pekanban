"""A Kanban column widget: a titled lane containing task cards."""

from __future__ import annotations

from datetime import date

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from kanban.models import Priority
from kanban.ui.card_widget import CardWidget


class ColumnWidget(QFrame):
    """A single board column with its cards and an inline add-task field."""

    task_added = Signal(int, str)  # column_id, title
    task_deleted = Signal(int)  # task_id

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
