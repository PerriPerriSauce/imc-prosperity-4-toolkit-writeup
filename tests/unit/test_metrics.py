"""Unit tests for performance metrics and risk calculations."""

from __future__ import annotations

from prosperity_toolkit.backtesting.metrics import PerformanceMetrics


def test_sharpe_ratio_zero_volatility() -> None:
    """Sharpe ratio must be zero when returns have zero standard deviation."""
    returns = [1.0, 1.0, 1.0, 1.0]
    sr = PerformanceMetrics.calculate_sharpe_ratio(returns)
    assert sr == 0.0


def test_sharpe_ratio_positive() -> None:
    """Sharpe ratio should be positive for positive mean returns."""
    returns = [1.0, 2.0, 1.5, 3.0, 2.5]
    sr = PerformanceMetrics.calculate_sharpe_ratio(returns)
    assert sr > 0.0


def test_max_drawdown() -> None:
    """Verify drawdown magnitude and duration calculation."""
    equity = [100.0, 110.0, 105.0, 95.0, 108.0, 120.0]
    # Peak is 110.0, lowest point is 95.0 -> drawdown magnitude is 15.0
    # Time spent below 110.0 before recovering at 120.0 is 3 ticks (105.0, 95.0, 108.0)
    max_dd, duration = PerformanceMetrics.calculate_max_drawdown(equity)
    assert max_dd == 15.0
    assert duration == 3
