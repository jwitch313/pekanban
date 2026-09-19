"""Tests for the database service: migrations and session management."""

from __future__ import annotations

from sqlalchemy import func, select

from kanban.models import Board
from kanban.services.database import (
    Database,
    _schema_version_table,
    create_database,
    run_migrations,
)


def test_migrations_are_idempotent(tmp_path) -> None:
    db = create_database(tmp_path / "t.db")
    db.init_db()
    # Running again should not raise or duplicate.
    run_migrations(db.engine)
    run_migrations(db.engine)
    db.dispose()


def test_schema_version_recorded(tmp_path) -> None:
    db = create_database(tmp_path / "t.db")
    db.init_db()
    with db.engine.connect() as connection:
        versions = connection.execute(select(_schema_version_table.c.version)).scalars().all()
    assert 1 in versions
    db.dispose()


def test_session_commits_on_success(database: Database) -> None:
    with database.session() as session:
        session.add(Board(name="Committed"))
    with database.session() as session:
        count = session.execute(select(func.count()).select_from(Board)).scalar()
    assert count == 1


def test_session_rolls_back_on_error(database: Database) -> None:
    try:
        with database.session() as session:
            session.add(Board(name="Rolled back"))
            raise RuntimeError("boom")
    except RuntimeError:
        pass
    with database.session() as session:
        count = session.execute(select(func.count()).select_from(Board)).scalar()
    assert count == 0
