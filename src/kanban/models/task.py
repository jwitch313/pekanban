"""Task ORM model and priority enum.

A task is a card that lives inside a column. It carries the core Kanban
metadata: title, description, priority, due date and status color.
"""

from __future__ import annotations

import enum
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from kanban.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from kanban.models.attachment import Attachment
    from kanban.models.column import BoardColumn
    from kanban.models.comment import Comment
    from kanban.models.label import Label
    from kanban.models.recurrence import Recurrence
    from kanban.models.subtask import Subtask


class Priority(enum.Enum):
    """Task priority levels, ordered from least to most urgent."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class Task(Base, TimestampMixin):
    """A single Kanban card within a column."""

    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    column_id: Mapped[int] = mapped_column(
        ForeignKey("columns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    priority: Mapped[Priority] = mapped_column(
        Enum(Priority, values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        default=Priority.MEDIUM,
        index=True,
    )
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    status_color: Mapped[str | None] = mapped_column(String(20), nullable=True)
    order_idx: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    column: Mapped[BoardColumn] = relationship("BoardColumn", back_populates="tasks")
    subtasks: Mapped[list[Subtask]] = relationship(
        "Subtask",
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="Subtask.order_idx",
    )
    labels: Mapped[list[Label]] = relationship(
        "Label",
        secondary="task_labels",
        back_populates="tasks",
    )
    attachments: Mapped[list[Attachment]] = relationship(
        "Attachment",
        back_populates="task",
        cascade="all, delete-orphan",
    )
    comments: Mapped[list[Comment]] = relationship(
        "Comment",
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="Comment.created_at",
    )
    recurrence: Mapped[Recurrence | None] = relationship(
        "Recurrence",
        back_populates="task",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Task id={self.id} title={self.title!r} priority={self.priority}>"
