"""
Tests for Step 6: date-range filter on GET /profile.

Spec: .claude/specs/06 date-filter-profile.md

Scope (driven purely by the spec + its "Definition of done" checklist, not by
reading app.py's filter implementation):
  - No query params -> same (unfiltered) data as Step 5
  - Quick-select presets (This Month / Last 3 Months / Last 6 Months / All Time)
    are followed via the actual rendered links, not hardcoded query strings
  - Custom date-range form filters all three sections (summary, transactions,
    category breakdown) and echoes the submitted range back into the inputs
  - Validation: date_from > date_to -> flash error + fallback to unfiltered
  - Validation: malformed / malicious / oversized date strings -> silent
    fallback to unfiltered, no crash, no SQL injection
  - Auth guard still applies to the (now parameterised) /profile route
  - Presets/custom form must be visibly distinguishable when active vs inactive
  - The filter must be scoped per-user (multi-tenant isolation)
  - The Rupee symbol is always present regardless of the active filter

Structural facts relied on (pre-existing conventions, confirmed by peeking at
files the task explicitly allowed, not the date-filter logic itself):
  - `database/db.py`: get_db()/init_db()/seed_db() connect to a hardcoded
    file path (`DB_PATH`), not a Flask config key, and app.py runs
    init_db()/seed_db() once at import time.
  - seed_db() creates a demo user demo@spendly.com / demo123 with 8 sample
    expenses, all dated within the current calendar month, with known
    descriptions ("Groceries for the week", "Cab to office", etc.).
  - /register expects name/email/password form fields; /login expects
    email/password (not username).
  - CATEGORIES (Food, Transport, Bills, Health, Entertainment, Shopping,
    Other) is a fixed list always rendered in the category breakdown.
  - profile.html renders quick-preset links as `<a href="...">LABEL</a>` and
    the custom-range Apply button as `<button ...>Apply</button>`, and the
    date inputs echo back `date_from_str`/`date_to_str` via `value="..."`.
  - format_currency() (pre-existing, Step 5) renders amounts as
    "₹{amount:,.2f}" -- used here only to build expected substrings.
"""

import os
import re
import tempfile
from datetime import date, timedelta

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
from database.db import get_db, init_db, seed_db  # noqa: E402


# ------------------------------------------------------------------ #
# Constants                                                           #
# ------------------------------------------------------------------ #

DEMO_EMAIL = "demo@spendly.com"
DEMO_PASSWORD = "demo123"

SEEDED_DESCRIPTIONS = [
    "Groceries for the week",
    "Cab to office",
    "Electricity bill",
    "Pharmacy purchase",
    "Movie night",
    "New shoes",
    "Miscellaneous",
    "Dinner with friends",
]

SECOND_USER = {"name": "Other User", "email": "other@example.com", "password": "otherpass123"}


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


def _insert_expense(user_id, amount, category, expense_date, description):
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO expenses (user_id, amount, category, date, description) "
            "VALUES (?, ?, ?, ?, ?)",
            (user_id, amount, category, expense_date, description),
        )
        conn.commit()
    finally:
        conn.close()


def _currency(amount):
    """Mirrors the pre-existing (Step 5) format_currency() convention."""
    return f"₹{amount:,.2f}"


def _html(response):
    return response.get_data(as_text=True)


def _extract_href(html_text, link_text):
    """Extract the href of an `<a ...>link_text</a>` anchor from rendered HTML."""
    match = re.search(
        r'<a href="([^"]*)"[^>]*>\s*' + re.escape(link_text) + r"\s*</a>", html_text
    )
    assert match, f"Could not find a link with text {link_text!r} in the page"
    return match.group(1).replace("&amp;", "&")


def _extract_anchor_tag(html_text, link_text):
    """Extract the full `<a ...>link_text</a>` markup for a given link."""
    match = re.search(
        r'<a href="[^"]*"[^>]*>\s*' + re.escape(link_text) + r"\s*</a>", html_text
    )
    assert match, f"Could not find a link with text {link_text!r} in the page"
    return match.group(0)


def _extract_button_tag(html_text, button_text):
    """Extract the full `<button ...>button_text</button>` markup."""
    match = re.search(
        r"<button[^>]*>\s*" + re.escape(button_text) + r"\s*</button>", html_text
    )
    assert match, f"Could not find a button with text {button_text!r} in the page"
    return match.group(0)


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
    """A logged-in client for the seeded demo user, with the 8 sample
    expenses from seed_db() intact (all dated within the current month)."""
    seed_db()
    client.post("/login", data={"email": DEMO_EMAIL, "password": DEMO_PASSWORD})
    return client


