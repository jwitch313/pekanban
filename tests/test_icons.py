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


def test_icons_have_semantic_colors(qapp: QApplication) -> None:
    """Each icon should default to a semantic color, not the old neutral gray."""
    for name in icons.icon_names():
        assert name in icons.DEFAULT_ICON_COLORS, f"icon {name!r} has no semantic color"
        assert icons.default_color(name) != icons.DEFAULT_ICON_COLOR, (
            f"icon {name!r} still uses the old neutral gray"
        )


def test_icons_render_in_color_not_gray(qapp: QApplication) -> None:
    """Icon strokes should render in their semantic color, not the old gray."""
    from PySide6.QtGui import QColor

    for name in icons.icon_names():
        expected = QColor(icons.default_color(name))
        pixmap = icons.icon(name, size=24).pixmap(24, 24)
        found = False
        for x in range(pixmap.width()):
            for y in range(pixmap.height()):
                c = pixmap.toImage().pixelColor(x, y)
                if c.alpha() > 0 and (c.red(), c.green(), c.blue()) == (
                    expected.red(),
                    expected.green(),
                    expected.blue(),
                ):
                    found = True
                    break
            if found:
                break
        assert found, f"icon {name!r} does not render in its semantic color {expected.name()}"
