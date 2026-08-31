"""
Tool: finalize_check

Called by the FM as the LAST action in a /check-style evaluation turn.
Its sole purpose is to receive the exact card(s) already produced by
stage_financial_card or request_missing_data as its actual arguments,
so a caller reading the tool-call INPUT (not regenerated prose) gets
a reliable, exact copy -- avoiding the FM re-typing/summarizing card
data inaccurately when asked to restate it in text.

Returns its input back unchanged; the real value is in the tool-call
input itself being observable by the backend via the network stream.
"""

from strands import tool


@tool
def finalize_check(cards: list[dict]) -> dict:
    """
    cards: the exact list of card objects already returned by
    stage_financial_card / request_missing_data during this turn.
    Pass an empty list if no cards were staged.
    """
    return {"cards": cards, "count": len(cards)}
