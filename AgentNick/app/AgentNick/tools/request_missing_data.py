"""
Tool: request_missing_data

The FM calls this instead of guessing or fabricating a number when it
doesn't have what it needs to make a confident recommendation for ANY
scenario. Produces a card asking the user to provide the missing
information manually or via document upload, rather than proceeding
on an assumption.
"""

from strands import tool

from .interfaces import (
    ApprovalCard,
    CardOption,
    CardOptionType,
    MissingDataRequest,
    StageApprovalCardInput,
)
from .stage_approval_card import stage_approval_card


@tool
def request_missing_data(input: MissingDataRequest, scenario_type: str) -> ApprovalCard:
    missing_list = ", ".join(input.what_is_missing)
    summary = f"I don't have: {missing_list}. {input.why_needed}"

    options = [
        CardOption(
            label="Enter Manually",
            option_type=CardOptionType.MANUAL_INPUT,
            requested_fields=input.what_is_missing,
        ),
    ]
    if input.can_upload_document:
        options.append(CardOption(
            label="Upload a Document",
            option_type=CardOptionType.DOCUMENT_UPLOAD,
            requested_fields=input.what_is_missing,
        ))

    return stage_approval_card(StageApprovalCardInput(
        scenario_type=scenario_type,
        title="A few details needed to help with this",
        summary=summary,
        computed_savings_gbp=None,
        options=options,
    ))
