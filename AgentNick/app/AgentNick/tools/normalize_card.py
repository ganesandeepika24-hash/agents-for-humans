"""
normalize_card.py

Shared defensive normalization for card option dicts coming from FM
tool-call arguments. Used by BOTH stage_financial_card (first pass,
building a card) and finalize_check (second pass, where the FM
re-transcribes the card from its own context -- and can reintroduce
malformed/inconsistent field names even for a card that was already
correctly built once).
"""

from .interfaces import CardOption, CardOptionType, EmailPayload

_VALID_TYPES = {t.value for t in CardOptionType}


def normalize_options(options: list[dict]) -> list[CardOption]:
    parsed_options = []
    for opt in options:
        raw_type = (
            opt.get("option_type")
            or opt.get("action_type")
            or opt.get("type")
            or "dismiss"
        )
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

        # action_url may show up under "action_url" or, when the FM
        # uses a "type"/"value" pair instead, under "value".
        action_url = None
        if option_type == CardOptionType.ACTION_URL:
            action_url = opt.get("action_url") or opt.get("value")

        if option_type == CardOptionType.EMAIL and email_payload is None:
            option_type = CardOptionType.DISMISS

        parsed_options.append(CardOption(
            label=opt.get("label", "Option"),
            option_type=option_type,
            email_payload=email_payload,
            action_url=action_url,
        ))
    return parsed_options
