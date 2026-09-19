"""Tests for the ORM models and schema creation."""

from __future__ import annotations

from sqlalchemy import inspect

from kanban.models import Base, Board, BoardColumn, Priority, Task
from kanban.services.database import create_database

EXPECTED_TABLES = {
    "boards",
    "columns",
    "tasks",
    "subtasks",
    "labels",
    "task_labels",
    "attachments",
    "comments",
    "recurrences",
    "schema_version",
}


def test_all_tables_created(tmp_path) -> None:
    db = create_database(tmp_path / "t.db")
    db.init_db()
    tables = set(inspect(db.engine).get_table_names())
    assert EXPECTED_TABLES.issubset(tables)
    db.dispose()


def test_board_column_task_relationship() -> None:
    board = Board(name="Work")
    column = BoardColumn(title="To Do", order_idx=0)
    board.columns.append(column)
    task = Task(title="Write tests", priority=Priority.HIGH, order_idx=0)
    column.tasks.append(task)

    assert board.columns[0] is column
    assert column.tasks[0] is task
    assert task.column is column


def test_priority_enum_values() -> None:
    assert [p.value for p in Priority] == ["low", "medium", "high", "urgent"]


def test_base_metadata_contains_all_models() -> None:
    table_names = set(Base.metadata.tables)
    assert "boards" in table_names
    assert "tasks" in table_names
    assert "task_labels" in table_names
