"""Overfitting diagnostics: Deflated Sharpe Ratio (DSR) and CSCV / PBO."""

from __future__ import annotations

import itertools
import math
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from scipy import stats

_EULER_MASCHERONI = 0.5772156649015329


@dataclass(frozen=True, slots=True)
class DSRResult:
    """Result of a Deflated Sharpe Ratio multiple-testing adjustment."""

    observed_sharpe: float
    expected_max_sharpe: float
    deflated_sharpe_ratio: float
    n_trials: int
    n_obs: int
    skewness: float
    excess_kurtosis: float

    @property
    def passes_95pct(self) -> bool:
        """True if DSR exceeds the 95% confidence threshold."""
        return self.deflated_sharpe_ratio >= 0.95


@dataclass(frozen=True, slots=True)
class CSCVResult:
    """Result of Combinatorial Symmetric Cross-Validation (PBO)."""

    pbo: float
    prob_oos_negative: float
    n_combinations: int
    n_slices: int
    n_trials: int
    logits: tuple[float, ...]
    mean_is_best_sharpe: float
    mean_oos_selected_sharpe: float

    @property
    def passes_pbo_threshold(self) -> bool:
        """True if Probability of Backtest Overfitting is strictly below 0.15."""
        return self.pbo < 0.15


@dataclass(frozen=True, slots=True)
class BootstrapCIResult:
    """Circular block-bootstrap confidence interval for Sharpe and cumulative PnL."""

    mean_sharpe: float
    sharpe_ci_low: float
    sharpe_ci_high: float
    mean_total_pnl: float
    pnl_ci_low: float
    pnl_ci_high: float
    block_size: int
    n_bootstraps: int


def _compute_sharpe(returns: NDArray[np.float64]) -> float:
    """Compute non-annualized per-period Sharpe ratio safely."""
    if returns.size < 2:
        return 0.0
    std = float(np.std(returns, ddof=1))
    if std <= 0.0:
        return 0.0
    return float(np.mean(returns)) / std


