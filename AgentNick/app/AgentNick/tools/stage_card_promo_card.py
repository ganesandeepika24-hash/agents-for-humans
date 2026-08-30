"""
stage_card_promo_card — scenario-specific wrapper around stage_approval_card.

Not a Strands @tool. Deterministic Python glue implementing progressive
disclosure for the card promo scenario:

- ALREADY_PAID_OFF / PROMO_ALREADY_LOST: single informational card, no
  countdown framing, appropriate options for that state.
- ACTIVE_PROMO: short initial card ("Keep This Card" / "See Alternatives").
  The stagnant-balance warning and the do-nothing-vs-transfer comparison
  are pre-computed and placed in extra_data, so the frontend can reveal
  them on click without a second backend call.
"""

from .interfaces import (
    ApprovalCard,
    CardOption,
    CardOptionType,
    CardPromoEvaluation,
    CardPromoOutcome,
    StageApprovalCardInput,
)
from .stage_approval_card import stage_approval_card


def stage_card_promo_card(evaluation: CardPromoEvaluation) -> ApprovalCard | None:
    if evaluation.outcome == CardPromoOutcome.ALREADY_PAID_OFF:
        return stage_approval_card(StageApprovalCardInput(
            scenario_type="card_promo",
            title="Your card balance is paid off",
            summary=evaluation.reasoning_summary,
            computed_savings_gbp=None,
            options=[CardOption(label="OK", option_type=CardOptionType.DISMISS)],
        ))

    if evaluation.outcome == CardPromoOutcome.PROMO_ALREADY_LOST:
        return stage_approval_card(StageApprovalCardInput(
            scenario_type="card_promo",
            title="Your 0% rate has already ended",
            summary=evaluation.reasoning_summary,
            computed_savings_gbp=None,
            options=[CardOption(label="See Options", option_type=CardOptionType.DISMISS)],
        ))

    # ACTIVE_PROMO
    title = f"Your 0% interest period ends in {evaluation.days_until_promo_ends} days"
    summary = (
        f"Outstanding balance: £{evaluation.current_balance_gbp:.2f}. "
        f"After the promo ends, standard APR of {evaluation.standard_apr_pct}% applies."
    )

    warning_text = None
    if evaluation.balance_stagnant_warning:
        warning_text = (
            f"At your current payment level, your balance will barely reduce — "
            f"you'd pay £{evaluation.do_nothing_total_interest_gbp:.2f} in interest over "
            f"the next 12 months for very little progress on the balance itself. "
            f"Are you sure you want to keep this card?"
        )

    comparison = None
    if evaluation.best_transfer_offer is not None:
        comparison = {
            "do_nothing_total_interest_gbp": evaluation.do_nothing_total_interest_gbp,
            "do_nothing_ending_balance_gbp": evaluation.do_nothing_ending_balance_gbp,
            "transfer_provider": evaluation.best_transfer_offer["provider"],
            "transfer_fee_gbp": evaluation.transfer_fee_gbp,
            "transfer_net_benefit_gbp": evaluation.transfer_net_benefit_gbp,
        }

    extra_data = {
        "balance_stagnant_warning": evaluation.balance_stagnant_warning,
        "warning_text": warning_text,
        "comparison": comparison,
    }

    return stage_approval_card(StageApprovalCardInput(
        scenario_type="card_promo",
        title=title,
        summary=summary,
        computed_savings_gbp=evaluation.transfer_net_benefit_gbp,
        options=[
            CardOption(label="Keep This Card", option_type=CardOptionType.REVEAL_WARNING),
            CardOption(label="See Alternatives", option_type=CardOptionType.REVEAL_COMPARISON),
        ],
        extra_data=extra_data,
    ))
