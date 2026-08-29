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
    source_type: Literal["tariff", "trial", "card_promo"]
    raw_data: dict  # contents of tariffs.json / trial.json / card_promo.json


class FinancialSignal(BaseModel):
    source_type: Literal["tariff", "trial", "card_promo"]
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


class TariffEvaluation(BaseModel):
    should_switch: bool
    best_offer: dict | None
    parity_matched: bool
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


class Action(BaseModel):
    type: Literal["email", "action_url"]
    email_payload: EmailPayload | None
    action_url: str | None


class StageApprovalCardInput(BaseModel):
    scenario_type: Literal[
        "trial_cancellation", "broadband_tariff", "card_promo", "hobby_registration"
    ]
    title: str
    summary: str
    computed_savings_gbp: float | None
    action_type: Literal["email", "action_url"]
    email_payload: EmailPayload | None
    action_url: str | None


class ApprovalCard(BaseModel):
    card_id: str
    scenario_type: Literal[
        "trial_cancellation", "broadband_tariff", "card_promo", "hobby_registration"
    ]
    title: str
    summary: str
    computed_savings_gbp: float | None
    action: Action
    status: Literal["pending", "approved", "rejected"]


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
