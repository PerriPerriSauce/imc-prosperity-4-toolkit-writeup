"""Unit tests for Prosperity 4 datamodel parity and CompetitionStrategyAdapter."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from prosperity_toolkit.backtesting.engine import BacktestEngine
from prosperity_toolkit.competition import (
    PROSPERITY4_POSITION_LIMITS,
    PROSPERITY4_R5_CATEGORIES,
    PROSPERITY4_VOUCHER_STRIKES,
    get_round_position_limits,
    get_round_products,
)
from prosperity_toolkit.competition.adapter import CompetitionStrategyAdapter
from prosperity_toolkit.competition.datamodel import (
    ConversionObservation,
    Listing,
    Observation,
    Order,
    OrderDepth,
    ProsperityEncoder,
    Symbol,
    Trade,
    TradingState,
)
from prosperity_toolkit.execution.simulator import ExecutionSimulator
from prosperity_toolkit.market.market_state import MarketStateSnapshot
from prosperity_toolkit.market.order_book import OrderBookL2


class _DummyStatefulTrader:
    """Minimal test Trader verifying traderData persistence and Order emission."""

    def run(self, state: TradingState) -> tuple[dict[Symbol, list[Order]], int, str]:
        count = int(state.traderData) + 1 if state.traderData else 1
        orders: dict[Symbol, list[Order]] = {}
        if state.timestamp == 0 and "OSMIUM" in state.order_depths:
            depth = state.order_depths["OSMIUM"]
            if depth.sell_orders:
                best_ask = min(depth.sell_orders.keys())
                orders["OSMIUM"] = [Order("OSMIUM", best_ask, 1)]
        return orders, 0, str(count)


def test_datamodel_object_construction() -> None:
    """Verify exact Prosperity 4 datamodel classes and serialization."""
    listing = Listing(symbol="OSMIUM", product="OSMIUM", denomination=1)
    assert listing.denomination == 1

    conv = ConversionObservation(
        bidPrice=100.0,
        askPrice=101.0,
        transportFees=0.5,
        exportTariff=1.0,
        importTariff=1.5,
        sugarPrice=50.0,
        sunlightIndex=60.0,
    )
    obs = Observation(
        plainValueObservations={"SUN": 10},
        conversionObservations={"ORCHID": conv},
    )
    assert "plainValueObservations" in str(obs)

    depth = OrderDepth()
    depth.buy_orders[99] = 10
    depth.sell_orders[101] = -10

    trade = Trade(symbol="OSMIUM", price=100, quantity=2, buyer="SUB", seller="", timestamp=100)
    assert "OSMIUM" in str(trade)

    state = TradingState(
        traderData="{}",
        timestamp=100,
        listings={"OSMIUM": listing},
        order_depths={"OSMIUM": depth},
        own_trades={"OSMIUM": [trade]},
        market_trades={},
        position={"OSMIUM": 0},
        observations=obs,
    )
    parsed = json.loads(state.toJSON())
    assert parsed["timestamp"] == 100
    assert parsed["position"] == {"OSMIUM": 0}

    encoded = json.dumps(listing, cls=ProsperityEncoder)
    assert '"symbol": "OSMIUM"' in encoded


def test_standalone_traders_datamodel_parity() -> None:
    """Verify traders/datamodel.py exposes identical core classes."""
    spec = importlib.util.spec_from_file_location("traders_datamodel", Path("traders/datamodel.py"))
    assert spec is not None and spec.loader is not None
    standalone_dm = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(standalone_dm)

    order = standalone_dm.Order("TOMATOES", 5000, -3)
    assert str(order) == "(TOMATOES, 5000, -3)"
    conv = standalone_dm.ConversionObservation(1.0, 2.0, 0.1, 0.2, 0.3, 10.0, 20.0)
    assert conv.sugarPrice == 10.0
    assert conv.sunlightIndex == 20.0


def test_competition_strategy_adapter_and_trader_data_persistence() -> None:
    """Verify CompetitionStrategyAdapter executes Trader.run and persists traderData."""
    book = OrderBookL2(symbol="OSMIUM")
    book.set_depth(bids={99: 5}, asks={101: -5})
    snap0 = MarketStateSnapshot(timestamp=0, books={"OSMIUM": book})
    snap1 = MarketStateSnapshot(timestamp=100, books={"OSMIUM": book})

    adapter = CompetitionStrategyAdapter(trader=_DummyStatefulTrader())
    engine = BacktestEngine(simulator=ExecutionSimulator(position_limits={"OSMIUM": 20}))
    result = engine.run(adapter, [snap0, snap1])

    assert adapter.trader_data == "2"
    assert len(adapter.latencies_ms) == 2
    assert adapter.mean_latency_ms >= 0.0
    assert len(result.fills) == 1
    assert result.fills[0].price == 101
    assert result.fills[0].quantity == 1


def test_prosperity4_specifications_and_limits() -> None:
    """Verify Round 0-5 product counts, strike table, and position limits."""
    assert len(get_round_products(0)) == 2
    assert len(get_round_products(1)) == 2
    assert len(get_round_products(2)) == 2
    assert len(get_round_products(3)) == 12
    assert len(get_round_products(4)) == 12
    assert len(get_round_products(5)) == 50
    assert len(PROSPERITY4_R5_CATEGORIES) == 10
    assert len(PROSPERITY4_VOUCHER_STRIKES) == 10
    assert len(PROSPERITY4_POSITION_LIMITS) == 66

    assert get_round_position_limits(3)["VELVETFRUIT_EXTRACT"] == 200
    assert get_round_position_limits(3)["VEV_5300"] == 300
    assert all(v == 10 for v in get_round_position_limits(5).values())
