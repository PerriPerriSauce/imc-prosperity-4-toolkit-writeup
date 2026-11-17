"""Adapter converting internal toolkit models to official competition TradingState."""

from __future__ import annotations

from collections.abc import Mapping

from prosperity_toolkit.competition.datamodel import (
    Listing,
    Observation,
    OrderDepth,
    Trade,
    TradingState,
)
from prosperity_toolkit.market.market_state import MarketStateSnapshot


class CompetitionStateAdapter:
    """Bridges internal toolkit MarketStateSnapshot to competition TradingState."""

    @staticmethod
    def to_trading_state(
        snapshot: MarketStateSnapshot,
        listings: Mapping[str, Listing] | None = None,
        own_trades: Mapping[str, list[Trade]] | None = None,
        market_trades: Mapping[str, list[Trade]] | None = None,
        observations: Observation | None = None,
    ) -> TradingState:
        """Convert internal snapshot to authoritative TradingState."""
        order_depths: dict[str, OrderDepth] = {}
        for sym, book in snapshot.books.items():
            depth = OrderDepth()
            depth.buy_orders = dict(book.bids)
            depth.sell_orders = dict(book.asks)
            order_depths[sym] = depth

        return TradingState(
            traderData=snapshot.trader_data,
            timestamp=snapshot.timestamp,
            listings=listings or {},
            order_depths=order_depths,
            own_trades=own_trades or {},
            market_trades=market_trades or {},
            position=snapshot.positions,
            observations=observations or Observation(),
        )
