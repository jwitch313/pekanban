"""Asset location helpers for the PeKanBan application.

The application ships image assets (the logo and window icon) in the
repository's top-level ``assets/`` folder. At runtime the folder is located
relative to this package during development, or inside the PyInstaller
bundle (``sys._MEIPASS``) when frozen.
"""

from __future__ import annotations

import sys
from pathlib import Path


def asset_dir() -> Path:
    """Return the directory containing the application's assets."""
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass is not None:
        return Path(meipass) / "assets"
    # src/kanban/assets.py -> parents[2] is the repository root.
    return Path(__file__).resolve().parents[2] / "assets"


def asset_path(name: str) -> Path:
    """Return the path of a bundled asset file, e.g. ``logo-icon.svg``."""
    return asset_dir() / name
