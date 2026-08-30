"""
Tool: stage_approval_card

Generic assembler — takes fully-decided fields and packages them into the
ApprovalCard shape from docs/approval_card_contract.md. Contains no
scenario-specific judgment; that logic lives in per-scenario wrapper
functions like stage_tariff_card, stage_trial_card, stage_card_promo_card.
"""

from uuid import uuid4

from strands import tool

from .interfaces import ApprovalCard, StageApprovalCardInput


@tool
def stage_approval_card(input: StageApprovalCardInput) -> ApprovalCard:
    if not input.options:
        raise ValueError("At least one CardOption is required")

    for opt in input.options:
        if opt.option_type == "email" and opt.email_payload is None:
            raise ValueError(f"Option '{opt.label}' has type 'email' but no email_payload")
        if opt.option_type == "action_url" and opt.action_url is None:
            raise ValueError(f"Option '{opt.label}' has type 'action_url' but no action_url")

    return ApprovalCard(
        card_id=str(uuid4()),
        scenario_type=input.scenario_type,
        title=input.title,
        summary=input.summary,
        computed_savings_gbp=input.computed_savings_gbp,
        options=input.options,
        status="pending",
        extra_data=input.extra_data,
    )