@pytest.fixture
def range_client(auth_client):
    """
    Logged-in demo-user client whose expenses have been replaced with four
    controlled records spanning distinct date windows, each tagged with a
    unique description marker used to assert filtering behavior:

      - TXN_TODAY (₹100.00) -> dated today             -> in "This Month"
      - TXN_45D   (₹150.00) -> dated 45 days ago        -> in "Last 3 Months",
                                                            not "This Month"
      - TXN_150D  (₹90.00)  -> dated 150 days ago       -> in "Last 6 Months",
                                                            not "Last 3 Months"
      - TXN_400D  (₹60.00)  -> dated 400 days ago       -> only in "All Time"

    These offsets (45/150/400 days) are chosen with wide safety margins
    around any plausible month-based window so the tests don't depend on
    exact preset-boundary arithmetic:
      - 45 days always falls outside the current calendar month (max month
        length is 31 days) but well inside any 3-month window (>= ~89 days).
      - 150 days always falls outside any 3-month window (<= ~92 days) but
        well inside any 6-month window (~181-184 days).
      - 400 days always falls outside any 6-month window.
    """
    user_id = _get_user_id(DEMO_EMAIL)

    conn = get_db()
    try:
        conn.execute("DELETE FROM expenses WHERE user_id = ?", (user_id,))
        conn.commit()
    finally:
        conn.close()

    today = date.today()
    _insert_expense(user_id, 100.00, "Food", today.isoformat(), "TXN_TODAY")
    _insert_expense(user_id, 150.00, "Transport", (today - timedelta(days=45)).isoformat(), "TXN_45D")
    _insert_expense(user_id, 90.00, "Bills", (today - timedelta(days=150)).isoformat(), "TXN_150D")
    _insert_expense(user_id, 60.00, "Other", (today - timedelta(days=400)).isoformat(), "TXN_400D")
    return auth_client


@pytest.fixture
def second_user_id(client):
    """Registers a second, independent user (not logged in) and returns their id."""
    client.post("/register", data=SECOND_USER)
    return _get_user_id(SECOND_USER["email"])


# ------------------------------------------------------------------ #
# DoD: no query params behaves exactly like the unfiltered Step 5 view #
# ------------------------------------------------------------------ #

class TestUnfilteredBaseline:
    def test_no_query_params_returns_200(self, auth_client):
        resp = auth_client.get("/profile")
        assert resp.status_code == 200

    def test_no_query_params_shows_all_seeded_expenses(self, auth_client):
        resp = auth_client.get("/profile")
        html = _html(resp)
        for description in SEEDED_DESCRIPTIONS:
            assert description in html, f"Expected unfiltered view to include {description!r}"

    def test_no_query_params_totals_match_all_expenses(self, auth_client):
        resp = auth_client.get("/profile")
        html = _html(resp)
        # 450 + 120.50 + 1500 + 800 + 600 + 2200.75 + 300 + 250 = 6221.25
        assert _currency(6221.25) in html, "Expected total spent to sum all 8 seeded expenses"
        assert '<span class="profile-stat-value">8</span>' in html, "Expected transaction count of 8"


# ------------------------------------------------------------------ #
# DoD: quick-select presets filter all three sections correctly        #
# ------------------------------------------------------------------ #

class TestQuickPresets:
    def test_this_month_preset_includes_only_current_month_expense(self, range_client):
        baseline_html = _html(range_client.get("/profile"))
        href = _extract_href(baseline_html, "This Month")

        resp = range_client.get(href)
        assert resp.status_code == 200
        html = _html(resp)

        assert "TXN_TODAY" in html
        assert "TXN_45D" not in html
        assert "TXN_150D" not in html
        assert "TXN_400D" not in html
        assert _currency(100.00) in html

    def test_last_3_months_preset_includes_today_and_45_days_ago(self, range_client):
        baseline_html = _html(range_client.get("/profile"))
        href = _extract_href(baseline_html, "Last 3 Months")

        resp = range_client.get(href)
        assert resp.status_code == 200
        html = _html(resp)

        assert "TXN_TODAY" in html
        assert "TXN_45D" in html
        assert "TXN_150D" not in html
        assert "TXN_400D" not in html
        assert _currency(250.00) in html

    def test_last_6_months_preset_includes_today_45_and_150_days_ago(self, range_client):
        baseline_html = _html(range_client.get("/profile"))
        href = _extract_href(baseline_html, "Last 6 Months")

        resp = range_client.get(href)
        assert resp.status_code == 200
        html = _html(resp)

        assert "TXN_TODAY" in html
        assert "TXN_45D" in html
        assert "TXN_150D" in html
        assert "TXN_400D" not in html
        assert _currency(340.00) in html

    def test_all_time_preset_includes_every_expense(self, range_client):
        baseline_html = _html(range_client.get("/profile"))
        href = _extract_href(baseline_html, "All Time")

        resp = range_client.get(href)
        assert resp.status_code == 200
        html = _html(resp)

        for marker in ("TXN_TODAY", "TXN_45D", "TXN_150D", "TXN_400D"):
            assert marker in html
        assert _currency(400.00) in html

    def test_all_time_preset_link_has_no_query_params(self, range_client):
        baseline_html = _html(range_client.get("/profile"))
        href = _extract_href(baseline_html, "All Time")
        assert "?" not in href, f"Expected a clean /profile URL for 'All Time', got {href!r}"


