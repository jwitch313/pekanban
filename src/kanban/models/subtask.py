"""Sub-task ORM model.

A sub-task is a child item within a parent task, used to break work down.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from kanban.models.base import Base

if TYPE_CHECKING:
    from kanban.models.task import Task


class Subtask(Base):
    """An ordered child task within a parent task."""

    __tablename__ = "subtasks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    order_idx: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    task: Mapped[Task] = relationship("Task", back_populates="subtasks")

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Subtask id={self.id} title={self.title!r} completed={self.completed}>"
