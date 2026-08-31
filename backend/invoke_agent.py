"""
invoke_agent.py

Core function for calling the deployed AgentNick agent on AWS Bedrock
AgentCore for /check-style evaluations. Captures the exact card data
by reading the finalize_check tool call's INPUT arguments directly
from the streamed events, rather than parsing the model's prose --
proven more reliable, since tool-call inputs are passed through
exactly as generated, while prose reconstruction of prior tool
results is not reliable.
"""

import json
import uuid

import boto3

RUNTIME_ARN = "arn:aws:bedrock-agentcore:eu-central-1:299276269111:runtime/AgentNick_AgentNick-a4vHUs5YeY"


def invoke_agent_for_check(
    scenario_type: str,
    raw_data: dict,
    as_of_date: str,
    threshold_min_gbp: float | None = None,
    threshold_min_pct: float | None = None,
) -> dict:
    """
    Sends a data-driven evaluation prompt to the deployed agent and
    returns {"full_text": str, "cards": list[dict]}.
    """
    client = boto3.client("bedrock-agentcore", region_name="eu-central-1")

    threshold_instruction = ""
    if threshold_min_gbp is not None or threshold_min_pct is not None:
        parts = []
        if threshold_min_gbp is not None:
            parts.append(f"£{threshold_min_gbp}")
        if threshold_min_pct is not None:
            parts.append(f"{threshold_min_pct}%")
        threshold_instruction = (
            f"\nThis user has set their own savings threshold: {' or '.join(parts)}. "
            f"When calling check_savings_threshold, pass this as "
            f"user_min_gbp_override/user_min_pct_override instead of using the system default."
        )

    prompt = f"""I want you to check on this signal. Here is the raw data:
source_type: {scenario_type}
raw_data: {json.dumps(raw_data)}
Today's date is {as_of_date}. Please evaluate this signal following your
standard process.{threshold_instruction}"""

    response = client.invoke_agent_runtime(
        agentRuntimeArn=RUNTIME_ARN,
        runtimeSessionId=str(uuid.uuid4()),
        payload=json.dumps({"prompt": prompt}).encode("utf-8"),
    )

    stream = response["response"]
    full_text = ""
    cards = []

    current_tool_name = None
    current_tool_input_buffer = ""

    for line in stream.iter_lines():
        if not line:
            continue
        decoded = line.decode("utf-8")
        if not decoded.startswith("data:"):
            continue
        data_str = decoded[len("data:"):].strip()
        try:
            event = json.loads(data_str)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict) or "event" not in event:
            continue
        e = event["event"]

        if "contentBlockStart" in e:
            start = e["contentBlockStart"].get("start", {})
            if "toolUse" in start:
                current_tool_name = start["toolUse"].get("name")
                current_tool_input_buffer = ""

        if "contentBlockDelta" in e:
            delta = e["contentBlockDelta"].get("delta", {})
            if "text" in delta:
                full_text += delta["text"]
            if "toolUse" in delta:
                current_tool_input_buffer += delta["toolUse"].get("input", "")

        if "contentBlockStop" in e:
            if current_tool_name == "finalize_check" and current_tool_input_buffer:
                try:
                    parsed = json.loads(current_tool_input_buffer)
                    cards = parsed.get("cards", [])
                except json.JSONDecodeError:
                    pass
            current_tool_name = None
            current_tool_input_buffer = ""

    return {"full_text": full_text, "cards": cards}
