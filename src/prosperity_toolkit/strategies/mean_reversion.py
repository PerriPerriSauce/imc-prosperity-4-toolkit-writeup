"""Mean-reversion strategy contracts."""

from __future__ import annotations

from prosperity_toolkit.strategies.base import BaseStrategy


class MeanReversionStrategyContract(BaseStrategy):
    """Protocol contract for Ornstein-Uhlenbeck and Bollinger/Z-score mean reversion."""
