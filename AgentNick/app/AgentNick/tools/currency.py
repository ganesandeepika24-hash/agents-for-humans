"""
Tool: convert_currency

A small, illustrative reference exchange-rate table -- NOT a live feed.
Clearly labeled as such; a real version would connect to a live FX API
(documented as roadmap). Lets the agent show GBP-equivalent figures
for non-GBP amounts so UK-based comparisons remain meaningful.
"""

from strands import tool
from pydantic import BaseModel

# Illustrative reference rates (to GBP), NOT live -- roadmap: real FX API
_REFERENCE_RATES_TO_GBP = {
    "GBP": 1.0,
    "USD": 0.79,
    "EUR": 0.86,
    "INR": 0.0095,
    "AUD": 0.52,
    "CAD": 0.58,
}


class CurrencyConversionResult(BaseModel):
    original_amount: float
    original_currency: str
    gbp_equivalent: float
    note: str


@tool
def convert_currency(amount: float, from_currency: str) -> CurrencyConversionResult:
    currency = from_currency.upper()
    rate = _REFERENCE_RATES_TO_GBP.get(currency)
    if rate is None:
        return CurrencyConversionResult(
            original_amount=amount, original_currency=currency,
            gbp_equivalent=amount,
            note=f"No reference rate available for {currency}; showing original amount unconverted.",
        )
    return CurrencyConversionResult(
        original_amount=amount, original_currency=currency,
        gbp_equivalent=round(amount * rate, 2),
        note="Illustrative reference rate, not live/real-time -- for demonstration purposes only.",
    )
