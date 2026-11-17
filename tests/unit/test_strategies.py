"""Unit tests for baseline and candidate trading strategies."""

from __future__ import annotations

from prosperity_toolkit.execution.simulator import ExecutionSimulator
from prosperity_toolkit.market.market_state import MarketStateSnapshot
from prosperity_toolkit.market.order_book import OrderBookL2
from prosperity_toolkit.strategies import (
    DriftAwareConfig,
    DriftAwareQuoter,
    InventorySkewedMarketMaker,
    MarketMakingConfig,
    OUMeanReversionConfig,
    OUMeanReversionStrategy,
    SymmetricMarketMaker,
)


def test_strategies_handle_empty_and_one_sided_books() -> None:
    """All strategies must handle empty and one-sided books without raising."""
    empty_book = OrderBookL2(symbol="OSMIUM")
    bid_only = OrderBookL2(symbol="OSMIUM")
    bid_only.set_depth(bids={9995: 10}, asks={})

    snap_empty = MarketStateSnapshot(timestamp=0, books={"OSMIUM": empty_book})
    snap_one_sided = MarketStateSnapshot(timestamp=100, books={"OSMIUM": bid_only})

    mm_cfg = [MarketMakingConfig(symbol="OSMIUM", position_limit=20)]
    ou_cfg = [OUMeanReversionConfig(symbol="OSMIUM", position_limit=20)]
    drift_cfg = [DriftAwareConfig(symbol="OSMIUM", position_limit=20)]

    for strat in [
        SymmetricMarketMaker(mm_cfg),
        InventorySkewedMarketMaker(mm_cfg),
        OUMeanReversionStrategy(ou_cfg),
        DriftAwareQuoter(drift_cfg),
    ]:
        assert strat.generate_orders(snap_empty) == []
        assert strat.generate_orders(snap_one_sided) == []


def test_inventory_skewed_respects_starting_position_with_takers() -> None:
    """Combined taker + passive orders must never exceed starting-position limits."""
    sim = ExecutionSimulator(position_limits={"OSMIUM": 10})
    cfg = [
        MarketMakingConfig(
            symbol="OSMIUM",
            position_limit=10,
            anchor_fv=10000.0,
            anchor_weight=1.0,
        ),
    ]
    strat = InventorySkewedMarketMaker(cfg)

    # Start at +6, cheap ask at 9998 (take_edge=1.0 vs 10000.0) with size 8 -> can take at most 4
    book = OrderBookL2(symbol="OSMIUM")
    book.set_depth(bids={9994: 10}, asks={9998: -8, 10004: -10})
    snap = MarketStateSnapshot(timestamp=0, books={"OSMIUM": book}, positions={"OSMIUM": 6})

    orders = strat.generate_orders(snap)
    # Must NOT raise PositionLimitExceededError
    sim.validate_orders_against_limits(starting_pos=6, orders=orders, limit=10)

    total_buys = sum(o.quantity for o in orders if o.quantity > 0)
    total_sells = sum(o.quantity for o in orders if o.quantity < 0)
    assert 6 + total_buys <= 10
    assert 6 + total_sells >= -10


def test_ou_mean_reversion_triggers_at_z_threshold() -> None:
    """OUMeanReversionStrategy enters only when bid/ask breaches entry_z * sigma."""
    cfg = [OUMeanReversionConfig(symbol="OSMIUM", mu=10000.0, sigma=4.0, entry_z=1.5, order_size=3)]
    strat = OUMeanReversionStrategy(cfg)  # threshold = 6.0 -> buy <= 9994, sell >= 10006

    neutral = OrderBookL2(symbol="OSMIUM")
    neutral.set_depth(bids={9995: 5}, asks={10005: -5})
    assert strat.generate_orders(MarketStateSnapshot(timestamp=0, books={"OSMIUM": neutral})) == []

    cheap = OrderBookL2(symbol="OSMIUM")
    cheap.set_depth(bids={9990: 5}, asks={9994: -2})
    orders = strat.generate_orders(MarketStateSnapshot(timestamp=100, books={"OSMIUM": cheap}))
    assert len(orders) == 1
    assert orders[0].price == 9994
    assert orders[0].quantity == 2
