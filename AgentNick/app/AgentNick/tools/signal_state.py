"""
Tool: get_signal_state / update_signal_state

SQLite-backed state tracking so the agent can check whether a specific
signal has already been resolved before staging a card, and record a
resolution once the user acts.
"""

import sqlite3
from pathlib import Path

from pydantic import BaseModel
from strands import tool

_DB_PATH = Path(__file__).parent.parent / "state.db"


def _get_connection():
    conn = sqlite3.connect(_DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS signal_state (
            signal_id TEXT PRIMARY KEY,
            resolved INTEGER NOT NULL DEFAULT 0,
            resolution TEXT,
            last_tier_shown TEXT
        )
    """)
    return conn


class SignalState(BaseModel):
    signal_id: str
    resolved: bool
    resolution: str | None
    last_tier_shown: str | None


@tool
def get_signal_state(signal_id: str) -> SignalState:
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT signal_id, resolved, resolution, last_tier_shown FROM signal_state WHERE signal_id = ?",
            (signal_id,),
        ).fetchone()
        if row is None:
            return SignalState(signal_id=signal_id, resolved=False, resolution=None, last_tier_shown=None)
        return SignalState(signal_id=row[0], resolved=bool(row[1]), resolution=row[2], last_tier_shown=row[3])
    finally:
        conn.close()


@tool
def update_signal_state(
    signal_id: str,
    resolved: bool,
    resolution: str | None = None,
    last_tier_shown: str | None = None,
) -> SignalState:
    conn = _get_connection()
    try:
        conn.execute(
            """
            INSERT INTO signal_state (signal_id, resolved, resolution, last_tier_shown)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(signal_id) DO UPDATE SET
                resolved = excluded.resolved,
                resolution = excluded.resolution,
                last_tier_shown = excluded.last_tier_shown
            """,
            (signal_id, int(resolved), resolution, last_tier_shown),
        )
        conn.commit()
        return SignalState(signal_id=signal_id, resolved=resolved, resolution=resolution, last_tier_shown=last_tier_shown)
    finally:
        conn.close()
