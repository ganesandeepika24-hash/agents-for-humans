"""
Tool: check_escalation_tier

Thin agent-tool wrapper around escalation_logic.compute_escalation_tier
(kept in a separate, Strands-free file so the backend's scheduler can
import the pure logic directly without needing the Strands SDK).
"""

from strands import tool
from pydantic import BaseModel
from .escalation_logic import compute_escalation_tier


class EscalationResult(BaseModel):
    tier: str
    percent_remaining: float
    days_remaining: int
    should_notify_now: bool


@tool
def check_escalation_tier(
    period_start_date: str, key_date: str, as_of_date: str,
    last_shown_tier: str | None = None,
) -> EscalationResult:
    """
    period_start_date: when this recurring period began.
    key_date: the date this period ends/renews.
    last_shown_tier: the tier this exact signal was last shown at, if
        any (None if never shown).
    """
    result = compute_escalation_tier(period_start_date, key_date, as_of_date, last_shown_tier)
    return EscalationResult(**result)
