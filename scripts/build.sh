#!/usr/bin/env bash
# build.sh — Build the PeKanBan executable with PyInstaller (cross-platform dev).
#
# Usage (from the repository root):
#   bash scripts/build.sh
#
# Output: dist/PeKanBan/PeKanBan(.exe)  (one-directory layout)
#
# Prerequisites:
#   - uv installed and on PATH
#   - `uv sync` has been run (installs PySide6, SQLAlchemy, PyInstaller)

set -euo pipefail

echo "==> Syncing dependencies (uv sync)..."
uv sync

echo "==> Building executable (pyinstaller kanban.spec)..."
uv run pyinstaller kanban.spec --noconfirm

if [[ -f dist/PeKanBan/PeKanBan.exe ]]; then
    echo "==> Build complete."
    echo "    Executable: dist/PeKanBan/PeKanBan.exe"
    echo "    Folder:     dist/PeKanBan — copy the whole folder to deploy."
elif [[ -f dist/PeKanBan/PeKanBan ]]; then
    echo "==> Build complete."
    echo "    Executable: dist/PeKanBan/PeKanBan"
    echo "    Folder:     dist/PeKanBan — copy the whole folder to deploy."
else
    echo "ERROR: expected output not found in dist/PeKanBan/" >&2
    exit 1
fi
