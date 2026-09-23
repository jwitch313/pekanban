# PeKanBan

A feature-rich, single-user Kanban task management application for Windows 10/11.

Drag-and-drop task cards across customizable columns, multiple boards, due dates,
priority levels, color-coded status indicators, search, and local data
import/export. Data is stored locally in SQLite; the app follows the system
dark/light mode.

Built with **Python**, **PySide6 (Qt 6)**, and **SQLAlchemy**.

## Status

This project is under active development.

## Development

Requires [uv](https://github.com/astral-sh/uv) and Python 3.9+.

```bash
# Install dependencies into a managed virtual environment
uv sync

# Run the application
uv run kanban

# Run the test suite
uv run pytest tests/ -v --cov=kanban

# Format & lint
uv run ruff format . && uv run ruff check . --fix

# Type check (strict)
uv run mypy src/
```

## Building the Windows executable

The app ships as a standalone executable built with [PyInstaller](https://pyinstaller.org/).
It produces a one-directory layout (fast startup, no per-launch extraction).

```powershell
# Windows (PowerShell)
powershell -ExecutionPolicy Bypass -File scripts\build.ps1
```

```bash
# Cross-platform (bash)
bash scripts/build.sh
```

Both scripts run `uv sync` and then `pyinstaller kanban.spec`. The result is:

```
dist/PeKanBan/
├── PeKanBan.exe      # launch this
└── _internal/        # bundled Python + Qt runtime
```

**Deploy** by copying the entire `dist/PeKanBan/` folder to the target machine.
No Python installation is required on the target. User data (SQLite database
and file attachments) is stored in `%USERPROFILE%\.kanban\`, independent of the
executable's location, so moving or updating the app never touches your data.

## License

PeKanBan is licensed under the GNU General Public License v3 (GPLv3). See the
[LICENSE](LICENSE) file for the full text.
