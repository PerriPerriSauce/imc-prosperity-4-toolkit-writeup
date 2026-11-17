"""Integration smoke test for basic backtesting loop."""

from __future__ import annotations

from prosperity_toolkit.backtesting.engine import BacktestEngine
from prosperity_toolkit.market.market_state import MarketStateSnapshot
from prosperity_toolkit.market.order_book import OrderBookL2
from prosperity_toolkit.strategies.baseline import NoOpBaselineStrategy


def test_end_to_end_noop_backtest() -> None:
    """Verify that BacktestEngine can run a NoOp baseline through synthetic snapshots."""
    book = OrderBookL2(symbol="TEST_ASSET")
    book.set_depth(bids={100: 5}, asks={102: -5})

    snap1 = MarketStateSnapshot(timestamp=0, books={"TEST_ASSET": book})
    snap2 = MarketStateSnapshot(timestamp=100, books={"TEST_ASSET": book})

    engine = BacktestEngine()
    strategy = NoOpBaselineStrategy()
    result = engine.run(strategy, snapshots=[snap1, snap2])

    assert result.strategy_name == "NoOpBaseline"
    assert result.total_pnl == 0.0
    assert len(result.fills) == 0
