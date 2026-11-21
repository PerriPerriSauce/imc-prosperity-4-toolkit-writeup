"""Historical replay loop and snapshot reconstruction from market data."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pandas as pd

from prosperity_toolkit.core.exceptions import PositionLimitExceededError
from prosperity_toolkit.core.models import OrderRequest, Position, Symbol, Timestamp
from prosperity_toolkit.execution.fills import FillEvent
from prosperity_toolkit.execution.simulator import ExecutionSimulator
from prosperity_toolkit.market.market_state import MarketStateSnapshot
from prosperity_toolkit.market.order_book import OrderBookL2
from prosperity_toolkit.market.order_flow import TradePrint
from prosperity_toolkit.strategies.base import BaseStrategy


def _optional_col(
    df: pd.DataFrame,
    col: str,
) -> tuple[list[Any] | None, list[bool] | None]:
    """Return raw values and validity flags for an optional DataFrame column."""
    if col not in df.columns:
        return None, None
    series = df[col]
    return series.tolist(), pd.notna(series).tolist()


def build_snapshots_from_dataframes(
    prices_df: pd.DataFrame,
    trades_df: pd.DataFrame | None = None,
) -> list[MarketStateSnapshot]:
    """Convert validated price and trade DataFrames into chronological MarketStateSnapshots."""
    if prices_df.empty:
        return []

    trades_by_ts: dict[int, dict[str, list[TradePrint]]] = {}
    if trades_df is not None and not trades_df.empty:
        t_ts = trades_df["timestamp"].tolist()
        t_sym = trades_df["symbol"].tolist()
        t_px = trades_df["price"].tolist()
        t_qty = trades_df["quantity"].tolist()
        t_buyer, ok_buyer = _optional_col(trades_df, "buyer")
        t_seller, ok_seller = _optional_col(trades_df, "seller")

        for idx in range(len(t_ts)):
            ts = int(t_ts[idx])
            sym = str(t_sym[idx])
            buyer = str(t_buyer[idx]) if t_buyer is not None and ok_buyer and ok_buyer[idx] else ""
            seller = (
                str(t_seller[idx]) if t_seller is not None and ok_seller and ok_seller[idx] else ""
            )
            tp = TradePrint(
                timestamp=ts,
                symbol=sym,
                price=int(t_px[idx]),
                quantity=int(t_qty[idx]),
                buyer=buyer,
                seller=seller,
            )
            trades_by_ts.setdefault(ts, {}).setdefault(sym, []).append(tp)

    ordered_prices = (
        prices_df
        if prices_df["timestamp"].is_monotonic_increasing
        else prices_df.sort_values("timestamp", kind="mergesort")
    )

    ts_col = ordered_prices["timestamp"].tolist()
    sym_col = ordered_prices["product"].tolist()
    levels: list[
        tuple[
            list[Any] | None,
            list[bool] | None,
            list[Any] | None,
            list[bool] | None,
            list[Any] | None,
            list[bool] | None,
            list[Any] | None,
            list[bool] | None,
        ]
    ] = []
    for lvl in (1, 2, 3):
        bp_v, bp_ok = _optional_col(ordered_prices, f"bid_price_{lvl}")
        bv_v, bv_ok = _optional_col(ordered_prices, f"bid_volume_{lvl}")
        ap_v, ap_ok = _optional_col(ordered_prices, f"ask_price_{lvl}")
        av_v, av_ok = _optional_col(ordered_prices, f"ask_volume_{lvl}")
        levels.append((bp_v, bp_ok, bv_v, bv_ok, ap_v, ap_ok, av_v, av_ok))

    snapshots: list[MarketStateSnapshot] = []
    current_ts: int | None = None
    books: dict[str, OrderBookL2] = {}

    for idx in range(len(ts_col)):
        ts = int(ts_col[idx])
        if current_ts is None:
            current_ts = ts
        elif ts != current_ts:
            snapshots.append(
                MarketStateSnapshot(
                    timestamp=current_ts,
                    books=books,
                    market_trades=trades_by_ts.get(current_ts, {}),
                ),
            )
            current_ts = ts
            books = {}

        sym = str(sym_col[idx])
        bids: dict[int, int] = {}
        asks: dict[int, int] = {}
        for bp_v, bp_ok, bv_v, bv_ok, ap_v, ap_ok, av_v, av_ok in levels:
            if bp_v is not None and bv_v is not None and bp_ok and bv_ok:
                if bp_ok[idx] and bv_ok[idx]:
                    bids[int(bp_v[idx])] = int(bv_v[idx])
            if ap_v is not None and av_v is not None and ap_ok and av_ok:
                if ap_ok[idx] and av_ok[idx]:
                    # Prosperity convention: sell_orders quantities are negative
                    asks[int(ap_v[idx])] = -abs(int(av_v[idx]))

        books[sym] = OrderBookL2(symbol=sym, bids=bids, asks=asks)

    if current_ts is not None:
        snapshots.append(
            MarketStateSnapshot(
                timestamp=current_ts,
                books=books,
                market_trades=trades_by_ts.get(current_ts, {}),
            ),
        )

    return snapshots


class HistoricalReplayLoop:
    """Manages sequential feed of historical market states with strict temporal causality."""

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
        positions: Mapping[Symbol, Position] | None = None,
        prior_market_trades: Mapping[Symbol, list[TradePrint]] | None = None,
        prior_own_trades: Mapping[Symbol, list[TradePrint]] | None = None,
    ) -> tuple[Timestamp, list[OrderRequest], list[FillEvent]]:
        """Execute a single causal timestamp step in the replay.

        The strategy sees order books at `state.timestamp` together with market/own
        trades from the *prior* interval (never same-tick `state.market_trades`).
        Submitted resting orders are then matched against incoming `state.market_trades`
        against the post-taker residual book.
        """
        eff_positions = dict(positions) if positions is not None else dict(state.positions)
        decision_state = MarketStateSnapshot(
            timestamp=state.timestamp,
            books=state.books,
            positions=eff_positions,
            market_trades=dict(prior_market_trades) if prior_market_trades is not None else {},
            own_trades=dict(prior_own_trades) if prior_own_trades is not None else {},
            trader_data=state.trader_data,
        )
        orders = strategy.generate_orders(decision_state)
        fills: list[FillEvent] = []
        orders_by_sym: dict[str, list[OrderRequest]] = {}
        for order in orders:
            orders_by_sym.setdefault(order.symbol, []).append(order)

        for symbol, book in state.books.items():
            sym_orders = orders_by_sym.get(symbol)
            if not sym_orders:
                continue

            curr_pos = eff_positions.get(symbol, 0)
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
                residual_book = self.simulator.remaining_book_after_taker(book, taker_fills)
                maker_fills = self.simulator.match_maker_orders(
                    state.timestamp,
                    resting,
                    sym_trades,
                    book=residual_book,
                )
                fills.extend(maker_fills)

        return state.timestamp, orders, fills
