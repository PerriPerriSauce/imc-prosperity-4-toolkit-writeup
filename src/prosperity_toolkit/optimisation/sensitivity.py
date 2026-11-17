"""Parameter sensitivity, cliff detection, and stability analysis."""

from __future__ import annotations

from collections.abc import Mapping


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
