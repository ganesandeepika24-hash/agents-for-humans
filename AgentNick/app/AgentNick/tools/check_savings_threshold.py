"""
Tool: check_savings_threshold

Makes the existing resolve_threshold/meets_threshold logic callable by
the FM. Wraps both into one step: resolve which threshold config applies
for this scenario (system default / user global / per-scenario override),
then check whether the given amount clears it.
"""

from strands import tool
from pydantic import BaseModel

from .interfaces import UserThresholdSettings, meets_threshold, resolve_threshold


class CheckThresholdInput(BaseModel):
    scenario_type: str
    amount_gbp: float
    base_amount_gbp: float
    user_settings: UserThresholdSettings | None = None


class ThresholdCheckResult(BaseModel):
    meets_threshold: bool
    threshold_source: str
    resolved_min_gbp: float | None
    resolved_min_pct: float | None


@tool
def check_savings_threshold(input: CheckThresholdInput) -> ThresholdCheckResult:
    resolved = resolve_threshold(input.scenario_type, input.user_settings)
    result = meets_threshold(input.amount_gbp, input.base_amount_gbp, resolved.config)

    return ThresholdCheckResult(
        meets_threshold=result,
        threshold_source=resolved.source,
        resolved_min_gbp=resolved.config.min_savings_gbp,
        resolved_min_pct=resolved.config.min_savings_pct,
    )
