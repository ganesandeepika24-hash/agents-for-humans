"""
Tool: parse_financial_signals

Normalizes ANY raw financial signal data into one common FinancialSignal
shape. The caller (the FM) specifies which fields hold the key date,
the key monetary amount, and a stable identity field -- keeps the tool
generic across any scenario.

Includes built-in sanity checks on the FM's field choices (comment 50)
-- these run automatically on every call, so they can't be skipped the
way a separate "please verify your choices" tool could be. Catches the
exact class of bug that caused the earlier signal_id instability issue
(the FM choosing a date-like or numeric value for identity_field).
"""

import hashlib
import re
from datetime import date

from strands import tool

from .interfaces import FinancialSignal

_DATE_LIKE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}")
_NUMERIC_PATTERN = re.compile(r"^-?\d+(\.\d+)?$")


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
    user_id_field: which key in raw_data holds the user identifier.
    as_of_date: ISO date string (YYYY-MM-DD) to treat as "today".

    Raises ValueError with a clear, correctable message if any chosen
    field doesn't exist, or if identity_field's value looks like a date
    or a plain number (a strong sign the wrong field was chosen) -- fix
    your field choice and call this again.
    """
    today = date.fromisoformat(as_of_date) if as_of_date else date.today()

    for field in (key_date_field, monetary_field, identity_field, user_id_field):
        if field not in raw_data:
            raise ValueError(
                f"Field '{field}' not found in raw_data. Available fields: "
                f"{list(raw_data.keys())}. Choose an existing field name."
            )

    identity_value = str(raw_data[identity_field])
    if _DATE_LIKE_PATTERN.match(identity_value):
        raise ValueError(
            f"identity_field='{identity_field}' has value '{identity_value}', which "
            f"looks like a date. identity_field must be a STABLE business identifier "
            f"(e.g. a provider or service name), never a date -- dates change between "
            f"checks and would break the system's ability to recognize this as the "
            f"same commitment later. Choose a different field, such as one holding a "
            f"company or service name."
        )
    if _NUMERIC_PATTERN.match(identity_value):
        raise ValueError(
            f"identity_field='{identity_field}' has value '{identity_value}', which "
            f"is purely numeric. identity_field must be a STABLE business identifier "
            f"(a name), not an amount or a number that could plausibly change. Choose "
            f"a different field, such as one holding a company or service name."
        )

    try:
        key_date = date.fromisoformat(raw_data[key_date_field])
    except (ValueError, TypeError):
        raise ValueError(
            f"key_date_field='{key_date_field}' has value '{raw_data[key_date_field]}', "
            f"which is not a valid YYYY-MM-DD date. Choose a field that actually "
            f"contains a date."
        )

    try:
        monetary_value = float(raw_data[monetary_field])
    except (ValueError, TypeError):
        raise ValueError(
            f"monetary_field='{monetary_field}' has value '{raw_data[monetary_field]}', "
            f"which is not a valid number. Choose a field that actually contains an "
            f"amount."
        )

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
        monetary_amount_gbp=monetary_value,
        raw_data=raw_data,
    )
