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
    agent = get_or_create_agent("test-session-3")
    async for event in agent.stream_async(prompt):
        if not isinstance(event, dict) or "event" not in event:
            continue
        e = event["event"]

        if "contentBlockStart" in e:
            start = e["contentBlockStart"].get("start", {})
            if "toolUse" in start:
                print(f"\n>>> TOOL CALL: {start['toolUse'].get('name')}")

        if "contentBlockStop" in e:
            pass  # end of a block, no action needed

        # Tool results come back as part of the next model turn's input --
        # print the raw message content whenever it contains a toolResult
        if "message" in e:
            for block in e["message"].get("content", []):
                if isinstance(block, dict) and "toolResult" in block:
                    tr = block["toolResult"]
                    status = tr.get("status")
                    content = tr.get("content")
                    print(f"<<< TOOL RESULT status={status}")
                    print(f"    {json.dumps(content)[:500]}")

        if "contentBlockDelta" in e:
            delta = e["contentBlockDelta"].get("delta", {})
            if "text" in delta:
                print(delta["text"], end="", flush=True)

asyncio.run(main())