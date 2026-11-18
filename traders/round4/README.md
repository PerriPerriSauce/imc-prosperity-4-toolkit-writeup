# Round 4 Submission Trader (`traders/round4/submission.py`)

## 1. Strategy Thesis & Counterparty Flow Selection

Round 4 retains the `12`-symbol Round 3 universe (`Day 1, 2` IS; `Day 3` OOS) while exposing live trade counterparty labels (`Mark 01..67`) inside `state.market_trades`. Disaggregating mark-outs by exact asset (`VELVETFRUIT_EXTRACT`) rather than pooling across disparate spreads exposes a sharp toxicity contrast:
- **`Mark 67`** buys with `100%` directional consistency ahead of permanent `+1.970`-tick mid jumps (`h = +1..50`).
- **`Mark 49`** absorbs passive liquidity with zero persistent directional edge.

[`Round4Submission`](submission.py) adds a decaying `Mark 67` buy-print impulse (`M67_BUMP = 0.5`, `M67_DECAY = 0.80`) onto `VELVETFRUIT_EXTRACT` fair valuation while widening `HYDROGEL_PACK` to its Round 4 IS plateau (`MM_EDGE = 5.5, MM_SKEW = 0.08`). An aggressive spot-chasing alternative (`s_alpha = 0.85`) failed `CSCV` (`PBO = 0.9714 > 0.15`) and `DSR` (`0.9390 < 0.95`) in-sample and was vetoed before OOS evaluation.

## 2. Production Parameters & State Contract

- **Runtime Interface**: Strictly `datamodel` + Python stdlib (`json`, `math`, `statistics.NormalDist`, `typing`); passes [`scripts/validate_submission.py`](../../scripts/validate_submission.py).
- **Selected IS Plateau (`Day 1` & `2`)**: `MM_EDGE = 5.5`, `MM_SKEW = 0.08`, `M67_BUMP = 0.5`, `M67_DECAY = 0.80`, `OPT_EDGE = 0.5`, `HEDGE_BAND = 10.0`.
- **`state.traderData` Schema**: Persists decayed `Mark 67` toxicity state alongside total implied volatility anchors $v_K$.

## 3. Held-Out Out-of-Sample Replay (`Day 3`, `10,000` Ticks)

| Strategy | Fill Mode | OOS PnL (`Day 3`) | OOS `Sharpe_252` | Max Drawdown | Fills | Mean Latency |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: |
| `NoOpBaseline` | `queue_aware` | `0.00` | `0.0000` | `0.00` | `0` | `—` |
| `Round3Ungated` *(no `Mark 67`)* | `queue_aware` | `12,048.00` | `0.3488` | `3,250.50` | `758` | `0.1933 ms` |
| **`Round4Submission`** | `conservative` | `11,635.00` | `0.3587` | `2,865.00` | `728` | `0.1919 ms` |
| **`Round4Submission`** | **`queue_aware`** | **`11,741.00`** | **`0.3613`** | **`2,901.00`** | **`731`** | **`0.1871 ms`** |
| **`Round4Submission`** | `touch` | `13,259.50` | `0.2780` | `3,560.00` | `1,041` | `0.2017 ms` |

- **Key Marginal Gain**: Conditioning on `Mark 67` turns `VELVETFRUIT_EXTRACT` OOS from `-328.50` (`R3`) to **`+1,027.00`**, trims MaxDD **`-10.8%`** (`3,250.50 -> 2,901.00`), and raises annualized `Sharpe_252` across every fill mode (`PBO = 0.0571`, `DSR = 0.9975`).

## 4. Verification & References

```bash
uv run python scripts/validate_submission.py traders/round4/submission.py
```

- Deep dive: [`docs/rounds/round_4.md`](../../docs/rounds/round_4.md) · [`EXP-R4-001`](../../reports/experiments/EXP-R4-001_round4_counterparty_flow.md)
