# Experiment EXP-R1-001: Bot-Wall Fair Value & Penny-Joining Refinement

- **Hypothesis**: Replacing noisy L1 microprice with maximum-volume resting bot-wall midpoint (`_popular_wall_mid`) and penny-improving wide 12–16 tick spreads (`best_bid + 1` / `best_ask - 1` clamped by `reservation +/- min_edge`) increases spread capture while reducing adverse selection and drawdown.
- **Calibration Split**: Round 1 `Day -2` & `Day -1` (`20,000` ticks total, `queue_aware` fill simulation).
- **Out-of-Sample Split**: Round 1 `Day 0` (`10,000` ticks) + 30 calibrated Monte Carlo sessions (`conservative` fills).
- **Assumed Limit**: `20` units/product (configurable assumption; official limit **UNVERIFIED**).

## Statistical Validation Results (In-Sample)
- **Plateau Selected**: `min_edge = 1.5`, `inventory_skew = 0.8`
- **Neighborhood Stability**: Local mean Sharpe `1.419`, std `0.020`, max neighbor drop `0.022`
- **CSCV / PBO ($S=8$, 70 partitions)**: `PBO = 0.086`, `prob_oos_neg = 0.000`
- **Deflated Sharpe Ratio (25 trials)**: `obs_sr = 0.0899`, `sr* = 0.0043`, `DSR = 1.0000`

## Held-Out Out-of-Sample Replay (`Day 0`, `10,000` Ticks)

| Strategy | Fill Mode | OOS PnL | `Sharpe_252` | Max Drawdown | Fills | Latency |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: |
| `NoOpBaseline` | `conservative` | 0.00 | 0.0000 | 0.00 | 0 | 0.0000 ms |
| `SymmetricMM` | `conservative` | 10,825.00 | 0.5005 | 886.00 | 582 | 0.0000 ms |
| `InventorySkewedMM` | `conservative` | 9,067.00 | 0.4029 | 837.50 | 931 | 0.0000 ms |
| `Round1Submission` | `conservative` | 22,151.00 | 1.1885 | 267.00 | 1,001 | 0.0373 ms |
| `NoOpBaseline` | `queue_aware` | 0.00 | 0.0000 | 0.00 | 0 | 0.0000 ms |
| `SymmetricMM` | `queue_aware` | 10,825.00 | 0.5005 | 886.00 | 582 | 0.0000 ms |
| `InventorySkewedMM` | `queue_aware` | 9,067.00 | 0.4029 | 837.50 | 931 | 0.0000 ms |
| `Round1Submission` | `queue_aware` | 22,157.00 | 1.1894 | 267.00 | 1,003 | 0.0323 ms |
| `NoOpBaseline` | `touch` | 0.00 | 0.0000 | 0.00 | 0 | 0.0000 ms |
| `SymmetricMM` | `touch` | 11,895.00 | 0.5502 | 913.50 | 599 | 0.0000 ms |
| `InventorySkewedMM` | `touch` | 9,087.00 | 0.4054 | 855.50 | 967 | 0.0000 ms |
| `Round1Submission` | `touch` | 22,667.00 | 1.2220 | 274.50 | 1,024 | 0.0405 ms |

## Monte Carlo Comparison (Conservative Fills, N=30)
- `SymmetricMM`: Mean PnL `359.52`, Std `496.20`, VaR95 `-451.87`, CVaR95 `-774.25`, ProbLoss `0.20`
- `Round1Submission`: Mean PnL `900.48`, Std `319.06`, VaR95 `446.18`, CVaR95 `344.25`, ProbLoss `0.00`

## Conclusion
Accepted. The refined specification dominates baseline and uncalibrated candidates out-of-sample across every fill regime while passing both CSCV (`PBO < 0.15`) and DSR (`>= 0.95`). See companion attribution study [EXP-R1-002](EXP-R1-002_per_asset_attribution_and_bootstrap.md).
