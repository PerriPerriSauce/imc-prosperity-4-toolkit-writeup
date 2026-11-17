"""Unit tests for order matching, partial fills, and position limit enforcement."""

from __future__ import annotations

import pytest

from prosperity_toolkit.core.exceptions import PositionLimitExceededError
from prosperity_toolkit.core.models import OrderRequest
from prosperity_toolkit.execution.fills import FillType
from prosperity_toolkit.execution.simulator import ExecutionSimulator
from prosperity_toolkit.market.order_book import OrderBookL2
from prosperity_toolkit.market.order_flow import TradePrint


def test_multi_level_taker_buy_partial_fill(sample_order_book: OrderBookL2) -> None:
    """Aggressive buy crossing multiple ask levels fills sequentially and leaves remainder."""
    # sample_order_book asks: {101: -10, 102: -25}
    sim = ExecutionSimulator()
    orders = [OrderRequest(symbol="TEST_ASSET", price=102, quantity=40)]

    fills, resting = sim.match_taker_with_remainder(0, sample_order_book, orders)

    assert len(fills) == 2
    assert fills[0].price == 101 and fills[0].quantity == 10
    assert fills[1].price == 102 and fills[1].quantity == 25
    assert fills[0].fill_type == FillType.TAKER

    assert len(resting) == 1
    assert resting[0].price == 102 and resting[0].quantity == 5


def test_no_double_consumption_within_same_tick(sample_order_book: OrderBookL2) -> None:
    """Multiple orders on the same tick cannot double-consume the same liquidity."""
    sim = ExecutionSimulator()
    orders = [
        OrderRequest(symbol="TEST_ASSET", price=101, quantity=8),
        OrderRequest(symbol="TEST_ASSET", price=101, quantity=8),
    ]

    fills, resting = sim.match_taker_with_remainder(0, sample_order_book, orders)

    total_filled = sum(f.quantity for f in fills)
    assert total_filled == 10
    assert len(resting) == 1
    assert resting[0].quantity == 6


def test_empty_order_book_leaves_all_resting() -> None:
    """Orders submitted against an empty book produce zero taker fills."""
    empty_book = OrderBookL2(symbol="TEST_ASSET")
    sim = ExecutionSimulator()
    orders = [OrderRequest(symbol="TEST_ASSET", price=100, quantity=5)]

    fills, resting = sim.match_taker_with_remainder(0, empty_book, orders)

    assert fills == []
    assert len(resting) == 1
    assert resting[0].quantity == 5


def test_position_limit_worst_case_starting_inventory() -> None:
    """Aggregate buys + starting_pos exceeding limit must raise PositionLimitExceededError."""
    sim = ExecutionSimulator(position_limits={"TEST_ASSET": 20})
    orders = [
        OrderRequest(symbol="TEST_ASSET", price=100, quantity=5),
        OrderRequest(symbol="TEST_ASSET", price=99, quantity=4),
    ]
    # Starting pos 12 + total buys 9 = 21 > 20
    with pytest.raises(PositionLimitExceededError, match="Worst-case long"):
        sim.validate_orders_against_limits(starting_pos=12, orders=orders, limit=20)

    # Starting pos -15 + total sells -6 = -21 < -20
    sell_orders = [OrderRequest(symbol="TEST_ASSET", price=100, quantity=-6)]
    with pytest.raises(PositionLimitExceededError, match="Worst-case short"):
        sim.validate_orders_against_limits(starting_pos=-15, orders=sell_orders, limit=20)


def test_maker_matching_conservative_vs_touch() -> None:
    """Conservative maker fills require trade strictly through limit price; touch allows equal."""
    resting = [OrderRequest(symbol="TEST_ASSET", price=100, quantity=5)]
    trades = [
        TradePrint(timestamp=100, symbol="TEST_ASSET", price=100, quantity=10, buyer="", seller=""),
    ]

    conservative_sim = ExecutionSimulator(conservative_fills=True)
    assert conservative_sim.match_maker_orders(100, resting, trades) == []

    touch_sim = ExecutionSimulator(conservative_fills=False)
    fills = touch_sim.match_maker_orders(100, resting, trades)
    assert len(fills) == 1
    assert fills[0].price == 100
    assert fills[0].quantity == 5
    assert fills[0].fill_type == FillType.MAKER


def test_maker_matching_queue_aware(sample_order_book: OrderBookL2) -> None:
    """Queue-aware maker fills must respect resting book volume ahead at the touch."""
    # sample_order_book has bids={99: 10, 98: 20} -> queue ahead at 99 is 10
    qa_sim = ExecutionSimulator(fill_mode="queue_aware")

    # Joining best_bid=99 with trade size 6 <= queue_ahead (10) -> 0 fills
    resting_join = [OrderRequest(symbol="TEST_ASSET", price=99, quantity=5)]
    small_trade = [
        TradePrint(timestamp=100, symbol="TEST_ASSET", price=99, quantity=6, buyer="", seller=""),
    ]
    assert qa_sim.match_maker_orders(100, resting_join, small_trade, book=sample_order_book) == []

    # Trade size 13 > queue_ahead (10) -> remaining fillable volume is 3
    large_trade = [
        TradePrint(timestamp=100, symbol="TEST_ASSET", price=99, quantity=13, buyer="", seller=""),
    ]
    fills = qa_sim.match_maker_orders(100, resting_join, large_trade, book=sample_order_book)
    assert len(fills) == 1
    assert fills[0].quantity == 3

    # Penny-improving at 100 has queue_ahead = 0 -> fills full 5 on trade of 5 at 100
    resting_improve = [OrderRequest(symbol="TEST_ASSET", price=100, quantity=5)]
    improve_trade = [
        TradePrint(timestamp=100, symbol="TEST_ASSET", price=100, quantity=5, buyer="", seller=""),
    ]
    improve_fills = qa_sim.match_maker_orders(
        100,
        resting_improve,
        improve_trade,
        book=sample_order_book,
    )
    assert len(improve_fills) == 1
    assert improve_fills[0].quantity == 5
