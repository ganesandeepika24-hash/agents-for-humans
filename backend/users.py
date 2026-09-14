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


def request_login_code(email: str) -> str:
    """Generates a 6-digit code, stores it (expires in 10 min), returns
    it so the caller can email it. Does NOT issue a session token --
    that only happens after verify_login_code succeeds. This is what
    proves the person logging in genuinely controls that inbox,
    closing the gap where knowing someone's email alone let anyone log
    in as them."""
    import random
    code = f"{random.randint(0, 999999):06d}"
    lookup = _lookup_fingerprint(email)
    conn = _get_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS login_codes (
                email_lookup TEXT PRIMARY KEY, code TEXT NOT NULL,
                email_encrypted TEXT NOT NULL, created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            INSERT INTO login_codes (email_lookup, code, email_encrypted, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(email_lookup) DO UPDATE SET code = excluded.code, created_at = excluded.created_at
        """, (lookup, code, _encrypt_email(email), datetime.utcnow().isoformat()))
        conn.commit()
        return code
    finally:
        conn.close()


def verify_login_code(email: str, code: str) -> dict | None:
    """Checks the code, and only if correct AND not expired (10 min),
    creates/finds the user and issues a real session token."""
    lookup = _lookup_fingerprint(email)
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT code, created_at FROM login_codes WHERE email_lookup = ?", (lookup,)
        ).fetchone()
        if row is None or row[0] != code:
            return None

        created_at = datetime.fromisoformat(row[1])
        if (datetime.utcnow() - created_at).total_seconds() > 600:
            return None

        conn.execute("DELETE FROM login_codes WHERE email_lookup = ?", (lookup,))

        user_row = conn.execute("SELECT user_id FROM users WHERE email_lookup = ?", (lookup,)).fetchone()
        if user_row:
            user_id = user_row[0]
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
