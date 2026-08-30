"""
simulate_balance_over_months — deterministic month-by-month balance
simulation, used by evaluate_card_promo to compute realistic interest
projections rather than a flat single-number estimate.
"""


def simulate_balance_over_months(
    balance: float, annual_rate_pct: float, monthly_payment: float, months: int = 12
) -> tuple[float, float]:
    """
    Returns (total_interest_paid, ending_balance) after simulating `months`
    of: interest accrues, then payment is applied. Balance never goes below 0.
    """
    monthly_rate = annual_rate_pct / 100 / 12
    total_interest = 0.0

    for _ in range(months):
        if balance <= 0:
            break
        interest = balance * monthly_rate
        total_interest += interest
        balance = balance + interest - monthly_payment
        if balance < 0:
            balance = 0.0

    return round(total_interest, 2), round(balance, 2)
