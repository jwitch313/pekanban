"""A single draggable task card widget.

The card is presentational only: it displays a task's title, priority badge,
due date, and assigned label chips, and emits signals when the user requests
an action. It also supports being dragged out of its column (F-01), highlights
overdue due dates (F-04), and lets the user assign or remove labels (F-11).
"""

from __future__ import annotations

from datetime import date

from PySide6.QtCore import QMimeData, QPoint, Qt, Signal
from PySide6.QtGui import (
    QAction,
    QActionGroup,
    QBrush,
    QColor,
    QDrag,
    QIcon,
    QMouseEvent,
    QPainter,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import (
    QCheckBox,
    QDateEdit,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from kanban.models import Priority
from kanban.ui import icons

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

#: Fallback chip color when a label has no explicit color.
DEFAULT_LABEL_COLOR = "#888888"

#: A label described for display: ``(id, name, color)``.
LabelSpec = tuple[int, str, str | None]


class LabelChip(QPushButton):
    """A small colored chip representing a label assigned to a card.

    Clicking the chip requests removal of that label from the card.
    """

    remove_requested = Signal(int)  # label_id

    def __init__(self, label_id: int, name: str, color: str | None) -> None:
        super().__init__(name)
        self._label_id = label_id
        self.setFlat(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAccessibleName(f"Label: {name}")
        self.setToolTip(f"Remove label {name}")
        self.setIcon(self._swatch_icon(color))
        self.setStyleSheet(self._chip_style(color))
        self.clicked.connect(lambda: self.remove_requested.emit(self._label_id))

    @property
    def label_id(self) -> int:
        """The database id of the label this chip represents."""
        return self._label_id

    @staticmethod
    def _swatch_icon(color: str | None) -> QIcon:
        """Build a small filled swatch icon in the label's color."""
        pixmap = QPixmap(12, 12)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor("#ffffff"), 1))
        painter.setBrush(QBrush(QColor(color if color else DEFAULT_LABEL_COLOR)))
        painter.drawEllipse(1, 1, 10, 10)
        painter.end()
        return QIcon(pixmap)

    @staticmethod
    def _chip_style(color: str | None) -> str:
        """Build a rounded, colored chip stylesheet for the given label color."""
        background = color if color else DEFAULT_LABEL_COLOR
        return (
            f"QPushButton {{ background-color: {background}; color: #ffffff; border: none;"
            " border-radius: 8px; padding: 1px 8px; font-size: 11px; }}"
            "QPushButton:hover { background-color: rgba(0, 0, 0, 60); }"
        )


class CardWidget(QFrame):
    """A Kanban card representing a single task."""

    delete_requested = Signal(int)  # task_id
    label_assign_requested = Signal(int, int)  # task_id, label_id
    label_unassign_requested = Signal(int, int)  # task_id, label_id
    subtask_added = Signal(int, str)  # task_id, title
    subtask_toggled = Signal(int)  # subtask_id
    subtask_deleted = Signal(int)  # subtask_id
    priority_changed = Signal(int, object)  # task_id, Priority
    due_date_changed = Signal(int, object)  # task_id, date | None

    def __init__(
        self,
        task_id: int,
        title: str,
        priority: Priority,
        due_date: date | None,
        labels: list[LabelSpec] | None = None,
        board_labels: list[LabelSpec] | None = None,
        subtasks: list[tuple[int, str, bool]] | None = None,
    ) -> None:
        super().__init__()
        self._task_id = task_id
        self._priority = priority
        self._due_date = due_date
        self._board_labels = list(board_labels or [])
        self._drag_start: QPoint | None = None
        self._overdue = False
        self._label_chips: list[LabelChip] = []
        self._subtask_rows: list[QCheckBox] = []
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

        self._priority_button = QPushButton()
        self._priority_button.setIcon(icons.icon("flag"))
        self._priority_button.setFixedWidth(24)
        self._priority_button.setAccessibleName("Change priority")
        self._priority_button.setToolTip("Change priority")
        self._priority_button.clicked.connect(self._show_priority_menu)
        meta_row.addWidget(self._priority_button)

        self._due_button = QPushButton()
        self._due_button.setIcon(icons.icon("calendar"))
        self._due_button.setFixedWidth(24)
        self._due_button.setAccessibleName("Set due date")
        self._due_button.setToolTip("Set due date")
        self._due_button.clicked.connect(self._show_due_date_picker)
        meta_row.addWidget(self._due_button)

        delete_button = QPushButton()
        delete_button.setIcon(icons.icon("trash"))
        delete_button.setFixedWidth(24)
        delete_button.setAccessibleName("Delete task")
        delete_button.setToolTip("Delete task")
        delete_button.clicked.connect(lambda: self.delete_requested.emit(self._task_id))
        meta_row.addWidget(delete_button)

        layout.addLayout(meta_row)

        self._label_row = QHBoxLayout()
        self._label_row.setSpacing(4)
        for label_id, name, color in labels or []:
            chip = LabelChip(label_id, name, color)
            chip.remove_requested.connect(
                lambda lid: self.label_unassign_requested.emit(self._task_id, lid)
            )
            self._label_row.addWidget(chip)
            self._label_chips.append(chip)

        label_button = QPushButton()
        label_button.setIcon(icons.icon("tag"))
        label_button.setFixedWidth(24)
        label_button.setAccessibleName("Assign label")
        label_button.setToolTip("Assign a label")
        label_button.clicked.connect(self._show_label_menu)
        self._label_row.addWidget(label_button)
        self._label_row.addStretch(1)
        layout.addLayout(self._label_row)

        self._subtask_section = self._build_subtask_section(subtasks or [])
        layout.addWidget(self._subtask_section)

    @property
    def task_id(self) -> int:
        """The database id of the task this card represents."""
        return self._task_id

    @property
    def overdue(self) -> bool:
        """Whether the task's due date is in the past."""
        return self._overdue

    @property
    def label_ids(self) -> list[int]:
        """The ids of the labels currently shown as chips on this card."""
        return [chip.label_id for chip in self._label_chips]

    # -- Sub-tasks --------------------------------------------------------
    def _build_subtask_section(self, subtasks: list[tuple[int, str, bool]]) -> QWidget:
        """Build the sub-task list and inline add field for this card."""
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 2, 0, 0)
        layout.setSpacing(3)

        header = QLabel("Subtasks")
        header.setObjectName("subtaskHeader")
        layout.addWidget(header)

        for subtask_id, subtask_title, completed in subtasks:
            row = QHBoxLayout()
            row.setSpacing(4)
            checkbox = QCheckBox(subtask_title)
            checkbox.setChecked(completed)
            checkbox.toggled.connect(
                lambda _checked, sid=subtask_id: self.subtask_toggled.emit(sid)
            )
            row.addWidget(checkbox, 1)
            delete_button = QPushButton()
            delete_button.setIcon(icons.icon("trash"))
            delete_button.setFixedWidth(20)
            delete_button.setAccessibleName(f"Delete subtask: {subtask_title}")
            delete_button.setToolTip(f"Delete subtask: {subtask_title}")
            delete_button.clicked.connect(
                lambda _checked=False, sid=subtask_id: self.subtask_deleted.emit(sid)
            )
            row.addWidget(delete_button)
            layout.addLayout(row)
            self._subtask_rows.append(checkbox)

        add_row = QHBoxLayout()
        add_row.setSpacing(4)
        self._subtask_edit = QLineEdit()
        self._subtask_edit.setPlaceholderText("Add subtask…")
        self._subtask_edit.returnPressed.connect(self._submit_new_subtask)
        add_row.addWidget(self._subtask_edit, 1)
        add_button = QPushButton()
        add_button.setIcon(icons.icon("plus"))
        add_button.setFixedWidth(24)
        add_button.setAccessibleName("Add subtask")
        add_button.setToolTip("Add subtask")
        add_button.clicked.connect(self._submit_new_subtask)
        add_row.addWidget(add_button)
        layout.addLayout(add_row)
        return section

    def _submit_new_subtask(self) -> None:
        """Emit a new-subtask request if the field is non-empty."""
        title = self._subtask_edit.text().strip()
        if not title:
            return
        self.subtask_added.emit(self._task_id, title)
        self._subtask_edit.clear()

    # -- Priority ---------------------------------------------------------
    def _show_priority_menu(self) -> None:
        """Pop up the priority menu anchored to the card (no dropdown arrow)."""
        menu = self._build_priority_menu()
        menu.exec(self.mapToGlobal(self.rect().bottomLeft()))

    def _build_priority_menu(self) -> QMenu:
        """Build an exclusive menu of the four priority levels."""
        menu = QMenu(self)
        group = QActionGroup(self)
        group.setExclusive(True)

        self._priority_actions: dict[Priority, QAction] = {}
        for priority in Priority:
            action = QAction(priority.value.capitalize(), self)
            action.setCheckable(True)
            action.setChecked(priority is self._priority)
            group.addAction(action)
            menu.addAction(action)
            self._priority_actions[priority] = action
            action.triggered.connect(
                lambda _checked, p=priority: self.priority_changed.emit(self._task_id, p)
            )
        return menu

    # -- Due date ---------------------------------------------------------
    def _show_due_date_picker(self) -> None:
        """Pop up a small date picker anchored to the card."""
        from PySide6.QtCore import QDate

        popup = QWidget()
        popup.setWindowFlags(Qt.WindowType.Popup)
        layout = QVBoxLayout(popup)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        self._due_picker = QDateEdit()
        self._due_picker.setCalendarPopup(True)
        self._due_picker.setDisplayFormat("yyyy-MM-dd")
        if self._due_date is not None:
            self._due_picker.setDate(
                QDate(self._due_date.year, self._due_date.month, self._due_date.day)
            )
        layout.addWidget(self._due_picker)

        button_row = QHBoxLayout()
        set_button = QPushButton("Set")
        set_button.setIcon(icons.icon("calendar"))
        set_button.clicked.connect(self._on_set_due)
        clear_button = QPushButton("Clear")
        clear_button.setIcon(icons.icon("clear"))
        clear_button.clicked.connect(self._on_clear_due)
        button_row.addWidget(set_button)
        button_row.addWidget(clear_button)
        layout.addLayout(button_row)

        popup.show()
        popup.move(self.mapToGlobal(self.rect().bottomLeft()))

    def _on_set_due(self) -> None:
        """Emit the picked due date."""
        self.due_date_changed.emit(self._task_id, self._due_picker.date().toPython())

    def _on_clear_due(self) -> None:
        """Request clearing the due date."""
        self.due_date_changed.emit(self._task_id, None)

    # -- Labels -----------------------------------------------------------
    def _build_label_menu(self) -> QMenu:
        """Build a menu of the board's labels not yet assigned to this card."""
        menu = QMenu(self)
        assigned = set(self.label_ids)
        for label_id, name, _color in self._board_labels:
            if label_id in assigned:
                continue
            action = menu.addAction(name)
            action.triggered.connect(
                lambda _checked=False, lid=label_id: self.label_assign_requested.emit(
                    self._task_id, lid
                )
            )
        return menu

    def _show_label_menu(self) -> None:
        """Pop up the label-assignment menu anchored to the card."""
        menu = self._build_label_menu()
        menu.exec(self.mapToGlobal(self.rect().bottomLeft()))

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
