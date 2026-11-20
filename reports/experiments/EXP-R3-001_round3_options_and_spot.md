# Experiment EXP-R3-001: Round 3 OU Spot + BS Total-Vol Options (No Spot Delta Hedging)

- **Hypothesis**: Combining Bayesian-updated OU fair values on `HYDROGEL_PACK` and `VELVETFRUIT_EXTRACT` with scale-free Black-Scholes total implied volatility across `VEV_4000..5500`—while omitting worthless `VEV_6000/6500` and eliminating slippage-heavy spot delta hedging—delivers cleaner IS and OOS performance than both `SymmetricSpotMM` and fixed-5d `OptionsVolatilityContract`.
- **IS Plateau Selected (`Days 0 & 1`)**: `spot_scale = 30.0`, `enter_band = 10.0` (`IR_tick = 0.015932`, 3x3 mean `0.015827 +/- 0.000606`, IS PnL `446,833.50`, `N_eff = 1.0109`, `CSCV PBO = 0.0000`, `DSR_block = 0.9966`).

## Held-Out OOS Replay (`Day 2`, 10,000 Ticks, `+/-200` Spot / `+/-300` VEV)

| Strategy | Fill Mode | OOS PnL | `IR_tick` | `BlkSR_1k` | `PnL/MaxDD` | Max DD | Fills |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| `SymmetricSpotMM` | `queue_aware` | `-7,160.00` | `-0.00388` | `-0.455` | `-0.50` | `14,245.00` | `382` |
| `OptionsVolatilityContract` | `queue_aware` | `-1,051.00` | `-0.00030` | `-0.063` | `-0.04` | `24,608.50` | `89` |
| `Round3Submission` | `conservative` | **`95,093.00`** | `0.00584` | `0.573` | `1.26` | `75,774.00` | `2,939` |
| `Round3Submission` | `queue_aware` | **`95,093.00`** | `0.00584` | `0.573` | `1.26` | `75,774.00` | `2,939` |
| `Round3Submission` | `touch` | **`95,238.00`** | `0.00585` | `0.573` | `1.26` | `75,730.50` | `2,989` |

- **Attribution**: Positive across all 10 active products led by `HYDROGEL_PACK` (`+23,078`), `VEV_5000` (`+13,790`), `VEV_5100` (`+12,814`), `VELVETFRUIT_EXTRACT` (`+10,866`), `VEV_5200` (`+10,096`). Wide block-bootstrap PnL CI (`[-184,416.62, +355,675.89]`) reflects realistic single-day unhedged spot variance.
- **Monte Carlo (`N=40`)**: `CalibratedQA` mean `29,852.01` (`ProbLoss = 0.025`, `<= 0.129`); `AdverseStress` mean `13,225.06` (`ProbLoss = 0.300`, `<= 0.454`).
