"""
user_settings.py

Persistent, per-user threshold preference storage. Backs item 8: lets
a user actually set their own £/% savings threshold instead of always
getting the system default (£15 / 10%, defined in
AgentNick/app/AgentNick/tools/interfaces.py's SYSTEM_DEFAULT).
"""

import sqlite3
from pathlib import Path

_DB_PATH = Path(__file__).parent / "user_settings.db"


def _get_connection():
    conn = sqlite3.connect(_DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS thresholds (
            user_id TEXT PRIMARY KEY,
            min_gbp REAL,
            min_pct REAL
        )
    """)
    return conn


def get_threshold(user_id: str) -> dict:
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT min_gbp, min_pct FROM thresholds WHERE user_id = ?", (user_id,)
        ).fetchone()
        if row is None:
            return {"min_gbp": None, "min_pct": None, "source": "system_default"}
        return {"min_gbp": row[0], "min_pct": row[1], "source": "user_set"}
    finally:
        conn.close()


def set_threshold(user_id: str, min_gbp: float | None, min_pct: float | None):
    conn = _get_connection()
    try:
        conn.execute(
            """
            INSERT INTO thresholds (user_id, min_gbp, min_pct)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                min_gbp = excluded.min_gbp,
                min_pct = excluded.min_pct
            """,
            (user_id, min_gbp, min_pct),
        )
        conn.commit()
    finally:
        conn.close()
