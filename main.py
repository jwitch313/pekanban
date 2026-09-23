"""PyInstaller entry point for the PeKanBan desktop app.

This thin wrapper exists so PyInstaller has a concrete file to analyse.
The real entry logic lives in :mod:`kanban.app`.
"""

from __future__ import annotations

from kanban.app import main

if __name__ == "__main__":
    raise SystemExit(main())
