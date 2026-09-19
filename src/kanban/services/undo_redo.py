"""Undo/redo stack for task operations (F-23).

A small command-pattern layer on top of :class:`TaskService`. Each reversible
action is a :class:`Command` with ``do()`` and ``undo()`` methods. The
:class:`UndoRedoService` keeps an undo stack and a redo stack with a
configurable maximum depth, and clears the redo stack whenever a new action is
executed (standard editor semantics).

The service is pure business logic with no GUI dependencies, so it is fully
unit-testable. ``main_window.py`` wires ``Ctrl+Z`` / ``Ctrl+Y`` to it.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from kanban.models import Priority
from kanban.services.task_service import TaskService


@dataclass
class TaskSnapshot:
    """A copy of a task's mutable fields, enough to restore it later."""

    column_id: int
    title: str
    description: str | None
    priority: Priority
    due_date: date | None
    status_color: str | None
    order_idx: int
    label_ids: list[int] = field(default_factory=list)


def _snapshot_task(service: TaskService, task_id: int) -> TaskSnapshot:
    """Capture the current state of a task for later restoration."""
    task = service.get_task(task_id)
    if task is None:
        raise LookupError(f"Task {task_id} does not exist")
    return TaskSnapshot(
        column_id=task.column_id,
        title=task.title,
        description=task.description,
        priority=task.priority,
        due_date=task.due_date,
        status_color=task.status_color,
        order_idx=task.order_idx,
        label_ids=[label.id for label in task.labels],
    )


class Command(ABC):
    """A reversible operation applied through the task service."""

    @abstractmethod
    def do(self) -> None:
        """Apply the operation (or re-apply it on redo)."""

    @abstractmethod
    def undo(self) -> None:
        """Reverse the operation."""


class CreateTaskCommand(Command):
    """Create a task; undo deletes it."""

    def __init__(
        self,
        service: TaskService,
        column_id: int,
        title: str,
        description: str | None = None,
        priority: Priority = Priority.MEDIUM,
        due_date: date | None = None,
        status_color: str | None = None,
    ) -> None:
        self._service = service
        self._column_id = column_id
        self._title = title
        self._description = description
        self._priority = priority
        self._due_date = due_date
        self._status_color = status_color
        self._task_id: int | None = None

    def do(self) -> None:
        task = self._service.create_task(
            self._column_id,
            self._title,
            self._description,
            self._priority,
            self._due_date,
            self._status_color,
        )
        self._task_id = task.id

    def undo(self) -> None:
        if self._task_id is not None:
            self._service.delete_task(self._task_id)
            self._task_id = None


class DeleteTaskCommand(Command):
    """Delete a task; undo recreates it from a snapshot."""

    def __init__(self, service: TaskService, task_id: int) -> None:
        self._service = service
        self._task_id = task_id
        self._snapshot: TaskSnapshot | None = None

    def do(self) -> None:
        self._snapshot = _snapshot_task(self._service, self._task_id)
        self._service.delete_task(self._task_id)

    def undo(self) -> None:
        snapshot = self._snapshot
        if snapshot is None:
            return
        task = self._service.create_task(
            snapshot.column_id,
            snapshot.title,
            snapshot.description,
            snapshot.priority,
            snapshot.due_date,
            snapshot.status_color,
        )
        self._service.move_task(task.id, snapshot.column_id, snapshot.order_idx)
        for label_id in snapshot.label_ids:
            self._service.assign_label(task.id, label_id)
        self._snapshot = None


class MoveTaskCommand(Command):
    """Move a task to a column/position; undo restores the origin."""

    def __init__(
        self,
        service: TaskService,
        task_id: int,
        target_column_id: int,
        target_index: int,
    ) -> None:
        self._service = service
        self._task_id = task_id
        self._target_column_id = target_column_id
        self._target_index = target_index
        self._origin_column_id: int | None = None
        self._origin_index: int | None = None

    def do(self) -> None:
        if self._origin_column_id is None:
            task = self._service.get_task(self._task_id)
            if task is not None:
                self._origin_column_id = task.column_id
                self._origin_index = task.order_idx
        self._service.move_task(self._task_id, self._target_column_id, self._target_index)

    def undo(self) -> None:
        if self._origin_column_id is not None and self._origin_index is not None:
            self._service.move_task(
                self._task_id, self._origin_column_id, self._origin_index
            )


class EditTaskCommand(Command):
    """Apply field edits to a task; undo restores the previous values."""

    def __init__(self, service: TaskService, task_id: int, changes: dict[str, Any]) -> None:
        self._service = service
        self._task_id = task_id
        self._changes = dict(changes)
        self._previous: dict[str, Any] | None = None

    def do(self) -> None:
        if self._previous is None:
            task = self._service.get_task(self._task_id)
            if task is not None:
                self._previous = {key: getattr(task, key) for key in self._changes}
        self._service.update_task(self._task_id, **self._changes)

    def undo(self) -> None:
        if self._previous is not None:
            self._service.update_task(self._task_id, **self._previous)


class UndoRedoService:
    """Manages the undo/redo stacks for task operations."""

    def __init__(self, service: TaskService, max_depth: int = 50) -> None:
        if max_depth < 1:
            raise ValueError("max_depth must be at least 1")
        self._service = service
        self._max_depth = max_depth
        self._undo_stack: list[Command] = []
        self._redo_stack: list[Command] = []

    @property
    def max_depth(self) -> int:
        """The configured maximum number of undo steps retained."""
        return self._max_depth

    def execute(self, command: Command) -> None:
        """Run a command, push it onto the undo stack, and clear the redo stack."""
        command.do()
        self._undo_stack.append(command)
        if len(self._undo_stack) > self._max_depth:
            self._undo_stack.pop(0)
        self._redo_stack.clear()

    def can_undo(self) -> bool:
        """Return True if there is an action to undo."""
        return bool(self._undo_stack)

    def can_redo(self) -> bool:
        """Return True if there is an action to redo."""
        return bool(self._redo_stack)

    def undo(self) -> None:
        """Undo the most recent action, if any."""
        if not self._undo_stack:
            return
        command = self._undo_stack.pop()
        command.undo()
        self._redo_stack.append(command)

    def redo(self) -> None:
        """Redo the most recently undone action, if any."""
        if not self._redo_stack:
            return
        command = self._redo_stack.pop()
        command.do()
        self._undo_stack.append(command)

    def clear(self) -> None:
        """Discard all undo/redo history."""
        self._undo_stack.clear()
        self._redo_stack.clear()
