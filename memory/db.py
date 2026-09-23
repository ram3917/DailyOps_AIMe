"""Per-agent SQLite memory access.

open_agent_db() is the ONLY function anywhere in this codebase allowed to
open an agent's memory database. Memory isolation depends on every agent
module calling it with its own literal agent name and nothing else -
tests/test_memory_isolation.py statically checks that this holds.
"""
import sqlite3
from pathlib import Path

MEMORY_DIR = Path(__file__).resolve().parent
SCHEMA_PATH = MEMORY_DIR / "schema.sql"


def get_agent_db_path(agent_name: str) -> Path:
    return MEMORY_DIR / f"{agent_name}.db"


def open_agent_db(agent_name: str) -> sqlite3.Connection:
    db_path = get_agent_db_path(agent_name)
    is_new = not db_path.exists()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    if is_new:
        conn.executescript(SCHEMA_PATH.read_text())
        conn.commit()
    return conn


def set_profile(conn: sqlite3.Connection, key: str, value) -> None:
    conn.execute(
        "INSERT INTO profile (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP",
        (key, str(value)),
    )
    conn.commit()


def get_profile(conn: sqlite3.Connection, key: str, default=None):
    row = conn.execute("SELECT value FROM profile WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else default


def get_all_profile(conn: sqlite3.Connection) -> dict:
    return {r["key"]: r["value"] for r in conn.execute("SELECT key, value FROM profile")}


def add_note(conn: sqlite3.Connection, date_str: str, note: str) -> None:
    conn.execute("INSERT INTO notes (date, note) VALUES (?, ?)", (date_str, note))
    conn.commit()


def get_notes(conn: sqlite3.Connection, limit: int = 20):
    return conn.execute(
        "SELECT date, note FROM notes ORDER BY date DESC, id DESC LIMIT ?", (limit,)
    ).fetchall()
