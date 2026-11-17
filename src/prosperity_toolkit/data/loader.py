"""High-level data loading interface."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from prosperity_toolkit.data.normalizer import DataNormalizer
from prosperity_toolkit.data.parser import SemicolonCSVParser
from prosperity_toolkit.data.validation import DataIntegrityValidator


class DataLoader:
    """Convenience loader orchestrating parsing, normalization, and validation."""

    def __init__(self, data_root: Path | str = "data") -> None:
        self.data_root = Path(data_root)

    def load_day_prices(self, round_num: int, day_num: int) -> pd.DataFrame:
        """Load and validate prices for a given round and day."""
        filename = f"prices_round_{round_num}_day_{day_num}.csv"
        raw_path = self.data_root / "raw" / f"round_{round_num}" / filename

        # Fallback to alternate directory shapes if present
        if not raw_path.exists():
            raw_path = self.data_root / "raw" / f"round{round_num}" / filename

        df = SemicolonCSVParser.parse_prices_csv(raw_path)
        cleaned = DataNormalizer.clean_prices(df)
        DataIntegrityValidator.validate_price_dataframe(cleaned)
        return cleaned
