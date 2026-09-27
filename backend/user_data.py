"""
user_data.py

Per-user copies of scenario data. Each user gets their own editable
raw_data for each scenario_type, seeded from the shared mock template
on first access.
"""

import sqlite3, json, os
from pathlib import Path
from cryptography.fernet import Fernet

_fernet = Fernet(os.environ['EMAIL_ENCRYPTION_KEY'].encode())

_DB_PATH = Path(__file__).parent / "user_data.db"
_TEMPLATE_DIR = Path(__file__).parent.parent / "AgentNick" / "app" / "AgentNick" / "data"
_SCENARIO_FILES = {
    "tariff": "tariffs.json", "trial": "trial.json",
    "card_promo": "card_promo.json", "card_promo_incomplete": "card_promo_incomplete.json",
}


def _get_connection():
    conn = sqlite3.connect(_DB_PATH)
    conn.execute("""CREATE TABLE IF NOT EXISTS user_scenario_data (
        user_id TEXT NOT NULL, scenario_type TEXT NOT NULL, data_json TEXT NOT NULL,
        PRIMARY KEY (user_id, scenario_type))""")
    return conn


def has_user_data(user_id: str, scenario_type: str) -> bool:
    """A brand-new user has no data for any scenario until they
    explicitly connect a real source (Gmail, document upload) or
    choose to try an example scenario -- this is the correct real-world
    behavior: nothing appears until something real (or explicitly
    requested example) actually feeds it."""
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT 1 FROM user_scenario_data WHERE user_id = ? AND scenario_type = ?",
            (user_id, scenario_type)).fetchone()
        return row is not None
    finally:
        conn.close()


def get_user_data(user_id: str, scenario_type: str) -> dict | None:
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT data_json FROM user_scenario_data WHERE user_id = ? AND scenario_type = ?",
            (user_id, scenario_type)).fetchone()
        if row:
            return json.loads(_fernet.decrypt(row[0].encode()).decode())
        return None
    finally:
        conn.close()


_ORIGINAL_BASELINE = __import__("datetime").date(2026, 8, 30)
_DATE_FIELDS_BY_SCENARIO = {
    "tariff": ["contract_start_date", "contract_end_date"],
    "trial": ["trial_start_date", "trial_end_date", "cancellation_deadline"],
    "card_promo": ["promo_apr_start_date", "promo_apr_end_date", "next_payment_due_date"],
    "card_promo_incomplete": ["promo_apr_start_date", "promo_apr_end_date", "next_payment_due_date"],
    "insurance": ["renewal_date"],
    "membership": ["renewal_date"],
}


# The ORIGINAL, fixed day-offsets-from-baseline for each date field,
# captured once and never re-derived from the template file's current
# (mutable) contents -- re-deriving from the file caused a real
# double-shift bug, since the file's stored date changes every time
# this runs, but the intended STORY offset (e.g. "contract ends 16
# days after the demo baseline") never should.
_FIXED_OFFSETS_FROM_BASELINE = {
    "tariff": {"contract_start_date": -365, "contract_end_date": 16},
    "trial": {"trial_start_date": -11, "trial_end_date": 3, "cancellation_deadline": 0},
    "card_promo": {"promo_apr_start_date": -370, "promo_apr_end_date": 26, "next_payment_due_date": 6},
    "card_promo_incomplete": {"promo_apr_start_date": -370, "promo_apr_end_date": 26, "next_payment_due_date": 6},
    "insurance": {"renewal_date": 32},
    "membership": {"renewal_date": 21},
}


def _refresh_dates_relative_to_today(data: dict, scenario_type: str) -> dict:
    """Shifts every date field to be that field's FIXED, original offset
    from today -- never re-derives the offset from the template file's
    current (mutable) value, which would compound on every call."""
    from datetime import date, timedelta
    today = date.today()
    offsets = _FIXED_OFFSETS_FROM_BASELINE.get(scenario_type, {})
    for field, offset_days in offsets.items():
        if field in data:
            data[field] = (today + timedelta(days=offset_days)).isoformat()
    return data


def enable_example_scenario(user_id: str, scenario_type: str) -> dict:
    """Explicit opt-in: user chose to try an example scenario. This is
    the ONLY way example/template data gets seeded now -- never
    automatically on first check. Dates are refreshed relative to
    today every time this runs, so they never go stale."""
    template_path = _TEMPLATE_DIR / _SCENARIO_FILES[scenario_type]
    with open(template_path) as f:
        data = json.load(f)
    data = _refresh_dates_relative_to_today(data, scenario_type)
    data["user_id"] = user_id
    set_user_data(user_id, scenario_type, data)
    return data


def set_user_data(user_id: str, scenario_type: str, data: dict):
    conn = _get_connection()
    try:
        conn.execute("""INSERT INTO user_scenario_data (user_id, scenario_type, data_json)
            VALUES (?, ?, ?) ON CONFLICT(user_id, scenario_type) DO UPDATE SET data_json = excluded.data_json""",
            (user_id, scenario_type, _fernet.encrypt(json.dumps(data).encode()).decode()))
        conn.commit()
    finally:
        conn.close()


def _get_gmail_tracking_connection():
    conn = sqlite3.connect(_DB_PATH)
    conn.execute("""CREATE TABLE IF NOT EXISTS gmail_derived_scenarios (
        user_id TEXT NOT NULL, scenario_type TEXT NOT NULL,
        PRIMARY KEY (user_id, scenario_type))""")
    return conn


def mark_gmail_derived(user_id: str, scenario_type: str):
    conn = _get_gmail_tracking_connection()
    try:
        conn.execute("INSERT OR IGNORE INTO gmail_derived_scenarios (user_id, scenario_type) VALUES (?, ?)",
                     (user_id, scenario_type))
        conn.commit()
    finally:
        conn.close()


def get_gmail_derived_scenarios(user_id: str) -> list:
    conn = _get_gmail_tracking_connection()
    try:
        rows = conn.execute("SELECT scenario_type FROM gmail_derived_scenarios WHERE user_id = ?", (user_id,)).fetchall()
        return [r[0] for r in rows]
    finally:
        conn.close()


def delete_user_data(user_id: str, scenario_type: str):
    conn = _get_connection()
    try:
        conn.execute("DELETE FROM user_scenario_data WHERE user_id = ? AND scenario_type = ?", (user_id, scenario_type))
        conn.commit()
    finally:
        conn.close()


def clear_all_gmail_derived_data(user_id: str) -> list:
    """Deletes all scenario data that was populated from Gmail for this
    user, and clears the tracking markers. Returns the list of
    scenario_types that were cleared, so the caller can also clean up
    associated cards and fingerprints."""
    scenario_types = get_gmail_derived_scenarios(user_id)
    for scenario_type in scenario_types:
        delete_user_data(user_id, scenario_type)
    conn = _get_gmail_tracking_connection()
    try:
        conn.execute("DELETE FROM gmail_derived_scenarios WHERE user_id = ?", (user_id,))
        conn.commit()
    finally:
        conn.close()
    return scenario_types
