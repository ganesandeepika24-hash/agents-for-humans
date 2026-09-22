"""
openbanking_reader.py

Reads transaction data in the real TrueLayer Data API v1 response shape
(verified against a genuine sandbox response, not guessed) and feeds
recurring charges into the same pattern-detection logic already proven
with Gmail receipts.

Currently reads from a local mock dataset (openbanking_mock.json),
built to exactly match the real API's field names and structure.
Swapping this for a live TrueLayer connection later requires only
replacing _load_transactions() with a real API call -- everything
downstream (grouping, pattern inference) is already source-agnostic.
"""

import json
from pathlib import Path
from collections import defaultdict

_MOCK_DATA_PATH = Path(__file__).parent / "openbanking_mock.json"


def _load_transactions(user_id: str) -> list[dict]:
    """Loads transaction data. Currently reads the mock dataset for any
    user; a real implementation would use the user's stored TrueLayer
    access token to call GET /data/v1/accounts/{account_id}/transactions
    for each of their connected accounts."""
    with open(_MOCK_DATA_PATH) as f:
        data = json.load(f)
    return data.get("results", [])


def group_transactions_by_merchant(transactions: list[dict]) -> dict:
    """Groups transactions by their description field (the real API's
    merchant/counterparty name), mirroring how Gmail receipts are
    grouped by subject line -- same downstream pattern-detection logic
    can then process either source identically."""
    groups = defaultdict(list)
    for txn in transactions:
        key = txn.get("description", "").strip().upper()
        if key:
            groups[key].append(txn)
    return dict(groups)


def transactions_to_receipt_like_format(transactions: list[dict]) -> list[dict]:
    """Converts real transaction records into the same {"subject",
    "body"} shape infer_recurring_pattern already expects (since that
    function was built around email-shaped input) -- lets us reuse it
    unchanged rather than writing a second, parallel version."""
    converted = []
    for txn in transactions:
        amount = abs(txn.get("amount", 0))
        date = txn.get("timestamp", "")[:10]
        merchant = txn.get("description", "Unknown")
        converted.append({
            "subject": f"Transaction: {merchant}",
            "body": f"Date: {date}\nMerchant: {merchant}\nAmount: £{amount:.2f}\nType: {txn.get('transaction_type', '')}",
        })
    return converted


def fetch_recurring_candidates(user_id: str) -> dict:
    """Full pipeline: load transactions, group by merchant, return only
    groups with 2+ occurrences (a real, meaningful repeat pattern) in
    the receipt-like format the existing pattern-detection logic needs."""
    transactions = _load_transactions(user_id)
    grouped = group_transactions_by_merchant(transactions)
    candidates = {}
    for merchant, txns in grouped.items():
        if len(txns) >= 2:
            candidates[merchant] = transactions_to_receipt_like_format(txns)
    return candidates
