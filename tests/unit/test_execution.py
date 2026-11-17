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
