"""Execution simulator matching orders against order books and position limits."""

from __future__ import annotations

from prosperity_toolkit.core.exceptions import PositionLimitExceededError
from prosperity_toolkit.core.models import OrderRequest, Position, Symbol, Timestamp
from prosperity_toolkit.execution.fills import FillEvent, FillType
from prosperity_toolkit.market.order_book import OrderBookL2


class ExecutionSimulator:
    """Simulates exchange matching engine and enforces Prosperity position constraints."""

    def __init__(self, position_limits: dict[Symbol, int] | None = None) -> None:
        self.position_limits = position_limits or {}

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
        """Execute crossing aggressive taker orders against available book depth."""
        fills: list[FillEvent] = []
        for order in orders:
            if order.quantity > 0:  # Buy taker
                best_ask = book.best_ask
                if best_ask is not None and order.price >= best_ask:
                    avail_depth = abs(book.asks.get(best_ask, 0))
                    matched_qty = min(order.quantity, avail_depth)
                    if matched_qty > 0:
                        fills.append(
                            FillEvent(
                                timestamp=timestamp,
                                symbol=order.symbol,
                                price=best_ask,
                                quantity=matched_qty,
                                fill_type=FillType.TAKER,
                            ),
                        )
            elif order.quantity < 0:  # Sell taker
                best_bid = book.best_bid
                if best_bid is not None and order.price <= best_bid:
                    avail_depth = abs(book.bids.get(best_bid, 0))
                    matched_qty = min(abs(order.quantity), avail_depth)
                    if matched_qty > 0:
                        fills.append(
                            FillEvent(
                                timestamp=timestamp,
                                symbol=order.symbol,
                                price=best_bid,
                                quantity=-matched_qty,
                                fill_type=FillType.TAKER,
                            ),
                        )
        return fills
