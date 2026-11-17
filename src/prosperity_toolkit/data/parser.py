"""CSV and raw file parsing routines for IMC Prosperity semicolon formats."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from prosperity_toolkit.core.exceptions import DataValidationError


class SemicolonCSVParser:
    """Parser for Prosperity semicolon-delimited CSV formats."""

    @staticmethod
    def parse_prices_csv(filepath: Path | str) -> pd.DataFrame:
        """Parse raw price and book depth CSV file."""
        path = Path(filepath)
        if not path.is_file():
            msg = f"Prices CSV file not found: {path}"
            raise FileNotFoundError(msg)

        try:
            df = pd.read_csv(path, sep=";")
        except Exception as err:
            msg = f"Failed to parse semicolon CSV {path}: {err}"
            raise DataValidationError(msg) from err

        return df

    @staticmethod
    def parse_trades_csv(filepath: Path | str) -> pd.DataFrame:
        """Parse raw public trades CSV file."""
        path = Path(filepath)
        if not path.is_file():
            msg = f"Trades CSV file not found: {path}"
            raise FileNotFoundError(msg)

        try:
            df = pd.read_csv(path, sep=";")
        except Exception as err:
            msg = f"Failed to parse semicolon CSV {path}: {err}"
            raise DataValidationError(msg) from err

        return df
