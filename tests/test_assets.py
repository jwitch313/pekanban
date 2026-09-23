"""Tests for asset resolution and the bundled PeKanBan logo files."""

from __future__ import annotations

from kanban.assets import asset_path


def test_logo_assets_exist() -> None:
    assert asset_path("logo.svg").is_file()
    assert asset_path("logo-icon.svg").is_file()
