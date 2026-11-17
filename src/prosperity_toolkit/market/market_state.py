"""Immutable state snapshot representation across all traded instruments."""

from __future__ import annotations

from dataclasses import dataclass, field

from prosperity_toolkit.core.models import Position, Symbol, Timestamp
from prosperity_toolkit.market.order_book import OrderBookL2


@dataclass
class MarketStateSnapshot:
    """Internal consolidated state snapshot at timestamp t."""

    timestamp: Timestamp
    books: dict[Symbol, OrderBookL2] = field(default_factory=dict)
    positions: dict[Symbol, Position] = field(default_factory=dict)
    trader_data: str = ""

    def get_position(self, symbol: Symbol) -> Position:
        """Query inventory position for given symbol, defaulting to zero."""
        return self.positions.get(symbol, 0)

    def get_book(self, symbol: Symbol) -> OrderBookL2 | None:
        """Query order book for given symbol."""
        return self.books.get(symbol)
