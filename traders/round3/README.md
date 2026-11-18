# Round 3 Submission Trader (`traders/round3/submission.py`)

## 1. Strategy Thesis & Volatility Surface Model

Round 3 introduces a full exchange slate reset across `12` products (`Day 0, 1` IS; `Day 2` OOS): two spot goods (`HYDROGEL_PACK`, `VELVETFRUIT_EXTRACT`, `±200`) and ten European call vouchers (`VEV_4000`–`VEV_6500`, `±300`).

Two structural pitfalls cause naive options strategies (`OptionsVolatilityContract`, `-7,604.00` OOS) to fail:
1. **Horizon Misspecification**: Hardcoding `TTE = 5` days misprices `VEV_5000..5500` because exchange bot quotes behave closer to an effective `~8`-day maturity schedule. [`Round3Submission`](submission.py) instead solves directly for **scale-free total implied volatility** $v_K = \sigma_K \sqrt{\tau}$ via bounded bisection (`_invert_total_v`) smoothed via EWMA, eliminating calendar assumptions completely.
2. **Dead-Strike Illiquidity**: `VEV_6000/6500` carry `bid = 0, ask = 1` across `10,000` ticks/day, while `VEV_4000/4500` trade as nearly pure parity proxies (`S - K`).

## 2. Production Parameters & State Contract

- **Runtime Interface**: Strictly `datamodel` and Python stdlib (`json`, `math`, `statistics.NormalDist`, `typing`); passes [`scripts/validate_submission.py`](../../scripts/validate_submission.py).
- **Selected IS Plateau (`Day 0` & `1`)**: `MM_EDGE = 4.5`, `MM_SKEW = 0.10`, `OPT_EDGE = 0.5`, `HEDGE_BAND = 10.0`.
- **`state.traderData` Schema**: Persists rolling total-vol estimates $v_K$ across liquid strikes (`VEV_5200..5500`) alongside spot MM anchors.
- **Delta & Risk Control**: Aggregates Black-Scholes option delta across `VEV_4000/4500` (`delta ~ 1.0`) and `VEV_5200..5500`, neutralizing directional spot exposure via `VELVETFRUIT_EXTRACT` whenever net delta breaches `±HEDGE_BAND` while capturing wide `15.7`-tick passive spread on `HYDROGEL_PACK`.

## 3. Held-Out Out-of-Sample Replay (`Day 2`, `10,000` Ticks)

| Strategy | Fill Mode | OOS PnL (`Day 2`) | OOS `Sharpe_252` | Max Drawdown | Fills | Mean Latency |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: |
| `SymmetricSpotMM` | `queue_aware` | `-7,160.00` | `-0.0616` | `14,245.00` | `382` | `—` |
| `OptionsVolatilityContract` *(fixed `5d`)* | `queue_aware` | `-7,604.00` | `-0.0646` | `8,719.00` | `390` | `—` |
| **`Round3Submission`** | `conservative` | `7,275.00` | `0.2214` | `1,957.00` | `721` | `0.2186 ms` |
| **`Round3Submission`** | **`queue_aware`** | **`7,525.50`** | **`0.2276`** | **`1,936.00`** | **`726`** | **`0.1872 ms`** |
| **`Round3Submission`** | `touch` | `8,490.00` | `0.1800` | `2,393.50` | `988` | `0.1706 ms` |

- **Overfitting & Tail Risk (`IS` -> `OOS`)**: `CSCV PBO = 0.0000`, `DSR = 0.9921`, `N_eff = 1.12`; `HYDROGEL_PACK +4,730.00`, `VEV_4000 +2,553.00`; coupled MC (`N=25`, `1,000` steps) `ProbLoss = 0.0000`.

## 4. Verification & References

```bash
uv run python scripts/validate_submission.py traders/round3/submission.py
uv run pytest tests/unit/test_options_and_cross_asset.py -v
```

- Deep dive: [`docs/rounds/round_3.md`](../../docs/rounds/round_3.md) · [`EXP-R3-001`](../../reports/experiments/EXP-R3-001_round3_options_and_spot.md)
