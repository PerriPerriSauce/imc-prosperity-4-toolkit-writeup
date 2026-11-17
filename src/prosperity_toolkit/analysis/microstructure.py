"""Empirical market microstructure analysis, stationarity tests, and OU calibration."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd
from numpy.typing import NDArray
from scipy import stats


@dataclass(frozen=True, slots=True)
class DescriptiveBookReport:
    """Descriptive statistics for a single instrument's historical order book."""

    product: str
    total_ticks: int
    two_sided_ticks: int
    one_sided_ticks: int
    empty_ticks: int
    mid_mean: float
    mid_std: float
    mid_min: float
    mid_max: float
    spread_mean: float
    spread_median: float
    spread_min: float
    spread_max: float
    avg_bid_depth_l1: float
    avg_ask_depth_l1: float


@dataclass(frozen=True, slots=True)
class ADFTestResult:
    """Result of an Augmented Dickey-Fuller unit-root test (with constant)."""

    t_statistic: float
    gamma_hat: float
    gamma_se: float
    n_obs: int
    lags: int
    critical_1pct: float = -3.433
    critical_5pct: float = -2.863
    critical_10pct: float = -2.567

    @property
    def reject_unit_root_5pct(self) -> bool:
        """True if null hypothesis of a unit root is rejected at the 5% level."""
        return self.t_statistic < self.critical_5pct


@dataclass(frozen=True, slots=True)
class OUCalibrationResult:
    """Estimated discrete AR(1) and mapped continuous Ornstein-Uhlenbeck parameters."""

    ar1_intercept: float
    ar1_slope: float
    ar1_slope_se: float
    theta: float
    mu: float
    sigma: float
    half_life: float
    residual_std: float
    r_squared: float


@dataclass(frozen=True, slots=True)
class OBIPredictiveResult:
    """Statistical evaluation of Order Book Imbalance predicting future mid-price changes."""

    horizon: int
    n_obs: int
    correlation: float
    p_value: float
    ols_slope: float
    t_stat: float


@dataclass(frozen=True, slots=True)
class TradeFlowClassification:
    """Trade print execution classification relative to contemporaneous book touches."""

    symbol: str
    total_trades: int
    at_or_above_ask: int
    at_or_below_bid: int
    inside_spread: int
    one_sided_or_missing_book: int
    arrival_rate_per_tick: float
    mean_trade_size: float


def summarize_order_book(df: pd.DataFrame, product: str) -> DescriptiveBookReport:
    """Compute descriptive statistics for a product's order book dataframe."""
    sub = df[df["product"] == product].sort_values("timestamp")
    if sub.empty:
        msg = f"No records found for product {product}"
        raise ValueError(msg)

    has_bid = sub["bid_price_1"].notna()
    has_ask = sub["ask_price_1"].notna()
    two_sided = has_bid & has_ask
    one_sided = has_bid ^ has_ask
    empty = (~has_bid) & (~has_ask)

    two_mid = (sub.loc[two_sided, "bid_price_1"] + sub.loc[two_sided, "ask_price_1"]) / 2.0
    spread = sub.loc[two_sided, "ask_price_1"] - sub.loc[two_sided, "bid_price_1"]

    return DescriptiveBookReport(
        product=product,
        total_ticks=len(sub),
        two_sided_ticks=int(two_sided.sum()),
        one_sided_ticks=int(one_sided.sum()),
        empty_ticks=int(empty.sum()),
        mid_mean=float(two_mid.mean()) if not two_mid.empty else 0.0,
        mid_std=float(two_mid.std(ddof=1)) if len(two_mid) > 1 else 0.0,
        mid_min=float(two_mid.min()) if not two_mid.empty else 0.0,
        mid_max=float(two_mid.max()) if not two_mid.empty else 0.0,
        spread_mean=float(spread.mean()) if not spread.empty else 0.0,
        spread_median=float(spread.median()) if not spread.empty else 0.0,
        spread_min=float(spread.min()) if not spread.empty else 0.0,
        spread_max=float(spread.max()) if not spread.empty else 0.0,
        avg_bid_depth_l1=float(sub.loc[has_bid, "bid_volume_1"].mean()) if has_bid.any() else 0.0,
        avg_ask_depth_l1=float(sub.loc[has_ask, "ask_volume_1"].mean()) if has_ask.any() else 0.0,
    )


def extract_two_sided_mid(df: pd.DataFrame, product: str) -> pd.Series:
    """Return chronological mid-price series strictly on two-sided books indexed by timestamp."""
    sub = df[df["product"] == product].sort_values("timestamp")
    both = sub["bid_price_1"].notna() & sub["ask_price_1"].notna()
    valid = sub.loc[both]
    mid = (valid["bid_price_1"] + valid["ask_price_1"]) / 2.0
    mid.index = pd.Index(valid["timestamp"], name="timestamp")
    return mid


