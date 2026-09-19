"""JSON import/export service.

Provides a full backup/restore of every board, column, task, and label
including their relationships. :meth:`ImportExportService.serialize` produces
a plain-JSON-serializable dict; :meth:`ImportExportService.deserialize`
rebuilds that data inside a single transaction so a restore is atomic.

The on-disk format is versioned (``SCHEMA_VERSION``) so future schema changes
can be handled with forward-compatible readers.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from sqlalchemy import select

from kanban.models import Board, BoardColumn, Label, Priority, Task
from kanban.services.database import Database

SCHEMA_VERSION = 1


class ImportExportService:
    """Serialize and restore the full Kanban data model to/from JSON."""

    def __init__(self, database: Database) -> None:
        self._db = database

    # -- Serialization ----------------------------------------------------
    def serialize(self) -> dict[str, Any]:
        """Return a JSON-serializable snapshot of all boards and their data."""
        with self._db.session() as session:
            boards = session.execute(select(Board).order_by(Board.id)).scalars().all()
            payload: dict[str, Any] = {"version": SCHEMA_VERSION, "boards": []}
            for board in boards:
                board_dict: dict[str, Any] = {
                    "name": board.name,
                    "icon": board.icon,
                    "color": board.color,
                    "labels": [
                        {"name": label.name, "color": label.color} for label in board.labels
                    ],
                    "columns": [],
                }
                for column in board.columns:
                    column_dict: dict[str, Any] = {
                        "title": column.title,
                        "icon": column.icon,
                        "color": column.color,
                        "tasks": [self._serialize_task(task) for task in column.tasks],
                    }
                    board_dict["columns"].append(column_dict)
                payload["boards"].append(board_dict)
            return payload

    @staticmethod
    def _serialize_task(task: Task) -> dict[str, Any]:
        """Serialize a single task, including its label names."""
        return {
            "title": task.title,
            "description": task.description,
            "priority": task.priority.value,
            "due_date": task.due_date.isoformat() if task.due_date is not None else None,
            "status_color": task.status_color,
            "completed": task.completed,
            "labels": [label.name for label in task.labels],
        }

    # -- Deserialization --------------------------------------------------
    def deserialize(self, data: dict[str, Any]) -> None:
        """Rebuild boards, columns, tasks, and labels from a serialized snapshot.

        Runs inside a single transaction: either the whole snapshot is applied
        or nothing is, so a restore never leaves a half-imported state.
        """
        boards_data = data.get("boards", [])
        if not isinstance(boards_data, list):
            raise ValueError("Invalid backup: 'boards' must be a list")

        with self._db.session() as session:
            for board_data in boards_data:
                if not isinstance(board_data, dict):
                    raise ValueError("Invalid backup: each board must be an object")
                board = Board(
                    name=str(board_data.get("name") or "Untitled"),
                    icon=board_data.get("icon"),
                    color=board_data.get("color"),
                )
                session.add(board)
                session.flush()

                # Board-scoped labels, keyed by name for task assignment.
                label_map: dict[str, Label] = {}
                for label_data in board_data.get("labels", []):
                    if not isinstance(label_data, dict):
                        continue
                    name = str(label_data.get("name") or "")
                    if not name:
                        continue
                    label = Label(name=name, color=label_data.get("color"), board_id=board.id)
                    session.add(label)
                    session.flush()
                    label_map[name] = label

                columns_data = board_data.get("columns", [])
                if not isinstance(columns_data, list):
                    raise ValueError("Invalid backup: 'columns' must be a list")
                for order_idx, column_data in enumerate(columns_data):
                    if not isinstance(column_data, dict):
                        raise ValueError("Invalid backup: each column must be an object")
                    column = BoardColumn(
                        title=str(column_data.get("title") or "Column"),
                        icon=column_data.get("icon"),
                        color=column_data.get("color"),
                        order_idx=order_idx,
                    )
                    board.columns.append(column)
                    session.add(column)
                    session.flush()

                    tasks_data = column_data.get("tasks", [])
                    if not isinstance(tasks_data, list):
                        raise ValueError("Invalid backup: 'tasks' must be a list")
                    for task_order, task_data in enumerate(tasks_data):
                        if not isinstance(task_data, dict):
                            raise ValueError("Invalid backup: each task must be an object")
                        task = Task(
                            title=str(task_data.get("title") or "Untitled"),
                            description=task_data.get("description"),
                            priority=self._parse_priority(task_data.get("priority")),
                            due_date=self._parse_date(task_data.get("due_date")),
                            status_color=task_data.get("status_color"),
                            completed=bool(task_data.get("completed", False)),
                            order_idx=task_order,
                        )
                        column.tasks.append(task)
                        session.add(task)
                        session.flush()

                        for label_name in task_data.get("labels", []):
                            name = str(label_name)
                            task_label = label_map.get(name)
                            if task_label is None:
                                task_label = Label(name=name, board_id=board.id)
                                session.add(task_label)
                                session.flush()
                                label_map[name] = task_label
                            task.labels.append(task_label)

    @staticmethod
    def _parse_priority(value: Any) -> Priority:
        """Coerce a serialized priority value, falling back to MEDIUM."""
        if value is None:
            return Priority.MEDIUM
        try:
            return Priority(str(value))
        except ValueError:
            return Priority.MEDIUM

    @staticmethod
    def _parse_date(value: Any) -> date | None:
        """Coerce an ISO-8601 date string, returning ``None`` when invalid."""
        if value is None or value == "":
            return None
        try:
            return date.fromisoformat(str(value))
        except ValueError:
            return None

    # -- File I/O ---------------------------------------------------------
    def export_json(self, path: str | Path) -> Path:
        """Write a full JSON backup to ``path`` and return the resolved path."""
        payload = self.serialize()
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return target

    def import_json(self, path: str | Path) -> None:
        """Read a JSON backup from ``path`` and restore it into the database."""
        source = Path(path)
        data = json.loads(source.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("Invalid JSON backup: expected a top-level object")
        self.deserialize(data)
