"""Task CRUD service.

Pure business logic with no GUI dependencies. All database access goes
through the :class:`~kanban.services.database.Database` session context
manager, so every operation is transactional.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import or_, select

from kanban.models import Board, BoardColumn, Label, Priority, Subtask, Task
from kanban.models.task import MAX_TITLE_LENGTH
from kanban.services.database import Database

#: Columns seeded on the starter board shown on first launch.
DEFAULT_COLUMNS: list[str] = ["To Do", "In Progress", "Completed", "Blocked"]

#: Placeholder card shown on the starter board so the UI is never empty.
PLACEHOLDER_TASK_TITLE = "Your Task"
PLACEHOLDER_TASK_DESCRIPTION = (
    "Add an optional description or note for your task. Set subtasks, a priority "
    "level and add a due date when needed. Create and edit boards, columns, tasks "
    "and labels that match your workflow. You may archive or delete your tasks "
    "when complete."
)


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

    def create_default_board(self, name: str = "My Board") -> Board:
        """Create the starter board with default columns and a placeholder task.

        Used only when the user has no existing boards (first launch or after
        deleting the last board) so the app never opens on an empty canvas.
        """
        with self._db.session() as session:
            board = Board(name=name)
            first_column: BoardColumn | None = None
            for order_idx, title in enumerate(DEFAULT_COLUMNS):
                column = BoardColumn(title=title, order_idx=order_idx)
                board.columns.append(column)
                if first_column is None:
                    first_column = column
            session.add(board)
            session.flush()
            assert first_column is not None
            task = Task(
                title=PLACEHOLDER_TASK_TITLE,
                description=PLACEHOLDER_TASK_DESCRIPTION,
                priority=Priority.MEDIUM,
                order_idx=0,
            )
            first_column.tasks.append(task)
            session.add(task)
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
            list(board.labels)
            for column in board.columns:
                for task in column.tasks:
                    list(task.labels)
                    list(task.subtasks)
            return board

    def rename_board(self, board_id: int, name: str) -> Board:
        """Rename a board."""
        with self._db.session() as session:
            board = session.get(Board, board_id)
            if board is None:
                raise LookupError(f"Board {board_id} does not exist")
            board.name = name
            session.flush()
            return board

    def delete_board(self, board_id: int) -> None:
        """Delete a board and everything it contains (columns, tasks, labels)."""
        with self._db.session() as session:
            board = session.get(Board, board_id)
            if board is None:
                raise LookupError(f"Board {board_id} does not exist")
            session.delete(board)
            session.flush()

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

    def rename_column(self, column_id: int, title: str) -> BoardColumn:
        """Rename a column."""
        with self._db.session() as session:
            column = session.get(BoardColumn, column_id)
            if column is None:
                raise LookupError(f"Column {column_id} does not exist")
            column.title = title
            session.flush()
            return column

    def move_column(self, column_id: int, new_order_idx: int) -> BoardColumn:
        """Reorder a column within its board, clamping the index to the valid range."""
        with self._db.session() as session:
            column = session.get(BoardColumn, column_id)
            if column is None:
                raise LookupError(f"Column {column_id} does not exist")
            ordered = [
                c
                for c in sorted(column.board.columns, key=lambda c: c.order_idx)
                if c.id != column.id
            ]
            index = max(0, min(new_order_idx, len(ordered)))
            ordered.insert(index, column)
            for new_idx, c in enumerate(ordered):
                c.order_idx = new_idx
            session.flush()
            return column

    def delete_column(self, column_id: int) -> None:
        """Delete a column and its tasks, then renumber the remaining columns."""
        with self._db.session() as session:
            column = session.get(BoardColumn, column_id)
            if column is None:
                raise LookupError(f"Column {column_id} does not exist")
            remaining = [
                c
                for c in sorted(column.board.columns, key=lambda c: c.order_idx)
                if c.id != column.id
            ]
            session.delete(column)
            session.flush()
            for new_idx, c in enumerate(remaining):
                c.order_idx = new_idx
            session.flush()

    # -- Labels -----------------------------------------------------------
    def create_label(self, board_id: int, name: str, color: str | None = None) -> Label:
        """Create a label scoped to a board."""
        with self._db.session() as session:
            board = session.get(Board, board_id)
            if board is None:
                raise LookupError(f"Board {board_id} does not exist")
            label = Label(name=name, color=color, board_id=board.id)
            session.add(label)
            session.flush()
            return label

    def list_labels(self, board_id: int) -> list[Label]:
        """Return all labels scoped to a board, ordered by id."""
        with self._db.session() as session:
            board = session.get(Board, board_id)
            if board is None:
                return []
            return list(board.labels)

    def delete_label(self, label_id: int) -> None:
        """Delete a label and remove it from any tasks that reference it."""
        with self._db.session() as session:
            label = session.get(Label, label_id)
            if label is None:
                raise LookupError(f"Label {label_id} does not exist")
            session.delete(label)
            session.flush()

    def assign_label(self, task_id: int, label_id: int) -> Task:
        """Attach a label to a task (idempotent)."""
        with self._db.session() as session:
            task = session.get(Task, task_id)
            if task is None:
                raise LookupError(f"Task {task_id} does not exist")
            label = session.get(Label, label_id)
            if label is None:
                raise LookupError(f"Label {label_id} does not exist")
            if label not in task.labels:
                task.labels.append(label)
            session.flush()
            return task

    def unassign_label(self, task_id: int, label_id: int) -> Task:
        """Detach a label from a task (idempotent)."""
        with self._db.session() as session:
            task = session.get(Task, task_id)
            if task is None:
                raise LookupError(f"Task {task_id} does not exist")
            label = session.get(Label, label_id)
            if label is None:
                raise LookupError(f"Label {label_id} does not exist")
            if label in task.labels:
                task.labels.remove(label)
            session.flush()
            return task

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
                title=title[:MAX_TITLE_LENGTH],
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
        """Return a task by id, or ``None`` if it does not exist.

        The label relationship is loaded inside the session so the returned
        object remains usable after the session closes.
        """
        with self._db.session() as session:
            task = session.get(Task, task_id)
            if task is not None:
                list(task.labels)
            return task

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
                if key == "title" and isinstance(value, str):
                    value = value[:MAX_TITLE_LENGTH]
                setattr(task, key, value)
            session.flush()
            return task

    def move_task(self, task_id: int, target_column_id: int, order_idx: int) -> Task:
        """Move a task to a new column and position (drag-and-drop support).

        The target column is renumbered so the task lands at ``order_idx``
        (clamped to the valid range), and the source column is renumbered to
        close the gap left behind. The foreign key is reassigned directly so
        the ``delete-orphan`` cascade on the column's task collection is not
        triggered.
        """
        with self._db.session() as session:
            task = session.get(Task, task_id)
            if task is None:
                raise LookupError(f"Task {task_id} does not exist")
            target = session.get(BoardColumn, target_column_id)
            if target is None:
                raise LookupError(f"Column {target_column_id} does not exist")

            source_id = task.column_id

            # Build the target ordering excluding the moved task, then insert
            # it at the clamped index.
            target_ids = [t.id for t in target.tasks if t.id != task.id]
            index = max(0, min(order_idx, len(target_ids)))
            target_ids.insert(index, task.id)

            task.column_id = target.id
            for new_idx, tid in enumerate(target_ids):
                if tid == task.id:
                    task.order_idx = new_idx
                else:
                    other = session.get(Task, tid)
                    if other is not None:
                        other.order_idx = new_idx

            # Close the gap in the source column when the task changed lanes.
            if source_id != target.id:
                source = session.get(BoardColumn, source_id)
                if source is not None:
                    for new_idx, other in enumerate(t for t in source.tasks if t.id != task.id):
                        other.order_idx = new_idx

            session.flush()
            return task

    def delete_task(self, task_id: int) -> None:
        """Delete a task and its dependent rows."""
        with self._db.session() as session:
            task = session.get(Task, task_id)
            if task is None:
                raise LookupError(f"Task {task_id} does not exist")
            session.delete(task)

    def archive_task(self, task_id: int) -> Task:
        """Mark a task as archived and return it."""
        with self._db.session() as session:
            task = session.get(Task, task_id)
            if task is None:
                raise LookupError(f"Task {task_id} does not exist")
            task.archived = True
            session.flush()
            return task

    def restore_task(self, task_id: int) -> Task:
        """Clear a task's archived flag and return it."""
        with self._db.session() as session:
            task = session.get(Task, task_id)
            if task is None:
                raise LookupError(f"Task {task_id} does not exist")
            task.archived = False
            session.flush()
            return task

    def list_archived_tasks(self, board_id: int) -> list[Task]:
        """Return all archived tasks on a board, ordered by column then position.

        Relationships are loaded inside the session so the returned objects
        remain usable after the session closes.
        """
        with self._db.session() as session:
            board = session.get(Board, board_id)
            if board is None:
                return []
            tasks = [t for c in board.columns for t in c.tasks if t.archived]
            for task in tasks:
                list(task.labels)
                list(task.subtasks)
            return tasks

    # -- Sub-tasks --------------------------------------------------------
    def add_subtask(self, task_id: int, title: str) -> Subtask:
        """Append a sub-task to a task, ordered after existing sub-tasks."""
        with self._db.session() as session:
            task = session.get(Task, task_id)
            if task is None:
                raise LookupError(f"Task {task_id} does not exist")
            subtask = Subtask(
                title=title,
                completed=False,
                order_idx=len(task.subtasks),
            )
            task.subtasks.append(subtask)
            session.add(subtask)
            session.flush()
            return subtask

    def list_subtasks(self, task_id: int) -> list[Subtask]:
        """Return a task's sub-tasks ordered by their position."""
        with self._db.session() as session:
            task = session.get(Task, task_id)
            if task is None:
                raise LookupError(f"Task {task_id} does not exist")
            return list(task.subtasks)

    def toggle_subtask(self, subtask_id: int) -> Subtask:
        """Flip a sub-task's completed flag and return it."""
        with self._db.session() as session:
            subtask = session.get(Subtask, subtask_id)
            if subtask is None:
                raise LookupError(f"Subtask {subtask_id} does not exist")
            subtask.completed = not subtask.completed
            session.flush()
            return subtask

    def delete_subtask(self, subtask_id: int) -> None:
        """Delete a sub-task and renumber the remaining sub-tasks."""
        with self._db.session() as session:
            subtask = session.get(Subtask, subtask_id)
            if subtask is None:
                raise LookupError(f"Subtask {subtask_id} does not exist")
            task_id = subtask.task_id
            session.delete(subtask)
            session.flush()
            task = session.get(Task, task_id)
            if task is not None:
                for new_idx, remaining in enumerate(task.subtasks):
                    remaining.order_idx = new_idx
                session.flush()

    # -- Search -----------------------------------------------------------
    def search_tasks(
        self,
        board_id: int,
        query: str = "",
        priority: Priority | None = None,
        column_id: int | None = None,
        due_before: date | None = None,
        due_after: date | None = None,
        label_id: int | None = None,
    ) -> list[Task]:
        """Return tasks on a board matching the supplied filters.

        All filters are optional and combined with ``AND``. ``query`` matches
        the task title or description (case-insensitive). Results are ordered
        by column position, then task position.
        """
        with self._db.session() as session:
            stmt = (
                select(Task)
                .join(BoardColumn, Task.column_id == BoardColumn.id)
                .where(BoardColumn.board_id == board_id)
            )
            if query:
                like = f"%{query}%"
                stmt = stmt.where(or_(Task.title.ilike(like), Task.description.ilike(like)))
            if priority is not None:
                stmt = stmt.where(Task.priority == priority)
            if column_id is not None:
                stmt = stmt.where(Task.column_id == column_id)
            if due_before is not None:
                stmt = stmt.where(Task.due_date <= due_before)
            if due_after is not None:
                stmt = stmt.where(Task.due_date >= due_after)
            if label_id is not None:
                stmt = stmt.where(Task.labels.any(Label.id == label_id))
            stmt = stmt.order_by(BoardColumn.order_idx, Task.order_idx)
            results = session.execute(stmt).scalars().all()
            return list(results)
