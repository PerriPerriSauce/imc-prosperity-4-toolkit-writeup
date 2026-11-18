"""Cross-asset factor, PCA cointegration, and synchronized pulse analytics."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from numpy.typing import NDArray

from prosperity_toolkit.analysis.microstructure import (
    augmented_dickey_fuller_test,
    estimate_ou_ar1,
)


@dataclass(frozen=True, slots=True)
class PCASpectrumResult:
    """Eigenvalue spectrum and leading/smallest eigenvectors of a multi-asset panel."""

    columns: tuple[str, ...]
    eigenvalues: NDArray[np.float64]
    smallest_eigenvector: NDArray[np.float64]
    largest_eigenvector: NDArray[np.float64]
    condition_ratio: float


@dataclass(frozen=True, slots=True)
class CointegratedBasketResult:
    """Minimum-variance linear combination and stationarity summary."""

    columns: tuple[str, ...]
    weights: NDArray[np.float64]
    spread_mean: float
    spread_std: float
    adf_t_stat: float
    reject_unit_root_5pct: bool
    ou_half_life: float


@dataclass(frozen=True, slots=True)
class TradePulseSummary:
    """Summary of synchronized multi-symbol trade pulses within a category."""

    n_pulse_events: int
    mean_group_size: float
    max_group_size: int
    uniform_side_share: float
    uniform_qty_share: float
    arrival_rate_per_tick: float


def compute_pca_spectrum(
    df_wide: pd.DataFrame,
    use_diffs: bool = True,
) -> PCASpectrumResult:
    """Compute sorted descending covariance eigenvalues and extreme eigenvectors."""
    clean = df_wide.dropna()
    if use_diffs:
        clean = clean.diff().dropna()
    if len(clean) < 10 or clean.shape[1] < 2:
        msg = "Need at least 10 observations and 2 assets for PCA spectrum"
        raise ValueError(msg)

    mat = clean.to_numpy(dtype=np.float64)
    mat = mat - np.mean(mat, axis=0, keepdims=True)
    cov = np.cov(mat, rowvar=False)
    eigvals, eigvecs = np.linalg.eigh(cov)
    order = np.argsort(eigvals)[::-1]
    eigvals_desc = np.maximum(eigvals[order], 0.0)
    eigvecs_desc = eigvecs[:, order]

    smallest_vec = eigvecs_desc[:, -1]
    if np.sum(smallest_vec) < 0:
        smallest_vec = -smallest_vec
    largest_vec = eigvecs_desc[:, 0]
    if np.sum(largest_vec) < 0:
        largest_vec = -largest_vec

    ratio = (
        float(eigvals_desc[0] / eigvals_desc[-1])
        if eigvals_desc[-1] > 1e-12
        else float("inf")
    )
    return PCASpectrumResult(
        columns=tuple(str(c) for c in clean.columns),
        eigenvalues=eigvals_desc,
        smallest_eigenvector=smallest_vec,
        largest_eigenvector=largest_vec,
        condition_ratio=ratio,
    )


def fit_cointegrating_basket(df_wide: pd.DataFrame) -> CointegratedBasketResult:
    """Extract minimum-variance level combination and test stationarity via ADF & OU."""
    clean = df_wide.dropna()
    pca = compute_pca_spectrum(clean, use_diffs=False)
    weights = pca.smallest_eigenvector
    spread = clean.to_numpy(dtype=np.float64) @ weights

    adf = augmented_dickey_fuller_test(spread, lags=1)
    ou = estimate_ou_ar1(spread)
    return CointegratedBasketResult(
        columns=pca.columns,
        weights=weights,
        spread_mean=float(np.mean(spread)),
        spread_std=float(np.std(spread, ddof=1)),
        adf_t_stat=adf.t_statistic,
        reject_unit_root_5pct=adf.reject_unit_root_5pct,
        ou_half_life=ou.half_life,
    )


def detect_trade_pulses(
    trades_df: pd.DataFrame,
    symbols: tuple[str, ...],
    price_wide: pd.DataFrame,
    total_ticks: int = 10_000,
    min_group_size: int = 3,
) -> TradePulseSummary:
    """Detect synchronized multi-asset trade timestamps across an asset category."""
    sub = trades_df[trades_df["symbol"].isin(symbols)].copy()
    if sub.empty:
        return TradePulseSummary(
            n_pulse_events=0,
            mean_group_size=0.0,
            max_group_size=0,
            uniform_side_share=0.0,
            uniform_qty_share=0.0,
            arrival_rate_per_tick=0.0,
        )

    # Infer trade initiator side from contemporaneous two-sided mid price
    mid_lookup = {
        sym: price_wide[sym].to_dict()
        for sym in symbols
        if sym in price_wide.columns
    }
    sides: list[int] = []
    for ts_raw, sym_raw, px_raw in zip(
        sub["timestamp"],
        sub["symbol"],
        sub["price"],
        strict=False,
    ):
        ts = int(ts_raw)
        sym = str(sym_raw)
        mid_val = mid_lookup.get(sym, {}).get(ts)
        if mid_val is None or pd.isna(mid_val):
            sides.append(0)
        elif float(px_raw) > float(mid_val):
            sides.append(1)
        elif float(px_raw) < float(mid_val):
            sides.append(-1)
        else:
            sides.append(0)
    sub["side"] = sides

    pulse_events = []
    uniform_side = 0
    uniform_qty = 0
    for _, grp in sub.groupby("timestamp"):
        n_syms = int(grp["symbol"].nunique())
        if n_syms >= min_group_size:
            pulse_events.append(n_syms)
            valid_sides = grp.loc[grp["side"] != 0, "side"].unique()
            if len(valid_sides) == 1:
                uniform_side += 1
            if grp["quantity"].nunique() == 1:
                uniform_qty += 1

    n_ev = len(pulse_events)
    if n_ev == 0:
        return TradePulseSummary(
            n_pulse_events=0,
            mean_group_size=0.0,
            max_group_size=0,
            uniform_side_share=0.0,
            uniform_qty_share=0.0,
            arrival_rate_per_tick=0.0,
        )

    return TradePulseSummary(
        n_pulse_events=n_ev,
        mean_group_size=float(np.mean(pulse_events)),
        max_group_size=int(np.max(pulse_events)),
        uniform_side_share=float(uniform_side / n_ev),
        uniform_qty_share=float(uniform_qty / n_ev),
        arrival_rate_per_tick=float(n_ev / total_ticks),
    )
