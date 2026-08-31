"""
Tool: parse_financial_signals

Normalizes ANY raw financial signal data into one common FinancialSignal
shape. Rather than a hardcoded table of known field names per scenario
type, the caller (the FM) specifies which field holds the key date and
which holds the key monetary amount — this keeps the tool genuinely
generic across any scenario, not just the three originally demoed.
"""

from datetime import date

from strands import tool

from .interfaces import FinancialSignal


@tool
def parse_financial_signals(
    source_type: str,
    raw_data: dict,
    key_date_field: str,
    monetary_field: str,
    user_id_field: str = "user_id",
    as_of_date: str | None = None,
) -> FinancialSignal:
    """
    Normalize a raw financial record into a FinancialSignal.

    source_type: a short label for what kind of signal this is (e.g.
        "tariff", "trial", "card_promo", or any other kind).
    raw_data: the raw dict of fields for this signal.
    key_date_field: which key in raw_data holds the date that matters
        (contract end, trial end, promo end, deadline, etc).
    monetary_field: which key in raw_data holds the amount at stake.
    user_id_field: which key in raw_data holds the user identifier.
        Defaults to "user_id".
    as_of_date: ISO date string (YYYY-MM-DD) to treat as "today". Defaults
        to the real current date if not given.
    """
    today = date.fromisoformat(as_of_date) if as_of_date else date.today()

    if key_date_field not in raw_data:
        raise ValueError(f"Field '{key_date_field}' not found in raw_data")
    if monetary_field not in raw_data:
        raise ValueError(f"Field '{monetary_field}' not found in raw_data")
    if user_id_field not in raw_data:
        raise ValueError(f"Field '{user_id_field}' not found in raw_data")

    key_date = date.fromisoformat(raw_data[key_date_field])
    days_until = (key_date - today).days

    return FinancialSignal(
        source_type=source_type,
        user_id=raw_data[user_id_field],
        key_date=key_date,
        days_until_key_date=days_until,
        monetary_amount_gbp=float(raw_data[monetary_field]),
        raw_data=raw_data,
    )
