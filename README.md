# 💸 Spendly — A Personal Expense Tracker

**Live app:** [expense-tracker-production-97bb.up.railway.app](https://expense-tracker-production-97bb.up.railway.app)
**Demo login:** `demo@spendly.com` / `demo123`

Spendly is a Flask + SQLite expense tracker built step-by-step as a learning project — and as a testbed for a fully agentic, spec-driven development workflow inside **Claude Code**. Every feature below was shipped through a repeatable pipeline of specs → implementation → automated tests → parallel security/quality review → deploy, orchestrated with Claude Code's subagents, custom slash commands, skills, and hooks.

---

## ✨ Product Features

- **Auth** — registration and login with `werkzeug` password hashing, session-based auth, and a `login_required` guard on protected routes
- **Profile dashboard** — total spend, transaction count, category breakdown with proportional bars, and a recent-transactions list
- **Date filtering** — this-month / last-3-months / last-6-months presets plus a custom date range, all server-rendered
- **Expense CRUD** — add and edit expenses with server-side validation (amount, category, date), flash messaging, and ₹ (INR) formatting throughout
- **Server-rendered UI** — Jinja2 templates extending a shared `base.html`, vanilla CSS, no frontend framework

## 🧱 Tech Stack

| Layer | Choice |
|---|---|
| Backend | Flask 3, Python 3.10 |
| Data | SQLite via a hand-rolled `sqlite3` wrapper (no ORM) — `database/db.py`, `database/queries.py` |
| Templates | Jinja2, `base.html` block inheritance |
| Styling | Vanilla CSS, Lucide icons |
| Testing | pytest, pytest-flask |
| Deployment | Railway (Railpack build, gunicorn WSGI server) |

---

## 🤖 Built with an agentic Claude Code workflow

The interesting part of this repo isn't the CRUD app — it's `.claude/`, which turns Claude Code into a small, opinionated engineering team with its own review board, test suite generator, and deployment pipeline. This project was used to explore how far that workflow can go.

### Spec-driven development
Every feature starts as a spec, not a prompt. The custom `/create-spec` command:
- refuses to run on a dirty working tree
- creates a numbered spec file (`.claude/specs/01_database_setup.md` … `08-edit-expense.md`) and a matching feature branch
- becomes the single source of truth an implementation is later graded against

### Custom subagents — a review board, not a single model call
| Subagent | Job |
|---|---|
| `spendly-security-reviewer` | Reviews the feature's diff for security issues (auth bypass, injection, unsafe queries) |
| `spendly-quality-reviewer` | Reviews the same diff for clean, idiomatic, maintainable Flask code |
| `spendly-test-runner` | Executes the pytest suite for the feature and analyzes failures |
| `pytest-spec-tester` | Writes spec-based tests from the spec file *before* looking at the implementation, so tests validate behavior, not implementation details |

`spendly-security-reviewer` and `spendly-quality-reviewer` run **in parallel** on the same diff via the `/code-review-feature <spec-name>` command — one command, two independent expert passes, synthesized into one review.

### Custom skill
`spendly-ui-designer` is a scoped design skill that knows Spendly's exact stack (Flask + Jinja2 + vanilla CSS + Lucide icons) and refuses to reach for React/Tailwind/Bootstrap — keeping every generated page consistent with the rest of the app.

### Hooks — guardrails, not just automation
Configured in `.claude/settings.json`:
- **PostToolUse:** every `.py` file touched by Write/Edit is auto-formatted with `black` before the change is considered done
- **PreToolUse:** a Bash guard inspects every shell command *before* it runs and blocks destructive operations (`rm`, `unlink`, `truncate`) targeting protected paths (`spendly.db`, `.env`, `migrations/`) — a safety net that runs outside the model's own judgment

### Slash commands for the boring parts
- `/create-spec` — spin up the next feature's spec + branch
- `/code-review-feature` — parallel security + quality review against a spec
- `/test-feature` — generate and run the pytest suite for a feature
- `/seed-user`, `/seed-expense` — populate realistic Indian dummy data for local dev/demo without hand-writing fixtures

### Shipping to production
The app was deployed end-to-end through Claude Code's Railway integration: build config (`Procfile`, `gunicorn`), project + service provisioning, environment variables (`SECRET_KEY`), a public domain, and health verification — all driven conversationally, no dashboard clicking required.

---

## 🗂️ Project Structure

```
expense-tracker/
├── app.py                  # Routes — auth, profile, expense CRUD
├── database/
│   ├── db.py                # get_db / init_db / seed_db
│   └── queries.py           # Query helpers used by routes
├── templates/                # Jinja2 templates (base.html + pages)
├── static/                   # CSS + JS
├── tests/                    # pytest suite
├── .claude/
│   ├── agents/               # spendly-security-reviewer, spendly-quality-reviewer, ...
│   ├── commands/              # /create-spec, /code-review-feature, /test-feature, ...
│   ├── skills/spendly-ui-designer/
│   ├── specs/                 # Numbered feature specs (source of truth per feature)
│   └── settings.json           # Hooks: auto-format + destructive-command guard
├── Procfile                  # gunicorn entrypoint for Railway
└── requirements.txt
```

## 🚀 Running Locally

```bash
# from the repo root
python -m venv venv
venv\Scripts\activate       # Windows
pip install -r requirements.txt
python app.py                # http://127.0.0.1:5001
```

The SQLite database (`expense_tracker.db`) is created and seeded automatically on first run.

## ✅ Testing

```bash
pytest
pytest tests/test_add_expense.py::test_name   # single test
```

## ☁️ Deployment

Deployed on [Railway](https://railway.com) using `gunicorn` bound to Railway's dynamic `$PORT`. Build and deploy are Railpack-managed — pushing to `main` is enough to ship.

---

*Built as a step-by-step learning project, and as a hands-on exploration of what an agentic, spec-driven workflow in Claude Code can look like in a real (if small) codebase.*
