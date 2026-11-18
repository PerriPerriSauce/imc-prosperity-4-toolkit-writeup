# Round 2 Submission Trader (`traders/round2/submission.py`)

## 1. Strategy Thesis & Scale Transition

Round 2 retains `ASH_COATED_OSMIUM` and `INTARIAN_PEPPER_ROOT` while quadrupling position limits from `±20` to **`±80` units** (`Day -1`, `Day 0` IS; `Day 1` OOS). Under `4x` inventory capacity, passive unskewed market making (`SymmetricMM_80`) suffers catastrophic inventory drift (`-20,294.50` OOS) by accumulating adverse short positions against `INTARIAN_PEPPER_ROOT`'s `+0.108`/tick linear drift.

[`Round2Submission`](submission.py) pairs bot-wall midpoint extraction (`_popular_wall_mid`) and causal alpha-beta trend estimation with wider plateau-calibrated edge thresholds (`MIN_EDGE = 3.5`) and scaled clip sizing (`QUOTE_CLIP = 30`).

## 2. Production Parameters & State Contract

- **Runtime Interface**: Strictly `datamodel` + Python stdlib (`json`, `math`, `typing`); passes [`scripts/validate_submission.py`](../../scripts/validate_submission.py).
- **Selected IS Plateau (`Day -1` & `0`)**: `MIN_EDGE = 3.5`, `INVENTORY_SKEW = 0.75`, `TAKE_EDGE = 1.0`, `QUOTE_CLIP = 30`, `EMA_ALPHA = 0.25`, `DRIFT_BETA = 0.01`.
- **`state.traderData` Schema**: JSON `{"fv": {...}, "drift": {...}, "ts": {...}}` preserving drift velocity across ticks.
- **Limit & Missing-Book Safety**: Skips fair-value updates whenever either book side vanishes; enforces aggregate starting-position `±80` batch bounds per symbol.

## 3. Held-Out Out-of-Sample Replay (`Day 1`, `10,000` Ticks)

| Strategy | Fill Mode | OOS PnL (`Day 1`) | OOS `Sharpe_252` | Max Drawdown | Fills | Mean Latency |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: |
| `SymmetricMM_80` | `queue_aware` | `-20,294.50` | `-0.3348` | `21,729.50` | `709` | `—` |
| `InventorySkewedMM_80` | `queue_aware` | `7,736.50` | `0.2445` | `3,784.50` | `1,016` | `—` |
| `DriftAwareQuoter_Pepper` | `queue_aware` | `6,344.50` | `0.3290` | `2,896.00` | `519` | `—` |
| **`Round2Submission`** | `conservative` | `27,378.00` | `1.3934` | `419.50` | `1,020` | `0.0385 ms` |
| **`Round2Submission`** | **`queue_aware`** | **`27,463.00`** | **`1.3972`** | **`419.50`** | **`1,022`** | **`0.0406 ms`** |
| **`Round2Submission`** | `touch` | `28,040.50` | `1.4117` | `392.50` | `1,053` | `0.0428 ms` |

- **Overfitting & Tail Risk (`IS` -> `OOS`)**: `CSCV PBO = 0.0000`, `DSR = 1.0000`, `N_eff = 1.22`; calibrated MAF Monte Carlo demonstrates `+33.4%` mean EV lift (`5,065.52 -> 6,755.98`, `ProbLoss = 0.0000`) under `+25%` arrival intensity.

## 4. Verification & References

```bash
uv run python scripts/validate_submission.py traders/round2/submission.py
uv run pytest tests/integration/test_round2_to_round5_submissions.py -k "round_num2 or synthetic"
```

- Deep dive: [`docs/rounds/round_2.md`](../../docs/rounds/round_2.md) · [`EXP-R2-001`](../../reports/experiments/EXP-R2-001_round2_scale_and_maf.md)
