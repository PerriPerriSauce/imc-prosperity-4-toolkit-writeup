"""Integration tests for historical CSV ingestion, snapshot building, and deterministic replay."""

from __future__ import annotations

from pathlib import Path

from prosperity_toolkit.backtesting.engine import BacktestEngine
from prosperity_toolkit.backtesting.replay import build_snapshots_from_dataframes
from prosperity_toolkit.cli import main as cli_main
from prosperity_toolkit.core.models import OrderRequest
from prosperity_toolkit.data.loader import DataLoader
from prosperity_toolkit.execution.simulator import ExecutionSimulator
from prosperity_toolkit.market.market_state import MarketStateSnapshot
from prosperity_toolkit.strategies.base import BaseStrategy
from prosperity_toolkit.strategies.baseline import NoOpBaselineStrategy


class _TestProbeStrategy(BaseStrategy):
    """Test-only probe strategy verifying taker fills and PnL tracking during replay."""

    def __init__(self) -> None:
        super().__init__(name="TestProbe")

    def generate_orders(self, state: MarketStateSnapshot) -> list[OrderRequest]:
        book = state.get_book("ASH_COATED_OSMIUM")
        if book is None or book.best_ask is None or book.best_bid is None:
            return []
        if state.timestamp == 0:
            # Buy 1 unit at best_ask (10002)
            return [OrderRequest(symbol="ASH_COATED_OSMIUM", price=book.best_ask, quantity=1)]
        if state.timestamp == 900:
            # Sell 1 unit at best_bid (9998)
            return [OrderRequest(symbol="ASH_COATED_OSMIUM", price=book.best_bid, quantity=-1)]
        return []


def test_deterministic_csv_replay_pipeline() -> None:
    """Verify full CSV -> Snapshot -> BacktestEngine pipeline is deterministic."""
    prices_df = DataLoader.load_prices_csv(
        Path("tests/fixtures/prices_round_1_day_0_sample.csv"),
        check_continuity=True,
    )
    trades_df = DataLoader.load_trades_csv(
        Path("tests/fixtures/trades_round_1_day_0_sample.csv"),
    )

    snapshots = build_snapshots_from_dataframes(prices_df, trades_df)
    assert len(snapshots) == 10
    # Verify negative ask volume convention in reconstructed book
    osmium_book_t0 = snapshots[0].get_book("ASH_COATED_OSMIUM")
    assert osmium_book_t0 is not None
    assert osmium_book_t0.asks[10002] == -10
    assert osmium_book_t0.bids[9998] == 10

    limits = {"ASH_COATED_OSMIUM": 20, "INTARIAN_PEPPER_ROOT": 20}
    engine_a = BacktestEngine(simulator=ExecutionSimulator(position_limits=limits))
    engine_b = BacktestEngine(simulator=ExecutionSimulator(position_limits=limits))

    res_a = engine_a.run(_TestProbeStrategy(), snapshots)
    res_b = engine_b.run(_TestProbeStrategy(), snapshots)

    assert res_a.total_pnl == res_b.total_pnl
    assert res_a.equity_curve == res_b.equity_curve
    assert len(res_a.fills) == 2
    # Bought 1 at 10002, sold 1 at 9998 -> realized PnL = -4.0
    assert res_a.total_pnl == -4.0


def test_cli_replay_and_noop() -> None:
    """Verify CLI replay command executes cleanly on synthetic fixtures."""
    exit_code = cli_main([
        "replay",
        "--prices",
        "tests/fixtures/prices_round_1_day_0_sample.csv",
        "--trades",
        "tests/fixtures/trades_round_1_day_0_sample.csv",
        "--limit",
        "20",
    ])
    assert exit_code == 0

    engine = BacktestEngine()
    noop_res = engine.run(NoOpBaselineStrategy(), [])
    assert noop_res.total_pnl == 0.0
