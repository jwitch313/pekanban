"""Settings service (final UI polish).

Persists UI preferences so the app remembers the user's setup across launches:
theme, active view, last selected board, and window geometry.

Values are stored as strings in a key/value table. A small whitelist of known
keys and per-key validation keeps the store well-formed.

Pure business logic with no GUI dependencies.
"""

from __future__ import annotations

from kanban.models import Setting
from kanban.services.database import Database


class SettingsService:
    """Read and write validated application settings."""

    KNOWN_KEYS = frozenset(
        {"theme", "theme_mode", "active_view", "last_board_id", "window_geometry"}
    )
    VALID_THEME = frozenset({"light", "dark"})
    VALID_THEME_MODE = frozenset({"system", "light", "dark"})
    VALID_VIEW = frozenset({"kanban", "calendar", "gantt", "dashboard"})

    def __init__(self, database: Database) -> None:
        self._db = database

    def get(self, key: str, default: str | None = None) -> str | None:
        """Return the value for ``key``, or ``default`` when unset."""
        self._check_key(key)
        with self._db.session() as session:
            row = session.query(Setting).filter(Setting.key == key).first()
            return row.value if row is not None else default

    def set(self, key: str, value: str) -> None:
        """Set ``key`` to ``value``, validating the key and value."""
        self._check_key(key)
        self._validate(key, value)
        with self._db.session() as session:
            row = session.query(Setting).filter(Setting.key == key).first()
            if row is None:
                session.add(Setting(key=key, value=value))
            else:
                row.value = value
            session.flush()

    def delete(self, key: str) -> None:
        """Remove a setting; a no-op when the key is not currently set."""
        self._check_key(key)
        with self._db.session() as session:
            row = session.query(Setting).filter(Setting.key == key).first()
            if row is not None:
                session.delete(row)
            session.flush()

    def all(self) -> dict[str, str]:
        """Return every stored setting as a dict keyed by name."""
        with self._db.session() as session:
            rows = session.query(Setting).order_by(Setting.key).all()
            return {row.key: row.value for row in rows}

    def reset(self) -> None:
        """Clear all stored settings."""
        with self._db.session() as session:
            session.query(Setting).delete()
            session.flush()

    # -- Typed accessors --------------------------------------------------
    def theme(self) -> str:
        """Current theme (``light`` or ``dark``), defaulting to ``light``."""
        value = self.get("theme")
        return "light" if value is None else value

    def set_theme(self, mode: str) -> None:
        """Set the theme to ``light`` or ``dark``."""
        self.set("theme", mode)

    def theme_mode(self) -> str:
        """Theme preference (``system``, ``light``, or ``dark``).

        Defaults to ``system`` so the app follows the OS theme until the user
        explicitly overrides it.
        """
        value = self.get("theme_mode")
        return "system" if value is None else value

    def set_theme_mode(self, mode: str) -> None:
        """Set the theme preference to ``system``, ``light``, or ``dark``."""
        self.set("theme_mode", mode)

    def active_view(self) -> str:
        """Current view mode, defaulting to ``kanban``."""
        value = self.get("active_view")
        return "kanban" if value is None else value

    def set_active_view(self, view: str) -> None:
        """Set the active view to a known mode."""
        self.set("active_view", view)

    def last_board_id(self) -> int | None:
        """The last selected board id, or ``None`` when unset."""
        raw = self.get("last_board_id")
        return int(raw) if raw is not None else None

    def set_last_board_id(self, board_id: int | None) -> None:
        """Remember the last selected board, or clear it when ``None``."""
        if board_id is None:
            self.delete("last_board_id")
        else:
            self.set("last_board_id", str(board_id))

    def window_geometry(self) -> str | None:
        """The persisted window geometry string, or ``None`` when unset."""
        return self.get("window_geometry")

    def set_window_geometry(self, geometry: str) -> None:
        """Persist the window geometry string."""
        self.set("window_geometry", geometry)

    # -- Helpers ----------------------------------------------------------
    @classmethod
    def _check_key(cls, key: str) -> None:
        if key not in cls.KNOWN_KEYS:
            raise ValueError(f"Unknown setting {key!r}")

    @classmethod
    def _validate(cls, key: str, value: str) -> None:
        if key == "theme" and value not in cls.VALID_THEME:
            raise ValueError(f"Invalid theme {value!r}")
        if key == "theme_mode" and value not in cls.VALID_THEME_MODE:
            raise ValueError(f"Invalid theme mode {value!r}")
        if key == "active_view" and value not in cls.VALID_VIEW:
            raise ValueError(f"Invalid view {value!r}")
        if key == "last_board_id":
            int(value)  # raises ValueError when not an integer
