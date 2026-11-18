"""Unit tests for ResearchDashboard Markdown and HTML tearsheet builders."""

from __future__ import annotations

from pathlib import Path

from prosperity_toolkit.visualisation.dashboard import ResearchDashboard


def test_render_markdown_summary_formats_values() -> None:
    md = ResearchDashboard.render_markdown_summary(
        {"Total PnL": 1234.5, "Fills": 42, "Mode": "queue_aware"}
    )
    assert "| Total PnL | 1,234.50 |" in md
    assert "| Fills | 42 |" in md
    assert "| Mode | queue_aware |" in md


def test_load_context_and_build_html_tearsheet(tmp_path: Path) -> None:
    tables_dir = tmp_path / "tables"
    figs_dir = tmp_path / "figures"
    tables_dir.mkdir()
    figs_dir.mkdir()

    (tables_dir / "r1_ablation_summary.csv").write_text(
        "day,split,fill_mode,strategy,total_pnl,max_drawdown,sharpe_ratio,total_trades,"
        "mean_latency_ms\n"
        "0,OOS,queue_aware,Round1Submission,22157.0,267.0,1.1894,1003,0.0388\n",
        encoding="utf-8",
    )
    (tables_dir / "r2_ablation_summary.csv").write_text(
        "split,fill_mode,strategy,total_pnl,sharpe_252,max_drawdown,total_fills,mean_latency_ms\n"
        "OOS,queue_aware,Round2Submission,27463.0,1.3972,419.5,1022,0.0384\n",
        encoding="utf-8",
    )
    (tables_dir / "r2_to_r5_overfitting_gates.csv").write_text(
        "round,plateau_params,is_sharpe_252,local_mean,local_std,cscv_pbo,dsr,oos_pnl,"
        "oos_sharpe_252\n"
        "2,\"edge=3.5,skew=0.75\",1.3715,1.3602,0.0176,0.0,1.0,27463.0,1.3972\n",
        encoding="utf-8",
    )
    (tables_dir / "manual_challenges_summary.csv").write_text(
        "round,challenge,scenario,parameter,optimal_action,expected_metric,metric_unit,"
        "assumption_note\n"
        "R5,Extra! Extra!,Test<script>,lam=0.5,prune 6/9,1000.0,XIRECs,Demo note\n",
        encoding="utf-8",
    )

    # Minimal 1x1 PNG bytes to verify base64 figure embedding
    tiny_png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\x0bIDATx\x9cc`\x00\x02"
        b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    (figs_dir / "manual_challenges_analysis.png").write_bytes(tiny_png)

    ctx = ResearchDashboard.load_portfolio_context(tables_dir=tables_dir)
    assert len(ctx["submissions_queue_aware"]) == 2
    assert len(ctx["overfitting_gates"]) == 1

    out_html = tmp_path / "dashboard.html"
    built = ResearchDashboard.build_html_tearsheet(
        context=ctx, output_path=out_html, figures_dir=figs_dir
    )
    assert built.exists()
    text = built.read_text(encoding="utf-8")
    assert "+49,620.00" in text
    assert "data:image/png;base64," in text
    assert "Test&lt;script&gt;" in text
    assert "Not Live Portal Scores" in text
