"""
users.py

Minimal real multi-user identity: email-based, no password, no OAuth.
User provides their email once; we create/find a user record and issue
a session token. Every subsequent request carries that token, so the
backend genuinely knows which user's data it's looking at -- this is
NOT full authentication (no email verification, no OAuth), but it is
real per-user identity, not the single implicit "demo_user" the system
previously assumed everywhere.

Real OAuth (Google/Microsoft sign-in) is a documented near-term
roadmap item -- deliberately deferred to avoid adding a cross-domain
redirect-chain failure mode this close to the submission deadline.
"""

import sqlite3
import secrets
from pathlib import Path
from datetime import datetime

_DB_PATH = Path(__file__).parent / "users.db"


def _get_connection():
    conn = sqlite3.connect(_DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    return conn


def login(email: str) -> dict:
    """Create the user if new, always issue a fresh session token."""
    conn = _get_connection()
    try:
        row = conn.execute("SELECT user_id FROM users WHERE email = ?", (email,)).fetchone()
        if row:
            user_id = row[0]
        else:
            user_id = secrets.token_hex(8)
            conn.execute(
                "INSERT INTO users (user_id, email, created_at) VALUES (?, ?, ?)",
                (user_id, email, datetime.utcnow().isoformat()),
            )

        token = secrets.token_urlsafe(32)
        conn.execute(
            "INSERT INTO sessions (token, user_id, created_at) VALUES (?, ?, ?)",
            (token, user_id, datetime.utcnow().isoformat()),
        )
        conn.commit()
        return {"user_id": user_id, "email": email, "token": token}
    finally:
        conn.close()


def get_user_id_from_token(token: str) -> str | None:
    conn = _get_connection()
    try:
        row = conn.execute("SELECT user_id FROM sessions WHERE token = ?", (token,)).fetchone()
        return row[0] if row else None
    finally:
        conn.close()


def list_all_user_ids() -> list[str]:
    """Used by the scheduler to check every registered user's signals."""
    conn = _get_connection()
    try:
        rows = conn.execute("SELECT user_id FROM users").fetchall()
        return [r[0] for r in rows]
    finally:
        conn.close()
