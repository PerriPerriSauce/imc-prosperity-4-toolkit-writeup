"""Fill simulation models determining maker and taker execution outcomes."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from prosperity_toolkit.core.models import Price, Quantity, Symbol, Timestamp


class FillType(Enum):
    """Fill execution category."""

    TAKER = "TAKER"
    MAKER = "MAKER"


@dataclass(frozen=True, slots=True)
class FillEvent:
    """Represents a matched order execution."""

    timestamp: Timestamp
    symbol: Symbol
    price: Price
    quantity: Quantity
    fill_type: FillType
    fee: float = 0.0


class FillModel:
    """Configurable execution fill logic."""

    def __init__(self, conservative: bool = True) -> None:
        self.conservative = conservative
