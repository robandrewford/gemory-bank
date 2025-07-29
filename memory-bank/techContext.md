# Tech Context

This document outlines the technologies and development setup for this project.

## Core Technologies:
- Python 3.10+

## Development Setup:

### Python Package Management: uv
We use `uv` for all dependency management tasks (installation, syncing, adding/removing packages).
- **Installation:** `pip install uv` (or follow `uv`'s official installation guide)
- **Common Commands:**
    - `uv sync`: Installs/syncs dependencies from `requirements.txt` or `pyproject.toml`.
    - `uv add <package>`: Adds a new package to `pyproject.toml` and installs it.
    - `uv remove <package>`: Removes a package.
    - `uv run <command>`: Runs a command in the project's virtual environment.

### Code Quality: Ruff (Linting and Formatting)
We use `ruff` for linting and formatting Python code. It's configured via `pyproject.toml`.
- **Installation:** `pip install ruff`
- **Common Commands:**
    - `ruff check .`: Runs linting checks on the entire project.
    - `ruff check . --fix`: Runs linting checks and attempts to automatically fix issues.
    - `ruff format .`: Formats Python code according to project standards.

### Database Setup:
- Local PostgreSQL instance.
- Connection string managed via environment variables.
- Migrations handled by Alembic (future consideration).

## Technical Constraints:
- Must run on Linux-based servers.
- API must be stateless (except for session if using session-based auth).
- No direct database access from external clients.

## Dependencies:
- Managed via `pyproject.toml` and `uv`.
- Key dependencies: `Flask`, `SQLAlchemy`, `psycopg2-binary`, `uv`, `ruff`.

## Tool Usage Patterns:
- Always use `uv` for Python dependency changes.
- Run `ruff check .` before committing Python code.
- Use `ruff format .` to ensure consistent code style.
- Use `git` for version control.
