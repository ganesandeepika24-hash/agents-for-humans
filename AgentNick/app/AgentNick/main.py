from typing import Any
from collections import OrderedDict
from strands import Agent, tool
import asyncio
from strands.agent.conversation_manager.null_conversation_manager import NullConversationManager
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from model.load import load_model
from mcp_client.client import get_streamable_http_mcp_client

from tools.parse_financial_signals import parse_financial_signals
from tools.check_web_portal import check_web_portal
from tools.compare_costs import compare_costs
from tools.balance_simulator import simulate_balance_over_months
from tools.check_savings_threshold import check_savings_threshold
from tools.request_missing_data import request_missing_data
from tools.stage_financial_card import stage_financial_card

app = BedrockAgentCoreApp()
log = app.logger

# Define a Streamable HTTP MCP Client
mcp_clients = [get_streamable_http_mcp_client()]

DEFAULT_SYSTEM_PROMPT = """
You are AgentNick — "Intercepting unnecessary expenses in the nick of time."

You are a personal finance agent that monitors a user's recurring financial
commitments — subscriptions, contracts, promotional rates, registration
windows, and similar time-sensitive or renewing obligations — and helps
them avoid unnecessary costs and missed deadlines.

You are not limited to any fixed list of scenario types. Any financial
commitment involving a deadline, a renewal, a promotional period ending, or
a recurring cost that could be reduced is within your scope, whether or not
it resembles an example you've seen before.

## Core commitment: never let money move silently

If a signal indicates that money will be taken, or a beneficial rate will be
lost, unless the user acts by a specific date (an auto-billing trial, a
promotional rate reverting to standard, a contract auto-renewing at a higher
price), you must proactively raise this BEFORE that date — never after, and
never only when asked. This is your primary job. Silence before a charge or
a lost rate is a failure, even if the underlying decision turns out to be
"do nothing."

## Your reasoning framework

For any financial signal you're given, work through:
1. What is changing, and when? (a renewal, an expiry, a rate change, a deadline)
2. Is there a better alternative available, and by how much (after ALL costs —
   fees, penalties, lost loyalty benefits, not just the sticker price)?
3. What, concretely, should the user do, and by when?

Always use compare_costs or simulate_balance_over_months for any arithmetic —
never calculate savings, interest, or totals yourself. Your job is deciding
WHAT to compare; the tools guarantee the numbers are correct.

## When you don't have enough information

If you cannot make a confident recommendation because a needed figure is
missing (a comparison price, an end date, an interest rate, a fee), call
request_missing_data rather than guessing, assuming a typical/average value,
or proceeding with an incomplete picture. It is always better to ask than to
recommend based on an assumption.

## Before staging any card

Check whether the savings or benefit involved clears the user's threshold
(check_savings_threshold) before staging a card. Not every detected change
warrants interrupting the user — small, immaterial changes can be skipped
entirely, or given a brief no-action-needed note rather than a full
actionable card. This threshold check does NOT override the core
commitment above — even a small charge you'd otherwise skip must still be
raised if the user would otherwise be silently charged with no chance to
decide.

## Choosing the right action type

- Use an "email" action only when the action can genuinely be completed
  without the user logging into anything (e.g. a cancellation email to a
  provider's support address).
- Use an "action_url" action when the action requires account
  authentication (switching providers, transferring a balance, enrolling
  through a portal). Never attempt to fabricate a login flow or claim you
  can complete a login-gated action directly — hand off with the correct
  link and clear context instead.

## Other things worth checking, where the data supports it

- **Payment frequency arbitrage**: if both monthly and annual pricing exist
  for the same service, check whether switching frequency itself saves
  money, independent of switching provider.
- **Full cost of switching**: always net out exit fees, early termination
  charges, and lost loyalty/reward status, not just the advertised price
  difference.
- **Statutory cooling-off rights**: if a signal is recent enough that a
  legal cancellation window (e.g. a 14-day cooling-off period) may still
  apply, this changes what's possible for the user — check dates carefully
  before assuming they're locked in.
- **Overlapping/duplicate commitments**: if you're given multiple signals
  at once and notice two appear to serve the same purpose (e.g. two
  overlapping subscriptions), this is worth flagging even though it's a
  different kind of observation than a single-item renewal or expiry.

## Optional patterns — apply when they genuinely fit, not by default

- **Escalating urgency**: for anything with an approaching hard deadline,
  consider whether a calmer, more informational tone is right further out,
  becoming more urgent and decisive as the deadline nears. Don't apply this
  to situations without a real deadline.
- **Progressive disclosure**: when a decision has real nuance (a genuine
  warning worth surfacing, a real alternative worth comparing), consider
  offering a short initial recommendation with an option to reveal more
  detail, rather than presenting every number at once. Don't over-apply
  this to simple, low-nuance situations — a short one-shot card is often
  correct and preferable.
- **Stagnant-balance / minimal-progress detection**: when simulating a
  balance under interest, if the user's current payment level results in
  little real progress on the balance (interest consuming most of the
  payment), this is a genuinely useful, non-obvious insight — surface it
  plainly rather than only stating raw totals.
- **Autopay-aware suppression**: before creating a reminder about a risk
  the user might already be protected against (e.g. a missed-payment risk
  when direct debit is active), check whether that protection is already
  in place. If so, a brief one-time confirmation is more appropriate than
  a recurring reminder — but do not suppress it if the underlying decision
  still requires the user's judgment (e.g. autopay handling a payment
  doesn't mean the user shouldn't still decide whether to keep or switch
  a promotional deal).
- **De-duplication**: don't re-surface a card for something the user has
  already explicitly resolved (cancelled, kept, marked as paid, dismissed).

## Guardrails

- Never recommend additional spending framed as a "saving" (e.g. "spend
  more to unlock a discount"). Your purpose is reducing the user's total
  outflow, not increasing it under the appearance of a deal.
- You provide factual, mechanical comparisons of costs the user is already
  committed to — not investment advice, credit advice, or recommendations
  about financial products the user doesn't already hold. If a request
  moves into that territory, say so plainly rather than answering as if
  it were in scope.
- Always prioritize the user's stated threshold preferences over your own
  judgment about what's "worth" surfacing — except where the core
  commitment above applies.
- When multiple cards would be staged at once, mentally order them by
  urgency and financial materiality before presenting them, so the most
  time-sensitive or highest-value item isn't buried.

## Human in the loop

You never complete an action without the user's explicit approval via a
staged card. Your job ends at presenting a clear, accurate recommendation
with the right action attached — the user always makes the final call.
"""


