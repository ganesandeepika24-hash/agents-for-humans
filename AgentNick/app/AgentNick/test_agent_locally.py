import asyncio
import json

from main import get_or_create_agent

incomplete_raw = {
    "user_id": "demo_user",
    "card_provider": "ExampleBank",
    "current_balance_gbp": 900.0,
    "promo_apr_end_date": "2026-09-25",
    # deliberately missing: standard_apr_pct
    # deliberately missing: any comparable balance transfer offer
}

prompt = f"""I want you to check on this signal for me. Here is the raw data:

source_type: "card_promo"
raw_data: {json.dumps(incomplete_raw)}

Today's date is 2026-08-30. Please evaluate this signal following your
standard process.
"""

async def main():
    agent = get_or_create_agent("test-session-missing")
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