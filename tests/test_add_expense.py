"""
Tests for Step 7: Add Expense (`GET`/`POST /expenses/add`).

Spec: .claude/specs/07-add-expense.md

Scope (driven purely by the spec's Routes / Rules for implementation /
Definition of done sections, not by reading app.py's or
database/queries.py's implementation):
  - GET /expenses/add while logged out -> redirect to /login (existing
    login_required behavior, unchanged by this step)
  - GET /expenses/add while logged in -> 200, form with amount, all 7 fixed
    categories, date defaulted to today, and an (optional) description field
  - Valid POST -> inserts a row into `expenses` scoped to the signed-in
    user's id, flashes a success message, and redirects to /profile
  - The newly added expense is reflected in /profile: recent transactions,
    total spent, transaction count, and category breakdown
  - Zero, negative, and non-numeric amounts are all rejected: no row
    created, form re-rendered (not redirected) with a visible error
  - A category outside the fixed list is rejected the same way
  - A malformed or empty date is rejected the same way
  - Submitting with no description still succeeds (description is optional)

Structural facts relied on (pre-existing conventions, confirmed by peeking
at test_date_filter_profile.py -- the repo's existing test file for the
profile route -- and templates/base.html, not at add-expense's own
implementation):
  - `database/db.py`: get_db()/init_db()/seed_db() connect to a hardcoded
    file path (`DB_PATH`), not a Flask config key, and app.py runs
    init_db()/seed_db() once at import time. DB_PATH must be redirected to a
    throwaway temp file *before* `app` is imported.
  - `/register` expects name/email/password form fields; `/login` expects
    email/password (not username).
  - CATEGORIES (Food, Transport, Bills, Health, Entertainment, Shopping,
    Other) is a fixed list of 7, exported from `app.py`.
  - `templates/base.html` renders every flashed message (regardless of
    category) inside `<div class="flash ...">{{ message }}</div>`, so a
    successful add's flash text is visible in the HTML after following the
    redirect.
  - format_currency() (pre-existing, Step 5) renders amounts as
    "₹{amount:,.2f}".
  - The spec's own POST rule names the re-render context variable `error`,
    so a validation failure is expected to surface the substring "error"
    somewhere in the rendered page (class name and/or message) -- checked
    case-insensitively rather than assuming exact copy.

This test file uses a freshly-registered, non-seeded user (rather than the
seed_db() demo user) so expense counts/totals asserted after an add are
trivial to reason about and independent of seeded sample data.
"""

import os
import tempfile
from datetime import date

import pytest

# ------------------------------------------------------------------ #
# Isolate the SQLite file the app uses BEFORE importing `app`.        #
#                                                                      #
# `database.db.get_db()` always connects to a hardcoded file path     #
# (`database.db.DB_PATH`) rather than a Flask config value, and       #
# `app.py` calls `init_db()` / `seed_db()` at *import time* (module   #
# level). To avoid ever touching the real dev `expense_tracker.db`,   #
# we redirect DB_PATH to a throwaway temp file before `app` -- and    #
# therefore its module-level init/seed call -- is imported.           #
# ------------------------------------------------------------------ #
import database.db as _db_module  # noqa: E402

_fd, _TEST_DB_PATH = tempfile.mkstemp(prefix="spendly_test_", suffix=".db")
os.close(_fd)
_db_module.DB_PATH = _TEST_DB_PATH

from app import CATEGORIES, app as flask_app  # noqa: E402
from database.db import get_db, init_db  # noqa: E402


# ------------------------------------------------------------------ #
# Constants                                                           #
# ------------------------------------------------------------------ #

NEW_USER = {
    "name": "Add Expense Tester",
    "email": "addexpense@example.com",
    "password": "testpass123",
}

TODAY = date.today().isoformat()

VALID_PAYLOAD = {
    "amount": "250.50",
    "category": "Food",
    "date": TODAY,
    "description": "Weekly grocery run",
}


# ------------------------------------------------------------------ #
# Helpers                                                              #
# ------------------------------------------------------------------ #

def _reset_db():
    """Wipe all rows so every test starts from a clean, known DB state."""
    conn = get_db()
    try:
        conn.execute("DELETE FROM expenses")
        conn.execute("DELETE FROM users")
        conn.commit()
    finally:
        conn.close()


