"""Tests for the settings service (Step 7, Slice 4, final UI polish)."""

from __future__ import annotations

import pytest

from kanban.services.database import Database
from kanban.services.settings_service import SettingsService


@pytest.fixture
def service(database: Database) -> SettingsService:
    return SettingsService(database)


def test_get_returns_default_when_unset(service: SettingsService) -> None:
    assert service.get("theme", "light") == "light"
    assert service.get("theme") is None


def test_set_and_get_roundtrip(service: SettingsService) -> None:
    service.set("theme", "dark")
    assert service.get("theme") == "dark"


def test_set_overwrites(service: SettingsService) -> None:
    service.set("theme", "light")
    service.set("theme", "dark")
    assert service.get("theme") == "dark"


def test_unknown_key_raises(service: SettingsService) -> None:
    with pytest.raises(ValueError):
        service.get("bogus")
    with pytest.raises(ValueError):
        service.set("bogus", "x")
    with pytest.raises(ValueError):
        service.delete("bogus")


def test_invalid_theme_raises(service: SettingsService) -> None:
    with pytest.raises(ValueError):
        service.set("theme", "neon")


def test_invalid_view_raises(service: SettingsService) -> None:
    with pytest.raises(ValueError):
        service.set("active_view", "gantt++")


def test_last_board_id_roundtrip(service: SettingsService) -> None:
    assert service.last_board_id() is None
    service.set_last_board_id(42)
    assert service.last_board_id() == 42


def test_last_board_id_clear(service: SettingsService) -> None:
    service.set_last_board_id(7)
    service.set_last_board_id(None)
    assert service.last_board_id() is None


def test_last_board_id_non_int_raises(service: SettingsService) -> None:
    with pytest.raises(ValueError):
        service.set("last_board_id", "not-a-number")


def test_all_returns_stored_settings(service: SettingsService) -> None:
    service.set("theme", "dark")
    service.set("active_view", "gantt")
    service.set_last_board_id(3)

    assert service.all() == {
        "active_view": "gantt",
        "last_board_id": "3",
        "theme": "dark",
    }


def test_reset_clears_all(service: SettingsService) -> None:
    service.set("theme", "dark")
    service.set("active_view", "calendar")
    service.reset()
    assert service.all() == {}
    assert service.get("theme") is None


def test_typed_defaults(service: SettingsService) -> None:
    assert service.theme() == "light"
    assert service.active_view() == "kanban"
    assert service.window_geometry() is None


def test_window_geometry_roundtrip(service: SettingsService) -> None:
    service.set_window_geometry("0,0,1280,720")
    assert service.window_geometry() == "0,0,1280,720"
