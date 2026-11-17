"""Data structures encapsulating comprehensive backtest results."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from prosperity_toolkit.execution.fills import FillEvent


@dataclass(frozen=True, slots=True)
class BacktestResult:
    """Summary record of a completed backtest execution."""

    strategy_name: str
    total_pnl: float
    max_drawdown: float
    max_drawdown_duration: int
    sharpe_ratio: float
    equity_curve: Sequence[float] = field(default_factory=tuple)
    fills: Sequence[FillEvent] = field(default_factory=tuple)

    def summary(self) -> dict[str, float | str | int]:
        """Return standardized metric summary dictionary."""
        return {
            "strategy": self.strategy_name,
            "total_pnl": self.total_pnl,
            "max_drawdown": self.max_drawdown,
            "max_drawdown_duration": self.max_drawdown_duration,
            "sharpe_ratio": self.sharpe_ratio,
            "total_trades": len(self.fills),
        }
