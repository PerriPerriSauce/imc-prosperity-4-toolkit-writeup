"""Unit tests for option pricing models and cross-asset PCA / pulse analytics."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from prosperity_toolkit.analysis import (
    bachelier_call,
    bachelier_call_delta,
    black_scholes_call,
    black_scholes_call_delta,
    detect_trade_pulses,
    fit_cointegrating_basket,
    implied_volatility_bachelier,
    implied_volatility_bs,
)


def test_black_scholes_and_iv_round_trip() -> None:
    """Black-Scholes price and IV inversion must agree cleanly."""
    spot, strike, tte, true_vol = 5250.0, 5300.0, 5.0 / 252.0, 0.045
    price = black_scholes_call(spot, strike, tte, true_vol)
    assert price > 0.0
    delta = black_scholes_call_delta(spot, strike, tte, true_vol)
    assert 0.0 < delta < 1.0

    recovered = implied_volatility_bs(price, spot, strike, tte)
    assert recovered is not None
    assert recovered == pytest.approx(true_vol, rel=1e-4)

    # Price below intrinsic cannot yield finite positive BS IV
    assert implied_volatility_bs(10.0, 5350.0, 5300.0, tte) is None


def test_bachelier_and_iv_round_trip() -> None:
    """Bachelier arithmetic option model must recover true per-step sigma."""
    spot, strike, steps, sigma = 5250.0, 5300.0, 30_000.0, 1.25
    price = bachelier_call(spot, strike, steps, sigma)
    delta = bachelier_call_delta(spot, strike, steps, sigma)
    assert price > 0.0
    assert 0.25 < delta < 0.55

    recovered = implied_volatility_bachelier(price, spot, strike, steps)
    assert recovered is not None
    assert recovered == pytest.approx(sigma, rel=1e-4)


def test_cointegrating_basket_recovers_constant_sum() -> None:
    """PCA level solver must recover uniform equal weights on a constant-sum basket."""
    rng = np.random.default_rng(7)
    n = 300
    a = 10_000.0 + np.cumsum(rng.normal(0, 5.0, n))
    b = 10_000.0 + np.cumsum(rng.normal(0, 5.0, n))
    c = 30_000.0 - a - b + rng.normal(0, 0.5, n)

    df = pd.DataFrame({"A": a, "B": b, "C": c})
    res = fit_cointegrating_basket(df)

    assert res.reject_unit_root_5pct
    assert res.spread_std < 1.0
    assert np.allclose(res.weights, res.weights[0], atol=0.05)


def test_detect_trade_pulses_identifies_cofiring() -> None:
    """Pulse detector should identify synchronous multi-symbol buy/sell bursts."""
    price_wide = pd.DataFrame(
        {"P1": [100.0, 100.0], "P2": [200.0, 200.0], "P3": [300.0, 300.0]},
        index=[100, 200],
    )
    trades_df = pd.DataFrame([
        {"timestamp": 100, "symbol": "P1", "price": 101.0, "quantity": 3},
        {"timestamp": 100, "symbol": "P2", "price": 201.0, "quantity": 3},
        {"timestamp": 100, "symbol": "P3", "price": 301.0, "quantity": 3},
        {"timestamp": 200, "symbol": "P1", "price": 99.0, "quantity": 2},
    ])
    summary = detect_trade_pulses(
        trades_df,
        symbols=("P1", "P2", "P3"),
        price_wide=price_wide,
        total_ticks=100,
        min_group_size=3,
    )
    assert summary.n_pulse_events == 1
    assert summary.max_group_size == 3
    assert summary.uniform_side_share == 1.0
    assert summary.uniform_qty_share == 1.0
