"""
Tool: simulate_balance_over_months

Generic deterministic balance simulation — usable for ANY interest-
bearing debt scenario (credit cards, loans, overdrafts), not just
card_promo. The FM decides when a balance simulation is relevant;
this tool guarantees the arithmetic is correct.
"""

from pydantic import BaseModel
from strands import tool


class SimulateBalanceInput(BaseModel):
    balance: float
    annual_rate_pct: float
    monthly_payment: float
    months: int = 12


class BalanceSimulationResult(BaseModel):
    total_interest_paid: float
    ending_balance: float


@tool
def simulate_balance_over_months(input: SimulateBalanceInput) -> BalanceSimulationResult:
    balance = input.balance
    monthly_rate = input.annual_rate_pct / 100 / 12
    total_interest = 0.0

    for _ in range(input.months):
        if balance <= 0:
            break
        interest = balance * monthly_rate
        total_interest += interest
        balance = balance + interest - input.monthly_payment
        if balance < 0:
            balance = 0.0

    return BalanceSimulationResult(
        total_interest_paid=round(total_interest, 2),
        ending_balance=round(balance, 2),
    )
