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


def enable_example_scenario(user_id: str, scenario_type: str) -> dict:
    """Explicit opt-in: user chose to try an example scenario. This is
    the ONLY way example/template data gets seeded now -- never
    automatically on first check."""
    template_path = _TEMPLATE_DIR / _SCENARIO_FILES[scenario_type]
    with open(template_path) as f:
        data = json.load(f)
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
