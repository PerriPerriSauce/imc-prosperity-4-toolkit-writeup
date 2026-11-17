"""Data validation checks enforcing monotonicity, non-crossing books, and continuity."""

from __future__ import annotations

import pandas as pd

from prosperity_toolkit.core.exceptions import DataValidationError


class DataIntegrityValidator:
    """Validates structural and economic integrity of historical market data."""

    @staticmethod
    def validate_price_dataframe(df: pd.DataFrame) -> None:
        """Validate price and order book depth table."""
        required = ["timestamp", "product", "mid_price"]
        for col in required:
            if col not in df.columns:
                msg = f"Missing required column in price dataframe: {col}"
                raise DataValidationError(msg)

        if df.empty:
            msg = "Price dataframe cannot be empty"
            raise DataValidationError(msg)

        # Check positive mid-price
        if (df["mid_price"] <= 0).any():
            msg = "Found non-positive mid_price entries in market data"
            raise DataValidationError(msg)

        # Check spread positivity where top-level bid and ask are both present
        if "bid_price_1" in df.columns and "ask_price_1" in df.columns:
            valid_both = df["bid_price_1"].notna() & df["ask_price_1"].notna()
            crossed = df[valid_both]["bid_price_1"] >= df[valid_both]["ask_price_1"]
            if crossed.any():
                msg = "Crossed or inverted order book detected (bid_1 >= ask_1)"
                raise DataValidationError(msg)

    @staticmethod
    def validate_timestamp_continuity(df: pd.DataFrame, expected_step: int = 100) -> None:
        """Verify that timestamps advance in uniform discrete intervals."""
        if "timestamp" not in df.columns:
            msg = "Cannot validate continuity: missing 'timestamp' column"
            raise DataValidationError(msg)

        for product, group in df.groupby("product"):
            sorted_ts = group["timestamp"].sort_values().drop_duplicates()
            diffs = sorted_ts.diff().dropna()
            if not diffs.empty and not (diffs == expected_step).all():
                bad = diffs[diffs != expected_step]
                msg = (
                    f"Timestamp discontinuity detected for product {product}: "
                    f"expected step {expected_step}, observed irregular diffs:\n{bad.head()}"
                )
                raise DataValidationError(msg)
