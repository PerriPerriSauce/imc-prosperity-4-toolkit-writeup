"""Level 2 Order Book representation supporting price ladders and depth queries."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from prosperity_toolkit.core.models import Price, Quantity, Symbol


@dataclass
class OrderBookL2:
    """Represents the multi-level order book for a single instrument."""

    symbol: Symbol
    bids: dict[Price, Quantity] = field(default_factory=dict)
    asks: dict[Price, Quantity] = field(default_factory=dict)

    def set_depth(
        self,
        bids: Mapping[Price, Quantity],
        asks: Mapping[Price, Quantity],
    ) -> None:
        """Update full book depth.

        Note: In Prosperity conventions, ask quantities may be stored as negative numbers.
        This container preserves exact signed quantities while providing absolute depth helpers.
        """
        self.bids = dict(bids)
        self.asks = dict(asks)

    @property
    def best_bid(self) -> Price | None:
        """Highest active buy price."""
        return max(self.bids.keys()) if self.bids else None

    @property
    def best_ask(self) -> Price | None:
        """Lowest active sell price."""
        return min(self.asks.keys()) if self.asks else None

    @property
    def spread(self) -> int | None:
        """Bid-ask spread in ticks/integer units."""
        if self.best_bid is not None and self.best_ask is not None:
            return int(self.best_ask - self.best_bid)
        return None

    @property
    def mid_price(self) -> float | None:
        """Midpoint of top-of-book prices."""
        if self.best_bid is not None and self.best_ask is not None:
            return float((self.best_bid + self.best_ask) / 2.0)
        return None

    @property
    def weighted_mid_price(self) -> float | None:
        """Volume-weighted mid price (microprice) at top of book."""
        bb = self.best_bid
        ba = self.best_ask
        if bb is None or ba is None:
            return None

        bid_vol = abs(self.bids[bb])
        ask_vol = abs(self.asks[ba])
        total_vol = bid_vol + ask_vol
        if total_vol == 0:
            return float((bb + ba) / 2.0)

        return float((bb * ask_vol + ba * bid_vol) / total_vol)
