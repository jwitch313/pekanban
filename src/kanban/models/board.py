"""Board ORM model.

A board is the top-level container for a set of columns and their tasks.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from kanban.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from kanban.models.column import BoardColumn
    from kanban.models.label import Label


class Board(Base, TimestampMixin):
    """A Kanban board containing an ordered set of columns."""

    __tablename__ = "boards"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    icon: Mapped[str | None] = mapped_column(String(50), nullable=True)
    color: Mapped[str | None] = mapped_column(String(20), nullable=True)

    columns: Mapped[list[BoardColumn]] = relationship(
        "BoardColumn",
        back_populates="board",
        cascade="all, delete-orphan",
        order_by="BoardColumn.order_idx",
    )
    labels: Mapped[list[Label]] = relationship(
        "Label",
        back_populates="board",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Board id={self.id} name={self.name!r}>"
