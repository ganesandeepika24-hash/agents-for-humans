"""
Tool: evaluate_payment_reminder

Independent trigger from evaluate_card_promo — this one watches for an
upcoming minimum payment due date, since missing it can forfeit a 0%
promo rate entirely. Direct debit users get a quiet one-time confirmation
(the risk this alert exists for is already mitigated). Manual payers get
a date-driven reminder cadence, same <= threshold pattern as trial.

due_date_marked_paid on PaymentReminderState prevents re-reminding once
the user has confirmed a specific due date is handled.
"""

from datetime import date

from strands import tool

from .interfaces import (
    EvaluatePaymentReminderInput,
    PaymentReminderEvaluation,
    PaymentReminderOutcome,
    PaymentReminderState,
)

_REMINDER_WINDOW_DAYS = 3


@tool
def evaluate_payment_reminder(
    input: EvaluatePaymentReminderInput,
    state: PaymentReminderState,
    as_of_date: date | None = None,
) -> PaymentReminderEvaluation:
    today = as_of_date or date.today()
    signal = input.signal
    if signal.source_type != "card_promo":
        raise ValueError(f"evaluate_payment_reminder requires source_type 'card_promo', got '{signal.source_type}'")

    raw = signal.raw_data
    payment_method = raw.get("payment_method", "manual")
    due_date_str = raw.get("next_payment_due_date")

    if payment_method == "direct_debit":
        return PaymentReminderEvaluation(
            outcome=PaymentReminderOutcome.DIRECT_DEBIT_ACTIVE,
            next_payment_due_date=due_date_str,
            days_until_due=None,
            reasoning_summary=(
                "Direct debit is active for this card — no action needed to keep your 0% rate."
            ),
        )

    if not due_date_str:
        raise ValueError("next_payment_due_date missing from card_promo raw_data for a manual payer")

    if state.due_date_marked_paid == due_date_str:
        return PaymentReminderEvaluation(
            outcome=PaymentReminderOutcome.ALREADY_MARKED_PAID,
            next_payment_due_date=due_date_str,
            days_until_due=None,
            reasoning_summary="You've already confirmed this payment — no reminder needed.",
        )

    due_date = date.fromisoformat(due_date_str)
    days_until_due = (due_date - today).days

    if days_until_due > _REMINDER_WINDOW_DAYS:
        return PaymentReminderEvaluation(
            outcome=PaymentReminderOutcome.NOT_YET_DUE,
            next_payment_due_date=due_date_str,
            days_until_due=days_until_due,
            reasoning_summary="Payment not yet due for reminder.",
        )

    return PaymentReminderEvaluation(
        outcome=PaymentReminderOutcome.PAYMENT_REMINDER,
        next_payment_due_date=due_date_str,
        days_until_due=days_until_due,
        reasoning_summary=(
            f"Your minimum payment is due in {days_until_due} day(s) ({due_date_str}). "
            f"Missing it could forfeit your 0% promotional rate."
        ),
    )
