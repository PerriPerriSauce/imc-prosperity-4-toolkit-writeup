"""Data normalizer transforming raw ingested tables into canonical structures."""

from __future__ import annotations

import pandas as pd


class DataNormalizer:
    """Normalizes raw market data frames into clean, typed parquet-ready frames."""

    @staticmethod
    def _strip_preserve_na(series: pd.Series[object]) -> pd.Series[object]:
        """Strip whitespace from non-null string entries while preserving NaNs."""
        return series.where(series.isna(), series.astype(str).str.strip())

    @classmethod
    def clean_prices(cls, df: pd.DataFrame) -> pd.DataFrame:
        """Strip whitespace, cast types, and sort canonically using stable mergesort."""
        cleaned = df.copy()
        cleaned.columns = [c.strip() for c in cleaned.columns]
        if "product" in cleaned.columns:
            cleaned["product"] = cls._strip_preserve_na(cleaned["product"])
        if "timestamp" in cleaned.columns:
            cleaned["timestamp"] = cleaned["timestamp"].astype(int)
        return cleaned.sort_values(
            by=["timestamp", "product"],
            kind="mergesort",
        ).reset_index(drop=True)

    @classmethod
    def clean_trades(cls, df: pd.DataFrame) -> pd.DataFrame:
        """Standardize trade records while preserving within-timestamp tape order."""
        cleaned = df.copy()
        cleaned.columns = [c.strip() for c in cleaned.columns]
        if "symbol" in cleaned.columns:
            cleaned["symbol"] = cls._strip_preserve_na(cleaned["symbol"])
        if "timestamp" in cleaned.columns:
            cleaned["timestamp"] = cleaned["timestamp"].astype(int)
        return cleaned.sort_values(
            by=["timestamp", "symbol"],
            kind="mergesort",
        ).reset_index(drop=True)

    @staticmethod
    def clean_observations(df: pd.DataFrame) -> pd.DataFrame:
        """Standardize environmental and conversion observation records."""
        cleaned = df.copy()
        cleaned.columns = [c.strip() for c in cleaned.columns]
        if "timestamp" in cleaned.columns:
            cleaned["timestamp"] = cleaned["timestamp"].astype(int)
        for col in cleaned.columns:
            if col != "timestamp":
                cleaned[col] = pd.to_numeric(cleaned[col], errors="coerce")
        return cleaned.sort_values(
            by=["timestamp"],
            kind="mergesort",
        ).reset_index(drop=True)
