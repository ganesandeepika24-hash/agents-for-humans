"""
Tool: stage_financial_card

Generic card-staging tool. Accepts options as a list of plain dicts.
Uses normalize_card.normalize_options for defensive parsing (shared
with finalize_check, since both handle FM-produced option dicts that
may not perfectly match the schema).

signal_id must be the exact value returned by parse_financial_signals
for this evaluation -- this is what lets the backend recognize repeat
checks of the same underlying commitment and avoid re-notifying about
an unchanged fact.
"""

from strands import tool

from .interfaces import ApprovalCard
from .normalize_card import normalize_options
from .stage_approval_card import stage_approval_card


@tool
def stage_financial_card(
    scenario_type: str,
    signal_id: str,
    title: str,
    summary: str,
    options: list[dict],
    computed_savings_gbp: float | None = None,
    extra_data: dict | None = None,
) -> ApprovalCard:
    parsed_options = normalize_options(options)

    return stage_approval_card(
        scenario_type=scenario_type,
        signal_id=signal_id,
        title=title,
        summary=summary,
        options=parsed_options,
        computed_savings_gbp=computed_savings_gbp,
        extra_data=extra_data,
    )
