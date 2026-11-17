"""Historical replay loop feeding tick-by-tick state into strategies."""

from __future__ import annotations

from prosperity_toolkit.core.models import OrderRequest, Timestamp
from prosperity_toolkit.execution.fills import FillEvent
from prosperity_toolkit.execution.simulator import ExecutionSimulator
from prosperity_toolkit.market.market_state import MarketStateSnapshot
from prosperity_toolkit.strategies.base import BaseStrategy


class HistoricalReplayLoop:
    """Manages sequential feed of historical market states."""

    def __init__(self, simulator: ExecutionSimulator) -> None:
        self.simulator = simulator

    def step(
        self,
        strategy: BaseStrategy,
        state: MarketStateSnapshot,
    ) -> tuple[Timestamp, list[OrderRequest], list[FillEvent]]:
        """Execute a single timestamp step in the replay."""
        orders = strategy.generate_orders(state)
        fills: list[FillEvent] = []

        # Validate order requests against positions
        for symbol, book in state.books.items():
            sym_orders = [o for o in orders if o.symbol == symbol]
            if sym_orders:
                curr_pos = state.get_position(symbol)
                limit = self.simulator.position_limits.get(symbol, 1000)
                self.simulator.validate_orders_against_limits(curr_pos, sym_orders, limit)
                sym_fills = self.simulator.match_taker_orders(state.timestamp, book, sym_orders)
                fills.extend(sym_fills)

        return state.timestamp, orders, fills
