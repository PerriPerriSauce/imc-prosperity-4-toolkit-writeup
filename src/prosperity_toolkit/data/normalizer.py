"""Data normalizer transforming raw ingested tables into canonical structures."""

from __future__ import annotations

import pandas as pd


class DataNormalizer:
    """Normalizes raw market data frames into clean, typed parquet-ready frames."""

    @staticmethod
    def clean_prices(df: pd.DataFrame) -> pd.DataFrame:
        """Strip whitespace, cast types, and sort canonically."""
        cleaned = df.copy()
        cleaned.columns = [c.strip() for c in cleaned.columns]
        if "product" in cleaned.columns:
            cleaned["product"] = cleaned["product"].astype(str).str.strip()
        if "timestamp" in cleaned.columns:
            cleaned["timestamp"] = cleaned["timestamp"].astype(int)
        return cleaned.sort_values(by=["timestamp", "product"]).reset_index(drop=True)

    @staticmethod
    def clean_trades(df: pd.DataFrame) -> pd.DataFrame:
        """Standardize trade records."""
        cleaned = df.copy()
        cleaned.columns = [c.strip() for c in cleaned.columns]
        if "symbol" in cleaned.columns:
            cleaned["symbol"] = cleaned["symbol"].astype(str).str.strip()
        if "timestamp" in cleaned.columns:
            cleaned["timestamp"] = cleaned["timestamp"].astype(int)
        return cleaned.sort_values(by=["timestamp", "symbol"]).reset_index(drop=True)
