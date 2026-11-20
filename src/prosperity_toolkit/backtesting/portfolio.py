"""Portfolio state, inventory tracking, cash accounting, and PnL valuation."""

from __future__ import annotations

from prosperity_toolkit.core.models import Cash, Position, Price, Symbol
from prosperity_toolkit.execution.fills import FillEvent


class PortfolioTracker:
    """Tracks cash, inventory, average cost basis, and realized/unrealized PnL."""

    def __init__(self, initial_cash: Cash = 0.0) -> None:
        self.initial_cash: float = float(initial_cash)
        self.cash: Cash = float(initial_cash)
        self.positions: dict[Symbol, Position] = {}
        self._avg_cost: dict[Symbol, float] = {}
        self.realized_pnl: float = 0.0

    def apply_fill(self, fill: FillEvent) -> None:
        """Update cash, position, average cost basis, and realized PnL from a fill."""
        if fill.quantity == 0:
            return
        px = float(fill.price)
        qty = int(fill.quantity)
        fee = float(fill.fee)

        # Cash outflow when buying, inflow when selling: -price * quantity - fee
        self.cash += -(px * qty) - fee
        self.realized_pnl -= fee

        curr_pos = self.positions.get(fill.symbol, 0)
        avg_cost = self._avg_cost.get(fill.symbol, 0.0)
        new_pos = curr_pos + qty

        if curr_pos == 0 or (curr_pos > 0 and qty > 0) or (curr_pos < 0 and qty < 0):
            # Opening or adding to existing side: update weighted average entry cost
            total_abs = abs(curr_pos) + abs(qty)
            self._avg_cost[fill.symbol] = (abs(curr_pos) * avg_cost + abs(qty) * px) / total_abs
        else:
            # Closing part or all of existing position (and possibly flipping sides)
            closed_qty = min(abs(curr_pos), abs(qty))
            if curr_pos > 0:
                self.realized_pnl += closed_qty * (px - avg_cost)
            else:
                self.realized_pnl += closed_qty * (avg_cost - px)

            if new_pos == 0:
                self._avg_cost.pop(fill.symbol, None)
            elif (curr_pos > 0 and new_pos < 0) or (curr_pos < 0 and new_pos > 0):
                self._avg_cost[fill.symbol] = px
            # If partially closed without flipping, avg_cost on remaining lot stays unchanged

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
        """Compute unrealized mark-to-market PnL relative to open position cost basis."""
        total = 0.0
        for sym, pos in self.positions.items():
            if pos == 0:
                continue
            mark = float(mark_prices.get(sym, 0.0))
            cost = self._avg_cost.get(sym, 0.0)
            total += float(pos) * (mark - cost)
        return total
