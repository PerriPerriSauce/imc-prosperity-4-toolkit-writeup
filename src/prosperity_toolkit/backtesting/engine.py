"""Main backtesting engine coordinator."""

from __future__ import annotations

from collections.abc import Sequence

from prosperity_toolkit.backtesting.metrics import PerformanceMetrics
from prosperity_toolkit.backtesting.portfolio import PortfolioTracker
from prosperity_toolkit.backtesting.replay import HistoricalReplayLoop
from prosperity_toolkit.backtesting.results import BacktestResult
from prosperity_toolkit.core.models import Symbol
from prosperity_toolkit.execution.fills import FillEvent
from prosperity_toolkit.execution.simulator import ExecutionSimulator
from prosperity_toolkit.market.market_state import MarketStateSnapshot
from prosperity_toolkit.market.order_flow import TradePrint
from prosperity_toolkit.strategies.base import BaseStrategy


class BacktestEngine:
    """Orchestrates end-to-end backtesting replay sessions."""

    def __init__(
        self,
        simulator: ExecutionSimulator | None = None,
        reject_on_limit_breach: bool = True,
        initial_cash: float = 0.0,
    ) -> None:
        self.simulator = simulator or ExecutionSimulator()
        self.replay_loop = HistoricalReplayLoop(
            self.simulator,
            reject_on_limit_breach=reject_on_limit_breach,
        )
        self.initial_cash = initial_cash
        self.portfolio = PortfolioTracker(initial_cash=initial_cash)

    def run(
        self,
        strategy: BaseStrategy,
        snapshots: Sequence[MarketStateSnapshot],
    ) -> BacktestResult:
        """Run strategy against provided sequence of market snapshots without mutating inputs."""
        self.portfolio = PortfolioTracker(initial_cash=self.initial_cash)
        all_fills: list[FillEvent] = []
        equity_curve: list[float] = []
        last_marks: dict[str, float] = {}
        prev_market_trades: dict[Symbol, list[TradePrint]] = {}
        prev_own_trades: dict[Symbol, list[TradePrint]] = {}

        for snap in snapshots:
            strategy.update_positions(self.portfolio.positions)

            _, _, fills = self.replay_loop.step(
                strategy,
                snap,
                positions=self.portfolio.positions,
                prior_market_trades=prev_market_trades,
                prior_own_trades=prev_own_trades,
            )
            curr_own_trades: dict[Symbol, list[TradePrint]] = {}
            for fill in fills:
                self.portfolio.apply_fill(fill)
                all_fills.append(fill)
                tp = TradePrint(
                    timestamp=fill.timestamp,
                    symbol=fill.symbol,
                    price=int(fill.price),
                    quantity=abs(fill.quantity),
                    buyer="SUBMISSION" if fill.quantity > 0 else "",
                    seller="SUBMISSION" if fill.quantity < 0 else "",
                )
                curr_own_trades.setdefault(fill.symbol, []).append(tp)

            prev_market_trades = snap.market_trades
            prev_own_trades = curr_own_trades

            for sym, book in snap.books.items():
                if book.mid_price is not None:
                    last_marks[sym] = book.mid_price
                elif sym not in last_marks:
                    if book.best_bid is not None:
                        last_marks[sym] = float(book.best_bid)
                    elif book.best_ask is not None:
                        last_marks[sym] = float(book.best_ask)
                    else:
                        last_marks[sym] = 0.0
            equity_curve.append(self.portfolio.total_valuation(last_marks))

        final_pnl = (equity_curve[-1] - self.initial_cash) if equity_curve else 0.0
        max_dd, max_dd_duration = PerformanceMetrics.calculate_max_drawdown(equity_curve)

        returns = [
            equity_curve[i] - equity_curve[i - 1]
            for i in range(1, len(equity_curve))
        ]
        # Store dimensionally valid unscaled per-tick information ratio
        sharpe = PerformanceMetrics.calculate_sharpe_ratio(returns, annualization_factor=1.0)

        return BacktestResult(
            strategy_name=strategy.name,
            total_pnl=final_pnl,
            max_drawdown=max_dd,
            max_drawdown_duration=max_dd_duration,
            sharpe_ratio=sharpe,
            equity_curve=equity_curve,
            fills=all_fills,
        )
