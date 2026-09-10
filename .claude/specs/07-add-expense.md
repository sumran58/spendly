# Spec: Add Expense

## Overview
Replaces the `/expenses/add` placeholder ("Add expense — coming in Step 7")
with a real form that lets a signed-in user record a new expense. This is
the first write path into the `expenses` table outside of `seed_db()`, so it
establishes the pattern (validation, parameterised insert, redirect-with-
flash) that Steps 8 (edit) and 9 (delete) will reuse. It does not touch
editing or deleting existing expenses — those stay separate placeholder
routes owned by later steps.

## Depends on
- Step 1 — Database setup (`database/db.py` — `expenses` table with
  `user_id`, `amount`, `category`, `date`, `description`). Already complete.
- Step 3 — Login and Logout (`session["user_id"]`, the `login_required`
  decorator). Already complete. `/expenses/add` is already gated by
  `login_required`.
- Step 4 — Profile page (`templates/profile.html`, `CATEGORIES` list in
  `app.py`). Already complete.
- Step 5 — Backend connection (`database/queries.py` pattern of
  `get_db()`/`try`/`finally` query helper functions). Already complete.

## Routes
- `GET /expenses/add` — render the add-expense form, `date` field defaulted
  to today — logged-in (already gated by `login_required`; replace the
  placeholder string body with `render_template`)
- `POST /expenses/add` — validate the submitted fields, insert a row into
  `expenses` scoped to `session["user_id"]`, flash a success message, and
  redirect to `/profile`; on validation failure, re-render the form with an
  inline error and the submitted values preserved — logged-in

## Database changes
No database changes. `expenses` table (from Step 1) already has every
column this step needs (`user_id`, `amount`, `category`, `date`,
`description`).

## Templates
- **Create:** `templates/add_expense.html` — extends `base.html`; a form
  with `amount` (number input), `category` (`<select>` populated from the
  fixed `CATEGORIES` list in `app.py`), `date` (date input, defaulted to
  today's date), and `description` (optional text input). Reuse the
  existing `.form-group` / `.form-input` / `.btn-submit` classes from
  `static/css/style.css` (the same ones `login.html`/`register.html` use)
  for the field styling; add only page-specific layout in a new stylesheet.
- **Modify:** `templates/profile.html` — add an "+ Add expense" link/button
  (using `url_for('add_expense')`) near the profile header or stats row so
  the form is reachable from the page users land on after login.

## Files to change
- `app.py`:
  - Change `@app.route("/expenses/add")` to accept `methods=["GET", "POST"]`.
  - On `GET`, render `add_expense.html` with today's date pre-filled and the
    `CATEGORIES` list for the dropdown.
  - On `POST`, validate: `amount` is present and parses as a positive float;
    `category` is one of `CATEGORIES`; `date` is a well-formed `YYYY-MM-DD`
    string (reuse the existing `_parse_date` helper); `description` is
    optional and stripped. On any validation failure, re-render
    `add_expense.html` with `error=...` and the submitted values so the
    user doesn't retype them. On success, call the new `add_expense` query
    helper, `flash("Expense added.")`, and redirect to `url_for("profile")`.
- `database/queries.py` — add:
  ```python
  def add_expense(user_id, amount, category, date, description):
      ...
  ```
  Parameterised `INSERT INTO expenses (...) VALUES (...)`, following the
  same `get_db()` / `try` / `finally` pattern as the other functions in this
  file.
- `templates/profile.html` — add the "+ Add expense" link.

## Files to create
- `templates/add_expense.html`
- `static/css/add_expense.css` — page-specific layout only (form-field
  styling comes from the shared `.form-group`/`.form-input`/`.btn-submit`
  classes already in `style.css`).

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only — never string-format values into SQL
- Passwords hashed with werkzeug (n/a here — no password handling on this
  page)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Scope the insert to `session["user_id"]` — never trust a `user_id` from
  the form
- Validate `category` server-side against the fixed `CATEGORIES` list in
  `app.py` — reject anything else, even though the field is a `<select>`
  (a raw POST could send an arbitrary value)
- Validate `amount` server-side as a positive number — reject zero,
  negative, and non-numeric input (client-side `type="number"` is not a
  security boundary)
- Reuse the existing `_parse_date` helper in `app.py` for date validation;
  reject malformed or missing dates with an inline error rather than
  crashing
- Format currency as ₹ (INR) anywhere an amount is echoed back, matching
  the rest of the app
- Close every `get_db()` connection (mirror the existing `try`/`finally`
  pattern used throughout `database/queries.py` and `app.py`)
- Do not modify `/expenses/<id>/edit` or `/expenses/<id>/delete` — those
  remain placeholders owned by Steps 8 and 9

## Definition of done
- [ ] Visiting `/expenses/add` while logged out redirects to `/login`
      (existing `login_required` behavior is unchanged)
- [ ] `GET /expenses/add` while logged in shows a form with amount,
      category (all 7 fixed categories), date (defaulted to today), and
      description fields
- [ ] Submitting valid values creates a new row in `expenses` linked to the
      signed-in user's `id`, flashes a success message, and redirects to
      `/profile`
- [ ] The newly added expense appears in `/profile`'s recent transactions
      and is reflected in the total spent, transaction count, and
      per-category breakdown
- [ ] Submitting a zero, negative, or non-numeric amount re-renders the form
      with a visible error and does not create a row
- [ ] Submitting a category outside the fixed list (e.g. via a raw POST)
      re-renders the form with a visible error and does not create a row
- [ ] Submitting a malformed or empty date re-renders the form with a
      visible error and does not create a row
- [ ] Submitting with no description still succeeds (description is
      optional)
- [ ] Amounts are displayed with the ₹ symbol wherever echoed
- [ ] App starts and runs without errors (`python app.py`)
