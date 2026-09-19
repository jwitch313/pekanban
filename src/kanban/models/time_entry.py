"""Time-entry ORM model.

A time entry records one interval of tracked work against a task. While a
timer is running the entry's ``ended_at`` is ``None``; pausing or stopping
closes the interval by setting ``ended_at``.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from kanban.models.base import Base

if TYPE_CHECKING:
    from kanban.models.task import Task


class TimeEntry(Base):
    """A single tracked interval of work on a task."""

    __tablename__ = "time_entries"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    paused: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    task: Mapped[Task] = relationship("Task", back_populates="time_entries")

    @property
    def is_running(self) -> bool:
        """Whether this interval is still open (timer running)."""
        return self.ended_at is None

    @property
    def duration_seconds(self) -> float:
        """Elapsed seconds for this interval (open intervals count to now)."""
        end = self.ended_at
        if end is None:
            return 0.0
        return max(0.0, (end - self.started_at).total_seconds())

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<TimeEntry id={self.id} task_id={self.task_id} running={self.is_running}>"
