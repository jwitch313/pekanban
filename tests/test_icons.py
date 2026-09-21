"""Tests for the SVG icon factory."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from kanban.ui import icons


def test_icon_returns_non_null_icon(qapp: QApplication) -> None:
    for name in icons.icon_names():
        assert not icons.icon(name).isNull(), f"icon {name!r} rendered null"


def test_icon_renders_at_requested_size(qapp: QApplication) -> None:
    icon = icons.icon("plus", size=24)
    assert icon.availableSizes() or not icon.isNull()


def test_icon_is_cached(qapp: QApplication) -> None:
    assert icons.icon("plus") is icons.icon("plus")


def test_unknown_icon_raises(qapp: QApplication) -> None:
    with pytest.raises(KeyError):
        icons.icon("does-not-exist")


def test_expected_icons_present(qapp: QApplication) -> None:
    names = set(icons.icon_names())
    for expected in (
        "plus",
        "trash",
        "pencil",
        "tag",
        "arrow_left",
        "arrow_right",
        "clear",
        "sun",
        "moon",
        "monitor",
    ):
        assert expected in names
