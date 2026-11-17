"""Portfolio state, inventory tracking, cash accounting, and PnL valuation."""

from __future__ import annotations

from prosperity_toolkit.core.models import Cash, Position, Price, Symbol
from prosperity_toolkit.execution.fills import FillEvent


class PortfolioTracker:
    """Tracks cash balances, inventory positions, and computes realized/unrealized PnL."""

    def __init__(self, initial_cash: Cash = 0.0) -> None:
        self.cash: Cash = initial_cash
        self.positions: dict[Symbol, Position] = {}
        self.realized_pnl: float = 0.0

    def apply_fill(self, fill: FillEvent) -> None:
        """Update cash and position based on matched trade fill."""
        # Cash outflow when buying, inflow when selling: - price * quantity
        trade_cash_flow = -(fill.price * fill.quantity) - fill.fee
        self.cash += trade_cash_flow

        curr_pos = self.positions.get(fill.symbol, 0)
        new_pos = curr_pos + fill.quantity
        self.positions[fill.symbol] = new_pos

    def get_position(self, symbol: Symbol) -> Position:
        """Get inventory for symbol."""
        return self.positions.get(symbol, 0)

    def total_valuation(self, mark_prices: dict[Symbol, Price | float]) -> float:
        """Compute net liquidation value (cash + marked inventory)."""
        inventory_val = float(sum(
            pos * mark_prices.get(sym, 0.0)
            for sym, pos in self.positions.items()
        ))
        return float(self.cash + inventory_val)

    def unrealized_pnl(self, mark_prices: dict[Symbol, Price | float]) -> float:
        """Compute unrealized PnL based on current marks."""
        # For zero-cost basis initialization, net PnL is cash + mark value
        return self.total_valuation(mark_prices)
