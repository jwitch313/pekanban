"""Theme management: light/dark stylesheets and system-aware detection.

The SDR requires dark mode that follows the Windows system setting. This module
owns the two QSS stylesheets and a small, testable detection helper. ``app.py``
calls :func:`apply_theme` at startup with the detected mode.
"""

from __future__ import annotations

import enum
import os
import platform

import PySide6.QtWidgets as QtWidgets


class ThemeMode(enum.Enum):
    """The two supported appearance modes."""

    LIGHT = "light"
    DARK = "dark"


LIGHT_QSS = """
* { outline: none; }
QMainWindow, QWidget { background-color: #f5f6f8; color: #1f2328; }
QLabel { color: #1f2328; }
QMenuBar { background-color: #ffffff; color: #1f2328; border-bottom: 1px solid #d0d4da; }
QMenuBar::item:selected { background-color: #e2e6ea; }
QMenu { background-color: #ffffff; color: #1f2328; border: 1px solid #d0d4da; }
QMenu::item:selected { background-color: #e2e6ea; }
QPushButton {
    background-color: #ffffff; color: #1f2328;
    border: 1px solid #c4c9d0; border-radius: 6px; padding: 6px 12px;
}
QPushButton:hover { background-color: #eef1f4; }
QPushButton:pressed { background-color: #e2e6ea; }
QLineEdit, QComboBox, QDateEdit {
    background-color: #ffffff; color: #1f2328;
    border: 1px solid #c4c9d0; border-radius: 6px; padding: 4px 8px;
    selection-background-color: #2f6fed; selection-color: #ffffff;
}
QComboBox::drop-down { border: none; }
QComboBox QAbstractItemView {
    background-color: #ffffff; color: #1f2328;
    border: 1px solid #c4c9d0; selection-background-color: #e2e6ea;
}
QCheckBox { color: #1f2328; spacing: 6px; }
QCheckBox::indicator {
    width: 16px; height: 16px; border: 1px solid #c4c9d0;
    border-radius: 4px; background: #ffffff;
}
QCheckBox::indicator:checked { background: #2f6fed; border-color: #2f6fed; }
QToolTip { background-color: #ffffff; color: #1f2328; border: 1px solid #c4c9d0; }
QScrollBar:vertical { background: transparent; width: 12px; margin: 0; }
QScrollBar::handle:vertical { background: #c4c9d0; border-radius: 6px; min-height: 24px; }
QScrollBar::handle:vertical:hover { background: #a9b0b9; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { background: transparent; height: 12px; margin: 0; }
QScrollBar::handle:horizontal { background: #c4c9d0; border-radius: 6px; min-width: 24px; }
QScrollBar::handle:horizontal:hover { background: #a9b0b9; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
"""

DARK_QSS = """
* { outline: none; }
QMainWindow, QWidget { background-color: #1e1f22; color: #e6e6e6; }
QLabel { color: #e6e6e6; }
QMenuBar { background-color: #26272b; color: #e6e6e6; border-bottom: 1px solid #3a3b40; }
QMenuBar::item:selected { background-color: #34353b; }
QMenu { background-color: #26272b; color: #e6e6e6; border: 1px solid #3a3b40; }
QMenu::item:selected { background-color: #34353b; }
QPushButton {
    background-color: #2c2d31; color: #e6e6e6;
    border: 1px solid #45464c; border-radius: 6px; padding: 6px 12px;
}
QPushButton:hover { background-color: #34353b; }
QPushButton:pressed { background-color: #3d3e44; }
QLineEdit, QComboBox, QDateEdit {
    background-color: #2c2d31; color: #e6e6e6;
    border: 1px solid #45464c; border-radius: 6px; padding: 4px 8px;
    selection-background-color: #2f6fed; selection-color: #ffffff;
}
QComboBox::drop-down { border: none; }
QComboBox QAbstractItemView {
    background-color: #2c2d31; color: #e6e6e6;
    border: 1px solid #45464c; selection-background-color: #34353b;
}
QCheckBox { color: #e6e6e6; spacing: 6px; }
QCheckBox::indicator {
    width: 16px; height: 16px; border: 1px solid #45464c;
    border-radius: 4px; background: #2c2d31;
}
QCheckBox::indicator:checked { background: #2f6fed; border-color: #2f6fed; }
QToolTip { background-color: #2c2d31; color: #e6e6e6; border: 1px solid #45464c; }
QScrollBar:vertical { background: transparent; width: 12px; margin: 0; }
QScrollBar::handle:vertical { background: #45464c; border-radius: 6px; min-height: 24px; }
QScrollBar::handle:vertical:hover { background: #5a5b62; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { background: transparent; height: 12px; margin: 0; }
QScrollBar::handle:horizontal { background: #45464c; border-radius: 6px; min-width: 24px; }
QScrollBar::handle:horizontal:hover { background: #5a5b62; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
"""


def theme_from_apps_use_light(value: int | None) -> ThemeMode:
    """Map the Windows ``AppsUseLightTheme`` registry value to a theme mode.

    ``1`` means the user prefers light, ``0`` means dark. ``None`` (value
    missing or unreadable) falls back to light.
    """
    if value is None:
        return ThemeMode.LIGHT
    return ThemeMode.LIGHT if int(value) == 1 else ThemeMode.DARK


def _detect_windows_theme() -> ThemeMode:
    """Read the Windows light/dark preference from the user registry."""
    import winreg

    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        )
        try:
            value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        finally:
            winreg.CloseKey(key)
        return theme_from_apps_use_light(int(value))
    except OSError:  # pragma: no cover - registry unavailable
        return ThemeMode.LIGHT


def detect_system_theme() -> ThemeMode:
    """Return the OS-level theme preference (dark or light).

    On Windows this reads the ``AppsUseLightTheme`` registry value. On other
    platforms it honors the ``KANBAN_THEME`` environment variable (``dark`` or
    ``light``) and otherwise defaults to light.
    """
    if platform.system() == "Windows":
        return _detect_windows_theme()
    override = os.environ.get("KANBAN_THEME", "").strip().lower()
    if override in {"dark", "light"}:
        return ThemeMode(override)
    return ThemeMode.LIGHT


def apply_theme(app: QtWidgets.QApplication, mode: ThemeMode) -> None:
    """Apply the given theme's stylesheet to the application."""
    app.setStyleSheet(DARK_QSS if mode is ThemeMode.DARK else LIGHT_QSS)
