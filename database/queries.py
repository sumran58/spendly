from database.db import get_db


def get_summary_stats(user_id, date_from=None, date_to=None):
    db = get_db()
    try:
        query = (
            "SELECT COALESCE(SUM(amount), 0) AS total, COUNT(*) AS count "
            "FROM expenses WHERE user_id = ?"
        )
        params = [user_id]
        if date_from and date_to:
            query += " AND date BETWEEN ? AND ?"
            params += [date_from, date_to]
        row = db.execute(query, params).fetchone()
    finally:
        db.close()
    return row["total"], row["count"]


def get_category_breakdown(user_id, date_from=None, date_to=None):
    db = get_db()
    try:
        query = (
            "SELECT category, SUM(amount) AS total, COUNT(*) AS count "
            "FROM expenses WHERE user_id = ?"
        )
        params = [user_id]
        if date_from and date_to:
            query += " AND date BETWEEN ? AND ?"
            params += [date_from, date_to]
        query += " GROUP BY category"
        return db.execute(query, params).fetchall()
    finally:
        db.close()


def get_recent_transactions(user_id, limit=10, date_from=None, date_to=None):
    db = get_db()
    try:
        query = (
            "SELECT id, amount, category, date, description "
            "FROM expenses WHERE user_id = ?"
        )
        params = [user_id]
        if date_from and date_to:
            query += " AND date BETWEEN ? AND ?"
            params += [date_from, date_to]
        query += " ORDER BY date DESC, id DESC LIMIT ?"
        params.append(limit)
        return db.execute(query, params).fetchall()
    finally:
        db.close()


def add_expense(user_id, amount, category, date, description):
    db = get_db()
    try:
        db.execute(
            "INSERT INTO expenses (user_id, amount, category, date, description) "
            "VALUES (?, ?, ?, ?, ?)",
            (user_id, amount, category, date, description),
        )
        db.commit()
    finally:
        db.close()
