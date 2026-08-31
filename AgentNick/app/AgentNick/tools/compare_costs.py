"""
Tool: compare_costs

Generic replacement for evaluate_tariff_parity's savings math and
evaluate_card_promo's transfer-fee comparison. The FM calls this whenever
it identifies two comparable costs (current vs. an alternative) for ANY
scenario — broadband, subscriptions, insurance, gym memberships, card
promos, anything. The FM decides WHAT to compare; this tool does the
arithmetic reliably.
"""

from strands import tool

from .interfaces import CompareCostsInput, CostComparison


@tool
def compare_costs(input: CompareCostsInput) -> CostComparison:
    total_current = input.current_monthly_cost * input.months
    total_alternative = (input.alternative_monthly_cost * input.months) + input.one_time_fees
    net_savings = round(total_current - total_alternative, 2)

    return CostComparison(
        total_current_cost=round(total_current, 2),
        total_alternative_cost=round(total_alternative, 2),
        net_savings=net_savings,
        worth_switching=net_savings > 0,
    )
