"""Command line interface for the Prosperity Toolkit."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence


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

    # Replay subcommand stub
    subparsers.add_parser("replay", help="Run historical market replay backtest")

    # Validate subcommand stub
    subparsers.add_parser("validate", help="Validate submission strategy file")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entrypoint."""
    parser = build_parser()
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])
    if args.command is None:
        parser.print_help()
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
