"""Recurrence ORM model.

Defines a recurrence pattern for a task so it can be auto-created on schedule.
"""

from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from kanban.models.base import Base

if TYPE_CHECKING:
    from kanban.models.task import Task


class RecurrencePattern(enum.Enum):
    """Supported recurrence cadences."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CUSTOM = "custom"


class Recurrence(Base):
    """A recurrence rule attached to a single task."""

    __tablename__ = "recurrences"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    pattern: Mapped[RecurrencePattern] = mapped_column(
        Enum(RecurrencePattern, values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        default=RecurrencePattern.DAILY,
    )
    next_run: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    disabled_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    task: Mapped[Task] = relationship("Task", back_populates="recurrence")

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Recurrence id={self.id} pattern={self.pattern}>"
