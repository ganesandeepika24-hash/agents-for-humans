"""
gmail_reader.py

Fetches recent emails via the Gmail API (read-only) and extracts
financial-signal fields from them using the same Bedrock-based
extraction pattern already proven working for document uploads.
"""

import base64
import requests

from gmail_auth import get_access_token
from upload_extraction import extract_fields_via_bedrock


def fetch_receipt_history(user_id: str, max_results: int = 30) -> list[dict]:
    """Broader search across a longer window, specifically for
    receipt/payment-confirmation-style emails -- used for pattern
    detection (recurring subscriptions), not just explicit renewal
    notices."""
    return fetch_recent_emails(
        user_id,
        query="newer_than:180d (receipt OR \"payment confirmation\" OR \"your subscription\" OR invoice OR \"you've been charged\" OR \"thank you for your payment\")",
        max_results=max_results,
    )


def group_emails_by_sender_domain(emails: list[dict]) -> dict:
    """Groups emails by the sending domain extracted from the subject/
    body heuristically -- real Gmail API would give us the From header
    directly; simplified here to work with what fetch_recent_emails
    already returns (subject + body only)."""
    groups = {}
    for email in emails:
        # Use the subject as a rough grouping key -- real emails from
        # the same recurring service tend to have very similar/identical
        # subject lines across months (e.g. "Your receipt from Claude").
        key = email["subject"].strip().lower()
        groups.setdefault(key, []).append(email)
    return groups


def fetch_recent_emails(user_id: str, query: str = "newer_than:30d", max_results: int = 10) -> list[dict]:
    access_token = get_access_token(user_id)
    if not access_token:
        return []

    headers = {"Authorization": f"Bearer {access_token}"}
    list_resp = requests.get(
        "https://gmail.googleapis.com/gmail/v1/users/me/messages",
        headers=headers, params={"q": query, "maxResults": max_results},
    )
    if list_resp.status_code != 200:
        return []

    message_ids = [m["id"] for m in list_resp.json().get("messages", [])]
    emails = []
    for msg_id in message_ids:
        detail_resp = requests.get(
            f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg_id}",
            headers=headers, params={"format": "full"},
        )
        if detail_resp.status_code != 200:
            continue
        detail = detail_resp.json()

        subject = next(
            (h["value"] for h in detail.get("payload", {}).get("headers", []) if h["name"] == "Subject"),
            "(no subject)",
        )
        body_text = _extract_body_text(detail.get("payload", {}))
        emails.append({"id": msg_id, "subject": subject, "body": body_text})

    return emails


def _extract_body_text(payload: dict) -> str:
    if payload.get("mimeType") == "text/plain" and "data" in payload.get("body", {}):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")
    for part in payload.get("parts", []):
        text = _extract_body_text(part)
        if text:
            return text
    return ""


def extract_signal_from_email(email: dict, scenario_type: str) -> dict:
    combined_text = f"Subject: {email['subject']}\n\n{email['body']}"
    fake_bytes = combined_text.encode("utf-8")
    return extract_fields_via_bedrock(fake_bytes, "text/plain", scenario_type)
