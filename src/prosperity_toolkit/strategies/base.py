"""Base class and lifecycle contract for all research strategies."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping

from prosperity_toolkit.core.models import OrderRequest, Position, Symbol
from prosperity_toolkit.market.market_state import MarketStateSnapshot


class BaseStrategy(ABC):
    """Abstract base class defining strategy lifecycle."""

    def __init__(self, name: str = "BaseStrategy") -> None:
        self.name = name
        self.positions: dict[Symbol, Position] = {}

    def update_positions(self, positions: Mapping[Symbol, Position]) -> None:
        """Sync internal position state with external engine state."""
        self.positions = dict(positions)

    @abstractmethod
    def generate_orders(self, state: MarketStateSnapshot) -> list[OrderRequest]:
        """Compute desired order requests given current market snapshot.

        Concrete implementations will be developed in strategy-specific milestones.
        """
        ...
