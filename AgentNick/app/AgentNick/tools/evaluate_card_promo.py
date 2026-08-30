"""
Tool: evaluate_card_promo

Given a card_promo FinancialSignal, determines the account's situation
and (if applicable) simulates the cost of doing nothing vs. transferring
the balance to a new 0% offer.

Three outcomes:
- ALREADY_PAID_OFF: balance is at or near zero, nothing to act on.
- PROMO_ALREADY_LOST: promo_rate_still_active is False (missed payment
  already forfeited the 0% rate) — standard APR is already being charged.
- ACTIVE_PROMO: promo is running, countdown + simulation logic applies.
"""

from strands import tool

from .balance_simulator import simulate_balance_over_months
from .interfaces import CardPromoEvaluation, CardPromoOutcome, EvaluateCardPromoInput

_PAID_OFF_THRESHOLD_GBP = 1.00  # balances below this are treated as paid off


@tool
def evaluate_card_promo(input: EvaluateCardPromoInput) -> CardPromoEvaluation:
    signal = input.signal
    if signal.source_type != "card_promo":
        raise ValueError(f"evaluate_card_promo requires source_type 'card_promo', got '{signal.source_type}'")

    raw = signal.raw_data
    balance = float(raw["current_balance_gbp"])
    standard_apr = float(raw["standard_apr_pct"])
    min_payment = float(raw["minimum_payment_gbp"])
    payment_method = raw.get("payment_method", "manual")
    promo_active = raw.get("promo_rate_still_active", True)
    offers = raw.get("balance_transfer_offers", [])

    # Case 1: already paid off — nothing to act on regardless of promo status
    if balance <= _PAID_OFF_THRESHOLD_GBP:
        return CardPromoEvaluation(
            outcome=CardPromoOutcome.ALREADY_PAID_OFF,
            days_until_promo_ends=None,
            current_balance_gbp=balance,
            standard_apr_pct=None,
            payment_method=payment_method,
            do_nothing_total_interest_gbp=None,
            do_nothing_ending_balance_gbp=None,
            transfer_fee_gbp=None,
            transfer_net_benefit_gbp=None,
            balance_stagnant_warning=False,
            best_transfer_offer=None,
            reasoning_summary="Your balance is already paid off — no action needed.",
        )

    # Case 2: promo already forfeited due to a missed payment
    if not promo_active:
        return CardPromoEvaluation(
            outcome=CardPromoOutcome.PROMO_ALREADY_LOST,
            days_until_promo_ends=None,
            current_balance_gbp=balance,
            standard_apr_pct=standard_apr,
            payment_method=payment_method,
            do_nothing_total_interest_gbp=None,
            do_nothing_ending_balance_gbp=None,
            transfer_fee_gbp=None,
            transfer_net_benefit_gbp=None,
            balance_stagnant_warning=False,
            best_transfer_offer=None,
            reasoning_summary=(
                f"Your 0% rate ended early due to a missed payment. Standard APR of "
                f"{standard_apr}% is already being applied to your £{balance:.2f} balance."
            ),
        )

    # Case 3: active promo — run the simulation
    do_nothing_interest, do_nothing_ending = simulate_balance_over_months(balance, standard_apr, min_payment, 12)

    # A stagnant/growing balance: less than 15% of the original balance is paid
    # down over 12 months of "minimum" payments.
    principal_reduction = balance - do_nothing_ending
    balance_stagnant_warning = principal_reduction < (balance * 0.15)

    best_offer = None
    best_net_benefit = None
    if offers:
        for offer in offers:
            transfer_fee = balance * (float(offer.get("transfer_fee_pct", 0)) / 100)
            net_benefit = do_nothing_interest - transfer_fee
            if best_net_benefit is None or net_benefit > best_net_benefit:
                best_offer = offer
                best_net_benefit = net_benefit

    transfer_fee_gbp = None
    if best_offer is not None:
        transfer_fee_gbp = round(balance * (float(best_offer.get("transfer_fee_pct", 0)) / 100), 2)

    summary = (
        f"Your 0% promotional period ends in {signal.days_until_key_date} days. "
        f"Outstanding balance: £{balance:.2f}. After the promo ends, standard APR "
        f"of {standard_apr}% applies."
    )

    return CardPromoEvaluation(
        outcome=CardPromoOutcome.ACTIVE_PROMO,
        days_until_promo_ends=signal.days_until_key_date,
        current_balance_gbp=balance,
        standard_apr_pct=standard_apr,
        payment_method=payment_method,
        do_nothing_total_interest_gbp=do_nothing_interest,
        do_nothing_ending_balance_gbp=do_nothing_ending,
        transfer_fee_gbp=transfer_fee_gbp,
        transfer_net_benefit_gbp=round(best_net_benefit, 2) if best_net_benefit is not None else None,
        balance_stagnant_warning=balance_stagnant_warning,
        best_transfer_offer=best_offer,
        reasoning_summary=summary,
    )
