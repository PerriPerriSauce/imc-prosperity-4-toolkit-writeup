"""Unit tests for market microstructure analysis, ADF, and OU parameter recovery."""

from __future__ import annotations

import numpy as np
import pandas as pd

from prosperity_toolkit.analysis.microstructure import (
    augmented_dickey_fuller_test,
    classify_trade_flow,
    compute_return_moments,
    estimate_linear_drift,
    estimate_ou_ar1,
    evaluate_obi_signal,
    extract_two_sided_mid,
    summarize_order_book,
)
from prosperity_toolkit.simulation.processes import OrnsteinUhlenbeckParams, simulate_ou_paths


def test_summarize_order_book_and_two_sided_mid() -> None:
    """Verify explicit counting of two-sided, one-sided, and empty books."""
    df = pd.DataFrame({
        "timestamp": [0, 100, 200, 300],
        "product": ["A", "A", "A", "A"],
        "bid_price_1": [99.0, 99.0, np.nan, np.nan],
        "bid_volume_1": [10.0, 10.0, np.nan, np.nan],
        "ask_price_1": [101.0, np.nan, 102.0, np.nan],
        "ask_volume_1": [12.0, np.nan, 8.0, np.nan],
        "mid_price": [100.0, 99.0, 102.0, 0.0],
    })
    rep = summarize_order_book(df, "A")
    assert rep.total_ticks == 4
    assert rep.two_sided_ticks == 1
    assert rep.one_sided_ticks == 2
    assert rep.empty_ticks == 1
    assert rep.spread_mean == 2.0

    two_mid = extract_two_sided_mid(df, "A")
    assert len(two_mid) == 1
    assert float(two_mid.iloc[0]) == 100.0


def test_compute_return_moments_alternating_bounce() -> None:
    """Alternating +2 / -2 price bounce must have lag-1 ACF == -1.0."""
    prices = [100.0, 102.0, 100.0, 102.0, 100.0, 102.0, 100.0]
    moments = compute_return_moments(prices, lags=(1, 2))
    assert abs(moments["mean"]) < 1e-12
    assert abs(moments["acf_lag_1"] - (-1.0)) < 1e-12
    assert abs(moments["acf_lag_2"] - 1.0) < 1e-12


def test_adf_distinguishes_ou_from_random_walk() -> None:
    """ADF test must reject unit root on stationary OU and fail to reject on random walk."""
    rng = np.random.default_rng(42)
    ou_params = OrnsteinUhlenbeckParams(mu=100.0, theta=0.2, sigma=1.0)
    ou_path = simulate_ou_paths(ou_params, n_sessions=1, n_steps=1000, rng=rng)[0]
    rw_path = np.cumsum(rng.standard_normal(1000))

    ou_adf = augmented_dickey_fuller_test(ou_path, lags=1)
    rw_adf = augmented_dickey_fuller_test(rw_path, lags=1)

    assert ou_adf.reject_unit_root_5pct
    assert not rw_adf.reject_unit_root_5pct


def test_ou_ar1_parameter_recovery() -> None:
    """AR(1) OLS estimator must recover true OU parameters on a long stationary path."""
    rng = np.random.default_rng(2026)
    true_params = OrnsteinUhlenbeckParams(mu=10000.0, theta=0.1, sigma=2.0, dt=1.0)
    path = simulate_ou_paths(true_params, n_sessions=1, n_steps=8000, rng=rng)[0]

    est = estimate_ou_ar1(path, dt=1.0)
    assert abs(est.mu - 10000.0) < 1.5
    assert abs(est.theta - 0.1) < 0.02
    assert abs(est.sigma - 2.0) < 0.1


def test_estimate_linear_drift_exact() -> None:
    """Linear drift OLS must recover exact slope and R^2=1.0 on noiseless drift."""
    ts = np.array([0.0, 100.0, 200.0, 300.0])
    prices = 10000.0 + 0.001 * ts
    slope, intercept, r2 = estimate_linear_drift(ts, prices)
    assert abs(slope - 0.001) < 1e-12
    assert abs(intercept - 10000.0) < 1e-9
    assert abs(r2 - 1.0) < 1e-12


def test_obi_signal_and_trade_classification() -> None:
    """Verify OBI predictive regression and trade touch classification."""
    # Positive OBI at t=0 predicts upward mid move at t=100; negative OBI predicts downward move
    n = 40
    timestamps = [i * 100 for i in range(n)]
    bid_p = [100.0 if i % 2 == 0 else 101.0 for i in range(n)]
    ask_p = [102.0 if i % 2 == 0 else 103.0 for i in range(n)]
    bid_v = [20.0 if i % 2 == 0 else 5.0 for i in range(n)]
    ask_v = [5.0 if i % 2 == 0 else 20.0 for i in range(n)]

    prices_df = pd.DataFrame({
        "timestamp": timestamps,
        "product": ["SYM"] * n,
        "bid_price_1": bid_p,
        "bid_volume_1": bid_v,
        "ask_price_1": ask_p,
        "ask_volume_1": ask_v,
        "mid_price": [(b + a) / 2.0 for b, a in zip(bid_p, ask_p, strict=True)],
    })
    obi_res = evaluate_obi_signal(prices_df, "SYM", horizons=(1,))
    assert len(obi_res) == 1
    assert obi_res[0].correlation > 0.9

    trades_df = pd.DataFrame({
        "timestamp": [0, 100, 200],
        "symbol": ["SYM", "SYM", "SYM"],
        "price": [102.0, 101.0, 101.0],
        "quantity": [3, 4, 2],
    })
    flow = classify_trade_flow(prices_df, trades_df, "SYM")
    assert flow.total_trades == 3
    assert flow.at_or_above_ask == 1
    assert flow.at_or_below_bid == 1
    assert flow.inside_spread == 1
