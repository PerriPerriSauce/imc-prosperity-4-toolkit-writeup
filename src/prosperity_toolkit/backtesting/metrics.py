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
        annualization_factor: float = 1.0,
    ) -> float:
        """Compute Sharpe / information ratio scaled by sqrt(annualization_factor).

        Defaults to `annualization_factor=1.0` (unscaled per-observation ratio) so
        tick-level series are never mislabeled as 252-day annualized Sharpes.
        """
        if annualization_factor <= 0.0:
            msg = f"annualization_factor must be strictly positive, got {annualization_factor}"
            raise ValueError(msg)
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
    def calculate_block_sharpe(returns: Sequence[float], block_size: int = 1000) -> float:
        """Compute Sharpe ratio across disjoint non-overlapping return blocks."""
        if block_size <= 0:
            msg = f"block_size must be strictly positive, got {block_size}"
            raise ValueError(msg)
        n_blocks = len(returns) // block_size
        if n_blocks < 2:
            return 0.0
        block_rets = [
            float(sum(returns[i * block_size : (i + 1) * block_size]))
            for i in range(n_blocks)
        ]
        mean_ret = sum(block_rets) / n_blocks
        var = sum((r - mean_ret) ** 2 for r in block_rets) / (n_blocks - 1)
        std = math.sqrt(var)
        return (mean_ret / std) if std > 0.0 else 0.0

    @staticmethod
    def calculate_pnl_to_drawdown(total_pnl: float, max_drawdown: float) -> float:
        """Compute finite intraday PnL-to-MaxDrawdown ratio (0.0 when MaxDD == 0)."""
        if max_drawdown <= 0.0:
            return 0.0
        return float(total_pnl / max_drawdown)

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
            if val >= peak:
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
