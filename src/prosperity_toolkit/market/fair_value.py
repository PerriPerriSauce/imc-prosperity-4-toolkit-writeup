"""Fair value estimation models."""

from __future__ import annotations

from typing import Protocol

from prosperity_toolkit.market.order_book import OrderBookL2


class FairValueEstimator(Protocol):
    """Protocol for estimators computing unobserved fair value (FV)."""

    def estimate_fair_value(self, book: OrderBookL2) -> float:
        """Estimate underlying fair price given current book state."""
        ...


class MicropriceFairValue:
    """Estimates fair value via order-book imbalance-weighted top-of-book prices."""

    def estimate_fair_value(self, book: OrderBookL2) -> float:
        """Compute microprice or fallback to mid-price."""
        val = book.weighted_mid_price
        if val is not None:
            return float(val)
        mid = book.mid_price
        if mid is not None:
            return float(mid)
        return 0.0
