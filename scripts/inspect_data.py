"""Inspect raw or processed market data files for basic statistics and data integrity."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from prosperity_toolkit.data.parser import SemicolonCSVParser
from prosperity_toolkit.data.validation import DataIntegrityValidator


def main() -> int:
    """CLI to inspect data."""
    parser = argparse.ArgumentParser(description="Inspect Prosperity market CSV file.")
    parser.add_argument("filepath", type=Path, help="Path to semicolon-delimited CSV")
    args = parser.parse_args()

    if not args.filepath.is_file():
        print(f"Error: file not found: {args.filepath}", file=sys.stderr)
        return 1

    try:
        df = SemicolonCSVParser.parse_prices_csv(args.filepath)
        DataIntegrityValidator.validate_price_dataframe(df)
        print(f"Successfully loaded and validated {args.filepath}")
        print(f"Rows: {len(df)}, Columns: {list(df.columns)}")
        print(df.head())
        return 0
    except Exception as err:
        print(f"Validation failed: {err}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
