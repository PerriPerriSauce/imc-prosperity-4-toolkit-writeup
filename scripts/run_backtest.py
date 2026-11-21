"""Command-line utility to run backtest replay on historical data."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import cast

from prosperity_toolkit.backtesting.engine import BacktestEngine
from prosperity_toolkit.backtesting.replay import build_snapshots_from_dataframes
from prosperity_toolkit.competition import (
    CompetitionStrategyAdapter,
    get_round_position_limits,
    load_competition_trader,
)
from prosperity_toolkit.data.loader import DataLoader
from prosperity_toolkit.execution.simulator import ExecutionSimulator, FillMode
from prosperity_toolkit.market.market_state import MarketStateSnapshot
from prosperity_toolkit.strategies.base import BaseStrategy
from prosperity_toolkit.strategies.baseline import NoOpBaselineStrategy
from prosperity_toolkit.visualisation.dashboard import ResearchDashboard


def main(argv: list[str] | None = None) -> int:
    """CLI to run a backtest."""
    parser = argparse.ArgumentParser(description="Run backtest replay.")
    parser.add_argument("--prices", type=Path, default=None, help="Path to prices CSV")
    parser.add_argument("--trades", type=Path, default=None, help="Path to trades CSV")
    parser.add_argument(
        "--round",
        type=int,
        default=None,
        help="Optional Prosperity 4 round (0-5) for official position limits",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=80,
        help="Fallback position limit per product when --round is omitted",
    )
    parser.add_argument(
        "--submission",
        type=Path,
        default=None,
        help="Optional standalone submission.py path defining Trader",
    )
    parser.add_argument(
        "--fill-mode",
        choices=["conservative", "queue_aware", "touch"],
        default="queue_aware",
        help="Passive matching mode (default: queue_aware)",
    )
    args = parser.parse_args(argv)

    snapshots: list[MarketStateSnapshot] = []
    limits: dict[str, int] = {}

    if args.prices is not None:
        prices_df = DataLoader.load_prices_csv(args.prices)
        trades_df = DataLoader.load_trades_csv(args.trades) if args.trades is not None else None
        snapshots = build_snapshots_from_dataframes(prices_df, trades_df)
        symbols = [str(p) for p in prices_df["product"].unique()]
        if args.round is not None:
            official = get_round_position_limits(args.round)
            limits = {sym: official.get(sym, args.limit) for sym in symbols}
        else:
            limits = {sym: args.limit for sym in symbols}

    fill_mode = cast(FillMode, args.fill_mode)
    simulator = ExecutionSimulator(position_limits=limits, fill_mode=fill_mode)
    engine = BacktestEngine(simulator=simulator)
    strategy: BaseStrategy
    if args.submission is not None:
        trader = load_competition_trader(args.submission)
        strategy = CompetitionStrategyAdapter(trader, name=args.submission.parent.name)
    else:
        strategy = NoOpBaselineStrategy()
    result = engine.run(strategy, snapshots=snapshots)

    print("=== Backtest Execution Complete ===")
    print(ResearchDashboard.render_markdown_summary(result.summary()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
