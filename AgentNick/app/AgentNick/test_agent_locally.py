import asyncio
import json

from main import get_or_create_agent

gym_raw = {
    "user_id": "demo_user",
    "provider": "FitZone Gym",
    "current_monthly_price_gbp": 35.0,
    "contract_end_date": "2026-09-20",
    "renewal_monthly_price_gbp": 55.0,
    "annual_membership_price_gbp": 480.0,
    "competitor_options": [
        {"provider": "PureGym", "monthly_price_gbp": 25.0, "signup_fee_gbp": 0.0},
    ],
}

prompt = f"""I want you to check on this signal for me. Here is the raw data:

source_type: "gym_membership"
raw_data: {json.dumps(gym_raw)}

Today's date is 2026-08-30. Please evaluate this signal following your
standard process.
"""

async def main():
    agent = get_or_create_agent("test-session-gym")
    async for event in agent.stream_async(prompt):
        if not isinstance(event, dict) or "event" not in event:
            continue
        e = event["event"]
        if "contentBlockStart" in e:
            start = e["contentBlockStart"].get("start", {})
            if "toolUse" in start:
                print(f"\n>>> TOOL CALL: {start['toolUse'].get('name')}")
        if "contentBlockDelta" in e:
            delta = e["contentBlockDelta"].get("delta", {})
            if "text" in delta:
                print(delta["text"], end="", flush=True)

asyncio.run(main())