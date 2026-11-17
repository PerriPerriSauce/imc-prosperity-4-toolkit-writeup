"""Run systematic parameter optimization across defined strategy parameters."""

from __future__ import annotations

import argparse

from prosperity_toolkit.optimisation.search import GridSearchOptimizer


def main() -> int:
    """CLI to run parameter search."""
    parser = argparse.ArgumentParser(description="Run parameter optimization.")
    parser.add_argument(
        "--config",
        type=str,
        default="config/optimisation.yaml",
        help="Path to config file",
    )
    _ = parser.parse_args()

    sample_space = {"spread": [1, 2, 3], "inventory_limit": [5, 10]}
    grid = GridSearchOptimizer.generate_grid(sample_space)
    print(f"Generated {len(grid)} parameter combinations for search.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
