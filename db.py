"""SQLite storage for the single monitored search, seen offers and check log."""
import sqlite3
from datetime import datetime, timezone

import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS search (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    origin TEXT NOT NULL,
    destination TEXT NOT NULL,
    departure_date TEXT NOT NULL,
    passengers INTEGER NOT NULL,
    email TEXT NOT NULL,
    max_price REAL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS seen_offers (
    offer_id TEXT PRIMARY KEY,
    price REAL,
    reported_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS checks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    checked_at TEXT NOT NULL,
    status TEXT NOT NULL,
    detail TEXT NOT NULL,
    offers_found INTEGER NOT NULL DEFAULT 0,
    alerts_sent INTEGER NOT NULL DEFAULT 0
);
"""


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect():
    conn = sqlite3.connect(config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init():
    with connect() as conn:
        conn.executescript(SCHEMA)


def get_search():
    with connect() as conn:
        row = conn.execute("SELECT * FROM search WHERE id = 1").fetchone()
    return dict(row) if row else None


def save_search(origin, destination, departure_date, passengers, email, max_price):
    """Replace the single monitored search and reset its alert history."""
    with connect() as conn:
        conn.execute("DELETE FROM search")
        conn.execute("DELETE FROM seen_offers")
        conn.execute("DELETE FROM checks")
        conn.execute(
            "INSERT INTO search (id, origin, destination, departure_date, passengers, email,"
            " max_price, created_at) VALUES (1, ?, ?, ?, ?, ?, ?, ?)",
            (origin, destination, departure_date, passengers, email, max_price, now()),
        )


def delete_search():
    with connect() as conn:
        conn.execute("DELETE FROM search")
        conn.execute("DELETE FROM seen_offers")
        conn.execute("DELETE FROM checks")


def seen_offers():
    with connect() as conn:
        rows = conn.execute("SELECT offer_id, price FROM seen_offers").fetchall()
    return {row["offer_id"]: row["price"] for row in rows}


def record_offer(offer_id, price):
    with connect() as conn:
        conn.execute(
            "INSERT INTO seen_offers (offer_id, price, reported_at) VALUES (?, ?, ?)"
            " ON CONFLICT(offer_id) DO UPDATE SET price = excluded.price,"
            " reported_at = excluded.reported_at",
            (offer_id, price, now()),
        )


def best_reported_price():
    with connect() as conn:
        row = conn.execute("SELECT MIN(price) AS best FROM seen_offers").fetchone()
    return row["best"] if row else None


def log_check(status, detail, offers_found=0, alerts_sent=0):
    with connect() as conn:
        conn.execute(
            "INSERT INTO checks (checked_at, status, detail, offers_found, alerts_sent)"
            " VALUES (?, ?, ?, ?, ?)",
            (now(), status, detail, offers_found, alerts_sent),
        )


def recent_checks(limit=10):
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM checks ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(row) for row in rows]
