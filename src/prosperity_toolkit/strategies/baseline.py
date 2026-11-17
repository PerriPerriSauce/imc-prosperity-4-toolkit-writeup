"""Passive baseline strategy interfaces (e.g. hold-1 unit, no-op)."""

from __future__ import annotations

from prosperity_toolkit.core.models import OrderRequest
from prosperity_toolkit.market.market_state import MarketStateSnapshot
from prosperity_toolkit.strategies.base import BaseStrategy


class NoOpBaselineStrategy(BaseStrategy):
    """Null strategy emitting zero orders for benchmark control purposes."""

    def __init__(self) -> None:
        super().__init__(name="NoOpBaseline")

    def generate_orders(self, state: MarketStateSnapshot) -> list[OrderRequest]:
        """Return empty list of orders."""
        return []
