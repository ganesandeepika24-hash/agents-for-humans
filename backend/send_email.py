"""
send_email.py

Sends the actual cancellation/action emails via Resend, for "email"-type
card options. On Resend's free tier without a verified domain, emails
can only be sent to the account's own verified address using the
onboarding@resend.dev sender -- so for this demo, TO_EMAIL_OVERRIDE
redirects all sends there regardless of the mock data's original
recipient, while keeping the original recipient visible in the subject
line for transparency during the demo.
"""

import os

import resend

resend.api_key = os.environ.get("RESEND_API_KEY", "")

# Set this to YOUR verified Resend account email.
TO_EMAIL_OVERRIDE = os.environ.get("DEMO_RECIPIENT_EMAIL", "")


def send_action_email(to: str, subject: str, body: str) -> dict:
    if not resend.api_key:
        raise RuntimeError("RESEND_API_KEY environment variable is not set")
    if not TO_EMAIL_OVERRIDE:
        raise RuntimeError("DEMO_RECIPIENT_EMAIL environment variable is not set")

    demo_subject = f"[AgentNick demo — originally to {to}] {subject}"

    result = resend.Emails.send({
        "from": "AgentNick <onboarding@resend.dev>",
        "to": TO_EMAIL_OVERRIDE,
        "subject": demo_subject,
        "text": body,
    })
    return result
