# Fair Value Estimation Across Regimes (Rounds 1–5)

Accurate fair value $V_t$ separates genuine fundamental drift from bid-ask bounce and informed counterparty flow. Across Rounds 1–5 of IMC Prosperity 4, five distinct stochastic regimes required matching estimator horizons to asset dynamics ([`postmortem.md`](../postmortem.md)).

## 1. Taxonomy of Empirical Fair-Value Estimators

| Regime Class | Instruments (Rounds) | Microstructure Signature | Selected Estimator | Pruned / Avoided Trap |
| :--- | :--- | :--- | :--- | :--- |
| **Stationary OU (`10,000` Anchor)** | `ASH_COATED_OSMIUM` (R1–R2), `HYDROGEL_PACK` (R3–R4) | `16`-tick median walls, strong mean reversion ($\mu \approx 10{,}000$) | Fixed `10,000` anchor (`Osmium`) / Bayesian-updated OU (`Hydrogel`, `Velvet`) | Removes L1 bounce noise (`-31%` to `-40%` step std) |
| **Deterministic Affine Drift** | `INTARIAN_PEPPER_ROOT` (R1–R2) | Exact linear trend (`+0.10000/tick`, `R^2 = 1.0000`, `ACF_1 ~ -0.45`) | Popular bot-wall fair value + asymmetric carry & skew | Eliminates short drift blowout (`SymmetricMM_80 -20,294.50`) |
| **Call-Option Surface** | `VEV_4000..5500` on `VELVETFRUIT_EXTRACT` (R3–R4) | Day-dependent calendar TTE mismatch (`~8d` bot clock vs `5d` nominal) | Total implied volatility ($v_K = \sigma_K \sqrt{\tau}$) + zero delta hedging | Eliminates fixed-TTE loss (`-1,051` baseline) and spot spread bleed |
| **Causal Counterparty Flow** | `VELVETFRUIT_EXTRACT` (R4 `Mark 14` & `Mark 55`) | Strictly causal `t - 100` `Mark 14 SELL` (`+3.788`, `t = 4.58`) & `Mark 55 BUY` (`+2.460`, `t = 4.07`) | Exponentially decayed fair-value impulse (`flow_weight = 1.5`) | Rejects `Mark 67` 1-tick bounce (`causal_1_to_200 = +0.113`, `t = 1.56`) |
| **High-Vol Random Walks & Lead-Lag** | `50` R5 Securities (`±10`) | RW steps with three synchronized pulses; discrete `MICROCHIP_CIRCLE` 50–200t lags | Zero-lag wall mid + vol-scaled AS (`vsm = 0.18`) + `mc_beta = 0.16` | Prunes lagged EMA (`29,130` DD), `Pebbles` crossing, and `VOL_GUARD` halts |

## 2. Why Popular Bot-Wall Mid Beats L1 Mid

Exchange market-making bots rest deep `10–30`-lot brackets around fair value, while thin `1–5`-lot orders flutter inside L1 (`mid_price`). Extracting fair value from maximum-volume resting walls ignores transient inside-spread ticks and naturally handles empty/one-sided books cleanly.

## 3. Why Filtering Helps Stationary Assets—and Hurts High-Volatility Random Walks

Exponential smoothing $\hat{V}_t = \alpha m_{\text{wall}, t} + (1 - \alpha)\hat{V}_{t-1}$ lowers variance only when microstructure noise dominates true innovation variance (`ASH_COATED_OSMIUM`). In **Round 5**, random-walk step innovations sit between `10` and `30` ticks inside tight `±10` position limits; lagging behind steps with `EmaSymmetricMM_All50` leaves stale quotes exposed to synchronized pulses (`29,130.00` OOS MaxDD, `PnL/MaxDD = 3.94`). Switching to zero-lag wall midpoints with proportional volatility-scaled inventory skew (`vol_skew_mult = 0.18, edge_frac = 0.14`) cuts OOS MaxDD cleanly in half (`14,961.50`) and lifts `PnL/MaxDD` `1.66x` (`6.53`).
