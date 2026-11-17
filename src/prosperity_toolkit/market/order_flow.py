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
        """Compute signed net buy vs sell volume over recorded window."""
        symbol_trades = [t for t in self._trades if t.symbol == symbol]
        # In trade reports, buyer/seller identification helps assess buyer-initiated flow
        return sum(t.quantity for t in symbol_trades)

    @property
    def trades(self) -> Sequence[TradePrint]:
        """Read-only view of recorded trades."""
        return tuple(self._trades)
