"""Task CRUD service.

Pure business logic with no GUI dependencies. All database access goes
through the :class:`~kanban.services.database.Database` session context
manager, so every operation is transactional.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import select

from kanban.models import Board, BoardColumn, Priority, Task
from kanban.services.database import Database


class TaskService:
    """High-level CRUD operations for boards, columns, and tasks."""

    def __init__(self, database: Database) -> None:
        self._db = database

    # -- Boards -----------------------------------------------------------
    def create_board(self, name: str, icon: str | None = None, color: str | None = None) -> Board:
        """Create a new board with a default 'To Do' column."""
        with self._db.session() as session:
            board = Board(name=name, icon=icon, color=color)
            board.columns.append(BoardColumn(title="To Do", order_idx=0))
            session.add(board)
            session.flush()
            return board

    def get_board(self, board_id: int) -> Board | None:
        """Return a board by id, or ``None`` if it does not exist."""
        with self._db.session() as session:
            return session.get(Board, board_id)

    def list_boards(self) -> list[Board]:
        """Return all boards ordered by id."""
        with self._db.session() as session:
            boards = session.execute(select(Board).order_by(Board.id)).scalars().all()
            return list(boards)

    def get_board_full(self, board_id: int) -> Board | None:
        """Return a board with its columns and tasks loaded for display.

        Relationships are loaded inside the session so the returned objects
        remain usable after the session closes (``expire_on_commit=False``).
        """
        with self._db.session() as session:
            board = session.get(Board, board_id)
            if board is None:
                return None
            for column in board.columns:
                list(column.tasks)
            return board

    # -- Columns ----------------------------------------------------------
    def create_column(
        self,
        board_id: int,
        title: str,
        icon: str | None = None,
        color: str | None = None,
    ) -> BoardColumn:
        """Append a new column to a board, ordered after existing columns."""
        with self._db.session() as session:
            board = session.get(Board, board_id)
            if board is None:
                raise LookupError(f"Board {board_id} does not exist")
            next_order = len(board.columns)
            column = BoardColumn(title=title, icon=icon, color=color, order_idx=next_order)
            board.columns.append(column)
            session.add(column)
            session.flush()
            return column

    # -- Tasks ------------------------------------------------------------
    def create_task(
        self,
        column_id: int,
        title: str,
        description: str | None = None,
        priority: Priority = Priority.MEDIUM,
        due_date: date | None = None,
        status_color: str | None = None,
    ) -> Task:
        """Create a task at the end of the given column."""
        with self._db.session() as session:
            column = session.get(BoardColumn, column_id)
            if column is None:
                raise LookupError(f"Column {column_id} does not exist")
            task = Task(
                title=title,
                description=description,
                priority=priority,
                due_date=due_date,
                status_color=status_color,
                order_idx=len(column.tasks),
            )
            column.tasks.append(task)
            session.add(task)
            session.flush()
            return task

    def get_task(self, task_id: int) -> Task | None:
        """Return a task by id, or ``None`` if it does not exist."""
        with self._db.session() as session:
            return session.get(Task, task_id)

    def list_tasks_in_column(self, column_id: int) -> list[Task]:
        """Return all tasks in a column, ordered by their position."""
        with self._db.session() as session:
            column = session.get(BoardColumn, column_id)
            if column is None:
                return []
            return list(column.tasks)

    def update_task(self, task_id: int, **fields: Any) -> Task:
        """Update mutable fields on a task and return the updated object."""
        with self._db.session() as session:
            task = session.get(Task, task_id)
            if task is None:
                raise LookupError(f"Task {task_id} does not exist")
            for key, value in fields.items():
                if not hasattr(task, key):
                    raise ValueError(f"Task has no field {key!r}")
                setattr(task, key, value)
            session.flush()
            return task

    def move_task(self, task_id: int, target_column_id: int, order_idx: int) -> Task:
        """Move a task to a new column and position (drag-and-drop support)."""
        with self._db.session() as session:
            task = session.get(Task, task_id)
            if task is None:
                raise LookupError(f"Task {task_id} does not exist")
            target = session.get(BoardColumn, target_column_id)
            if target is None:
                raise LookupError(f"Column {target_column_id} does not exist")
            # Reassign the foreign key directly; manipulating the column's
            # task collection would trigger the delete-orphan cascade.
            task.column_id = target.id
            task.order_idx = order_idx
            session.flush()
            return task

    def delete_task(self, task_id: int) -> None:
        """Delete a task and its dependent rows."""
        with self._db.session() as session:
            task = session.get(Task, task_id)
            if task is None:
                raise LookupError(f"Task {task_id} does not exist")
            session.delete(task)
