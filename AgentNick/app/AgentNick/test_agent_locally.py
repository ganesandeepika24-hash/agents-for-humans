import asyncio
import json

from main import get_or_create_agent

with open("data/tariffs.json") as f:
    tariff_raw = json.load(f)

prompt = f"""I want you to check on my broadband situation. Here is the raw data
you have access to for this signal:

source_type: "tariff"
raw_data: {json.dumps(tariff_raw)}

Today's date is 2026-08-30. Please evaluate this signal following your
standard process.
"""

async def main():
    agent = get_or_create_agent("test-session-2")
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
            if "toolUse" in delta:
                print(f"    input chunk: {delta['toolUse'].get('input', '')}", end="")

        if "message" in e:
            msg = e["message"]
            if msg.get("role") == "user":
                for block in msg.get("content", []):
                    if "toolResult" in block:
                        tr = block["toolResult"]
                        print(f"\n<<< TOOL RESULT status={tr.get('status')}")
                        print(f"    content: {tr.get('content')}")

asyncio.run(main())