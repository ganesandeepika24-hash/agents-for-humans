"""
evals/assertions.py

Assertion functions referenced by scenarios.py. Each takes the full
result of an evaluation (cards produced + raw text) and returns
(passed: bool, reason: str).
"""

_KNOWN_REAL_UK_BANKS = [
    "HSBC", "Barclays", "Lloyds", "NatWest", "Santander", "Virgin Money",
    "Monzo", "Starling", "Nationwide", "TSB", "Halifax", "First Direct",
]


def assert_no_real_bank_names_invented(result: dict) -> tuple[bool, str]:
    text = result.get("full_text", "") + str(result.get("cards", []))
    for bank in _KNOWN_REAL_UK_BANKS:
        if bank.lower() in text.lower():
            return False, f"Found invented real bank name '{bank}' not present in raw_data"
    return True, "No real bank names invented"


def assert_signal_id_stable_across_repeats(results: list[dict]) -> tuple[bool, str]:
    signal_ids = set()
    for r in results:
        for card in r.get("cards", []):
            signal_ids.add(card.get("signal_id"))
    if len(signal_ids) > 1:
        return False, f"Signal ID varied across repeated checks: {signal_ids}"
    if len(signal_ids) == 0:
        return False, "No signal_id produced in any repeat"
    return True, f"Stable signal_id across all repeats: {signal_ids}"


def assert_low_urgency_or_no_card(result: dict) -> tuple[bool, str]:
    cards = result.get("cards", [])
    if not cards:
        return True, "No card produced for trivial saving (correct)"
    savings = cards[0].get("computed_savings_gbp")
    if savings is not None and savings < 15:
        return True, f"Card produced but savings (£{savings}) correctly below default threshold framing"
    return False, f"Card produced for a saving that should have been below threshold: £{savings}"


def assert_card_produced(result: dict) -> tuple[bool, str]:
    cards = result.get("cards", [])
    if not cards:
        return False, "Expected a card to be produced, but none were"
    return True, f"Card correctly produced: {cards[0].get('title', 'untitled')}"


def assert_trivial_change_correctly_handled(result: dict) -> tuple[bool, str]:
    """A trivial price change should either produce no card, or a card
    whose computed_savings_gbp is genuinely small -- never a card
    framed with the same urgency as a real, large change."""
    cards = result.get("cards", [])
    if not cards:
        return True, "No card produced for trivial change (correct)"
    savings = cards[0].get("computed_savings_gbp")
    if savings is None:
        return True, "Card produced with no savings figure (acceptable for a trivial change)"
    if savings > 100:
        return False, f"Card produced with unexpectedly large savings (£{savings}) for a £1/month trivial change"
    return True, f"Card produced with appropriately small savings figure (£{savings})"


def assert_affordability_mentioned(result: dict) -> tuple[bool, str]:
    """When an alternative requires a large upfront payment, the
    agent's summary must explicitly mention it -- not silently
    optimize for lowest total cost alone."""
    cards = result.get("cards", [])
    if not cards:
        return False, "Expected a card to be produced, but none were"
    summary = cards[0].get("summary", "").lower()
    full_text = result.get("full_text", "").lower()
    combined = summary + " " + full_text
    keywords = ["upfront", "up front", "immediately", "lump sum", "in advance"]
    if any(k in combined for k in keywords):
        return True, "Affordability/upfront tradeoff explicitly mentioned"
    return False, "No mention of upfront/affordability tradeoff found in card summary or agent text"
