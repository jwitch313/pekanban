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
    QFontMetrics,
    QIcon,
    QMouseEvent,
    QPainter,
    QPalette,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import (
    QCheckBox,
    QDateEdit,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from kanban.models import Priority
from kanban.ui import icons
from kanban.ui.flow_layout import FlowLayout

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


class _DoubleClickableLabel(QLabel):
    """A label that emits a signal when double-clicked (used for inline rename)."""

    double_clicked = Signal()

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt naming
        self.double_clicked.emit()
        super().mouseDoubleClickEvent(event)


def make_drop_shadow() -> QGraphicsDropShadowEffect:
    """Build a light drop shadow for cards and columns.

    A soft, low-opacity shadow with a small downward offset gives depth without
    overwhelming the flat, modern look of the board.
    """
    effect = QGraphicsDropShadowEffect()
    effect.setBlurRadius(18)
    effect.setOffset(0, 2)
    shadow = QColor(0, 0, 0)
    shadow.setAlpha(70)
    effect.setColor(shadow)
    return effect


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
    description_changed = Signal(int, object)  # task_id, str | None
    title_changed = Signal(int, str)  # task_id, new_title
    archive_requested = Signal(int)  # task_id
    restore_requested = Signal(int)  # task_id

    def __init__(
        self,
        task_id: int,
        title: str,
        priority: Priority,
        due_date: date | None,
        labels: list[LabelSpec] | None = None,
        board_labels: list[LabelSpec] | None = None,
        subtasks: list[tuple[int, str, bool]] | None = None,
        description: str | None = None,
        archived: bool = False,
    ) -> None:
        super().__init__()
        self._task_id = task_id
        self._priority = priority
        self._due_date = due_date
        self._description = description
        self._archived = archived
        self._board_labels = list(board_labels or [])
        self._drag_start: QPoint | None = None
        self._overdue = False
        self._label_chips: list[LabelChip] = []
        self._subtask_rows: list[QCheckBox] = []
        self._due_popup: QWidget | None = None
        self._notes_popup: QWidget | None = None
        self.setObjectName("card")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        # Keep a Python reference: Qt does not own the effect, so without this
        # it would be garbage-collected and the shadow would vanish.
        self._shadow = make_drop_shadow()
        self.setGraphicsEffect(self._shadow)
        self.setAccessibleName(f"Task: {title}")

        self._layout = QVBoxLayout(self)
        layout = self._layout
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        self._title_label = _DoubleClickableLabel(title)
        self._title_label.setObjectName("taskTitle")
        self._title_label.setWordWrap(True)
        self._title_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self._title_label.double_clicked.connect(self._start_title_edit)
        title_font = self._title_label.font()
        title_font.setBold(True)
        title_font.setPointSize(max(title_font.pointSize(), 11))
        self._title_label.setFont(title_font)
        layout.addWidget(self._title_label)

        self._title_edit = QLineEdit()
        self._title_edit.setAccessibleName("Edit task title")
        self._title_edit.setMaxLength(128)
        self._title_edit.returnPressed.connect(self._commit_title_edit)
        self._title_edit.editingFinished.connect(self._commit_title_edit)
        self._title_edit.hide()

        if description is not None and description.strip():
            description_label = QLabel(description)
            description_label.setObjectName("taskDescription")
            description_label.setWordWrap(True)
            description_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            description_font = description_label.font()
            description_font.setBold(False)
            description_font.setPointSize(9)
            description_label.setFont(description_font)
            layout.addWidget(description_label)

        meta_row = QHBoxLayout()
        meta_row.setSpacing(6)
        badge = QLabel(priority.value.capitalize())
        badge.setObjectName("priorityBadge")
        badge.setStyleSheet(f"color: {PRIORITY_COLORS[priority]}; font-weight: bold;")
        meta_row.addWidget(badge)

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

        self._notes_button = QPushButton()
        self._notes_button.setObjectName("notesButton")
        self._notes_button.setIcon(icons.icon("pencil"))
        self._notes_button.setFixedWidth(24)
        self._notes_button.setAccessibleName("Edit description")
        self._notes_button.setToolTip("Edit description")
        self._notes_button.clicked.connect(self._show_notes_popup)
        meta_row.addWidget(self._notes_button)

        if self._archived:
            restore_button = QPushButton()
            restore_button.setObjectName("restoreButton")
            restore_button.setIcon(icons.icon("restore"))
            restore_button.setFixedWidth(24)
            restore_button.setAccessibleName("Restore task")
            restore_button.setToolTip("Restore task")
            restore_button.clicked.connect(lambda: self.restore_requested.emit(self._task_id))
            meta_row.addWidget(restore_button)
        else:
            archive_button = QPushButton()
            archive_button.setObjectName("archiveButton")
            archive_button.setIcon(icons.icon("archive"))
            archive_button.setFixedWidth(24)
            archive_button.setAccessibleName("Archive task")
            archive_button.setToolTip("Archive task")
            archive_button.clicked.connect(lambda: self.archive_requested.emit(self._task_id))
            meta_row.addWidget(archive_button)

        delete_button = QPushButton()
        delete_button.setIcon(icons.icon("trash"))
        delete_button.setFixedWidth(24)
        delete_button.setAccessibleName("Delete task")
        delete_button.setToolTip("Delete task")
        delete_button.clicked.connect(lambda: self.delete_requested.emit(self._task_id))
        meta_row.addWidget(delete_button)

        layout.addLayout(meta_row)

        if due_date is not None:
            due_label = QLabel(f"Due {due_date.isoformat()}")
            due_label.setObjectName("dueDate")
            if due_date < date.today():
                self._overdue = True
                due_label.setStyleSheet(f"color: {OVERDUE_COLOR}; font-weight: bold;")
            layout.addWidget(due_label)

        # A flow layout so label chips wrap onto new lines when the card is
        # narrower than their combined width (instead of clipping/overflowing).
        self._label_row = FlowLayout()
        self._label_row.setHorizontalSpacing(4)
        self._label_row.setVerticalSpacing(4)
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
    def archived(self) -> bool:
        """Whether this card represents an archived task."""
        return self._archived

    def _can_drag(self) -> bool:
        """Archived cards are not draggable (no drop target in archive view)."""
        return not self._archived

    @property
    def label_ids(self) -> list[int]:
        """The ids of the labels currently shown as chips on this card."""
        return [chip.label_id for chip in self._label_chips]

    # -- Title ------------------------------------------------------------
    def _start_title_edit(self) -> None:
        """Swap the title label for an inline edit field."""
        if not self._title_edit.isHidden():
            return
        self._title_edit.setText(self._title_label.text())
        self._title_label.hide()
        self._layout.insertWidget(self._title_label_index() + 1, self._title_edit)
        self._title_edit.show()
        self._title_edit.setFocus()
        self._title_edit.selectAll()

    def _commit_title_edit(self) -> None:
        """Commit an inline title edit, emitting a signal if it changed."""
        if self._title_edit.isHidden():
            return
        new_title = self._title_edit.text().strip()
        self._layout.removeWidget(self._title_edit)
        self._title_edit.hide()
        self._title_label.show()
        if new_title and new_title != self._title_label.text():
            self._title_label.setText(new_title)
            self.title_changed.emit(self._task_id, new_title)

    def _title_label_index(self) -> int:
        """Return the index of the title label within the card layout."""
        for i in range(self._layout.count()):
            item = self._layout.itemAt(i)
            if item is not None and item.widget() is self._title_label:
                return i
        return 0

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
        """Pop up a small date picker anchored to the card.

        The popup is a top-level window retained on ``self`` so it is not
        garbage-collected (and closed) before the user can interact with it.
        It is deliberately *not* parented to the card: the card's stylesheet
        rule ``#card QWidget { background: transparent }`` would otherwise
        make the popup and its calendar transparent. Clicking the button
        again toggles the popup closed.
        """
        from PySide6.QtCore import QDate

        if self._due_popup is not None:
            if self._due_popup.isVisible():
                self._due_popup.hide()
                return
            self._due_popup.deleteLater()
            self._due_popup = None

        popup = QWidget()
        popup.setWindowFlags(Qt.WindowType.Popup)
        self.destroyed.connect(popup.deleteLater)
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
        else:
            self._due_picker.setDate(QDate.currentDate())
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

        self._due_popup = popup
        popup.show()
        popup.move(self.mapToGlobal(self.rect().bottomLeft()))

    def _on_set_due(self) -> None:
        """Emit the picked due date and close the picker."""
        self.due_date_changed.emit(self._task_id, self._due_picker.date().toPython())
        self._close_due_picker()

    def _on_clear_due(self) -> None:
        """Request clearing the due date and close the picker."""
        self.due_date_changed.emit(self._task_id, None)
        self._close_due_picker()

    def _close_due_picker(self) -> None:
        """Hide the due-date popup if it is open."""
        if self._due_popup is not None:
            self._due_popup.hide()

    # -- Description ------------------------------------------------------
    def _show_notes_popup(self) -> None:
        """Pop up a small description editor anchored to the card.

        Mirrors the due-date picker: a top-level window retained on ``self``
        so it is not garbage-collected before the user can interact with it.
        It is deliberately *not* parented to the card, whose stylesheet makes
        child widgets transparent. Clicking the button again toggles it closed.
        """
        if self._notes_popup is not None:
            if self._notes_popup.isVisible():
                self._notes_popup.hide()
                return
            self._notes_popup.deleteLater()
            self._notes_popup = None

        popup = QWidget()
        popup.setWindowFlags(Qt.WindowType.Popup)
        self.destroyed.connect(popup.deleteLater)
        layout = QVBoxLayout(popup)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        self._notes_edit = QTextEdit()
        self._notes_edit.setPlaceholderText("Add a description…")
        self._notes_edit.setFixedHeight(120)
        if self._description:
            self._notes_edit.setPlainText(self._description)
        layout.addWidget(self._notes_edit)

        button_row = QHBoxLayout()
        set_button = QPushButton("Set")
        set_button.setIcon(icons.icon("pencil"))
        set_button.clicked.connect(self._on_set_description)
        clear_button = QPushButton("Clear")
        clear_button.setIcon(icons.icon("clear"))
        clear_button.clicked.connect(self._on_clear_description)
        button_row.addWidget(set_button)
        button_row.addWidget(clear_button)
        layout.addLayout(button_row)

        self._notes_popup = popup
        popup.show()
        popup.move(self.mapToGlobal(self.rect().bottomLeft()))

    def _on_set_description(self) -> None:
        """Emit the edited description and close the popup."""
        text = self._notes_edit.toPlainText().strip()
        self.description_changed.emit(self._task_id, text if text else None)
        self._close_notes_popup()

    def _on_clear_description(self) -> None:
        """Request clearing the description and close the popup."""
        self.description_changed.emit(self._task_id, None)
        self._close_notes_popup()

    def _close_notes_popup(self) -> None:
        """Hide the notes popup if it is open."""
        if self._notes_popup is not None:
            self._notes_popup.hide()

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

    def _elide_drag_title(self, title: str) -> str:
        """Return ``title`` truncated to 32 characters with an ellipsis if needed."""
        if len(title) <= 32:
            return title
        return title[:31] + "\u2026"

    def _build_drag_pixmap(self) -> QPixmap:
        """Render a small preview of this card to use as the drag image.

        The preview shows the (elided) task title on a themed rounded panel so
        the user sees a miniature of the card while dragging, rather than the
        default plus-sign cursor.
        """
        title = self._elide_drag_title(self._title_label.text())
        font = self.font()
        font.setBold(True)
        metrics = QFontMetrics(font)
        text_width = metrics.horizontalAdvance(title)
        padding = 12
        width = min(max(text_width + padding * 2, 96), 240)
        height = metrics.height() + padding * 2

        pixmap = QPixmap(width, height)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        palette = self.palette()
        background = palette.color(QPalette.ColorRole.Window)
        text_color = palette.color(QPalette.ColorRole.WindowText)
        border = QColor(background)
        border.setAlpha(160)

        painter.setPen(QPen(border, 1))
        painter.setBrush(QBrush(background))
        painter.drawRoundedRect(0, 0, width - 1, height - 1, 8, 8)

        painter.setPen(text_color)
        painter.setFont(font)
        painter.drawText(0, 0, width, height, int(Qt.AlignmentFlag.AlignCenter), title)
        painter.end()
        return pixmap

    def _start_drag(self) -> None:
        """Begin a Qt drag carrying this card's task id and a mini preview."""
        drag = QDrag(self)
        drag.setMimeData(self.make_mime_data())
        drag.setPixmap(self._build_drag_pixmap())
        drag.setHotSpot(QPoint(0, 0))
        drag.exec(Qt.DropAction.MoveAction)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt naming
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt naming
        if (
            self._can_drag()
            and event.buttons() & Qt.MouseButton.LeftButton
            and self._should_start_drag(event.position().toPoint())
        ):
            self._start_drag()
        super().mouseMoveEvent(event)
