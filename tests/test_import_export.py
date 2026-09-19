"""Tests for the JSON import/export service."""

from __future__ import annotations

import os
import tempfile
from datetime import date

import pytest

from kanban.models import Priority
from kanban.services.database import Database, create_database
from kanban.services.import_export import ImportExportService
from kanban.services.task_service import TaskService


@pytest.fixture
def service(database: Database) -> ImportExportService:
    return ImportExportService(database)


@pytest.fixture
def tasks(database: Database) -> TaskService:
    return TaskService(database)


def _build_sample(tasks: TaskService):
    """Create a board with a column, a task, and a label, then wire them up."""
    board = tasks.create_board("Work", icon="briefcase", color="#123456")
    column = board.columns[0]
    label = tasks.create_label(board.id, "Bug", color="#ff0000")
    task = tasks.create_task(
        column.id,
        "Fix crash",
        description="Repro steps",
        priority=Priority.HIGH,
        due_date=date(2025, 6, 1),
        status_color="#00ff00",
    )
    tasks.assign_label(task.id, label.id)
    return board, column, label, task


def test_serialize_empty_database(service: ImportExportService) -> None:
    payload = service.serialize()
    assert payload["version"] == 1
    assert payload["boards"] == []


def test_serialize_structure(service: ImportExportService, tasks: TaskService) -> None:
    board, _column, _label, _task = _build_sample(tasks)
    payload = service.serialize()
    assert len(payload["boards"]) == 1
    board_data = payload["boards"][0]
    assert board_data["name"] == board.name
    assert board_data["icon"] == "briefcase"
    assert board_data["color"] == "#123456"
    assert board_data["labels"] == [{"name": "Bug", "color": "#ff0000"}]
    assert len(board_data["columns"]) == 1
    column_data = board_data["columns"][0]
    assert column_data["title"] == "To Do"
    assert len(column_data["tasks"]) == 1
    task_data = column_data["tasks"][0]
    assert task_data["title"] == "Fix crash"
    assert task_data["priority"] == "high"
    assert task_data["due_date"] == "2025-06-01"
    assert task_data["status_color"] == "#00ff00"
    assert task_data["completed"] is False
    assert task_data["labels"] == ["Bug"]


def test_round_trip_preserves_structure(service: ImportExportService, tasks: TaskService) -> None:
    _board, _column, _label, _task = _build_sample(tasks)
    payload = service.serialize()

    # Restore into a fresh database.
    with tempfile.TemporaryDirectory() as tmp:
        fresh = create_database(os.path.join(tmp, "fresh.db"))
        fresh.init_db()
        try:
            ImportExportService(fresh).deserialize(payload)
            restored = TaskService(fresh).get_board_full(1)
            assert restored is not None
            assert restored.name == "Work"
            assert len(restored.columns) == 1
            column = restored.columns[0]
            assert column.title == "To Do"
            assert len(column.tasks) == 1
            task = column.tasks[0]
            assert task.title == "Fix crash"
            assert task.priority is Priority.HIGH
            assert task.due_date == date(2025, 6, 1)
            assert task.status_color == "#00ff00"
            assert [label.name for label in task.labels] == ["Bug"]
            assert [label.name for label in restored.labels] == ["Bug"]
        finally:
            fresh.dispose()


def test_export_and_import_file_round_trip(
    service: ImportExportService, tasks: TaskService, tmp_path
) -> None:
    _board, _column, _label, _task = _build_sample(tasks)
    out = tmp_path / "backup.json"
    service.export_json(out)
    assert out.exists()

    # Import into a fresh database from the file.
    fresh = create_database(tmp_path / "fresh.db")
    fresh.init_db()
    try:
        ImportExportService(fresh).import_json(out)
        restored = TaskService(fresh).get_board_full(1)
        assert restored is not None
        assert restored.name == "Work"
        assert restored.columns[0].tasks[0].title == "Fix crash"
    finally:
        fresh.dispose()


def test_deserialize_invalid_priority_falls_back_to_medium(
    service: ImportExportService,
) -> None:
    payload = {
        "version": 1,
        "boards": [
            {
                "name": "B",
                "columns": [
                    {"title": "C", "tasks": [{"title": "T", "priority": "bogus"}]}
                ],
            }
        ],
    }
    service.deserialize(payload)
    board = TaskService(service._db).get_board_full(1)
    assert board is not None
    assert board.columns[0].tasks[0].priority is Priority.MEDIUM


def test_deserialize_invalid_date_becomes_none(service: ImportExportService) -> None:
    payload = {
        "version": 1,
        "boards": [
            {
                "name": "B",
                "columns": [
                    {"title": "C", "tasks": [{"title": "T", "due_date": "not-a-date"}]}
                ],
            }
        ],
    }
    service.deserialize(payload)
    board = TaskService(service._db).get_board_full(1)
    assert board is not None
    assert board.columns[0].tasks[0].due_date is None


def test_deserialize_missing_optional_fields(service: ImportExportService) -> None:
    payload = {
        "version": 1,
        "boards": [{"name": "B", "columns": [{"title": "C", "tasks": [{"title": "T"}]}]}]
    }
    service.deserialize(payload)
    board = TaskService(service._db).get_board_full(1)
    assert board is not None
    task = board.columns[0].tasks[0]
    assert task.priority is Priority.MEDIUM
    assert task.due_date is None
    assert task.completed is False
    assert task.labels == []


def test_deserialize_task_label_not_in_board_creates_label(
    service: ImportExportService,
) -> None:
    payload = {
        "version": 1,
        "boards": [
            {
                "name": "B",
                "labels": [],
                "columns": [
                    {"title": "C", "tasks": [{"title": "T", "labels": ["AdHoc"]}]}
                ],
            }
        ],
    }
    service.deserialize(payload)
    board = TaskService(service._db).get_board_full(1)
    assert board is not None
    assert [label.name for label in board.columns[0].tasks[0].labels] == ["AdHoc"]
    assert [label.name for label in board.labels] == ["AdHoc"]


def test_deserialize_rejects_non_list_boards(service: ImportExportService) -> None:
    with pytest.raises(ValueError):
        service.deserialize({"version": 1, "boards": "nope"})


def test_import_json_rejects_non_object(tmp_path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("[1, 2, 3]", encoding="utf-8")
    with pytest.raises(ValueError):
        service = ImportExportService(create_database(tmp_path / "x.db"))
        service.import_json(bad)


def test_import_json_missing_file_raises(tmp_path) -> None:
    service = ImportExportService(create_database(tmp_path / "x.db"))
    with pytest.raises(FileNotFoundError):
        service.import_json(tmp_path / "does_not_exist.json")
