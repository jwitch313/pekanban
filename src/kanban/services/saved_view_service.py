"""Saved views service (F-25).

CRUD for named, reusable filter combinations. Filters are stored as a JSON
object so the UI can persist arbitrary filter state and re-apply it later.

Pure business logic with no GUI dependencies.
"""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from kanban.models import SavedView
from kanban.services.database import Database


class SavedViewService:
    """Create, list, update, and delete saved filter views."""

    def __init__(self, database: Database) -> None:
        self._db = database

    def create_view(self, name: str, filters: dict[str, Any] | None = None) -> SavedView:
        """Create a saved view with the given name and filter dict.

        Raises ``ValueError`` for a blank name, a non-dict filter payload, or a
        duplicate name.
        """
        name = self._clean_name(name)
        payload = self._encode(filters)
        with self._db.session() as session:
            if self._find_by_name(session, name) is not None:
                raise ValueError(f"A saved view named {name!r} already exists")
            view = SavedView(name=name, filter_json=payload)
            session.add(view)
            session.flush()
            return view

    def list_views(self) -> list[SavedView]:
        """Return all saved views ordered by name."""
        with self._db.session() as session:
            views = session.query(SavedView).order_by(SavedView.name).all()
            session.expunge_all()
            return views

    def get_view(self, view_id: int) -> SavedView:
        """Return a saved view by id, or raise ``LookupError``."""
        with self._db.session() as session:
            view = session.get(SavedView, view_id)
            if view is None:
                raise LookupError(f"Saved view {view_id} does not exist")
            session.expunge(view)
            return view

    def update_view(
        self,
        view_id: int,
        name: str | None = None,
        filters: dict[str, Any] | None = None,
    ) -> SavedView:
        """Update a saved view's name and/or filters.

        Only the supplied fields change. Raises ``LookupError`` when the view
        is missing and ``ValueError`` for a blank/duplicate name.
        """
        with self._db.session() as session:
            view = session.get(SavedView, view_id)
            if view is None:
                raise LookupError(f"Saved view {view_id} does not exist")
            if name is not None:
                clean = self._clean_name(name)
                existing = self._find_by_name(session, clean)
                if existing is not None and existing.id != view_id:
                    raise ValueError(f"A saved view named {clean!r} already exists")
                view.name = clean
            if filters is not None:
                view.filter_json = self._encode(filters)
            session.flush()
            return view

    def delete_view(self, view_id: int) -> None:
        """Delete a saved view, or raise ``LookupError`` when missing."""
        with self._db.session() as session:
            view = session.get(SavedView, view_id)
            if view is None:
                raise LookupError(f"Saved view {view_id} does not exist")
            session.delete(view)
            session.flush()

    def filters_for(self, view_id: int) -> dict[str, Any]:
        """Return the decoded filter dict for a saved view."""
        raw = json.loads(self.get_view(view_id).filter_json)
        if not isinstance(raw, dict):
            raise ValueError("stored filters are not a dict")
        return raw

    # -- Helpers ----------------------------------------------------------
    @staticmethod
    def _clean_name(name: str) -> str:
        clean = name.strip()
        if not clean:
            raise ValueError("Saved view name must not be blank")
        return clean

    @staticmethod
    def _encode(filters: dict[str, Any] | None) -> str:
        payload = filters if filters is not None else {}
        if not isinstance(payload, dict):
            raise ValueError("filters must be a dict")
        return json.dumps(payload)

    @staticmethod
    def _find_by_name(session: Session, name: str) -> SavedView | None:
        return session.query(SavedView).filter(SavedView.name == name).first()
