"""Historical replay loop and snapshot reconstruction from market data."""

from __future__ import annotations

import pandas as pd

from prosperity_toolkit.core.exceptions import PositionLimitExceededError
from prosperity_toolkit.core.models import OrderRequest, Timestamp
from prosperity_toolkit.execution.fills import FillEvent
from prosperity_toolkit.execution.simulator import ExecutionSimulator
from prosperity_toolkit.market.market_state import MarketStateSnapshot
from prosperity_toolkit.market.order_book import OrderBookL2
from prosperity_toolkit.market.order_flow import TradePrint
from prosperity_toolkit.strategies.base import BaseStrategy


def _extract_book(row: pd.Series[object], symbol: str) -> OrderBookL2:
    """Construct an OrderBookL2 from a single normalized price DataFrame row."""
    bids: dict[int, int] = {}
    asks: dict[int, int] = {}

    for lvl in (1, 2, 3):
        bp = row.get(f"bid_price_{lvl}")
        bv = row.get(f"bid_volume_{lvl}")
        if pd.notna(bp) and pd.notna(bv):
            bids[int(bp)] = int(bv)

        ap = row.get(f"ask_price_{lvl}")
        av = row.get(f"ask_volume_{lvl}")
        if pd.notna(ap) and pd.notna(av):
            # Prosperity convention: sell_orders quantities are negative
            asks[int(ap)] = -abs(int(av))

    book = OrderBookL2(symbol=symbol)
    book.set_depth(bids=bids, asks=asks)
    return book


def build_snapshots_from_dataframes(
    prices_df: pd.DataFrame,
    trades_df: pd.DataFrame | None = None,
) -> list[MarketStateSnapshot]:
    """Convert validated price and trade DataFrames into chronological MarketStateSnapshots."""
    if prices_df.empty:
        return []

    trades_by_ts: dict[int, dict[str, list[TradePrint]]] = {}
    if trades_df is not None and not trades_df.empty:
        for _, trow in trades_df.iterrows():
            ts = int(trow["timestamp"])
            sym = str(trow["symbol"])
            tp = TradePrint(
                timestamp=ts,
                symbol=sym,
                price=int(trow["price"]),
                quantity=int(trow["quantity"]),
                buyer=str(trow["buyer"]) if pd.notna(trow.get("buyer")) else "",
                seller=str(trow["seller"]) if pd.notna(trow.get("seller")) else "",
            )
            trades_by_ts.setdefault(ts, {}).setdefault(sym, []).append(tp)

    snapshots: list[MarketStateSnapshot] = []
    for ts_key, group in prices_df.groupby("timestamp", sort=True):
        ts = int(ts_key)
        books: dict[str, OrderBookL2] = {}
        for _, row in group.iterrows():
            sym = str(row["product"])
            books[sym] = _extract_book(row, sym)

        snapshots.append(
            MarketStateSnapshot(
                timestamp=ts,
                books=books,
                market_trades=trades_by_ts.get(ts, {}),
            ),
        )

    return snapshots


class HistoricalReplayLoop:
    """Manages sequential feed of historical market states."""

    def __init__(
        self,
        simulator: ExecutionSimulator,
        reject_on_limit_breach: bool = True,
    ) -> None:
        self.simulator = simulator
        self.reject_on_limit_breach = reject_on_limit_breach

    def step(
        self,
        strategy: BaseStrategy,
        state: MarketStateSnapshot,
    ) -> tuple[Timestamp, list[OrderRequest], list[FillEvent]]:
        """Execute a single timestamp step in the replay."""
        orders = strategy.generate_orders(state)
        fills: list[FillEvent] = []

        for symbol, book in state.books.items():
            sym_orders = [o for o in orders if o.symbol == symbol]
            if not sym_orders:
                continue

            curr_pos = state.get_position(symbol)
            limit = self.simulator.position_limits.get(symbol, 1000)

            try:
                self.simulator.validate_orders_against_limits(curr_pos, sym_orders, limit)
            except PositionLimitExceededError:
                if self.reject_on_limit_breach:
                    # Exchange cancels all orders for this product on this tick
                    continue
                raise

            taker_fills, resting = self.simulator.match_taker_with_remainder(
                state.timestamp,
                book,
                sym_orders,
            )
            fills.extend(taker_fills)

            sym_trades = state.market_trades.get(symbol, [])
            if resting and sym_trades:
                maker_fills = self.simulator.match_maker_orders(
                    state.timestamp,
                    resting,
                    sym_trades,
                    book=book,
                )
                fills.extend(maker_fills)

        return state.timestamp, orders, fills
