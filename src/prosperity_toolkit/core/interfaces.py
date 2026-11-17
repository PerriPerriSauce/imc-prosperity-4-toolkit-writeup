"""Abstract interfaces and protocols governing core framework interactions."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from prosperity_toolkit.core.models import OrderRequest, Symbol, Timestamp


@runtime_checkable
class MarketDataProvider(Protocol):
    """Protocol for components providing market data streams."""

    def current_timestamp(self) -> Timestamp:
        """Return the current simulation timestamp."""
        ...


@runtime_checkable
class ExecutionHandler(Protocol):
    """Protocol for execution simulators."""

    def submit_orders(
        self,
        timestamp: Timestamp,
        orders: list[OrderRequest],
    ) -> list[OrderRequest]:
        """Process and match submitted orders."""
        ...


@runtime_checkable
class StrategyProtocol(Protocol):
    """Generic protocol for algorithmic trading strategies."""

    def reset(self) -> None:
        """Reset internal state between simulation runs."""
        ...

    def get_positions(self) -> dict[Symbol, int]:
        """Return current tracked positions."""
        ...
