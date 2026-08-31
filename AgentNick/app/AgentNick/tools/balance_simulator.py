"""
Tool: simulate_balance_over_months

Generic deterministic balance simulation for any interest-bearing debt
scenario (credit cards, loans, overdrafts).
"""

from pydantic import BaseModel
from strands import tool


class BalanceSimulationResult(BaseModel):
    total_interest_paid: float
    ending_balance: float


@tool
def simulate_balance_over_months(
    balance: float,
    annual_rate_pct: float,
    monthly_payment: float,
    months: int = 12,
) -> BalanceSimulationResult:
    total_interest = 0.0

    for _ in range(months):
        if balance <= 0:
            break
        interest = balance * (annual_rate_pct / 100 / 12)
        total_interest += interest
        balance = balance + interest - monthly_payment
        if balance < 0:
            balance = 0.0

    return BalanceSimulationResult(
        total_interest_paid=round(total_interest, 2),
        ending_balance=round(balance, 2),
    )
