"""Declarative base and shared mixins for all ORM models."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Declarative base class for all PeKanBan ORM models.

    All models inherit from this class so that ``Base.metadata`` contains the
    full schema for migrations and ``create_all``.
    """


class TimestampMixin:
    """Adds ``created_at`` and ``updated_at`` audit columns.

    All timestamps are stored in UTC. SQLite's ``CURRENT_TIMESTAMP`` is UTC,
    so the server defaults are consistent with application-side values.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
