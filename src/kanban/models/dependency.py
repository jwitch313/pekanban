"""Task dependency ORM model.

A dependency means ``task`` is blocked by ``depends_on`` ("A blocks B").
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from kanban.models.base import Base

if TYPE_CHECKING:
    from kanban.models.task import Task


class Dependency(Base):
    """A directed edge: ``task`` cannot complete until ``depends_on`` does."""

    __tablename__ = "dependencies"
    __table_args__ = (UniqueConstraint("task_id", "depends_on_id", name="uq_dependency_pair"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    depends_on_id: Mapped[int] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    task: Mapped[Task] = relationship("Task", foreign_keys=[task_id])
    depends_on: Mapped[Task] = relationship("Task", foreign_keys=[depends_on_id])

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Dependency task={self.task_id} blocked_by={self.depends_on_id}>"
