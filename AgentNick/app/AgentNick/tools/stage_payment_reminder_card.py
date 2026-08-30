"""
stage_payment_reminder_card — scenario-specific wrapper around
stage_approval_card.

Not a Strands @tool. Only PAYMENT_REMINDER produces a card. The other
three outcomes (direct debit, not yet due, already marked paid) are all
"nothing to show the user" states — silent, not just low-priority.

"Mark as Paid" is a DISMISS-type option; there's no email/link action
here since paying a bill isn't something this agent does on the user's
behalf. Whatever calls this is responsible for updating
PaymentReminderState.due_date_marked_paid when that option is chosen.
"""

from .interfaces import (
    ApprovalCard,
    CardOption,
    CardOptionType,
    PaymentReminderEvaluation,
    PaymentReminderOutcome,
    StageApprovalCardInput,
)
from .stage_approval_card import stage_approval_card


def stage_payment_reminder_card(evaluation: PaymentReminderEvaluation) -> ApprovalCard | None:
    if evaluation.outcome != PaymentReminderOutcome.PAYMENT_REMINDER:
        return None

    title = f"Payment due in {evaluation.days_until_due} day(s)"

    return stage_approval_card(StageApprovalCardInput(
        scenario_type="card_promo",
        title=title,
        summary=evaluation.reasoning_summary,
        computed_savings_gbp=None,
        options=[
            CardOption(label="Mark as Paid", option_type=CardOptionType.DISMISS),
            CardOption(label="Remind Me Later", option_type=CardOptionType.REMIND_LATER),
        ],
    ))
