"""The board view: a horizontally scrollable set of columns."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from kanban.models import Board
from kanban.ui.column_widget import ColumnWidget


class BoardView(QScrollArea):
    """Displays the columns and cards of the currently selected board."""

    column_added = Signal(str)  # title
    column_renamed = Signal(int, str)  # column_id, new_title
    column_moved = Signal(int, int)  # column_id, new_index
    column_deleted = Signal(int)  # column_id
    task_added = Signal(int, str)  # column_id, title
    task_deleted = Signal(int)  # task_id
    task_moved = Signal(int, int, int)  # task_id, target_column_id, index

    def __init__(self) -> None:
        super().__init__()
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        self._column_layout = QHBoxLayout(container)
        self._column_layout.setContentsMargins(12, 12, 12, 12)
        self._column_layout.setSpacing(12)
        self._column_layout.addStretch(1)
        self.setWidget(container)

        self._add_column_row = self._build_add_column_row()
        self._column_layout.insertWidget(0, self._add_column_row)

    def _build_add_column_row(self) -> QWidget:
        """Build the inline 'add column' control shown before the columns."""
        row = QWidget()
        layout = QVBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        edit = QLineEdit()
        edit.setPlaceholderText("Add a column…")
        edit.returnPressed.connect(self._submit_new_column)
        layout.addWidget(edit)
        button = QPushButton("+ Add column")
        button.clicked.connect(self._submit_new_column)
        layout.addWidget(button)
        self._column_edit = edit
        return row

    def _submit_new_column(self) -> None:
        """Emit a new-column request if the field is non-empty."""
        title = self._column_edit.text().strip()
        if not title:
            return
        self.column_added.emit(title)
        self._column_edit.clear()

    def clear_columns(self) -> None:
        """Remove all column widgets from the view, keeping the add-column row."""
        for i in range(self._column_layout.count() - 1, -1, -1):
            item = self._column_layout.itemAt(i)
            if item is None:
                continue
            widget = item.widget()
            if isinstance(widget, ColumnWidget):
                self._column_layout.takeAt(i)
                widget.setParent(None)
                widget.deleteLater()

    def add_column_widget(self, column: ColumnWidget) -> None:
        """Insert a column widget before the trailing stretch."""
        column.task_added.connect(self.task_added)
        column.task_deleted.connect(self.task_deleted)
        column.task_moved.connect(self.task_moved)
        column.column_renamed.connect(self.column_renamed)
        column.column_moved.connect(self.column_moved)
        column.column_deleted.connect(self.column_deleted)
        self._column_layout.insertWidget(self._column_layout.count() - 1, column)

    def load_board(self, board: Board) -> None:
        """Rebuild the view from a fully-loaded board object."""
        self.clear_columns()
        for index, column in enumerate(board.columns):
            tasks = [(task.id, task.title, task.priority, task.due_date) for task in column.tasks]
            self.add_column_widget(ColumnWidget(column.id, column.title, tasks, index))
