"""Market making strategy interfaces and contract specifications."""

from __future__ import annotations

from prosperity_toolkit.strategies.base import BaseStrategy


class MarketMakingStrategyContract(BaseStrategy):
    """Protocol contract for symmetric and inventory-skewed market makers."""
