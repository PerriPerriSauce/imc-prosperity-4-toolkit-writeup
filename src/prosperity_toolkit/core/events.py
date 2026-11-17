"""Event models for event-driven simulation and telemetry."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias

from prosperity_toolkit.core.models import Cash, Price, Quantity, Symbol, Timestamp

EventId: TypeAlias = str


@dataclass(frozen=True, slots=True)
class MarketDataTickEvent:
    """Triggered when a new market snapshot is ingested."""

    timestamp: Timestamp
    symbol: Symbol
    mid_price: float


@dataclass(frozen=True, slots=True)
class OrderFillEvent:
    """Triggered when an order execution occurs."""

    timestamp: Timestamp
    symbol: Symbol
    price: Price
    quantity: Quantity
    fee: Cash = 0.0


@dataclass(frozen=True, slots=True)
class PortfolioSnapshotEvent:
    """Periodic record of portfolio cash, positions, and aggregate valuation."""

    timestamp: Timestamp
    cash: Cash
    positions: dict[Symbol, Quantity]
    total_unrealized_pnl: float
    total_realized_pnl: float
