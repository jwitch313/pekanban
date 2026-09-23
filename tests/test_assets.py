"""Tests for asset resolution and the bundled PeKanBan logo files."""

from __future__ import annotations

from kanban.assets import asset_path


def test_logo_assets_exist() -> None:
    assert asset_path("logo.svg").is_file()
    assert asset_path("logo-icon.svg").is_file()


def test_dark_logo_assets_exist() -> None:
    """Light-grey logo variants must ship for dark backgrounds."""
    assert asset_path("logo-dark.svg").is_file()
    assert asset_path("logo-icon-dark.svg").is_file()


def test_dark_logo_uses_light_stroke() -> None:
    """The dark-theme icon must not reuse the brown light-theme stroke."""
    icon = asset_path("logo-icon-dark.svg").read_text(encoding="utf-8")
    assert "#8C5A2B" not in icon
    assert "#c8cdd4" in icon