# ------------------------------------------------------------------ #
# DoD: custom date-range form filters correctly and echoes the range   #
# ------------------------------------------------------------------ #

class TestCustomRange:
    def test_custom_range_shows_only_expenses_within_range(self, range_client):
        today = date.today()
        date_from = (today - timedelta(days=60)).isoformat()
        date_to = (today - timedelta(days=30)).isoformat()

        resp = range_client.get("/profile", query_string={"date_from": date_from, "date_to": date_to})
        assert resp.status_code == 200
        html = _html(resp)

        assert "TXN_45D" in html
        assert "TXN_TODAY" not in html
        assert "TXN_150D" not in html
        assert "TXN_400D" not in html
        assert _currency(150.00) in html

    def test_custom_range_echoes_submitted_dates_into_form_inputs(self, range_client):
        today = date.today()
        date_from = (today - timedelta(days=60)).isoformat()
        date_to = (today - timedelta(days=30)).isoformat()

        resp = range_client.get("/profile", query_string={"date_from": date_from, "date_to": date_to})
        html = _html(resp)

        assert f'value="{date_from}"' in html
        assert f'value="{date_to}"' in html

    def test_custom_range_with_no_matching_expenses_shows_empty_state(self, range_client):
        today = date.today()
        date_from = (today + timedelta(days=10)).isoformat()
        date_to = (today + timedelta(days=20)).isoformat()

        resp = range_client.get("/profile", query_string={"date_from": date_from, "date_to": date_to})
        assert resp.status_code == 200
        html = _html(resp)

        assert _currency(0) in html, "Expected ₹0.00 total spent for an empty range"
        assert "No transactions in this period." in html
        for marker in ("TXN_TODAY", "TXN_45D", "TXN_150D", "TXN_400D"):
            assert marker not in html
        # Category breakdown still renders the fixed category list, all at zero.
        for category in CATEGORIES:
            assert category in html


# ------------------------------------------------------------------ #
# DoD: validation rules and graceful fallback                          #
# ------------------------------------------------------------------ #

class TestValidationAndFallback:
    def test_date_from_after_date_to_flashes_error_and_falls_back_to_unfiltered(self, range_client):
        today = date.today()
        date_from = today.isoformat()
        date_to = (today - timedelta(days=100)).isoformat()

        resp = range_client.get("/profile", query_string={"date_from": date_from, "date_to": date_to})
        assert resp.status_code == 200
        html = _html(resp)

        assert "Start date must be before end date." in html
        for marker in ("TXN_TODAY", "TXN_45D", "TXN_150D", "TXN_400D"):
            assert marker in html
        assert _currency(400.00) in html

    def test_malformed_date_string_falls_back_to_unfiltered_without_crashing(self, range_client):
        resp = range_client.get(
            "/profile", query_string={"date_from": "not-a-date", "date_to": "also-bad"}
        )
        assert resp.status_code == 200
        html = _html(resp)

        for marker in ("TXN_TODAY", "TXN_45D", "TXN_150D", "TXN_400D"):
            assert marker in html
        assert _currency(400.00) in html

    def test_only_one_valid_date_param_falls_back_to_unfiltered(self, range_client):
        today = date.today()
        resp = range_client.get("/profile", query_string={"date_from": today.isoformat()})
        assert resp.status_code == 200
        html = _html(resp)

        for marker in ("TXN_TODAY", "TXN_45D", "TXN_150D", "TXN_400D"):
            assert marker in html
        assert _currency(400.00) in html

    @pytest.mark.parametrize(
        "date_from,date_to",
        [
            ("2024-13-40", "2024-01-31"),
            ("", ""),
            ("2024/01/01", "2024/01/31"),
        ],
    )
    def test_various_malformed_dates_do_not_crash(self, range_client, date_from, date_to):
        resp = range_client.get(
            "/profile", query_string={"date_from": date_from, "date_to": date_to}
        )
        assert resp.status_code == 200


