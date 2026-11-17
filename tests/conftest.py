"""Pytest configuration and shared test fixtures."""

from __future__ import annotations

import pytest

from prosperity_toolkit.market.order_book import OrderBookL2


@pytest.fixture
def sample_order_book() -> OrderBookL2:
    """Fixture providing a standard two-sided order book."""
    book = OrderBookL2(symbol="TEST_ASSET")
    # Prosperity convention: bids are positive quantity, asks are negative quantity
    book.set_depth(
        bids={99: 10, 98: 20},
        asks={101: -10, 102: -25},
    )
    return book
