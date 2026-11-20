"""Multi-session Monte Carlo scenario runner and distribution summary."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import TypeAlias

import numpy as np

from prosperity_toolkit.backtesting.engine import BacktestEngine
from prosperity_toolkit.backtesting.results import BacktestResult
from prosperity_toolkit.core.models import Symbol
from prosperity_toolkit.execution.simulator import ExecutionSimulator, FillMode
from prosperity_toolkit.market.market_state import MarketStateSnapshot
from prosperity_toolkit.market.order_flow import TradePrint
from prosperity_toolkit.simulation.processes import (
    OrnsteinUhlenbeckParams,
    RandomWalkParams,
    simulate_ou_paths,
    simulate_random_walk_paths,
)
from prosperity_toolkit.simulation.pulses import TradeArrivalConfig, simulate_trade_arrivals
from prosperity_toolkit.simulation.synthetic_book import (
    BotBookConfig,
    build_counterparty_trade,
    build_synthetic_book,
)
from prosperity_toolkit.strategies.base import BaseStrategy

ProcessParams: TypeAlias = OrnsteinUhlenbeckParams | RandomWalkParams


@dataclass(frozen=True, slots=True)
class AssetScenarioConfig:
    """Complete stochastic configuration for a single simulated asset."""

    symbol: Symbol
    process: ProcessParams
    book: BotBookConfig = BotBookConfig()
    arrivals: TradeArrivalConfig = TradeArrivalConfig()
    position_limit: int = 20


@dataclass(frozen=True, slots=True)
class MonteCarloSummary:
    """Distributional performance and tail-risk summary across Monte Carlo sessions."""

    strategy_name: str
    n_sessions: int
    n_steps: int
    seed: int | None
    pnl_distribution: tuple[float, ...]
    mean_pnl: float
    std_pnl: float
    median_pnl: float
    var_95: float
    cvar_95: float
    prob_loss: float
    mean_sharpe: float
    mean_max_drawdown: float
    worst_max_drawdown: float

    def summary(self) -> dict[str, float | str | int]:
        """Return standardized metric summary dictionary for reporting."""
        return {
            "strategy": self.strategy_name,
            "n_sessions": self.n_sessions,
            "n_steps": self.n_steps,
            "mean_pnl": self.mean_pnl,
            "std_pnl": self.std_pnl,
            "median_pnl": self.median_pnl,
            "var_95": self.var_95,
            "cvar_95": self.cvar_95,
            "prob_loss": self.prob_loss,
            "mean_sharpe": self.mean_sharpe,
            "mean_max_drawdown": self.mean_max_drawdown,
            "worst_max_drawdown": self.worst_max_drawdown,
        }


class MonteCarloEngine:
    """Vectorized stochastic market simulator feeding BacktestEngine sessions."""

    def __init__(
        self,
        assets: Sequence[AssetScenarioConfig],
        conservative_fills: bool = True,
        tick_step: int = 100,
        fill_mode: FillMode | None = None,
        adverse_selection_prob: float = 0.0,
        adverse_jump_size: float = 4.0,
    ) -> None:
        if not assets:
            msg = "MonteCarloEngine requires at least one AssetScenarioConfig"
            raise ValueError(msg)
        if not 0.0 <= adverse_selection_prob <= 1.0:
            msg = f"adverse_selection_prob must be in [0, 1], got {adverse_selection_prob}"
            raise ValueError(msg)
        self.assets = list(assets)
        self.fill_mode: FillMode | None = fill_mode
        self.conservative_fills = conservative_fills
        self.tick_step = tick_step
        self.adverse_selection_prob = adverse_selection_prob
        self.adverse_jump_size = adverse_jump_size

    def run(
        self,
        strategy_factory: Callable[[], BaseStrategy],
        n_sessions: int = 100,
        n_steps: int = 200,
        seed: int | None = 42,
    ) -> MonteCarloSummary:
        """Simulate n_sessions independent market paths and aggregate PnL distributions."""
        if n_sessions <= 0 or n_steps <= 0:
            msg = "n_sessions and n_steps must be strictly positive"
            raise ValueError(msg)

        rng = np.random.default_rng(seed)

        # Pre-generate all FV paths and counterparty arrivals vectorized in NumPy
        fv_paths: dict[Symbol, np.ndarray] = {}
        arrival_mats: dict[Symbol, np.ndarray] = {}
        limits: dict[Symbol, int] = {}

        for asset in self.assets:
            if isinstance(asset.process, OrnsteinUhlenbeckParams):
                fv_paths[asset.symbol] = simulate_ou_paths(
                    asset.process,
                    n_sessions,
                    n_steps,
                    rng,
                )
            else:
                fv_paths[asset.symbol] = simulate_random_walk_paths(
                    asset.process,
                    n_sessions,
                    n_steps,
                    rng,
                )
            arrival_mats[asset.symbol] = simulate_trade_arrivals(
                asset.arrivals,
                n_sessions,
                n_steps,
                rng,
            )
            if self.adverse_selection_prob > 0.0 and n_steps > 1:
                arr = arrival_mats[asset.symbol]
                informed_mask = (arr != 0) & (
                    rng.random((n_sessions, n_steps)) < self.adverse_selection_prob
                )
                jumps = np.where(informed_mask, np.sign(arr) * self.adverse_jump_size, 0.0)
                # Causal informed impact materializes on subsequent ticks (t+1 onward)
                shifted_cum = np.zeros_like(fv_paths[asset.symbol])
                shifted_cum[:, 1:] = np.cumsum(jumps[:, :-1], axis=1)
                fv_paths[asset.symbol] = fv_paths[asset.symbol] + shifted_cum
            limits[asset.symbol] = asset.position_limit

        session_results: list[BacktestResult] = []
        simulator = ExecutionSimulator(
            position_limits=limits,
            conservative_fills=self.conservative_fills,
            fill_mode=self.fill_mode,
        )
        engine = BacktestEngine(simulator=simulator)

        for s_idx in range(n_sessions):
            snapshots: list[MarketStateSnapshot] = []
            for t_idx in range(n_steps):
                ts = t_idx * self.tick_step
                books = {}
                trades: dict[Symbol, list[TradePrint]] = {}
                for asset in self.assets:
                    sym = asset.symbol
                    fv = float(fv_paths[sym][s_idx, t_idx])
                    book = build_synthetic_book(sym, fv, asset.book)
                    books[sym] = book

                    arr_qty = int(arrival_mats[sym][s_idx, t_idx])
                    tp = build_counterparty_trade(ts, sym, book, arr_qty)
                    if tp is not None:
                        trades[sym] = [tp]

                snapshots.append(
                    MarketStateSnapshot(
                        timestamp=ts,
                        books=books,
                        market_trades=trades,
                    ),
                )

            strategy = strategy_factory()
            session_results.append(engine.run(strategy, snapshots))

        pnls = np.array([r.total_pnl for r in session_results], dtype=np.float64)
        sharpes = np.array([r.sharpe_ratio for r in session_results], dtype=np.float64)
        drawdowns = np.array([r.max_drawdown for r in session_results], dtype=np.float64)

        var_95 = float(np.percentile(pnls, 5.0))
        tail_mask = pnls <= var_95
        cvar_95 = float(np.mean(pnls[tail_mask])) if np.any(tail_mask) else var_95

        return MonteCarloSummary(
            strategy_name=session_results[0].strategy_name,
            n_sessions=n_sessions,
            n_steps=n_steps,
            seed=seed,
            pnl_distribution=tuple(float(x) for x in pnls),
            mean_pnl=float(np.mean(pnls)),
            std_pnl=float(np.std(pnls, ddof=1)) if n_sessions > 1 else 0.0,
            median_pnl=float(np.median(pnls)),
            var_95=var_95,
            cvar_95=cvar_95,
            prob_loss=float(np.mean(pnls < 0.0)),
            mean_sharpe=float(np.mean(sharpes)),
            mean_max_drawdown=float(np.mean(drawdowns)),
            worst_max_drawdown=float(np.max(drawdowns)),
        )
