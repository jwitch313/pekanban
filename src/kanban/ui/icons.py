"""SVG-based icon factory for the KanBan UI.

Qt's built-in standard icons lack the specific glyphs the app needs (pencil,
tag, arrows, sun/moon). This module renders a small set of inline, Feather-style
SVG icons to :class:`QIcon` instances so every button carries a relevant, modern
glyph.

Icons are stroke-based and rendered in a neutral mid-gray that stays legible on
both the light and dark button backgrounds, so a single icon set works for both
themes without re-rendering on theme changes.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

#: Neutral stroke color legible on both light and dark button backgrounds.
DEFAULT_ICON_COLOR = "#8a8f98"

#: Feather-style icon paths (24x24 viewBox, stroke-based).
_ICON_PATHS: dict[str, str] = {
    "plus": "M12 5v14M5 12h14",
    "trash": (
        "M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"
        "M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6M10 11v6M14 11v6"
    ),
    "pencil": "M17 3a2.828 2.828 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z",
    "tag": "M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82zM7 7h.01",
    "arrow_left": "M19 12H5M12 19l-7-7 7-7",
    "arrow_right": "M5 12h14M12 5l7 7-7 7",
    "clear": "M18 6L6 18M6 6l12 12",
    "sun": (
        "M12 17a5 5 0 1 0 0-10 5 5 0 0 0 0 10z"
        "M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42"
        "M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"
    ),
    "moon": "M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z",
    "monitor": "M2 3h20v14H2zM8 21h8M12 17v4",
}

#: Rendered icons cached by (name, color, size) to avoid re-rendering.
_cache: dict[tuple[str, str, int], QIcon] = {}


def _svg_for(name: str, color: str) -> bytes:
    """Build the SVG document for ``name`` stroked in ``color``."""
    path = _ICON_PATHS[name]
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24">'
        f'<path d="{path}" fill="none" stroke="{color}" stroke-width="2" '
        'stroke-linecap="round" stroke-linejoin="round"/></svg>'
    )
    return svg.encode("utf-8")


def icon(name: str, color: str = DEFAULT_ICON_COLOR, size: int = 16) -> QIcon:
    """Return a rendered :class:`QIcon` for the named glyph.

    ``name`` must be a key in the built-in icon set. The icon is rendered at
    ``size`` pixels using ``color`` as the stroke color and cached for reuse.
    """
    if name not in _ICON_PATHS:
        raise KeyError(f"Unknown icon {name!r}")
    key = (name, color, size)
    cached = _cache.get(key)
    if cached is not None:
        return cached
    renderer = QSvgRenderer(_svg_for(name, color))
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    result = QIcon(pixmap)
    _cache[key] = result
    return result


def icon_names() -> list[str]:
    """Return the sorted names of all available icons."""
    return sorted(_ICON_PATHS)
