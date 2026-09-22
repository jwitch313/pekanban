"""Database engine, session management, and schema migrations.

This module owns all SQLAlchemy engine/session creation. Callers should use
the :class:`Database` object and its ``session()`` context manager rather than
touching the engine directly.

Design notes:
- SQLite is used with WAL mode for better concurrency and a shared cache.
- A lightweight, versioned migration framework replaces Alembic (the SDR
  allows "Alembic or manual schema evolution scripts").
- No raw SQL strings are used; DDL and DML go through SQLAlchemy Core/ORM.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    MetaData,
    Table,
    func,
    select,
    text,
)
from sqlalchemy import (
    create_engine as create_sqlalchemy_engine,
)
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from kanban.models import Base

DEFAULT_DB_FILENAME = "kanban.db"
APP_DATA_DIRNAME = ".kanban"


def default_db_path() -> Path:
    """Return the default on-disk location for the SQLite database file."""
    data_dir = Path.home() / APP_DATA_DIRNAME
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / DEFAULT_DB_FILENAME


def create_engine(db_path: str | Path | None = None) -> Engine:
    """Create a SQLite engine with sensible defaults for a desktop app."""
    path = Path(db_path) if db_path is not None else default_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    url = f"sqlite:///{path.as_posix()}"
    return create_sqlalchemy_engine(
        url,
        connect_args={"check_same_thread": False},
    )


@dataclass(frozen=True)
class Migration:
    """A single, ordered schema migration."""

    version: int
    name: str
    apply: Callable[[Engine], None]


def _migration_0001_initial(engine: Engine) -> None:
    """Create the initial schema from the ORM metadata."""
    Base.metadata.create_all(engine)


def _migration_0002_task_archived(engine: Engine) -> None:
    """Add the ``archived`` flag to existing tasks.

    Fresh databases already get the column from the ORM metadata (migration 1);
    this migration only runs on databases created before the column existed.
    """
    from sqlalchemy import inspect

    inspector = inspect(engine)
    if not inspector.has_table("tasks"):
        return
    existing = {column["name"] for column in inspector.get_columns("tasks")}
    if "archived" in existing:
        return
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE tasks ADD COLUMN archived BOOLEAN NOT NULL DEFAULT 0"))


MIGRATIONS: list[Migration] = [
    Migration(version=1, name="initial schema", apply=_migration_0001_initial),
    Migration(version=2, name="task archived flag", apply=_migration_0002_task_archived),
]

# Bookkeeping table tracking which migrations have been applied.
_metadata = MetaData()
_schema_version_table = Table(
    "schema_version",
    _metadata,
    Column("version", Integer, primary_key=True),
    Column("applied_at", DateTime, server_default=func.now()),
)


def _ensure_schema_version_table(engine: Engine) -> None:
    """Create the migration bookkeeping table if it does not exist."""
    _schema_version_table.create(engine, checkfirst=True)


def _current_version(engine: Engine) -> int:
    """Return the highest applied migration version (0 if none)."""
    with engine.connect() as connection:
        value = connection.execute(select(func.max(_schema_version_table.c.version))).scalar()
    return int(value) if value is not None else 0


def run_migrations(engine: Engine) -> None:
    """Apply any pending migrations in version order."""
    _ensure_schema_version_table(engine)
    current = _current_version(engine)
    for migration in MIGRATIONS:
        if migration.version > current:
            with engine.begin() as connection:
                migration.apply(engine)
                connection.execute(_schema_version_table.insert().values(version=migration.version))


class Database:
    """Owns the engine and provides scoped, transactional sessions."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine
        self._session_factory = sessionmaker(
            bind=engine,
            expire_on_commit=False,
        )

    @property
    def engine(self) -> Engine:
        """Expose the underlying engine for advanced use."""
        return self._engine

    @contextmanager
    def session(self) -> Iterator[Session]:
        """Yield a session that commits on success and rolls back on error."""
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def init_db(self) -> None:
        """Create the schema and apply all pending migrations."""
        run_migrations(self._engine)

    def dispose(self) -> None:
        """Dispose of the engine's connection pool."""
        self._engine.dispose()


def create_database(db_path: str | Path | None = None) -> Database:
    """Convenience factory that builds a :class:`Database` from a path."""
    return Database(create_engine(db_path))
