"""High-level data loading and ingestion interface."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from prosperity_toolkit.core.exceptions import DataValidationError
from prosperity_toolkit.data.normalizer import DataNormalizer
from prosperity_toolkit.data.parser import SemicolonCSVParser
from prosperity_toolkit.data.validation import (
    DataIntegrityValidator,
    ValidationReport,
    parse_round_day_from_filename,
)


class DataLoader:
    """Convenience loader orchestrating parsing, normalization, and validation."""

    def __init__(self, data_root: Path | str = "data") -> None:
        self.data_root = Path(data_root)

    @staticmethod
    def ingest_csv(
        filepath: Path | str,
        dataset_type: str | None = None,
    ) -> tuple[pd.DataFrame, ValidationReport]:
        """Load a raw CSV, normalize it, and return (DataFrame, ValidationReport)."""
        path = Path(filepath)
        inferred_type, _, _ = parse_round_day_from_filename(path)
        effective_type = dataset_type or inferred_type
        if effective_type not in {"prices", "trades", "observations"}:
            msg = (
                f"Cannot determine dataset_type ('prices', 'trades', or 'observations') "
                f"for {path}. Specify dataset_type explicitly."
            )
            raise DataValidationError(msg)

        if effective_type == "prices":
            raw_df = SemicolonCSVParser.parse_prices_csv(path)
            cleaned = DataNormalizer.clean_prices(raw_df)
        elif effective_type == "observations":
            raw_df = SemicolonCSVParser.parse_observations_csv(path)
            cleaned = DataNormalizer.clean_observations(raw_df)
        else:
            raw_df = SemicolonCSVParser.parse_trades_csv(path)
            cleaned = DataNormalizer.clean_trades(raw_df)

        report = DataIntegrityValidator.build_report(path, cleaned, effective_type)
        return cleaned, report

    @staticmethod
    def load_prices_csv(filepath: Path | str, check_continuity: bool = False) -> pd.DataFrame:
        """Load, normalize, and validate a prices CSV file from an explicit path."""
        df = SemicolonCSVParser.parse_prices_csv(filepath)
        cleaned = DataNormalizer.clean_prices(df)
        DataIntegrityValidator.validate_price_dataframe(cleaned)
        dup_count = DataIntegrityValidator.detect_price_duplicates(cleaned)
        if dup_count > 0:
            msg = f"Found {dup_count} duplicate (timestamp, product) rows in {filepath}"
            raise DataValidationError(msg)
        if check_continuity:
            DataIntegrityValidator.validate_timestamp_continuity(cleaned)
        return cleaned

    @staticmethod
    def load_trades_csv(filepath: Path | str) -> pd.DataFrame:
        """Load, normalize, and validate a trades CSV file from an explicit path."""
        df = SemicolonCSVParser.parse_trades_csv(filepath)
        cleaned = DataNormalizer.clean_trades(df)
        DataIntegrityValidator.validate_trades_dataframe(cleaned)
        return cleaned

    @staticmethod
    def load_observations_csv(
        filepath: Path | str,
        check_continuity: bool = False,
    ) -> pd.DataFrame:
        """Load, normalize, and validate an observations CSV file from an explicit path."""
        df = SemicolonCSVParser.parse_observations_csv(filepath)
        cleaned = DataNormalizer.clean_observations(df)
        DataIntegrityValidator.validate_observations_dataframe(cleaned)
        if check_continuity:
            DataIntegrityValidator.validate_timestamp_continuity(cleaned)
        return cleaned

    def _resolve_raw_file(self, round_num: int, filename: str) -> Path:
        candidates = [
            self.data_root / "raw" / "prosperity4" / f"round{round_num}" / filename,
            self.data_root / "raw" / f"round_{round_num}" / filename,
            self.data_root / "raw" / f"round{round_num}" / filename,
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return candidates[0]

    def load_day_prices(self, round_num: int, day_num: int) -> pd.DataFrame:
        """Load and validate prices for a given round and day."""
        filename = f"prices_round_{round_num}_day_{day_num}.csv"
        return self.load_prices_csv(self._resolve_raw_file(round_num, filename))

    def load_day_trades(self, round_num: int, day_num: int) -> pd.DataFrame:
        """Load and validate trades for a given round and day."""
        filename = f"trades_round_{round_num}_day_{day_num}.csv"
        return self.load_trades_csv(self._resolve_raw_file(round_num, filename))

    def load_day_observations(self, round_num: int, day_num: int) -> pd.DataFrame:
        """Load and validate observations for a given round and day."""
        filename = f"observations_round_{round_num}_day_{day_num}.csv"
        return self.load_observations_csv(self._resolve_raw_file(round_num, filename))
