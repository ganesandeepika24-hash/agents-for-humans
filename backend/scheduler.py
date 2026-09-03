"""
scheduler.py

Runs /check-equivalent logic on a timer, across all registered users
and all known scenario types, without any user action. Uses cards.py
(persistent, per-user) to avoid re-notifying about signals already
surfaced. Sends a digest email + push per user for any newly-found
cards belonging to them.
"""

import json
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler

from invoke_agent import invoke_agent_for_check
from send_email import send_action_email
from push_notifications import send_push_to_user
from users import list_all_user_ids
from cards import has_been_notified, record_notification

_paused = False


def pause():
    global _paused
    _paused = True
    print("[scheduler] Paused.")


def resume():
    global _paused
    _paused = False
    print("[scheduler] Resumed.")


def is_paused() -> bool:
    return _paused

DATA_DIR = Path(__file__).parent.parent / "AgentNick" / "app" / "AgentNick" / "data"
_SCENARIO_FILES = {
    "tariff": "tariffs.json",
    "trial": "trial.json",
    "card_promo": "card_promo.json",
}


def run_scheduled_check():
    if _paused:
        print("[scheduler] Skipped (paused).")
        return

    print("[scheduler] Running scheduled check across all users and scenarios...")
    user_ids = list_all_user_ids()

    if not user_ids:
        print("[scheduler] No registered users yet, skipping.")
        return

    for user_id in user_ids:
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
                print(f"[scheduler] Error checking {scenario_type} for {user_id}: {e}")
                continue

            for card in result.get("cards", []):
                signal_id = card.get("signal_id")
                if signal_id and not has_been_notified(user_id, signal_id):
                    new_cards.append(card)
                    record_notification(user_id, signal_id, card)

        if new_cards:
            _send_digest(user_id, new_cards)
        else:
            print(f"[scheduler] No new cards for user {user_id} this run.")


def _send_digest(user_id: str, cards: list[dict]):
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
    print(f"[scheduler] Digest email sent for user {user_id}: {result.get('id')}")

    if len(cards) == 1:
        card = cards[0]
        actions = []
        for opt in card.get("options", [])[:2]:
            opt_type = opt.get("option_type")
            if opt_type in ("dismiss", "remind_later"):
                actions.append({"action": opt_type, "title": opt.get("label", opt_type)})
        send_push_to_user(
            user_id,
            title=card["title"],
            body=card["summary"][:150],
            url="/static/index.html",
            card_id=card.get("card_id"),
            signal_id=card.get("signal_id"),
            actions=actions,
        )
    else:
        send_push_to_user(
            user_id,
            title=f"AgentNick: {len(cards)} update(s)",
            body=f"{len(cards)} things need your attention",
            url="/static/index.html",
        )


def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(run_scheduled_check, "interval", minutes=30, id="agentnick_check")
    scheduler.start()
    print("[scheduler] Started — checking every 30 minutes.")
    return scheduler
