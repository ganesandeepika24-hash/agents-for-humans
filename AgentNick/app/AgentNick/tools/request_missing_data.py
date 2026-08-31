"""
Tool: request_missing_data

The FM calls this instead of guessing or fabricating a number when it
doesn't have what it needs to make a confident recommendation.
"""

from strands import tool

from .interfaces import ApprovalCard, CardOption, CardOptionType, StageApprovalCardInput
from .stage_approval_card import stage_approval_card


@tool
def request_missing_data(
    scenario_type: str,
    what_is_missing: list[str],
    why_needed: str,
    can_upload_document: bool = True,
) -> ApprovalCard:
    missing_list = ", ".join(what_is_missing)
    summary = f"I don\'t have: {missing_list}. {why_needed}"

    options = [
        CardOption(label="Enter Manually", option_type=CardOptionType.MANUAL_INPUT, requested_fields=what_is_missing),
    ]
    if can_upload_document:
        options.append(CardOption(
            label="Upload a Document",
            option_type=CardOptionType.DOCUMENT_UPLOAD,
            requested_fields=what_is_missing,
        ))

    return stage_approval_card(StageApprovalCardInput(
        scenario_type=scenario_type,
        title="A few details needed to help with this",
        summary=summary,
        computed_savings_gbp=None,
        options=options,
    ))
