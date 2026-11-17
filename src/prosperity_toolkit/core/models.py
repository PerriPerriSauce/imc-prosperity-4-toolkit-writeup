"""Fundamental data types, identifiers, and core domain models."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TypeAlias

Timestamp: TypeAlias = int
Symbol: TypeAlias = str
Price: TypeAlias = int
Quantity: TypeAlias = int
Position: TypeAlias = int
Cash: TypeAlias = float


class Direction(Enum):
    """Trade direction."""

    BUY = 1
    SELL = -1


@dataclass(frozen=True, slots=True)
class OrderRequest:
    """Internal order request definition."""

    symbol: Symbol
    price: Price
    quantity: Quantity

    def __post_init__(self) -> None:
        if self.quantity == 0:
            msg = f"Order quantity cannot be zero for symbol {self.symbol}"
            raise ValueError(msg)
        if self.price <= 0:
            msg = f"Order price must be strictly positive, got {self.price}"
            raise ValueError(msg)

    @property
    def direction(self) -> Direction:
        """Derive trade direction from quantity sign."""
        return Direction.BUY if self.quantity > 0 else Direction.SELL
