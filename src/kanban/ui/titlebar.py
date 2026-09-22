"""Recolor the native Windows title bar to match the active theme.

Qt cannot recolor the native Windows title bar, but Windows 11 (build 22000+)
exposes ``DwmSetWindowAttribute`` with ``DWMWA_CAPTION_COLOR`` to do exactly
that while keeping the native window frame (resize, minimize, maximize, close).
This module wraps that call so it is safe to invoke on any platform and in
tests: it reports failure as ``False`` instead of raising when the API is
unavailable.
"""

from __future__ import annotations

import ctypes
import sys

#: DWM attribute id for the caption (title bar) color.
DWMWA_CAPTION_COLOR = 35


def hex_to_colorref(hex_color: str) -> int:
    """Convert a ``#RRGGBB`` hex string to a Windows ``COLORREF`` (``0x00BBGGRR``)."""
    value = hex_color.lstrip("#")
    if len(value) != 6:
        raise ValueError(f"Expected a #RRGGBB color, got {hex_color!r}")
    red = int(value[0:2], 16)
    green = int(value[2:4], 16)
    blue = int(value[4:6], 16)
    return (blue << 16) | (green << 8) | red


def set_title_bar_color(hwnd: int, hex_color: str) -> bool:
    """Recolor the native Windows title bar of the window with ``hwnd``.

    Returns ``True`` on success. Returns ``False`` (without raising) on
    non-Windows platforms, when the DWM API is unavailable, or when the call
    fails — so callers may invoke it unconditionally.
    """
    if sys.platform != "win32":
        return False
    try:
        dwmapi = ctypes.windll.dwmapi
        colorref = ctypes.c_uint(hex_to_colorref(hex_color))
        result = int(
            dwmapi.DwmSetWindowAttribute(
                ctypes.c_void_p(hwnd),
                ctypes.c_uint(DWMWA_CAPTION_COLOR),
                ctypes.byref(colorref),
                ctypes.sizeof(colorref),
            )
        )
    except (OSError, AttributeError, ValueError):
        return False
    return result == 0  # S_OK
