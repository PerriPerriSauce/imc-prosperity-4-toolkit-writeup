"""Chart generation utilities using Matplotlib."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import matplotlib.pyplot as plt


class PerformanceCharts:
    """Standardized chart plotting routines for research reports and tearsheets."""

    @staticmethod
    def plot_equity_curve(
        equity_curve: Sequence[float],
        title: str = "Cumulative PnL Equity Curve",
        output_path: Path | str | None = None,
    ) -> None:
        """Render equity curve plot and optionally export to disk."""
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(equity_curve, label="Net PnL", color="#1f77b4", linewidth=1.5)
        ax.set_title(title)
        ax.set_xlabel("Ticks / Timestamps")
        ax.set_ylabel("PnL (Units)")
        ax.grid(True, linestyle="--", alpha=0.6)
        ax.legend()
        fig.tight_layout()

        if output_path is not None:
            path = Path(output_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            fig.savefig(path, dpi=300)
        plt.close(fig)
