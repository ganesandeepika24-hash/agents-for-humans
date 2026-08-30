"""
EmailSource — planned ingestion path, not implemented in this build.

Intended design: authenticate via Gmail/Outlook OAuth (user-consented),
search the inbox for provider notification emails (e.g. UK Ofcom-mandated
end-of-contract notices, card statement emails, trial confirmation
emails), and extract structured fields from the email body/attachments
using the same LLM-based extraction approach as UploadSource.

Not built for this hackathon submission — real OAuth setup, inbox search,
and attachment parsing are non-trivial scope beyond the build window.
Documented here as a first-class extension point rather than omitted,
since it's the primary realistic ingestion path for a production version
of this agent.
"""

from .base import SignalSource


class EmailSource(SignalSource):
    def __init__(self, oauth_credentials=None):
        self.oauth_credentials = oauth_credentials

    def fetch(self, source_type: str) -> dict:
        raise NotImplementedError(
            "EmailSource is a planned ingestion path (Gmail/Outlook OAuth + "
            "inbox search + LLM extraction). Not implemented in this build — "
            "see README, Data Sourcing & Realism section."
        )
