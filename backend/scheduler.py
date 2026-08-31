"""
scheduler.py

Runs /check-equivalent logic on a timer, across all known scenario
types, without any user action. Uses signal_state (via the deployed
agent's own SQLite state, queried through a lightweight local check)
to avoid re-notifying about cards already sent. Sends a digest email
via Resend for any newly-found cards.

This is the real "proactive" mechanism: the user never has to open the
dashboard or click a button for AgentNick to notice something and
reach them.
"""

import json
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler

from invoke_agent import invoke_agent_for_check
from send_email import send_action_email
from push_notifications import send_push_to_all

DATA_DIR = Path(__file__).parent.parent / "AgentNick" / "app" / "AgentNick" / "data"
_SCENARIO_FILES = {
    "tariff": "tariffs.json",
    "trial": "trial.json",
    "card_promo": "card_promo.json",
}

# Simple local record of card_ids we've already notified about this run,
# so a digest isn't re-sent every single scheduler tick for the same card.
_notified_card_ids = set()


def run_scheduled_check():
    print("[scheduler] Running scheduled check across all scenarios...")
    new_cards = []

    for scenario_type, filename in _SCENARIO_FILES.items():
        data_path = DATA_DIR / filename
        with open(data_path) as f:
            raw_data = json.load(f)

        try:
            result = invoke_agent_for_check(
                scenario_type=scenario_type,
                raw_data=raw_data,
                as_of_date="2026-08-30",
            )
        except Exception as e:
            print(f"[scheduler] Error checking {scenario_type}: {e}")
            continue

        for card in result.get("cards", []):
            card_id = card.get("card_id")
            if card_id and card_id not in _notified_card_ids:
                new_cards.append(card)
                _notified_card_ids.add(card_id)

    if new_cards:
        _send_digest(new_cards)
    else:
        print("[scheduler] No new cards found this run.")


def _send_digest(cards: list[dict]):
    lines = [f"AgentNick found {len(cards)} thing(s) that need your attention:\n"]
    for card in cards:
        savings = card.get("computed_savings_gbp")
        savings_str = f" (£{savings:.2f} potential impact)" if savings else ""
        lines.append(f"• {card['title']}{savings_str}\n  {card['summary']}\n")

    body = "\n".join(lines)

    result = send_action_email(
        to="you",
        subject=f"AgentNick: {len(cards)} update(s) need your attention",
        body=body,
    )
    print(f"[scheduler] Digest email sent: {result.get('id')}")

    send_push_to_all(
        title=f"AgentNick: {len(cards)} update(s)",
        body=cards[0]["title"] if len(cards) == 1 else f"{len(cards)} things need your attention",
        url="/static/index.html",
    )


def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(run_scheduled_check, "interval", minutes=2, id="agentnick_check")
    scheduler.start()
    print("[scheduler] Started — checking every 2 minutes.")
    return scheduler
