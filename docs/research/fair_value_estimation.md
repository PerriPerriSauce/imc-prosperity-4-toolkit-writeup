# Fair Value Estimation Across Regimes (Rounds 1–5)

Accurate fair value $V_t$ separates genuine fundamental drift from bid-ask bounce and informed toxic flow. Across Rounds 1–5 of IMC Prosperity 4, five distinct stochastic regimes required fundamentally different estimators—and reusing the wrong estimator across regimes proved to be the single largest source of strategy drawdowns ([`postmortem.md`](../postmortem.md)).

## 1. Taxonomy of Empirical Fair-Value Estimators

| Regime Class | Observed Instruments (Rounds) | Microstructure Signature | Selected Estimator | Avoided Failure Mode |
| :--- | :--- | :--- | :--- | :--- |
| **Wide-Wall Mean-Reverting OU** | `ASH_COATED_OSMIUM` (R1–R2), `HYDROGEL_PACK` (R3–R4) | `15–16`-tick resting walls, OU half-life `5.4–10.5` ticks (R1–R2) or `~188.8` ticks (R3 `HYDROGEL_PACK`), deep popular walls | Popular Bot-Wall Midpoint (`_popular_wall_mid`) | Removes `38.7–40.0%` of raw L1 bounce noise std (`EXP-R1-002`) |
| **Steady Linear / Affine Drift** | `INTARIAN_PEPPER_ROOT` (R1–R2) | Slope $\approx +0.108$/tick, `R^2_linear = 1.0`, `ACF_1(dmid) ≈ -0.495` | Two-Stage Wall-Mid OLS / Trend Anchor (`drift_alpha + slope * t`) | Eliminates resting inventory drift-lag (`SymmetricMM_80` lost `-20,294.5` OOS) |
| **Call-Option Surface** | `VEV_4000..6500` on `VELVETFRUIT_EXTRACT` (R3–R4) | Deep-ITM parity vs convexity near ATM (`VEV_5000..5500` IV $\approx 23–24\%$ vs effective `8d` schedule) | Calendar-Invariant Total Implied Vol ($v_K = \sigma_K \sqrt{\tau}$) + Deep-ITM Parity (`S - K`) | Eliminates hardcoded `T = 5` blowout (`-7,604.00` OOS loss) |
| **Informed Counterparty Flow** | `VELVETFRUIT_EXTRACT` (R4 live IDs) | `Mark 67` (`100%` buyer) & `Mark 49` (`100%` seller) trigger `+1.90–1.97` permanent jump at `h = 1..50` ticks | Contemporaneous Flow Bump (`± M67_BUMP=0.5`, decay `0.80`) on `state.market_trades` | Flips `VELVETFRUIT_EXTRACT` OOS from `-328.5` (R3) to **`+1,027.0`** (R4) |
| **High-Vol Random Walks & Baskets** | `50` Round 5 Spot Securities (`10` categories) | Step volatility $\sigma_{\Delta P} \approx 10–30$, tight `±10` caps; `Pebbles` sum `= 50,000` (`hl = 0.16`); `Snackpack` daily shifting pair | Zero-Lag Bot-Wall Mid ($\alpha = 1.0$) + Rolling `K_day` Pair EMA ($\alpha = 0.005$) + Atomic Pebbles IOC | Cuts R5 drawdown **`-78.7%`** vs lagged EMA (`29,130 -> 6,205.5`) and lifts OOS PnL to **`+123,173.00`** |

## 2. Empirical Noise Attenuation: Why Popular Bot-Wall Mid Beats L1 Mid

On Prosperity exchanges, institutional market-making bots rest large `10–30` lot orders symmetrically around fair value, while noisy human or small-size repricing orders flutter inside the top of book (`L1`). Taking raw L1 mid-price:

$$m_{\text{L1}, t} = \frac{b_{1,t} + a_{1,t}}{2}$$

treats every single-lot penny improvement as a shift in intrinsic value. In Round 1 IS (`EXP-R1-002`), switching to the max-volume resting wall midpoint $m_{\text{wall}, t}$ attenuated one-tick difference standard deviation from `1.78–1.92` ticks down to `1.09–1.17` ticks (`-30.9%` to `-40.0%` std reduction; `52–64%` variance cut) across *both* `ASH_COATED_OSMIUM` and `INTARIAN_PEPPER_ROOT`. Note also a practical bonus: `_popular_wall_mid` handles missing L1 sides naturally without forward-looking state, returning `None` cleanly whenever either side of the book is empty.

## 3. Why Filtering Helps Stationary Assets—and Blows Up High-Volatility Random Walks

Applying exponential smoothing $\hat{V}_t = \alpha m_{\text{wall}, t} + (1 - \alpha)\hat{V}_{t-1}$ improves RMSE only when observation noise $\sigma_\epsilon^2$ dominates innovation variance $\sigma_\eta^2$ (steady-state Kalman gain $K < 1$ requires small signal-to-noise ratio $\sigma_\eta^2 / \sigma_\epsilon^2$).

- When $P_t$ evolves as a slow stationary OU (`Osmium`, $\sigma_{\Delta P} \approx 1.9$) behind wide spreads (`16` ticks), steady-state Kalman gain stays below `1` without risking adverse fills.
- In **Round 5**, however, asset step innovations jumped to $\sigma_{\Delta P} \approx 10–30$ ticks per timestamp with zero stationary drift mean. Any smoothing $\alpha < 1$ lags behind true fair value by multiple spread widths after random jumps, turning resting passive quotes into negatively skewed free options against informed/synchronized Poisson pulse takers (`EmaSymmetricMM_All50` suffered `29,130.00` OOS drawdown with `Sharpe_252 = 0.3260` vs **`6,205.50`** MaxDD and **`0.8109`** Sharpe for lag-free [`Round5Submission`](../../traders/round5/submission.py)).

## 4. Non-Stationary Cross-Asset Fair Value (`K_day`) vs Instantaneous Parity

Cross-asset relationships also divide cleanly by reversion timescale:
1. **Slowly Drifting Anchor (`SNACKPACK_CHOCOLATE + VANILLA`)**: Daily pair sum mean shifted from `20,025.04` (`Day 2`) $\to$ `19,926.89` (`Day 3`) $\to$ `19,870.09` (`Day 4`), while maintaining `-0.912` to `-0.918` return difference correlation. Tracking the equilibrium intercept online (`K_day` EMA $\alpha = 0.005$ persisted in `traderData`) centers quoting around contemporary session parity without hardcoded constant bias.
2. **Ultra-Fast Structural Sum (`PEBBLES_XS..XL`)**: Total sum stays anchored at `50,000 ± 2.82` with an Ornstein–Uhlenbeck half-life of `0.16` ticks OOS. Fair value residuals mean-revert faster than one simulation step, meaning passive fair-value shifts expire stale; instead, keeping resting quotes anchored on local `wall_mid` while triggering atomic IOC taking whenever implied `peb_imp` clears `TAKE_EDGE + PEBBLES_TAKE_BUFFER` preserves spread edge (`+15,469.00` OOS on `Pebbles`).
