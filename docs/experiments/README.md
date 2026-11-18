# Quantitative Experiments Registry

Controlled empirical experiments testing specific microstructural hypotheses, execution assumptions, and strategy ablations. Every experiment specifies its hypothesis, calibration vs. OOS split, and acceptance criteria before execution.

## Active & Completed Experiments

| Experiment ID | Round / Assets | Hypothesis Tested | Validation Status | Primary Artifact |
| :--- | :--- | :--- | :--- | :--- |
| **`EXP-R1-001`** | R1 (`ASH_COATED_OSMIUM`, `INTARIAN_PEPPER_ROOT`) | Replacing L1 microprice with max-volume bot-wall mid (`_popular_wall_mid`) + penny-improving wide spreads (`min_edge=1.5`, `skew=0.80`) improves OOS Sharpe and lowers drawdown vs. uncalibrated skewed baseline | **Accepted** (`PBO=0.086`, `DSR=1.0000`, OOS Day 0 `PnL=22,157`, `MC ProbLoss=0.00`) | [EXP-R1-001_baseline_vs_refined.md](../../reports/experiments/EXP-R1-001_baseline_vs_refined.md) |
| **`EXP-R1-002`** | R1 (`ASH_COATED_OSMIUM`, `INTARIAN_PEPPER_ROOT`) | `_popular_wall_mid` attenuates high-frequency quote jitter variance; OOS `Day 0` edge is balanced across both instruments and holds under circular block-bootstrap CIs | **Accepted** (`N_eff=1.11`, OOS Sharpe 95% CI `[1.046, 1.329]`, 51.6%/48.4% PnL split) | [EXP-R1-002_per_asset_attribution_and_bootstrap.md](../../reports/experiments/EXP-R1-002_per_asset_attribution_and_bootstrap.md) |
| **`EXP-R2-001`** | R2 (`ASH_COATED_OSMIUM`, `INTARIAN_PEPPER_ROOT`, `±80`) | Scaling bot-wall MM & inventory skew (`min_edge=3.5, skew=0.75`) captures `±80` capacity; MAF `+25%` arrival boost raises calibrated MC PnL `+33.4%` (`+1,690` / `1k` steps) | **Accepted** (`PBO=0.000`, `DSR=1.0000`, OOS Day 1 `PnL=27,463`, `SR=1.3972`, `ProbLoss=0.00`) | [EXP-R2-001_round2_scale_and_maf.md](../../reports/experiments/EXP-R2-001_round2_scale_and_maf.md) |
| **`EXP-R3-001`** | R3 (`HYDROGEL`, `VELVETFRUIT`, `VEV_4000..6500`) | Day-invariant total-vol inversion ($v_K=\sigma_K\sqrt{\tau}$) + spot delta hedging + wide `HYDROGEL_PACK` MM (`edge=4.5, skew=0.10`) eliminates fixed-TTE loss | **Accepted** (`PBO=0.000`, `DSR=0.9921`, OOS Day 2 `PnL=7,525.5`, `SR=0.2276`, `ProbLoss=0.00`) | [EXP-R3-001_round3_options_and_spot.md](../../reports/experiments/EXP-R3-001_round3_options_and_spot.md) |
| **`EXP-R4-001`** | R4 (`Mark 67`/`22` flow + `12` R3 instruments) | Aligning `Mark 67` buy-impulse gating to IS plateau (`m67=0.5, mm_edge=5.5`) lifts `VELVETFRUIT_EXTRACT` OOS (`+1,027.00`), trims MaxDD `-10.8%`, and beats `Round3Ungated` on Sharpe | **Accepted** (`PBO=0.0571`, `DSR=0.9975`, OOS Day 3 `PnL=11,741.00`, `SR=0.3613`, `touch=13,259.50`) | [EXP-R4-001_round4_counterparty_flow.md](../../reports/experiments/EXP-R4-001_round4_counterparty_flow.md) |
| **`EXP-R5-001`** | R5 (`50` assets across `10` categories, `±10`) | Zero-lag wall-mid quoting (`ef=0.18, sk=1.25`), `QUOTE_CLIP=10`, atomic `PEBBLES` IOC crossing, `SNACKPACK` `K_day` EMA, and `Robots`/`Microchips` `VOL_GUARD` capture multi-category flow cleanly | **Accepted** (`PBO=0.1000`, `DSR=1.0000`, OOS Day 4 `PnL=123,173.00`, `SR=0.8109`, `ProbLoss=0.00`) | [EXP-R5-001_round5_portfolio_optimization.md](../../reports/experiments/EXP-R5-001_round5_portfolio_optimization.md) |

## Experiment Protocol Schema

Each archived experiment in `reports/experiments/` records:
1. **Hypothesis**: Economic or microstructural mechanism under test.
2. **Data Split**: Strict separation between calibration days and held-out out-of-sample days.
3. **Statistical Gate**: CSCV PBO ($< 0.15$), Deflated Sharpe Ratio ($\ge 0.95$), effective trials ($N_{\text{eff}}$), and neighborhood stability.
4. **Conclusion**: Accepted / Rejected / Revised with explicit limitations.
