# Round 1: Market Fundamentals & Empirical Microstructure

## 1. Tradable Instruments (Observed)

Verified from `data/raw/prosperity4/round1/prices_round_1_day_{-2,-1,0}.csv` (10,000 ticks per instrument per day, `timestamp` step = `100`):

- **`ASH_COATED_OSMIUM`**: Stationary mean-reverting instrument centered near `10,000` XIRECS.
- **`INTARIAN_PEPPER_ROOT`**: Linearly drifting instrument increasing by `+1,000` XIRECS per day (`+0.10` per 100-tick step: `10,000 -> 11,000 -> 12,000 -> 13,000`).

---

## 2. Empirical Microstructure Summary (Observed Data vs. Estimated Parameters)

We treat **Day -2** and **Day -1** as the exploratory/calibration split and **Day 0** as the out-of-sample verification split.

### A. Book Structure & Missing-Side Regimes (Observed)
Unlike Round 0 (`EMERALDS`, `TOMATOES`) where 100% of ticks are two-sided, Round 1 exhibits frequent liquidity gaps:
- **One-sided books**: `7.5%–8.0%` of ticks (`754–795` per day for `ASH_COATED_OSMIUM`; `726–768` per day for `INTARIAN_PEPPER_ROOT`).
- **Empty books**: `14–21` ticks per day where both `bid_price_1` and `ask_price_1` are missing (recorded as `mid_price == 0.0` in the raw CSV).
- **Methodological Implication**: Computing returns on raw CSV `mid_price` injects artificial $\pm 8$ tick jumps whenever one side vanishes. All empirical analysis below filters strictly to **two-sided ticks** (`bid_price_1` and `ask_price_1` both present).

### B. `ASH_COATED_OSMIUM` (Stationary Mean-Reverting Regime)
| Split | Day | Two-Sided Ticks | Mid Mean | Mid Std | Mean Spread | ADF $t$-stat (lags=2) | Est. OU $\hat{\theta}$ | Est. Half-Life |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Calibration | Day -2 | 9,187 | 9,998.16 | 4.73 | 16.15 | $-8.429$ (reject $H_0$) | 0.0853 | 8.13 ticks |
| Calibration | Day -1 | 9,225 | 10,000.83 | 3.83 | 16.19 | $-10.990$ (reject $H_0$) | 0.1352 | 5.13 ticks |
| **OOS Check** | **Day 0** | **9,232** | **10,001.62** | **5.22** | **16.18** | **$-7.898$ (reject $H_0$)** | **0.0732** | **9.47 ticks** |

- **Public Trade Flow**: 411–429 prints/day (~`4.1%–4.3%` arrival probability per tick), balanced ~50/50 between `ask_price_1` and `bid_price_1` touches, mean print size `5.15–5.25`.

### C. `INTARIAN_PEPPER_ROOT` (Deterministic Linear Drift + Proportional Noise)
| Split | Day | Two-Sided Ticks | Mid Mean | Mean Spread | Spread / Mid | OLS Drift Slope (`/step`) | OLS $R^2$ | Detrended Residual Std |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Calibration | Day -2 | 9,216 | 10,500.57 | 11.99 | 11.42 bps | `+0.10000` | 1.0000 | 1.1237 |
| Calibration | Day -1 | 9,219 | 11,501.41 | 13.01 | 11.31 bps | `+0.10001` | 1.0000 | 1.2596 |
| **OOS Check** | **Day 0** | **9,253** | **12,500.96** | **14.13** | **11.30 bps** | **`+0.10000`** | **1.0000** | **1.3352** |

- **Detrended Residuals**: Once detrended by $\hat{P}_t = \hat{\alpha} + 0.001 \cdot t$, residuals are strongly stationary across all 3 days (ADF $t = -55.50, -56.23, -55.92$) with near-zero AR(1) persistence ($\hat{b} \approx 0.006\text{–}0.015$).
- **Proportional Scaling**: Both the quoted spread (`~11.3 bps`) and detrended residual std (`~1.08 bps`) scale linearly with the underlying price level.
- **Public Trade Flow**: 332–344 prints/day (~`3.3%–3.4%` arrival probability per tick), mean print size `5.07–5.24`.

---

## 3. Position & Risk Constraints

- **Position Limits**: **UNVERIFIED** against official Prosperity 4 wiki/rules table (see [COMPETITION_SPECIFICATION.md](../competition/COMPETITION_SPECIFICATION.md)).
- **Exchange Order Check**: Worst-case aggregate buy/sell exposure evaluated against starting tick inventory.
