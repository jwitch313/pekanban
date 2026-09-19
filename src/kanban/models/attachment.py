"""File attachment ORM model.

Attachments reference files stored on disk; the DB keeps metadata only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from kanban.models.base import Base

if TYPE_CHECKING:
    from kanban.models.task import Task


class Attachment(Base):
    """Metadata for a file attached to a task."""

    __tablename__ = "attachments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    filepath: Mapped[str] = mapped_column(String(1000), nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(200), nullable=True)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

    task: Mapped[Task] = relationship("Task", back_populates="attachments")

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Attachment id={self.id} filename={self.filename!r}>"
