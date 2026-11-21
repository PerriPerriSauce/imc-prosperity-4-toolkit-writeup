"""Command line interface for the Prosperity Toolkit."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import cast

from prosperity_toolkit.backtesting.engine import BacktestEngine
from prosperity_toolkit.backtesting.replay import build_snapshots_from_dataframes
from prosperity_toolkit.competition import (
    CompetitionStrategyAdapter,
    SubmissionValidator,
    get_round_position_limits,
    load_competition_trader,
)
from prosperity_toolkit.data.loader import DataLoader
from prosperity_toolkit.execution.simulator import ExecutionSimulator, FillMode
from prosperity_toolkit.simulation import (
    AssetScenarioConfig,
    MonteCarloEngine,
    OrnsteinUhlenbeckParams,
)
from prosperity_toolkit.strategies.base import BaseStrategy
from prosperity_toolkit.strategies.baseline import NoOpBaselineStrategy
from prosperity_toolkit.visualisation.dashboard import ResearchDashboard


def build_parser() -> argparse.ArgumentParser:
    """Construct command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog="prosperity-toolkit",
        description="IMC Prosperity 4 Quantitative Trading Toolkit and Backtesting Framework.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.1.0",
        help="Show program version number.",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    replay_parser = subparsers.add_parser("replay", help="Run historical market replay backtest")
    replay_parser.add_argument(
        "--prices",
        type=Path,
        required=True,
        help="Path to semicolon-delimited prices CSV file.",
    )
    replay_parser.add_argument(
        "--trades",
        type=Path,
        default=None,
        help="Optional path to semicolon-delimited trades CSV file.",
    )
    replay_parser.add_argument(
        "--round",
        type=int,
        default=None,
        help="Optional Prosperity 4 round (0-5) to load official product limits.",
    )
    replay_parser.add_argument(
        "--limit",
        type=int,
        default=80,
        help="Fallback position limit per product when --round is omitted (default: 80).",
    )
    replay_parser.add_argument(
        "--submission",
        type=Path,
        default=None,
        help="Optional path to standalone submission.py script defining Trader.",
    )
    replay_parser.add_argument(
        "--fill-mode",
        choices=["conservative", "queue_aware", "touch"],
        default="queue_aware",
        help="Simulator passive fill matching mode (default: queue_aware).",
    )

    validate_parser = subparsers.add_parser("validate", help="Validate submission strategy file")
    validate_parser.add_argument(
        "filepath",
        type=Path,
        help="Path to standalone submission.py script.",
    )

    mc_parser = subparsers.add_parser("mc", help="Run Monte Carlo baseline simulation")
    mc_parser.add_argument("--sessions", type=int, default=50, help="Number of synthetic sessions")
    mc_parser.add_argument("--steps", type=int, default=200, help="Ticks per synthetic session")
    mc_parser.add_argument("--seed", type=int, default=42, help="Random seed")

    return parser


def _run_replay(
    prices_path: Path,
    trades_path: Path | None,
    default_limit: int,
    round_num: int | None = None,
    submission_path: Path | None = None,
    fill_mode: FillMode = "queue_aware",
) -> int:
    """Execute historical replay from CSV inputs."""
    prices_df = DataLoader.load_prices_csv(prices_path)
    trades_df = DataLoader.load_trades_csv(trades_path) if trades_path is not None else None

    snapshots = build_snapshots_from_dataframes(prices_df, trades_df)
    symbols = {str(p) for p in prices_df["product"].unique()}
    if round_num is not None:
        official = get_round_position_limits(round_num)
        limits = {sym: official.get(sym, default_limit) for sym in symbols}
    else:
        limits = dict.fromkeys(symbols, default_limit)

    simulator = ExecutionSimulator(position_limits=limits, fill_mode=fill_mode)
    engine = BacktestEngine(simulator=simulator)
    strategy: BaseStrategy
    if submission_path is not None:
        trader = load_competition_trader(submission_path)
        strategy = CompetitionStrategyAdapter(trader, name=submission_path.parent.name)
    else:
        strategy = NoOpBaselineStrategy()
    result = engine.run(strategy, snapshots=snapshots)

    print(
        f"Replayed {len(snapshots)} ticks across {len(symbols)} symbols "
        f"(strategy={result.strategy_name}, fill_mode={fill_mode}).",
    )
    print(ResearchDashboard.render_markdown_summary(result.summary()))
    return 0


def _run_validate(filepath: Path) -> int:
    """Validate a standalone submission script."""
    errors = SubmissionValidator.validate_file(filepath)
    if errors:
        print("Submission validation FAILED:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1
    print(f"SUCCESS: {filepath} passed submission validation.")
    return 0


def _run_mc(sessions: int, steps: int, seed: int) -> int:
    """Run a baseline Monte Carlo simulation."""
    asset = AssetScenarioConfig(
        symbol="SYNTHETIC_OU",
        process=OrnsteinUhlenbeckParams(mu=10000.0, theta=0.05, sigma=2.0),
    )
    mc_engine = MonteCarloEngine(assets=[asset])
    summary = mc_engine.run(
        strategy_factory=NoOpBaselineStrategy,
        n_sessions=sessions,
        n_steps=steps,
        seed=seed,
    )
    print(f"Simulated {sessions} synthetic sessions ({steps} ticks each, seed={seed}).")
    print(ResearchDashboard.render_markdown_summary(summary.summary()))
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entrypoint."""
    parser = build_parser()
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])
    if args.command is None:
        parser.print_help()
        return 0
    if args.command == "replay":
        return _run_replay(
            args.prices,
            args.trades,
            args.limit,
            round_num=args.round,
            submission_path=args.submission,
            fill_mode=cast(FillMode, args.fill_mode),
        )
    if args.command == "validate":
        return _run_validate(args.filepath)
    if args.command == "mc":
        return _run_mc(args.sessions, args.steps, args.seed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
