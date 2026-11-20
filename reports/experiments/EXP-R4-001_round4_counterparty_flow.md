# Experiment EXP-R4-001: Causal Prior-Tick Counterparty Alpha (`Mark 14` & `Mark 55`)

- **Negative Result Resolved**: Strictly In-Sample (`Days 1 & 2`) decomposition on `VELVETFRUIT_EXTRACT` ([`r4_counterparty_velvet_midmoves.csv`](../tables/r4_counterparty_velvet_midmoves.csv)) proved `Mark 67` (`+1.924` at `t -> t+1` after `-1.765` pre-dip) is a mechanical 1-tick bounce (`causal_1_to_200 = +0.113`, `OU-adj t = +1.56`) rather than causal directional flow.
- **Causal Hypothesis**: Conditioning spot & call-option fair values on strictly **prior-tick** (`t - 100`) prints from `Mark 14 SELL` (`ou_adj_h200 = +3.788, t = +4.58`) and `Mark 55 BUY` (`ou_adj_h200 = +2.460, t = +4.07`) captures genuine reversion/momentum alpha without look-ahead bias.
- **IS Plateau Selected (`Days 1 & 2`)**: `spot_scale = 30.0`, `flow_weight = 1.5` (`IR_tick = 0.011374`, IS PnL `341,648.00` vs. `313,275.50` at `flow_weight = 0.0`, `N_eff = 1.0157`, `CSCV PBO = 0.0143`, `DSR_block = 0.9783`).

## Held-Out OOS Replay (`Day 3`, 10,000 Ticks)

| Strategy | Fill Mode | OOS PnL | `IR_tick` | `BlkSR_1k` | `PnL/MaxDD` | Max DD | Fills |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| `Round3NoFlow` | `queue_aware` | `249,386.50` | `0.01617` | `0.597` | `3.38` | `73,758.00` | `3,469` |
| `Round4Submission` | `conservative` | **`260,537.00`** | `0.01680` | `0.646` | `3.66` | `71,177.00` | `3,667` |
| `Round4Submission` | `queue_aware` | **`260,540.00`** | `0.01680` | `0.646` | `3.66` | `71,177.00` | `3,669` |
| `Round4Submission` | `touch` | **`260,392.00`** | `0.01678` | `0.644` | `3.65` | `71,390.00` | `3,802` |

- **Causal Uplift**: `Round4Submission` beats `Round3NoFlow` by **`+11,153.50`** OOS while reducing MaxDD by **`-2,581.00`** (`73,758 -> 71,177`); circular block-bootstrap PnL 95% CI `[14,650.65, 525,360.43]` (`IR_tick > 0` across entire 95% CI!).
- **Monte Carlo (`N=40`)**: `CalibratedQA` mean `27,562.95` (`ProbLoss = 0.125`, `<= 0.261`); `AdverseStress` mean `12,042.42` (`ProbLoss = 0.275`, `<= 0.428`).
