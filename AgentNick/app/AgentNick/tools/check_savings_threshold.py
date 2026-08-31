"""
Tool: check_savings_threshold

Makes the resolve_threshold/meets_threshold logic callable by the FM.
Simplified to flat parameters -- FM passes an optional override amount
and/or percent directly, rather than a nested settings object.
"""

from strands import tool
from pydantic import BaseModel

from .interfaces import ThresholdConfig, ThresholdMode, meets_threshold


class ThresholdCheckResult(BaseModel):
    meets_threshold: bool
    threshold_source: str
    resolved_min_gbp: float | None
    resolved_min_pct: float | None


@tool
def check_savings_threshold(
    amount_gbp: float,
    base_amount_gbp: float,
    user_min_gbp_override: float | None = None,
    user_min_pct_override: float | None = None,
) -> ThresholdCheckResult:
    if user_min_gbp_override is not None or user_min_pct_override is not None:
        config = ThresholdConfig(
            mode=ThresholdMode.OR,
            min_savings_gbp=user_min_gbp_override,
            min_savings_pct=user_min_pct_override,
        )
        source = "user_override"
    else:
        config = ThresholdConfig(mode=ThresholdMode.OR, min_savings_gbp=15.0, min_savings_pct=10.0)
        source = "system_default"

    result = meets_threshold(amount_gbp, base_amount_gbp, config)

    return ThresholdCheckResult(
        meets_threshold=result,
        threshold_source=source,
        resolved_min_gbp=config.min_savings_gbp,
        resolved_min_pct=config.min_savings_pct,
    )
