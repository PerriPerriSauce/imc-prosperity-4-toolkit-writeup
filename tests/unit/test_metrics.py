"""Unit tests for performance metrics and risk calculations."""

from __future__ import annotations

import math

import pytest

from prosperity_toolkit.backtesting.metrics import PerformanceMetrics


def test_sharpe_ratio_zero_volatility() -> None:
    """Sharpe ratio must be zero when returns have zero standard deviation."""
    returns = [1.0, 1.0, 1.0, 1.0]
    sr = PerformanceMetrics.calculate_sharpe_ratio(returns)
    assert sr == 0.0


def test_sharpe_ratio_unscaled_default_and_explicit_scaling() -> None:
    """Default Sharpe is unscaled per-observation IR; explicit factor scales by sqrt."""
    returns = [1.0, 2.0, 1.5, 3.0, 2.5]
    ir = PerformanceMetrics.calculate_sharpe_ratio(returns)
    expected_ir = 2.0 / math.sqrt(0.625)
    assert ir == pytest.approx(expected_ir)

    scaled = PerformanceMetrics.calculate_sharpe_ratio(returns, annualization_factor=10.0)
    assert scaled == pytest.approx(expected_ir * math.sqrt(10.0))

    with pytest.raises(ValueError, match="strictly positive"):
        PerformanceMetrics.calculate_sharpe_ratio(returns, annualization_factor=0.0)


def test_block_sharpe_and_pnl_to_drawdown() -> None:
    """Verify block Sharpe aggregation and PnL-to-MaxDD ratio."""
    returns = [1.0, 1.0, 3.0, 3.0, 2.0, 2.0]  # block sums (size=2): [2.0, 6.0, 4.0]
    bsr = PerformanceMetrics.calculate_block_sharpe(returns, block_size=2)
    assert bsr == pytest.approx(4.0 / 2.0)  # mean=4, std=2
    assert PerformanceMetrics.calculate_pnl_to_drawdown(100.0, 25.0) == pytest.approx(4.0)
    assert PerformanceMetrics.calculate_pnl_to_drawdown(100.0, 0.0) == 0.0


def test_max_drawdown_magnitude_and_flat_or_exact_recovery_duration() -> None:
    """Verify drawdown magnitude, duration reset on exact recovery, and 0 duration when flat."""
    equity = [100.0, 110.0, 105.0, 95.0, 108.0, 120.0]
    max_dd, duration = PerformanceMetrics.calculate_max_drawdown(equity)
    assert max_dd == 15.0
    assert duration == 3

    # Flat equity curve has 0 drawdown and 0 duration
    assert PerformanceMetrics.calculate_max_drawdown([100.0, 100.0, 100.0, 100.0]) == (0.0, 0)

    # Exact peak recovery resets duration cleanly
    exact_rec = [0.0, 10.0, 5.0, 10.0, 10.0]
    assert PerformanceMetrics.calculate_max_drawdown(exact_rec) == (5.0, 1)
