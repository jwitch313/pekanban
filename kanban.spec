# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for the PeKanBan desktop app.

Builds a one-directory (``--onedir``) windowed executable. One-directory is
preferred over one-file for a Qt desktop app: it starts faster and avoids the
per-launch extraction cost of a self-extracting archive.

Usage:
    uv run pyinstaller kanban.spec
"""

from PyInstaller.utils.hooks import collect_all

# PySide6 ships data files, binaries, and hidden imports that PyInstaller's
# built-in hook already handles, but collecting explicitly keeps the build
# robust across PySide6 point releases.
datas, binaries, hiddenimports = collect_all("PySide6")

# Bundle the logo assets (window icon, wordmark) into the app folder.
datas += [("assets", "assets")]

# Bundle the user manual so the Help window can display it in the frozen build.
datas += [("docs", "docs")]

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="PeKanBan",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,  # windowed app — no console window
    disable_windowed_traceback=False,
    icon="assets/PeKanBan-icon.ico",  # custom app icon for the .exe
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="PeKanBan",
)
