"""
SignalSource — abstraction for where raw scenario data comes from.

parse_financial_signals never reads files or calls APIs directly; it only
ever receives a raw dict via ParseSignalsInput. A SignalSource is
responsible for producing that dict, from whatever real or mock origin.

This keeps the ingestion layer swappable and makes explicit, in code,
which sources are implemented vs. planned — rather than the codebase
implying that local mock JSON is the permanent/only data path.
"""

from abc import ABC, abstractmethod


class SignalSource(ABC):
    @abstractmethod
    def fetch(self, source_type: str) -> dict:
        """Return a raw dict matching the shape parse_financial_signals expects
        for the given source_type ('tariff' | 'trial' | 'card_promo')."""
        raise NotImplementedError
