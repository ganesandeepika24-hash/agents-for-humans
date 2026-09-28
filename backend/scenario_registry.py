"""
scenario_registry.py

The single source of truth for which scenario types exist and what
mock data file each one maps to. Previously duplicated separately in
app.py, scheduler.py, and user_data.py -- that duplication caused a
real bug (user_data.py's copy was missing insurance/membership,
silently breaking enable_example_scenario for those two types for
this entire session). Every file should import from here instead of
defining its own copy.
"""

SCENARIO_FILES = {
    "tariff": "tariffs.json",
    "trial": "trial.json",
    "card_promo": "card_promo.json",
    "card_promo_incomplete": "card_promo_incomplete.json",
    "insurance": "insurance.json",
    "membership": "membership.json",
}
