"""
Tool: check_escalation_tier

Determines whether a signal is worth surfacing RIGHT NOW based on what
percentage of its total period remains -- not a fixed day count, so a
7-day trial and an 18-month promotion scale sensibly against the same
logic. Returns a tier the caller can compare against what was last
shown, to decide whether to (re)notify.
"""

from datetime import date
from strands import tool
from pydantic import BaseModel

_TIERS = [
    (0.50, "too_early"),      # >50% of period remains -- stay quiet
    (0.25, "early_notice"),   # 25-50% remains -- one calm mention
    (0.10, "reminder"),       # 10-25% remains -- a real follow-up
    (0.0, "urgent"),          # <10% remains -- urgent, may recur daily
]


class EscalationResult(BaseModel):
    tier: str
    percent_remaining: float
    days_remaining: int
    should_notify_now: bool


@tool
def check_escalation_tier(
    period_start_date: str,
    key_date: str,
    as_of_date: str,
    last_shown_tier: str | None = None,
) -> EscalationResult:
    """
    period_start_date: when this recurring period began (contract
        start, trial start, policy start) -- required to compute what
        FRACTION of the period remains, not just an absolute day count.
    key_date: the date this period ends/renews.
    last_shown_tier: the tier this exact signal was last shown at, if
        any (None if never shown). Used to decide whether the current
        tier represents genuine new escalation worth re-notifying about.
    """
    start = date.fromisoformat(period_start_date)
    end = date.fromisoformat(key_date)
    today = date.fromisoformat(as_of_date)

    total_days = max((end - start).days, 1)
    days_remaining = (end - today).days
    percent_remaining = max(days_remaining, 0) / total_days

    tier = "urgent"
    for threshold, tier_name in _TIERS:
        if percent_remaining >= threshold:
            tier = tier_name
            break

    tier_order = ["too_early", "early_notice", "reminder", "urgent"]
    should_notify = tier != "too_early" and (
        last_shown_tier is None
        or tier_order.index(tier) > tier_order.index(last_shown_tier)
    )

    return EscalationResult(
        tier=tier, percent_remaining=round(percent_remaining, 3),
        days_remaining=days_remaining, should_notify_now=should_notify,
    )
