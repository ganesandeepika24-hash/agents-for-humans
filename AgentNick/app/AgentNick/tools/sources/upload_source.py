"""
UploadSource — extracts structured fields from a user-uploaded document
(statement PDF/image) using vision-based LLM extraction.

Unlike EmailSource, this IS implemented for this build — see the
card_promo scenario, which uses this as its primary path for fields
(promo_apr_end_date, standard_apr_pct) that aren't reliably obtainable
via Open Banking.

Implementation lives here rather than being stubbed, since it's the
real fallback path described in the README's Data Sourcing section.
"""

from .base import SignalSource


class UploadSource(SignalSource):
    """
    file_bytes: raw bytes of the uploaded PDF or image.
    media_type: e.g. "application/pdf", "image/png", "image/jpeg".
    expected_fields: which fields to extract, scoped per source_type by
        the caller (see tools/extract_from_document.py).
    """
    def __init__(self, file_bytes: bytes, media_type: str):
        self.file_bytes = file_bytes
        self.media_type = media_type

    def fetch(self, source_type: str) -> dict:
        from ..extract_from_document import extract_fields_from_document
        return extract_fields_from_document(
            file_bytes=self.file_bytes,
            media_type=self.media_type,
            source_type=source_type,
        )
