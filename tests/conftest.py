"""Shared pytest fixtures for the KanBan test suite."""

from __future__ import annotations

import pytest

from kanban.services.database import Database, create_database


@pytest.fixture
def database(tmp_path) -> Database:
    """Provide a fresh, migrated in-file SQLite database per test."""
    db = create_database(tmp_path / "test_kanban.db")
    db.init_db()
    yield db
    db.dispose()
