"""Execution simulator matching orders against order books and position limits."""

from __future__ import annotations

from typing import Literal, TypeAlias

from prosperity_toolkit.core.exceptions import PositionLimitExceededError
from prosperity_toolkit.core.models import OrderRequest, Position, Symbol, Timestamp
from prosperity_toolkit.execution.fills import FillEvent, FillType
from prosperity_toolkit.market.order_book import OrderBookL2
from prosperity_toolkit.market.order_flow import TradePrint

FillMode: TypeAlias = Literal["conservative", "queue_aware", "touch"]


class ExecutionSimulator:
    """Simulates exchange matching engine and enforces Prosperity position constraints."""

    def __init__(
        self,
        position_limits: dict[Symbol, int] | None = None,
        conservative_fills: bool = True,
        fill_mode: FillMode | None = None,
    ) -> None:
        self.position_limits = position_limits or {}
        if fill_mode is not None:
            self.fill_mode: FillMode = fill_mode
        else:
            self.fill_mode = "conservative" if conservative_fills else "touch"
        self.conservative_fills = self.fill_mode == "conservative"

    def validate_orders_against_limits(
        self,
        starting_pos: Position,
        orders: list[OrderRequest],
        limit: int,
    ) -> None:
        """Enforce Prosperity aggregate worst-case starting position check.

        In Prosperity:
            worst_long = starting_pos + sum(max(0, qty))
            worst_short = starting_pos + sum(min(0, qty))
        If worst_long > limit or worst_short < -limit, all orders for that product are rejected.
        """
        buy_qty = sum(o.quantity for o in orders if o.quantity > 0)
        sell_qty = sum(o.quantity for o in orders if o.quantity < 0)

        if starting_pos + buy_qty > limit:
            msg = (
                f"Worst-case long exposure {starting_pos + buy_qty} exceeds position limit {limit}"
            )
            raise PositionLimitExceededError(msg)

        if starting_pos + sell_qty < -limit:
            msg = (
                f"Worst-case short exposure {starting_pos + sell_qty} "
                f"exceeds position limit -{limit}"
            )
            raise PositionLimitExceededError(msg)

    def match_taker_orders(
        self,
        timestamp: Timestamp,
        book: OrderBookL2,
        orders: list[OrderRequest],
    ) -> list[FillEvent]:
        """Execute crossing aggressive taker orders across the full sorted price ladder."""
        fills, _ = self.match_taker_with_remainder(timestamp, book, orders)
        return fills

    def match_taker_with_remainder(
        self,
        timestamp: Timestamp,
        book: OrderBookL2,
        orders: list[OrderRequest],
    ) -> tuple[list[FillEvent], list[OrderRequest]]:
        """Match aggressive taker orders across book levels and return unfilled remainders."""
        fills: list[FillEvent] = []
        resting: list[OrderRequest] = []

        rem_asks = {p: abs(v) for p, v in book.asks.items() if v != 0}
        rem_bids = {p: abs(v) for p, v in book.bids.items() if v != 0}

        for order in orders:
            if order.quantity > 0:
                remaining = order.quantity
                for ask_price in sorted(rem_asks.keys()):
                    if ask_price > order.price or remaining <= 0:
                        break
                    avail = rem_asks[ask_price]
                    if avail <= 0:
                        continue
                    matched = min(remaining, avail)
                    fills.append(
                        FillEvent(
                            timestamp=timestamp,
                            symbol=order.symbol,
                            price=ask_price,
                            quantity=matched,
                            fill_type=FillType.TAKER,
                        ),
                    )
                    rem_asks[ask_price] -= matched
                    remaining -= matched
                if remaining > 0:
                    resting.append(
                        OrderRequest(symbol=order.symbol, price=order.price, quantity=remaining),
                    )
            else:
                remaining = abs(order.quantity)
                for bid_price in sorted(rem_bids.keys(), reverse=True):
                    if bid_price < order.price or remaining <= 0:
                        break
                    avail = rem_bids[bid_price]
                    if avail <= 0:
                        continue
                    matched = min(remaining, avail)
                    fills.append(
                        FillEvent(
                            timestamp=timestamp,
                            symbol=order.symbol,
                            price=bid_price,
                            quantity=-matched,
                            fill_type=FillType.TAKER,
                        ),
                    )
                    rem_bids[bid_price] -= matched
                    remaining -= matched
                if remaining > 0:
                    resting.append(
                        OrderRequest(symbol=order.symbol, price=order.price, quantity=-remaining),
                    )

        return fills, resting

    def match_maker_orders(
        self,
        timestamp: Timestamp,
        resting_orders: list[OrderRequest],
        market_trades: list[TradePrint],
        book: OrderBookL2 | None = None,
    ) -> list[FillEvent]:
        """Match passive resting orders under conservative, queue_aware, or touch fill rules."""
        if not resting_orders or not market_trades:
            return []

        fills: list[FillEvent] = []
        rem_trade_vols = [abs(t.quantity) for t in market_trades]
        bid_queue = {p: abs(v) for p, v in book.bids.items()} if book is not None else {}
        ask_queue = {p: abs(v) for p, v in book.asks.items()} if book is not None else {}

        for order in resting_orders:
            remaining = abs(order.quantity)
            is_buy = order.quantity > 0

            for idx, trade in enumerate(market_trades):
                if remaining <= 0:
                    break
                if trade.symbol != order.symbol or rem_trade_vols[idx] <= 0:
                    continue

                strictly_through = (
                    trade.price < order.price if is_buy else trade.price > order.price
                )
                at_touch = trade.price == order.price

                if self.fill_mode == "conservative":
                    if not strictly_through:
                        continue
                    fillable_vol = rem_trade_vols[idx]
                elif self.fill_mode == "touch":
                    if not (strictly_through or at_touch):
                        continue
                    fillable_vol = rem_trade_vols[idx]
                else:  # queue_aware
                    if strictly_through:
                        fillable_vol = rem_trade_vols[idx]
                    elif at_touch:
                        q_map = bid_queue if is_buy else ask_queue
                        ahead = q_map.get(order.price, 0)
                        if rem_trade_vols[idx] <= ahead:
                            q_map[order.price] = ahead - rem_trade_vols[idx]
                            rem_trade_vols[idx] = 0
                            continue
                        fillable_vol = rem_trade_vols[idx] - ahead
                        q_map[order.price] = 0
                    else:
                        continue

                matched = min(remaining, fillable_vol)
                if matched <= 0:
                    continue
                fills.append(
                    FillEvent(
                        timestamp=timestamp,
                        symbol=order.symbol,
                        price=order.price,
                        quantity=matched if is_buy else -matched,
                        fill_type=FillType.MAKER,
                    ),
                )
                rem_trade_vols[idx] -= matched
                remaining -= matched

        return fills
