"""Build the self-contained HTML quantitative research portfolio tearsheet."""

from __future__ import annotations

from pathlib import Path

from prosperity_toolkit.visualisation.dashboard import ResearchDashboard


def main() -> None:
    """Load verified CSV metrics and render reports/dashboard.html."""
    tables_dir = Path("reports/tables")
    figures_dir = Path("reports/figures")
    output_path = Path("reports/dashboard.html")

    context = ResearchDashboard.load_portfolio_context(tables_dir=tables_dir)
    rendered = ResearchDashboard.build_html_tearsheet(
        context=context,
        output_path=output_path,
        figures_dir=figures_dir,
    )
    subs = context.get("submissions_queue_aware", [])
    total_pnl = sum(float(r["total_pnl"]) for r in subs)
    print(
        f"Built {rendered} ({rendered.stat().st_size:,d} bytes) from {len(subs)} OOS "
        f"submission rounds (sum queue_aware OOS PnL = {total_pnl:,.2f})."
    )


if __name__ == "__main__":
    main()
