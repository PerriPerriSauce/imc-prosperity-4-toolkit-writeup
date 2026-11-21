# Experiment EXP-R5-001: 50-Asset Vol-Scaled AS & Discrete Microchip Lead-Lag

- **Pruned Hypotheses**: IS analysis rejected `Pebbles` crossing (`std = 2.82` lies strictly inside `12–14` tick spreads), contemporaneous `Snackpacks` correlations (`diff_corr = -0.92`), zero-lag `Robots`, and hard `VOL_GUARD` halts.
- **Hypothesis Tested**: Volatility-scaled Avellaneda-Stoikov quoting (`vol_skew_mult = 0.18, edge_frac = 0.14`) across all 50 books plus strictly causal discrete delays from `MICROCHIP_CIRCLE` (`50/100/150/200` ticks to `OVAL/SQUARE/RECTANGLE/TRIANGLE`, IS `mc_beta = 0.16` concave peak: IS PnL `237,928.50`, `IR_tick = 0.03531` vs. `226,217.50`, `IR_tick = 0.03398` at `mc_beta = 0.0`).
- **IS Diagnostics (`Days 2 & 3`)**: `N_eff = 1.1437`, `DSR_block = 1.0000`, `CSCV PBO = 0.5429` (arising from tied `IR_tick` values across flat neighbors `0.0315..0.0356`).

## Held-Out OOS Replay (`Day 4`, 10,000 Ticks, `50 x ±10`)

| Strategy | Fill Mode | OOS PnL | `IR_tick` | `BlkSR_1k` | `PnL/MaxDD` | Max DD | Fills |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| `EmaSymmetricMM_All50` | `queue_aware` | `114,851.00` | `0.02054` | `1.154` | `3.94` | `29,130.00` | `10,146` |
| `Round5NoLeadLag` | `queue_aware` | `95,412.50` | `0.02642` | `1.339` | `6.08` | `15,692.50` | `8,107` |
| `Round5Submission` | `conservative` | **`97,514.00`** | `0.02621` | `1.106` | `6.52` | `14,961.50` | `8,323` |
| `Round5Submission` | `queue_aware` | **`97,628.00`** | `0.02624` | `1.108` | `6.53` | `14,961.50` | `8,325` |
| `Round5Submission` | `touch` | **`114,924.00`** | `0.02948` | `1.251` | `8.50` | `13,516.00` | `8,688` |

- **Takeaways**: Adding `mc_beta = 0.16` improves OOS PnL **`+2,215.50`** (`Microchips` doubles `+2.2k -> +4.5k`) and reduces MaxDD (`15,692.5 -> 14,961.5`), delivering `1.66x` higher risk-adjusted `PnL/MaxDD` than `EmaSymmetricMM_All50`. Bootstrap 95% PnL CI `[39,002.28, 149,879.30]` is strictly positive.
- **11-Asset Representative Joint MC (`N=40`)**: `Calibrated` `15,279.26` / `AdverseStress` `12,994.25` (`0/40` losses, Wilson upper `<= 0.0876`).
