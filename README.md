# KanBan

A feature-rich, single-user Kanban task management application for Windows 10/11.

Drag-and-drop task cards across customizable columns, multiple boards, due dates,
priority levels, color-coded status indicators, search, and local data
import/export. Data is stored locally in SQLite; the app follows the system
dark/light mode.

Built with **Python**, **PySide6 (Qt 6)**, and **SQLAlchemy**.

## Status

This project is under active development. See `plans/SDR_KanBan_App.md` for the
full Software Design Requirements and the implementation roadmap.

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

## License

MIT
