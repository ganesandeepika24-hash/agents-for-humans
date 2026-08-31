"""
send_email.py

Sends the actual cancellation/action emails via Resend, for "email"-type
card options. Wraps the raw instruction body with a proper greeting and
sign-off, since the body stored in an ApprovalCard's email_payload is a
functional instruction, not a ready-to-send email.
"""

import os

import resend

resend.api_key = os.environ.get("RESEND_API_KEY", "")
TO_EMAIL_OVERRIDE = os.environ.get("DEMO_RECIPIENT_EMAIL", "")


def _format_email_body(raw_body: str) -> str:
    return f"""Hello,

{raw_body}

Thank you,
A valued customer

--
This email was sent on your behalf by AgentNick, your personal finance
agent, following your explicit approval.
"""


def send_action_email(to: str, subject: str, body: str) -> dict:
    if not resend.api_key:
        raise RuntimeError("RESEND_API_KEY environment variable is not set")
    if not TO_EMAIL_OVERRIDE:
        raise RuntimeError("DEMO_RECIPIENT_EMAIL environment variable is not set")

    demo_subject = f"[AgentNick demo — originally to {to}] {subject}"
    formatted_body = _format_email_body(body)

    result = resend.Emails.send({
        "from": "AgentNick <onboarding@resend.dev>",
        "to": TO_EMAIL_OVERRIDE,
        "subject": demo_subject,
        "text": formatted_body,
    })
    return result
