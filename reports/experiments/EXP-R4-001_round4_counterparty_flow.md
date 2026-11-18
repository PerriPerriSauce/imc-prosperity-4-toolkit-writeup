# Experiment EXP-R4-001: Counterparty Flow Gating & Plateau Alignment (`Round 4`)

- **Hypothesis**:
  1. Conditioning `VELVETFRUIT_EXTRACT` fair value cleanly on live `Mark 67` buy prints (`M67_BUMP = 0.5`, exponential decay `0.80x` per tick) dodges permanent `+1.97`-tick informed jumps without chasing transient bounce.
  2. Aligning submission constants directly to the IS-validated `3x3` plateau (`m67_bump = 0.5, mm_edge = 5.5`) while rejecting high-PBO aggressive spot-chasing variants improves OOS Sharpe and cuts max drawdown relative to ungated Round 3 logic.
- **Calibration Split**: Round 4 `Day 1` & `Day 2` (`20,000` ticks, `12` instruments, `±200`/`±300` caps, `queue_aware`).
- **Out-of-Sample Split**: Single-pass held-out Round 4 `Day 3` (`10,000` ticks) across `conservative`, `queue_aware`, and `touch` fill regimes + `N=25` coupled Monte Carlo runs (`1,000` steps).

## Statistical Validation Results (`Day 1` & `Day 2` IS)
- **Plateau Selected (`4x4` Grid)**: `m67_bump = 0.5`, `mm_edge = 5.5` (`IS Sharpe_252 = 0.3725`, `3x3` local mean `0.3498`, std `0.0186`).
- **Rejected Candidate Audit**: An aggressive spot-chasing variant (`s_alpha = 0.85` plus unconstrained option crossing) was evaluated strictly IS and **vetoed** for failing `CSCV` (`PBO = 0.9714 > 0.15`) and `DSR` (`0.9390 < 0.95`).
- **CSCV / PBO (`S = 8`, `70` partitions)**: `PBO = 0.0571` (`< 0.15`), `N_eff = 1.08`.
- **Deflated Sharpe Ratio (`16` trials)**: `DSR = 0.9975` (`>= 0.95`).

## Held-Out Out-of-Sample (`Day 3`) & Ablation Comparison

| Strategy | `conservative` PnL / SR | `queue_aware` PnL / SR / DD | `touch` PnL / SR | `queue_aware` Latency |
| :--- | :---: | :---: | :---: | ---: |
| `NoOpBaseline` | `0.00 / 0.000` | `0.00 / 0.000 / 0.00` | `0.00 / 0.000` | `0.0000 ms` |
| `Round3Ungated` (`m67=0, edge=4.5`) | `11,942.00 / 0.3462` | `12,048.00 / 0.3488 / 3,250.50` | `12,284.50 / 0.2347` | `0.1933 ms` |
| **`Round4Submission`** (`m67=0.5, edge=5.5`) | **`11,635.00 / 0.3587`** | **`11,741.00 / 0.3613 / 2,901.00`** | **`13,259.50 / 0.2780`** | **`0.1871 ms`** |

- **OOS Per-Asset Attribution (`queue_aware`)**: `HYDROGEL_PACK +8,407.00`, `VEV_4000 +2,493.00`, **`VELVETFRUIT_EXTRACT +1,027.00`**, `VEV_4500 -74.00`, `VEV_5200 -41.00`, `VEV_5300 -71.00`.
- **Circular Block Bootstrap (`Day 3`)**: `Sharpe_252` 95% CI `[0.0932, 0.6302]`; PnL CI `[3,079.11, 20,064.41]`.
- **Coupled Options+Spot MC (`N=25`, `1,000` steps)**: Mean PnL `2,345.10`, `VaR95 = 1,692.40`, `CVaR95 = 1,116.75`, `ProbLoss = 0.0000`, Mean `Sharpe_252 = 0.4966`, Worst Max DD `1,905.50`.

## Conclusion
**Accepted.** Aligning `M67_BUMP = 0.5` directly to the IS plateau passes all overfitting checks cleanly (`PBO = 0.0571, DSR = 0.9975`), flips `VELVETFRUIT_EXTRACT` OOS from `-328.50` (R3) to **`+1,027.00`**, cuts `queue_aware` max drawdown **`-10.8%`** (`3,250.50 -> 2,901.00`), and outperforms `Round3Ungated` on annualized `Sharpe_252` across every fill mode while running at `0.1871 ms/tick`.
