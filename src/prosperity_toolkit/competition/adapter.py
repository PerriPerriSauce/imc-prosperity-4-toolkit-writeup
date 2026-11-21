"""Adapter bridging internal toolkit models and competition Trader submissions."""

from __future__ import annotations

import importlib.util
import sys
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Protocol

from prosperity_toolkit.competition.datamodel import (
    Listing,
    Observation,
    Order,
    OrderDepth,
    Symbol,
    Trade,
    TradingState,
)
from prosperity_toolkit.core.models import OrderRequest
from prosperity_toolkit.market.market_state import MarketStateSnapshot
from prosperity_toolkit.strategies.base import BaseStrategy


class CompetitionTraderProtocol(Protocol):
    """Protocol for standalone Prosperity Trader classes."""

    def run(self, state: TradingState) -> tuple[dict[Symbol, list[Order]], int, str]:
        """Execute a single tick and return (orders, conversions, traderData)."""
        ...


class CompetitionStateAdapter:
    """Bridges internal toolkit MarketStateSnapshot to competition TradingState."""

    @staticmethod
    def to_trading_state(
        snapshot: MarketStateSnapshot,
        trader_data: str = "",
        listings: Mapping[str, Listing] | None = None,
        own_trades: Mapping[str, list[Trade]] | None = None,
        observations: Observation | None = None,
    ) -> TradingState:
        """Convert internal snapshot to authoritative TradingState."""
        order_depths: dict[str, OrderDepth] = {}
        for sym, book in snapshot.books.items():
            depth = OrderDepth()
            depth.buy_orders = dict(book.bids)
            depth.sell_orders = dict(book.asks)
            order_depths[sym] = depth

        market_trades: dict[str, list[Trade]] = {}
        for sym, prints in snapshot.market_trades.items():
            market_trades[sym] = [
                Trade(
                    symbol=tp.symbol,
                    price=tp.price,
                    quantity=tp.quantity,
                    buyer=tp.buyer,
                    seller=tp.seller,
                    timestamp=tp.timestamp,
                )
                for tp in prints
            ]

        return TradingState(
            traderData=trader_data,
            timestamp=snapshot.timestamp,
            listings=dict(listings) if listings is not None else {},
            order_depths=order_depths,
            own_trades=dict(own_trades) if own_trades is not None else {},
            market_trades=market_trades,
            position=dict(snapshot.positions),
            observations=observations or Observation(),
        )


class CompetitionStrategyAdapter(BaseStrategy):
    """Wraps a standalone competition Trader for execution inside BacktestEngine."""

    def __init__(
        self,
        trader: CompetitionTraderProtocol,
        name: str | None = None,
        listings: Mapping[str, Listing] | None = None,
    ) -> None:
        super().__init__(name=name or type(trader).__name__)
        self.trader = trader
        self.listings = dict(listings) if listings is not None else {}
        self.trader_data: str = ""
        self.last_conversions: int = 0
        self.latencies_ms: list[float] = []

    def reset(self) -> None:
        """Reset persisted traderData and latency telemetry."""
        self.trader_data = ""
        self.last_conversions = 0
        self.latencies_ms.clear()

    def generate_orders(self, state: MarketStateSnapshot) -> list[OrderRequest]:
        """Translate MarketStateSnapshot to TradingState, invoke Trader.run, and convert orders."""
        own_trades: dict[str, list[Trade]] = {
            sym: [
                Trade(
                    symbol=tp.symbol,
                    price=tp.price,
                    quantity=tp.quantity,
                    buyer=tp.buyer,
                    seller=tp.seller,
                    timestamp=tp.timestamp,
                )
                for tp in prints
            ]
            for sym, prints in state.own_trades.items()
        }
        trading_state = CompetitionStateAdapter.to_trading_state(
            snapshot=state,
            trader_data=self.trader_data,
            listings=self.listings,
            own_trades=own_trades,
        )

        t0 = time.perf_counter()
        raw_result: Any = self.trader.run(trading_state)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        self.latencies_ms.append(elapsed_ms)

        if isinstance(raw_result, tuple):
            orders_dict, conversions, next_trader_data = raw_result
            self.last_conversions = int(conversions)
            self.trader_data = str(next_trader_data)
        else:
            orders_dict = raw_result
            self.last_conversions = 0

        requests: list[OrderRequest] = []
        for sym_orders in orders_dict.values():
            for order in sym_orders:
                if order.quantity != 0:
                    requests.append(
                        OrderRequest(
                            symbol=order.symbol,
                            price=int(order.price),
                            quantity=int(order.quantity),
                        ),
                    )
        return requests

    @property
    def mean_latency_ms(self) -> float:
        """Mean per-tick execution latency in milliseconds."""
        if not self.latencies_ms:
            return 0.0
        return sum(self.latencies_ms) / len(self.latencies_ms)


def load_competition_trader(
    submission_path: Path,
    **kwargs: Any,
) -> CompetitionTraderProtocol:
    """Dynamically load a standalone ``Trader`` instance from a submission script."""
    resolved = submission_path.resolve()
    traders_dir = (
        resolved.parents[1]
        if len(resolved.parents) >= 2 and (resolved.parents[1] / "datamodel.py").exists()
        else Path("traders").resolve()
    )
    if traders_dir.exists() and str(traders_dir) not in sys.path:
        sys.path.insert(0, str(traders_dir))
    mod_name = f"loaded_{resolved.parent.name}_{resolved.stem}"
    spec = importlib.util.spec_from_file_location(mod_name, resolved)
    if spec is None or spec.loader is None:
        msg = f"Unable to load submission module from {resolved}"
        raise ImportError(msg)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    trader_cls = getattr(module, "Trader", None)
    if trader_cls is None:
        msg = f"Submission module {resolved} does not define a Trader class."
        raise AttributeError(msg)
    trader: CompetitionTraderProtocol = trader_cls(**kwargs)
    return trader

