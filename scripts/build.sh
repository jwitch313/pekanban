#!/usr/bin/env bash
# build.sh — Build the KanBan executable with PyInstaller (cross-platform dev).
#
# Usage (from the repository root):
#   bash scripts/build.sh
#
# Output: dist/KanBan/KanBan(.exe)  (one-directory layout)
#
# Prerequisites:
#   - uv installed and on PATH
#   - `uv sync` has been run (installs PySide6, SQLAlchemy, PyInstaller)

set -euo pipefail

echo "==> Syncing dependencies (uv sync)..."
uv sync

echo "==> Building executable (pyinstaller kanban.spec)..."
uv run pyinstaller kanban.spec --noconfirm

if [[ -f dist/KanBan/KanBan.exe ]]; then
    echo "==> Build complete."
    echo "    Executable: dist/KanBan/KanBan.exe"
    echo "    Folder:     dist/KanBan — copy the whole folder to deploy."
elif [[ -f dist/KanBan/KanBan ]]; then
    echo "==> Build complete."
    echo "    Executable: dist/KanBan/KanBan"
    echo "    Folder:     dist/KanBan — copy the whole folder to deploy."
else
    echo "ERROR: expected output not found in dist/KanBan/" >&2
    exit 1
fi
