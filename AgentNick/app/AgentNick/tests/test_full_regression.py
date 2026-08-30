from datetime import date
import json

from tools.parse_financial_signals import parse_financial_signals
from tools.evaluate_tariff_parity import evaluate_tariff_parity
from tools.evaluate_card_promo import evaluate_card_promo
from tools.evaluate_payment_reminder import evaluate_payment_reminder
from tools.stage_tariff_card import stage_tariff_card
from tools.stage_trial_card import stage_trial_card
from tools.stage_card_promo_card import stage_card_promo_card
from tools.stage_payment_reminder_card import stage_payment_reminder_card
from tools.check_web_portal import check_web_portal
from tools.interfaces import (
    ParseSignalsInput, EvaluateTariffInput, EvaluateCardPromoInput,
    EvaluatePaymentReminderInput, TrialReminderState, PaymentReminderState,
    CheckWebPortalInput,
)

AS_OF = date(2026, 8, 30)

def load(name):
    with open(f"data/{name}.json") as f:
        return json.load(f)

# Tariff
raw = load("tariffs")
signal = parse_financial_signals(ParseSignalsInput(source_type="tariff", raw_data=raw), as_of_date=AS_OF)
evaluation = evaluate_tariff_parity(EvaluateTariffInput(signal=signal))
card = stage_tariff_card(evaluation, signal)
print("TARIFF:", "OK" if card and card.scenario_type == "broadband_tariff" else "FAIL")

# Trial
raw = load("trial")
signal = parse_financial_signals(ParseSignalsInput(source_type="trial", raw_data=raw), as_of_date=AS_OF)
state = TrialReminderState(user_id=raw["user_id"], service=raw["service"])
card = stage_trial_card(signal, state)
print("TRIAL:", "OK" if card and card.scenario_type == "trial_cancellation" else "FAIL")

# Card promo (promo countdown)
raw = load("card_promo")
signal = parse_financial_signals(ParseSignalsInput(source_type="card_promo", raw_data=raw), as_of_date=AS_OF)
evaluation = evaluate_card_promo(EvaluateCardPromoInput(signal=signal))
card = stage_card_promo_card(evaluation)
print("CARD_PROMO (countdown):", "OK" if card and card.scenario_type == "card_promo" else "FAIL")

# Card promo (payment reminder)
pr_state = PaymentReminderState(user_id=raw["user_id"], card_provider=raw["card_provider"])
signal2 = parse_financial_signals(ParseSignalsInput(source_type="card_promo", raw_data=raw), as_of_date=date(2026, 9, 3))
pr_eval = evaluate_payment_reminder(EvaluatePaymentReminderInput(signal=signal2), pr_state, as_of_date=date(2026, 9, 3))
pr_card = stage_payment_reminder_card(pr_eval)
print("CARD_PROMO (payment reminder):", "OK" if pr_card else "FAIL")

# Hobby registration (scraper — requires mock-site server running separately)
try:
    result = check_web_portal(CheckWebPortalInput(url="http://localhost:8000/index.html"), as_of_date=AS_OF)
    print("HOBBY_REGISTRATION (scrape):", "OK" if result.scrape_successful else f"FAIL: {result.error_message}")
except Exception as e:
    print("HOBBY_REGISTRATION (scrape):", f"ERROR: {e}")

print()
print("Regression check complete.")
