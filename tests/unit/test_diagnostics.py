"""Unit tests for DSR, CSCV/PBO overfitting diagnostics, and 2D plateau sensitivity."""

from __future__ import annotations

import math

import numpy as np
from scipy import stats

from prosperity_toolkit.analysis.diagnostics import OverfittingDiagnostics
from prosperity_toolkit.optimisation.sensitivity import SensitivityAnalyzer


def test_expected_max_sharpe_monotonic() -> None:
    """Expected max Sharpe under H0 must be 0 for N=1 and strictly increase with N."""
    assert OverfittingDiagnostics.estimate_expected_max_sharpe(1, 1.0) == 0.0
    sr_10 = OverfittingDiagnostics.estimate_expected_max_sharpe(10, 0.25)
    sr_100 = OverfittingDiagnostics.estimate_expected_max_sharpe(100, 0.25)
    assert sr_10 > 0.0
    assert sr_100 > sr_10


def test_deflated_sharpe_ratio_analytical_and_monotonicity() -> None:
    """Verify DSR against exact closed-form Gaussian standard error and N-trial deflation."""
    obs_sr = 0.2
    n_obs = 101
    res_single = OverfittingDiagnostics.deflated_sharpe_ratio(
        observed_sr=obs_sr,
        n_trials=1,
        sr_variance=0.01,
        n_obs=n_obs,
        skewness=0.0,
        excess_kurtosis=0.0,
    )
    expected_z = (obs_sr * math.sqrt(n_obs - 1)) / math.sqrt(1.0 + 0.5 * obs_sr**2)
    assert abs(res_single.deflated_sharpe_ratio - float(stats.norm.cdf(expected_z))) < 1e-12

    res_many = OverfittingDiagnostics.deflated_sharpe_ratio(
        observed_sr=obs_sr,
        n_trials=50,
        sr_variance=0.01,
        n_obs=n_obs,
        skewness=-1.0,
        excess_kurtosis=4.0,
    )
    assert res_many.deflated_sharpe_ratio < res_single.deflated_sharpe_ratio


def test_cscv_pbo_signal_vs_noise() -> None:
    """CSCV must yield low PBO (< 0.15) with genuine alpha and high PBO on pure noise."""
    rng = np.random.default_rng(2026)
    noise_mat = rng.normal(0.0, 1.0, size=(800, 12))
    noise_cscv = OverfittingDiagnostics.compute_cscv_pbo(noise_mat, n_slices=8)
    assert noise_cscv.n_combinations == 70
    assert not noise_cscv.passes_pbo_threshold

    signal_mat = noise_mat.copy()
    signal_mat[:, 0] += 0.35  # Dominant genuine edge in trial 0
    signal_cscv = OverfittingDiagnostics.compute_cscv_pbo(signal_mat, n_slices=8)
    assert signal_cscv.passes_pbo_threshold
    assert signal_cscv.pbo < noise_cscv.pbo


def test_sensitivity_rejects_isolated_spike_for_plateau() -> None:
    """2D plateau selector must choose a stable plateau over an isolated cliff spike."""
    x_vals = [0.0, 1.0, 2.0, 3.0, 4.0]
    y_vals = [0.0, 1.0, 2.0, 3.0, 4.0]
    scores = np.full((5, 5), -5.0, dtype=np.float64)
    # Isolated spike at (0, 0) surrounded by -5.0 cliffs
    scores[0, 0] = 12.0
    # Broad stable plateau around (3, 3)
    scores[2:5, 2:5] = 8.0

    sel = SensitivityAnalyzer.select_stable_plateau_2d(x_vals, y_vals, scores, std_penalty=1.0)
    assert (sel.x_index, sel.y_index) == (3, 3)
    assert sel.raw_score == 8.0
    assert sel.local_std == 0.0


def test_effective_trials_bounds() -> None:
    """Effective trial count must equal 1 for identical cols and ~N for orthogonal cols."""
    rng = np.random.default_rng(11)
    base = rng.normal(0.0, 1.0, size=(500, 1))
    identical = np.repeat(base, 5, axis=1)
    assert abs(OverfittingDiagnostics.estimate_effective_trials(identical) - 1.0) < 1e-6

    orth = rng.normal(0.0, 1.0, size=(2000, 5))
    n_eff = OverfittingDiagnostics.estimate_effective_trials(orth)
    assert 4.5 <= n_eff <= 5.0


def test_block_bootstrap_ci_contains_point_estimate() -> None:
    """Block bootstrap CI must bracket the sample mean total PnL cleanly."""
    rng = np.random.default_rng(7)
    rets = rng.normal(0.5, 1.0, size=400)
    ci = OverfittingDiagnostics.block_bootstrap_ci(rets, block_size=20, n_bootstraps=300, seed=7)
    sample_pnl = float(np.sum(rets))
    assert ci.pnl_ci_low < sample_pnl < ci.pnl_ci_high
    assert ci.sharpe_ci_low < ci.mean_sharpe < ci.sharpe_ci_high
