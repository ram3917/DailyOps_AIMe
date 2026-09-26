"""Local SQLite store for the Personal Trainer: profile, daily Garmin log,
and chat history. Everything the trainer needs lives here - no external
services. This is the only module that opens trainer.db.
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "trainer.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS profile (
  key TEXT PRIMARY KEY,
  value TEXT,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS daily_log (
  date TEXT PRIMARY KEY,
  steps INTEGER,
  sleep_hours REAL,
  weight_kg REAL,
  resting_hr INTEGER,
  body_battery INTEGER,
  stress INTEGER,
  activity_type TEXT,
  duration_min REAL,
  calories INTEGER,
  avg_hr INTEGER,
  max_hr INTEGER,
  training_load REAL,
  distance_km REAL,
  elevation_gain_m REAL,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS chat_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  role TEXT NOT NULL,
  content TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def set_profile(key: str, value) -> None:
    conn = connect()
    conn.execute(
        "INSERT INTO profile (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP",
        (key, str(value)),
    )
    conn.commit()
    conn.close()


def get_profile(key: str, default=None):
    conn = connect()
    row = conn.execute("SELECT value FROM profile WHERE key = ?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else default


def get_all_profile() -> dict:
    conn = connect()
    rows = conn.execute("SELECT key, value FROM profile").fetchall()
    conn.close()
    return {r["key"]: r["value"] for r in rows}


def upsert_daily_log(row: dict) -> None:
    """row must include 'date'; any other daily_log column is optional."""
    conn = connect()
    columns = list(row.keys())
    placeholders = ", ".join("?" for _ in columns)
    updates = ", ".join(f"{c} = excluded.{c}" for c in columns if c != "date")
    conn.execute(
        f"INSERT INTO daily_log ({', '.join(columns)}) VALUES ({placeholders}) "
        f"ON CONFLICT(date) DO UPDATE SET {updates}, updated_at = CURRENT_TIMESTAMP",
        [row[c] for c in columns],
    )
    conn.commit()
    conn.close()


def get_daily_log(date_str: str) -> dict | None:
    conn = connect()
    row = conn.execute("SELECT * FROM daily_log WHERE date = ?", (date_str,)).fetchone()
    conn.close()
    return dict(row) if row else None


def set_weight(date_str: str, weight_kg: float) -> None:
    upsert_daily_log({"date": date_str, "weight_kg": weight_kg})


def add_message(role: str, content: str) -> None:
    conn = connect()
    conn.execute("INSERT INTO chat_history (role, content) VALUES (?, ?)", (role, content))
    conn.commit()
    conn.close()


def get_recent_messages(limit: int = 20) -> list:
    conn = connect()
    rows = conn.execute(
        "SELECT role, content FROM chat_history ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in reversed(rows)]
