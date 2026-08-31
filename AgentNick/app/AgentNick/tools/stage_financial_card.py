"""
Tool: stage_financial_card

Generic card-staging tool. Accepts options as a list of plain dicts
(each with label, option_type, and optionally email_to/email_subject/
email_body or action_url) rather than a nested Pydantic list, since
flat/dict types are reliable with Strands tool-calling while nested
BaseModel parameters are not.
"""

from strands import tool

from .interfaces import (
    ApprovalCard,
    CardOption,
    CardOptionType,
    EmailPayload,
    StageApprovalCardInput,
)
from .stage_approval_card import stage_approval_card


@tool
def stage_financial_card(
    scenario_type: str,
    title: str,
    summary: str,
    options: list[dict],
    computed_savings_gbp: float | None = None,
    extra_data: dict | None = None,
) -> ApprovalCard:
    parsed_options = []
    for opt in options:
        email_payload = None
        if opt.get("email_to"):
            email_payload = EmailPayload(
                to=opt["email_to"],
                subject=opt.get("email_subject", ""),
                body=opt.get("email_body", ""),
            )
        parsed_options.append(CardOption(
            label=opt["label"],
            option_type=CardOptionType(opt["option_type"]),
            email_payload=email_payload,
            action_url=opt.get("action_url"),
        ))

    return stage_approval_card(StageApprovalCardInput(
        scenario_type=scenario_type,
        title=title,
        summary=summary,
        computed_savings_gbp=computed_savings_gbp,
        options=parsed_options,
        extra_data=extra_data,
    ))
