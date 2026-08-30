"""
extract_from_document — sends a document (PDF/image) to Claude via
Bedrock's Converse API and extracts structured fields as JSON.

This is a real, working Bedrock call — not a mock — used by UploadSource
to extract fields that aren't reliably obtainable via Open Banking
(e.g. promo_apr_end_date, standard_apr_pct for the card_promo scenario).
"""

import json

import boto3

MODEL_ID = "eu.anthropic.claude-sonnet-4-5-20250929-v1:0"

_FIELD_SCHEMAS = {
    "card_promo": {
        "promo_apr_end_date": "The date the 0% or promotional interest rate ends, in YYYY-MM-DD format",
        "standard_apr_pct": "The standard/regular purchase APR percentage that applies after the promo ends, as a number",
        "current_balance_gbp": "The outstanding balance shown on the statement, as a number",
        "minimum_payment_gbp": "The minimum payment due, as a number",
    },
}


def extract_fields_from_document(file_bytes: bytes, media_type: str, source_type: str) -> dict:
    if source_type not in _FIELD_SCHEMAS:
        raise ValueError(f"No extraction schema defined for source_type: {source_type}")

    fields = _FIELD_SCHEMAS[source_type]
    field_list = "\n".join(f'- "{k}": {v}' for k, v in fields.items())

    prompt = (
        f"Extract the following fields from this document. "
        f"Respond ONLY with a JSON object, no other text, no markdown formatting.\n\n"
        f"Fields to extract:\n{field_list}\n\n"
        f"If a field cannot be found in the document, use null for that field."
    )

    doc_format = "pdf" if media_type == "application/pdf" else media_type.split("/")[-1]

    client = boto3.client("bedrock-runtime")
    response = client.converse(
        modelId=MODEL_ID,
        messages=[
            {
                "role": "user",
                "content": [
                    {"document": {"format": doc_format, "name": "statement", "source": {"bytes": file_bytes}}},
                    {"text": prompt},
                ],
            }
        ],
        inferenceConfig={"maxTokens": 500, "temperature": 0},
    )

    raw_text = response["output"]["message"]["content"][0]["text"]
    cleaned = raw_text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    try:
        extracted = json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise ValueError(f"Model did not return valid JSON: {raw_text}") from e

    return extracted
