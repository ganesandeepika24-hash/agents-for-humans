"""
Tool: compare_costs

Generic cost-comparison arithmetic tool. The FM decides WHAT to compare
for any scenario; this tool guarantees the numbers are correct.
"""

from strands import tool

from .interfaces import CostComparison


@tool
def compare_costs(
    current_monthly_cost: float,
    alternative_monthly_cost: float,
    one_time_fees: float = 0.0,
    months: int = 12,
) -> CostComparison:
    total_current = current_monthly_cost * months
    total_alternative = (alternative_monthly_cost * months) + one_time_fees
    net_savings = round(total_current - total_alternative, 2)

    return CostComparison(
        total_current_cost=round(total_current, 2),
        total_alternative_cost=round(total_alternative, 2),
        net_savings=net_savings,
        worth_switching=net_savings > 0,
    )
