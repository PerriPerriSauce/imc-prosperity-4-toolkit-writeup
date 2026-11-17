"""Descriptive statistics, moments, and distribution properties."""

from __future__ import annotations

import math
from collections.abc import Sequence


class SummaryStatistics:
    """Calculates distribution statistics for empirical time series."""

    @staticmethod
    def mean(series: Sequence[float]) -> float:
        """Arithmetic mean."""
        return sum(series) / len(series) if series else 0.0

    @staticmethod
    def variance(series: Sequence[float]) -> float:
        """Sample variance."""
        n = len(series)
        if n < 2:
            return 0.0
        m = sum(series) / n
        return sum((x - m) ** 2 for x in series) / (n - 1)

    @staticmethod
    def standard_deviation(series: Sequence[float]) -> float:
        """Sample standard deviation."""
        return math.sqrt(SummaryStatistics.variance(series))
