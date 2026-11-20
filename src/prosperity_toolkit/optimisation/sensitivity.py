"""Parameter sensitivity, cliff detection, and plateau stability analysis."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray


@dataclass(frozen=True, slots=True)
class PlateauSelection:
    """Result of stability-penalized 2D parameter plateau selection."""

    x_index: int
    y_index: int
    x_value: float
    y_value: float
    raw_score: float
    plateau_score: float
    local_mean: float
    local_std: float
    max_neighbor_drop: float
    is_boundary: bool = False


class SensitivityAnalyzer:
    """Evaluates stability of strategy performance across parameter perturbations."""

    @staticmethod
    def compute_local_variance(parameter_scores: Mapping[float, float]) -> float:
        """Measure variance of objective scores across neighboring parameter choices."""
        if len(parameter_scores) < 2:
            return 0.0
        scores = list(parameter_scores.values())
        mean = sum(scores) / len(scores)
        return sum((s - mean) ** 2 for s in scores) / (len(scores) - 1)

    @staticmethod
    def select_stable_plateau_2d(
        x_values: Sequence[float],
        y_values: Sequence[float],
        score_matrix: NDArray[np.float64],
        std_penalty: float = 1.0,
        require_interior: bool = False,
    ) -> PlateauSelection:
        """Select parameters maximizing (local_mean - std_penalty * local_std) over 3x3 patches.

        Rejects isolated spikes (parameter cliffs) in favor of broad stable plateaus.
        When `require_interior=True` and the grid is at least 3x3, restricts candidates
        strictly to interior full 3x3 neighborhoods to prevent edge-clipping bias.
        """
        mat = np.asarray(score_matrix, dtype=np.float64)
        nx, ny = len(x_values), len(y_values)
        if mat.shape != (nx, ny) or nx == 0 or ny == 0:
            msg = f"score_matrix shape {mat.shape} does not match ({nx}, {ny})"
            raise ValueError(msg)

        use_interior = require_interior and nx >= 3 and ny >= 3
        i_indices = range(1, nx - 1) if use_interior else range(nx)
        j_indices = range(1, ny - 1) if use_interior else range(ny)

        best: PlateauSelection | None = None
        for i in i_indices:
            for j in j_indices:
                i_lo, i_hi = max(0, i - 1), min(nx, i + 2)
                j_lo, j_hi = max(0, j - 1), min(ny, j + 2)
                patch = mat[i_lo:i_hi, j_lo:j_hi]
                local_mean = float(np.mean(patch))
                local_std = float(np.std(patch, ddof=1)) if patch.size > 1 else 0.0
                plateau_score = local_mean - std_penalty * local_std

                center = float(mat[i, j])
                neighbors: list[float] = []
                for di, dj in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    ni, nj = i + di, j + dj
                    if 0 <= ni < nx and 0 <= nj < ny:
                        neighbors.append(float(mat[ni, nj]))
                max_drop = max((center - nb for nb in neighbors), default=0.0)
                is_boundary = i == 0 or i == nx - 1 or j == 0 or j == ny - 1

                candidate = PlateauSelection(
                    x_index=i,
                    y_index=j,
                    x_value=float(x_values[i]),
                    y_value=float(y_values[j]),
                    raw_score=center,
                    plateau_score=plateau_score,
                    local_mean=local_mean,
                    local_std=local_std,
                    max_neighbor_drop=max_drop,
                    is_boundary=is_boundary,
                )
                if best is None or candidate.plateau_score > best.plateau_score:
                    best = candidate

        assert best is not None
        return best
