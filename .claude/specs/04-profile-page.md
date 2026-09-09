# Spec: Profile Page

## Overview
Replaces the `/profile` placeholder ("Profile page — coming in Step 4") with
a real page. This is the screen users land on right after `POST /login`
succeeds, so it needs to exist before expense management (Steps 7-9) is
usable. It shows the signed-in user's account details (name, email, member
since) and a read-only summary of their expenses — total spent, transaction
count, and a per-category breakdown — pulled from the `expenses` table that
Step 1 already seeds with demo data. It does not add expense creation,
editing, or deletion; those stay separate placeholder routes owned by later
steps.

## Depends on
- Step 1 — Database setup (`database/db.py` — `users` and `expenses`
  tables). Already complete.
- Step 3 — Login and Logout (`session["user_id"]`, `session["user_name"]`,
  the `login_required` decorator, and the session-aware navbar). Already
  complete.

## Routes
- `GET /profile` — render account details and an expense summary for the
  signed-in user — logged-in (already gated by `login_required`; replace the
  placeholder string body with `render_template`)

No other routes change.

## Database changes
No database changes. Uses the existing `expenses` table (`user_id`,
`amount`, `category`, `date`, `description`) and `users` table (`name`,
`email`, `created_at`) from Step 1 — read-only `SELECT` queries only.

## Templates
- **Create:** `templates/profile.html` — extends `base.html`; account info
  card (name, email, member-since date formatted from `created_at`) plus a
  summary section (total spent, transaction count, amount per category,
  using the fixed category list from Step 1: Food, Transport, Bills, Health,
  Entertainment, Shopping, Other).
- **Modify:** none. `base.html`'s session-aware nav (from Step 3) already
  links here via `url_for('profile')`.

## Files to change
- `app.py` — replace the `/profile` placeholder body with a `GET`-only
  handler that queries the signed-in user's row from `users`, aggregates
  their `expenses` (total amount, count, per-category totals), and calls
  `render_template("profile.html", ...)` with that data.

## Files to create
- `templates/profile.html`

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug (n/a here — no password handling on this
  page)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Scope `expenses` queries to `session["user_id"]` — never return another
  user's data
- Per-category totals must cover all 7 fixed categories (Step 1's list),
  showing ₹0 for a category with no expenses rather than omitting it
- Format currency as ₹ (INR), matching the rest of the app's mockups/copy
- Read-only page: no form submission, no POST handler, no edits to
  `users` or `expenses`
- Close every `get_db()` connection (mirror the existing `try`/`finally`
  pattern used in `/register` and `/login`)

## Definition of done
- [ ] Logging in with the seeded demo account (`demo@spendly.com` /
      `demo123`) and landing on `/profile` shows "Demo User" and
      `demo@spendly.com` instead of the placeholder string
- [ ] The page shows a total spent figure that equals the sum of the demo
      user's 8 seeded expenses, formatted with ₹
- [ ] The page shows a transaction count of 8 for the demo user
- [ ] The page shows all 7 categories with correct per-category totals
      (₹0 for any category with no seeded expenses for that user)
- [ ] Visiting `/profile` while logged out still redirects to `/login`
      (existing `login_required` behavior is unchanged)
- [ ] Registering a brand-new account, logging in, and visiting `/profile`
      shows that user's own name/email and ₹0 / 0 transactions (no demo
      data leakage between users)
- [ ] App starts and runs without errors (`python app.py`)