def _get_user_id(email):
    conn = get_db()
    try:
        row = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    finally:
        conn.close()
    assert row is not None, f"Expected a user with email {email!r} to exist"
    return row["id"]


def _count_expenses(user_id):
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT COUNT(*) AS count FROM expenses WHERE user_id = ?", (user_id,)
        ).fetchone()
    finally:
        conn.close()
    return row["count"]


def _get_expenses(user_id):
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM expenses WHERE user_id = ? ORDER BY id", (user_id,)
        ).fetchall()
    finally:
        conn.close()
    return rows


def _currency(amount):
    """Mirrors the pre-existing (Step 5) format_currency() convention."""
    return f"₹{amount:,.2f}"


def _html(response):
    return response.get_data(as_text=True)


# ------------------------------------------------------------------ #
# Fixtures                                                             #
# ------------------------------------------------------------------ #

@pytest.fixture
def app():
    flask_app.config.update({"TESTING": True, "SECRET_KEY": "test-secret"})
    _reset_db()
    init_db()
    yield flask_app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_client(client):
    """A logged-in client for a freshly-registered, non-seeded user, so it
    starts with zero expenses."""
    client.post("/register", data=NEW_USER)
    client.post("/login", data={"email": NEW_USER["email"], "password": NEW_USER["password"]})
    return client


@pytest.fixture
def user_id(auth_client):
    """The id of the logged-in NEW_USER, resolved *after* auth_client has
    registered them."""
    return _get_user_id(NEW_USER["email"])


# ------------------------------------------------------------------ #
# DoD: GET /expenses/add while logged out redirects to /login          #
# ------------------------------------------------------------------ #

class TestAuthGuard:
    def test_get_add_expense_while_logged_out_redirects_to_login(self, client):
        resp = client.get("/expenses/add")
        assert resp.status_code == 302, "Expected an unauthenticated GET to redirect"
        assert "/login" in resp.headers.get("Location", ""), "Expected redirect to /login"

    def test_post_add_expense_while_logged_out_redirects_to_login(self, client):
        resp = client.post("/expenses/add", data=VALID_PAYLOAD)
        assert resp.status_code == 302, "Expected an unauthenticated POST to redirect"
        assert "/login" in resp.headers.get("Location", ""), "Expected redirect to /login"

    def test_post_add_expense_while_logged_out_creates_no_row(self, client):
        # No user is logged in, so there is no session user_id to scope a row
        # to; the route must not touch the DB before the auth guard fires.
        resp = client.post("/expenses/add", data=VALID_PAYLOAD)
        assert resp.status_code == 302
        conn = get_db()
        try:
            row = conn.execute("SELECT COUNT(*) AS count FROM expenses").fetchone()
        finally:
            conn.close()
        assert row["count"] == 0, "Expected no expense row from an unauthenticated POST"


# ------------------------------------------------------------------ #
# DoD: GET /expenses/add while logged in shows the form correctly      #
# ------------------------------------------------------------------ #

class TestGetForm:
    def test_get_form_returns_200(self, auth_client):
        resp = auth_client.get("/expenses/add")
        assert resp.status_code == 200

    def test_get_form_has_amount_field(self, auth_client):
        html = _html(auth_client.get("/expenses/add"))
        assert 'name="amount"' in html, "Expected an amount input field"

    def test_get_form_has_category_field(self, auth_client):
        html = _html(auth_client.get("/expenses/add"))
        assert 'name="category"' in html, "Expected a category select field"

    def test_get_form_has_description_field(self, auth_client):
        html = _html(auth_client.get("/expenses/add"))
        assert 'name="description"' in html, "Expected a description field"

    def test_get_form_shows_all_seven_fixed_categories(self, auth_client):
        assert len(CATEGORIES) == 7, "Expected the fixed CATEGORIES list to have 7 entries"
        html = _html(auth_client.get("/expenses/add"))
        for category in CATEGORIES:
            assert category in html, f"Expected category {category!r} in the add-expense form"

    def test_get_form_date_defaults_to_today(self, auth_client):
        html = _html(auth_client.get("/expenses/add"))
        assert f'value="{TODAY}"' in html, "Expected the date field to default to today's date"


# ------------------------------------------------------------------ #
# DoD: a valid POST creates a row, flashes success, redirects          #
# ------------------------------------------------------------------ #

