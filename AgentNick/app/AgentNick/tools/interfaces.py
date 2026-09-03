"""
Tool interface definitions for AgentNick.
Defines the exact input/output schemas for all four @tool functions,
plus the shared threshold resolution system used by evaluators before
staging an approval card.
"""

from datetime import date
from enum import Enum
from typing import Literal

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Tool 1: parse_financial_signals
# ---------------------------------------------------------------------------

class ParseSignalsInput(BaseModel):
    source_type: str  # free-form: "tariff", "trial", "card_promo", "gym_membership", "insurance", anything
    raw_data: dict


class FinancialSignal(BaseModel):
    signal_id: str
    source_type: str
    user_id: str
    key_date: date
    days_until_key_date: int
    monetary_amount_gbp: float
    raw_data: dict  # original data preserved for scenario-specific fields


# ---------------------------------------------------------------------------
# Tool 2: evaluate_tariff_parity
# ---------------------------------------------------------------------------

class EvaluateTariffInput(BaseModel):
    signal: FinancialSignal  # must have source_type == "tariff"


class TariffOutcome(str, Enum):
    PRICE_DROP = "price_drop"
    SAME_PRICE_RENEWAL = "same_price_renewal"
    PRICE_HIKE_NO_BETTER_OFFER = "price_hike_no_better_offer"
    SWITCH_RECOMMENDED = "switch_recommended"


class TariffEvaluation(BaseModel):
    outcome: TariffOutcome
    should_switch: bool
    best_offer: dict | None
    parity_matched: bool
    annual_price_change_gbp: float
    net_savings_12mo_gbp: float
    reasoning_summary: str


# ---------------------------------------------------------------------------
# Tool 3: check_web_portal
# ---------------------------------------------------------------------------

class CheckWebPortalInput(BaseModel):
    url: str


class ClassOffer(BaseModel):
    name: str
    standard_price_gbp: float
    early_bird_price_gbp: float
    savings_gbp: float


class RegistrationStatus(BaseModel):
    scrape_successful: bool
    error_message: str | None
    registration_open: bool | None
    early_bird_deadline: date | None
    days_until_deadline: int | None
    classes: list[ClassOffer]


# ---------------------------------------------------------------------------
# Tool 4: stage_approval_card
# ---------------------------------------------------------------------------

class EmailPayload(BaseModel):
    to: str
    subject: str
    body: str


class CardOptionType(str, Enum):
    EMAIL = "email"
    ACTION_URL = "action_url"
    REMIND_LATER = "remind_later"
    DISMISS = "dismiss"
    REVEAL_WARNING = "reveal_warning"
    REVEAL_COMPARISON = "reveal_comparison"
    MANUAL_INPUT = "manual_input"
    DOCUMENT_UPLOAD = "document_upload"
    INFO_ONLY = "info_only"  # a genuine recommendation with no direct
                              # link available (e.g. no signup_url in
                              # the data) -- distinct from "dismiss",
                              # which means the user is choosing to take
                              # no action, not that a link is missing


class CardOption(BaseModel):
    label: str
    option_type: CardOptionType
    email_payload: EmailPayload | None = None
    action_url: str | None = None


class StageApprovalCardInput(BaseModel):
    scenario_type: str  # free-form label describing the kind of signal, e.g. "broadband_tariff"
    signal_id: str
    title: str
    summary: str
    computed_savings_gbp: float | None
    options: list[CardOption]
    extra_data: dict | None = None


class ApprovalCard(BaseModel):
    card_id: str
    signal_id: str
    scenario_type: str
    title: str
    summary: str
    computed_savings_gbp: float | None
    options: list[CardOption]
    status: Literal["pending", "approved", "rejected"]
    extra_data: dict | None = None


class TrialReminderState(BaseModel):
    user_id: str
    service: str
    resolved: bool = False
    last_tier_shown: str | None = None


# ---------------------------------------------------------------------------
# Tool 2b: evaluate_card_promo
# ---------------------------------------------------------------------------

class EvaluateCardPromoInput(BaseModel):
    signal: FinancialSignal  # must have source_type == "card_promo"


class CardPromoOutcome(str, Enum):
    ALREADY_PAID_OFF = "already_paid_off"
    PROMO_ALREADY_LOST = "promo_already_lost"
    ACTIVE_PROMO = "active_promo"


