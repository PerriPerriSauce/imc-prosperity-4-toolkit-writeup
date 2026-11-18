# Round 1 Submission Trader (`traders/round1/submission.py`)

## 1. Strategy Thesis & Market Microstructure

Round 1 opens with two low-limit securities (`ASH_COATED_OSMIUM` and `INTARIAN_PEPPER_ROOT`, `±20` assumed configurable limit; **UNVERIFIED** against external portal logs). Inspecting raw historical order books (`Day -2`, `Day -1` IS; `Day 0` OOS) reveals:
- Resting liquidity is anchored by deep institutional bot walls surrounded by wide spreads (`12–16` ticks) containing intermittent inside-spread retail prints and `~7.5%` one-sided ticks.
- Naive unweighted L1 midpoints absorb substantial bid-ask bounce; filtering fair value via `_popular_wall_mid` (selecting the highest-volume resting bid and ask levels) cuts innovation step variance by `30.9%–40.0%` in-sample.
- `ASH_COATED_OSMIUM` mean-reverts around a stable stationary regime (`EMA alpha = 0.25`), while `INTARIAN_PEPPER_ROOT` exhibits persistent linear drift tracked causally by an alpha-beta filter (`alpha = 0.25, beta = 0.01`).

## 2. Production Parameters & State Contract

- **Runtime Interface**: Imports strictly from `datamodel` and Python stdlib (`json`, `math`, `typing`); verified by [`scripts/validate_submission.py`](../../scripts/validate_submission.py).
- **Selected IS Plateau (`Day -2` & `-1`)**: `min_edge = 1.5`, `inventory_skew = 0.80`, `take_edge = 1.0`, `quote_size = 5`.
- **`state.traderData` Schema**: JSON payload `{"fv": {sym: float}, "drift": {sym: float}, "ts": {sym: int}}` with defensive malformed-JSON fallback.
- **Limit & Missing-Book Safety**: Skips passive midpoint updates on one-sided/empty books (`~7.5%` of Round 1 ticks) and clamps every buy/sell batch strictly within `[start_pos - 20, start_pos + 20]`.

## 3. Held-Out Out-of-Sample Replay (`Day 0`, `10,000` Ticks)

| Strategy | Fill Mode | OOS PnL (`Day 0`) | OOS `Sharpe_252` | Max Drawdown | Fills | Mean Latency |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: |
| `NoOpBaseline` | `queue_aware` | `0.00` | `0.0000` | `0.00` | `0` | `—` |
| `SymmetricMM` *(L1 touch)* | `queue_aware` | `10,825.00` | `0.5005` | `886.00` | `582` | `—` |
| `InventorySkewedMM` | `queue_aware` | `9,067.00` | `0.4029` | `837.50` | `931` | `—` |
| **`Round1Submission`** | `conservative` | `22,151.00` | `1.1885` | `267.00` | `1,001` | `0.0410 ms` |
| **`Round1Submission`** | **`queue_aware`** | **`22,157.00`** | **`1.1894`** | **`267.00`** | **`1,003`** | **`0.0340 ms`** |
| **`Round1Submission`** | `touch` | `22,667.00` | `1.2220` | `274.50` | `1,024` | `0.0369 ms` |

- **Overfitting Gates (`Day -2, -1` IS)**: `CSCV PBO = 0.0860`, `DSR = 1.0000`, `N_eff = 1.11`, circular block bootstrap OOS `Sharpe_252` 95% CI `[1.046, 1.329]`, calibrated MC (`N=30`) `ProbLoss = 0.0000`.

## 4. Verification & References

```bash
uv run python scripts/validate_submission.py traders/round1/submission.py
uv run pytest tests/integration/test_round1_submission.py -v
```

- Deep dive: [`docs/rounds/round_1.md`](../../docs/rounds/round_1.md) · [`EXP-R1-001`](../../reports/experiments/EXP-R1-001_baseline_vs_refined.md) · [`EXP-R1-002`](../../reports/experiments/EXP-R1-002_per_asset_attribution_and_bootstrap.md)
