"""ORM models for the KanBan application.

Importing this package registers every model on ``Base.metadata`` so that
migrations and ``create_all`` see the full schema.
"""

from __future__ import annotations

from kanban.models.attachment import Attachment
from kanban.models.base import Base, TimestampMixin
from kanban.models.board import Board
from kanban.models.column import BoardColumn
from kanban.models.comment import Comment
from kanban.models.label import Label, task_labels
from kanban.models.recurrence import Recurrence, RecurrencePattern
from kanban.models.subtask import Subtask
from kanban.models.task import Priority, Task
from kanban.models.time_entry import TimeEntry

__all__ = [
    "Attachment",
    "Base",
    "Board",
    "BoardColumn",
    "Comment",
    "Label",
    "Priority",
    "Recurrence",
    "RecurrencePattern",
    "Subtask",
    "Task",
    "TimeEntry",
    "TimestampMixin",
    "task_labels",
]
