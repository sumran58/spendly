# Spec: Registration

## Overview
Implements account creation for Spendly. The `/register` route currently
only renders `register.html` on GET; this step adds `POST` handling so a
visitor can submit the form, have their password hashed, and get a new row
in the `users` table — or see an inline error if the email is already taken
or a field is invalid. No session/login mechanism exists yet (no
`app.secret_key`, no `flask.session` usage anywhere), so this step does not
log the new user in; it redirects to `/login` on success. Session-based
auth is left to a future step.

## Depends on
Step 1 — Database setup (`database/db.py` with `get_db()`, `init_db()`,
`users` table with `UNIQUE` email constraint). Already complete.

## Routes
- `GET /register` — render the registration form — public (already implemented, unchanged)
- `POST /register` — handle form submission, create the user, redirect to `/login` on success or re-render the form with an error on failure — public

## Database changes
No database changes. `users` table (from Step 1) already has the
`email TEXT UNIQUE NOT NULL` and `password_hash TEXT NOT NULL` columns this
step needs.

## Templates
- **Create:** none
- **Modify:** `templates/register.html` — no structural change needed; it
  already posts to `/register` with `name`/`email`/`password` fields and
  already has an `{% if error %}` block for `error`. Re-populate `name` and
  `email` input `value=` attributes on error so the user doesn't retype them.

## Files to change
- `app.py` — change `@app.route("/register")` to accept `methods=["GET", "POST"]`; on `POST`, validate input, hash the password, insert the user, handle the duplicate-email case, and redirect to `/login` on success.
- `templates/register.html` — preserve submitted `name`/`email` values after a failed submission.

## Files to create
None.

## New dependencies
No new dependencies. Use `werkzeug.security.generate_password_hash` (already a transitive Flask dependency and already used in `database/db.py`).

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Validate server-side even though the form has `required`/`type=email`/etc. (client-side validation is not a security boundary): non-empty `name`, valid-looking `email`, `password` at least 8 characters (matches the placeholder text "Min. 8 characters").
- Catch the `sqlite3.IntegrityError` from the `UNIQUE` email constraint and re-render `register.html` with `error="An account with that email already exists."` instead of letting it crash the request.
- Do not implement session/login logic in this step — that is out of scope until a session mechanism is designed.

## Definition of done
- [ ] Submitting the form with a new name/email/password creates a row in `users` with a hashed (not plaintext) password
- [ ] After a successful submission, the browser is redirected to `/login`
- [ ] Submitting with an email that already exists re-renders `register.html` with a visible error and does not create a duplicate row
- [ ] Submitting with a password under 8 characters re-renders `register.html` with a visible error and does not create a row
- [ ] Submitting with an empty name re-renders `register.html` with a visible error and does not create a row
- [ ] On a failed submission, the previously typed name and email are still shown in the form fields
- [ ] `GET /register` still renders the form as before
- [ ] App starts and runs without errors (`python app.py`)
