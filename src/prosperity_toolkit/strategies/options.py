"""Option and derivative volatility trading strategy contracts."""

from __future__ import annotations

from prosperity_toolkit.strategies.base import BaseStrategy


class OptionsStrategyContract(BaseStrategy):
    """Protocol contract for Black-Scholes implied volatility and delta hedging."""
