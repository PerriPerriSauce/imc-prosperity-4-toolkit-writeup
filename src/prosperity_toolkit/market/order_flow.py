"""Order flow tracking, trade imbalance, and microstructure analytics."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from prosperity_toolkit.core.models import Quantity, Symbol, Timestamp


@dataclass(frozen=True, slots=True)
class TradePrint:
    """Historical trade occurrence."""

    timestamp: Timestamp
    symbol: Symbol
    price: int
    quantity: Quantity
    buyer: str
    seller: str


class OrderFlowTracker:
    """Tracks rolling order flow, trade imbalances, and transaction frequencies."""

    def __init__(self, window_size: int = 50) -> None:
        self.window_size = window_size
        self._trades: list[TradePrint] = []

    def record_trade(self, trade: TradePrint) -> None:
        """Append trade print to rolling history."""
        self._trades.append(trade)
        if len(self._trades) > self.window_size:
            self._trades.pop(0)

    def net_volume_imbalance(self, symbol: Symbol) -> int:
        """Compute signed net buy vs sell volume over the recorded window.

        Supports explicitly signed `quantity` (positive buy, negative sell) as
        well as unsigned positive prints tagged asymmetrically on `buyer` vs `seller`.
        Returns 0 for unsigned prints where neither side identifies an aggressor.
        """
        imbalance = 0
        for trade in self._trades:
            if trade.symbol != symbol:
                continue
            if trade.quantity < 0:
                imbalance += trade.quantity
            elif trade.buyer and not trade.seller:
                imbalance += trade.quantity
            elif trade.seller and not trade.buyer:
                imbalance -= trade.quantity
        return imbalance

    @property
    def trades(self) -> Sequence[TradePrint]:
        """Read-only view of recorded trades."""
        return tuple(self._trades)
