# Spec: Edit Expense

## Overview
Replaces the `/expenses/<id>/edit` placeholder ("Edit expense — coming in
Step 8") with a real form that lets a signed-in user correct an existing
expense's amount, category, date, or description. It reuses the validation
and form patterns established in Step 7 (add expense), but adds an
ownership check — a user must only be able to edit their own expenses,
never another user's by guessing an id — and pre-fills the form with the
expense's current values instead of blank/default ones. It does not touch
deleting expenses — that stays a separate placeholder route owned by
Step 9.

## Depends on
- Step 1 — Database setup (`database/db.py` — `expenses` table with `id`,
  `user_id`, `amount`, `category`, `date`, `description`). Already complete.
- Step 3 — Login and Logout (`session["user_id"]`, the `login_required`
  decorator). Already complete. `/expenses/<id>/edit` is already gated by
  `login_required`.
- Step 4 — Profile page (`templates/profile.html`, `CATEGORIES` list in
  `app.py`, recent-transactions list). Already complete.
- Step 5 — Backend connection (`database/queries.py` pattern of
  `get_db()`/`try`/`finally` query helper functions). Already complete.
- Step 7 — Add expense (`templates/add_expense.html` markup/CSS pattern,
  `_parse_date` helper, `CATEGORIES` validation, `add_expense` query
  helper). Already complete — this step mirrors its validation rules.

## Routes
- `GET /expenses/<int:id>/edit` — load the expense by id, verify it belongs
  to `session["user_id"]` (404 or redirect if not found / not owned), and
  render an edit form pre-filled with its current `amount`, `category`,
  `date`, and `description` — logged-in
- `POST /expenses/<int:id>/edit` — re-verify ownership, validate the
  submitted fields with the same rules as add-expense, update the row in
  `expenses`, flash a success message, and redirect to `/profile`; on
  validation failure, re-render the form with an inline error and the
  submitted values preserved; if the expense doesn't exist or isn't owned
  by the current user, do not update anything — logged-in

## Database changes
No database changes. `expenses` table (from Step 1) already has every
column this step needs (`id`, `user_id`, `amount`, `category`, `date`,
`description`).

## Templates
- **Create:** `templates/edit_expense.html` — extends `base.html`; same
  form shape as `add_expense.html` (`amount`, `category` `<select>`, `date`,
  `description`) but action posts to
  `url_for('edit_expense', id=expense.id)`, submit button reads
  "Save changes", and fields are pre-filled from the loaded expense (or
  re-submitted values on a validation error). Reuse the existing
  `.form-group` / `.form-input` / `.btn-submit` / `.auth-*` classes from
  `static/css/style.css` and the layout pattern from
  `static/css/add_expense.css` — add a new stylesheet only if page-specific
  layout differs.
- **Modify:** `templates/profile.html` — add an "Edit" link
  (`url_for('edit_expense', id=txn.id)`) to each row in the recent
  transactions list so expenses are reachable for editing from the page
  users land on after login.

## Files to change
- `app.py`:
  - Change `@app.route("/expenses/<int:id>/edit")` to accept
    `methods=["GET", "POST"]`.
  - On both `GET` and `POST`, first load the expense via a new
    `get_expense_by_id` query helper scoped to `session["user_id"]`; if it
    returns `None`, `flash` a not-found message and redirect to
    `url_for("profile")` (do not leak whether the id exists for another
    user).
  - On `GET`, render `edit_expense.html` with the loaded expense's values
    and the `CATEGORIES` list for the dropdown.
  - On `POST`, validate `amount`, `category`, and `date` using the same
    rules as `add_expense` (reuse `_parse_date`); on any validation
    failure, re-render `edit_expense.html` with `error=...` and the
    submitted values. On success, call the new `update_expense` query
    helper (scoped to both `id` and `user_id` in the `WHERE` clause),
    `flash("Expense updated.")`, and redirect to `url_for("profile")`.
  - In the `profile()` view, add `"id": row["id"]` to each dict built in
    `recent_transactions` so `profile.html` can link to the edit page.
- `database/queries.py` — add:
  ```python
  def get_expense_by_id(user_id, expense_id):
      ...

  def update_expense(user_id, expense_id, amount, category, date, description):
      ...
  ```
  Both parameterised and scoped by `user_id` (in addition to `id`),
  following the same `get_db()` / `try` / `finally` pattern as the other
  functions in this file. `update_expense`'s `UPDATE ... WHERE id = ? AND
  user_id = ?` is the ownership enforcement at the SQL level, not just in
  Python.
- `templates/profile.html` — add the "Edit" link per transaction row.

## Files to create
- `templates/edit_expense.html`

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only — never string-format values into SQL
- Passwords hashed with werkzeug (n/a here — no password handling on this
  page)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Scope every read and write to `session["user_id"]` — a user must never
  be able to view or modify another user's expense by changing the `id` in
  the URL; enforce this in the SQL `WHERE` clause, not just with an
  `if`-check in Python
- Validate `category` server-side against the fixed `CATEGORIES` list in
  `app.py` — reject anything else, even though the field is a `<select>`
- Validate `amount` server-side as a positive number — reject zero,
  negative, and non-numeric input
- Reuse the existing `_parse_date` helper in `app.py` for date validation;
  reject malformed or missing dates with an inline error rather than
  crashing
- Format currency as ₹ (INR) anywhere an amount is echoed back, matching
  the rest of the app
- Close every `get_db()` connection (mirror the existing `try`/`finally`
  pattern used throughout `database/queries.py` and `app.py`)
- Do not modify `/expenses/<id>/delete` — it remains a placeholder owned
  by Step 9
- Do not modify `/expenses/add` or its template beyond what's needed to
  keep `add_expense.html` and `edit_expense.html` visually consistent

## Definition of done
- [ ] Visiting `/expenses/<id>/edit` while logged out redirects to `/login`
      (existing `login_required` behavior is unchanged)
- [ ] `GET /expenses/<id>/edit` for an expense owned by the signed-in user
      shows a form pre-filled with its current amount, category, date, and
      description
- [ ] `GET /expenses/<id>/edit` for an expense that doesn't exist, or that
      belongs to a different user, does not show the expense's data — it
      flashes a message and redirects to `/profile`
- [ ] Submitting valid changes updates the existing row (not a new one),
      flashes a success message, and redirects to `/profile`
- [ ] The updated values appear in `/profile`'s recent transactions and are
      reflected in the total spent, transaction count, and per-category
      breakdown
- [ ] Submitting a zero, negative, or non-numeric amount re-renders the
      form with a visible error and does not change the stored row
- [ ] Submitting a category outside the fixed list re-renders the form
      with a visible error and does not change the stored row
- [ ] Submitting a malformed or empty date re-renders the form with a
      visible error and does not change the stored row
- [ ] Submitting a `POST` to `/expenses/<id>/edit` for an expense owned by
      a different user does not change that row
- [ ] Amounts are displayed with the ₹ symbol wherever echoed
- [ ] `/profile` shows a working "Edit" link for each recent transaction
- [ ] App starts and runs without errors (`python app.py`)
