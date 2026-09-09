"""
users.py

Minimal real multi-user identity: email-based, no password, no OAuth
(see module docstring history for why OAuth is deliberately deferred).

Email addresses are encrypted at rest (Fernet symmetric encryption),
not stored as plain text -- fixed after a real-world review flagged
this as a genuine PII exposure risk, especially given we already had
one real security incident this build (a brief accidental public file
listing). Since encrypted values differ every time even for the same
input, we can't search "WHERE email = ?" directly against the
encrypted column -- instead we store a separate, deterministic lookup
fingerprint (HMAC-SHA256) alongside the encrypted value: search by
fingerprint, decrypt only when the actual email is needed.
"""

import sqlite3
import secrets
import hmac
import hashlib
import base64
import os
from pathlib import Path
from datetime import datetime

from cryptography.fernet import Fernet

_DB_PATH = Path(__file__).parent / "users.db"

_ENCRYPTION_KEY = os.environ.get("EMAIL_ENCRYPTION_KEY")
if not _ENCRYPTION_KEY:
    raise RuntimeError(
        "EMAIL_ENCRYPTION_KEY environment variable is required -- "
        "generate one with: python3 -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
    )

_fernet = Fernet(_ENCRYPTION_KEY.encode())
_hmac_key_bytes = base64.urlsafe_b64decode(_ENCRYPTION_KEY.encode())


def _lookup_fingerprint(email: str) -> str:
    """Deterministic (same input -> same output, always) so we can
    search for it, but not reversible back to the email itself."""
    normalized = email.strip().lower()
    return hmac.new(_hmac_key_bytes, normalized.encode(), hashlib.sha256).hexdigest()


def _encrypt_email(email: str) -> str:
    return _fernet.encrypt(email.encode()).decode()


def _decrypt_email(encrypted: str) -> str:
    return _fernet.decrypt(encrypted.encode()).decode()


def _get_connection():
    conn = sqlite3.connect(_DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            email_encrypted TEXT NOT NULL,
            email_lookup TEXT UNIQUE NOT NULL,
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
        lookup = _lookup_fingerprint(email)
        row = conn.execute("SELECT user_id FROM users WHERE email_lookup = ?", (lookup,)).fetchone()
        if row:
            user_id = row[0]
        else:
            user_id = secrets.token_hex(8)
            conn.execute(
                "INSERT INTO users (user_id, email_encrypted, email_lookup, created_at) VALUES (?, ?, ?, ?)",
                (user_id, _encrypt_email(email), lookup, datetime.utcnow().isoformat()),
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


def get_email_for_user(user_id: str) -> str | None:
    """Decrypts and returns the real email -- used sparingly, only
    where genuinely needed (e.g. sending mail), not for casual lookup."""
    conn = _get_connection()
    try:
        row = conn.execute("SELECT email_encrypted FROM users WHERE user_id = ?", (user_id,)).fetchone()
        return _decrypt_email(row[0]) if row else None
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
