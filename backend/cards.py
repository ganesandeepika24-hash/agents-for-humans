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
    """Insert ONLY if this signal_id has never been seen before for this
    user. Deliberately never overwrites card_json on subsequent calls,
    even while still pending -- the agent regenerates fresh wording on
    every /check call (same underlying facts, different phrasing), and
    if we kept overwriting the stored text, the card visible to the
    user would appear to "change" on every page load. Freezing the
    content on first sight keeps what the user sees stable, while
    has_been_notified()/status still correctly track resolution."""
    conn = _get_connection()
    try:
        conn.execute(
            """
            INSERT OR IGNORE INTO notified_signals
                (user_id, signal_id, card_json, first_notified_at, status)
            VALUES (?, ?, ?, ?, 'pending')
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


def forget_signal(user_id: str, signal_id: str):
    """Completely removes the stored entry for this signal, rather than
    marking it resolved. Used when the user has submitted new data
    (manual entry or document upload) -- the signal_id stays the same
    (it's derived from a stable identity field, not from which fields
    happen to be populated), so we can't rely on a fresh signal_id
    appearing after re-evaluation. Forgetting the old entry lets the
    re-evaluation's record_notification treat it as genuinely new,
    rather than being silently suppressed as already-resolved."""
    conn = _get_connection()
    try:
        conn.execute(
            "DELETE FROM notified_signals WHERE user_id = ? AND signal_id = ?",
            (user_id, signal_id),
        )
        conn.commit()
    finally:
        conn.close()


def _get_fingerprint_connection():
    conn = sqlite3.connect(_DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS data_fingerprints (
            user_id TEXT NOT NULL,
            scenario_type TEXT NOT NULL,
            fingerprint TEXT NOT NULL,
            PRIMARY KEY (user_id, scenario_type)
        )
    """)
    return conn


def get_last_fingerprint(user_id: str, scenario_type: str) -> str | None:
    """The stored fingerprint of the raw data values as of the last
    check for this scenario -- distinct from signal_id, which
    identifies WHO/WHAT the commitment is about, not what the current
    numbers are. Used to skip calling the AI entirely when nothing
    about the underlying data has actually changed since last time."""
    conn = _get_fingerprint_connection()
    try:
        row = conn.execute(
            "SELECT fingerprint FROM data_fingerprints WHERE user_id = ? AND scenario_type = ?",
            (user_id, scenario_type),
        ).fetchone()
        return row[0] if row else None
    finally:
        conn.close()


def set_last_fingerprint(user_id: str, scenario_type: str, fingerprint: str):
    conn = _get_fingerprint_connection()
    try:
        conn.execute("""
            INSERT INTO data_fingerprints (user_id, scenario_type, fingerprint)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, scenario_type) DO UPDATE SET fingerprint = excluded.fingerprint
        """, (user_id, scenario_type, fingerprint))
        conn.commit()
    finally:
        conn.close()


def reopen_signal(user_id: str, signal_id: str, card: dict):
    """Overwrites and reopens a card for this signal_id, REGARDLESS of
    whether it was previously 'pending' (frozen with stale numbers) or
    'resolved' (silenced forever). Used specifically when the
    underlying data values have genuinely changed since the user last
    saw this signal -- fixes the gap where a resolved or frozen card
    could never reflect new, materially different facts about the same
    underlying commitment."""
    conn = _get_connection()
    try:
        conn.execute("""
            INSERT INTO notified_signals (user_id, signal_id, card_json, first_notified_at, status)
            VALUES (?, ?, ?, ?, 'pending')
            ON CONFLICT(user_id, signal_id) DO UPDATE SET
                card_json = excluded.card_json,
                status = 'pending'
        """, (user_id, signal_id, json.dumps(card), datetime.utcnow().isoformat()))
        conn.commit()
    finally:
        conn.close()


def get_card_by_signal(user_id: str, signal_id: str) -> dict | None:
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT card_json, status FROM notified_signals WHERE user_id = ? AND signal_id = ?",
            (user_id, signal_id),
        ).fetchone()
        if row is None:
            return None
        card = json.loads(row[0])
        card["status"] = row[1]
        return card
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
