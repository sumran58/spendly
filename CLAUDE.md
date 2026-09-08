# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

"Spendly" is a Flask-based personal expense tracker built as a step-by-step learning project. Most functionality is intentionally unimplemented — routes and the database layer exist as stubs with comments describing what each step should build. When asked to "implement the next step" or similar, check the stub comments in `app.py` and `database/db.py` for what is expected before writing code.

Current state:
- `app.py` — only `/`, `/register`, `/login` render real templates (GET only, no form handling yet). `/logout`, `/profile`, `/expenses/add`, `/expenses/<id>/edit`, `/expenses/<id>/delete` are placeholder routes returning plain strings.
- `database/db.py` — empty except a comment specifying it must provide `get_db()` (SQLite connection with `row_factory` and foreign keys enabled), `init_db()` (creates tables with `CREATE TABLE IF NOT EXISTS`), and `seed_db()` (inserts sample dev data).
- `database/__init__.py` — empty.
- `static/js/main.js` — empty stub.
- No tests exist yet, though `pytest` and `pytest-flask` are in `requirements.txt`.

## Commands

Run from the `expense-tracker/expense-tracker` directory (the Flask app root, where `app.py` lives).

```bash
# Install dependencies (create/activate a venv first)
pip install -r requirements.txt

# Run the dev server (http://127.0.0.1:5001, debug mode on)
python app.py

# Run tests (once tests exist)
pytest
pytest path/to/test_file.py::test_name   # single test
```

The SQLite database file is `expense_tracker.db` at the project root (git-ignored); it does not exist until `init_db()` is implemented and called.

## Architecture

- **Flask app factory-free style**: a single global `app = Flask(__name__)` in `app.py`, routes defined directly on it (no blueprints).
- **Templates**: Jinja2, all extending `templates/base.html`, which defines `title`, `head`, `content`, and `scripts` blocks, a shared nav/footer, and pulls in `static/css/style.css` and `static/js/main.js`. New pages should extend `base.html` the same way `landing.html`, `login.html`, and `register.html` do.
- **Database layer**: intended to be a thin `sqlite3` wrapper isolated in `database/db.py` (`get_db`/`init_db`/`seed_db`), not an ORM. Routes should go through these functions rather than opening ad hoc connections.
- **Auth**: no session/auth mechanism implemented yet — `login`/`register` currently only render forms; form submission handling, password hashing, and session management are future steps.
- **Currency/locale**: UI uses ₹ (INR) throughout mockups and copy — keep this consistent when adding expense-related UI.
