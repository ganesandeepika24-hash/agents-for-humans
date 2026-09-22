"""
evals/run_evals.py

Runs every scenario in scenarios.py. Scenarios marked requires_agent
invoke the real deployed agent (genuine AI calls -- this takes real
time and consumes real API usage, run deliberately not on every save).
Others test the fast, deterministic identity-fingerprinting logic only.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, "/workspaces/agents-for-humans/backend")

from tools.parse_financial_signals import parse_financial_signals

import evals.assertions as assertions
from evals.scenarios import SCENARIOS

_IDENTITY_FIELD_MAP = {
    "tariff": "provider", "card_promo": "card_provider", "card_promo_incomplete": "card_provider",
    "trial": "service", "insurance": "provider", "membership": "provider",
}
_KEY_DATE_FIELD_MAP = {
    "tariff": "contract_end_date", "card_promo": "promo_apr_end_date",
    "card_promo_incomplete": "promo_apr_end_date", "trial": "cancellation_deadline",
    "insurance": "renewal_date", "membership": "renewal_date",
}
_MONETARY_FIELD_MAP = {
    "tariff": "current_price_gbp", "card_promo": "current_balance_gbp",
    "card_promo_incomplete": "current_balance_gbp", "trial": "auto_bill_amount_gbp",
    "insurance": "current_price_gbp", "membership": "current_price_gbp",
}


def _run_deterministic(scenario: dict) -> dict:
    raw_data = scenario["raw_data"]
    scenario_type = scenario["scenario_type"]
    signal = parse_financial_signals(
        source_type=scenario_type, raw_data=raw_data,
        key_date_field=_KEY_DATE_FIELD_MAP.get(scenario_type, "contract_end_date"),
        monetary_field=_MONETARY_FIELD_MAP.get(scenario_type, "current_price_gbp"),
        identity_field=_IDENTITY_FIELD_MAP.get(scenario_type, "provider"),
        as_of_date=scenario["as_of_date"],
    )
    return {"cards": [{"signal_id": signal.signal_id}], "full_text": ""}


def _run_full_agent(scenario: dict) -> dict:
    from invoke_agent import invoke_agent_for_check
    return invoke_agent_for_check(
        scenario_type=scenario["scenario_type"],
        raw_data=scenario["raw_data"],
        as_of_date=scenario["as_of_date"],
    )


def main():
    passed = 0
    failed = 0
    skipped = 0

    run_agent_evals = "--with-agent" in sys.argv

    for scenario in SCENARIOS:
        name = scenario["name"]
        assert_fn = getattr(assertions, scenario["assert_fn"])
        needs_agent = scenario.get("requires_agent", False)

        if needs_agent and not run_agent_evals:
            print(f"[SKIP] {name}: requires real agent invocation, run with --with-agent to include")
            skipped += 1
            continue

        try:
            if scenario.get("repeat_count"):
                results = [_run_deterministic(scenario) for _ in range(scenario["repeat_count"])]
                ok, reason = assert_fn(results)
            elif needs_agent:
                result = _run_full_agent(scenario)
                ok, reason = assert_fn(result)
            else:
                result = _run_deterministic(scenario)
                ok, reason = assert_fn(result)
        except Exception as e:
            ok, reason = False, f"Exception during eval: {e}"

        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {name}: {reason}")
        if ok:
            passed += 1
        else:
            failed += 1

    print(f"\n{passed} passed, {failed} failed, {skipped} skipped, {len(SCENARIOS)} total")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
