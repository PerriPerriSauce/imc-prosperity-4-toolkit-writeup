"""Quantitative performance metrics, Sharpe ratio, and drawdown diagnostics."""

from __future__ import annotations

import math
from collections.abc import Sequence


class PerformanceMetrics:
    """Calculates quantitative risk-adjusted performance measures."""

    @staticmethod
    def calculate_sharpe_ratio(
        returns: Sequence[float],
        risk_free_rate: float = 0.0,
        annualization_factor: float = 252.0,
    ) -> float:
        """Compute annualized Sharpe ratio from a series of periodic returns."""
        if len(returns) < 2:
            return 0.0

        mean_return = sum(returns) / len(returns) - risk_free_rate
        squared_diffs = [(r - (mean_return + risk_free_rate)) ** 2 for r in returns]
        variance = sum(squared_diffs) / (len(returns) - 1)
        std_dev = math.sqrt(variance)

        if std_dev == 0.0:
            return 0.0

        return (mean_return / std_dev) * math.sqrt(annualization_factor)

    @staticmethod
    def calculate_max_drawdown(equity_curve: Sequence[float]) -> tuple[float, int]:
        """Compute maximum drawdown magnitude and duration.

        Returns:
            Tuple of (max_drawdown_amount, max_drawdown_duration_ticks).
        """
        if not equity_curve:
            return 0.0, 0

        peak = equity_curve[0]
        max_dd = 0.0
        current_duration = 0
        max_duration = 0

        for val in equity_curve:
            if val > peak:
                peak = val
                current_duration = 0
            else:
                dd = peak - val
                if dd > max_dd:
                    max_dd = dd
                current_duration += 1
                if current_duration > max_duration:
                    max_duration = current_duration

        return max_dd, max_duration
