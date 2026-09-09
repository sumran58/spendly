# Spec: Login and Logout

## Overview
Implements session-based authentication for Spendly. `/login` currently only
renders `login.html` on GET; this step adds `POST` handling so a registered
user can sign in, and introduces `flask.session` as the app's first
session/auth mechanism (no `app.secret_key` or `session` usage exists
anywhere yet). It also implements `/logout` to clear the session, and adds a
`login_required` decorator to gate the pages that only make sense for a
signed-in user (`/profile`, `/expenses/add`, `/expenses/<id>/edit`,
`/expenses/<id>/delete`) — those routes stay placeholder strings for now
(their real implementation is Steps 4, 7, 8, 9), but they should already
require a session once login exists.

## Depends on
- Step 1 — Database setup (`database/db.py` with `get_db()`, `users` table
  with `password_hash`). Already complete.
- Step 2 — Registration (`POST /register` creates rows in `users` with a
  werkzeug password hash). Already complete.

## Routes
- `GET /login` — render the sign-in form — public (already implemented, unchanged)
- `POST /login` — validate credentials against `users`, start a session on success, redirect to `/profile` — public
- `GET /logout` — clear the session, redirect to `/` — logged-in (safe to hit while logged out too; it just becomes a no-op redirect)
- `GET /profile` — existing placeholder — now logged-in only (redirects to `/login` if no session)
- `GET /expenses/add` — existing placeholder — now logged-in only
- `GET /expenses/<id>/edit` — existing placeholder — now logged-in only
- `GET /expenses/<id>/delete` — existing placeholder — now logged-in only

## Database changes
No database changes. `users` table (from Step 1) already has the
`email UNIQUE NOT NULL` and `password_hash NOT NULL` columns this step needs.

## Templates
- **Create:** none
- **Modify:**
  - `templates/login.html` — no structural change needed; it already posts
    to `/login` with `email`/`password` fields and already has an
    `{% if error %}` block.
  - `templates/base.html` — nav currently always shows "Sign in" /
    "Get started". Make it session-aware: when `session.user_id` is set,
    show a "Profile" link and a "Logout" link instead.

## Files to change
- `app.py`:
  - Set `app.secret_key` (read from `SECRET_KEY` env var, fall back to a
    fixed dev value) — required before `flask.session` can be used.
  - Change `@app.route("/login")` to accept `methods=["GET", "POST"]`; on
    `POST`, look up the user by email, verify the password with
    `check_password_hash`, and on success set `session["user_id"]` and
    `session["user_name"]` then redirect to `/profile`. On failure,
    re-render `login.html` with a single generic error (don't reveal
    whether the email or the password was wrong) and the submitted email
    re-populated.
  - Add a `login_required` decorator (checks `session.get("user_id")`,
    redirects to `/login` if absent) and apply it to `/profile`,
    `/expenses/add`, `/expenses/<id>/edit`, `/expenses/<id>/delete`.
  - Replace the `/logout` placeholder body with `session.clear()` followed
    by `redirect(url_for("landing"))`.
- `templates/base.html` — branch the nav links on `session.get("user_id")`.

## Files to create
None.

## New dependencies
No new dependencies. Use `werkzeug.security.check_password_hash` (already a
transitive Flask dependency, and its counterpart `generate_password_hash` is
already used in `database/db.py` and `app.py`).

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug (verify with `check_password_hash`, never
  compare plaintext)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Use one generic error message ("Invalid email or password.") for both a
  nonexistent email and a wrong password — do not let a user enumerate
  registered emails via distinct error messages.
- `login_required` must be a plain function-based decorator using
  `functools.wraps`, applied per-route — no Flask-Login or other new
  dependency.
- Do not touch `/register`'s existing behavior.

## Definition of done
- [ ] Submitting `/login` with the seeded demo credentials (`demo@spendly.com` / `demo123`) redirects to `/profile` and the placeholder page loads (no redirect loop)
- [ ] Submitting `/login` with a wrong password re-renders `login.html` with a visible "Invalid email or password." error and does not start a session
- [ ] Submitting `/login` with an email that doesn't exist shows the same generic error (not a different one)
- [ ] Visiting `/profile`, `/expenses/add`, `/expenses/<id>/edit`, or `/expenses/<id>/delete` while logged out redirects to `/login`
- [ ] After logging in, visiting those same routes succeeds (shows the existing placeholder text) instead of redirecting
- [ ] Visiting `/logout` clears the session and redirects to `/`; visiting `/profile` afterward redirects to `/login` again
- [ ] The navbar shows "Sign in" / "Get started" when logged out, and "Profile" / "Logout" when logged in
- [ ] `GET /login` still renders the form as before
- [ ] App starts and runs without errors (`python app.py`)
