"""Label ORM model and the task/label association table.

Labels are color-coded tags. A label may be scoped to a board (``board_id``
set) or global (``board_id`` is ``None``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Column, ForeignKey, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from kanban.models.base import Base

if TYPE_CHECKING:
    from kanban.models.board import Board
    from kanban.models.task import Task

# Many-to-many association table between tasks and labels.
task_labels = Table(
    "task_labels",
    Base.metadata,
    Column(
        "task_id",
        ForeignKey("tasks.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "label_id",
        ForeignKey("labels.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Label(Base):
    """A color-coded tag that can be applied to tasks."""

    __tablename__ = "labels"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    color: Mapped[str | None] = mapped_column(String(20), nullable=True)
    board_id: Mapped[int | None] = mapped_column(
        ForeignKey("boards.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    board: Mapped[Board | None] = relationship("Board", back_populates="labels")
    tasks: Mapped[list[Task]] = relationship(
        "Task",
        secondary=task_labels,
        back_populates="labels",
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Label id={self.id} name={self.name!r}>"