# ------------------------------------------------------------------ #
# Auth guard: the filtered /profile route still requires login         #
# ------------------------------------------------------------------ #

class TestAuthGuard:
    def test_unauthenticated_request_without_filter_redirects_to_login(self, client):
        resp = client.get("/profile")
        assert resp.status_code == 302
        assert "/login" in resp.headers.get("Location", "")

    def test_unauthenticated_request_with_filter_params_redirects_to_login(self, client):
        resp = client.get(
            "/profile", query_string={"date_from": "2024-01-01", "date_to": "2024-01-31"}
        )
        assert resp.status_code == 302
        assert "/login" in resp.headers.get("Location", "")


# ------------------------------------------------------------------ #
# DoD: the ₹ symbol is always present, regardless of the active filter #
# ------------------------------------------------------------------ #

class TestCurrencyDisplay:
    @pytest.mark.parametrize(
        "params",
        [
            {},
            {"date_from": "not-a-date", "date_to": "also-bad"},
        ],
    )
    def test_rupee_symbol_present(self, range_client, params):
        resp = range_client.get("/profile", query_string=params)
        assert "₹" in _html(resp)

    def test_rupee_symbol_present_on_empty_range(self, range_client):
        today = date.today()
        resp = range_client.get(
            "/profile",
            query_string={
                "date_from": (today + timedelta(days=10)).isoformat(),
                "date_to": (today + timedelta(days=20)).isoformat(),
            },
        )
        assert "₹" in _html(resp)


# ------------------------------------------------------------------ #
# DoD: the active preset / custom range must be visually distinguished #
# ------------------------------------------------------------------ #

class TestActiveStateHighlighting:
    def test_active_preset_markup_differs_from_inactive(self, range_client):
        baseline_html = _html(range_client.get("/profile"))
        inactive_tag = _extract_anchor_tag(baseline_html, "This Month")
        href = _extract_href(baseline_html, "This Month")

        active_html = _html(range_client.get(href))
        active_tag = _extract_anchor_tag(active_html, "This Month")

        assert active_tag != inactive_tag, (
            "Expected the 'This Month' link markup to visually differ once active"
        )

    def test_active_apply_button_markup_differs_from_inactive(self, range_client):
        baseline_html = _html(range_client.get("/profile"))
        inactive_tag = _extract_button_tag(baseline_html, "Apply")

        today = date.today()
        custom_html = _html(
            range_client.get(
                "/profile",
                query_string={
                    "date_from": (today - timedelta(days=60)).isoformat(),
                    "date_to": (today - timedelta(days=30)).isoformat(),
                },
            )
        )
        active_tag = _extract_button_tag(custom_html, "Apply")

        assert active_tag != inactive_tag, (
            "Expected the custom-range Apply button markup to visually differ once active"
        )


# ------------------------------------------------------------------ #
# Multi-tenant isolation: the filter only ever touches the caller's own #
# expenses, even though it's not a per-user route parameter             #
# ------------------------------------------------------------------ #

class TestUserIsolation:
    def test_date_filter_does_not_leak_another_users_expenses(self, range_client, second_user_id):
        today = date.today()
        _insert_expense(second_user_id, 999.00, "Food", today.isoformat(), "OTHER_USER_TXN")

        resp = range_client.get("/profile")
        html = _html(resp)

        assert "OTHER_USER_TXN" not in html
        assert _currency(400.00) in html


# ------------------------------------------------------------------ #
# Security / robustness edge cases                                     #
# ------------------------------------------------------------------ #

class TestSecurityEdgeCases:
    def test_sql_injection_attempt_in_date_param_is_handled_safely(self, range_client):
        user_id = _get_user_id(DEMO_EMAIL)
        expenses_before = _count_expenses(user_id)

        resp = range_client.get(
            "/profile",
            query_string={
                "date_from": "2024-01-01'); DROP TABLE expenses; --",
                "date_to": "2024-01-31",
            },
        )
        assert resp.status_code == 200

        # Falls back to unfiltered view rather than erroring or being injected.
        html = _html(resp)
        assert _currency(400.00) in html

        # The expenses table survived intact.
        assert _count_expenses(user_id) == expenses_before

    def test_overly_long_date_string_does_not_crash(self, range_client):
        long_value = "2024-01-01" * 500
        resp = range_client.get(
            "/profile", query_string={"date_from": long_value, "date_to": "2024-01-31"}
        )
        assert resp.status_code == 200
        html = _html(resp)
        assert _currency(400.00) in html
