"""Tests for the light/dark theme module (Step 4, Slice 3)."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from kanban.ui.theme import (
    DARK_QSS,
    LIGHT_QSS,
    ThemeMode,
    apply_theme,
    detect_system_theme,
    resolve_theme_mode,
    theme_from_apps_use_light,
)


def test_theme_from_apps_use_light_light() -> None:
    assert theme_from_apps_use_light(1) is ThemeMode.LIGHT


def test_theme_from_apps_use_light_dark() -> None:
    assert theme_from_apps_use_light(0) is ThemeMode.DARK


def test_theme_from_apps_use_light_missing_defaults_light() -> None:
    assert theme_from_apps_use_light(None) is ThemeMode.LIGHT


def test_detect_system_theme_returns_valid_mode() -> None:
    assert detect_system_theme() in {ThemeMode.LIGHT, ThemeMode.DARK}


def test_apply_theme_dark(qapp: QApplication) -> None:
    apply_theme(qapp, ThemeMode.DARK)
    assert qapp.styleSheet() == DARK_QSS


def test_apply_theme_light(qapp: QApplication) -> None:
    apply_theme(qapp, ThemeMode.LIGHT)
    assert qapp.styleSheet() == LIGHT_QSS


def test_stylesheets_are_nonempty_and_cover_key_widgets() -> None:
    for qss in (LIGHT_QSS, DARK_QSS):
        assert qss.strip()
        assert "QMainWindow" in qss
        assert "QPushButton" in qss
        assert "QLineEdit" in qss


def test_stylesheets_style_board_widgets_for_contrast() -> None:
    """Board object names must be styled so columns and cards contrast."""
    for qss in (LIGHT_QSS, DARK_QSS):
        for selector in ("#boardView", "#column", "#card", "#columnTitle"):
            assert selector in qss, f"{selector} missing from stylesheet"


def test_column_and_card_backgrounds_differ() -> None:
    """The column and card backgrounds must not be identical (readability)."""
    import re

    for qss in (LIGHT_QSS, DARK_QSS):
        column_bg = re.search(r"#column\s*\{[^}]*background-color:\s*(#[0-9a-fA-F]+)", qss)
        card_bg = re.search(r"#card\s*\{[^}]*background-color:\s*(#[0-9a-fA-F]+)", qss)
        assert column_bg is not None and card_bg is not None
        assert column_bg.group(1).lower() != card_bg.group(1).lower()


def test_resolve_theme_mode_light() -> None:
    assert resolve_theme_mode("light") is ThemeMode.LIGHT


def test_resolve_theme_mode_dark() -> None:
    assert resolve_theme_mode("dark") is ThemeMode.DARK


def test_resolve_theme_mode_system_uses_detection(monkeypatch) -> None:
    import kanban.ui.theme as theme_module

    monkeypatch.setattr(theme_module, "detect_system_theme", lambda: ThemeMode.DARK)
    assert resolve_theme_mode("system") is ThemeMode.DARK


def test_resolve_theme_mode_invalid_raises() -> None:
    with pytest.raises(ValueError):
        resolve_theme_mode("neon")
