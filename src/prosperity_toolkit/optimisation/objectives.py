"""Optimization objective functions."""

from __future__ import annotations

from typing import Protocol

from prosperity_toolkit.backtesting.results import BacktestResult


class OptimizationObjective(Protocol):
    """Protocol for scoring backtest outcomes during parameter search."""

    def evaluate(self, result: BacktestResult) -> float:
        """Return scalar objective value to maximize."""
        ...


class TotalPnLObjective:
    """Objective evaluating raw total profit and loss."""

    def evaluate(self, result: BacktestResult) -> float:
        return float(result.total_pnl)


class SharpeObjective:
    """Objective evaluating risk-adjusted Sharpe ratio."""

    def evaluate(self, result: BacktestResult) -> float:
        return float(result.sharpe_ratio)
