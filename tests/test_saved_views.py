"""Tests for saved views (Step 7, Slice 3, F-25)."""

from __future__ import annotations

import pytest

from kanban.services.database import Database
from kanban.services.saved_view_service import SavedViewService


@pytest.fixture
def service(database: Database) -> SavedViewService:
    return SavedViewService(database)


def test_create_and_get_roundtrip(service: SavedViewService) -> None:
    filters = {"priority": "high", "due_this_week": True}
    view = service.create_view("High + Due", filters)

    fetched = service.get_view(view.id)
    assert fetched.name == "High + Due"
    assert service.filters_for(view.id) == filters


def test_create_default_filters_empty(service: SavedViewService) -> None:
    view = service.create_view("All")
    assert service.filters_for(view.id) == {}


def test_create_blank_name_raises(service: SavedViewService) -> None:
    with pytest.raises(ValueError):
        service.create_view("   ")


def test_create_duplicate_name_raises(service: SavedViewService) -> None:
    service.create_view("Mine")
    with pytest.raises(ValueError):
        service.create_view("Mine")


def test_create_non_dict_filters_raises(service: SavedViewService) -> None:
    with pytest.raises(ValueError):
        service.create_view("Bad", filters=["not", "a", "dict"])  # type: ignore[arg-type]


def test_list_views_ordered_by_name(service: SavedViewService) -> None:
    service.create_view("Zebra")
    service.create_view("Alpha")
    service.create_view("Mid")

    names = [v.name for v in service.list_views()]
    assert names == ["Alpha", "Mid", "Zebra"]


def test_update_name_and_filters(service: SavedViewService) -> None:
    view = service.create_view("Old", {"a": 1})

    updated = service.update_view(view.id, name="New", filters={"b": 2})

    assert updated.name == "New"
    assert service.filters_for(view.id) == {"b": 2}


def test_update_partial_keeps_other_fields(service: SavedViewService) -> None:
    view = service.create_view("Keep", {"a": 1})

    updated = service.update_view(view.id, name="Renamed")

    assert updated.name == "Renamed"
    assert service.filters_for(view.id) == {"a": 1}


def test_update_duplicate_name_raises(service: SavedViewService) -> None:
    service.create_view("One")
    other = service.create_view("Two")
    with pytest.raises(ValueError):
        service.update_view(other.id, name="One")


def test_update_missing_raises(service: SavedViewService) -> None:
    with pytest.raises(LookupError):
        service.update_view(9999, name="X")


def test_delete_view(service: SavedViewService) -> None:
    view = service.create_view("Gone")
    service.delete_view(view.id)
    with pytest.raises(LookupError):
        service.get_view(view.id)


def test_delete_missing_raises(service: SavedViewService) -> None:
    with pytest.raises(LookupError):
        service.delete_view(9999)
