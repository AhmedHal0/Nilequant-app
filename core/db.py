"""SQLite persistence. Path from DATABASE_PATH or data/nilequant.db."""
from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS watchlist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL UNIQUE,
    added_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    quantity REAL NOT NULL,
    price REAL NOT NULL,
    fees REAL NOT NULL DEFAULT 0,
    source TEXT NOT NULL DEFAULT 'manual',
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL,
    symbol TEXT,
    params TEXT NOT NULL DEFAULT '{}',
    enabled INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS daily_briefings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mode TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS news_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query TEXT NOT NULL,
    payload TEXT NOT NULL,
    fetched_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS analysis_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    period TEXT NOT NULL,
    payload TEXT NOT NULL,
    fetched_at TEXT NOT NULL,
    UNIQUE(symbol, period)
);
CREATE INDEX IF NOT EXISTS idx_tx_symbol ON transactions(symbol);
CREATE INDEX IF NOT EXISTS idx_news_query ON news_cache(query);
"""

DEFAULT_WATCH = ["COMI", "SWDY", "FWRY", "TMGH", "ABUK"]


def db_path() -> Path:
    raw = os.getenv("DATABASE_PATH", "").strip()
    if raw:
        p = Path(raw)
    else:
        p = Path(__file__).resolve().parent.parent / "data" / "nilequant.db"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@contextmanager
def connect():
    path = db_path()
    con = sqlite3.connect(str(path), timeout=30, isolation_level=None)
    con.row_factory = sqlite3.Row
    try:
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA foreign_keys=ON")
        yield con
    finally:
        con.close()


def init_db() -> Path:
    path = db_path()
    with connect() as con:
        con.executescript(SCHEMA)
        n = con.execute("SELECT COUNT(*) AS c FROM watchlist").fetchone()["c"]
        if n == 0:
            now = utcnow()
            con.executemany(
                "INSERT OR IGNORE INTO watchlist(symbol, added_at) VALUES (?, ?)",
                [(s, now) for s in DEFAULT_WATCH],
            )
        if not con.execute("SELECT 1 FROM settings WHERE key='favorite_symbol'").fetchone():
            con.execute(
                "INSERT INTO settings(key, value) VALUES (?, ?)",
                ("favorite_symbol", DEFAULT_WATCH[0]),
            )
        if not con.execute("SELECT 1 FROM settings WHERE key='theme'").fetchone():
            con.execute("INSERT INTO settings(key, value) VALUES (?, ?)", ("theme", "light"))
        if not con.execute("SELECT 1 FROM settings WHERE key='cash_balance'").fetchone():
            con.execute("INSERT INTO settings(key, value) VALUES (?, ?)", ("cash_balance", "0"))
    return path


def get_setting(key: str, default: str = "") -> str:
    init_db()
    with connect() as con:
        row = con.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row["value"] if row else default


def set_setting(key: str, value: str) -> None:
    init_db()
    with connect() as con:
        con.execute(
            "INSERT INTO settings(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, str(value)),
        )


def json_dumps(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, default=str)


def json_loads(s: str, default=None):
    try:
        return json.loads(s)
    except Exception:
        return default
