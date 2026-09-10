"""
Tool: check_cooling_off_period

A small, honestly-labeled reference table of typical cooling-off
windows by category -- NOT a legal source, genuinely varies by
jurisdiction/provider/contract terms. Flagged clearly in docs and
README as illustrative, not authoritative.
"""

from datetime import date
from strands import tool
from pydantic import BaseModel

_TYPICAL_WINDOWS_DAYS = {
    "tariff": 14,
    "card_promo": 14,
    "trial": 0,  # trials are pre-charge, not post-signup cooling-off
    "insurance": 14,
    "gym": 14,
}


class CoolingOffResult(BaseModel):
    within_window: bool
    days_remaining_in_window: int
    window_days_used: int
    note: str


@tool
def check_cooling_off_period(
    scenario_type: str,
    contract_start_date: str,
    as_of_date: str,
) -> CoolingOffResult:
    """
    contract_start_date: when the user signed up / the contract began
        (NOT the renewal/end date).
    Returns whether the user may still be within a typical
    penalty-free exit window for this category -- illustrative only,
    always tell the user to verify their specific contract terms.
    """
    window_days = _TYPICAL_WINDOWS_DAYS.get(scenario_type, 14)
    start = date.fromisoformat(contract_start_date)
    today = date.fromisoformat(as_of_date)
    days_since_start = (today - start).days
    remaining = window_days - days_since_start

    return CoolingOffResult(
        within_window=remaining > 0,
        days_remaining_in_window=max(0, remaining),
        window_days_used=window_days,
        note=(
            f"Based on a typical {window_days}-day window for this category "
            f"-- this is illustrative, not a legal guarantee. Actual "
            f"cooling-off rights vary by provider and jurisdiction; the "
            f"user should verify their specific contract terms."
        ),
    )
