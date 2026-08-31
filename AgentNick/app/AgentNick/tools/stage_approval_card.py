"""
Tool: stage_approval_card

Generic assembler — takes fully-decided fields and packages them into the
ApprovalCard shape. Not FM-callable directly (uses flat params here since
it's called internally by stage_financial_card / request_missing_data,
both of which ARE FM-callable with flat signatures per the Strands
nested-Pydantic tool-calling limitation).
"""

from uuid import uuid4

from strands import tool

from .interfaces import ApprovalCard, CardOption


def stage_approval_card(
    scenario_type: str,
    signal_id: str,
    title: str,
    summary: str,
    options: list[CardOption],
    computed_savings_gbp: float | None = None,
    extra_data: dict | None = None,
) -> ApprovalCard:
    if not options:
        raise ValueError("At least one CardOption is required")

    for opt in options:
        if opt.option_type == "email" and opt.email_payload is None:
            raise ValueError(f"Option '{opt.label}' has type 'email' but no email_payload")
        if opt.option_type == "action_url" and opt.action_url is None:
            raise ValueError(f"Option '{opt.label}' has type 'action_url' but no action_url")

    return ApprovalCard(
        card_id=str(uuid4()),
        signal_id=signal_id,
        scenario_type=scenario_type,
        title=title,
        summary=summary,
        computed_savings_gbp=computed_savings_gbp,
        options=options,
        status="pending",
        extra_data=extra_data,
    )
