# Experiment EXP-R1-001: Round 1 10,000-Anchor Osmium MM & Pepper Carry Refinement

- **Hypothesis**: Anchoring `ASH_COATED_OSMIUM` at 10,000 with inventory-skewed penny-improved quotes while accumulating structural `INTARIAN_PEPPER_ROOT` carry (+0.10 XIREC/tick drift) up to the verified +/-80 limit captures stationary spread plus drift without ad-hoc directional risk.
- **Calibration Split**: Round 1 `Day -2` & `Day -1` evaluated independently (10,000 ticks/day, zero overnight carry, `queue_aware` simulation).
- **Out-of-Sample Split**: Round 1 `Day 0` (10,000 ticks) plus 40-session MC suites (`queue_aware`, `conservative`, and `adverse_selection_prob=0.30`).
- **Official Position Limit**: `+/-80` units/product.

## Statistical Validation Results (In-Sample)
- **Interior Plateau Selected**: `min_edge = 2.0`, `inventory_skew = 0.4`
- **Neighborhood Stability (3x3)**: Local mean `IR_tick = 0.05788`, std `0.00009`, max drop `0.00021`
- **CSCV / PBO ($S=8$, 70 partitions)**: `PBO = 0.129`, `prob_oos_neg = 0.000`
- **Block Deflated Sharpe Ratio (100-tick blocks, N_eff=1.02 / 25)**: `obs_sr = 3.1974`, `sr* = 0.0000`, `DSR_block = 1.0000`

## Held-Out Out-of-Sample Replay (`Day 0`, 10,000 Ticks)

| Strategy | Fill Mode | OOS PnL | `IR_tick` | `BlkSR_1k` | `PnL/MaxDD` | Max DD | Fills | Latency |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `NoOpBaseline` | `conservative` | 0.00 | 0.00000 | 0.000 | 0.00 | 0.00 | 0 | 0.0000 ms |
| `SymmetricMM` | `conservative` | 21,731.00 | 0.02034 | 0.920 | 8.85 | 2,455.00 | 618 | 0.0000 ms |
| `InventorySkewedMM` | `conservative` | 8,072.00 | 0.01187 | 0.273 | 2.73 | 2,959.00 | 952 | 0.0000 ms |
| `Round1Submission` | `conservative` | 91,098.00 | 0.05445 | 9.327 | 64.84 | 1,405.00 | 712 | 0.0217 ms |
| `NoOpBaseline` | `queue_aware` | 0.00 | 0.00000 | 0.000 | 0.00 | 0.00 | 0 | 0.0000 ms |
| `SymmetricMM` | `queue_aware` | 21,731.00 | 0.02034 | 0.920 | 8.85 | 2,455.00 | 618 | 0.0000 ms |
| `InventorySkewedMM` | `queue_aware` | 8,251.00 | 0.01227 | 0.328 | 3.01 | 2,743.00 | 957 | 0.0000 ms |
| `Round1Submission` | `queue_aware` | 91,098.00 | 0.05445 | 9.327 | 64.84 | 1,405.00 | 712 | 0.0204 ms |
| `NoOpBaseline` | `touch` | 0.00 | 0.00000 | 0.000 | 0.00 | 0.00 | 0 | 0.0000 ms |
| `SymmetricMM` | `touch` | 30,670.00 | 0.02627 | 0.920 | 10.27 | 2,986.00 | 635 | 0.0000 ms |
| `InventorySkewedMM` | `touch` | 8,133.00 | 0.01127 | 0.260 | 2.52 | 3,229.50 | 977 | 0.0000 ms |
| `Round1Submission` | `touch` | 91,743.00 | 0.05522 | 9.399 | 65.95 | 1,391.00 | 760 | 0.0210 ms |

## Monte Carlo Risk Comparison (N=40 sessions x 1,000 ticks)
- `SymmetricMM`: Mean PnL `562.46`, Std `2,970.34`, VaR95 `-4,609.05`, CVaR95 `-5,711.00`, ProbLoss `0.375` (95% Wilson upper <= `0.530`)
- `Round1Submission_QA`: Mean PnL `6,675.06`, Std `2,619.24`, VaR95 `3,431.15`, CVaR95 `2,845.75`, ProbLoss `0.000` (95% Wilson upper <= `0.088`)
- `Round1Submission_Conservative`: Mean PnL `6,675.06`, Std `2,619.24`, VaR95 `3,431.15`, CVaR95 `2,845.75`, ProbLoss `0.000` (95% Wilson upper <= `0.088`)
- `Round1Submission_AdverseStress`: Mean PnL `3,783.54`, Std `2,769.09`, VaR95 `-253.65`, CVaR95 `-2,503.00`, ProbLoss `0.075` (95% Wilson upper <= `0.199`)

## Conclusion
Accepted. Under verified `+/-80` limits and unannualized metrics, `Round1Submission` passes interior plateau, CSCV, and block DSR gates IS and dominates baselines across all fill regimes on Day 0 OOS. Companion attribution in [EXP-R1-002](EXP-R1-002_per_asset_attribution_and_bootstrap.md).
