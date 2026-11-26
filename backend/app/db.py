"""SQLite storage for the demo store: orders and support tickets."""

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DEFAULT_DB_PATH = "data/support.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS orders (
    id          TEXT PRIMARY KEY,
    email       TEXT NOT NULL,
    items       TEXT NOT NULL,
    total       INTEGER NOT NULL,      -- rupees
    status      TEXT NOT NULL,         -- processing | shipped | delivered | cancelled
    ordered_on  TEXT NOT NULL,
    eta         TEXT,
    courier     TEXT,
    tracking_no TEXT
);

CREATE TABLE IF NOT EXISTS tickets (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    email       TEXT NOT NULL,
    order_id    TEXT,
    subject     TEXT NOT NULL,
    description TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'open',
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

SEED_ORDERS = [
    ("AC1042", "priya@example.com", "Wireless earbuds", 2499, "shipped", "2026-11-20", "2026-11-28", "Delhivery", "DL88213490"),
    ("AC1043", "priya@example.com", "Phone case, Screen guard", 698, "delivered", "2026-11-02", None, "Blue Dart", "BD55102931"),
    ("AC1057", "rahul@example.com", "Smartwatch", 5999, "processing", "2026-11-25", "2026-12-01", None, None),
    ("AC1061", "rahul@example.com", "USB-C charger", 1199, "cancelled", "2026-11-18", None, None, None),
    ("AC1066", "neha@example.com", "Bluetooth speaker", 3499, "delivered", "2026-10-29", None, "Delhivery", "DL87719022"),
]


def get_db_path() -> Path:
    # read on every call so tests can point SUPPORT_DB at a temp file
    return Path(os.environ.get("SUPPORT_DB", DEFAULT_DB_PATH))


@contextmanager
def connect():
    path = get_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    """Create tables and add the sample orders the first time the app runs."""
    with connect() as conn:
        conn.executescript(SCHEMA)
        if conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 0:
            conn.executemany("INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", SEED_ORDERS)
