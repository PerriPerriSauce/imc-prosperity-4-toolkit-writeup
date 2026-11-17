"""Command-line utility to run backtest replay on historical data."""

from __future__ import annotations

import argparse

from prosperity_toolkit.backtesting.engine import BacktestEngine
from prosperity_toolkit.strategies.baseline import NoOpBaselineStrategy
from prosperity_toolkit.visualisation.dashboard import ResearchDashboard


def main() -> int:
    """CLI to run a backtest."""
    parser = argparse.ArgumentParser(description="Run backtest replay.")
    parser.add_argument("--strategy", type=str, default="noop", help="Strategy identifier")
    _ = parser.parse_args()

    engine = BacktestEngine()
    strategy = NoOpBaselineStrategy()
    result = engine.run(strategy, snapshots=[])

    print("=== Backtest Execution Complete ===")
    print(ResearchDashboard.render_markdown_summary(result.summary()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
