"""Tests for keyboard shortcuts (Step 4, Slice 4)."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QApplication

from kanban.main_window import MainWindow
from kanban.ui.column_widget import ColumnWidget


def _first_column(window: MainWindow) -> ColumnWidget:
    """Return the first ColumnWidget in the board view."""
    layout = window._board_view._column_layout
    for i in range(layout.count()):
        item = layout.itemAt(i)
        widget = item.widget() if item is not None else None
        if isinstance(widget, ColumnWidget):
            return widget
    raise AssertionError("no column widget found")


def test_shortcuts_registered(window: MainWindow) -> None:
    keys = {shortcut.key().toString() for shortcut in window._shortcuts}
    assert QKeySequence("Ctrl+N").toString() in keys
    assert QKeySequence("Ctrl+T").toString() in keys
    assert QKeySequence("Esc").toString() in keys


def test_shortcut_new_column_focuses(window: MainWindow, qapp: QApplication) -> None:
    window.show()
    qapp.processEvents()
    window._shortcut_new_column()
    qapp.processEvents()
    assert window._board_view._column_edit.hasFocus()


def test_shortcut_new_task_focuses(window: MainWindow, qapp: QApplication) -> None:
    window.show()
    qapp.processEvents()
    window._shortcut_new_task()
    qapp.processEvents()
    assert _first_column(window)._add_edit.hasFocus()


def test_shortcut_cancel_clears_focused_edit(
    window: MainWindow, qapp: QApplication
) -> None:
    window.show()
    qapp.processEvents()
    edit = window._board_view._column_edit
    edit.setFocus()
    edit.setText("draft")
    qapp.processEvents()
    window._shortcut_cancel()
    assert edit.text() == ""
