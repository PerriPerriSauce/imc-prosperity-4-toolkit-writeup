"""Microstructure indicators, rolling metrics, and volatility estimators."""

from __future__ import annotations

import math
from collections import deque


class MarketIndicators:
    """Fast online indicator calculations using fixed-size circular buffers."""

    @staticmethod
    def exponential_moving_average(current: float, prev_ema: float, alpha: float) -> float:
        """Compute single-step exponential moving average update."""
        return alpha * current + (1.0 - alpha) * prev_ema

    @staticmethod
    def rolling_volatility(buffer: deque[float]) -> float:
        """Calculate sample standard deviation of buffered prices."""
        n = len(buffer)
        if n < 2:
            return 0.0
        mean = sum(buffer) / n
        variance = sum((x - mean) ** 2 for x in buffer) / (n - 1)
        return math.sqrt(variance)
