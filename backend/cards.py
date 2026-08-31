"""
cards.py

Persistent, per-user store of cards the system has already surfaced to
a user, keyed by signal_id (not card_id -- signal_id is the stable
identity of the underlying commitment, card_id is fresh every check).
Replaces the scheduler's previous in-memory, non-user-scoped
_notified_card_ids set.

This is what makes "don't re-notify about an unchanged fact" actually
work correctly per-user and across process restarts.
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime

_DB_PATH = Path(__file__).parent / "cards.db"


def _get_connection():
    conn = sqlite3.connect(_DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS notified_signals (
            user_id TEXT NOT NULL,
            signal_id TEXT NOT NULL,
            card_json TEXT NOT NULL,
            first_notified_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            PRIMARY KEY (user_id, signal_id)
        )
    """)
    return conn


def has_been_notified(user_id: str, signal_id: str) -> bool:
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT 1 FROM notified_signals WHERE user_id = ? AND signal_id = ? AND status != 'resolved'",
            (user_id, signal_id),
        ).fetchone()
        return row is not None
    finally:
        conn.close()


def record_notification(user_id: str, signal_id: str, card: dict):
    """Insert if new. If this signal was already resolved, leave it
    resolved -- a fresh check finding the same underlying commitment
    again is not grounds to resurface something the user already
    explicitly decided on. Only updates card_json for entries still
    genuinely pending (fresher numbers on an unresolved item)."""
    conn = _get_connection()
    try:
        conn.execute(
            """
            INSERT INTO notified_signals (user_id, signal_id, card_json, first_notified_at, status)
            VALUES (?, ?, ?, ?, 'pending')
            ON CONFLICT(user_id, signal_id) DO UPDATE SET
                card_json = excluded.card_json
            WHERE notified_signals.status != 'resolved'
            """,
            (user_id, signal_id, json.dumps(card), datetime.utcnow().isoformat()),
        )
        conn.commit()
    finally:
        conn.close()


def mark_resolved(user_id: str, signal_id: str):
    conn = _get_connection()
    try:
        conn.execute(
            "UPDATE notified_signals SET status = 'resolved' WHERE user_id = ? AND signal_id = ?",
            (user_id, signal_id),
        )
        conn.commit()
    finally:
        conn.close()


def get_pending_cards_for_user(user_id: str) -> list[dict]:
    conn = _get_connection()
    try:
        rows = conn.execute(
            "SELECT card_json FROM notified_signals WHERE user_id = ? AND status = 'pending'",
            (user_id,),
        ).fetchall()
        return [json.loads(r[0]) for r in rows]
    finally:
        conn.close()
