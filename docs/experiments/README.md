# Quantitative Experiments Registry

Controlled empirical experiments testing specific microstructural hypotheses, execution assumptions, and strategy ablations. Every experiment specifies its hypothesis, calibration vs. held-out split, statistical validation metrics, and honest negative findings.

## Completed Experiments (Held-Out Simulated `queue_aware`)

| Experiment ID | Round / Limits | Hypothesis Tested | Validation Status | Primary Artifact |
| :--- | :--- | :--- | :--- | :--- |
| **`EXP-R1-001`** | R1 (`±80`, `2` assets) | Fixed `10,000` OU anchor on `ASH_COATED_OSMIUM` + max-volume carry on `INTARIAN_PEPPER_ROOT` (`min_edge=2.0, skew=0.40`) captures spread and `+0.10/tick` trend safely | **Accepted** (`DSR_block=1.0000`, `PBO=0.129`, `N_eff=1.02`, OOS `PnL=+91,098.00`, `IR_tick=0.05445`) | [EXP-R1-001_baseline_vs_refined.md](../../reports/experiments/EXP-R1-001_baseline_vs_refined.md) |
| **`EXP-R1-002`** | R1 (`±80`, `2` assets) | Per-asset attribution and `100`-tick circular block bootstrap on OOS `Day 0` confirm independent contribution from both assets | **Accepted** (`Osmium +11,371`, `Pepper +79,727`, 95% Boot PnL `[85,711.14, 96,434.06]`) | [EXP-R1-002_per_asset_attribution_and_bootstrap.md](../../reports/experiments/EXP-R1-002_per_asset_attribution_and_bootstrap.md) |
| **`EXP-R2-001`** | R2 (`±80`, `2` assets) | Refined plateau (`min_edge=2.5, skew=0.40`) on `Day 1` avoids `SymmetricMM_80` drift loss (`-20,294.50`); calibrated MAF flow increases EV under synthetic tests | **Accepted** (`DSR_block=1.0000`, `PBO=0.300` flat ties, OOS `PnL=+94,209.00`, `IR_tick=0.05466`) | [EXP-R2-001_round2_scale_and_maf.md](../../reports/experiments/EXP-R2-001_round2_scale_and_maf.md) |
| **`EXP-R3-001`** | R3 (`±200/300`, `12` assets) | Bayesian OU (`HYDROGEL`/`VELVET`) + Black-Scholes total-vol (`VEV_4000..5500`) **without** destructive spot delta hedging eliminates fixed-TTE loss (`-1,051` baseline) | **Accepted** (`DSR_block=0.9966`, `PBO=0.000`, OOS `PnL=+95,093.00`, `IR_tick=0.00584`) | [EXP-R3-001_round3_options_and_spot.md](../../reports/experiments/EXP-R3-001_round3_options_and_spot.md) |
| **`EXP-R4-001`** | R4 (`±200/300`, `Mark 14`/`55`) | Strictly causal prior-tick counterparty flow (`Mark 14 SELL`, `Mark 55 BUY`; excluding `Mark 67` 1-tick bounce) outperforms `Round3NoFlow` | **Accepted** (`DSR_block=0.9783`, `PBO=0.014`, OOS `PnL=+260,540.00` vs `249,386.50` no-flow, `-2,581` MaxDD) | [EXP-R4-001_round4_counterparty_flow.md](../../reports/experiments/EXP-R4-001_round4_counterparty_flow.md) |
| **`EXP-R5-001`** | R5 (`50 x ±10`) | Vol-scaled AS (`vsm=0.18, ef=0.14`) + `MICROCHIP_CIRCLE` 50/100/150/200 lag (`mc_beta=0.16`) while pruning `Pebbles` crossing and `VOL_GUARD` halts | **Accepted** (`DSR_block=1.0000`, `PBO=0.543` flat ties, OOS `PnL=+97,628.00`, `PnL/MaxDD=6.53` vs `3.94` naive) | [EXP-R5-001_round5_portfolio_optimization.md](../../reports/experiments/EXP-R5-001_round5_portfolio_optimization.md) |

## Experiment Protocol Schema

Every archived experiment records:
1. **Hypothesis & Pruned Alternatives**: Both tested edges and rejected candidates.
2. **Data Split**: Strict separation between calibration days and single-pass held-out evaluation days.
3. **Statistical Gates**: Interior $3 \times 3$ plateau selection, `DSR_block` (`100`-tick blocks penalized by $N_{\text{eff}}$), `CSCV PBO`, circular block bootstrap CIs, and calibrated + adverse-selection MC stress tests.
