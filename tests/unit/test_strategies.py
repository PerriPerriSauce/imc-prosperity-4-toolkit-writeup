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
    OptionStrikeSpec,
    OptionsVolatilityConfig,
    OptionsVolatilityStrategy,
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


def test_bachelier_options_strategy_uses_spot_take_edge() -> None:
    """Bachelier pricing and spot_take_edge should gate spot sweeps properly."""
    cfg = OptionsVolatilityConfig(
        spot_symbol="SPOT",
        spot_limit=50,
        pricing_model="bachelier",
        base_vol=1.5,
        spot_take_edge=3.0,
        hedge_band=100.0,
        strikes=(
            OptionStrikeSpec("OPT_5200", 5200.0, position_limit=100, take_edge=2.0),
            OptionStrikeSpec("OPT_5300", 5300.0, position_limit=100, take_edge=2.0),
        ),
    )
    strat = OptionsVolatilityStrategy(cfg)

    spot_book = OrderBookL2(symbol="SPOT")
    spot_book.set_depth(bids={5240: 5, 5230: 50}, asks={5260: -5, 5270: -50})
    opt1 = OrderBookL2(symbol="OPT_5200")
    opt1.set_depth(bids={60: 20}, asks={66: -20})
    opt2 = OrderBookL2(symbol="OPT_5300")
    opt2.set_depth(bids={8: 20}, asks={14: -20})

    # Warm EMA on fair snapshot
    snap0 = MarketStateSnapshot(
        timestamp=0,
        books={"SPOT": spot_book, "OPT_5200": opt1, "OPT_5300": opt2},
    )
    orders0 = strat.generate_orders(snap0)
    assert all(isinstance(o.quantity, int) and o.quantity != 0 for o in orders0)

    # Dislocation inside spot_take_edge=3.0 (ask=5248 vs fv~5250, gap=2 < 3) must not sweep
    spot_cheap = OrderBookL2(symbol="SPOT")
    spot_cheap.set_depth(bids={5240: 20}, asks={5248: -5, 5260: -20})
    snap1 = MarketStateSnapshot(
        timestamp=100,
        books={"SPOT": spot_cheap, "OPT_5200": opt1, "OPT_5300": opt2},
    )
    orders1 = strat.generate_orders(snap1)
    spot_buys_crossing_5248 = [
        o for o in orders1 if o.symbol == "SPOT" and o.quantity > 0 and o.price >= 5248
    ]
    assert not spot_buys_crossing_5248

