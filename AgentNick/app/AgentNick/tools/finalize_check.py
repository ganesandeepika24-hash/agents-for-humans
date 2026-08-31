"""
Tool: finalize_check

Called by the FM as the LAST action in a /check-style evaluation turn.
Its sole purpose is to receive the exact card(s) already produced by
stage_financial_card or request_missing_data as its actual arguments,
so a caller reading the tool-call INPUT (not regenerated prose) gets
a reliable, exact copy.

Since the FM is re-transcribing these cards from its own context (not
literally passing through the same Python object), it can reintroduce
malformed option fields even for a card built correctly the first
time. This function re-normalizes each card's options through the same
normalize_card helper stage_financial_card uses, as a safety net.
"""

from strands import tool

from .normalize_card import normalize_options


@tool
def finalize_check(cards: list[dict]) -> dict:
    """
    cards: the exact list of card objects already returned by
    stage_financial_card / request_missing_data during this turn.
    Pass an empty list if no cards were staged.
    """
    cleaned_cards = []
    for card in cards:
        if "options" in card and isinstance(card["options"], list):
            normalized = normalize_options(card["options"])
            card = {**card, "options": [opt.model_dump() for opt in normalized]}
        cleaned_cards.append(card)

    return {"cards": cleaned_cards, "count": len(cleaned_cards)}
