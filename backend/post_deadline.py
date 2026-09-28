"""
post_deadline.py

Rewrites a card's displayed text once its deadline has passed, so it
accurately reflects what happened rather than continuing to show
"act now" urgency about a moment that's already gone. No AI call
needed -- we already know the outcome from the data itself.
"""

_TEMPLATES = {
    "tariff": lambda d: (
        f"{d.get('provider', 'Your provider')} renewed at £{d.get('renewal_price_gbp', 0):.2f}/month",
        f"Your contract with {d.get('provider', 'your provider')} has renewed. "
        f"You're now paying £{d.get('renewal_price_gbp', 0):.2f}/month, up from £{d.get('current_price_gbp', 0):.2f}/month.",
    ),
    "card_promo": lambda d: (
        f"{d.get('card_provider', 'Your card')}: standard rate now applies",
        f"Your promotional rate with {d.get('card_provider', 'your provider')} has ended. "
        f"Your balance is now accruing interest at {d.get('standard_apr_pct', '?')}% APR.",
    ),
    "card_promo_incomplete": lambda d: (
        f"{d.get('card_provider', 'Your card')}: standard rate now applies",
        f"Your promotional rate with {d.get('card_provider', 'your provider')} has ended.",
    ),
    "trial": lambda d: (
        f"{d.get('service', 'Your trial')} is now billing you",
        f"Your {d.get('service', 'service')} trial has ended and you're now being charged "
        f"£{d.get('auto_bill_amount_gbp', 0):.2f}/{d.get('billing_frequency', 'month')}.",
    ),
    "insurance": lambda d: (
        f"{d.get('provider', 'Your policy')} renewed at £{d.get('renewal_price_gbp', '?')}",
        f"Your {d.get('policy_type', 'insurance')} policy with {d.get('provider', 'your provider')} "
        f"has renewed at £{d.get('renewal_price_gbp', 0):.2f}.",
    ),
    "membership": lambda d: (
        f"{d.get('provider', 'Your membership')} renewed at £{d.get('renewal_price_gbp', 0):.2f}/month",
        f"Your membership with {d.get('provider', 'your provider')} has renewed. "
        f"You're now paying £{d.get('renewal_price_gbp', 0):.2f}/month.",
    ),
}


def reword_for_expiry(card: dict, raw_data: dict) -> dict:
    """Returns a copy of the card with title/summary rewritten to
    reflect the deadline having passed. Options are cleared (nothing
    left to act on before the fact) except a plain dismiss."""
    scenario_type = card.get("scenario_type")
    template_fn = _TEMPLATES.get(scenario_type)

    reworded = dict(card)
    if template_fn:
        title, summary = template_fn(raw_data)
        reworded["title"] = title
        reworded["summary"] = summary
    else:
        reworded["title"] = f"{reworded.get('title', 'This')} — deadline has passed"
        reworded["summary"] = "This deadline has passed. No further action is available here."

    reworded["options"] = [
        {"label": "Got it", "option_type": "dismiss", "email_payload": None, "action_url": None}
    ]
    reworded["computed_savings_gbp"] = None
    return reworded
