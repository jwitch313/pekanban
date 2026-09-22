"""A search & filter bar for the current board.

The bar is presentational only: it collects a free-text query, a priority, a
column, a label, and an optional due-date range, and emits
:attr:`filters_changed` with a dictionary of the active filters. The
:class:`~kanban.main_window.MainWindow` routes that to
:meth:`TaskService.search_tasks` and re-renders the board with only the
matching cards.
"""

from __future__ import annotations

from datetime import date

from PySide6.QtCore import QDate, Qt, Signal
from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtWidgets import (
    QCalendarWidget,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLineEdit,
    QMenu,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from kanban.models import Priority
from kanban.ui import icons

#: A dictionary of active search/filter criteria.
Filters = dict[str, object]


class SearchBar(QFrame):
    """Collects search/filter criteria and emits them as a dictionary."""

    filters_changed = Signal(dict)
    theme_selected = Signal(str)
    view_archive_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("searchBar")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        self._query = QLineEdit()
        self._query.setPlaceholderText("Search tasks…")
        self._query.setAccessibleName("Search query")
        self._query.textChanged.connect(self._emit_filters)
        self._bound_query_width()
        layout.addWidget(self._query)

        self._priority = QComboBox()
        self._priority.setAccessibleName("Priority filter")
        self._priority.addItem("Any priority", None)
        for priority in Priority:
            self._priority.addItem(priority.value.capitalize(), priority)
        self._priority.currentIndexChanged.connect(self._emit_filters)
        layout.addWidget(self._priority)

        self._column = QComboBox()
        self._column.setAccessibleName("Column filter")
        self._column.addItem("Any column", None)
        self._column.currentIndexChanged.connect(self._emit_filters)
        layout.addWidget(self._column)

        self._label = QComboBox()
        self._label.setAccessibleName("Label filter")
        self._label.addItem("Any label", None)
        self._label.currentIndexChanged.connect(self._emit_filters)
        layout.addWidget(self._label)

        # Each due-date field is a plain, typeable text box paired with a
        # small calendar button that pops up a QCalendarWidget. A field only
        # contributes to the filter while it holds a parseable yyyy-MM-dd
        # date, so no separate active flags are needed.
        self._due_after = QLineEdit()
        self._due_after.setPlaceholderText("yyyy-MM-dd")
        self._due_after.setAccessibleName("Due from")
        self._due_after.setFixedWidth(100)
        self._due_after.textChanged.connect(self._emit_filters)
        layout.addWidget(self._due_after)

        self._due_after_calendar = QPushButton()
        self._due_after_calendar.setIcon(icons.icon("calendar"))
        self._due_after_calendar.setAccessibleName("Due from calendar")
        self._due_after_calendar.setToolTip("Pick due-from date")
        self._due_after_calendar.clicked.connect(
            lambda: self._show_due_calendar(self._due_after_calendar, self._due_after)
        )
        layout.addWidget(self._due_after_calendar)

        self._due_before = QLineEdit()
        self._due_before.setPlaceholderText("yyyy-MM-dd")
        self._due_before.setAccessibleName("Due until")
        self._due_before.setFixedWidth(100)
        self._due_before.textChanged.connect(self._emit_filters)
        layout.addWidget(self._due_before)

        self._due_before_calendar = QPushButton()
        self._due_before_calendar.setIcon(icons.icon("calendar"))
        self._due_before_calendar.setAccessibleName("Due until calendar")
        self._due_before_calendar.setToolTip("Pick due-until date")
        self._due_before_calendar.clicked.connect(
            lambda: self._show_due_calendar(self._due_before_calendar, self._due_before)
        )
        layout.addWidget(self._due_before_calendar)

        self._due_calendar_popup: QWidget | None = None
        self._due_calendar: QCalendarWidget | None = None
        self._calendar_target: QLineEdit | None = None

        clear_button = QPushButton("Clear")
        clear_button.setIcon(icons.icon("clear"))
        clear_button.setAccessibleName("Clear filters")
        clear_button.setToolTip("Clear filters")
        clear_button.clicked.connect(self.clear)
        layout.addWidget(clear_button)

        self._theme_button = QPushButton()
        self._theme_button.setIcon(icons.icon("monitor"))
        self._theme_button.setAccessibleName("Theme")
        self._theme_button.setToolTip("Theme")
        self._theme_button.setMenu(self._build_theme_menu())

        self._archive_button = QPushButton()
        self._archive_button.setObjectName("viewArchiveButton")
        self._archive_button.setIcon(icons.icon("archive"))
        self._archive_button.setAccessibleName("View archive")
        self._archive_button.setToolTip("View archived tasks")
        self._archive_button.clicked.connect(self.view_archive_requested.emit)

        # Push the archive + theme buttons to the far right; the search box and
        # filter controls stay left-justified with the extra space absorbed here.
        # The archive button sits to the left of the theme button so the two
        # stay grouped on the right edge.
        layout.addStretch(1)
        layout.addWidget(self._archive_button)
        layout.addWidget(self._theme_button)

    def set_viewing_archive(self, viewing: bool) -> None:
        """Reflect whether the archive view is active on the archive button."""
        if viewing:
            self._archive_button.setToolTip("Back to board")
        else:
            self._archive_button.setToolTip("View archived tasks")

    def _bound_query_width(self) -> None:
        """Clamp the search box to a readable width (24-64 characters).

        The width is derived from the current font so it tracks the actual
        character advance. Overflowing text scrolls within the field (the
        default ``QLineEdit`` behaviour), so no extra work is needed there.
        """
        metrics = self._query.fontMetrics()
        padding = 16  # frame + left/right padding
        min_px = metrics.horizontalAdvance("0" * 24) + padding
        max_px = metrics.horizontalAdvance("0" * 64) + padding
        self._query.setMinimumWidth(min_px)
        self._query.setMaximumWidth(max_px)

    def _build_theme_menu(self) -> QMenu:
        """Build an exclusive System/Light/Dark theme selector menu."""
        menu = QMenu(self)
        group = QActionGroup(self)
        group.setExclusive(True)

        self._theme_actions: dict[str, QAction] = {}
        for mode, label, icon_name in (
            ("system", "System", "monitor"),
            ("light", "Light", "sun"),
            ("dark", "Dark", "moon"),
        ):
            action = QAction(icons.icon(icon_name), label, self)
            action.setCheckable(True)
            group.addAction(action)
            menu.addAction(action)
            self._theme_actions[mode] = action
            action.triggered.connect(lambda _checked, m=mode: self.theme_selected.emit(m))
        return menu

    def set_theme_mode(self, mode: str) -> None:
        """Reflect the active theme preference in the menu's checked action."""
        action = self._theme_actions.get(mode)
        if action is not None:
            action.setChecked(True)

    def _show_due_calendar(self, anchor: QPushButton, target: QLineEdit) -> None:
        """Pop up a calendar anchored to ``anchor`` for the ``target`` field.

        The popup is a top-level window retained on ``self`` so it is not
        garbage-collected (and closed) before the user can interact with it.
        Clicking the button again toggles the popup closed.
        """
        if self._due_calendar_popup is not None and self._due_calendar_popup.isVisible():
            self._due_calendar_popup.hide()
            return

        if self._due_calendar_popup is None:
            popup = QWidget()
            popup.setWindowFlags(Qt.WindowType.Popup)
            layout = QVBoxLayout(popup)
            layout.setContentsMargins(4, 4, 4, 4)
            self._due_calendar = QCalendarWidget()
            self._due_calendar.setSelectedDate(QDate.currentDate())
            self._due_calendar.selectionChanged.connect(self._on_calendar_selected)
            layout.addWidget(self._due_calendar)
            self.destroyed.connect(popup.deleteLater)
            self._due_calendar_popup = popup

        self._calendar_target = target
        popup = self._due_calendar_popup
        popup.show()
        popup.move(anchor.mapToGlobal(anchor.rect().bottomLeft()))

    def _on_calendar_selected(self) -> None:
        """Write the picked date into the target field and close the popup."""
        if self._calendar_target is not None and self._due_calendar is not None:
            self._calendar_target.setText(self._due_calendar.selectedDate().toString("yyyy-MM-dd"))
        self._close_due_calendar()

    def _close_due_calendar(self) -> None:
        """Hide the due-date calendar popup if it is open."""
        if self._due_calendar_popup is not None:
            self._due_calendar_popup.hide()

    def _parse_due(self, edit: QLineEdit) -> date | None:
        """Parse a field's text as a yyyy-MM-dd date, or ``None`` if invalid."""
        text = edit.text().strip()
        if not text:
            return None
        parsed = QDate.fromString(text, "yyyy-MM-dd")
        if not parsed.isValid():
            return None
        return date(parsed.year(), parsed.month(), parsed.day())

    def _emit_filters(self, *_args: object) -> None:
        """Emit the current filter dictionary."""
        self.filters_changed.emit(self.build_filters())

    def build_filters(self) -> Filters:
        """Return the current filter values as a dictionary."""
        return {
            "query": self._query.text().strip(),
            "priority": self._priority.currentData(),
            "column_id": self._column.currentData(),
            "label_id": self._label.currentData(),
            "due_before": self._parse_due(self._due_before),
            "due_after": self._parse_due(self._due_after),
        }

    def load_columns(self, columns: list[tuple[int, str]]) -> None:
        """Populate the column filter from ``(id, title)`` tuples."""
        self._column.blockSignals(True)
        self._column.clear()
        self._column.addItem("Any column", None)
        for column_id, title in columns:
            self._column.addItem(title, column_id)
        self._column.blockSignals(False)

    def load_labels(self, labels: list[tuple[int, str]]) -> None:
        """Populate the label filter from ``(id, name)`` tuples."""
        self._label.blockSignals(True)
        self._label.clear()
        self._label.addItem("Any label", None)
        for label_id, name in labels:
            self._label.addItem(name, label_id)
        self._label.blockSignals(False)

    def _reset_controls(self) -> None:
        """Reset every control to its default (no-filter) state."""
        self._query.blockSignals(True)
        self._query.clear()
        self._query.blockSignals(False)

        self._priority.blockSignals(True)
        self._priority.setCurrentIndex(0)
        self._priority.blockSignals(False)

        self._column.blockSignals(True)
        self._column.setCurrentIndex(0)
        self._column.blockSignals(False)

        self._label.blockSignals(True)
        self._label.setCurrentIndex(0)
        self._label.blockSignals(False)

        self._due_after.blockSignals(True)
        self._due_after.clear()
        self._due_after.blockSignals(False)

        self._due_before.blockSignals(True)
        self._due_before.clear()
        self._due_before.blockSignals(False)

    def clear(self) -> None:
        """Reset all controls and emit an empty filter set."""
        self._reset_controls()
        self.filters_changed.emit(self.build_filters())

    def reset(self) -> None:
        """Reset all controls without emitting (used when switching boards)."""
        self._reset_controls()