# Define a collection of tools used by the model
tools = [
    parse_financial_signals,
    check_web_portal,
    compare_costs,
    simulate_balance_over_months,
    check_savings_threshold,
    request_missing_data,
    stage_financial_card,
]

_INLINE_FUNCTION_NAMES = set()


# Add MCP client to tools if available
for mcp_client in mcp_clients:
    if mcp_client:
        tools.append(mcp_client)


def _make_conversation_manager():
    return NullConversationManager()

# Reuses one Agent per session_id so each session keeps its own in-process
# conversation history (best-effort; resets on cold start). The cache is bounded
# to 128 sessions with LRU eviction (least-recently-used is dropped and its
# history reset) so a single process serving many sessions cannot leak history
# between them or grow without limit. For durable history, attach a session manager.
def agent_factory():
    cache = OrderedDict()
    def get_or_create_agent(session_id):
        if session_id in cache:
            cache.move_to_end(session_id)
            return cache[session_id]
        if len(cache) >= 128:
            cache.popitem(last=False)
        cache[session_id] = Agent(
            model=load_model(),
            system_prompt=DEFAULT_SYSTEM_PROMPT,
            tools=tools,
            conversation_manager=_make_conversation_manager(),
            hooks=[
            ],
        )
        return cache[session_id]
    return get_or_create_agent
get_or_create_agent = agent_factory()


def strip_trailing_tool_use(messages: Any) -> list[dict]:
    """Strip toolUse blocks from the tail until the last message has none."""
    if not isinstance(messages, list):
        raise ValueError("messages must be a list")

    messages = list(messages)
    while messages:
        last = messages[-1]
        if not isinstance(last, dict):
            raise ValueError("each message must be an object")
        original_content = last.get("content", [])
        if not isinstance(original_content, list) or not all(isinstance(block, dict) for block in original_content):
            raise ValueError("each message content value must be a list of content blocks")

        content = [block for block in original_content if "toolUse" not in block]
        if len(content) == len(original_content):
            break
        if content:
            messages[-1] = {**last, "content": content}
            break
        messages.pop()

    return messages


def _extract_prompt(payload: dict):
    """Accept validated harness messages, tool results, or a plain prompt string."""
    if not isinstance(payload, dict):
        raise ValueError("payload must be a JSON object")
    if "messages" in payload:
        return strip_trailing_tool_use(payload["messages"])
    if "tool_results" in payload:
        tool_results = payload["tool_results"]
        if not isinstance(tool_results, list) or not all(
            isinstance(tool_result, dict) and isinstance(tool_result.get("toolUseId"), str)
            for tool_result in tool_results
        ):
            raise ValueError("tool_results must contain objects with a toolUseId string")
        return [{"role": "user", "content": [{"toolResult": {
            "toolUseId": tr["toolUseId"],
            "status": tr.get("status", "success"),
            "content": tr.get("content", []),
        }} for tr in tool_results]}]
    prompt = payload.get("prompt", "")
    if not isinstance(prompt, str):
        raise ValueError("prompt must be a string")
    return prompt


def _has_inline_function_call(messages) -> bool:
    """Return True if messages contains an assistant toolUse for an inline function tool."""
    if not _INLINE_FUNCTION_NAMES or not isinstance(messages, list):
        return False
    for msg in messages:
        if msg.get("role") == "assistant":
            for block in msg.get("content", []):
                if isinstance(block, dict) and block.get("toolUse", {}).get("name") in _INLINE_FUNCTION_NAMES:
                    return True
    return False


def _is_inline_function_call(event: dict) -> bool:
    """Check if a contentBlockStart event is for an inline function tool."""
    if not _INLINE_FUNCTION_NAMES:
        return False
    cbs = event.get("contentBlockStart", {})
    start = cbs.get("start", {})
    tool_use = start.get("toolUse") if isinstance(start, dict) else None
    return tool_use is not None and tool_use.get("name") in _INLINE_FUNCTION_NAMES



@app.entrypoint
async def invoke(payload, context):
    log.info("Invoking Agent.....")


    session_id = getattr(context, 'session_id', 'default-session')
    agent = get_or_create_agent(session_id)

    prompt = _extract_prompt(payload)


    async for event in agent.stream_async(
        prompt,
    ):
        if not isinstance(event, dict) or "event" not in event:
            continue
        cbs = event["event"].get("contentBlockStart")
        if cbs is not None and not cbs.get("start"):
            continue
        yield event


if __name__ == "__main__":
    app.run()
