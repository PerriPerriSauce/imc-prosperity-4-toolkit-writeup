"""Synthetic Level 2 order book and counterparty trade print builder."""

from __future__ import annotations

import math
from dataclasses import dataclass

from prosperity_toolkit.core.models import Symbol, Timestamp
from prosperity_toolkit.market.order_book import OrderBookL2
from prosperity_toolkit.market.order_flow import TradePrint


@dataclass(frozen=True, slots=True)
class BotBookConfig:
    """Configuration for synthetic market-maker bot quoting around fair value."""

    half_spread_l1: float = 2.0
    depth_l1: int = 10
    step_l2: int = 2
    depth_l2: int = 0

    def __post_init__(self) -> None:
        if self.half_spread_l1 < 0:
            msg = f"half_spread_l1 must be non-negative, got {self.half_spread_l1}"
            raise ValueError(msg)
        if self.depth_l1 <= 0:
            msg = f"depth_l1 must be strictly positive, got {self.depth_l1}"
            raise ValueError(msg)
        if self.step_l2 <= 0:
            msg = f"step_l2 must be strictly positive, got {self.step_l2}"
            raise ValueError(msg)
        if self.depth_l2 < 0:
            msg = f"depth_l2 must be non-negative, got {self.depth_l2}"
            raise ValueError(msg)


def build_synthetic_book(
    symbol: Symbol,
    fair_value: float,
    config: BotBookConfig,
) -> OrderBookL2:
    """Construct a discrete integer OrderBookL2 around fair_value."""
    bid_1 = math.floor(fair_value - config.half_spread_l1)
    ask_1 = math.ceil(fair_value + config.half_spread_l1)
    if bid_1 >= ask_1:
        ask_1 = bid_1 + 1

    bids: dict[int, int] = {bid_1: config.depth_l1}
    asks: dict[int, int] = {ask_1: -config.depth_l1}

    if config.depth_l2 > 0:
        bids[bid_1 - config.step_l2] = config.depth_l2
        asks[ask_1 + config.step_l2] = -config.depth_l2

    book = OrderBookL2(symbol=symbol)
    book.set_depth(bids=bids, asks=asks)
    return book


def build_counterparty_trade(
    timestamp: Timestamp,
    symbol: Symbol,
    book: OrderBookL2,
    signed_arrival_qty: int,
) -> TradePrint | None:
    """Create a synthetic counterparty TradePrint if signed_arrival_qty is non-zero."""
    if signed_arrival_qty == 0:
        return None

    if signed_arrival_qty > 0:
        # Buyer-initiated market order lifts the prevailing best ask (or mid if empty)
        price = book.best_ask if book.best_ask is not None else 0
        if price <= 0:
            return None
        return TradePrint(
            timestamp=timestamp,
            symbol=symbol,
            price=price,
            quantity=signed_arrival_qty,
            buyer="BOT",
            seller="",
        )

    # Seller-initiated market order hits the prevailing best bid
    price = book.best_bid if book.best_bid is not None else 0
    if price <= 0:
        return None
    return TradePrint(
        timestamp=timestamp,
        symbol=symbol,
        price=price,
        quantity=abs(signed_arrival_qty),
        buyer="",
        seller="BOT",
    )
