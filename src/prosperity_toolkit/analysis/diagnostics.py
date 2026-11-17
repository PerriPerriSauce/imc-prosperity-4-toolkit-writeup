"""Overfitting diagnostics including Deflated Sharpe Ratio (DSR) and trial adjustments."""

from __future__ import annotations

import math


class OverfittingDiagnostics:
    """Statistical corrections for multiple testing and backtest overfitting."""

    @staticmethod
    def estimate_expected_max_sharpe(n_trials: int, variance_sharpe: float = 1.0) -> float:
        """Approximation of the expected maximum Sharpe ratio from N independent trials.

        Using extreme value theory: E[max_N] ~ sqrt(2 * ln(N)) * std_dev.
        """
        if n_trials <= 1:
            return 0.0
        return math.sqrt(2.0 * math.log(n_trials)) * math.sqrt(variance_sharpe)
