# Experiment EXP-R2-001: Round 2 Limit Scaling (+/-80) & Market Access Fee Valuation

- **Objective**: Calibrate Round 2 market making strictly In-Sample (`Days -1 & 0`) under official `+/-80` limits, pass `require_interior=True`, CSCV, and block-DSR gates, and quantify Market Access Fee arrival sensitivity (`N=40 x 1,000`).
- **IS Plateau Selected**: `min_edge = 2.5`, `inventory_skew = 0.40` (`IR_tick = 0.060523`, 3x3 mean `0.060408 +/- 0.000107`, IS PnL `186,226.00`, `N_eff = 1.0401`, `CSCV PBO = 0.3000`, `DSR_block = 1.0000`).
- **Why `PBO = 0.300` Occurred**: All interior `3x3` cells share nearly identical `IR_tick` (`0.0602..0.0606`, `N_eff = 1.04`), so 8-slice permutations swap top neighbor ranks easily without indicating genuine overfitting (`DSR_block = 1.0000`).

## Held-Out OOS Replay (`Day 1`, 10,000 Ticks, `+/-80`)

| Strategy | Fill Mode | OOS PnL | `IR_tick` | `BlkSR_1k` | `PnL/MaxDD` | Max DD | Fills |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| `SymmetricMM_80` | `queue_aware` | `-20,294.50` | `-0.02109` | `-0.868` | `-0.93` | `21,729.50` | `709` |
| `InventorySkewedMM_80` | `queue_aware` | `8,904.00` | `0.01812` | `0.700` | `2.95` | `3,022.50` | `1,022` |
| `DriftAwareQuoter_Pepper` | `queue_aware` | `7,823.50` | `0.02605` | `0.693` | `3.12` | `2,507.00` | `522` |
| `Round2Submission` | `conservative` | **`94,209.00`** | `0.05466` | `8.237` | `67.24` | `1,401.00` | `832` |
| `Round2Submission` | `queue_aware` | **`94,209.00`** | `0.05466` | `8.237` | `67.24` | `1,401.00` | `832` |
| `Round2Submission` | `touch` | **`94,293.00`** | `0.05471` | `8.233` | `67.30` | `1,401.00` | `846` |

- **Per-Asset OOS Attribution**: `INTARIAN_PEPPER_ROOT` `+81,163.00`, `ASH_COATED_OSMIUM` `+13,046.00`; portfolio circular block bootstrap 95% CI: `[87,698.94, 100,093.15]` XIRECs.
- **Monte Carlo (`N=40`, `queue_aware`)**: Baseline (`rate=0.08`) `10,966.54`, `+25% MAF` (`rate=0.10`) `12,631.66` (`0/40` losses, Wilson 95% upper `<= 0.0876`); `AdverseStress` (`p=0.30, jump=6.0`) `5,572.65` (`ProbLoss = 0.100`, Wilson 95% upper `<= 0.2305`).
