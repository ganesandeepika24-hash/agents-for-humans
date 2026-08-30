"""
MockJSONSource — reads local mock data files.

This is the demo/development implementation of SignalSource. It is
functionally interchangeable with any other SignalSource; nothing in
parse_financial_signals or any evaluator depends on data having come
from a file specifically.
"""

import json
from pathlib import Path

from .base import SignalSource

_FILENAME_MAP = {
    "tariff": "tariffs.json",
    "trial": "trial.json",
    "card_promo": "card_promo.json",
}


class MockJSONSource(SignalSource):
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)

    def fetch(self, source_type: str) -> dict:
        if source_type not in _FILENAME_MAP:
            raise ValueError(f"Unknown source_type: {source_type}")
        path = self.data_dir / _FILENAME_MAP[source_type]
        with open(path) as f:
            return json.load(f)
