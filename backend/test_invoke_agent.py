import json
from invoke_agent import invoke_agent_for_check

with open("../AgentNick/app/AgentNick/data/tariffs.json") as f:
    tariff_raw = json.load(f)

result = invoke_agent_for_check(
    scenario_type="tariff",
    raw_data=tariff_raw,
    as_of_date="2026-08-30",
)

print("=== FULL TEXT (last 800 chars) ===")
print(result["full_text"][-800:])
print()
print("=== PARSED CARDS ===")
print(json.dumps(result["cards"], indent=2))
