"""
Tool: evaluate_tariff_parity

Given a tariff FinancialSignal, determines what's happening with the
user's broadband renewal and whether switching provider is worthwhile.

Four possible outcomes:
- PRICE_DROP: renewal is cheaper than current price. No action needed.
- SAME_PRICE_RENEWAL: renewal price is unchanged. No action needed.
- PRICE_HIKE_NO_BETTER_OFFER: price is rising, but no comparable offer
  (same or better speed, cheaper after fees) is available. Informational only.
- SWITCH_RECOMMENDED: price is rising, and a genuinely better offer exists.
"""

from strands import tool

from .interfaces import EvaluateTariffInput, TariffEvaluation, TariffOutcome


@tool
def evaluate_tariff_parity(input: EvaluateTariffInput) -> TariffEvaluation:
    signal = input.signal
    if signal.source_type != "tariff":
        raise ValueError(f"evaluate_tariff_parity requires source_type 'tariff', got '{signal.source_type}'")

    raw = signal.raw_data
    current_price = float(raw["current_price_gbp"])
    renewal_price = float(raw["renewal_price_gbp"])
    current_speed = float(raw["current_speed_mbps"])
    offers = raw.get("market_comparable_offers", [])

    annual_price_change = (current_price - renewal_price) * 12  # positive = drop, negative = hike

    # Case 1 & 2: renewal price is same or cheaper than current — nothing to act on,
    # regardless of what offers exist in the market.
    if renewal_price <= current_price:
        outcome = TariffOutcome.PRICE_DROP if renewal_price < current_price else TariffOutcome.SAME_PRICE_RENEWAL
        if outcome == TariffOutcome.PRICE_DROP:
            summary = (
                f"Good news — your renewal price is dropping to £{renewal_price:.2f}/mo "
                f"from £{current_price:.2f}/mo. No action needed."
            )
        else:
            summary = f"Your plan is renewing at the same price (£{current_price:.2f}/mo) — no action needed."

        return TariffEvaluation(
            outcome=outcome,
            should_switch=False,
            best_offer=None,
            parity_matched=False,
            annual_price_change_gbp=annual_price_change,
            net_savings_12mo_gbp=0.0,
            reasoning_summary=summary,
        )

    # Price is rising from here on — check whether any offer meets parity
    # (matches or beats current speed).
    parity_offers = [o for o in offers if float(o.get("speed_mbps", 0)) >= current_speed]
    parity_matched = len(parity_offers) > 0

    best_offer = None
    best_net_savings = 0.0

    if parity_offers:
        # Among parity-matching offers, evaluate 12-month net savings for each,
        # pick the one with the highest savings.
        for offer in parity_offers:
            offer_price = float(offer["price_gbp"])
            signup_fee = float(offer.get("signup_fee_gbp", 0))
            net_savings = (renewal_price * 12) - (offer_price * 12) - signup_fee
            if best_offer is None or net_savings > best_net_savings:
                best_offer = offer
                best_net_savings = net_savings

    if best_offer is not None and best_net_savings > 0:
        summary = (
            f"Your price is increasing to £{renewal_price:.2f}/mo from £{current_price:.2f}/mo. "
            f"{best_offer['provider']} offers the same or better speed for £{best_offer['price_gbp']:.2f}/mo — "
            f"switching saves you £{best_net_savings:.2f} over 12 months."
        )
        return TariffEvaluation(
            outcome=TariffOutcome.SWITCH_RECOMMENDED,
            should_switch=True,
            best_offer=best_offer,
            parity_matched=True,
            annual_price_change_gbp=annual_price_change,
            net_savings_12mo_gbp=best_net_savings,
            reasoning_summary=summary,
        )

    # Price is rising, but no offer beats it after parity + fees (or no offers meet parity at all)
    summary = (
        f"Your price is increasing to £{renewal_price:.2f}/mo from £{current_price:.2f}/mo — "
        f"we checked, but no better matching offer is currently available."
    )
    return TariffEvaluation(
        outcome=TariffOutcome.PRICE_HIKE_NO_BETTER_OFFER,
        should_switch=False,
        best_offer=None,
        parity_matched=parity_matched,
        annual_price_change_gbp=annual_price_change,
        net_savings_12mo_gbp=0.0,
        reasoning_summary=summary,
    )
