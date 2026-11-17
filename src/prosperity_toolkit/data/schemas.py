"""Strict schema definitions for Prosperity 4 raw and processed data."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

PRICE_CSV_COLUMNS: Final[list[str]] = [
    "day",
    "timestamp",
    "product",
    "bid_price_1",
    "bid_volume_1",
    "bid_price_2",
    "bid_volume_2",
    "bid_price_3",
    "bid_volume_3",
    "ask_price_1",
    "ask_volume_1",
    "ask_price_2",
    "ask_volume_2",
    "ask_price_3",
    "ask_volume_3",
    "mid_price",
    "profit_and_loss",
]

TRADE_CSV_COLUMNS: Final[list[str]] = [
    "timestamp",
    "buyer",
    "seller",
    "symbol",
    "price",
    "quantity",
]


@dataclass(frozen=True, slots=True)
class PriceRecordSchema:
    """Schema descriptor for a single timestamp price and book depth entry."""

    day: int
    timestamp: int
    product: str
    bid_price_1: int | None
    bid_volume_1: int | None
    bid_price_2: int | None
    bid_volume_2: int | None
    bid_price_3: int | None
    bid_volume_3: int | None
    ask_price_1: int | None
    ask_volume_1: int | None
    ask_price_2: int | None
    ask_volume_2: int | None
    ask_price_3: int | None
    ask_volume_3: int | None
    mid_price: float
    profit_and_loss: float = 0.0


@dataclass(frozen=True, slots=True)
class TradeRecordSchema:
    """Schema descriptor for a public market trade print."""

    timestamp: int
    buyer: str
    seller: str
    symbol: str
    price: int
    quantity: int