class OverfittingDiagnostics:
    """Statistical corrections for multiple testing and backtest overfitting."""

    @staticmethod
    def estimate_expected_max_sharpe(n_trials: int, variance_sharpe: float = 1.0) -> float:
        """Bailey & Lopez de Prado (2014) expected maximum Sharpe under H0.

        Uses Euler-Mascheroni extreme value approximation:
            E[max_N] = std_SR * ((1 - gamma) * Phi^-1(1 - 1/N) + gamma * Phi^-1(1 - 1/(N*e)))
        """
        if n_trials <= 1 or variance_sharpe <= 0.0:
            return 0.0
        std_sr = math.sqrt(variance_sharpe)
        z1 = float(stats.norm.ppf(1.0 - 1.0 / n_trials))
        z2 = float(stats.norm.ppf(1.0 - 1.0 / (n_trials * math.e)))
        return std_sr * ((1.0 - _EULER_MASCHERONI) * z1 + _EULER_MASCHERONI * z2)

    @classmethod
    def deflated_sharpe_ratio(
        cls,
        observed_sr: float,
        n_trials: int,
        sr_variance: float,
        n_obs: int,
        skewness: float = 0.0,
        excess_kurtosis: float = 0.0,
    ) -> DSRResult:
        """Compute Deflated Sharpe Ratio from explicit distribution moments.

        Note: `excess_kurtosis` is Fisher excess kurtosis (0.0 for Gaussian), so
        (K - 1) / 4 = (excess_kurtosis + 2) / 4.
        """
        if n_obs < 2:
            msg = "Need at least 2 return observations to compute DSR"
            raise ValueError(msg)

        sr_star = cls.estimate_expected_max_sharpe(n_trials, sr_variance)
        kurt_term = ((excess_kurtosis + 2.0) / 4.0) * (observed_sr**2)
        denom_inner = 1.0 - skewness * observed_sr + kurt_term
        denom = math.sqrt(max(1e-12, denom_inner))
        z_score = ((observed_sr - sr_star) * math.sqrt(n_obs - 1)) / denom
        dsr = float(stats.norm.cdf(z_score))

        return DSRResult(
            observed_sharpe=observed_sr,
            expected_max_sharpe=sr_star,
            deflated_sharpe_ratio=dsr,
            n_trials=n_trials,
            n_obs=n_obs,
            skewness=skewness,
            excess_kurtosis=excess_kurtosis,
        )

    @classmethod
    def evaluate_trial_dsr(
        cls,
        selected_returns: Sequence[float] | NDArray[np.float64],
        all_trial_sharpes: Sequence[float],
        n_trials_override: float | None = None,
    ) -> DSRResult:
        """Evaluate DSR for a selected strategy given tested trial Sharpes.

        Args:
            selected_returns: Return series for the chosen strategy.
            all_trial_sharpes: Unscaled Sharpe ratios on the same sampling horizon.
            n_trials_override: Optional effective independent trial count (`N_eff`).
        """
        ret = np.asarray(selected_returns, dtype=np.float64)
        obs_sr = _compute_sharpe(ret)
        raw_n = len(all_trial_sharpes)
        sr_var = float(np.var(all_trial_sharpes, ddof=1)) if raw_n > 1 else 0.0
        eff_n = (
            max(1, round(n_trials_override))
            if n_trials_override is not None
            else max(1, raw_n)
        )
        skew = float(stats.skew(ret)) if ret.size > 2 and np.std(ret) > 0 else 0.0
        ex_kurt = (
            float(stats.kurtosis(ret, fisher=True))
            if ret.size > 3 and np.std(ret) > 0
            else 0.0
        )

        return cls.deflated_sharpe_ratio(
            observed_sr=obs_sr,
            n_trials=eff_n,
            sr_variance=sr_var,
            n_obs=int(ret.size),
            skewness=skew,
            excess_kurtosis=ex_kurt,
        )

    @classmethod
    def evaluate_block_matrix_dsr(
        cls,
        trial_returns_matrix: NDArray[np.float64],
        selected_col_idx: int,
        block_size: int = 100,
    ) -> tuple[DSRResult, float]:
        """Compute N_eff-adjusted DSR after aggregating returns into disjoint blocks.

        Aggregating correlated tick returns into non-overlapping blocks mitigates
        N_obs inflation under serial dependence while keeping observed Sharpe,
        cross-trial Sharpe variance, and N_eff on the exact same time horizon.
        """
        mat = np.asarray(trial_returns_matrix, dtype=np.float64)
        if mat.ndim != 2 or mat.shape[0] < 2:
            msg = "trial_returns_matrix must have shape (T >= 2, N)"
            raise ValueError(msg)
        eff_block = max(1, min(block_size, mat.shape[0] // 2))
        n_blocks = mat.shape[0] // eff_block
        block_mat = (
            mat[: n_blocks * eff_block, :]
            .reshape(n_blocks, eff_block, mat.shape[1])
            .sum(axis=1)
        )
        trial_srs = [_compute_sharpe(block_mat[:, j]) for j in range(block_mat.shape[1])]
        n_eff = cls.estimate_effective_trials(block_mat)
        dsr = cls.evaluate_trial_dsr(
            selected_returns=block_mat[:, selected_col_idx],
            all_trial_sharpes=trial_srs,
            n_trials_override=n_eff,
        )
        return dsr, n_eff

    @staticmethod
    def compute_cscv_pbo(
        trial_returns_matrix: NDArray[np.float64],
        n_slices: int = 8,
    ) -> CSCVResult:
        """Compute Probability of Backtest Overfitting (PBO) via CSCV.

        Args:
            trial_returns_matrix: 2D array of shape (T, N) with T periodic returns across N trials.
            n_slices: Even number of disjoint contiguous time slices S (default 8 -> 70 combos).
        """
        mat = np.asarray(trial_returns_matrix, dtype=np.float64)
        if mat.ndim != 2:
            msg = "trial_returns_matrix must be 2-dimensional (T, N)"
            raise ValueError(msg)
        n_steps, n_trials = mat.shape
        if n_slices < 4 or n_slices % 2 != 0:
            msg = f"n_slices must be an even integer >= 4, got {n_slices}"
            raise ValueError(msg)
        if n_trials < 2:
            msg = "CSCV requires at least 2 candidate trials"
            raise ValueError(msg)
        if n_steps < n_slices * 2:
            msg = f"Time series length {n_steps} too short for {n_slices} slices"
            raise ValueError(msg)

        usable = (n_steps // n_slices) * n_slices
        blocks = np.array_split(mat[:usable], n_slices, axis=0)
        half = n_slices // 2
        all_indices = set(range(n_slices))

        logits: list[float] = []
        is_best_srs: list[float] = []
        oos_sel_srs: list[float] = []
        oos_neg_count = 0

        for is_combo in itertools.combinations(range(n_slices), half):
            oos_combo = tuple(sorted(all_indices - set(is_combo)))
            is_data = np.vstack([blocks[i] for i in is_combo])
            oos_data = np.vstack([blocks[i] for i in oos_combo])

            is_std = np.std(is_data, axis=0, ddof=1)
            is_mean = np.mean(is_data, axis=0)
            is_srs = np.where(is_std > 0, is_mean / is_std, 0.0)

            oos_std = np.std(oos_data, axis=0, ddof=1)
            oos_mean = np.mean(oos_data, axis=0)
            oos_srs = np.where(oos_std > 0, oos_mean / oos_std, 0.0)

            best_idx = int(np.argmax(is_srs))
            is_best_srs.append(float(is_srs[best_idx]))
            oos_sel_sr = float(oos_srs[best_idx])
            oos_sel_srs.append(oos_sel_sr)
            if oos_sel_sr <= 0.0:
                oos_neg_count += 1

            # Relative rank in (0, 1) across all N OOS Sharpes
            rank_1based = float(stats.rankdata(oos_srs, method="average")[best_idx])
            omega = rank_1based / (n_trials + 1.0)
            omega = min(max(omega, 1e-6), 1.0 - 1e-6)
            logits.append(math.log(omega / (1.0 - omega)))

        n_combos = len(logits)
        pbo = sum(1 for lam in logits if lam <= 0.0) / n_combos

        return CSCVResult(
            pbo=pbo,
            prob_oos_negative=oos_neg_count / n_combos,
            n_combinations=n_combos,
            n_slices=n_slices,
            n_trials=n_trials,
            logits=tuple(logits),
            mean_is_best_sharpe=float(np.mean(is_best_srs)),
            mean_oos_selected_sharpe=float(np.mean(oos_sel_srs)),
        )

    @staticmethod
    def estimate_effective_trials(trial_returns_matrix: NDArray[np.float64]) -> float:
        """Compute effective independent trial count N_eff via correlation eigenvalue ratio.

        N_eff = (sum lambda_k)^2 / sum(lambda_k^2) in [1, N]. Filters degenerate
        zero-variance trials so constant-return columns do not zero out matrix diagonals.
        """
        mat = np.asarray(trial_returns_matrix, dtype=np.float64)
        if mat.ndim != 2 or mat.shape[1] < 2:
            return float(mat.shape[1]) if mat.ndim == 2 else 1.0
        stds = np.std(mat, axis=0, ddof=1)
        valid = stds > 1e-12
        if int(np.sum(valid)) < 2:
            return 1.0
        corr = np.asarray(np.corrcoef(mat[:, valid], rowvar=False), dtype=np.float64)
        corr = np.nan_to_num(corr, nan=0.0)
        np.fill_diagonal(corr, 1.0)
        eigvals = np.linalg.eigvalsh(corr)
        eigvals = np.maximum(eigvals, 0.0)
        denom = float(np.sum(eigvals**2))
        if denom <= 0.0:
            return 1.0
        return float((np.sum(eigvals) ** 2) / denom)

    @staticmethod
    def block_bootstrap_ci(
        returns: Sequence[float] | NDArray[np.float64],
        block_size: int = 100,
        n_bootstraps: int = 500,
        alpha: float = 0.05,
        seed: int = 42,
        scale_factor: float = 1.0,
    ) -> BootstrapCIResult:
        """Circular block-bootstrap CI preserving short-horizon serial dependence."""
        ret = np.asarray(returns, dtype=np.float64)
        n = ret.size
        if n < 2 or block_size <= 0 or n_bootstraps <= 0 or scale_factor <= 0.0:
            msg = (
                "Need valid return series (len >= 2), block_size > 0, "
                "n_bootstraps > 0, and scale_factor > 0"
            )
            raise ValueError(msg)

        eff_block = min(block_size, n)
        n_blocks = math.ceil(n / eff_block)
        rng = np.random.default_rng(seed)

        boot_sharpes = np.empty(n_bootstraps, dtype=np.float64)
        boot_pnls = np.empty(n_bootstraps, dtype=np.float64)
        sqrt_scale = math.sqrt(scale_factor)

        for b_idx in range(n_bootstraps):
            starts = rng.integers(0, n, size=n_blocks)
            offsets = np.arange(eff_block)
            indices = (starts[:, None] + offsets[None, :]).ravel()[:n] % n
            sample = ret[indices]
            std = float(np.std(sample, ddof=1))
            boot_sharpes[b_idx] = (
                (float(np.mean(sample)) / std) * sqrt_scale if std > 0 else 0.0
            )
            boot_pnls[b_idx] = float(np.sum(sample))

        lo_q = 100.0 * (alpha / 2.0)
        hi_q = 100.0 * (1.0 - alpha / 2.0)
        return BootstrapCIResult(
            mean_sharpe=float(np.mean(boot_sharpes)),
            sharpe_ci_low=float(np.percentile(boot_sharpes, lo_q)),
            sharpe_ci_high=float(np.percentile(boot_sharpes, hi_q)),
            mean_total_pnl=float(np.mean(boot_pnls)),
            pnl_ci_low=float(np.percentile(boot_pnls, lo_q)),
            pnl_ci_high=float(np.percentile(boot_pnls, hi_q)),
            block_size=eff_block,
            n_bootstraps=n_bootstraps,
        )
