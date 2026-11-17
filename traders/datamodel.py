"""Official IMC Prosperity 4 Data Model.

Standalone module for competition submission scripts.
Zero external toolkit dependencies.
"""

from __future__ import annotations

import json
from collections.abc import Mapping

Time = int
Symbol = str
Product = str
Position = int
UserId = str
ObservationValue = int


class Listing:
    """Represents an exchange product listing."""

    def __init__(self, symbol: Symbol, product: Product, denomination: Product) -> None:
        self.symbol = symbol
        self.product = product
        self.denomination = denomination


class Order:
    """Represents a submitted buy or sell order."""

    def __init__(self, symbol: Symbol, price: int, quantity: int) -> None:
        self.symbol = symbol
        self.price = price
        self.quantity = quantity

    def __str__(self) -> str:
        return f"({self.symbol}, {self.price}, {self.quantity})"

    def __repr__(self) -> str:
        return f"Order({self.symbol!r}, {self.price!r}, {self.quantity!r})"


class OrderDepth:
    """Represents the order book depth for a specific product."""

    def __init__(self) -> None:
        self.buy_orders: dict[int, int] = {}
        self.sell_orders: dict[int, int] = {}


class Trade:
    """Represents an executed trade transaction."""

    def __init__(
        self,
        symbol: Symbol,
        price: int,
        quantity: int,
        buyer: UserId | None = None,
        seller: UserId | None = None,
        timestamp: int = 0,
    ) -> None:
        self.symbol = symbol
        self.price = price
        self.quantity = quantity
        self.buyer = buyer
        self.seller = seller
        self.timestamp = timestamp

    def __str__(self) -> str:
        parts = [self.symbol, str(self.price), str(self.quantity)]
        parts.extend([str(self.buyer), str(self.seller), str(self.timestamp)])
        return f"({', '.join(parts)})"

    def __repr__(self) -> str:
        return (
            f"Trade({self.symbol!r}, {self.price!r}, {self.quantity!r}, "
            f"{self.buyer!r}, {self.seller!r}, {self.timestamp!r})"
        )


class ConversionObservation:
    """Observations related to conversion and foreign market metrics."""

    def __init__(
        self,
        bidPrice: float = 0.0,
        askPrice: float = 0.0,
        transportFees: float = 0.0,
        exportTariff: float = 0.0,
        importTariff: float = 0.0,
        sunlight: float = 0.0,
        humidity: float = 0.0,
    ) -> None:
        self.bidPrice = bidPrice
        self.askPrice = askPrice
        self.transportFees = transportFees
        self.exportTariff = exportTariff
        self.importTariff = importTariff
        self.sunlight = sunlight
        self.humidity = humidity


class Observation:
    """Container for environmental and plain value observations."""

    def __init__(
        self,
        plainValueObservations: dict[Product, ObservationValue] | None = None,
        conversionObservations: dict[Product, ConversionObservation] | None = None,
    ) -> None:
        self.plainValueObservations = plainValueObservations or {}
        self.conversionObservations = conversionObservations or {}


class TradingState:
    """Complete snapshot of market state delivered to Trader.run at each tick."""

    def __init__(
        self,
        traderData: str,
        timestamp: Time,
        listings: Mapping[Symbol, Listing],
        order_depths: Mapping[Symbol, OrderDepth],
        own_trades: Mapping[Symbol, list[Trade]],
        market_trades: Mapping[Symbol, list[Trade]],
        position: Mapping[Product, Position],
        observations: Observation,
    ) -> None:
        self.traderData = traderData
        self.timestamp = timestamp
        self.listings = dict(listings)
        self.order_depths = dict(order_depths)
        self.own_trades = dict(own_trades)
        self.market_trades = dict(market_trades)
        self.position = dict(position)
        self.observations = observations

    def to_json(self) -> str:
        """Serialize state summary."""
        return json.dumps({
            "timestamp": self.timestamp,
            "position": self.position,
            "traderData": self.traderData,
        })
