# Experiment EXP-R1-002: Round 1 Per-Asset Attribution & Block Bootstrap Inference

- **Objective**: Decompose `Round1Submission` Day 0 OOS PnL by asset under verified `+/-80` limits and separate portfolio-level block-bootstrap confidence intervals from asset-level point attributions.
- **OOS Portfolio Total (`queue_aware`)**: `91,098.00 XIRECs`, `IR_tick = 0.05444`, `BlkSR_1k = 9.327`, `MaxDD = 1,405.00`.
- **Circular Block Bootstrap 95% CI (block_size=100, B=1,000)**: `IR_tick` in `[0.05052, 0.05875]`; `PnL` in `[85,711.14, 96,434.06]`.

## Per-Asset Day 0 OOS Mark-to-Market Attribution

| Symbol | Scope | OOS PnL (XIRECs) |
| :--- | :--- | ---: |
| `PORTFOLIO` | `portfolio` | **91,098.00** |
| `ASH_COATED_OSMIUM` | `asset` | 11,371.00 |
| `INTARIAN_PEPPER_ROOT` | `asset` | 79,727.00 |

## Methodological Note
Portfolio bootstrap intervals reflect the aggregate tick PnL process across a single held-out 10,000-tick session (with weak overnight independence limited by having two IS days and one OOS day); asset rows intentionally omit duplicated portfolio intervals in [r1_bootstrap_and_attribution.csv](../tables/r1_bootstrap_and_attribution.csv).