class TestValidPost:
    def test_valid_post_redirects_to_profile(self, auth_client):
        resp = auth_client.post("/expenses/add", data=VALID_PAYLOAD)
        assert resp.status_code == 302
        assert "/profile" in resp.headers.get("Location", "")

    def test_valid_post_flashes_success_message(self, auth_client):
        resp = auth_client.post("/expenses/add", data=VALID_PAYLOAD, follow_redirects=True)
        assert resp.status_code == 200
        assert "Expense added." in _html(resp)

    def test_valid_post_creates_row_scoped_to_signed_in_user(self, auth_client, user_id):
        auth_client.post("/expenses/add", data=VALID_PAYLOAD)

        rows = _get_expenses(user_id)
        assert len(rows) == 1, "Expected exactly one expense row to be created"
        row = rows[0]
        assert row["user_id"] == user_id
        assert float(row["amount"]) == pytest.approx(250.50)
        assert row["category"] == "Food"
        assert row["date"] == TODAY
        assert row["description"] == "Weekly grocery run"

    def test_valid_post_does_not_create_a_row_for_another_user(self, auth_client, user_id):
        auth_client.post("/expenses/add", data=VALID_PAYLOAD)
        conn = get_db()
        try:
            rows = conn.execute(
                "SELECT COUNT(*) AS count FROM expenses WHERE user_id != ?", (user_id,)
            ).fetchone()
        finally:
            conn.close()
        assert rows["count"] == 0, "Expected the new row to only be scoped to the signed-in user"


# ------------------------------------------------------------------ #
# DoD: the new expense is reflected in /profile                        #
# ------------------------------------------------------------------ #

class TestProfileReflection:
    def test_new_expense_appears_in_recent_transactions(self, auth_client):
        auth_client.post("/expenses/add", data=VALID_PAYLOAD)
        html = _html(auth_client.get("/profile"))
        assert "Weekly grocery run" in html, "Expected the new expense's description on /profile"

    def test_new_expense_reflected_in_total_spent(self, auth_client):
        auth_client.post("/expenses/add", data=VALID_PAYLOAD)
        html = _html(auth_client.get("/profile"))
        assert _currency(250.50) in html, "Expected the total spent to include the new expense"

    def test_new_expense_reflected_in_transaction_count(self, auth_client):
        auth_client.post("/expenses/add", data=VALID_PAYLOAD)
        html = _html(auth_client.get("/profile"))
        assert '<span class="profile-stat-value">1</span>' in html, (
            "Expected the transaction count to be 1 after adding one expense"
        )

    def test_new_expense_reflected_in_category_breakdown(self, auth_client):
        auth_client.post("/expenses/add", data=VALID_PAYLOAD)
        html = _html(auth_client.get("/profile"))
        assert "Food" in html
        assert _currency(250.50) in html, (
            "Expected the Food category breakdown to include the new expense's amount"
        )

    def test_multiple_added_expenses_accumulate_in_totals(self, auth_client):
        auth_client.post(
            "/expenses/add",
            data={"amount": "100", "category": "Transport", "date": TODAY, "description": "Cab"},
        )
        auth_client.post(
            "/expenses/add",
            data={"amount": "50", "category": "Bills", "date": TODAY, "description": "Internet"},
        )
        html = _html(auth_client.get("/profile"))
        assert _currency(150.00) in html, "Expected total spent to sum both added expenses"
        assert '<span class="profile-stat-value">2</span>' in html


# ------------------------------------------------------------------ #
# DoD: zero / negative / non-numeric amounts are rejected               #
# ------------------------------------------------------------------ #

class TestAmountValidation:
    @pytest.mark.parametrize(
        "bad_amount",
        ["0", "0.00", "-1", "-50.25", "abc", "", "twenty"],
        ids=["zero", "zero-decimal", "negative-int", "negative-float", "non-numeric", "empty", "words"],
    )
    def test_invalid_amount_rejected_no_row_created(self, auth_client, user_id, bad_amount):
        payload = dict(VALID_PAYLOAD, amount=bad_amount)
        resp = auth_client.post("/expenses/add", data=payload)

        assert resp.status_code == 200, "Expected the form to be re-rendered, not redirected"
        assert _count_expenses(user_id) == 0, "Expected no row to be created for an invalid amount"

        html = _html(resp)
        assert 'name="amount"' in html, "Expected the add-expense form to be re-rendered"
        assert "error" in html.lower(), "Expected a visible error indicator"

    def test_non_numeric_amount_preserves_submitted_value(self, auth_client):
        payload = dict(VALID_PAYLOAD, amount="abc")
        resp = auth_client.post("/expenses/add", data=payload)
        html = _html(resp)
        assert 'value="abc"' in html, "Expected the submitted (invalid) amount to be preserved"


