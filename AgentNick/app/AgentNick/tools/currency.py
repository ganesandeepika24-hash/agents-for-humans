"""
Tool: convert_currency

Uses a real, free, live exchange-rate API (exchangerate-api.com) --
no API key required, rates updated daily. Falls back to a small
illustrative reference table only if the live API is unreachable,
so a transient network issue never breaks a card evaluation.
"""

import requests
from strands import tool
from pydantic import BaseModel

# Fallback only, used if the live API call fails -- not the primary path
_FALLBACK_RATES_TO_GBP = {
    "GBP": 1.0, "USD": 0.79, "EUR": 0.86, "INR": 0.0095, "AUD": 0.52, "CAD": 0.58,
}

_API_URL = "https://api.exchangerate-api.com/v4/latest/GBP"
_TIMEOUT_SECONDS = 5


class CurrencyConversionResult(BaseModel):
    original_amount: float
    original_currency: str
    gbp_equivalent: float
    note: str


@tool
def convert_currency(amount: float, from_currency: str) -> CurrencyConversionResult:
    currency = from_currency.upper()

    if currency == "GBP":
        return CurrencyConversionResult(
            original_amount=amount, original_currency=currency,
            gbp_equivalent=round(amount, 2), note="Already in GBP.",
        )

    try:
        response = requests.get(_API_URL, timeout=_TIMEOUT_SECONDS)
        response.raise_for_status()
        rates = response.json().get("rates", {})
        gbp_to_currency_rate = rates.get(currency)
        if gbp_to_currency_rate:
            # API gives GBP -> currency; we need currency -> GBP, so invert
            gbp_equivalent = amount / gbp_to_currency_rate
            return CurrencyConversionResult(
                original_amount=amount, original_currency=currency,
                gbp_equivalent=round(gbp_equivalent, 2),
                note=f"Live exchange rate as of {response.json().get('date', 'today')}.",
            )
    except Exception:
        pass  # fall through to fallback table below

    fallback_rate = _FALLBACK_RATES_TO_GBP.get(currency)
    if fallback_rate is None:
        return CurrencyConversionResult(
            original_amount=amount, original_currency=currency,
            gbp_equivalent=amount,
            note=f"No rate available for {currency}; showing original amount unconverted.",
        )
    return CurrencyConversionResult(
        original_amount=amount, original_currency=currency,
        gbp_equivalent=round(amount * fallback_rate, 2),
        note="Live rate unavailable -- used fallback reference rate.",
    )
