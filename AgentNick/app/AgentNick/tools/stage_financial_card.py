"""
Tool: stage_financial_card

Generic replacement for stage_tariff_card / stage_trial_card /
stage_card_promo_card / stage_payment_reminder_card. The FM proposes the
title, summary, savings figure, and options based on its own reasoning
(guided by system prompt principles); stage_approval_card's existing
validation still guards against malformed output (email needs a
payload, action_url needs a URL).

The FM is responsible for applying the threshold check (resolve_threshold
/ meets_threshold) BEFORE calling this — the system prompt instructs it
to do so. This tool does not gate on outcome type since there is no
fixed outcome taxonomy anymore.
"""

from strands import tool

from .interfaces import ApprovalCard, StageApprovalCardInput
from .stage_approval_card import stage_approval_card


@tool
def stage_financial_card(input: StageApprovalCardInput) -> ApprovalCard:
    return stage_approval_card(input)
