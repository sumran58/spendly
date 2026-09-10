import calendar
import functools
import os
import sqlite3
from datetime import date, datetime

from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from database.db import get_db, init_db, seed_db
from database.queries import get_category_breakdown, get_recent_transactions, get_summary_stats

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")

with app.app_context():
    init_db()
    seed_db()


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

def login_required(view):
    @functools.wraps(view)
    def wrapped_view(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped_view


# Mirrors the fixed category list seeded in database/db.py's seed_db()
CATEGORIES = ["Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"]


def format_currency(amount):
    return f"₹{amount:,.2f}"


def _parse_date(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _months_ago(base, months):
    month = base.month - months
    year = base.year
    while month <= 0:
        month += 12
        year -= 1
    day = min(base.day, calendar.monthrange(year, month)[1])
    return base.replace(year=year, month=month, day=day)


@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        if session.get("user_id") is not None:
            return redirect(url_for("profile"))
        return render_template("register.html")

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    if not name:
        return render_template(
            "register.html", error="Please enter your name.", name=name, email=email
        )

    if "@" not in email or email.startswith("@") or email.endswith("@") \
            or "." not in email.rsplit("@", 1)[-1]:
        return render_template(
            "register.html", error="Please enter a valid email address.",
            name=name, email=email,
        )

    if len(password) < 8:
        return render_template(
            "register.html", error="Password must be at least 8 characters.",
            name=name, email=email,
        )

    password_hash = generate_password_hash(password)

    db = get_db()
    try:
        db.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email, password_hash),
        )
        db.commit()
    except sqlite3.IntegrityError:
        return render_template(
            "register.html", error="An account with that email already exists.",
            name=name, email=email,
        )
    finally:
        db.close()

    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        if session.get("user_id") is not None:
            return redirect(url_for("profile"))
        return render_template("login.html")

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    db = get_db()
    try:
        user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    finally:
        db.close()

    if user is None or not check_password_hash(user["password_hash"], password):
        return render_template(
            "login.html", error="Invalid email or password.", email=email,
        )

    session["user_id"] = user["id"]
    session["user_name"] = user["name"]
    return redirect(url_for("profile"))


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


@app.route("/profile")
@login_required
def profile():
    today = date.today()
    date_from = _parse_date(request.args.get("date_from", ""))
    date_to = _parse_date(request.args.get("date_to", ""))

    if date_from and date_to and date_from > date_to:
        flash("Start date must be before end date.")
        date_from = date_to = None

    date_from_str = date_from.isoformat() if date_from else None
    date_to_str = date_to.isoformat() if date_to else None

    presets = {
        "this_month": {
            "date_from": today.replace(day=1).isoformat(),
            "date_to": today.isoformat(),
        },
        "last_3_months": {
            "date_from": _months_ago(today, 3).isoformat(),
            "date_to": today.isoformat(),
        },
        "last_6_months": {
            "date_from": _months_ago(today, 6).isoformat(),
            "date_to": today.isoformat(),
        },
    }
    if date_from_str is None and date_to_str is None:
        active_preset = "all_time"
    else:
        active_preset = next(
            (key for key, preset in presets.items()
             if preset["date_from"] == date_from_str and preset["date_to"] == date_to_str),
            "custom",
        )

    db = get_db()
    try:
        user = db.execute(
            "SELECT name, email, created_at FROM users WHERE id = ?",
            (session["user_id"],),
        ).fetchone()
    finally:
        db.close()

    total_spent, transaction_count = get_summary_stats(
        session["user_id"], date_from_str, date_to_str
    )
    category_rows = get_category_breakdown(session["user_id"], date_from_str, date_to_str)
    recent_rows = get_recent_transactions(session["user_id"], date_from=date_from_str, date_to=date_to_str)

    totals_by_category = {row["category"]: row["total"] for row in category_rows}
    max_category_total = max(totals_by_category.values(), default=0)

    categories = []
    for name in CATEGORIES:
        total = totals_by_category.get(name, 0)
        percent = round((total / max_category_total) * 100) if max_category_total > 0 else 0
        categories.append({
            "name": name,
            "amount_display": format_currency(total),
            "percent": percent,
        })

    recent_transactions = [
        {
            "date": row["date"],
            "category": row["category"],
            "description": row["description"],
            "amount_display": format_currency(row["amount"]),
        }
        for row in recent_rows
    ]

    try:
        member_since = datetime.strptime(
            user["created_at"], "%Y-%m-%d %H:%M:%S"
        ).strftime("%B %Y")
    except (ValueError, TypeError):
        member_since = "—"

    return render_template(
        "profile.html",
        user=user,
        member_since=member_since,
        total_spent_display=format_currency(total_spent),
        transaction_count=transaction_count,
        categories=categories,
        recent_transactions=recent_transactions,
        presets=presets,
        active_preset=active_preset,
        date_from_str=date_from_str,
        date_to_str=date_to_str,
    )


@app.route("/expenses/add")
@login_required
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
@login_required
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
@login_required
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=True, port=5001)
