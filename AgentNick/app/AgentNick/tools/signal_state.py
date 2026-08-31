"""
Tool: get_signal_state / update_signal_state

Generic, SQLite-backed replacement for TrialReminderState/PaymentReminderState.
Any scenario can use this to check whether a specific signal has already
been resolved (cancelled, kept, marked paid, dismissed) before staging a
card, and to record a resolution once the user acts.

signal_id is caller-defined — should be a stable identifier for the
specific commitment being tracked (e.g. "demo_user:trial:ExampleStreaming"
or "demo_user:card_promo:ExampleBank"), not the card_id (which is
regenerated every time a card is staged).
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


class GetSignalStateInput(BaseModel):
    signal_id: str


class SignalState(BaseModel):
    signal_id: str
    resolved: bool
    resolution: str | None
    last_tier_shown: str | None


class UpdateSignalStateInput(BaseModel):
    signal_id: str
    resolved: bool
    resolution: str | None = None
    last_tier_shown: str | None = None


@tool
def get_signal_state(input: GetSignalStateInput) -> SignalState:
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT signal_id, resolved, resolution, last_tier_shown FROM signal_state WHERE signal_id = ?",
            (input.signal_id,),
        ).fetchone()
        if row is None:
            return SignalState(signal_id=input.signal_id, resolved=False, resolution=None, last_tier_shown=None)
        return SignalState(
            signal_id=row[0],
            resolved=bool(row[1]),
            resolution=row[2],
            last_tier_shown=row[3],
        )
    finally:
        conn.close()


@tool
def update_signal_state(input: UpdateSignalStateInput) -> SignalState:
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
            (input.signal_id, int(input.resolved), input.resolution, input.last_tier_shown),
        )
        conn.commit()
        return SignalState(
            signal_id=input.signal_id,
            resolved=input.resolved,
            resolution=input.resolution,
            last_tier_shown=input.last_tier_shown,
        )
    finally:
        conn.close()