def compute_return_moments(
    series: Sequence[float] | pd.Series,
    lags: tuple[int, ...] = (1, 2, 5, 10),
) -> dict[str, float]:
    """Compute moments and lag autocorrelations of first differences dP_t = P_t - P_{t-1}."""
    arr = np.asarray(series, dtype=np.float64)
    if arr.size < 3:
        msg = "Need at least 3 observations to compute return moments"
        raise ValueError(msg)

    diffs = np.diff(arr)
    results: dict[str, float] = {
        "n_diffs": float(diffs.size),
        "mean": float(np.mean(diffs)),
        "std": float(np.std(diffs, ddof=1)),
        "skewness": float(stats.skew(diffs)),
        "excess_kurtosis": float(stats.kurtosis(diffs)),
    }
    for lag in lags:
        if diffs.size > lag + 1:
            x = diffs[:-lag]
            y = diffs[lag:]
            if np.std(x) > 0 and np.std(y) > 0:
                corr = float(np.corrcoef(x, y)[0, 1])
            else:
                corr = 0.0
            results[f"acf_lag_{lag}"] = corr
    return results


def augmented_dickey_fuller_test(
    series: Sequence[float] | NDArray[np.float64],
    lags: int = 1,
) -> ADFTestResult:
    """Run Augmented Dickey-Fuller test with drift constant via OLS.

    Model:
        dy_t = alpha + gamma * y_{t-1} + sum_{j=1}^p delta_j * dy_{t-j} + eps_t
    Tests H0: gamma = 0 (unit root) against H1: gamma < 0 (stationary).
    Critical values correspond to MacKinnon (1994/2010) large-sample values with constant.
    """
    y = np.asarray(series, dtype=np.float64)
    if y.ndim != 1 or y.size <= lags + 5:
        msg = "Series must be 1-D with length > lags + 5"
        raise ValueError(msg)
    if lags < 0:
        msg = f"lags must be non-negative, got {lags}"
        raise ValueError(msg)

    dy = np.diff(y)
    n_total = dy.size
    start = lags

    dep = dy[start:]
    y_lag1 = y[start:n_total]
    cols: list[NDArray[np.float64]] = [np.ones_like(dep), y_lag1]

    for j in range(1, lags + 1):
        cols.append(dy[start - j : n_total - j])

    design = np.column_stack(cols)
    beta, _, _, _ = np.linalg.lstsq(design, dep, rcond=None)
    residuals = dep - design @ beta

    n_obs = dep.size
    dof = n_obs - design.shape[1]
    sigma2 = float(np.dot(residuals, residuals) / dof)
    cov_beta = sigma2 * np.linalg.inv(design.T @ design)
    gamma_hat = float(beta[1])
    gamma_se = float(math.sqrt(cov_beta[1, 1]))
    t_stat = gamma_hat / gamma_se if gamma_se > 0 else 0.0

    return ADFTestResult(
        t_statistic=t_stat,
        gamma_hat=gamma_hat,
        gamma_se=gamma_se,
        n_obs=n_obs,
        lags=lags,
    )


def estimate_ou_ar1(
    series: Sequence[float] | NDArray[np.float64],
    dt: float = 1.0,
) -> OUCalibrationResult:
    """Estimate Ornstein-Uhlenbeck parameters via exact discrete-time AR(1) OLS."""
    y = np.asarray(series, dtype=np.float64)
    if y.size < 10 or dt <= 0:
        msg = "Series needs at least 10 observations and dt > 0"
        raise ValueError(msg)

    y_prev = y[:-1]
    y_curr = y[1:]
    design = np.column_stack([np.ones_like(y_prev), y_prev])
    beta, _, _, _ = np.linalg.lstsq(design, y_curr, rcond=None)

    a = float(beta[0])
    b = float(beta[1])
    resid = y_curr - design @ beta
    n_obs = y_curr.size
    sigma2_eta = float(np.dot(resid, resid) / (n_obs - 2))
    resid_std = math.sqrt(sigma2_eta)

    cov = sigma2_eta * np.linalg.inv(design.T @ design)
    b_se = math.sqrt(float(cov[1, 1]))

    ss_tot = float(np.sum((y_curr - np.mean(y_curr)) ** 2))
    ss_res = float(np.dot(resid, resid))
    r_squared = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

    if 0.0 < b < 1.0:
        theta = -math.log(b) / dt
        mu = a / (1.0 - b)
        sigma = resid_std * math.sqrt(-2.0 * math.log(b) / (dt * (1.0 - b**2)))
        half_life = math.log(2.0) / theta
    else:
        theta = 0.0
        mu = float(np.mean(y))
        sigma = resid_std / math.sqrt(dt)
        half_life = float("inf")

    return OUCalibrationResult(
        ar1_intercept=a,
        ar1_slope=b,
        ar1_slope_se=b_se,
        theta=theta,
        mu=mu,
        sigma=sigma,
        half_life=half_life,
        residual_std=resid_std,
        r_squared=r_squared,
    )


