"""A search & filter bar for the current board.

The bar is presentational only: it collects a free-text query, a priority, a
column, a label, and an optional due-date range, and emits
:attr:`filters_changed` with a dictionary of the active filters. The
:class:`~kanban.main_window.MainWindow` routes that to
:meth:`TaskService.search_tasks` and re-renders the board with only the
matching cards.
"""

from __future__ import annotations

from PySide6.QtCore import QDate, Signal
from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QFrame,
    QHBoxLayout,
    QLineEdit,
    QMenu,
    QPushButton,
)

from kanban.models import Priority
from kanban.ui import icons

#: A dictionary of active search/filter criteria.
Filters = dict[str, object]


class SearchBar(QFrame):
    """Collects search/filter criteria and emits them as a dictionary."""

    filters_changed = Signal(dict)
    theme_selected = Signal(str)

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
        layout.addWidget(self._query, 1)

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

        # Each due-date field is always enabled so the user can pick a date
        # directly. A field only contributes to the filter once the user has
        # actually set a date (tracked by the ``*_active`` flags below).
        self._due_after_active = False
        self._due_before_active = False

        self._due_after = QDateEdit()
        self._due_after.setCalendarPopup(True)
        self._due_after.setAccessibleName("Due from")
        self._due_after.setDisplayFormat("yyyy-MM-dd")
        self._due_after.dateChanged.connect(self._on_due_after_changed)
        layout.addWidget(self._due_after)

        self._due_before = QDateEdit()
        self._due_before.setCalendarPopup(True)
        self._due_before.setAccessibleName("Due until")
        self._due_before.setDisplayFormat("yyyy-MM-dd")
        self._due_before.dateChanged.connect(self._on_due_before_changed)
        layout.addWidget(self._due_before)

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
        layout.addWidget(self._theme_button)

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

    def _on_due_after_changed(self, *_args: object) -> None:
        """Mark the 'due from' field active and re-emit filters."""
        self._due_after_active = True
        self._emit_filters()

    def _on_due_before_changed(self, *_args: object) -> None:
        """Mark the 'due until' field active and re-emit filters."""
        self._due_before_active = True
        self._emit_filters()

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
            "due_before": (self._due_before.date().toPython() if self._due_before_active else None),
            "due_after": (self._due_after.date().toPython() if self._due_after_active else None),
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

        self._due_after_active = False
        self._due_before_active = False

        self._due_after.blockSignals(True)
        self._due_after.setDate(QDate.currentDate())
        self._due_after.blockSignals(False)

        self._due_before.blockSignals(True)
        self._due_before.setDate(QDate.currentDate())
        self._due_before.blockSignals(False)

    def clear(self) -> None:
        """Reset all controls and emit an empty filter set."""
        self._reset_controls()
        self.filters_changed.emit(self.build_filters())

    def reset(self) -> None:
        """Reset all controls without emitting (used when switching boards)."""
        self._reset_controls()
