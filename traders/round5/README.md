# Round 5 Submission Trader (`traders/round5/submission.py`)

## 1. Strategy Thesis & Multi-Timescale 50-Asset Architecture

Round 5 expands the exchange to **`50` spot contracts** across `10` categories (`Day 2, 3` IS; `Day 4` OOS; uniform `±10` per-symbol limits, `500` total gross lots). In-sample microstructure analysis reveals why lagged quoting breaks down under `±10` inventory caps (`EmaSymmetricMM_All50` suffers `29,130.00` OOS drawdown):
1. **Random-Walk Innovations (`sigma_diff ~ 10–30`) & Synchronized Pulses**: Zero independent noise prints occur; arrivals cluster into three category-wide synchronized pulse groups (`Group V` `40` symbols, `Pebbles` `5`, `Microchips` `5`) with `100%` uniform side and clip size.
2. **Sub-Tick Accounting Invariant (`Pebbles`)**: The five `PEBBLES_*` prices satisfy $\sum_{i=1}^5 P_i = 50{,}000 \pm 2.82$ (`ADF t = -70.16`, Ornstein-Uhlenbeck half-life `0.16` ticks OOS). Passive skew adjustment misses this sub-tick snapback; atomic **IOC cross-taking** decoupled from unbiased resting MM captures **`+15,469.00`** OOS on `Pebbles`.
3. **Regime-Shifting Pairs & High-Vol Guard**: `SNACKPACK_CHOCOLATE + VANILLA` (`r = -0.912`) shifts its equilibrium anchor $K_{\text{day}}$ (`-98.2` ticks across Days 2–3), tracked causally via slow online EMA (`PAIR_EMA_ALPHA = 0.005`), while `Robots` and `Microchips` dynamically widen quotes (`LOW_RATIO_EDGE_FRAC = 0.35`) when spread-to-vol drops below `VOL_GUARD_MULT = 0.50`.

## 2. Production Parameters & State Contract

- **Runtime Interface**: Strictly `datamodel` + Python stdlib (`json`, `math`, `typing`); passes [`scripts/validate_submission.py`](../../scripts/validate_submission.py).
- **Selected IS Plateau (`Day 2` & `3`)**: `EDGE_FRAC = 0.18`, `INVENTORY_SKEW = 1.25`, `QUOTE_CLIP = 10`, `PEBBLES_TAKE_BUFFER = 1.5`, `PAIR_RESIDUAL_WEIGHT = 0.25`.
- **`state.traderData` Schema**: JSON `{"k": float | None, "m": {sym: float}, "v": {sym: float}}` tracking online `Snackpacks` anchor and per-symbol EWMA step volatility.

## 3. Held-Out Out-of-Sample Replay (`Day 4`, `500,000` Book Rows)

| Strategy | Fill Mode | OOS PnL (`Day 4`) | OOS `Sharpe_252` | Max Drawdown | Fills | Mean Latency |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: |
| `EmaSymmetricMM_All50` | `queue_aware` | `114,851.00` | `0.3260` | `29,130.00` | `10,146` | `—` |
| `LagFreeMM_All50_NoBaskets` | `queue_aware` | `123,451.00` | `0.8089` | `6,205.50` | `7,396` | `—` |
| **`Round5Submission`** | `conservative` | `123,173.00` | `0.8109` | `6,205.50` | `7,477` | `0.6164 ms` |
| **`Round5Submission`** | **`queue_aware`** | **`123,173.00`** | **`0.8109`** | **`6,205.50`** | **`7,477`** | **`0.6920 ms`** |
| **`Round5Submission`** | `touch` | `140,545.50` | `0.8338` | `8,419.50` | `8,088` | `0.6661 ms` |

- **All-10 Category Attribution (`queue_aware`)**: `Galaxy Sounds +24,662.00`, `Oxygen Shakes +16,875.50`, `Snackpacks +15,965.00`, `Pebbles +15,469.00`, `Sleep Pods +12,020.50`, `UV-Visors +12,020.00`, `Panels +9,571.50`, `Translators +8,225.50`, `Microchips +7,124.00`, `Robots +1,240.00` (`88.3%` of single-day public-tape ceiling; `PBO = 0.1000`, `DSR = 1.0000`).

## 4. Verification & References

```bash
uv run python scripts/validate_submission.py traders/round5/submission.py
uv run pytest tests/integration/test_round2_to_round5_submissions.py -v
```

- Deep dive: [`docs/rounds/round_5.md`](../../docs/rounds/round_5.md) · [`EXP-R5-001`](../../reports/experiments/EXP-R5-001_round5_portfolio_optimization.md)
