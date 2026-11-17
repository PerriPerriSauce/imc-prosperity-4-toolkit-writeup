"""Risk modeling and inventory exposure assessment."""

from __future__ import annotations

from collections.abc import Sequence


class RiskAssessment:
    """Evaluates inventory risk, exposure durations, and tail risks."""

    @staticmethod
    def position_holding_time(positions: Sequence[int]) -> float:
        """Calculate percentage of simulation spent with non-zero inventory."""
        if not positions:
            return 0.0
        non_zero = sum(1 for p in positions if p != 0)
        return non_zero / len(positions)
