"""
evals/scenarios.py

Structured evaluation scenarios, one per real scenario type, loading
the actual mock data files used throughout the project (not
duplicated/hand-typed data) -- ensures evals stay honest to what the
real system actually processes.
"""

import json
from pathlib import Path

_DATA_DIR = Path(__file__).parent.parent / "data"


def _load(filename: str) -> dict:
    with open(_DATA_DIR / filename) as f:
        return json.load(f)


SCENARIOS = [
    {
        "name": "tariff_no_fabrication",
        "description": "Real tariff data has comparison offers -- verify no OTHER company is invented beyond what's in the data.",
        "scenario_type": "tariff",
        "raw_data": _load("tariffs.json"),
        "as_of_date": "2026-08-30",
        "assert_fn": "assert_no_real_bank_names_invented",
        "requires_agent": True,
    },
    {
        "name": "tariff_no_alternatives_no_urgent_savings_claim",
        "description": "When renewal price increases trivially AND no market alternatives exist, the agent must not claim a large savings figure with nothing to base it on.",
        "scenario_type": "tariff",
        "raw_data": {
            **_load("tariffs.json"),
            "renewal_price_gbp": 46.0,
            "market_comparable_offers": [],
        },
        "as_of_date": "2026-08-30",
        "assert_fn": "assert_trivial_change_correctly_handled",
        "requires_agent": True,
    },
    {
        "name": "tariff_signal_id_stable",
        "description": "Same real tariff commitment must produce the same signal_id across repeated checks.",
        "scenario_type": "tariff",
        "raw_data": _load("tariffs.json"),
        "as_of_date": "2026-08-30",
        "assert_fn": "assert_signal_id_stable_across_repeats",
        "requires_agent": False,
        "repeat_count": 3,
    },
    {
        "name": "trial_produces_urgent_card",
        "description": "A trial with a near-term cancellation deadline must produce an actionable card.",
        "scenario_type": "trial",
        "raw_data": _load("trial.json"),
        "as_of_date": "2026-08-30",
        "assert_fn": "assert_card_produced",
        "requires_agent": True,
    },
    {
        "name": "card_promo_affordability_noted",
        "description": "An alternative requiring a large upfront payment must be explicitly flagged, not silently optimized past.",
        "scenario_type": "card_promo",
        "raw_data": {
            **_load("card_promo.json"),
            "balance_transfer_offers": [{
                **_load("card_promo.json")["balance_transfer_offers"][0],
                "requires_upfront_payoff_gbp": 1250.0,
            }],
        },
        "as_of_date": "2026-08-30",
        "assert_fn": "assert_affordability_mentioned",
        "requires_agent": True,
    },
    {
        "name": "card_promo_incomplete_requests_missing_data",
        "description": "Deliberately incomplete card promo data must trigger a request-missing-data card, not a fabricated guess.",
        "scenario_type": "card_promo_incomplete",
        "raw_data": _load("card_promo_incomplete.json"),
        "as_of_date": "2026-08-30",
        "assert_fn": "assert_card_produced",
        "requires_agent": True,
    },
    {
        "name": "insurance_produces_card",
        "description": "A real insurance renewal price jump must produce an actionable card.",
        "scenario_type": "insurance",
        "raw_data": _load("insurance.json"),
        "as_of_date": "2026-08-30",
        "assert_fn": "assert_card_produced",
        "requires_agent": True,
    },
    {
        "name": "membership_produces_card",
        "description": "A real membership renewal price jump must produce an actionable card.",
        "scenario_type": "membership",
        "raw_data": _load("membership.json"),
        "as_of_date": "2026-08-30",
        "assert_fn": "assert_card_produced",
        "requires_agent": True,
    },
]
