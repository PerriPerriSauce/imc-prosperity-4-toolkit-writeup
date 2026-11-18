"""Integration tests validating local raw Round 0-5 datasets against specs."""

from __future__ import annotations

from pathlib import Path

import pytest

from prosperity_toolkit.competition import PROSPERITY4_ROUND_DAYS, get_round_products
from prosperity_toolkit.data.loader import DataLoader

_RAW_ROOT = Path("data/raw/prosperity4")


@pytest.mark.parametrize("round_num", [0, 1, 2, 3, 4, 5])
def test_raw_round_representative_day_validates(round_num: int) -> None:
    """Verify representative raw CSV pair for each ingested round validates cleanly."""
    day = PROSPERITY4_ROUND_DAYS[round_num][-1]
    price_path = _RAW_ROOT / f"round{round_num}" / f"prices_round_{round_num}_day_{day}.csv"
    trade_path = _RAW_ROOT / f"round{round_num}" / f"trades_round_{round_num}_day_{day}.csv"
    if not price_path.exists() or not trade_path.exists():
        pytest.skip(f"Raw files for Round {round_num} Day {day} not present locally.")

    price_df, price_rep = DataLoader.ingest_csv(price_path)
    trade_df, trade_rep = DataLoader.ingest_csv(trade_path)

    assert price_rep.is_valid, f"Price errors: {price_rep.errors}"
    assert trade_rep.is_valid, f"Trade errors: {trade_rep.errors}"
    assert set(price_df["product"].unique()) == set(get_round_products(round_num))
    assert set(trade_df["symbol"].unique()) <= set(get_round_products(round_num))