def estimate_linear_drift(
    timestamps: Sequence[float] | NDArray[np.float64],
    prices: Sequence[float] | NDArray[np.float64],
) -> tuple[float, float, float]:
    """Fit P_t = intercept + slope * t via OLS; returns (slope, intercept, r_squared)."""
    t = np.asarray(timestamps, dtype=np.float64)
    p = np.asarray(prices, dtype=np.float64)
    if t.size != p.size or t.size < 2:
        msg = "timestamps and prices must have matching length >= 2"
        raise ValueError(msg)

    res = stats.linregress(t, p)
    return float(res.slope), float(res.intercept), float(res.rvalue**2)


def evaluate_obi_signal(
    df: pd.DataFrame,
    product: str,
    horizons: tuple[int, ...] = (1, 5, 10),
) -> list[OBIPredictiveResult]:
    """Evaluate correlation and OLS slope between OBI_t and future mid-price changes."""
    sub = df[df["product"] == product].sort_values("timestamp").copy()
    both = sub["bid_price_1"].notna() & sub["ask_price_1"].notna()
    valid = sub.loc[both].reset_index(drop=True)

    mid = (valid["bid_price_1"] + valid["ask_price_1"]) / 2.0
    total_vol = valid["bid_volume_1"] + valid["ask_volume_1"]
    obi = (valid["bid_volume_1"] - valid["ask_volume_1"]) / total_vol.replace(0, np.nan)

    results: list[OBIPredictiveResult] = []
    for h in horizons:
        future_change = mid.shift(-h) - mid
        mask = obi.notna() & future_change.notna()
        x = obi.loc[mask].to_numpy(dtype=np.float64)
        y = future_change.loc[mask].to_numpy(dtype=np.float64)

        if x.size < 10 or np.std(x) == 0 or np.std(y) == 0:
            results.append(
                OBIPredictiveResult(
                    horizon=h,
                    n_obs=int(x.size),
                    correlation=0.0,
                    p_value=1.0,
                    ols_slope=0.0,
                    t_stat=0.0,
                ),
            )
            continue

        reg = stats.linregress(x, y)
        r = float(reg.rvalue)
        n = int(x.size)
        t_stat = float(reg.slope / reg.stderr) if reg.stderr > 0 else 0.0
        results.append(
            OBIPredictiveResult(
                horizon=h,
                n_obs=n,
                correlation=r,
                p_value=float(reg.pvalue),
                ols_slope=float(reg.slope),
                t_stat=t_stat,
            ),
        )

    return results


def classify_trade_flow(
    prices_df: pd.DataFrame,
    trades_df: pd.DataFrame,
    symbol: str,
) -> TradeFlowClassification:
    """Classify public trades relative to contemporaneous L1 bid/ask quotes."""
    sym_prices = prices_df[prices_df["product"] == symbol]
    n_ticks = len(sym_prices)
    sym_trades = trades_df[trades_df["symbol"] == symbol]

    if sym_trades.empty:
        return TradeFlowClassification(
            symbol=symbol,
            total_trades=0,
            at_or_above_ask=0,
            at_or_below_bid=0,
            inside_spread=0,
            one_sided_or_missing_book=0,
            arrival_rate_per_tick=0.0,
            mean_trade_size=0.0,
        )

    merged = sym_trades.merge(
        sym_prices[["timestamp", "bid_price_1", "ask_price_1"]],
        on="timestamp",
        how="left",
    )
    both = merged["bid_price_1"].notna() & merged["ask_price_1"].notna()
    two_sided = merged.loc[both]

    at_ask = int((two_sided["price"] >= two_sided["ask_price_1"]).sum())
    at_bid = int((two_sided["price"] <= two_sided["bid_price_1"]).sum())
    inside = int(
        ((two_sided["price"] > two_sided["bid_price_1"])
         & (two_sided["price"] < two_sided["ask_price_1"])).sum(),
    )
    missing = int((~both).sum())

    return TradeFlowClassification(
        symbol=symbol,
        total_trades=len(sym_trades),
        at_or_above_ask=at_ask,
        at_or_below_bid=at_bid,
        inside_spread=inside,
        one_sided_or_missing_book=missing,
        arrival_rate_per_tick=len(sym_trades) / n_ticks if n_ticks > 0 else 0.0,
        mean_trade_size=float(sym_trades["quantity"].mean()),
    )
