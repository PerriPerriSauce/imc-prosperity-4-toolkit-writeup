"""Integration tests for standalone Round 1 competition submission."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

from prosperity_toolkit.backtesting.engine import BacktestEngine
from prosperity_toolkit.backtesting.replay import build_snapshots_from_dataframes
from prosperity_toolkit.competition.adapter import (
    CompetitionStrategyAdapter,
    CompetitionTraderProtocol,
)
from prosperity_toolkit.competition.submission import SubmissionValidator
from prosperity_toolkit.data.loader import DataLoader
from prosperity_toolkit.execution.simulator import ExecutionSimulator


def _instantiate_round1_trader() -> CompetitionTraderProtocol:
    traders_dir = str(Path("traders").resolve())
    if traders_dir not in sys.path:
        sys.path.insert(0, traders_dir)
    sub_path = Path("traders/round1/submission.py")
    spec = importlib.util.spec_from_file_location("round1_sub_test", sub_path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    trader: CompetitionTraderProtocol = mod.Trader()
    return trader


def test_round1_submission_ast_compliance() -> None:
    """Round 1 submission must pass AST validation with zero forbidden imports."""
    errors = SubmissionValidator.validate_file("traders/round1/submission.py")
    assert errors == []


def test_round1_submission_deterministic_replay_and_latency() -> None:
    """Round 1 Trader must run deterministically without limit breaches and < 1.0 ms/tick."""
    prices_df = DataLoader.load_prices_csv("tests/fixtures/prices_round_1_day_0_sample.csv")
    trades_df = DataLoader.load_trades_csv("tests/fixtures/trades_round_1_day_0_sample.csv")
    snapshots = build_snapshots_from_dataframes(prices_df, trades_df)

    limits = {"ASH_COATED_OSMIUM": 20, "INTARIAN_PEPPER_ROOT": 20}
    sim_a = ExecutionSimulator(position_limits=limits, fill_mode="queue_aware")
    sim_b = ExecutionSimulator(position_limits=limits, fill_mode="queue_aware")

    adapter_a = CompetitionStrategyAdapter(
        trader=_instantiate_round1_trader(),
    )
    adapter_b = CompetitionStrategyAdapter(
        trader=_instantiate_round1_trader(),
    )

    # reject_on_limit_breach=False ensures any position-limit breach raises immediately
    res_a = BacktestEngine(simulator=sim_a, reject_on_limit_breach=False).run(adapter_a, snapshots)
    res_b = BacktestEngine(simulator=sim_b, reject_on_limit_breach=False).run(adapter_b, snapshots)

    assert res_a.total_pnl == res_b.total_pnl
    assert res_a.equity_curve == res_b.equity_curve
    assert adapter_a.mean_latency_ms < 1.0

    persisted = json.loads(adapter_a.trader_data)
    assert "ASH_COATED_OSMIUM" in persisted
    assert "INTARIAN_PEPPER_ROOT" in persisted


def test_round1_submission_handles_malformed_trader_data() -> None:
    """Trader must recover gracefully if incoming traderData is malformed JSON."""
    trader = _instantiate_round1_trader()
    adapter = CompetitionStrategyAdapter(trader=trader)
    adapter.trader_data = "{corrupt_json"

    prices_df = DataLoader.load_prices_csv("tests/fixtures/prices_round_1_day_0_sample.csv")
    snapshots = build_snapshots_from_dataframes(prices_df)[:2]
    res = BacktestEngine().run(adapter, snapshots)
    assert len(res.equity_curve) == 2
