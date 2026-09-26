"""
openbanking_mock_generator.py

Generates realistic Open Banking transaction data with dates computed
relative to today -- avoids the staleness problem of a hardcoded
static file, where "last charge: 14 September" looks increasingly odd
as real time passes it by.

Includes multiple genuine recurring patterns (not just one), plus
realistic one-off purchases, matching the real shape verified against
TrueLayer's sandbox in an earlier session.
"""

import json
from datetime import datetime, timedelta


def _iso(days_ago: int) -> str:
    return (datetime.utcnow() - timedelta(days=days_ago)).strftime("%Y-%m-%dT00:00:00Z")


def generate_mock_transactions() -> dict:
    """Three genuine recurring patterns (different frequencies), plus
    several realistic one-off purchases that should NOT be detected as
    recurring (only 1 occurrence each)."""
    transactions = []
    balance = 1500.0

    # Recurring pattern 1: Anthropic, monthly, 3 occurrences
    for i, days_ago in enumerate([60, 30, 1]):
        balance -= 16.0
        transactions.append({
            "timestamp": _iso(days_ago), "description": "ANTHROPIC",
            "transaction_type": "DEBIT", "transaction_category": "PURCHASE",
            "transaction_classification": [], "amount": -16.0, "currency": "GBP",
            "transaction_id": f"mock-anthropic-{i:03d}",
            "provider_transaction_id": f"mock-provider-{i:03d}",
            "normalised_provider_transaction_id": f"txn-mock-anthropic-{i:03d}",
            "running_balance": {"currency": "GBP", "amount": round(balance, 2)},
            "meta": {"provider_transaction_category": "DEB"},
        })

    # Recurring pattern 2: PulseFit Gym, monthly, 2 occurrences
    for i, days_ago in enumerate([45, 15]):
        balance -= 45.0
        transactions.append({
            "timestamp": _iso(days_ago), "description": "PULSEFIT GYM",
            "transaction_type": "DEBIT", "transaction_category": "PURCHASE",
            "transaction_classification": [], "amount": -45.0, "currency": "GBP",
            "transaction_id": f"mock-pulsefit-{i:03d}",
            "provider_transaction_id": f"mock-provider-pf-{i:03d}",
            "normalised_provider_transaction_id": f"txn-mock-pulsefit-{i:03d}",
            "running_balance": {"currency": "GBP", "amount": round(balance, 2)},
            "meta": {"provider_transaction_category": "DEB"},
        })

    # Recurring pattern 3: Reelbox streaming, monthly, 4 occurrences
    for i, days_ago in enumerate([90, 60, 30, 2]):
        balance -= 12.99
        transactions.append({
            "timestamp": _iso(days_ago), "description": "REELBOX STREAMING",
            "transaction_type": "DEBIT", "transaction_category": "PURCHASE",
            "transaction_classification": [], "amount": -12.99, "currency": "GBP",
            "transaction_id": f"mock-reelbox-{i:03d}",
            "provider_transaction_id": f"mock-provider-rb-{i:03d}",
            "normalised_provider_transaction_id": f"txn-mock-reelbox-{i:03d}",
            "running_balance": {"currency": "GBP", "amount": round(balance, 2)},
            "meta": {"provider_transaction_category": "DEB"},
        })

    # Realistic one-off purchases -- should NOT be detected as recurring
    one_offs = [
        ("TESCO STORES", -34.52, 5), ("AMAZON UK", -18.99, 12),
        ("TFL TRAVEL", -8.90, 8), ("COSTA COFFEE", -4.65, 3),
        ("BOOTS PHARMACY", -12.30, 20),
    ]
    for i, (desc, amount, days_ago) in enumerate(one_offs):
        balance += amount
        transactions.append({
            "timestamp": _iso(days_ago), "description": desc,
            "transaction_type": "DEBIT", "transaction_category": "PURCHASE",
            "transaction_classification": [], "amount": amount, "currency": "GBP",
            "transaction_id": f"mock-oneoff-{i:03d}",
            "provider_transaction_id": f"mock-provider-oo-{i:03d}",
            "normalised_provider_transaction_id": f"txn-mock-oneoff-{i:03d}",
            "running_balance": {"currency": "GBP", "amount": round(balance, 2)},
            "meta": {"provider_transaction_category": "DEB"},
        })

    transactions.sort(key=lambda t: t["timestamp"], reverse=True)
    return {"results": transactions, "status": "Succeeded"}


if __name__ == "__main__":
    data = generate_mock_transactions()
    with open("openbanking_mock.json", "w") as f:
        json.dump(data, f, indent=2)
    print(f"Generated {len(data['results'])} transactions, dates relative to today ({datetime.utcnow().strftime('%Y-%m-%d')})")
