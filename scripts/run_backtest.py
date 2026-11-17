"""Command-line utility to run backtest replay on historical data."""

from __future__ import annotations

import argparse
from pathlib import Path

from prosperity_toolkit.backtesting.engine import BacktestEngine
from prosperity_toolkit.backtesting.replay import build_snapshots_from_dataframes
from prosperity_toolkit.data.loader import DataLoader
from prosperity_toolkit.execution.simulator import ExecutionSimulator
from prosperity_toolkit.market.market_state import MarketStateSnapshot
from prosperity_toolkit.strategies.baseline import NoOpBaselineStrategy
from prosperity_toolkit.visualisation.dashboard import ResearchDashboard


def main() -> int:
    """CLI to run a backtest."""
    parser = argparse.ArgumentParser(description="Run backtest replay.")
    parser.add_argument("--prices", type=Path, default=None, help="Path to prices CSV")
    parser.add_argument("--trades", type=Path, default=None, help="Path to trades CSV")
    parser.add_argument("--limit", type=int, default=20, help="Position limit per product")
    args = parser.parse_args()

    snapshots: list[MarketStateSnapshot] = []
    limits: dict[str, int] = {}

    if args.prices is not None:
        prices_df = DataLoader.load_prices_csv(args.prices)
        trades_df = DataLoader.load_trades_csv(args.trades) if args.trades is not None else None
        snapshots = build_snapshots_from_dataframes(prices_df, trades_df)
        limits = {str(p): args.limit for p in prices_df["product"].unique()}

    simulator = ExecutionSimulator(position_limits=limits)
    engine = BacktestEngine(simulator=simulator)
    strategy = NoOpBaselineStrategy()
    result = engine.run(strategy, snapshots=snapshots)

    print("=== Backtest Execution Complete ===")
    print(ResearchDashboard.render_markdown_summary(result.summary()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