class CardPromoEvaluation(BaseModel):
    outcome: CardPromoOutcome
    days_until_promo_ends: int | None
    current_balance_gbp: float
    standard_apr_pct: float | None
    payment_method: Literal["direct_debit", "manual"]
    do_nothing_total_interest_gbp: float | None   # 12-month simulation at standard APR
    do_nothing_ending_balance_gbp: float | None
    transfer_fee_gbp: float | None
    transfer_net_benefit_gbp: float | None         # interest saved minus transfer fee
    balance_stagnant_warning: bool                 # true if balance barely reduces / grows under do-nothing
    best_transfer_offer: dict | None
    reasoning_summary: str


# ---------------------------------------------------------------------------
# Tool 2c: evaluate_payment_reminder
# ---------------------------------------------------------------------------

class EvaluatePaymentReminderInput(BaseModel):
    signal: FinancialSignal  # must have source_type == "card_promo"


class PaymentReminderOutcome(str, Enum):
    DIRECT_DEBIT_ACTIVE = "direct_debit_active"
    NOT_YET_DUE = "not_yet_due"
    ALREADY_MARKED_PAID = "already_marked_paid"
    PAYMENT_REMINDER = "payment_reminder"


class PaymentReminderEvaluation(BaseModel):
    outcome: PaymentReminderOutcome
    next_payment_due_date: str | None
    days_until_due: int | None
    reasoning_summary: str


class PaymentReminderState(BaseModel):
    user_id: str
    card_provider: str
    due_date_marked_paid: str | None = None  # the specific due_date already confirmed paid, if any


# ---------------------------------------------------------------------------
# Generic financial reasoning tools (replace scenario-specific evaluators)
# ---------------------------------------------------------------------------

class CompareCostsInput(BaseModel):
    current_monthly_cost: float
    alternative_monthly_cost: float
    one_time_fees: float = 0.0
    months: int = 12


class CostComparison(BaseModel):
    total_current_cost: float
    total_alternative_cost: float
    net_savings: float
    worth_switching: bool


class MissingDataRequest(BaseModel):
    what_is_missing: list[str]
    why_needed: str
    can_upload_document: bool = True


# ---------------------------------------------------------------------------
# Threshold system (used by evaluators before deciding whether to call
# stage_approval_card — NOT stored on the ApprovalCard itself)
# ---------------------------------------------------------------------------

class ThresholdMode(str, Enum):
    OR = "or"                      # trigger if EITHER absolute OR percent is met
    NUMBER_ONLY = "number_only"    # per-item toggle
    PERCENT_ONLY = "percent_only"  # per-item toggle


class ThresholdConfig(BaseModel):
    mode: ThresholdMode = ThresholdMode.OR
    min_savings_gbp: float | None = None
    min_savings_pct: float | None = None


class UserThresholdSettings(BaseModel):
    user_global_default: ThresholdConfig | None = None   # tier 2
    per_scenario_overrides: dict[str, ThresholdConfig] = {}  # tier 3


class ResolvedThreshold(BaseModel):
    config: ThresholdConfig
    source: Literal["system_default", "user_global", "scenario_override"]


# Tier 1 — system default. Tune these two numbers as you like.
SYSTEM_DEFAULT = ThresholdConfig(mode=ThresholdMode.OR, min_savings_gbp=15.0, min_savings_pct=10.0)


def resolve_threshold(
    scenario_type: str, settings: UserThresholdSettings | None
) -> ResolvedThreshold:
    """Three-tier fallback: per-scenario override -> user global default -> system default."""
    if settings and scenario_type in settings.per_scenario_overrides:
        return ResolvedThreshold(
            config=settings.per_scenario_overrides[scenario_type],
            source="scenario_override",
        )
    if settings and settings.user_global_default is not None:
        return ResolvedThreshold(config=settings.user_global_default, source="user_global")
    return ResolvedThreshold(config=SYSTEM_DEFAULT, source="system_default")


def meets_threshold(amount_gbp: float, base_amount_gbp: float, config: ThresholdConfig) -> bool:
    """Evaluate whether a savings amount clears the given threshold config."""
    if config.mode == ThresholdMode.NUMBER_ONLY:
        return config.min_savings_gbp is not None and amount_gbp >= config.min_savings_gbp

    if config.mode == ThresholdMode.PERCENT_ONLY:
        return (
            config.min_savings_pct is not None
            and base_amount_gbp > 0
            and (amount_gbp / base_amount_gbp) * 100 >= config.min_savings_pct
        )

    # OR mode (default)
    hits_amount = config.min_savings_gbp is not None and amount_gbp >= config.min_savings_gbp
    hits_pct = (
        config.min_savings_pct is not None
        and base_amount_gbp > 0
        and (amount_gbp / base_amount_gbp) * 100 >= config.min_savings_pct
    )
    return hits_amount or hits_pct
