"""The board view: a horizontally scrollable set of columns."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from kanban.models import Board, Task
from kanban.ui.card_widget import CardWidget, LabelSpec
from kanban.ui.column_widget import ColumnWidget


class BoardView(QScrollArea):
    """Displays the columns and cards of the currently selected board."""

    column_renamed = Signal(int, str)  # column_id, new_title
    column_moved = Signal(int, int)  # column_id, new_index
    column_deleted = Signal(int)  # column_id
    task_added = Signal(int, str)  # column_id, title
    task_deleted = Signal(int)  # task_id
    task_moved = Signal(int, int, int)  # task_id, target_column_id, index
    label_assign_requested = Signal(int, int)  # task_id, label_id
    label_unassign_requested = Signal(int, int)  # task_id, label_id
    subtask_added = Signal(int, str)  # task_id, title
    subtask_toggled = Signal(int)  # subtask_id
    subtask_deleted = Signal(int)  # subtask_id
    priority_changed = Signal(int, object)  # task_id, Priority
    due_date_changed = Signal(int, object)  # task_id, date | None
    description_changed = Signal(int, object)  # task_id, str | None
    title_changed = Signal(int, str)  # task_id, new_title
    archive_requested = Signal(int)  # task_id
    restore_requested = Signal(int)  # task_id

    def __init__(self) -> None:
        super().__init__()
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        container.setObjectName("boardView")
        self._column_layout = QHBoxLayout(container)
        self._column_layout.setContentsMargins(12, 12, 12, 12)
        self._column_layout.setSpacing(12)
        self._column_layout.addStretch(1)
        self.setWidget(container)

    def clear_columns(self) -> None:
        """Remove all widgets (columns and the archived view) from the view."""
        for i in range(self._column_layout.count() - 1, -1, -1):
            item = self._column_layout.itemAt(i)
            if item is None:
                continue
            widget = item.widget()
            if widget is not None:
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
        column.label_assign_requested.connect(self.label_assign_requested)
        column.label_unassign_requested.connect(self.label_unassign_requested)
        column.subtask_added.connect(self.subtask_added)
        column.subtask_toggled.connect(self.subtask_toggled)
        column.subtask_deleted.connect(self.subtask_deleted)
        column.priority_changed.connect(self.priority_changed)
        column.due_date_changed.connect(self.due_date_changed)
        column.description_changed.connect(self.description_changed)
        column.title_changed.connect(self.title_changed)
        self._column_layout.insertWidget(self._column_layout.count() - 1, column)

    def load_board(self, board: Board, visible_task_ids: set[int] | None = None) -> None:
        """Rebuild the view from a fully-loaded board object.

        When ``visible_task_ids`` is provided, only tasks whose id is in the
        set are rendered (used for search & filtering). ``None`` shows all.
        """
        self.clear_columns()
        board_labels = [(label.id, label.name, label.color) for label in board.labels]
        for index, column in enumerate(board.columns):
            tasks = []
            for task in column.tasks:
                if task.archived:
                    continue
                if visible_task_ids is not None and task.id not in visible_task_ids:
                    continue
                labels = [(label.id, label.name, label.color) for label in task.labels]
                subtasks = [(sub.id, sub.title, sub.completed) for sub in task.subtasks]
                tasks.append(
                    (
                        task.id,
                        task.title,
                        task.priority,
                        task.due_date,
                        labels,
                        subtasks,
                        task.description,
                    )
                )
            self.add_column_widget(
                ColumnWidget(column.id, column.title, tasks, index, board_labels=board_labels)
            )

    def load_archived(
        self,
        tasks: list[Task],
        board_labels: list[LabelSpec] | None = None,
    ) -> None:
        """Render archived tasks in a single full-width widget.

        The archived view replaces the normal columns: one large widget fills
        the display area and lists each archived task as a full-width card.
        """
        self.clear_columns()
        board_labels = list(board_labels or [])

        container = QWidget()
        container.setObjectName("archivedView")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        if not tasks:
            placeholder = QLabel("No archived tasks.")
            placeholder.setObjectName("archivedEmpty")
            layout.addWidget(placeholder)
            layout.addStretch(1)
            self._column_layout.insertWidget(self._column_layout.count() - 1, container)
            return

        for task in tasks:
            labels = [(label.id, label.name, label.color) for label in task.labels]
            subtasks = [(sub.id, sub.title, sub.completed) for sub in task.subtasks]
            card = CardWidget(
                task.id,
                task.title,
                task.priority,
                task.due_date,
                labels=labels,
                board_labels=board_labels,
                subtasks=subtasks,
                description=task.description,
                archived=True,
            )
            card.archive_requested.connect(self.archive_requested)
            card.restore_requested.connect(self.restore_requested)
            card.delete_requested.connect(self.task_deleted)
            card.label_assign_requested.connect(self.label_assign_requested)
            card.label_unassign_requested.connect(self.label_unassign_requested)
            card.subtask_added.connect(self.subtask_added)
            card.subtask_toggled.connect(self.subtask_toggled)
            card.subtask_deleted.connect(self.subtask_deleted)
            card.priority_changed.connect(self.priority_changed)
            card.due_date_changed.connect(self.due_date_changed)
            card.description_changed.connect(self.description_changed)
            card.title_changed.connect(self.title_changed)
            layout.addWidget(card)
        layout.addStretch(1)
        self._column_layout.insertWidget(self._column_layout.count() - 1, container)

    def focus_first_task_input(self) -> bool:
        """Focus the first column's add-task field. Returns True if one exists."""
        for i in range(self._column_layout.count()):
            item = self._column_layout.itemAt(i)
            widget = item.widget() if item is not None else None
            if isinstance(widget, ColumnWidget):
                widget.focus_add_task()
                return True
        return False
