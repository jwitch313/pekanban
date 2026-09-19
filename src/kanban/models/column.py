"""Board column ORM model.

A column is an ordered lane within a board (e.g. "To Do", "In Progress").
The class is named ``BoardColumn`` to avoid shadowing SQLAlchemy's ``Column``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from kanban.models.base import Base

if TYPE_CHECKING:
    from kanban.models.board import Board
    from kanban.models.task import Task


class BoardColumn(Base):
    """An ordered column within a board."""

    __tablename__ = "columns"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    board_id: Mapped[int] = mapped_column(
        ForeignKey("boards.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    icon: Mapped[str | None] = mapped_column(String(50), nullable=True)
    color: Mapped[str | None] = mapped_column(String(20), nullable=True)
    order_idx: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    board: Mapped[Board] = relationship("Board", back_populates="columns")
    tasks: Mapped[list[Task]] = relationship(
        "Task",
        back_populates="column",
        cascade="all, delete-orphan",
        order_by="Task.order_idx",
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<BoardColumn id={self.id} title={self.title!r}>"
