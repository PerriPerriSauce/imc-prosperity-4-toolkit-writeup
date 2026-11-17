"""Official IMC Prosperity 4 Data Model.

This module provides exact structural parity with traders/datamodel.py and the
official IMC Prosperity 4 competition runtime.
"""

from __future__ import annotations

import json
from json import JSONEncoder
from typing import Any

import jsonpickle

Time = int
Symbol = str
Product = str
Position = int
UserId = str
ObservationValue = int


class Listing:
    """Represents an exchange product listing."""

    def __init__(self, symbol: Symbol, product: Product, denomination: int) -> None:
        self.symbol = symbol
        self.product = product
        self.denomination = denomination


class ConversionObservation:
    """Observations related to conversion and foreign market metrics."""

    def __init__(
        self,
        bidPrice: float,
        askPrice: float,
        transportFees: float,
        exportTariff: float,
        importTariff: float,
        sugarPrice: float,
        sunlightIndex: float,
    ) -> None:
        self.bidPrice = bidPrice
        self.askPrice = askPrice
        self.transportFees = transportFees
        self.exportTariff = exportTariff
        self.importTariff = importTariff
        self.sugarPrice = sugarPrice
        self.sunlightIndex = sunlightIndex


class Observation:
    """Container for environmental and plain value observations."""

    def __init__(
        self,
        plainValueObservations: dict[Product, ObservationValue] | None = None,
        conversionObservations: dict[Product, ConversionObservation] | None = None,
    ) -> None:
        self.plainValueObservations: dict[Product, ObservationValue] = (
            plainValueObservations if plainValueObservations is not None else {}
        )
        self.conversionObservations: dict[Product, ConversionObservation] = (
            conversionObservations if conversionObservations is not None else {}
        )

    def __str__(self) -> str:
        plain_str = jsonpickle.encode(self.plainValueObservations)
        conv_str = jsonpickle.encode(self.conversionObservations)
        return f"(plainValueObservations: {plain_str}, conversionObservations: {conv_str})"


class Order:
    """Represents a submitted buy or sell order."""

    def __init__(self, symbol: Symbol, price: int, quantity: int) -> None:
        self.symbol = symbol
        self.price = price
        self.quantity = quantity

    def __str__(self) -> str:
        return f"({self.symbol}, {self.price}, {self.quantity})"

    def __repr__(self) -> str:
        return f"({self.symbol}, {self.price}, {self.quantity})"


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
        self.price: int = price
        self.quantity: int = quantity
        self.buyer = buyer
        self.seller = seller
        self.timestamp = timestamp

    def __str__(self) -> str:
        buyer_str = self.buyer if self.buyer is not None else ""
        seller_str = self.seller if self.seller is not None else ""
        return (
            f"({self.symbol}, {buyer_str} << {seller_str}, "
            f"{self.price}, {self.quantity}, {self.timestamp})"
        )

    def __repr__(self) -> str:
        return self.__str__()


class TradingState:
    """Complete snapshot of market state delivered to Trader.run at each tick."""

    def __init__(
        self,
        traderData: str,
        timestamp: Time,
        listings: dict[Symbol, Listing],
        order_depths: dict[Symbol, OrderDepth],
        own_trades: dict[Symbol, list[Trade]],
        market_trades: dict[Symbol, list[Trade]],
        position: dict[Product, Position],
        observations: Observation,
    ) -> None:
        self.traderData = traderData
        self.timestamp = timestamp
        self.listings = listings
        self.order_depths = order_depths
        self.own_trades = own_trades
        self.market_trades = market_trades
        self.position = position
        self.observations = observations

    def toJSON(self) -> str:
        """Serialize state to JSON."""
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True)


class ProsperityEncoder(JSONEncoder):
    """JSON encoder for Prosperity datamodel objects."""

    def default(self, o: Any) -> Any:
        return o.__dict__
