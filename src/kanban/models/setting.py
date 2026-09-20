"""Application settings ORM model.

A key/value row for persisting UI preferences (theme, active view, last board,
window geometry) so the app remembers the user's setup across launches.
"""

from __future__ import annotations

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from kanban.models.base import Base


class Setting(Base):
    """A single persisted application setting."""

    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Setting key={self.key!r}>"
