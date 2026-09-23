"""Shared pytest fixtures for the PeKanBan test suite."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from kanban.main_window import MainWindow
from kanban.services.database import Database, create_database


@pytest.fixture
def database(tmp_path) -> Database:
    """Provide a fresh, migrated in-file SQLite database per test."""
    db = create_database(tmp_path / "test_kanban.db")
    db.init_db()
    yield db
    db.dispose()


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    """Provide a single offscreen QApplication for the whole session."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def window(qapp, tmp_path) -> MainWindow:
    """Provide a main window backed by a throwaway database."""
    db = create_database(tmp_path / "ui.db")
    win = MainWindow(database=db)
    yield win
    win.close()
    db.dispose()
