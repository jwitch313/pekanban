"""Saved view ORM model.

A saved view captures a named filter combination (stored as JSON) so the user
can quickly toggle between saved filter states (F-25).
"""

from __future__ import annotations

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from kanban.models.base import Base, TimestampMixin


class SavedView(Base, TimestampMixin):
    """A named, reusable filter combination."""

    __tablename__ = "saved_views"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True, index=True)
    filter_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<SavedView id={self.id} name={self.name!r}>"
