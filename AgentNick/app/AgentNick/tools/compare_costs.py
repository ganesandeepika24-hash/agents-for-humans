"""
Tool: compare_costs

Generic cost-comparison arithmetic tool. The FM decides WHAT to compare
for any scenario; this tool guarantees the numbers are correct.

Tracks upfront amounts separately from ongoing monthly costs (comment
55) -- a £1000 upfront payment and £1000 spread across 12 months are
NOT equivalent from the user's perspective even when the total is
identical, since affordability/cash-flow matters independently of
total cost. The tool never decides FOR the user which matters more --
it surfaces the tradeoff plainly so the FM can state it explicitly
rather than silently optimizing for lowest total cost alone.
"""

from strands import tool

from .interfaces import CostComparison

# Below this difference, an upfront-cost distinction isn't worth
# calling out explicitly -- avoids noisy notes for trivial amounts.
_AFFORDABILITY_NOTE_THRESHOLD_GBP = 50.0


@tool
def compare_costs(
    current_monthly_cost: float,
    alternative_monthly_cost: float,
    one_time_fees: float = 0.0,
    months: int = 12,
    current_upfront_amount: float = 0.0,
    alternative_upfront_amount: float = 0.0,
) -> CostComparison:
    """
    current_upfront_amount / alternative_upfront_amount: any amount the
    user would need to pay immediately/upfront under each option,
    DISTINCT from one_time_fees (a small signup/switching fee) -- use
    this specifically when an option requires a genuinely large lump
    sum (e.g. paying off a balance in full, an annual-in-advance plan)
    that could be a real affordability constraint, not just a minor fee.
    """
    total_current = current_monthly_cost * months
    total_alternative = (alternative_monthly_cost * months) + one_time_fees
    net_savings = round(total_current - total_alternative, 2)

    upfront_difference = round(alternative_upfront_amount - current_upfront_amount, 2)

    affordability_note = None
    if abs(upfront_difference) >= _AFFORDABILITY_NOTE_THRESHOLD_GBP:
        if upfront_difference > 0:
            affordability_note = (
                f"The alternative requires £{alternative_upfront_amount:.2f} upfront "
                f"(£{upfront_difference:.2f} more upfront than staying), even though "
                f"the total cost comparison may favor it -- flag this affordability "
                f"difference explicitly, don't rely on total cost alone."
            )
        else:
            affordability_note = (
                f"The alternative requires £{alternative_upfront_amount:.2f} upfront, "
                f"£{abs(upfront_difference):.2f} LESS than staying "
                f"(£{current_upfront_amount:.2f}) -- worth noting this is easier on "
                f"cash flow too, not just cheaper overall."
            )

    return CostComparison(
        total_current_cost=round(total_current, 2),
        total_alternative_cost=round(total_alternative, 2),
        net_savings=net_savings,
        worth_switching=net_savings > 0,
        current_upfront_amount=current_upfront_amount,
        alternative_upfront_amount=alternative_upfront_amount,
        upfront_difference=upfront_difference,
        affordability_note=affordability_note,
    )
