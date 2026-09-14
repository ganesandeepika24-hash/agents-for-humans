"""
upload_extraction.py

Sends an uploaded document (statement PDF/image) to Claude via Bedrock's
Converse API to extract missing structured fields. Same pattern as the
agent's own extract_from_document tool, reimplemented here since the
backend needs this independent of the agent's tool-calling loop --
this runs directly when a user uploads a document via /upload-document,
before any agent evaluation happens.
"""

import json

import boto3
from botocore.config import Config

MODEL_ID = "eu.anthropic.claude-sonnet-4-5-20250929-v1:0"
_BOTO_CONFIG = Config(read_timeout=60, connect_timeout=10, retries={"max_attempts": 0})

_FIELD_SCHEMAS = {
    "card_promo": {
        "standard_apr_pct": "The standard/regular purchase APR percentage that applies after the promo ends, as a number",
        "balance_transfer_offers": "Any balance transfer offers mentioned, as a list of objects with provider, promo_apr_pct, promo_duration_months, transfer_fee_pct",
        "renewal_price_gbp": "Any retention/loyalty offer price mentioned directly in the email, as a number, if present",
    },
    "card_promo_incomplete": {
        "standard_apr_pct": "The standard/regular purchase APR percentage that applies after the promo ends, as a number",
        "balance_transfer_offers": "Any balance transfer offers mentioned, as a list of objects with provider, promo_apr_pct, promo_duration_months, transfer_fee_pct",
    },
    "tariff": {
        "renewal_price_gbp": "The price that will apply after the current contract/promo ends, as a number",
        "market_comparable_offers": "Any comparable provider offers mentioned",
    },
    "trial": {
        "auto_bill_amount_gbp": "The amount that will be charged once the trial ends, as a number",
        "cancellation_deadline": "The date by which cancellation must happen, in YYYY-MM-DD format",
    },
    "insurance": {
        "renewal_price_gbp": "The renewal premium amount, as a number",
        "current_price_gbp": "The current/expiring premium amount, as a number",
        "renewal_date": "The renewal date, in YYYY-MM-DD format",
    },
    "membership": {
        "renewal_price_gbp": "The renewal price for the membership/subscription, as a number",
        "current_price_gbp": "The current price, as a number",
        "renewal_date": "The renewal or next-billing date, in YYYY-MM-DD format",
    },
}

# Categories the classifier can choose from -- genuinely broader than
# just our three original demo scenarios, matching the real-world
# category breakdown discussed for this product.
CATEGORIES = ["tariff", "trial", "card_promo", "insurance", "membership", "none"]


def classify_email(email_text: str) -> str:
    """First pass: what category (if any) does this email belong to?
    Returns one of CATEGORIES, or 'none' if it's not a relevant
    financial/contract signal at all."""
    prompt = (
        f"Read this email and classify it into EXACTLY ONE of these categories:\n"
        f"- tariff: broadband/mobile/utility contract renewal or price change\n"
        f"- trial: free trial ending or converting to paid subscription\n"
        f"- card_promo: credit card promotional/0%% rate ending\n"
        f"- insurance: insurance policy renewal\n"
        f"- membership: gym, streaming, or other recurring membership/subscription renewal\n"
        f"- none: not relevant to any of the above\n\n"
        f"Respond with ONLY the single category word, nothing else.\n\n"
        f"Email:\n{email_text[:3000]}"
    )
    client = boto3.client("bedrock-runtime", region_name="eu-central-1", config=_BOTO_CONFIG)
    response = client.converse(
        modelId=MODEL_ID,
        messages=[{"role": "user", "content": [{"text": prompt}]}],
        inferenceConfig={"maxTokens": 20, "temperature": 0},
    )
    result = response["output"]["message"]["content"][0]["text"].strip().lower()
    return result if result in CATEGORIES else "none"


def extract_fields_via_bedrock(file_bytes: bytes, media_type: str, scenario_type: str) -> dict:
    schema = _FIELD_SCHEMAS.get(scenario_type, _FIELD_SCHEMAS["card_promo"])
    field_list = "\n".join(f'- "{k}": {v}' for k, v in schema.items())

    prompt = (
        f"Extract the following fields from this document. "
        f"Respond ONLY with a JSON object, no other text, no markdown formatting.\n\n"
        f"Fields to extract:\n{field_list}\n\n"
        f"If a field cannot be found in the document, use null for that field."
    )

    _FORMAT_MAP = {
        "application/pdf": "pdf", "text/plain": "txt", "text/csv": "csv",
        "text/html": "html", "text/markdown": "md",
        "application/msword": "doc",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
        "application/vnd.ms-excel": "xls",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
    }
    doc_format = _FORMAT_MAP.get(media_type, "txt")

    client = boto3.client("bedrock-runtime", region_name="eu-central-1", config=_BOTO_CONFIG)
    response = client.converse(
        modelId=MODEL_ID,
        messages=[{
            "role": "user",
            "content": [
                {"document": {"format": doc_format, "name": "statement", "source": {"bytes": file_bytes}}},
                {"text": prompt},
            ],
        }],
        inferenceConfig={"maxTokens": 500, "temperature": 0},
    )

    raw_text = response["output"]["message"]["content"][0]["text"]
    cleaned = raw_text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise ValueError(f"Model did not return valid JSON: {raw_text}") from e
