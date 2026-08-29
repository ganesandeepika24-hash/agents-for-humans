"""
Tool: stage_approval_card

Generic assembler — takes fully-decided fields and packages them into the
ApprovalCard shape from docs/approval_card_contract.md. Contains no
scenario-specific judgment; that logic lives in per-scenario wrapper
functions like stage_tariff_card (below).
"""

from uuid import uuid4

from strands import tool

from .interfaces import Action, ApprovalCard, StageApprovalCardInput


@tool
def stage_approval_card(input: StageApprovalCardInput) -> ApprovalCard:
    if input.action_type == "email" and input.email_payload is None:
        raise ValueError("email_payload is required when action_type is 'email'")
    if input.action_type == "action_url" and input.action_url is None:
        raise ValueError("action_url is required when action_type is 'action_url'")

    return ApprovalCard(
        card_id=str(uuid4()),
        scenario_type=input.scenario_type,
        title=input.title,
        summary=input.summary,
        computed_savings_gbp=input.computed_savings_gbp,
        action=Action(
            type=input.action_type,
            email_payload=input.email_payload,
            action_url=input.action_url,
        ),
        status="pending",
    )
