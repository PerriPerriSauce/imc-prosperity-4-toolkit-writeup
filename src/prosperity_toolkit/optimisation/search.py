"""Systematic search algorithms over strategy parameter spaces."""

from __future__ import annotations

import itertools
from collections.abc import Mapping, Sequence
from typing import Any


class GridSearchOptimizer:
    """Deterministic Cartesian grid generator."""

    @staticmethod
    def generate_grid(parameter_space: Mapping[str, Sequence[Any]]) -> list[dict[str, Any]]:
        """Produce list of discrete parameter combinations."""
        keys = list(parameter_space.keys())
        values = [parameter_space[k] for k in keys]
        combinations = itertools.product(*values)
        return [dict(zip(keys, combo, strict=True)) for combo in combinations]
