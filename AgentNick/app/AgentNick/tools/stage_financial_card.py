"""
Tool: stage_financial_card

Generic card-staging tool. Accepts options as a list of plain dicts.
Tolerant of extra/unexpected keys the FM includes (description,
impact_gbp, etc -- ignored). Unrecognized option_type values fall back
to "dismiss" rather than raising, since we can't enumerate every phrase
an FM might use for a no-action option ("none", "no_action", "skip").

signal_id must be the exact value returned by parse_financial_signals
for this evaluation -- this is what lets the backend recognize repeat
checks of the same underlying commitment and avoid re-notifying about
an unchanged fact.
"""

from strands import tool

from .interfaces import ApprovalCard, CardOption, CardOptionType, EmailPayload
from .stage_approval_card import stage_approval_card

_VALID_TYPES = {t.value for t in CardOptionType}


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
    parsed_options = []
    for opt in options:
        raw_type = opt.get("option_type") or opt.get("action_type") or "dismiss"
        if raw_type not in _VALID_TYPES:
            raw_type = "dismiss"

        email_payload = None
        if opt.get("email_to"):
            email_payload = EmailPayload(
                to=opt["email_to"],
                subject=opt.get("email_subject", ""),
                body=opt.get("email_body", ""),
            )

        option_type = CardOptionType(raw_type)
        action_url = opt.get("action_url") if option_type == CardOptionType.ACTION_URL else None
        if option_type == CardOptionType.EMAIL and email_payload is None:
            option_type = CardOptionType.DISMISS

        parsed_options.append(CardOption(
            label=opt.get("label", "Option"),
            option_type=option_type,
            email_payload=email_payload,
            action_url=action_url,
        ))

    return stage_approval_card(
        scenario_type=scenario_type,
        signal_id=signal_id,
        title=title,
        summary=summary,
        options=parsed_options,
        computed_savings_gbp=computed_savings_gbp,
        extra_data=extra_data,
    )
