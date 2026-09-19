
---
paths:
- "src/**/*.py"
---

## Python Coding Rules

### Package Management
- Always use a virtual environment for Python development. Use uv to create and manage the virtual environment if it does not already exist.
- Use uv for initialization, package management, dependencies, installation, dev testing, run execution, tool calls, deployment and PyPI.
Examples:
* **Environment Setup:** `uv sync`
* **Run Application:** `uv run python src/main.py`
* **Run All Tests:** `uv run pytest tests/ -v --cov=src`
* **Format & Lint Code:** `uv run ruff format . && uv run ruff check . --fix`
* **Type Verification:** `uv run mypy src/`

### Library Usage
- Do not install packages, libraries or modules that are part of the Python Standard Library, instead they should be imported as needed.
- Do **not** install packages, libraries or modules that do not have a positive reputation, regular development actitivy, a secure history or is less than 90 days old.
- Import modules at the top of a file and group imports in the following order: standard libraries, third-party libraries and local project imports.
- When importing modules for GUI tasks check `~/.opensrc/**` for related codebase and library reference documentation to help with planning and logic. If the module or library is not available in opensrc then pause and prompt the user to install the codebase and library reference documentation to help with planning and logic.
- When importing modules for database tasks check `~/.opensrc/**` for related codebase and library reference documentation to help with planning and logic. If the module or library is not available in opensrc then pause and prompt the user to install the codebase and library reference documentation to help with planning and logic.

### File Structure & Naming Conventions
- Main package should have its own directory under `src/` with the same name as the package.
- Services should be saved to the `services/` directory under the main package directory.
- Models should be saved to the `models/` directory under the main package directory.
- UI components, presentational atoms and design-system primitives should be saved to the `ui/` directory under the main package directory.
- Data files should be saved to the `data/` directory.
- Executable scripts should be saved to the `bin/` directory.
- Package test suite and test code should be saved to the `tests/` directory.
- User facing documentation should be saved to the `docs/` directory.
- Use descriptive names for variables, functions and classes.
- Naming conventions:
| Code Element | Naming Style | Example |
| :--- | :--- | :--- |
| Variable | Snake Case (lowercase with underscores) | user_age, total_price |
| Function | Snake Case (lowercase with underscores) | calculate_total(), print_message() |
| Class | Pascal Case / CapWords (capitalize every word) | SmartPhone, BankCustomer |
| Constant | Screaming Snake Case (ALL CAPS with underscores) | PI, MAX_CONNECTIONS |
| Module / File | Short, lowercase words (underscores allowed) | math_helpers.py |
| Package / Folder | Short, lowercase words (with hyphens) | analytics |

### Code Style, Workflow & Preferences
- Follow PEP 8 style guide for Python code.
- Write clear and concise comments to explain code.
- Keep functions and methods short and focused on a single task. Aim for a maximum of 20 lines of code per function.
- Reuse functions whenever possible.
- Do not create any functions, tools or utilities that have existing libraries that provide the needed solutions.
- Do not rewrite working utility functions unless explicitly asked to optimize them.
- Use constants or variables to represent magic numbers for better code maintainability.
- Write a unit test for each new utility function added that contains any math, logic, conditions,  regular expressions, user input cleaning or complex tools.

### Database Practices
- Always create a schema diagram for new database designs.
- Always refer to the schema diagram when writing code to connect to SQLite.
- Always refer to the schema diagram when writing queries to ensure proper joins and relationships.
- Always use a context manager when connecting to SQLite to ensure proper resource management.
- Never use raw SQL queries in code. Use an ORM or query builder instead.
- Use parameterized queries to prevent SQL injection.
- Use connection pooling for performance.
- Use migrations for schema changes.