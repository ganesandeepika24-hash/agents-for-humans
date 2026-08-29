"""
stage_tariff_card — scenario-specific wrapper around stage_approval_card.

Not a Strands @tool. Deterministic Python glue: decides whether a
TariffEvaluation warrants a card at all, and if so, builds the exact
StageApprovalCardInput from evaluation data with no FM judgment involved.
"""

from .interfaces import ApprovalCard, CardOption, CardOptionType, FinancialSignal, StageApprovalCardInput, TariffEvaluation, TariffOutcome
from .stage_approval_card import stage_approval_card


def stage_tariff_card(evaluation: TariffEvaluation, signal: FinancialSignal) -> ApprovalCard | None:
    if evaluation.outcome != TariffOutcome.SWITCH_RECOMMENDED:
        return None

    portal_url = signal.raw_data.get("provider_portal_url")
    if not portal_url:
        raise ValueError("provider_portal_url missing from tariff raw_data")

    best = evaluation.best_offer
    title = f"Switch to {best['provider']} and save £{evaluation.net_savings_12mo_gbp:.2f}"

    return stage_approval_card(StageApprovalCardInput(
        scenario_type="broadband_tariff",
        title=title,
        summary=evaluation.reasoning_summary,
        computed_savings_gbp=evaluation.net_savings_12mo_gbp,
        options=[
            CardOption(
                label=f"Switch to {best['provider']}",
                option_type=CardOptionType.ACTION_URL,
                action_url=portal_url,
            ),
        ],
    ))
