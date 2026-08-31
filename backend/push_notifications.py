"""
push_notifications.py

Web Push notification support. Subscriptions are stored in-memory for
this hackathon build (a real product would persist per-user
subscriptions in a database) -- a list of subscription objects the
browser gives us when the user grants permission.
"""

import json
import os
from pathlib import Path

from pywebpush import webpush, WebPushException

_PRIVATE_KEY_PATH = Path(__file__).parent / "private_key.pem"
_VAPID_CLAIM_EMAIL = os.environ.get("VAPID_CLAIM_EMAIL", "")

# In-memory subscription store for this demo.
_subscriptions: list[dict] = []


def add_subscription(subscription: dict):
    if subscription not in _subscriptions:
        _subscriptions.append(subscription)


def send_push_to_all(title: str, body: str, url: str | None = None):
    if not _subscriptions:
        print("[push] No subscriptions registered, skipping push.")
        return

    payload = json.dumps({"title": title, "body": body, "url": url or "/"})

    for sub in list(_subscriptions):
        try:
            webpush(
                subscription_info=sub,
                data=payload,
                vapid_private_key=str(_PRIVATE_KEY_PATH),
                vapid_claims={"sub": f"mailto:{_VAPID_CLAIM_EMAIL}"},
            )
            print(f"[push] Sent to subscription {sub.get('endpoint', '')[:50]}...")
        except WebPushException as e:
            print(f"[push] Failed to send, removing dead subscription: {e}")
            _subscriptions.remove(sub)
