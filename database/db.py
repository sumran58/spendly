import calendar
import os
import sqlite3
from datetime import date

from werkzeug.security import generate_password_hash

DB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "expense_tracker.db")
)

CREATE_USERS_TABLE = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now'))
)
"""

CREATE_EXPENSES_TABLE = """
CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    amount REAL NOT NULL,
    category TEXT NOT NULL,
    date TEXT NOT NULL,
    description TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users (id)
)
"""


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    conn.execute(CREATE_USERS_TABLE)
    conn.execute(CREATE_EXPENSES_TABLE)
    conn.commit()
    conn.close()


def seed_db():
    conn = get_db()
    existing = conn.execute("SELECT COUNT(*) AS count FROM users").fetchone()
    if existing["count"] > 0:
        conn.close()
        return

    password_hash = generate_password_hash("demo123")
    cursor = conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("Demo User", "demo@spendly.com", password_hash),
    )
    user_id = cursor.lastrowid

    today = date.today()
    last_day = calendar.monthrange(today.year, today.month)[1]

    def d(day):
        return f"{today.year:04d}-{today.month:02d}-{min(day, last_day):02d}"

    sample_expenses = [
        (user_id, 450.00, "Food", d(2), "Groceries for the week"),
        (user_id, 120.50, "Transport", d(4), "Cab to office"),
        (user_id, 1500.00, "Bills", d(6), "Electricity bill"),
        (user_id, 800.00, "Health", d(8), "Pharmacy purchase"),
        (user_id, 600.00, "Entertainment", d(11), "Movie night"),
        (user_id, 2200.75, "Shopping", d(14), "New shoes"),
        (user_id, 300.00, "Other", d(17), "Miscellaneous"),
        (user_id, 250.00, "Food", d(20), "Dinner with friends"),
    ]
    conn.executemany(
        "INSERT INTO expenses (user_id, amount, category, date, description) "
        "VALUES (?, ?, ?, ?, ?)",
        sample_expenses,
    )
    conn.commit()
    conn.close()
