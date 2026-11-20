"""Data validation checks enforcing monotonicity, non-crossing books, and continuity."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from prosperity_toolkit.core.exceptions import DataValidationError
from prosperity_toolkit.data.schemas import (
    OBSERVATION_CSV_COLUMNS,
    OBSERVATION_REQUIRED_COLUMNS,
    PRICE_CSV_COLUMNS,
    PRICE_REQUIRED_COLUMNS,
    TRADE_CSV_COLUMNS,
    TRADE_REQUIRED_COLUMNS,
)

_FILENAME_PATTERN = re.compile(
    r"^(prices|trades|observations)_round_(\d+)_day_(-?\d+).*\.csv$",
)


@dataclass(frozen=True, slots=True)
class ValidationReport:
    """Structured report summarizing ingestion validation and integrity checks."""

    filepath: str
    dataset_type: str
    round_num: int | None
    day_num: int | None
    sha256: str
    row_count: int
    duplicate_count: int
    missing_value_counts: dict[str, int] = field(default_factory=dict)
    symbols: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """Return True if zero validation errors were recorded."""
        return len(self.errors) == 0


def compute_sha256(filepath: Path | str) -> str:
    """Compute SHA-256 hex digest of a file without modifying it."""
    path = Path(filepath)
    hasher = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def parse_round_day_from_filename(
    filepath: Path | str,
) -> tuple[str | None, int | None, int | None]:
    """Extract (dataset_type, round_num, day_num) from standard Prosperity CSV filenames."""
    name = Path(filepath).name
    match = _FILENAME_PATTERN.match(name)
    if not match:
        return None, None, None
    return match.group(1), int(match.group(2)), int(match.group(3))


class DataIntegrityValidator:
    """Validates structural and economic integrity of historical market data."""

    @staticmethod
    def detect_price_duplicates(df: pd.DataFrame) -> int:
        """Count duplicate (timestamp, product) rows in a prices DataFrame."""
        if "timestamp" not in df.columns or "product" not in df.columns:
            return 0
        return int(df.duplicated(subset=["timestamp", "product"]).sum())

    @staticmethod
    def detect_trade_duplicates(df: pd.DataFrame) -> int:
        """Count exact duplicate trade records."""
        cols = ["timestamp", "buyer", "seller", "symbol", "price", "quantity"]
        subset = [c for c in cols if c in df.columns]
        if not subset:
            return 0
        return int(df.duplicated(subset=subset).sum())

    @staticmethod
    def detect_observation_duplicates(df: pd.DataFrame) -> int:
        """Count duplicate timestamp rows in an observations DataFrame."""
        if "timestamp" not in df.columns:
            return 0
        return int(df.duplicated(subset=["timestamp"]).sum())

    @staticmethod
    def validate_price_dataframe(df: pd.DataFrame) -> None:
        """Validate price and order book depth table."""
        unexpected = sorted(set(df.columns) - set(PRICE_CSV_COLUMNS))
        if unexpected:
            msg = f"Unexpected columns in price dataframe: {unexpected}"
            raise DataValidationError(msg)

        for col in PRICE_REQUIRED_COLUMNS:
            if col not in df.columns:
                msg = f"Missing required column in price dataframe: {col}"
                raise DataValidationError(msg)

        if df.empty:
            msg = "Price dataframe cannot be empty"
            raise DataValidationError(msg)

        for col in PRICE_REQUIRED_COLUMNS:
            if df[col].isna().any():
                msg = f"Null values found in required price column: {col}"
                raise DataValidationError(msg)

        if not pd.api.types.is_numeric_dtype(df["timestamp"]):
            msg = "Column 'timestamp' must be numeric"
            raise DataValidationError(msg)

        if not pd.api.types.is_numeric_dtype(df["mid_price"]):
            msg = "Column 'mid_price' must be numeric"
            raise DataValidationError(msg)

        # Check negative mid-price; mid_price == 0 is only valid on empty books
        if (df["mid_price"] < 0).any():
            msg = "Found negative mid_price entries in market data"
            raise DataValidationError(msg)

        zero_mid = df["mid_price"] == 0
        if zero_mid.any():
            has_bid = (
                df["bid_price_1"].notna()
                if "bid_price_1" in df.columns
                else pd.Series(False, index=df.index)
            )
            has_ask = (
                df["ask_price_1"].notna()
                if "ask_price_1" in df.columns
                else pd.Series(False, index=df.index)
            )
            if (zero_mid & (has_bid | has_ask)).any():
                msg = "Found mid_price == 0.0 on non-empty order book"
                raise DataValidationError(msg)

        # Check non-negative book prices (0 permitted on deep-OTM call bids)
        for side in ("bid", "ask"):
            for lvl in (1, 2, 3):
                price_col = f"{side}_price_{lvl}"
                if price_col in df.columns:
                    present = df[price_col].notna()
                    if (df[present][price_col] < 0).any():
                        msg = f"Negative quote price detected in {price_col}"
                        raise DataValidationError(msg)

        # Check spread positivity where top-level bid and ask are both present
        if "bid_price_1" in df.columns and "ask_price_1" in df.columns:
            valid_both = df["bid_price_1"].notna() & df["ask_price_1"].notna()
            crossed = df[valid_both]["bid_price_1"] >= df[valid_both]["ask_price_1"]
            if crossed.any():
                msg = "Crossed or inverted order book detected (bid_1 >= ask_1)"
                raise DataValidationError(msg)

        # Check L2/L3 bid price ladder monotonicity (bid_1 > bid_2 > bid_3)
        for lvl in (1, 2):
            hi_col = f"bid_price_{lvl}"
            lo_col = f"bid_price_{lvl + 1}"
            if hi_col in df.columns and lo_col in df.columns:
                both = df[hi_col].notna() & df[lo_col].notna()
                if (df[both][hi_col] <= df[both][lo_col]).any():
                    msg = f"Non-monotonic bid ladder detected: {hi_col} <= {lo_col}"
                    raise DataValidationError(msg)

        # Check L2/L3 ask price ladder monotonicity (ask_1 < ask_2 < ask_3)
        for lvl in (1, 2):
            lo_col = f"ask_price_{lvl}"
            hi_col = f"ask_price_{lvl + 1}"
            if lo_col in df.columns and hi_col in df.columns:
                both = df[lo_col].notna() & df[hi_col].notna()
                if (df[both][lo_col] >= df[both][hi_col]).any():
                    msg = f"Non-monotonic ask ladder detected: {lo_col} >= {hi_col}"
                    raise DataValidationError(msg)

        # Check positive book volumes where present
        for side in ("bid", "ask"):
            for lvl in (1, 2, 3):
                vol_col = f"{side}_volume_{lvl}"
                if vol_col in df.columns:
                    present = df[vol_col].notna()
                    if (df[present][vol_col] <= 0).any():
                        msg = f"Non-positive volume detected in {vol_col}"
                        raise DataValidationError(msg)

    @staticmethod
    def validate_trades_dataframe(df: pd.DataFrame) -> None:
        """Validate public trades table (0.0 trade prices permitted for deep-OTM bids)."""
        unexpected = sorted(set(df.columns) - set(TRADE_CSV_COLUMNS))
        if unexpected:
            msg = f"Unexpected columns in trades dataframe: {unexpected}"
            raise DataValidationError(msg)

        for col in TRADE_REQUIRED_COLUMNS:
            if col not in df.columns:
                msg = f"Missing required column in trades dataframe: {col}"
                raise DataValidationError(msg)

        if df.empty:
            return

        for col in TRADE_REQUIRED_COLUMNS:
            if df[col].isna().any():
                msg = f"Null values found in required trades column: {col}"
                raise DataValidationError(msg)

        if not pd.api.types.is_numeric_dtype(df["price"]):
            msg = "Column 'price' in trades dataframe must be numeric"
            raise DataValidationError(msg)

        if not pd.api.types.is_numeric_dtype(df["quantity"]):
            msg = "Column 'quantity' in trades dataframe must be numeric"
            raise DataValidationError(msg)

        if (df["price"] < 0).any():
            msg = "Found negative trade price in trades dataframe"
            raise DataValidationError(msg)

        if (df["quantity"] <= 0).any():
            msg = "Found non-positive trade quantity in trades dataframe"
            raise DataValidationError(msg)

    @staticmethod
    def validate_observations_dataframe(df: pd.DataFrame) -> None:
        """Validate conversion and environmental observations table."""
        unexpected = sorted(set(df.columns) - set(OBSERVATION_CSV_COLUMNS))
        if unexpected:
            msg = f"Unexpected columns in observations dataframe: {unexpected}"
            raise DataValidationError(msg)

        for col in OBSERVATION_REQUIRED_COLUMNS:
            if col not in df.columns:
                msg = f"Missing required column in observations dataframe: {col}"
                raise DataValidationError(msg)

        if df.empty:
            msg = "Observations dataframe cannot be empty"
            raise DataValidationError(msg)

        for col in df.columns:
            if df[col].isna().any():
                msg = f"Null values found in observations column: {col}"
                raise DataValidationError(msg)
            if not pd.api.types.is_numeric_dtype(df[col]):
                msg = f"Column '{col}' in observations dataframe must be numeric"
                raise DataValidationError(msg)

        if (df["bidPrice"] < 0).any() or (df["askPrice"] < 0).any():
            msg = "Negative quote price in observations dataframe"
            raise DataValidationError(msg)

        if (df["bidPrice"] >= df["askPrice"]).any():
            msg = "Crossed observation quote detected (bidPrice >= askPrice)"
            raise DataValidationError(msg)

    @staticmethod
    def validate_timestamp_continuity(df: pd.DataFrame, expected_step: int = 100) -> None:
        """Verify that timestamps advance in uniform discrete intervals."""
        if "timestamp" not in df.columns:
            msg = "Cannot validate continuity: missing 'timestamp' column"
            raise DataValidationError(msg)

        if "product" in df.columns:
            groups = df.groupby("product")
        else:
            groups = [("ALL", df)]

        for product, group in groups:
            sorted_ts = group["timestamp"].sort_values(kind="mergesort")
            diffs = sorted_ts.diff().dropna()
            if not diffs.empty and not (diffs == expected_step).all():
                bad = diffs[diffs != expected_step]
                msg = (
                    f"Timestamp discontinuity or duplicate detected for product {product}: "
                    f"expected step {expected_step}, observed irregular diffs:\n{bad.head()}"
                )
                raise DataValidationError(msg)

    @classmethod
    def build_report(
        cls,
        filepath: Path | str,
        df: pd.DataFrame,
        dataset_type: str,
    ) -> ValidationReport:
        """Run all integrity checks and produce a structured ValidationReport."""
        path = Path(filepath)
        parsed_type, round_num, day_num = parse_round_day_from_filename(path)
        effective_type = dataset_type or parsed_type or "trades"
        sha = compute_sha256(path)
        missing_counts = {str(col): int(df[col].isna().sum()) for col in df.columns}
        errors: list[str] = []
        warnings: list[str] = []

        if effective_type == "prices":
            dup_count = cls.detect_price_duplicates(df)
            symbols = (
                sorted(df["product"].astype(str).unique().tolist())
                if "product" in df.columns
                else []
            )
            try:
                cls.validate_price_dataframe(df)
            except DataValidationError as err:
                errors.append(str(err))
            if dup_count > 0:
                errors.append(f"Found {dup_count} duplicate (timestamp, product) rows")
            if "mid_price" in df.columns:
                zero_count = int((df["mid_price"] == 0).sum())
                if zero_count > 0:
                    warnings.append(f"Found {zero_count} empty-book rows with mid_price == 0.0")
        elif effective_type == "observations":
            dup_count = cls.detect_observation_duplicates(df)
            symbols = []
            try:
                cls.validate_observations_dataframe(df)
            except DataValidationError as err:
                errors.append(str(err))
            if dup_count > 0:
                errors.append(f"Found {dup_count} duplicate timestamp rows in observations")
        else:
            dup_count = cls.detect_trade_duplicates(df)
            symbols = (
                sorted(df["symbol"].astype(str).unique().tolist())
                if "symbol" in df.columns
                else []
            )
            try:
                cls.validate_trades_dataframe(df)
            except DataValidationError as err:
                errors.append(str(err))
            if dup_count > 0:
                warnings.append(f"Found {dup_count} exact duplicate trade records")
            if "price" in df.columns and not df.empty:
                zero_price_trades = int((df["price"] == 0).sum())
                if zero_price_trades > 0:
                    warnings.append(
                        f"Found {zero_price_trades} zero-price trade records (deep-OTM zero bid)",
                    )

        return ValidationReport(
            filepath=str(path),
            dataset_type=effective_type,
            round_num=round_num,
            day_num=day_num,
            sha256=sha,
            row_count=len(df),
            duplicate_count=dup_count,
            missing_value_counts=missing_counts,
            symbols=symbols,
            errors=errors,
            warnings=warnings,
        )
