"""
stage_trial_card — scenario-specific wrapper around stage_approval_card.

Not a Strands @tool. Deterministic Python glue implementing a three-tier
reminder cadence:
  - > 3 days out: no card, too early
  - <= 3 days out: "standard" tier — Cancel Now / Remind Me Later
  - <= 1 day out:  "urgent" tier   — Cancel Now / Remind Me Later
  - <= 0 days out: "final" tier    — Continue with Cancellation / Keep Subscription
  - already resolved (per TrialReminderState): no card, regardless of days
  - already ended (days < 0) and unresolved: still shown as "final" tier,
    since the user hasn't explicitly decided either way yet
"""

from .interfaces import (
    ApprovalCard,
    CardOption,
    CardOptionType,
    EmailPayload,
    FinancialSignal,
    StageApprovalCardInput,
    TrialReminderState,
)
from .stage_approval_card import stage_approval_card


def stage_trial_card(signal: FinancialSignal, state: TrialReminderState) -> ApprovalCard | None:
    if signal.source_type != "trial":
        raise ValueError(f"stage_trial_card requires source_type 'trial', got '{signal.source_type}'")

    if state.resolved:
        return None

    days = signal.days_until_key_date
    if days > 3:
        return None  # too early, no card

    raw = signal.raw_data
    service = raw.get("service", "this service")
    amount = signal.monetary_amount_gbp
    cancellation_email = raw.get("cancellation_email")
    if not cancellation_email:
        raise ValueError("cancellation_email missing from trial raw_data")

    cancel_email_option = CardOption(
        label="Cancel Now",
        option_type=CardOptionType.EMAIL,
        email_payload=EmailPayload(
            to=cancellation_email,
            subject="Cancel my subscription",
            body=f"Please cancel my {service} trial effective immediately.",
        ),
    )

    if days <= 0:
        title = f"Last chance — decide on {service} today"
        summary = (
            f"Today is the last day before you're charged £{amount:.2f} for {service}. "
            f"Choose now — cancel or keep your subscription."
        )
        options = [
            CardOption(label="Continue with Cancellation", option_type=CardOptionType.EMAIL,
                       email_payload=cancel_email_option.email_payload),
            CardOption(label="Keep Subscription", option_type=CardOptionType.DISMISS),
        ]
        tier = "final"
    elif days <= 1:
        title = f"Urgent: {service} bills you tomorrow"
        summary = (
            f"Your {service} trial ends in {days} day. Cancel now to avoid "
            f"a £{amount:.2f} charge, or decide later today."
        )
        options = [
            cancel_email_option,
            CardOption(label="Remind Me Later", option_type=CardOptionType.REMIND_LATER),
        ]
        tier = "urgent"
    else:  # days == 2 or 3
        title = f"Cancel {service} before you're billed"
        summary = (
            f"Your {service} trial ends in {days} days ({signal.key_date.isoformat()}). "
            f"Cancel now to avoid a £{amount:.2f} charge."
        )
        options = [
            cancel_email_option,
            CardOption(label="Remind Me Later", option_type=CardOptionType.REMIND_LATER),
        ]
        tier = "standard"

    state.last_tier_shown = tier

    return stage_approval_card(StageApprovalCardInput(
        scenario_type="trial_cancellation",
        title=title,
        summary=summary,
        computed_savings_gbp=amount,
        options=options,
    ))
