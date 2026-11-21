"""Generate canonical official competition results table and comparison chart."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np


@dataclass(frozen=True)
class OfficialRoundRecord:
    """Official Team 63-bit integers round scorecard entry."""

    round_id: str
    phase: str
    algo_pnl: int
    manual_pnl: int
    notes: str

    @property
    def round_total_pnl(self) -> int:
        return self.algo_pnl + self.manual_pnl


OFFICIAL_TEAM_NAME = "63-bit integers"
OFFICIAL_RANKS = "60th Worldwide / 8th Australia / 13th APAC"
OFFICIAL_PHASE2_TOTAL = 700_334

OFFICIAL_RECORDS: tuple[OfficialRoundRecord, ...] = (
    OfficialRoundRecord(
        round_id="R1",
        phase="Phase 1",
        algo_pnl=116_927,
        manual_pnl=87_995,
        notes="Stationary Osmium MM + Pepper carry; R1 Uniform Clearing manual",
    ),
    OfficialRoundRecord(
        round_id="R2",
        phase="Phase 1",
        algo_pnl=115_543,
        manual_pnl=200_716,
        notes="Live Algo exceeds 1-day OOS (+94,209) via MAF liquidity & multi-day carry",
    ),
    OfficialRoundRecord(
        round_id="R3",
        phase="Phase 2",
        algo_pnl=213_104,
        manual_pnl=78_225,
        notes="Phase 2 leaderboard reset; OU spots + VEV calls & Bayesian reserve manual",
    ),
    OfficialRoundRecord(
        round_id="R4",
        phase="Phase 2",
        algo_pnl=220_783,
        manual_pnl=36_969,
        notes="Causal Mark 14/55 counterparty flow + Aether Crystal discrete/straddle manual",
    ),
    OfficialRoundRecord(
        round_id="R5",
        phase="Phase 2",
        algo_pnl=31_087,
        manual_pnl=120_165,
        notes="Live R5 sprint capped algo at +31,087 before post-contest redesign reached +97,628",
    ),
)


def _load_postcontest_oos_pnl(tables_dir: Path, round_num: int) -> float:
    """Load verified queue_aware held-out OOS PnL for Round N from CSV."""
    ab_path = tables_dir / f"r{round_num}_ablation_summary.csv"
    with ab_path.open("r", encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            if (
                row.get("split") == "OOS"
                and row.get("fill_mode") == "queue_aware"
                and str(row.get("strategy", "")).endswith("Submission")
            ):
                return float(row["total_pnl"])
    msg = f"Could not find OOS queue_aware Submission row in {ab_path}"
    raise FileNotFoundError(msg)


def generate_artifacts(
    tables_dir: Path = Path("reports/tables"),
    figures_dir: Path = Path("reports/figures"),
) -> tuple[Path, Path]:
    """Write competition_results.csv and competition_vs_postcontest.png."""
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    oos_values = [
        _load_postcontest_oos_pnl(tables_dir, idx)
        for idx in range(1, len(OFFICIAL_RECORDS) + 1)
    ]

    csv_path = tables_dir / "competition_results.csv"
    fieldnames = [
        "round",
        "phase",
        "algo_pnl",
        "manual_pnl",
        "round_total_pnl",
        "postcontest_oos_algo_pnl",
        "notes",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for rec, oos_pnl in zip(OFFICIAL_RECORDS, oos_values, strict=True):
            writer.writerow({
                "round": rec.round_id,
                "phase": rec.phase,
                "algo_pnl": rec.algo_pnl,
                "manual_pnl": rec.manual_pnl,
                "round_total_pnl": rec.round_total_pnl,
                "postcontest_oos_algo_pnl": round(oos_pnl, 2),
                "notes": rec.notes,
            })

    # Render clean two-panel visual comparison
    plt.style.use("seaborn-v0_8-whitegrid")
    fig, axes = plt.subplots(1, 2, figsize=(13.8, 5.4), dpi=200)

    rounds = [rec.round_id for rec in OFFICIAL_RECORDS]
    algo_live = np.array([float(rec.algo_pnl) for rec in OFFICIAL_RECORDS], dtype=np.float64)
    manual_live = np.array([float(rec.manual_pnl) for rec in OFFICIAL_RECORDS], dtype=np.float64)
    totals = algo_live + manual_live
    post_oos = np.array(oos_values, dtype=np.float64)
    x = np.arange(len(rounds))

    # Left panel: Official Live Competition PnL (Algo + Manual Stacked)
    ax0 = axes[0]
    ax0.bar(x, algo_live, width=0.58, color="#1d3557", label="Live Algorithmic PnL")
    ax0.bar(
        x,
        manual_live,
        width=0.58,
        bottom=algo_live,
        color="#2a9d8f",
        label="Live Manual PnL",
    )
    ax0.axvline(1.5, color="#e63946", linestyle="--", linewidth=1.6, alpha=0.85)
    ax0.text(
        1.56,
        365_000,
        "Phase 2 Reset\nP1: +521,181\nP2: +700,334*",
        color="#b91c1c",
        fontsize=8.1,
        fontweight="bold",
        va="top",
        bbox={"boxstyle": "round,pad=0.3", "facecolor": "#fef2f2", "edgecolor": "#fca5a5"},
    )
    for i in range(len(x)):
        ax0.text(
            x[i],
            totals[i] + 6_500,
            f"+{totals[i] / 1000:.1f}k",
            ha="center",
            va="bottom",
            fontsize=8.6,
            fontweight="bold",
            color="#0f172a",
        )
        if algo_live[i] >= 28_000:
            ax0.text(
                x[i],
                algo_live[i] * 0.5,
                f"{algo_live[i] / 1000:.1f}k",
                ha="center",
                va="center",
                fontsize=7.4,
                color="white",
                fontweight="bold",
            )
        if manual_live[i] >= 28_000:
            ax0.text(
                x[i],
                algo_live[i] + manual_live[i] * 0.5,
                f"{manual_live[i] / 1000:.1f}k",
                ha="center",
                va="center",
                fontsize=7.4,
                color="white",
                fontweight="bold",
            )

    ax0.set_xticks(x, rounds)
    ax0.set_ylim(0, 388_000)
    ax0.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{int(v / 1000)}k"))
    ax0.set_ylabel("Official Competition PnL (XIRECs)")
    ax0.set_title(
        f"Team {OFFICIAL_TEAM_NAME}: Official Round PnL\n({OFFICIAL_RANKS})",
        fontsize=10.5,
        fontweight="bold",
    )
    ax0.legend(loc="upper right", fontsize=8.3)

    # Right panel: Live Algo vs Post-Contest 1-Day Held-Out OOS Replay (queue_aware)
    ax1 = axes[1]
    w = 0.36
    ax1.bar(x - w / 2, algo_live, width=w, color="#1d3557", label="Official Live Algo (Full Round)")
    ax1.bar(
        x + w / 2,
        post_oos,
        width=w,
        color="#e76f51",
        label="Post-Contest 1-Day Sim OOS (queue_aware)",
    )
    for i in range(len(x)):
        ax1.text(
            x[i] - w / 2,
            algo_live[i] + 5_500,
            f"+{algo_live[i] / 1000:.1f}k",
            ha="center",
            va="bottom",
            fontsize=7.8,
            color="#1d3557",
            fontweight="bold",
        )
        ax1.text(
            x[i] + w / 2,
            post_oos[i] + 5_500,
            f"+{post_oos[i] / 1000:.1f}k",
            ha="center",
            va="bottom",
            fontsize=7.8,
            color="#c2410c",
            fontweight="bold",
        )

    ax1.annotate(
        "Post-contest redesign:\nVol-scaled AS + Microchip lags\n(+31.1k live -> +97.6k OOS)",
        xy=(4 + w / 2, post_oos[4] + 22_000),
        xytext=(2.55, 292_000),
        fontsize=8.0,
        fontweight="bold",
        color="#7c2d12",
        bbox={"boxstyle": "round,pad=0.35", "facecolor": "#fff7ed", "edgecolor": "#fdba74"},
        arrowprops={"arrowstyle": "->", "color": "#c2410c", "lw": 1.3},
    )
    ax1.set_xticks(x, rounds)
    ax1.set_ylim(0, 345_000)
    ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{int(v / 1000)}k"))
    ax1.set_ylabel("Algorithmic PnL (XIRECs)")
    ax1.set_title(
        "Official Live Algo vs. Post-Contest 1-Day OOS Audit\n"
        "(Reconciles R1-R4 Edge & Diagnoses R5 Redesign)",
        fontsize=10.5,
        fontweight="bold",
    )
    ax1.legend(loc="upper left", fontsize=8.3)

    fig.tight_layout()
    fig_path = figures_dir / "competition_vs_postcontest.png"
    fig.savefig(fig_path, dpi=200)
    plt.close(fig)
    return csv_path, fig_path


def main() -> None:
    """Build canonical competition scorecard table and comparison figure."""
    csv_path, fig_path = generate_artifacts()
    print(f"Wrote {csv_path} and {fig_path}.")


if __name__ == "__main__":
    main()
