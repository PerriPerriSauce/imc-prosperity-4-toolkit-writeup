"""Unit tests for ResearchDashboard Markdown and HTML tearsheet builders."""

from __future__ import annotations

from pathlib import Path

from prosperity_toolkit.visualisation.dashboard import ResearchDashboard


def test_render_markdown_summary_formats_values() -> None:
    md = ResearchDashboard.render_markdown_summary(
        {"Total PnL": 1234.5, "Fills": 42, "Mode": "queue_aware"},
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
        "day,split,fill_mode,strategy,total_pnl,ir_tick,block_sharpe_1k,pnl_to_max_dd,"
        "max_drawdown,total_trades,mean_latency_ms\n"
        "0,OOS,queue_aware,Round1Submission,91098.0,0.054445,9.3269,64.8384,1405.0,712,0.0195\n",
        encoding="utf-8",
    )
    (tables_dir / "r2_ablation_summary.csv").write_text(
        "split,fill_mode,strategy,total_pnl,ir_tick,block_sharpe_1k,pnl_to_max_dd,"
        "max_drawdown,total_fills,mean_latency_ms\n"
        "OOS,queue_aware,Round2Submission,94209.0,0.054659,8.2366,67.2441,1401.0,832,0.0281\n",
        encoding="utf-8",
    )
    (tables_dir / "r1_overfitting_gates.csv").write_text(
        "round,plateau_params,is_ir_tick,local_mean,local_std,n_eff,cscv_pbo,dsr_block,"
        "oos_pnl,oos_ir_tick,oos_block_sharpe_1k\n"
        "1,\"edge=2.0,skew=0.4\",0.058017,0.057878,0.000094,1.0216,0.1286,1.0,91098.0,0.054445,9.3269\n",
        encoding="utf-8",
    )
    (tables_dir / "r2_to_r5_overfitting_gates.csv").write_text(
        "round,plateau_params,is_ir_tick,local_mean,local_std,n_eff,cscv_pbo,dsr_block,"
        "oos_pnl,oos_ir_tick,oos_block_sharpe_1k\n"
        "2,\"edge=2.5,skew=0.4\",0.060523,0.060408,0.000107,1.0401,0.3,1.0,94209.0,0.054659,8.2366\n",
        encoding="utf-8",
    )
    (tables_dir / "r1_mc_risk_summary.csv").write_text(
        "strategy,n_sessions,n_steps,mean_pnl,std_pnl,median_pnl,var_95,cvar_95,prob_loss,"
        "mean_sharpe,mean_max_drawdown,worst_max_drawdown,prob_loss_ci95_upper\n"
        "Round1Submission_AdverseStress,40,1000,3783.5,2769.1,3307.0,-253.6,-2503.0,0.075,"
        "0.0224,3097.1,6179.5,0.1986\n",
        encoding="utf-8",
    )
    (tables_dir / "manual_challenges_summary.csv").write_text(
        "round,challenge,scenario,parameter,optimal_action,expected_metric,metric_unit,"
        "assumption_note\n"
        "R5,Extra! Extra!,Test<script>,lam=0.5,prune 4/9,855944.53,XIRECs,Demo note\n",
        encoding="utf-8",
    )

    tiny_png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\x0bIDATx\x9cc`\x00\x02"
        b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    (figs_dir / "manual_challenges_analysis.png").write_bytes(tiny_png)

    ctx = ResearchDashboard.load_portfolio_context(tables_dir=tables_dir)
    assert len(ctx["submissions_queue_aware"]) == 2
    assert len(ctx["overfitting_gates"]) == 2

    out_html = tmp_path / "dashboard.html"
    built = ResearchDashboard.build_html_tearsheet(
        context=ctx,
        output_path=out_html,
        figures_dir=figs_dir,
    )
    assert built.exists()
    text = built.read_text(encoding="utf-8")
    assert "+185,307.00" in text
    assert "IR_tick" in text
    assert "Sharpe (252)" not in text
    assert "Zero losing paths" not in text
    assert "data:image/png;base64," in text
    assert "Test&lt;script&gt;" in text
    assert "Not Live Portal Scores" in text
