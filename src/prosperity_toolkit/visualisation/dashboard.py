"""Summary dashboard reporting for backtest and parameter optimization runs."""

from __future__ import annotations

from collections.abc import Mapping


class ResearchDashboard:
    """Formats simulation summaries into formatted Markdown tables."""

    @staticmethod
    def render_markdown_summary(metrics: Mapping[str, float | str | int]) -> str:
        """Render a clean Markdown summary table."""
        lines = [
            "| Metric | Value |",
            "| :--- | :--- |",
        ]
        for k, v in metrics.items():
            if isinstance(v, float):
                formatted = f"{v:,.2f}"
            else:
                formatted = str(v)
            lines.append(f"| {k} | {formatted} |")
        return "\n".join(lines)
