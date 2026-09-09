import functools
import os
import sqlite3
from datetime import datetime

from flask import Flask, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from database.db import get_db, init_db, seed_db

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
    db = get_db()
    try:
        user = db.execute(
            "SELECT name, email, created_at FROM users WHERE id = ?",
            (session["user_id"],),
        ).fetchone()
        category_rows = db.execute(
            "SELECT category, SUM(amount) AS total, COUNT(*) AS count "
            "FROM expenses WHERE user_id = ? GROUP BY category",
            (session["user_id"],),
        ).fetchall()
    finally:
        db.close()

    totals_by_category = {row["category"]: row["total"] for row in category_rows}
    counts_by_category = {row["category"]: row["count"] for row in category_rows}

    total_spent = sum(totals_by_category.values())
    transaction_count = sum(counts_by_category.values())
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
