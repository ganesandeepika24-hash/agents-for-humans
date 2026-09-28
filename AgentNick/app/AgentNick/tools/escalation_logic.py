"""
escalation_logic.py

Pure date-arithmetic logic for escalation tiers, with ZERO dependency
on Strands or any agent framework -- safe to import directly from the
backend's scheduler, which has no Strands SDK installed. escalation.py
imports this and wraps it as an agent @tool.
"""

from datetime import date

_TIERS = [
    (0.50, "too_early"),
    (0.25, "early_notice"),
    (0.10, "reminder"),
    (0.0, "urgent"),
]
_TIER_ORDER = ["too_early", "early_notice", "reminder", "urgent"]


def compute_escalation_tier(
    period_start_date: str, key_date: str, as_of_date: str,
    last_shown_tier: str | None = None,
) -> dict:
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

    should_notify = tier != "too_early" and (
        last_shown_tier is None
        or _TIER_ORDER.index(tier) > _TIER_ORDER.index(last_shown_tier)
    )

    return {
        "tier": tier, "percent_remaining": round(percent_remaining, 3),
        "days_remaining": days_remaining, "should_notify_now": should_notify,
    }
