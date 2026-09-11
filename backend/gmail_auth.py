"""
gmail_auth.py

Minimal OAuth2 flow for read-only Gmail access, implemented via direct
HTTP calls (no heavy google-auth dependency) for simplicity and fewer
version-conflict risks. Refresh tokens are encrypted at rest using the
same pattern as users.py.
"""

import os
import sqlite3
import requests
from pathlib import Path
from cryptography.fernet import Fernet

_DB_PATH = Path(__file__).parent / "gmail_tokens.db"
_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
_REDIRECT_URI = os.environ.get("GOOGLE_REDIRECT_URI")
_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"

_fernet = Fernet(os.environ["EMAIL_ENCRYPTION_KEY"].encode())


def _get_connection():
    conn = sqlite3.connect(_DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS gmail_tokens (
            user_id TEXT PRIMARY KEY,
            refresh_token_encrypted TEXT NOT NULL,
            connected_at TEXT NOT NULL
        )
    """)
    return conn


def build_authorization_url(user_id: str) -> str:
    params = {
        "client_id": _CLIENT_ID,
        "redirect_uri": _REDIRECT_URI,
        "response_type": "code",
        "scope": _SCOPE,
        "access_type": "offline",
        "prompt": "consent",
        "state": user_id,
    }
    query = "&".join(f"{k}={requests.utils.quote(str(v))}" for k, v in params.items())
    return f"https://accounts.google.com/o/oauth2/v2/auth?{query}"


def exchange_code_for_tokens(code: str) -> dict:
    response = requests.post("https://oauth2.googleapis.com/token", data={
        "code": code,
        "client_id": _CLIENT_ID,
        "client_secret": _CLIENT_SECRET,
        "redirect_uri": _REDIRECT_URI,
        "grant_type": "authorization_code",
    })
    response.raise_for_status()
    return response.json()


def store_refresh_token(user_id: str, refresh_token: str):
    from datetime import datetime
    encrypted = _fernet.encrypt(refresh_token.encode()).decode()
    conn = _get_connection()
    try:
        conn.execute("""
            INSERT INTO gmail_tokens (user_id, refresh_token_encrypted, connected_at)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET refresh_token_encrypted = excluded.refresh_token_encrypted
        """, (user_id, encrypted, datetime.utcnow().isoformat()))
        conn.commit()
    finally:
        conn.close()


def is_connected(user_id: str) -> bool:
    conn = _get_connection()
    try:
        row = conn.execute("SELECT 1 FROM gmail_tokens WHERE user_id = ?", (user_id,)).fetchone()
        return row is not None
    finally:
        conn.close()


def get_access_token(user_id: str) -> str | None:
    conn = _get_connection()
    try:
        row = conn.execute("SELECT refresh_token_encrypted FROM gmail_tokens WHERE user_id = ?", (user_id,)).fetchone()
    finally:
        conn.close()
    if row is None:
        return None
    refresh_token = _fernet.decrypt(row[0].encode()).decode()

    response = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": _CLIENT_ID,
        "client_secret": _CLIENT_SECRET,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    })
    if response.status_code != 200:
        return None
    return response.json().get("access_token")
