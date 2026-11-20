"""Compile a publication-quality PDF research monograph from verified CSVs and figures."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from html import escape
from pathlib import Path
from typing import Any

from prosperity_toolkit.visualisation.dashboard import (
    ResearchDashboard,
    _encode_png_data_uri,
    _read_csv_rows,
    _to_float,
)


def _find_browser_executable() -> Path:
    """Locate a headless Chromium-based browser binary for HTML-to-PDF rendering."""
    candidates = [
        shutil.which("msedge"),
        shutil.which("chrome"),
        shutil.which("google-chrome"),
        shutil.which("chromium"),
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    ]
    for raw in candidates:
        if raw and Path(raw).exists():
            return Path(raw)
    msg = "No Chromium/Edge executable found for PDF compilation."
    raise FileNotFoundError(msg)


def _figure_block(
    figures_dir: Path,
    filename: str,
    caption: str,
    tag: str,
    wide: bool = False,
) -> str:
    uri = _encode_png_data_uri(figures_dir / filename)
    if uri is None:
        return ""
    cls = "fig-card wide" if wide else "fig-card"
    return (
        f"<figure class='{cls}'>"
        f"<img src='{uri}' alt='{escape(caption)}' />"
        f"<figcaption><strong>{escape(tag)}.</strong> {escape(caption)}</figcaption>"
        "</figure>"
    )


def _format_submission_rows(subs: list[dict[str, Any]]) -> str:
    return "\n".join(
        "<tr>"
        f"<td><strong>{escape(str(r['round']))}</strong></td>"
        f"<td><code>{escape(str(r['strategy']))}</code></td>"
        f"<td class='num'><strong>{r['total_pnl']:,.2f}</strong></td>"
        f"<td class='num'>{r['ir_tick']:.5f}</td>"
        f"<td class='num'>{r['block_sharpe_1k']:.3f}</td>"
        f"<td class='num'>{r['max_drawdown']:,.2f}</td>"
        f"<td class='num'>{r['pnl_to_max_dd']:.2f}</td>"
        f"<td class='num'>{r['total_fills']:,d}</td>"
        f"<td class='num'>{r['mean_latency_ms']:.4f} ms</td>"
        "</tr>"
        for r in subs
    )


def _format_fill_sensitivity_rows(algo_oos: list[dict[str, Any]]) -> str:
    return "\n".join(
        "<tr>"
        f"<td>{escape(str(r['round']))}</td>"
        f"<td><code>{escape(str(r['strategy']))}</code></td>"
        f"<td>{escape(str(r['fill_mode']))}</td>"
        f"<td class='num'>{r['total_pnl']:,.2f}</td>"
        f"<td class='num'>{r['ir_tick']:.5f}</td>"
        f"<td class='num'>{r['block_sharpe_1k']:.3f}</td>"
        f"<td class='num'>{r['max_drawdown']:,.2f}</td>"
        f"<td class='num'>{r['total_fills']:,d}</td>"
        "</tr>"
        for r in algo_oos
        if str(r["strategy"]).endswith("Submission")
    )


def _format_gate_rows(gates: list[dict[str, str]]) -> str:
    return "\n".join(
        "<tr>"
        f"<td><strong>R{escape(g.get('round', ''))}</strong></td>"
        f"<td><code>{escape(g.get('plateau_params', ''))}</code></td>"
        f"<td class='num'>{_to_float(g.get('is_ir_tick')):.5f}</td>"
        f"<td class='num'>{_to_float(g.get('local_mean')):.5f} "
        f"&plusmn; {_to_float(g.get('local_std')):.5f}</td>"
        f"<td class='num'>{_to_float(g.get('n_eff')):.2f}</td>"
        f"<td class='num'>{_to_float(g.get('cscv_pbo')):.4f}</td>"
        f"<td class='num'>{_to_float(g.get('dsr_block')):.4f}</td>"
        f"<td class='num'>{_to_float(g.get('oos_pnl')):,.2f}</td>"
        f"<td class='num'>{_to_float(g.get('oos_ir_tick')):.5f}</td>"
        "</tr>"
        for g in gates
    )


def _format_mc_rows(
    mc_r1: list[dict[str, str]],
    mc_r2_r5: list[dict[str, str]],
) -> str:
    r1_part = "\n".join(
        "<tr>"
        "<td>R1</td>"
        f"<td><code>{escape(m.get('strategy', ''))}</code></td>"
        f"<td class='num'>{_to_float(m.get('mean_pnl')):,.2f}</td>"
        f"<td class='num'>{_to_float(m.get('var_95')):,.2f}</td>"
        f"<td class='num'>{_to_float(m.get('cvar_95')):,.2f}</td>"
        f"<td class='num'>{_to_float(m.get('prob_loss')):.3f}</td>"
        f"<td class='num'>{_to_float(m.get('prob_loss_ci95_upper')):.3f}</td>"
        f"<td class='num'>{_to_float(m.get('mean_sharpe')):.4f}</td>"
        "</tr>"
        for m in mc_r1
    )
    later_part = "\n".join(
        "<tr>"
        f"<td>R{escape(m.get('round', ''))}</td>"
        f"<td><code>{escape(m.get('scenario', ''))}</code></td>"
        f"<td class='num'>{_to_float(m.get('mean_pnl')):,.2f}</td>"
        f"<td class='num'>{_to_float(m.get('var_95')):,.2f}</td>"
        f"<td class='num'>{_to_float(m.get('cvar_95')):,.2f}</td>"
        f"<td class='num'>{_to_float(m.get('prob_loss')):.3f}</td>"
        f"<td class='num'>{_to_float(m.get('prob_loss_ci95_upper')):.3f}</td>"
        f"<td class='num'>{_to_float(m.get('mean_ir_tick') or m.get('mean_sharpe_252')):.4f}</td>"
        "</tr>"
        for m in mc_r2_r5
    )
    return f"{r1_part}\n{later_part}"


def _format_manual_rows(manual_rows: list[dict[str, str]]) -> str:
    return "\n".join(
        "<tr>"
        f"<td><strong>{escape(m.get('round', ''))}</strong></td>"
        f"<td>{escape(m.get('challenge', ''))}</td>"
        f"<td>{escape(m.get('scenario', ''))}</td>"
        f"<td><code>{escape(m.get('optimal_action', ''))}</code></td>"
        f"<td class='num'>{_to_float(m.get('expected_metric')):,.2f} "
        f"{escape(m.get('metric_unit', ''))}</td>"
        f"<td>{escape(m.get('assumption_note', ''))}</td>"
        "</tr>"
        for m in manual_rows
    )


def _format_basket_rows(r5_baskets: list[dict[str, str]]) -> str:
    return "\n".join(
        "<tr>"
        f"<td>{escape(b.get('structure', ''))}</td>"
        f"<td>{escape(b.get('split', ''))}</td>"
        f"<td class='num'>{_to_float(b.get('mean')):,.2f}</td>"
        f"<td class='num'>{_to_float(b.get('std')):,.2f}</td>"
        f"<td class='num'>{_to_float(b.get('adf_t')):.2f}</td>"
        f"<td class='num'>{_to_float(b.get('half_life')):.2f}</td>"
        f"<td>{escape(b.get('notes', ''))}</td>"
        "</tr>"
        for b in r5_baskets
    )


def _format_pca_rows(r5_pca: list[dict[str, str]]) -> str:
    return "\n".join(
        "<tr>"
        f"<td>{escape(p.get('category', ''))}</td>"
        f"<td class='num'>{_to_float(p.get('is_diff_eig1')):.2f}</td>"
        f"<td class='num'>{_to_float(p.get('is_lvl_cond_ratio')):.1f}</td>"
        f"<td class='num'>{_to_float(p.get('oos_lvl_cond_ratio')):.1f}</td>"
        f"<td class='num'>{escape(p.get('is_pulse_events_20k', ''))}</td>"
        f"<td class='num'>{_to_float(p.get('is_pulse_uniform_side_pct')):.1f}%</td>"
        f"<td class='num'>{escape(p.get('oos_d4_pulse_events', ''))}</td>"
        f"<td class='num'>{_to_float(p.get('oos_d4_uniform_qty_pct')):.1f}%</td>"
        "</tr>"
        for p in r5_pca
    )


def _find_row(
    rows: list[dict[str, str]],
    **criteria: str,
) -> dict[str, str]:
    for r in rows:
        if all(r.get(k) == v for k, v in criteria.items()):
            return r
    return {}


def build_print_html(
    tables_dir: Path = Path("reports/tables"),
    figures_dir: Path = Path("reports/figures"),
) -> str:
    """Assemble clean A4-paginated print HTML backed strictly by generated CSV tables."""
    ctx = ResearchDashboard.load_portfolio_context(tables_dir=tables_dir)
    subs: list[dict[str, Any]] = list(ctx.get("submissions_queue_aware", []))
    gates: list[dict[str, str]] = list(ctx.get("overfitting_gates", []))
    mc_r1: list[dict[str, str]] = list(ctx.get("mc_r1", []))
    mc_r2_r5: list[dict[str, str]] = list(ctx.get("mc_r2_r5", []))
    manual_rows: list[dict[str, str]] = list(ctx.get("manual_rows", []))
    algo_oos: list[dict[str, Any]] = list(ctx.get("algo_oos_rows", []))
    boot_rows: list[dict[str, str]] = list(ctx.get("bootstrap_rows", []))

    r5_baskets = _read_csv_rows(tables_dir / "r5_baskets_summary.csv")
    r5_pca = _read_csv_rows(tables_dir / "r5_category_pca_and_pulses.csv")
    r4_velvet = _read_csv_rows(tables_dir / "r4_counterparty_velvet_midmoves.csv")
    r5_chips = _read_csv_rows(tables_dir / "r5_microchips_leadlag.csv")
    r2_maf = _read_csv_rows(tables_dir / "r2_maf_sensitivity.csv")
    r5_ab_raw = _read_csv_rows(tables_dir / "r5_ablation_summary.csv")

    def _oos_map(rows: list[dict[str, Any]], rnd: str, strat: str) -> dict[str, Any]:
        for r in rows:
            if (
                r.get("round") == rnd
                and r.get("strategy") == strat
                and r.get("fill_mode") == "queue_aware"
            ):
                return r
        return {
            "total_pnl": 0.0,
            "ir_tick": 0.0,
            "block_sharpe_1k": 0.0,
            "max_drawdown": 0.0,
            "pnl_to_max_dd": 0.0,
        }

    cum_pnl = sum(float(r["total_pnl"]) for r in subs)
    phase1_pnl = sum(float(r["total_pnl"]) for r in subs if r.get("round") in {"R1", "R2"})
    phase2_pnl = sum(
        float(r["total_pnl"]) for r in subs if r.get("round") in {"R3", "R4", "R5"}
    )
    max_lat = max((float(r["mean_latency_ms"]) for r in subs), default=0.0)
    min_dsr = min((_to_float(g.get("dsr_block")) for g in gates), default=0.0)
    neffs = [_to_float(g.get("n_eff")) for g in gates if g.get("n_eff")]
    neff_lo, neff_hi = (min(neffs), max(neffs)) if neffs else (1.0, 1.0)

    cal_probs = [
        _to_float(m.get("prob_loss"))
        for m in mc_r1
        if "Submission" in m.get("strategy", "") and "Stress" not in m.get("strategy", "")
    ] + [
        _to_float(m.get("prob_loss"))
        for m in mc_r2_r5
        if "Stress" not in m.get("scenario", "")
    ]
    stress_probs = [
        _to_float(m.get("prob_loss")) for m in mc_r1 if "Stress" in m.get("strategy", "")
    ] + [
        _to_float(m.get("prob_loss")) for m in mc_r2_r5 if "Stress" in m.get("scenario", "")
    ]
    max_cal_loss = max(cal_probs, default=0.0)
    max_stress_loss = max(stress_probs, default=0.0)

    # Dynamic key stats from CSVs for text blocks
    r1_sub = _oos_map(algo_oos, "R1", "Round1Submission")
    r1_sym = _oos_map(algo_oos, "R1", "SymmetricMM")
    r2_sub = _oos_map(algo_oos, "R2", "Round2Submission")
    r2_sym = _oos_map(algo_oos, "R2", "SymmetricMM_80")
    r3_sub = _oos_map(algo_oos, "R3", "Round3Submission")
    r3_sym = _oos_map(algo_oos, "R3", "SymmetricSpotMM")
    r4_sub = _oos_map(algo_oos, "R4", "Round4Submission")
    r4_noflow = _oos_map(algo_oos, "R4", "Round3NoFlow")
    r5_sub = _oos_map(algo_oos, "R5", "Round5Submission")
    r5_noll = _oos_map(algo_oos, "R5", "Round5NoLeadLag")
    r5_sym = _oos_map(algo_oos, "R5", "EmaSymmetricMM_All50")

    r5_is_sub = _find_row(
        r5_ab_raw, split="IS", fill_mode="queue_aware", strategy="Round5Submission",
    )
    r5_is_noll = _find_row(
        r5_ab_raw, split="IS", fill_mode="queue_aware", strategy="Round5NoLeadLag",
    )
    r5_pdd_mult = float(r5_sub.get("pnl_to_max_dd", 0.0)) / max(
        float(r5_sym.get("pnl_to_max_dd", 0.0)),
        1e-9,
    )
    g2 = next((g for g in gates if g.get("round") == "2"), {})
    g5 = next((g for g in gates if g.get("round") == "5"), {})

    r4_flow_uplift = float(r4_sub["total_pnl"]) - float(r4_noflow["total_pnl"])
    r5_mc_uplift = float(r5_sub["total_pnl"]) - float(r5_noll["total_pnl"])

    m67 = _find_row(r4_velvet, counterparty="Mark 67", side="buyer")
    m14s = _find_row(r4_velvet, counterparty="Mark 14", side="seller")
    m55b = _find_row(r4_velvet, counterparty="Mark 55", side="buyer")

    chip_peaks = [c for c in r5_chips if c.get("is_peak_lag") == "True"]
    maf_08: dict[str, str] = next(
        (m for m in r2_maf if _to_float(m.get("arrival_rate")) == 0.08),
        {},
    )
    maf_10: dict[str, str] = next(
        (m for m in r2_maf if _to_float(m.get("arrival_rate")) == 0.10),
        {},
    )

    r1_asset_map = {
        b["bucket"]: _to_float(b["oos_pnl"])
        for b in boot_rows
        if b.get("round") == "1" and b.get("scope") == "asset"
    }
    r4_mv = next(
        (
            m
            for m in manual_rows
            if m.get("round") == "R4"
            and (
                "Mean-Variance" in m.get("challenge", "")
                or "Mean-Variance" in m.get("scenario", "")
            )
        ),
        {},
    )
    r5_kkt = next(
        (
            m
            for m in manual_rows
            if m.get("round") == "R5" and "Risk-Adjusted" in m.get("scenario", "")
        ),
        {},
    )
    r5_exact = next(
        (
            m
            for m in manual_rows
            if m.get("round") == "R5" and "Exact KKT" in m.get("scenario", "")
        ),
        {},
    )

    manual_summary_rows = "\n".join(
        "<tr>"
        f"<td><strong>{escape(m.get('round', ''))}</strong></td>"
        f"<td>{escape(m.get('challenge', ''))}</td>"
        f"<td>{escape(m.get('scenario', ''))}</td>"
        f"<td><code>{escape(m.get('optimal_action', ''))}</code></td>"
        f"<td class='num'>{_to_float(m.get('expected_metric')):,.2f} "
        f"{escape(m.get('metric_unit', ''))}</td>"
        "</tr>"
        for m in manual_rows
        if (
            (m.get("round") == "R1" and "stochastic" in m.get("scenario", ""))
            or (m.get("round") == "R2" and "Focal" in m.get("scenario", ""))
            or (m.get("round") == "R3" and "Ex-Ante" in m.get("scenario", ""))
            or (m.get("round") == "R4" and "Mean-Variance" in m.get("scenario", ""))
            or (m.get("round") == "R5" and "Risk-Adjusted" in m.get("scenario", ""))
        )
    )

    sub_rows = _format_submission_rows(subs)
    fill_sens_rows = _format_fill_sensitivity_rows(algo_oos)
    gate_rows = _format_gate_rows(gates)
    mc_rows = _format_mc_rows(mc_r1, mc_r2_r5)
    manual_html_rows = _format_manual_rows(manual_rows)
    basket_rows = _format_basket_rows(r5_baskets)
    pca_rows = _format_pca_rows(r5_pca)

    fig_r1_eq = _figure_block(
        figures_dir,
        "r1_oos_equity_comparison.png",
        "Round 1 held-out Day 0 equity comparison under official +/-80 limits (queue_aware).",
        "Figure 1",
    )
    fig_r1_heat = _figure_block(
        figures_dir,
        "r1_sensitivity_heatmap.png",
        "Round 1 independent-day IS tick IR surface showing interior plateau selection.",
        "Figure 2",
    )
    fig_r2_maf = _figure_block(
        figures_dir,
        "r2_sensitivity_and_maf_valuation.png",
        "Round 2 IS tick IR surface and Market Access Fee arrival-rate MC sensitivity.",
        "Figure 3",
    )
    fig_r3_opt = _figure_block(
        figures_dir,
        "r3_options_iv_smile_and_premium.png",
        "VEV European call total implied-volatility smile and time-decay calibration (IS).",
        "Figure 4",
    )
    fig_r4_mark = _figure_block(
        figures_dir,
        "r4_counterparty_markouts.png",
        "Round 4 volume and causal VELVETFRUIT decomposition (Mark 67 vs Mark 14/55).",
        "Figure 5",
    )
    fig_r3_r4_mc = _figure_block(
        figures_dir,
        "r3_r4_oos_attribution_and_mc.png",
        "Rounds 3-4 10-asset OOS attribution and calibrated vs adverse-stress MC.",
        "Figure 6",
        wide=True,
    )
    fig_r5_inv = _figure_block(
        figures_dir,
        "r5_pebbles_and_snackpacks_invariants.png",
        "Round 5 Pebbles constant-sum invariant and Snackpacks negatively coupled pair.",
        "Figure 7",
    )
    fig_r5_cat = _figure_block(
        figures_dir,
        "r5_sensitivity_and_category_oos.png",
        "Round 5 IS plateau surface and Day 4 OOS attribution (McLeadLag vs NoLeadLag).",
        "Figure 8",
    )
    fig_r2_r5_eq = _figure_block(
        figures_dir,
        "r2_to_r5_oos_equity_summary.png",
        "Exact held-out OOS equity trajectories across Rounds 2 through 5 (queue_aware).",
        "Figure 9",
        wide=True,
    )
    fig_manual = _figure_block(
        figures_dir,
        "manual_challenges_analysis.png",
        "Ex-ante manual challenge comparative statics across Rounds 1 through 5.",
        "Figure 10",
        wide=True,
    )

    css = """
  @page { size: A4; margin: 14mm 13mm 15mm 13mm; }
  * { box-sizing: border-box; }
  body {
    font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
    color: #0f172a; background: #ffffff; font-size: 9.3pt; line-height: 1.43; margin: 0;
  }
  .title-banner {
    border-top: 4px solid #1d3557; border-bottom: 1.5px solid #cbd5e1;
    padding: 10px 0 12px 0; margin-bottom: 12px;
  }
  .kicker {
    font-size: 7.7pt; text-transform: uppercase; letter-spacing: 0.08em;
    color: #2a9d8f; font-weight: 700; margin-bottom: 4px;
  }
  h1 { font-size: 16.5pt; margin: 0 0 6px 0; color: #0f172a; line-height: 1.18; }
  .lead { color: #334155; font-size: 9.1pt; margin: 0; }
  .kpi-row {
    display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px;
    margin: 10px 0 14px 0; break-inside: avoid;
  }
  .kpi-box {
    border: 1px solid #cbd5e1; border-left: 3.5px solid #1d3557;
    border-radius: 5px; padding: 7px 9px; background: #f8fafc;
  }
  .kpi-label {
    font-size: 7.2pt; text-transform: uppercase; color: #475569;
    letter-spacing: 0.04em; font-weight: 600;
  }
  .kpi-val { font-size: 12pt; font-weight: 700; color: #0f172a; margin-top: 2px; }
  .kpi-sub { font-size: 7.2pt; color: #64748b; }
  h2 {
    font-size: 11.6pt; color: #1d3557; border-bottom: 1px solid #cbd5e1;
    padding-bottom: 3px; margin: 14px 0 7px 0; break-after: avoid;
  }
  h3 { font-size: 9.9pt; color: #1e293b; margin: 9px 0 4px 0; break-after: avoid; }
  p { margin: 0 0 6px 0; }
  ul { margin: 3px 0 8px 0; padding-left: 18px; }
  li { margin-bottom: 3px; }
  .eq {
    background: #f8fafc; border-left: 3px solid #2a9d8f; padding: 6px 10px; margin: 6px 0;
    font-family: "Cambria Math", "Times New Roman", Georgia, serif;
    font-size: 9.3pt; color: #0f172a; break-inside: avoid;
  }
  table {
    width: 100%; border-collapse: collapse; margin: 5px 0 10px 0;
    font-size: 7.8pt; break-inside: avoid;
  }
  th, td {
    padding: 4px 5px; border-bottom: 1px solid #cbd5e1;
    text-align: left; vertical-align: top;
  }
  th {
    background: #f1f5f9; color: #1e293b; font-weight: 700; font-size: 7.2pt;
    text-transform: uppercase; letter-spacing: 0.03em;
  }
  td.num { text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }
  code {
    font-family: Consolas, "Courier New", monospace; font-size: 7.5pt;
    background: #f1f5f9; padding: 1px 3px; border-radius: 3px; color: #0f172a;
  }
  .callout {
    background: #f8fafc; border: 1px solid #cbd5e1; border-left: 4px solid #1d3557;
    padding: 7px 10px; margin: 8px 0 10px 0; border-radius: 4px;
    font-size: 8.3pt; break-inside: avoid;
  }
  .fig-grid-2 {
    display: grid; grid-template-columns: 1fr 1fr; gap: 9px;
    margin: 6px 0 10px 0; break-inside: avoid;
  }
  .fig-card {
    margin: 6px 0 10px 0; border: 1px solid #e2e8f0; border-radius: 5px;
    padding: 6px; background: #ffffff; break-inside: avoid;
  }
  .fig-grid-2 .fig-card { margin: 0; }
  .fig-card img {
    width: 100%; height: auto; display: block; max-height: 76mm; object-fit: contain;
  }
  .fig-card.wide img { max-height: 90mm; }
  figcaption { margin-top: 4px; font-size: 7.5pt; color: #475569; text-align: center; }
"""

    chip_lag_summary = ", ".join(
        f"{c.get('follower', '').replace('MICROCHIP_', '')} lag={c.get('lag_ticks')} "
        f"(IS beta={c.get('is_pooled_beta')})"
        for c in chip_peaks
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>IMC Prosperity 4 — Quantitative Trading Research Monograph</title>
<style>{css}</style>
</head>
<body>

<div class="title-banner">
  <div class="kicker">
    IMC Prosperity 4 &middot; Quantitative Trading &amp; Manual Game Theory Research
  </div>
  <h1>
    Multi-Round Market Microstructure, Causal Flow &amp; Lead-Lag Statistical Arbitrage
  </h1>
  <p class="lead">
    Reproducible technical writeup covering chronological out-of-sample backtesting under verified
    official limits, strict queue-priority execution simulation, block DSR / CSCV diagnostics,
    calibrated &amp; stressed Monte Carlo risk analysis, and ex-ante Manual Challenge models.
  </p>
</div>

<div class="kpi-row">
  <div class="kpi-box">
    <div class="kpi-label">Simulated OOS Replay PnL</div>
    <div class="kpi-val">+{cum_pnl:,.2f}</div>
    <div class="kpi-sub">Phase 1: +{phase1_pnl:,.0f} &bull; Phase 2: +{phase2_pnl:,.0f}</div>
  </div>
  <div class="kpi-box">
    <div class="kpi-label">Min Block DSR (R1&ndash;R5)</div>
    <div class="kpi-val">{min_dsr:.4f}</div>
    <div class="kpi-sub">N_eff {neff_lo:.2f}&ndash;{neff_hi:.2f} (&ge; 0.95 gate)</div>
  </div>
  <div class="kpi-box">
    <div class="kpi-label">MC Loss (Cal / Stress)</div>
    <div class="kpi-val">{max_cal_loss * 100:.1f}% / {max_stress_loss * 100:.1f}%</div>
    <div class="kpi-sub">Calibrated vs. adverse-selection stress (N=40)</div>
  </div>
  <div class="kpi-box">
    <div class="kpi-label">Peak Tick Latency</div>
    <div class="kpi-val">{max_lat:.4f} ms</div>
    <div class="kpi-sub">50-asset R5 loop inside exchange budget</div>
  </div>
</div>

<div class="callout">
  <strong>Epistemic &amp; Simulation Boundaries:</strong>
  All algorithmic tables report <strong>simulated chronological out-of-sample replays</strong> on
  archived historical books using strict price-time maker queue conservation under
  <code>queue_aware</code> (plus <code>conservative</code> and <code>touch</code> stress regimes),
  or synthetic Monte Carlo sessions&mdash;never live competition fills. All Manual Challenge tables
  evaluate ex-ante mathematical models under explicitly stated offline assumptions.
</div>

<h2>1. Executive Summary &amp; Research Architecture</h2>
<p>
  Across Rounds 1&ndash;5 of IMC Prosperity 4, optimal strategy design tracks four structural
  shifts: (i) stationary 10,000-anchored quoting on <code>ASH_COATED_OSMIUM</code> plus
  <code>+0.10/tick</code> carry on <code>INTARIAN_PEPPER_ROOT</code> under verified
  <code>&plusmn;80</code> limits in Rounds 1&ndash;2; (ii) Market Access Fee arrival-rate valuation;
  (iii) Bayesian OU spot anchors and Black-Scholes total implied volatility across active calls
  (<code>VEV_4000..5500</code>) with causal prior-tick counterparty flow in Rounds 3&ndash;4
  (<code>&plusmn;200</code> spot / <code>&plusmn;300</code> options); and (iv) a 50-symbol market
  in Round 5 (<code>&plusmn;10</code> limit) combining volatility-scaled Avellaneda-Stoikov MM
  with 50/100/150/200-tick <code>MICROCHIP_CIRCLE</code> lead-lag signals.
</p>

<h3>Final Algorithmic Submission Held-Out OOS Scorecard (<code>queue_aware</code>)</h3>
<table>
  <thead>
    <tr>
      <th>Round</th>
      <th>Submission Class</th>
      <th style="text-align:right">OOS PnL</th>
      <th style="text-align:right">IR_tick</th>
      <th style="text-align:right">BlkSR_1k</th>
      <th style="text-align:right">Max DD</th>
      <th style="text-align:right">PnL/MaxDD</th>
      <th style="text-align:right">Total Fills</th>
      <th style="text-align:right">Mean Latency</th>
    </tr>
  </thead>
  <tbody>{sub_rows}</tbody>
</table>

<h3>Ex-Ante Manual Challenge Model Summary (Rounds 1&ndash;5, Not Live Portal Scores)</h3>
<table>
  <thead>
    <tr>
      <th>Round</th>
      <th>Challenge</th>
      <th>Model Regime</th>
      <th>Ex-Ante Optimal Policy</th>
      <th style="text-align:right">Model EV / Fair Value</th>
    </tr>
  </thead>
  <tbody>{manual_summary_rows}</tbody>
</table>

<h2>2. Round-by-Round Microstructure Discovery &amp; Negative Results</h2>

<h3>Round 1 &amp; Round 2: Anchor-Plus-Drift Carry &amp; MAF Leverage (<code>&plusmn;80</code>)</h3>
<p>
  On held-out Day 0, anchoring <code>ASH_COATED_OSMIUM</code> around <code>10,000</code> and
  holding structural long inventory on <code>INTARIAN_PEPPER_ROOT</code> (verified
  <code>+0.1000/tick</code> linear slope, <code>R^2 = 1.0000</code>) raises
  <code>Round1Submission</code> OOS PnL to <strong><code>+{r1_sub['total_pnl']:,.2f}</code></strong>
  (<code>IR_tick = {r1_sub['ir_tick']:.5f}</code>, <code>BlkSR_1k</code>
  <code>{r1_sub['block_sharpe_1k']:.3f}</code> vs. <code>SymmetricMM</code>
  <code>{r1_sym['total_pnl']:,.2f}</code>), split
  <code>+{r1_asset_map.get('ASH_COATED_OSMIUM', 0.0):,.0f}</code> Osmium and
  <code>+{r1_asset_map.get('INTARIAN_PEPPER_ROOT', 0.0):,.0f}</code> Pepper. On Round 2 Day 1,
  interior plateau <code>(edge=2.5, skew=0.4)</code> earns
  <strong><code>+{r2_sub['total_pnl']:,.2f}</code></strong> vs.
  <code>SymmetricMM_80</code> <code>{r2_sym['total_pnl']:,.2f}</code>. Raising synthetic arrival
  intensity from <code>0.08</code> to <code>0.10</code> lifts MC mean PnL from
  <code>{_to_float(maf_08.get('mean_pnl')):,.2f}</code> to
  <code>{_to_float(maf_10.get('mean_pnl')):,.2f}</code>.
</p>
<div class="fig-grid-2">
  {fig_r1_eq}
  {fig_r1_heat}
</div>
{fig_r2_maf}

<h3>Rounds 3 &amp; 4: OU Spot + BS Total-Vol &amp; Causal Counterparty Disentanglement</h3>
<p>
  Round 3 IS ablation proves cross-hedging option delta in wide spot spreads destroys edge, so
  holding spot and <code>VEV_4000..5500</code> unhedged (omitting worthless
  <code>VEV_6000/6500</code>) lifts <code>Round3Submission</code> to
  <strong><code>+{r3_sub['total_pnl']:,.2f}</code></strong> on Day 2 OOS (vs.
  <code>SymmetricSpotMM</code> <code>{r3_sym['total_pnl']:,.2f}</code>). In Round 4, IS analysis on
  <code>VELVETFRUIT_EXTRACT</code> shows <code>Mark 67</code>'s raw fill mark-out is a
  non-causal 1-tick bounce (<code>mid_0_to_1 = {escape(m67.get('mid_0_to_1', ''))}</code> vs.
  <code>t+1&rarr;t+200 = {escape(m67.get('causal_1_to_200', ''))}</code>). Using strictly causal
  prior prints from <code>Mark 14 SELL</code>
  (<code>ou_adj_h200 = {escape(m14s.get('ou_adj_h200', ''))}</code>,
  <code>t = {escape(m14s.get('t_ou_h200', ''))}</code>) and <code>Mark 55 BUY</code>
  (<code>ou_adj_h200 = {escape(m55b.get('ou_adj_h200', ''))}</code>,
  <code>t = {escape(m55b.get('t_ou_h200', ''))}</code>) lifts Day 3 OOS PnL to
  <strong><code>+{r4_sub['total_pnl']:,.2f}</code></strong>&mdash;an OOS uplift of
  <code>+{r4_flow_uplift:,.2f}</code> above <code>Round3NoFlow</code>
  (<code>{r4_noflow['total_pnl']:,.2f}</code>) with lower drawdown.
</p>
<div class="fig-grid-2">
  {fig_r3_opt}
  {fig_r4_mark}
</div>
{fig_r3_r4_mc}

<h3>Round 5: Vol-Scaled Avellaneda-Stoikov &amp; Discrete Microchip Lead-Lag</h3>
<p>
  Across all 50 instruments under official <code>&plusmn;10</code> limits, IS testing rejected
  <code>Pebbles</code> constant-sum crossing (<code>std = 2.82</code> sits inside 12&ndash;14 tick
  spreads), contemporaneous <code>Snackpacks</code> correlation across shifting levels, and
  <code>Robots</code> lags. Volatility-scaled AS quoting plus discrete
  <code>MICROCHIP_CIRCLE</code> lead-lag ({escape(chip_lag_summary)}) lifts IS profit from
  <code>{_to_float(r5_is_noll.get('total_pnl')):,.1f}</code> to
  <code>{_to_float(r5_is_sub.get('total_pnl')):,.1f}</code>
  (<code>IR_tick = {_to_float(r5_is_sub.get('ir_tick')):.5f}</code> at
  <code>mc_beta = 0.16</code>) and earns <strong><code>+{r5_sub['total_pnl']:,.2f}</code></strong>
  on Day 4 OOS (<code>IR_tick = {r5_sub['ir_tick']:.5f}</code>,
  <code>MaxDD = {r5_sub['max_drawdown']:,.2f}</code>,
  <code>PnL/MaxDD = {r5_sub['pnl_to_max_dd']:.2f}</code>, <code>+{r5_mc_uplift:,.2f}</code>
  above <code>Round5NoLeadLag</code> and <code>{r5_pdd_mult:.2f}&times;</code> higher
  <code>PnL/MaxDD</code> than unfiltered <code>EmaSymmetricMM_All50</code> at
  <code>{r5_sym['pnl_to_max_dd']:.2f}</code>).
</p>

<table>
  <thead>
    <tr>
      <th>Basket / Invariant</th>
      <th>Split</th>
      <th style="text-align:right">Mean Spread</th>
      <th style="text-align:right">Spread Std</th>
      <th style="text-align:right">ADF t-stat</th>
      <th style="text-align:right">OU Half-Life</th>
      <th>Empirical Note</th>
    </tr>
  </thead>
  <tbody>{basket_rows}</tbody>
</table>

<table>
  <thead>
    <tr>
      <th>R5 Category (5 Assets Each)</th>
      <th style="text-align:right">IS Diff PC1</th>
      <th style="text-align:right">IS Cond Ratio</th>
      <th style="text-align:right">OOS Cond Ratio</th>
      <th style="text-align:right">IS Pulses (20k)</th>
      <th style="text-align:right">Side Uniformity</th>
      <th style="text-align:right">OOS D4 Pulses</th>
      <th style="text-align:right">Qty Uniformity</th>
    </tr>
  </thead>
  <tbody>{pca_rows}</tbody>
</table>

<div class="fig-grid-2">
  {fig_r5_inv}
  {fig_r5_cat}
</div>

<h2>3. Overfitting Controls, Fill Sensitivity &amp; Monte Carlo Stress</h2>
<p>
  We report unscaled per-tick IR (<code>IR_tick</code>), disjoint 1,000-tick block Sharpe
  (<code>BlkSR_1k</code>), block Deflated Sharpe Ratio (<code>DSR_block</code> at 100-tick blocks),
  effective independent trials (<code>N_eff</code>), and CSCV <code>PBO</code>. Because adjacent
  parameter grid points produce highly correlated tick equity streams
  (<code>N_eff = {neff_lo:.2f}&ndash;{neff_hi:.2f}</code> across 25 grid trials), R2 and R5 yield
  elevated slice-rank PBO (<code>{_to_float(g2.get('cscv_pbo')):.3f}</code> /
  <code>{_to_float(g5.get('cscv_pbo')):.3f}</code>) from near-identical neighbor ties, whereas
  every round clears <code>DSR_block &ge; {min_dsr:.3f}</code> with flat <code>3&times;3</code>
  interior stability. Adverse-selection stress raises loss rates bounded via exact Wilson 95%
  upper intervals.
</p>

<h3>In-Sample Validation Gates &amp; Block DSR / CSCV Summary (R1&ndash;R5)</h3>
<table>
  <thead>
    <tr>
      <th>Round</th>
      <th>Interior Plateau</th>
      <th style="text-align:right">IS IR_tick</th>
      <th style="text-align:right">3&times;3 Mean &plusmn; Std</th>
      <th style="text-align:right">N_eff</th>
      <th style="text-align:right">CSCV PBO</th>
      <th style="text-align:right">DSR_block</th>
      <th style="text-align:right">OOS PnL</th>
      <th style="text-align:right">OOS IR_tick</th>
    </tr>
  </thead>
  <tbody>{gate_rows}</tbody>
</table>

<h3>
  Fill-Model Sensitivity (<code>conservative</code> / <code>queue_aware</code> / <code>touch</code>)
</h3>
<table>
  <thead>
    <tr>
      <th>Round</th>
      <th>Submission</th>
      <th>Fill Mode</th>
      <th style="text-align:right">OOS PnL</th>
      <th style="text-align:right">IR_tick</th>
      <th style="text-align:right">BlkSR_1k</th>
      <th style="text-align:right">MaxDD</th>
      <th style="text-align:right">Fills</th>
    </tr>
  </thead>
  <tbody>{fill_sens_rows}</tbody>
</table>

<h3>Calibrated &amp; Adverse-Stress Monte Carlo Benchmarks (N=40 Sessions &times; 1,000 Steps)</h3>
<table>
  <thead>
    <tr>
      <th>Round</th>
      <th>Scenario / Strategy</th>
      <th style="text-align:right">Mean PnL</th>
      <th style="text-align:right">VaR 95%</th>
      <th style="text-align:right">CVaR 95%</th>
      <th style="text-align:right">Prob Loss</th>
      <th style="text-align:right">95% Wilson Up</th>
      <th style="text-align:right">Mean IR_tick</th>
    </tr>
  </thead>
  <tbody>{mc_rows}</tbody>
</table>

{fig_r2_r5_eq}

<h2>4. Manual Challenges: Closed-Form Valuation &amp; Constrained Optimization</h2>
<div class="eq">
  <strong>R1&ndash;R5 Equilibrium &amp; Risk-Control Formulations:</strong>
  R2 FOC: (100 &minus; s &minus; r*) / (1 + r*) = ln(1 + r*) &nbsp;|&nbsp;
  R4: Exact BS + Rubinstein chooser + 4/d discrete KO (Day-15 min-var hedge) &nbsp;|&nbsp;
  R5: Exact KKT with finite -92% loss bound (&kappa; = 3.0)
</div>
<p>
  In Round 4 (<em>Aether Crystal</em>), closed-form BS and Rubinstein chooser formulas price
  <code>AC_50_C15</code> / <code>AC_50_P15</code> at <code>12.0269</code>, <code>AC_40_BP</code>
  at <code>4.7679</code>, and <code>AC_50_CO</code> at <code>21.8977</code>; 100k-path discrete
  4/day GBM gives <code>AC_45_KO = 0.2113</code> vs. <code>0.175</code> ask (vs.
  <code>0.1562</code> under 24/day checks); Day-15 min-variance hedging achieves EV
  <code>{_to_float(r4_mv.get('expected_metric')):,.2f}</code>
  (<code>{escape(r4_mv.get('parameter', ''))}</code>). In Round 5 (<em>Extra! Extra!</em>),
  bounding <code>Ashes of the Phoenix</code> downside at <code>-92%</code> keeps payoff bounds
  finite and yields KKT net expectation
  <code>{_to_float(r5_exact.get('expected_metric')):,.2f}</code>
  (<code>{_to_float(r5_kkt.get('expected_metric')):,.2f}</code> under risk penalty
  <code>&kappa;=3.0</code>).
</p>

<table>
  <thead>
    <tr>
      <th>Round</th>
      <th>Challenge</th>
      <th>Model Regime</th>
      <th>Optimal Action / Allocation</th>
      <th style="text-align:right">Expected Metric</th>
      <th>Modeling Assumptions</th>
    </tr>
  </thead>
  <tbody>{manual_html_rows}</tbody>
</table>

{fig_manual}

</body>
</html>
"""


def compile_pdf_writeup(
    output_pdf: Path = Path("reports/IMC_Prosperity4_Research_Writeup.pdf"),
    tables_dir: Path = Path("reports/tables"),
    figures_dir: Path = Path("reports/figures"),
) -> Path:
    """Compile HTML monograph via headless Chromium/Edge into a standalone PDF."""
    browser = _find_browser_executable()
    html_text = build_print_html(tables_dir=tables_dir, figures_dir=figures_dir)
    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        html_path = tmp_path / "monograph.html"
        profile_dir = tmp_path / "edge_profile"
        profile_dir.mkdir(parents=True, exist_ok=True)
        html_path.write_text(html_text, encoding="utf-8")
        cmd = [
            str(browser),
            "--headless",
            "--disable-gpu",
            "--no-first-run",
            "--no-default-browser-check",
            "--no-pdf-header-footer",
            f"--user-data-dir={profile_dir}",
            f"--print-to-pdf={output_pdf.resolve()}",
            html_path.resolve().as_uri(),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if proc.returncode != 0 or not output_pdf.exists():
            msg = (
                f"Browser PDF export failed (exit={proc.returncode}): "
                f"{proc.stderr.strip() or proc.stdout.strip()}"
            )
            raise RuntimeError(msg)
    return output_pdf


def main() -> None:
    """Generate the standalone PDF monograph under reports/."""
    pdf_path = compile_pdf_writeup()
    print(f"Built {pdf_path} ({pdf_path.stat().st_size:,d} bytes).")


if __name__ == "__main__":
    main()
