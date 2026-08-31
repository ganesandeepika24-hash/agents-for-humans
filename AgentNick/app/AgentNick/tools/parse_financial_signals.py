"""
Tool: parse_financial_signals

Normalizes ANY raw financial signal data into one common FinancialSignal
shape. The caller (the FM) specifies which fields hold the key date,
the key monetary amount, and a stable identity field -- keeps the tool
generic across any scenario.
"""

import hashlib
from datetime import date

from strands import tool

from .interfaces import FinancialSignal


@tool
def parse_financial_signals(
    source_type: str,
    raw_data: dict,
    key_date_field: str,
    monetary_field: str,
    identity_field: str,
    user_id_field: str = "user_id",
    as_of_date: str | None = None,
) -> FinancialSignal:
    """
    Normalize a raw financial record into a FinancialSignal.

    source_type: a short label for what kind of signal this is.
    raw_data: the raw dict of fields for this signal.
    key_date_field: which key in raw_data holds the date that matters.
    monetary_field: which key in raw_data holds the amount at stake.
    identity_field: which key in raw_data holds a STABLE business
        identifier for this specific commitment -- e.g. "provider",
        "service", "card_provider". Must NOT be a date or a monetary
        amount, since those can legitimately change between checks.
        This is what signal_id is built from, so choosing consistently
        for the same commitment across repeated checks is essential --
        do not pick different fields for the same kind of signal on
        different calls.
    user_id_field: which key in raw_data holds the user identifier.
    as_of_date: ISO date string (YYYY-MM-DD) to treat as "today".
    """
    today = date.fromisoformat(as_of_date) if as_of_date else date.today()

    for field in (key_date_field, monetary_field, identity_field, user_id_field):
        if field not in raw_data:
            raise ValueError(f"Field '{field}' not found in raw_data")

    key_date = date.fromisoformat(raw_data[key_date_field])
    days_until = (key_date - today).days
    user_id = raw_data[user_id_field]

    # Deterministic identity built from STABLE fields only (user, scenario
    # type, business identifier) -- deliberately excludes the date, since
    # different date fields or values must not change the identity of the
    # same underlying commitment.
    fingerprint_source = f"{user_id}|{source_type}|{raw_data[identity_field]}"
    signal_id = hashlib.sha256(fingerprint_source.encode()).hexdigest()[:16]

    return FinancialSignal(
        signal_id=signal_id,
        source_type=source_type,
        user_id=user_id,
        key_date=key_date,
        days_until_key_date=days_until,
        monetary_amount_gbp=float(raw_data[monetary_field]),
        raw_data=raw_data,
    )