# ------------------------------------------------------------------ #
# DoD: a category outside the fixed list is rejected                    #
# ------------------------------------------------------------------ #

class TestCategoryValidation:
    @pytest.mark.parametrize(
        "bad_category",
        ["Groceries", "food", "", "Other; DROP TABLE expenses;--"],
        ids=["unknown-category", "wrong-case", "empty", "sql-injection-attempt"],
    )
    def test_invalid_category_rejected_no_row_created(self, auth_client, user_id, bad_category):
        payload = dict(VALID_PAYLOAD, category=bad_category)
        resp = auth_client.post("/expenses/add", data=payload)

        assert resp.status_code == 200, "Expected the form to be re-rendered, not redirected"
        assert _count_expenses(user_id) == 0, (
            "Expected no row to be created for a category outside the fixed list"
        )

        html = _html(resp)
        assert "error" in html.lower(), "Expected a visible error indicator"

    def test_invalid_category_does_not_drop_expenses_table(self, auth_client, user_id):
        payload = dict(VALID_PAYLOAD, category="Other; DROP TABLE expenses;--")
        auth_client.post("/expenses/add", data=payload)

        # The table must still exist and be queryable.
        assert _count_expenses(user_id) == 0

        # A subsequent valid POST must still succeed, proving the table survived.
        resp = auth_client.post("/expenses/add", data=VALID_PAYLOAD)
        assert resp.status_code == 302
        assert _count_expenses(user_id) == 1


# ------------------------------------------------------------------ #
# DoD: a malformed or empty date is rejected                            #
# ------------------------------------------------------------------ #

class TestDateValidation:
    @pytest.mark.parametrize(
        "bad_date",
        ["", "not-a-date", "2024-13-40", "2024/01/31", "31-01-2024", "2024-02-30"],
        ids=["empty", "non-date-text", "invalid-month-day", "wrong-separator", "wrong-order", "invalid-day-for-month"],
    )
    def test_invalid_date_rejected_no_row_created(self, auth_client, user_id, bad_date):
        payload = dict(VALID_PAYLOAD, date=bad_date)
        resp = auth_client.post("/expenses/add", data=payload)

        assert resp.status_code == 200, "Expected the form to be re-rendered, not redirected"
        assert _count_expenses(user_id) == 0, "Expected no row to be created for a malformed date"

        html = _html(resp)
        assert "error" in html.lower(), "Expected a visible error indicator"

    def test_missing_date_field_rejected_no_row_created(self, auth_client, user_id):
        payload = {k: v for k, v in VALID_PAYLOAD.items() if k != "date"}
        resp = auth_client.post("/expenses/add", data=payload)

        assert resp.status_code == 200
        assert _count_expenses(user_id) == 0


# ------------------------------------------------------------------ #
# DoD: submitting with no description still succeeds                    #
# ------------------------------------------------------------------ #

class TestOptionalDescription:
    def test_empty_description_still_succeeds(self, auth_client, user_id):
        payload = dict(VALID_PAYLOAD, description="")
        resp = auth_client.post("/expenses/add", data=payload)

        assert resp.status_code == 302, "Expected a successful redirect with an empty description"
        assert "/profile" in resp.headers.get("Location", "")
        assert _count_expenses(user_id) == 1

        rows = _get_expenses(user_id)
        assert not rows[0]["description"], "Expected description to be empty/null"

    def test_missing_description_field_still_succeeds(self, auth_client, user_id):
        payload = {k: v for k, v in VALID_PAYLOAD.items() if k != "description"}
        resp = auth_client.post("/expenses/add", data=payload)

        assert resp.status_code == 302, "Expected a successful redirect with no description field"
        assert "/profile" in resp.headers.get("Location", "")
        assert _count_expenses(user_id) == 1

    def test_expense_without_description_appears_on_profile(self, auth_client, user_id):
        payload = dict(VALID_PAYLOAD, description="")
        auth_client.post("/expenses/add", data=payload)

        resp = auth_client.get("/profile")
        assert resp.status_code == 200
        html = _html(resp)
        assert _currency(250.50) in html
        assert '<span class="profile-stat-value">1</span>' in html
