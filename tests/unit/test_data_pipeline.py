"""Unit tests for CSV parsing, normalization, and data integrity validation."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from prosperity_toolkit.core.exceptions import DataValidationError
from prosperity_toolkit.data.loader import DataLoader
from prosperity_toolkit.data.validation import (
    DataIntegrityValidator,
    compute_sha256,
    parse_round_day_from_filename,
)


def test_load_synthetic_round1_fixtures() -> None:
    """Verify loading and validation of synthetic Round 1 price and trade fixtures."""
    prices_path = Path("tests/fixtures/prices_round_1_day_0_sample.csv")
    trades_path = Path("tests/fixtures/trades_round_1_day_0_sample.csv")

    prices_df, price_rep = DataLoader.ingest_csv(prices_path)
    trades_df, trade_rep = DataLoader.ingest_csv(trades_path)

    assert len(prices_df) == 20
    assert price_rep.is_valid
    assert price_rep.round_num == 1
    assert price_rep.day_num == 0
    assert len(price_rep.sha256) == 64
    assert set(prices_df["product"].unique()) == {
        "ASH_COATED_OSMIUM",
        "INTARIAN_PEPPER_ROOT",
    }
    assert len(trades_df) == 7
    assert trade_rep.is_valid


def test_parse_round_day_negative_days() -> None:
    """Verify filename parsing handles negative tutorial/pre-round day numbers."""
    dtype, rnd, day = parse_round_day_from_filename("prices_round_0_day_-2.csv")
    assert dtype == "prices"
    assert rnd == 0
    assert day == -2


def test_empty_book_zero_mid_price_allowed_with_warning(tmp_path: Path) -> None:
    """Empty book rows with mid_price == 0.0 should pass validation with a warning."""
    csv_path = tmp_path / "prices_round_1_day_0.csv"
    csv_path.write_text(
        "day;timestamp;product;bid_price_1;bid_volume_1;ask_price_1;ask_volume_1;mid_price\n"
        "0;0;OSMIUM;;;;;0.0\n",
        encoding="utf-8",
    )
    _, report = DataLoader.ingest_csv(csv_path)
    assert report.is_valid
    assert any("empty-book rows" in w for w in report.warnings)


def test_non_empty_book_zero_mid_price_rejected() -> None:
    """Non-empty book with mid_price == 0.0 must fail validation."""
    df = pd.DataFrame({
        "timestamp": [0],
        "product": ["OSMIUM"],
        "bid_price_1": [99],
        "ask_price_1": [101],
        "mid_price": [0.0],
    })
    with pytest.raises(DataValidationError, match="mid_price == 0.0 on non-empty"):
        DataIntegrityValidator.validate_price_dataframe(df)


def test_null_required_column_rejected() -> None:
    """Missing values in required columns must fail validation."""
    df = pd.DataFrame({
        "timestamp": [0],
        "product": ["OSMIUM"],
        "mid_price": [None],
    })
    with pytest.raises(DataValidationError, match="Null values found"):
        DataIntegrityValidator.validate_price_dataframe(df)


def test_duplicate_price_rows_flagged_invalid(tmp_path: Path) -> None:
    """Duplicate (timestamp, product) rows must be detected and flagged as invalid."""
    csv_path = tmp_path / "prices_round_1_day_0.csv"
    csv_path.write_text(
        "day;timestamp;product;bid_price_1;bid_volume_1;ask_price_1;ask_volume_1;mid_price\n"
        "0;0;OSMIUM;99;5;101;5;100.0\n"
        "0;0;OSMIUM;99;5;101;5;100.0\n",
        encoding="utf-8",
    )
    _, report = DataLoader.ingest_csv(csv_path)
    assert not report.is_valid
    assert report.duplicate_count == 1
    assert len(compute_sha256(csv_path)) == 64


def test_duplicate_trade_rows_flagged_warning(tmp_path: Path) -> None:
    """Duplicate trade rows should be counted and reported as a warning."""
    csv_path = tmp_path / "trades_round_1_day_-2.csv"
    csv_path.write_text(
        "timestamp;buyer;seller;symbol;currency;price;quantity\n"
        "100;;;OSMIUM;XIRECS;10000.0;2\n"
        "100;;;OSMIUM;XIRECS;10000.0;2\n",
        encoding="utf-8",
    )
    _, report = DataLoader.ingest_csv(csv_path)
    assert report.is_valid
    assert report.duplicate_count == 1
    assert any("duplicate trade" in w for w in report.warnings)


def test_reject_crossed_order_book() -> None:
    """Crossed books (bid_price_1 >= ask_price_1) must fail validation."""
    df = pd.DataFrame({
        "timestamp": [0],
        "product": ["TEST"],
        "bid_price_1": [105],
        "ask_price_1": [100],
        "mid_price": [102.5],
    })
    with pytest.raises(DataValidationError, match="Crossed or inverted"):
        DataIntegrityValidator.validate_price_dataframe(df)


def test_reject_non_monotonic_bid_ladder() -> None:
    """Non-monotonic bid levels (bid_1 <= bid_2) must fail validation."""
    df = pd.DataFrame({
        "timestamp": [0],
        "product": ["TEST"],
        "bid_price_1": [99],
        "bid_price_2": [100],
        "ask_price_1": [102],
        "mid_price": [100.5],
    })
    with pytest.raises(DataValidationError, match="Non-monotonic bid ladder"):
        DataIntegrityValidator.validate_price_dataframe(df)


def test_reject_non_monotonic_ask_ladder() -> None:
    """Non-monotonic ask levels (ask_1 >= ask_2) must fail validation."""
    df = pd.DataFrame({
        "timestamp": [0],
        "product": ["TEST"],
        "bid_price_1": [99],
        "ask_price_1": [102],
        "ask_price_2": [101],
        "mid_price": [100.5],
    })
    with pytest.raises(DataValidationError, match="Non-monotonic ask ladder"):
        DataIntegrityValidator.validate_price_dataframe(df)


def test_reject_timestamp_discontinuity() -> None:
    """Irregular timestamp gaps must fail continuity validation."""
    df = pd.DataFrame({
        "timestamp": [0, 100, 300],
        "product": ["TEST", "TEST", "TEST"],
        "mid_price": [100.0, 101.0, 102.0],
    })
    with pytest.raises(DataValidationError, match="Timestamp discontinuity"):
        DataIntegrityValidator.validate_timestamp_continuity(df, expected_step=100)


def test_reject_non_positive_trade_values() -> None:
    """Trades with non-positive price or quantity must fail validation."""
    bad_df = pd.DataFrame({
        "timestamp": [100],
        "symbol": ["TEST"],
        "price": [100],
        "quantity": [0],
    })
    with pytest.raises(DataValidationError, match="non-positive trade quantity"):
        DataIntegrityValidator.validate_trades_dataframe(bad_df)

    neg_price_df = pd.DataFrame({
        "timestamp": [100],
        "symbol": ["TEST"],
        "price": [-1],
        "quantity": [2],
    })
    with pytest.raises(DataValidationError, match="negative trade price"):
        DataIntegrityValidator.validate_trades_dataframe(neg_price_df)


def test_zero_price_otm_trade_and_zero_bid_book_allowed_with_warning(tmp_path: Path) -> None:
    """Deep-OTM vouchers with 0 bid price and 0-price prints should pass with warning."""
    price_csv = tmp_path / "prices_round_3_day_0.csv"
    price_csv.write_text(
        "day;timestamp;product;bid_price_1;bid_volume_1;ask_price_1;ask_volume_1;mid_price\n"
        "0;0;VEV_6500;0;15;1;15;0.5\n",
        encoding="utf-8",
    )
    _, price_rep = DataLoader.ingest_csv(price_csv)
    assert price_rep.is_valid
    assert price_rep.round_num == 3

    trade_csv = tmp_path / "trades_round_3_day_0.csv"
    trade_csv.write_text(
        "timestamp;buyer;seller;symbol;currency;price;quantity\n"
        "100;;;VEV_6500;XIRECS;0.0;3\n",
        encoding="utf-8",
    )
    _, trade_rep = DataLoader.ingest_csv(trade_csv)
    assert trade_rep.is_valid
    assert any("zero-price trade" in w for w in trade_rep.warnings)


def test_unexpected_columns_rejected(tmp_path: Path) -> None:
    """Unexpected CSV columns must fail strict schema validation explicitly."""
    bad_price = tmp_path / "prices_round_5_day_2.csv"
    bad_price.write_text(
        "day;timestamp;product;bid_price_1;ask_price_1;mid_price;unexpected_col\n"
        "2;0;PEBBLES_XS;999;1001;1000.0;42\n",
        encoding="utf-8",
    )
    _, rep = DataLoader.ingest_csv(bad_price)
    assert not rep.is_valid
    assert any("Unexpected columns" in e for e in rep.errors)

    bad_trade = pd.DataFrame({
        "timestamp": [100],
        "symbol": ["PEBBLES_XS"],
        "price": [1000.0],
        "quantity": [1],
        "extra_field": ["bad"],
    })
    with pytest.raises(DataValidationError, match="Unexpected columns"):
        DataIntegrityValidator.validate_trades_dataframe(bad_trade)


def test_observations_csv_ingestion_and_validation(tmp_path: Path) -> None:
    """ConversionObservation CSV files must validate columns, duplicates, and quotes."""
    obs_csv = tmp_path / "observations_round_4_day_1.csv"
    obs_csv.write_text(
        "timestamp,bidPrice,askPrice,transportFees,exportTariff,importTariff,"
        "sugarPrice,sunlightIndex\n"
        "0,100.0,102.0,1.0,2.5,1.5,50.0,60.0\n"
        "100,101.0,103.0,1.0,2.5,1.5,50.5,61.0\n",
        encoding="utf-8",
    )
    df, report = DataLoader.ingest_csv(obs_csv)
    assert report.is_valid
    assert report.dataset_type == "observations"
    assert report.round_num == 4
    assert report.day_num == 1
    assert len(df) == 2

    bad_obs = tmp_path / "observations_round_4_day_2.csv"
    bad_obs.write_text(
        "timestamp,bidPrice,askPrice,transportFees,exportTariff,importTariff,humidity\n"
        "0,100.0,102.0,1.0,2.5,1.5,80.0\n",
        encoding="utf-8",
    )
    _, bad_rep = DataLoader.ingest_csv(bad_obs)
    assert not bad_rep.is_valid
    assert any("Unexpected columns" in e for e in bad_rep.errors)
