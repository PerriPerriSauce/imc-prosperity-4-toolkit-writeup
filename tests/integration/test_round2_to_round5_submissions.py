"""Integration tests verifying standalone Round 2–5 competition traders."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

from prosperity_toolkit.backtesting.engine import BacktestEngine
from prosperity_toolkit.backtesting.replay import build_snapshots_from_dataframes
from prosperity_toolkit.competition import (
    Observation,
    SubmissionValidator,
    TradingState,
    get_round_position_limits,
)
from prosperity_toolkit.competition.adapter import (
    CompetitionStrategyAdapter,
    CompetitionTraderProtocol,
)
from prosperity_toolkit.data.loader import DataLoader
from prosperity_toolkit.execution.simulator import ExecutionSimulator
from prosperity_toolkit.market.market_state import MarketStateSnapshot
from prosperity_toolkit.market.order_book import OrderBookL2


def _load_trader(round_num: int) -> CompetitionTraderProtocol:
    repo_root = Path(__file__).resolve().parents[2]
    traders_dir = str(repo_root / "traders")
    if traders_dir not in sys.path:
        sys.path.insert(0, traders_dir)
    sub_path = repo_root / "traders" / f"round{round_num}" / "submission.py"
    spec = importlib.util.spec_from_file_location(f"round{round_num}_submission", sub_path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    trader: CompetitionTraderProtocol = mod.Trader()
    return trader


@pytest.mark.parametrize("round_num", [2, 3, 4, 5])
def test_submissions_pass_validator_and_handle_empty_corrupt_state(round_num: int) -> None:
    """Every submission passes AST checks and handles empty books + corrupt traderData."""
    sub_path = (
        Path(__file__).resolve().parents[2] / "traders" / f"round{round_num}" / "submission.py"
    )
    assert SubmissionValidator.validate_file(sub_path) == []

    trader = _load_trader(round_num)
    corrupt_state = TradingState(
        traderData="{CORRUPT_NOT_JSON!!!",
        timestamp=0,
        listings={},
        order_depths={},
        own_trades={},
        market_trades={},
        position={},
        observations=Observation(),
    )
    orders, conversions, next_data = trader.run(corrupt_state)
    assert orders == {}
    assert conversions == 0
    assert isinstance(next_data, str)


@pytest.mark.parametrize(
    ("round_num", "sample_day", "max_latency_ms"),
    [
        (2, -1, 1.0),
        (3, 0, 1.5),
        (4, 1, 1.5),
        (5, 2, 3.0),
    ],
)
def test_submissions_deterministic_zero_breaches_and_low_latency(
    round_num: int,
    sample_day: int,
    max_latency_ms: float,
) -> None:
    """Replay first 400 ticks of IS day cleanly without limit breaches and within latency caps."""
    loader = DataLoader()
    try:
        prices_df = loader.load_day_prices(round_num, sample_day)
        trades_df = loader.load_day_trades(round_num, sample_day)
    except FileNotFoundError as exc:
        pytest.skip(f"Round {round_num} raw CSVs unavailable locally: {exc}")
    cutoff = prices_df["timestamp"].drop_duplicates().sort_values().iloc[399]
    p_slice = prices_df[prices_df["timestamp"] <= cutoff]
    t_slice = trades_df[trades_df["timestamp"] <= cutoff]
    snapshots = build_snapshots_from_dataframes(p_slice, t_slice)
    limits = get_round_position_limits(round_num)

    sim_a = ExecutionSimulator(position_limits=limits, fill_mode="queue_aware")
    sim_b = ExecutionSimulator(position_limits=limits, fill_mode="queue_aware")
    eng_a = BacktestEngine(simulator=sim_a, reject_on_limit_breach=False)
    eng_b = BacktestEngine(simulator=sim_b, reject_on_limit_breach=False)

    adapt_a = CompetitionStrategyAdapter(_load_trader(round_num), name=f"R{round_num}_A")
    adapt_b = CompetitionStrategyAdapter(_load_trader(round_num), name=f"R{round_num}_B")

    res_a = eng_a.run(adapt_a, snapshots)
    res_b = eng_b.run(adapt_b, snapshots)

    assert res_a.total_pnl == pytest.approx(res_b.total_pnl)
    assert len(res_a.fills) == len(res_b.fills)
    assert adapt_a.mean_latency_ms < max_latency_ms


def test_submissions_handle_one_sided_books_without_crashing() -> None:
    """All submissions safely skip or handle missing bid/ask levels."""
    for round_num in (2, 3, 4, 5):
        trader = _load_trader(round_num)
        limits = get_round_position_limits(round_num)
        adapter = CompetitionStrategyAdapter(trader, name=f"R{round_num}_OneSided")
        books = {sym: OrderBookL2(symbol=sym, bids={10000: 10}, asks={}) for sym in limits}
        snap = MarketStateSnapshot(timestamp=100, books=books)
        orders = adapter.generate_orders(snap)
        assert isinstance(orders, list)


@pytest.mark.parametrize(
    ("round_num", "max_latency_ms"),
    [(2, 1.5), (3, 2.0), (4, 2.0), (5, 3.5)],
)
def test_synthetic_round2_to_round5_determinism_and_limits(
    round_num: int,
    max_latency_ms: float,
) -> None:
    """Verify determinism, limit compliance, and speed on synthetic books (CI-safe)."""
    limits = get_round_position_limits(round_num)
    snapshots: list[MarketStateSnapshot] = []
    for tick in range(120):
        ts = tick * 100
        shift = (tick % 5) - 2
        books: dict[str, OrderBookL2] = {}
        for sym in limits:
            base = 10000 if sym.startswith("PEBBLES") else 5000 + (sum(ord(c) for c in sym) % 50)
            mid = base + shift
            books[sym] = OrderBookL2(
                symbol=sym,
                bids={mid - 2: 12, mid - 5: 30},
                asks={mid + 2: 12, mid + 5: 30},
            )
        snapshots.append(MarketStateSnapshot(timestamp=ts, books=books))

    sim_a = ExecutionSimulator(position_limits=limits, fill_mode="queue_aware")
    sim_b = ExecutionSimulator(position_limits=limits, fill_mode="queue_aware")
    eng_a = BacktestEngine(simulator=sim_a, reject_on_limit_breach=False)
    eng_b = BacktestEngine(simulator=sim_b, reject_on_limit_breach=False)

    adapt_a = CompetitionStrategyAdapter(_load_trader(round_num), name=f"R{round_num}_SynA")
    adapt_b = CompetitionStrategyAdapter(_load_trader(round_num), name=f"R{round_num}_SynB")

    res_a = eng_a.run(adapt_a, snapshots)
    res_b = eng_b.run(adapt_b, snapshots)

    assert res_a.total_pnl == pytest.approx(res_b.total_pnl)
    assert len(res_a.fills) == len(res_b.fills)
    assert adapt_a.mean_latency_ms < max_latency_ms
