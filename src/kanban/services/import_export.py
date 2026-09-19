"""JSON import/export service.

Provides a full backup/restore of every board, column, task, and label
including their relationships. :meth:`ImportExportService.serialize` produces
a plain-JSON-serializable dict; :meth:`ImportExportService.deserialize`
rebuilds that data inside a single transaction so a restore is atomic.

The on-disk format is versioned (``SCHEMA_VERSION``) so future schema changes
can be handled with forward-compatible readers.
"""

from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from kanban.models import Board, BoardColumn, Label, Priority, Task
from kanban.services.database import Database

SCHEMA_VERSION = 1

#: Column order for CSV export/import. ``labels`` are joined with ``;``.
CSV_HEADER = [
    "board",
    "column",
    "title",
    "description",
    "priority",
    "due_date",
    "status_color",
    "completed",
    "labels",
]


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

    # -- CSV --------------------------------------------------------------
    def export_csv(self, path: str | Path) -> Path:
        """Write every task as a flat CSV row to ``path`` and return the path.

        Each row carries its board and column names so the file is self-
        describing; labels are joined with ``;``.
        """
        payload = self.serialize()
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=CSV_HEADER)
            writer.writeheader()
            for board_data in payload["boards"]:
                for column_data in board_data["columns"]:
                    for task_data in column_data["tasks"]:
                        writer.writerow(
                            {
                                "board": board_data["name"],
                                "column": column_data["title"],
                                "title": task_data["title"],
                                "description": task_data["description"] or "",
                                "priority": task_data["priority"],
                                "due_date": task_data["due_date"] or "",
                                "status_color": task_data["status_color"] or "",
                                "completed": "true" if task_data["completed"] else "false",
                                "labels": ";".join(task_data["labels"]),
                            }
                        )
        return target

    def import_csv(self, path: str | Path) -> None:
        """Read a CSV file and import its rows into the database.

        Boards, columns, and labels are matched by name and created on demand
        (find-or-create), so a CSV can be imported into an empty or existing
        database. Rows without a title are skipped.
        """
        source = Path(path)
        with source.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            rows = list(reader)

        with self._db.session() as session:
            for row in rows:
                title = (row.get("title") or "").strip()
                if not title:
                    continue
                board = self._find_or_create_board(session, row.get("board"))
                column = self._find_or_create_column(session, board, row.get("column"))
                task = Task(
                    title=title,
                    description=(row.get("description") or "").strip() or None,
                    priority=self._parse_priority(row.get("priority")),
                    due_date=self._parse_date(row.get("due_date")),
                    status_color=(row.get("status_color") or "").strip() or None,
                    completed=self._parse_bool(row.get("completed")),
                    order_idx=len(column.tasks),
                )
                column.tasks.append(task)
                session.add(task)
                session.flush()
                for label_name in self._split_labels(row.get("labels")):
                    task.labels.append(self._find_or_create_label(session, board, label_name))

    @staticmethod
    def _find_or_create_board(session: Session, name: Any) -> Board:
        """Return the board with the given name, creating it if absent."""
        board_name = (name or "").strip() or "Untitled"
        board = session.execute(select(Board).where(Board.name == board_name)).scalar_one_or_none()
        if board is None:
            board = Board(name=board_name)
            session.add(board)
            session.flush()
        return board

    @staticmethod
    def _find_or_create_column(session: Session, board: Board, title: Any) -> BoardColumn:
        """Return the board's column with the given title, creating it if absent."""
        column_title = (title or "").strip() or "Column"
        for column in board.columns:
            if column.title == column_title:
                return column
        column = BoardColumn(title=column_title, order_idx=len(board.columns))
        board.columns.append(column)
        session.add(column)
        session.flush()
        return column

    @staticmethod
    def _find_or_create_label(session: Session, board: Board, name: str) -> Label:
        """Return the board's label with the given name, creating it if absent."""
        for label in board.labels:
            if label.name == name:
                return label
        label = Label(name=name, board_id=board.id)
        session.add(label)
        session.flush()
        return label

    @staticmethod
    def _parse_bool(value: Any) -> bool:
        """Coerce a CSV boolean cell to a Python bool."""
        if value is None:
            return False
        return str(value).strip().lower() in {"1", "true", "yes", "y", "t"}

    @staticmethod
    def _split_labels(value: Any) -> list[str]:
        """Split a ``;``-joined label cell into a clean list of names."""
        if value is None:
            return []
        return [part.strip() for part in str(value).split(";") if part.strip()]
