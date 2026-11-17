"""Unit tests for Level 2 order book operations."""

from __future__ import annotations

from prosperity_toolkit.market.order_book import OrderBookL2


def test_order_book_bids_asks(sample_order_book: OrderBookL2) -> None:
    """Verify top of book extraction and spread calculation."""
    assert sample_order_book.best_bid == 99
    assert sample_order_book.best_ask == 101
    assert sample_order_book.spread == 2
    assert sample_order_book.mid_price == 100.0


def test_order_book_empty() -> None:
    """Verify behavior of empty order book."""
    empty_book = OrderBookL2(symbol="EMPTY")
    assert empty_book.best_bid is None
    assert empty_book.best_ask is None
    assert empty_book.spread is None
    assert empty_book.mid_price is None
    assert empty_book.weighted_mid_price is None


def test_volume_weighted_mid(sample_order_book: OrderBookL2) -> None:
    """Verify microprice volume weighting."""
    # bids={99: 10}, asks={101: -10} -> equal volumes (10, 10) -> microprice = 100.0
    w_mid = sample_order_book.weighted_mid_price
    assert w_mid is not None
    assert round(w_mid, 2) == 100.0
