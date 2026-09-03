"""
push_notifications.py

Web Push notification support. Subscriptions are persisted in SQLite,
keyed by user_id -- so a push about one user's data can only ever
reach that user's own registered device(s), never anyone else's.
"""

import json
import os
import sqlite3
from pathlib import Path

from pywebpush import webpush, WebPushException

_DB_PATH = Path(__file__).parent / "push_subscriptions.db"
_PRIVATE_KEY_PATH = Path(__file__).parent / "private_key.pem"
_VAPID_CLAIM_EMAIL = os.environ.get("VAPID_CLAIM_EMAIL", "")


def _get_connection():
    conn = sqlite3.connect(_DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            user_id TEXT NOT NULL,
            endpoint TEXT NOT NULL,
            subscription_json TEXT NOT NULL,
            PRIMARY KEY (user_id, endpoint)
        )
    """)
    return conn


def add_subscription(user_id: str, subscription: dict):
    endpoint = subscription.get("endpoint", "")
    conn = _get_connection()
    try:
        conn.execute(
            """
            INSERT INTO subscriptions (user_id, endpoint, subscription_json)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, endpoint) DO UPDATE SET subscription_json = excluded.subscription_json
            """,
            (user_id, endpoint, json.dumps(subscription)),
        )
        conn.commit()
    finally:
        conn.close()


def _remove_subscription(user_id: str, endpoint: str):
    conn = _get_connection()
    try:
        conn.execute("DELETE FROM subscriptions WHERE user_id = ? AND endpoint = ?", (user_id, endpoint))
        conn.commit()
    finally:
        conn.close()


def send_push_to_user(
    user_id: str,
    title: str,
    body: str,
    url: str | None = None,
    card_id: str | None = None,
    signal_id: str | None = None,
    actions: list[dict] | None = None,
):
    """
    actions: list of {"action": str, "title": str} dicts, up to 2 --
    these render as buttons directly on the notification. Each
    "action" value should match an option_type the service worker
    knows how to resolve (e.g. "dismiss", "remind_later") or a card
    reference for the frontend to handle if opened.
    """
    conn = _get_connection()
    try:
        rows = conn.execute(
            "SELECT endpoint, subscription_json FROM subscriptions WHERE user_id = ?", (user_id,)
        ).fetchall()
    finally:
        conn.close()

    if not rows:
        print(f"[push] No subscriptions for user {user_id}, skipping push.")
        return

    payload = json.dumps({
        "title": title,
        "body": body,
        "url": url or "/",
        "card_id": card_id,
        "signal_id": signal_id,
        "actions": actions or [],
    })

    for endpoint, sub_json in rows:
        sub = json.loads(sub_json)
        try:
            webpush(
                subscription_info=sub,
                data=payload,
                vapid_private_key=str(_PRIVATE_KEY_PATH),
                vapid_claims={"sub": f"mailto:{_VAPID_CLAIM_EMAIL}"},
            )
            print(f"[push] Sent to user {user_id}, subscription {endpoint[:50]}...")
        except WebPushException as e:
            print(f"[push] Failed for user {user_id}, removing dead subscription: {e}")
            _remove_subscription(user_id, endpoint)
