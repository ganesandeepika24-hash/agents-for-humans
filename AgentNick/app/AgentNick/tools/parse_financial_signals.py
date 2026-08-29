"""
Tool: parse_financial_signals

Normalizes raw mock data (tariff / trial / card_promo) into one common
FinancialSignal shape, so downstream evaluators don't each need to know
about all three raw data formats.
"""

from datetime import date

from strands import tool

from .interfaces import FinancialSignal, ParseSignalsInput


# Maps each source_type to which raw field holds the "date that matters"
# and which raw field holds "the number at stake".
_KEY_DATE_FIELDS = {
    "tariff": "contract_end_date",
    "trial": "trial_end_date",
    "card_promo": "promo_apr_end_date",
}

_MONETARY_FIELDS = {
    "tariff": "current_price_gbp",
    "trial": "auto_bill_amount_gbp",
    "card_promo": "current_balance_gbp",
}


@tool
def parse_financial_signals(input: ParseSignalsInput, as_of_date: date | None = None) -> FinancialSignal:
    """
    Normalize a raw tariff / trial / card_promo record into a FinancialSignal.

    as_of_date defaults to date.today() for real usage. Tests and demo
    scripts can pass an explicit date for deterministic, repeatable output.
    """
    today = as_of_date or date.today()
    raw = input.raw_data
    source_type = input.source_type

    if source_type not in _KEY_DATE_FIELDS:
        raise ValueError(f"Unknown source_type: {source_type}")

    key_date_field = _KEY_DATE_FIELDS[source_type]
    monetary_field = _MONETARY_FIELDS[source_type]

    if key_date_field not in raw:
        raise ValueError(f"Expected field '{key_date_field}' missing from raw_data for source_type '{source_type}'")
    if monetary_field not in raw:
        raise ValueError(f"Expected field '{monetary_field}' missing from raw_data for source_type '{source_type}'")
    if "user_id" not in raw:
        raise ValueError("Expected field 'user_id' missing from raw_data")

    key_date = date.fromisoformat(raw[key_date_field])
    days_until = (key_date - today).days

    return FinancialSignal(
        source_type=source_type,
        user_id=raw["user_id"],
        key_date=key_date,
        days_until_key_date=days_until,
        monetary_amount_gbp=float(raw[monetary_field]),
        raw_data=raw,
    )
