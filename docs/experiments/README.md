# Quantitative Experiments Registry

Controlled empirical experiments testing specific microstructural hypotheses, execution assumptions, and strategy ablations. Every experiment specifies its hypothesis, calibration vs. OOS split, and acceptance criteria before execution.

---

## Active & Completed Experiments

| Experiment ID | Round / Assets | Hypothesis Tested | Validation Status | Primary Artifact |
| :--- | :--- | :--- | :--- | :--- |
| **`EXP-R1-001`** | R1 (`ASH_COATED_OSMIUM`, `INTARIAN_PEPPER_ROOT`) | Replacing L1 microprice with max-volume bot-wall mid (`_popular_wall_mid`) + penny-improving wide spreads (`min_edge=1.5`, `skew=0.80`) improves OOS Sharpe and lowers drawdown vs. Stage 5 baseline | **Accepted** (`PBO=0.086`, `DSR=1.0000`, OOS Day 0 `PnL=22,157`, `MC ProbLoss=0.00`) | [EXP-R1-001_stage5_vs_stage6.md](../../reports/experiments/EXP-R1-001_stage5_vs_stage6.md) |
| **`EXP-R1-002`** | R1 (`ASH_COATED_OSMIUM`, `INTARIAN_PEPPER_ROOT`) | `_popular_wall_mid` attenuates high-frequency quote jitter variance; OOS `Day 0` edge is balanced across both instruments and holds under circular block-bootstrap CIs | **Accepted** (`N_eff=1.11`, OOS Sharpe 95% CI `[1.046, 1.329]`, 51.6%/48.4% PnL split) | [EXP-R1-002_per_asset_attribution_and_bootstrap.md](../../reports/experiments/EXP-R1-002_per_asset_attribution_and_bootstrap.md) |

---

## Experiment Protocol Schema

Each archived experiment in `reports/experiments/` records:
1. **Hypothesis**: Economic or microstructural mechanism under test.
2. **Data Split**: Strict separation between calibration days and held-out out-of-sample days.
3. **Statistical Gate**: CSCV PBO ($< 0.15$), Deflated Sharpe Ratio ($\ge 0.95$), effective trials ($N_{\text{eff}}$), and neighborhood stability.
4. **Conclusion**: Accepted / Rejected / Revised with explicit limitations.
