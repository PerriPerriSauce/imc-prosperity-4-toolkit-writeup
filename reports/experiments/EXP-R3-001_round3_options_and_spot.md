# Experiment EXP-R3-001: Round 3 Spot Market Making & Day-Invariant Options Hedging

- **Hypothesis**:
  1. Extracting wide-spread (`15.7`-tick) liquidity on `HYDROGEL_PACK` (`±200`) and deep-ITM parity (`S - K`) on `VEV_4000` / `VEV_4500` (`±300`), while valuing `VEV_5200..5500` via online-inverted Black-Scholes total volatility ($v_K = \sigma_K \sqrt{\tau}$) and hedging net option delta inside `HEDGE_BAND = 10` on `VELVETFRUIT_EXTRACT` (`±200`), avoids random-walk TTE misspecification and delivers positive OOS PnL across fill modes.
- **Calibration Split (IS)**: Round 3 `Day 0` & `Day 1` (`queue_aware`).
- **Held-Out Out-of-Sample Split (OOS)**: Round 3 `Day 2` (`10,000` ticks) + `N=25` Coupled Options+Spot Monte Carlo sessions.

---

## 1. Statistical Validation Gates (IS `Day 0` & `Day 1`)

Sweeping `mm_edge in {1.5, 2.5, 3.5, 4.5}` $\times$ `mm_skew in {0.02, 0.04, 0.07, 0.10}`:
- **Plateau Selected**: `mm_edge = 4.5`, `mm_skew = 0.10` (`N_eff = 1.12`)
- **Neighborhood Stability**: `IS Sharpe_252 = 0.4351`, `local_mean = 0.3684`, `local_std = 0.0535`
- **CSCV / PBO (`70` splits)**: **`PBO = 0.000`** (`passes < 0.15`)
- **Deflated Sharpe Ratio (`16` trials)**: **`DSR = 0.9921`** (`passes >= 0.95`)

*(Source: [`reports/tables/r3_sensitivity_grid.csv`](../tables/r3_sensitivity_grid.csv), [`reports/tables/r2_to_r5_overfitting_gates.csv`](../tables/r2_to_r5_overfitting_gates.csv).)*

---

## 2. Out-of-Sample Replay & Coupled Monte Carlo Results

| Strategy | Fill Mode | IS PnL (`Day 0, 1`) | OOS PnL (`Day 2`) | OOS `Sharpe_252` | OOS Max DD | OOS Fills | Mean Latency |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| `NoOpBaseline` | `queue_aware` | 0.00 | 0.00 | 0.0000 | 0.00 | 0 | — |
| `SymmetricSpotMM` | `queue_aware` | 11,573.00 | $-7{,}160.00$ | $-0.0616$ | 14,245.00 | 382 | — |
| `OptionsVolatilityContract` *(fixed `T=5`)* | `queue_aware` | $-1{,}222.00$ | $-7{,}604.00$ | $-0.0646$ | 8,719.00 | 390 | — |
| **`Round3Submission`** | `conservative` | 28,373.00 | **7,275.00** | **0.2214** | **1,957.00** | 721 | 0.2147 ms |
| **`Round3Submission`** | `queue_aware` | 28,955.00 | **7,525.50** | **0.2276** | **1,936.00** | 726 | **0.2171 ms** |
| **`Round3Submission`** | `touch` | 33,214.00 | **8,490.00** | **0.1800** | **2,393.50** | 988 | 0.2020 ms |

- **OOS Asset Breakdown (`Day 2`, `queue_aware`)**: `HYDROGEL_PACK` **`+4,730.00`**, `VEV_4000` **`+2,553.00`**, `VEV_5200` **`+382.00`**, `VEV_4500` **`+117.00`**, `VEV_5300` **`+72.00`**, `VELVETFRUIT_EXTRACT` **`-328.50`** *(spot absorbs delta hedge & spread cost; net portfolio `+7,525.50`)*.
- **Circular Block Bootstrap (`block=100, B=1,000`)**: `Sharpe_252` 95% CI **`[0.0097, 0.4392]`**, OOS PnL 95% CI **`[319.19, 15,054.22]`**.
- **Coupled Options+Spot MC (`N=25`, `1,000` steps)**: Mean PnL **`2,448.56`**, Std **`738.98`**, `VaR95 = 1,137.00`, `CVaR95 = 1,121.25`, **`ProbLoss = 0.0000`**.

## Key Failure Mode Diagnosed & Conclusion
Notice why `OptionsVolatilityContract` with a hardcoded `5`-day calendar failed both IS (`-1,222.00`) and OOS (`-7,604.00`): market makers priced `VEV_5000..5500` consistent with roughly an `8`-day schedule ($\hat{\sigma} \approx 0.20$), causing stale fixed-horizon BS models to short undervalued bids aggressively. Inverting total volatility $v_K = \sigma_K \sqrt{\tau}$ directly from option mids eliminates expiry-calendar bias completely. Accepted.
