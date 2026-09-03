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
}


def extract_fields_via_bedrock(file_bytes: bytes, media_type: str, scenario_type: str) -> dict:
    schema = _FIELD_SCHEMAS.get(scenario_type, _FIELD_SCHEMAS["card_promo"])
    field_list = "\n".join(f'- "{k}": {v}' for k, v in schema.items())

    prompt = (
        f"Extract the following fields from this document. "
        f"Respond ONLY with a JSON object, no other text, no markdown formatting.\n\n"
        f"Fields to extract:\n{field_list}\n\n"
        f"If a field cannot be found in the document, use null for that field."
    )

    doc_format = "pdf" if media_type == "application/pdf" else media_type.split("/")[-1]

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
