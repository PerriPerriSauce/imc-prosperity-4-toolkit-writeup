# Round 3: Velvetfruit Volatility Surface, Stationary Trap & Call Option Surface EDA

## 1. Round Structure & Product Reset

Round 3 initiated Phase 2 of IMC Prosperity 4 with a **full leaderboard reset** and a **clean product slate** (`12` tradable instruments, `120,000` order-book rows/day across `Day 0, 1, 2`):

- **Spot Market (`±200` Position Limit)**:
  - `HYDROGEL_PACK`: Wide-spread (`15.71` mean spread), mean-reverting spot asset fluctuating around `9,990`.
  - `VELVETFRUIT_EXTRACT`: Tight-spread (`4.99` mean spread) spot asset oscillating near `5,247–5,255`, serving as the **underlying** for all ten European call vouchers.
- **European Call Option Chain (`±300` Position Limit per Strike)**:
  - `VEV_4000`, `VEV_4500`, `VEV_5000`, `VEV_5100`, `VEV_5200`, `VEV_5300`, `VEV_5400`, `VEV_5500`, `VEV_6000`, `VEV_6500` (strikes $K \in [4{,}000, 6{,}500]$; `5` trading days remaining to expiry from Round 3 `Day 0` per community specification).
- **Manual Challenge ("The Celestial Gardeners' Guild")**: Two-stage sealed-bid auction on a discrete reserve grid $\{670, 675, \dots, 920\}$ with a `920` buyback and a cubic penalty $\big(\frac{920 - \bar{b}_2}{920 - b_2}\big)^3$ whenever $b_2 < \bar{b}_2$.

To prevent overfitting option pricing rules before live simulation, **In-Sample (IS) exploration uses `Day 0` and `Day 1`**, holding out **`Round 3 Day 2` and `Round 4 Day 3`** strictly as out-of-sample (OOS) checks on surface stability and time decay.

---

## 2. Underlying Spots & Stationary Mean-Reversion Dynamics (The Random-Walk Trap)

| Symbol | IS Mean | IS Std ($S_t$) | IS Mean Spread | $\text{Std}(\Delta S_t)$ | ADF $t$ (`Day 0`) | AR(1) Half-Life | `Day 0` $\to$ `Day 2` $\to$ `R4 Day 3` Mid |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | :--- |
| `HYDROGEL_PACK` | 9,991.51 | 32.07 | 15.71 | 2.1698 | $-3.67$ | 188.8 ticks | `9,990.96 -> 9,989.40 -> 10,002.50` |
| `VELVETFRUIT_EXTRACT` | 5,247.45 | 14.18 | 4.99 | 1.1277 | $-3.53$ | 206.1 ticks | `5,246.51 -> 5,255.39 -> 5,239.16` |

*(Source: [`reports/tables/r3_r4_options_surface.csv`](../../reports/tables/r3_r4_options_surface.csv).)*

A critical finding emerges immediately when comparing short-step diffusion against full-day variance:
- Naively scaling $\sigma_{\text{diff}} = 1.1277$/tick as a random walk across a `50,000`-tick (`5`-day) horizon predicts terminal dispersion $\sigma_T = 1.1277 \sqrt{50{,}000} \approx \mathbf{252.2\text{ XIRECs}}$.
- **In reality**, `VELVETFRUIT_EXTRACT` rejects the unit-root null on `Day 0` (`ADF t = -3.53 < -2.863`, half-life `206.1` ticks) and remains tightly bounded (`IS std = 14.18`, spanning roughly `[5,198, 5,300]` across all days). Its stationary distribution stays near $\sigma_{\infty} \approx 14\text{–}16$ XIRECs regardless of how many days remain!

---

## 3. Empirical Option Surface, Implied Volatility & Flow Audit

Table below summarizes all `10` strikes across IS (`Day 0–1`), multi-day OOS (`Day 2`, `R4 Day 3`), implied volatility under standard random-walk scaling (`TTE = 5 days = 50,000 ticks`), empirical regression delta $\hat{\Delta}_{\text{emp}} = \frac{\text{Cov}(\Delta C, \Delta S)}{\text{Var}(\Delta S)}$, and seller aggressiveness:

| Strike | IS Mid Mean | Bid $-$ Intr | Ask $-$ Intr | Bachelier $\sigma_{50k}$ | BS $\sigma_{5d}$ | $\hat{\Delta}_{\text{emp}}$ (IS) | $\Delta_{\text{Bach}, 50k}$ | `D0 -> D1 -> D2 -> D3` Mid | IS Trades | Seller-Init % |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :--- | ---: | ---: |
| **4000** | 1247.47 | $-10.37$ | +10.40 | 1.5595 | 0.5388 | 0.751 | 1.000 | `1246.5 -> 1248.4 -> 1255.4 -> 1239.2` | 336 | 51.8% |
| **4500** | 747.46 | $-7.89$ | +7.91 | 0.9543 | 0.3115 | 0.663 | 0.998 | `746.5 -> 748.4 -> 755.4 -> 739.2` | 1 | 0.0% |
| **5000** | 253.26 | +2.81 | +8.81 | 0.7699 | 0.2386 | 0.651 | 0.837 | `253.3 -> 253.3 -> 258.5 -> 241.6` | 1 | 0.0% |
| **5100** | 166.55 | +16.95 | +21.24 | 0.7761 | 0.2381 | 0.568 | 0.721 | `168.1 -> 165.0 -> 167.3 -> 150.3` | 1 | 0.0% |
| **5200** | 96.30 | **+47.40** | +50.30 | 0.7850 | 0.2386 | 0.431 | 0.575 | `97.5 -> 95.1 -> 94.1 -> 77.8` | 10 | **90.0%** |
| **5300** | 47.90 | **+46.83** | +48.97 | 0.7971 | 0.2400 | 0.272 | 0.417 | **`48.9 -> 46.9 -> 44.5 -> 32.1`** | 76 | **98.7%** |
| **5400** | 17.06 | **+16.36** | +17.76 | 0.7587 | 0.2262 | 0.132 | 0.273 | **`18.5 -> 15.7 -> 13.7 -> 8.5`** | 145 | **100.0%** |
| **5500** | 7.31 | +6.73 | +7.90 | 0.8272 | 0.2444 | 0.059 | 0.158 | `8.1 -> 6.6 -> 5.3 -> 2.3` | 173 | **100.0%** |
| **6000** | 0.50 | 0.00 | +1.00 | 1.3181 | 0.3727 | 0.000 | 0.001 | `0.5 -> 0.5 -> 0.5 -> 0.5` | 189 | **100.0%** |
| **6500** | 0.50 | 0.00 | +1.00 | 2.0782 | 0.5639 | 0.000 | 0.000 | `0.5 -> 0.5 -> 0.5 -> 0.5` | 189 | **100.0%** |

![Round 3 VEV Options Intrinsic Excess, Implied Vol Smile, and Seller Flow](../../reports/figures/r3_options_iv_smile_and_premium.png)

### Key Microstructural & Quantitative Insights

1. **No Static Cross-Strike Arbitrage (`0` Violations)**:
   - Checking all `20,000` IS rows confirms **zero ticks** where $\text{ask}(K_{\text{lo}}) < \text{bid}(K_{\text{hi}})$. Market-making bots keep cross-strike call monotonicity strictly intact.
2. **Stationary Underlying Makes ATM/Slightly-OTM Bids Structurally Overpriced**:
   - Under diffusive $\sqrt{T}$ Bachelier scaling (`50,000` ticks), quoted implied $\sigma \approx 0.76\text{–}0.83$ looks superficially *lower* than $\sigma_{\text{diff}} = 1.13$. That comparison is misleading because the spot process is **stationary** ($\sigma_\infty \approx 14\text{–}16$, half-life `206` ticks), NOT an unbounded Brownian motion!
   - Against the stationary distribution centered near `5,250`, a `VEV_5300` call lies more than `3` stationary standard deviations out of the money, yet market makers bid **`+46.83` XIRECs above intrinsic** (`VEV_5200`: `+47.40`; `VEV_5400`: `+16.36`).
3. **Relentless Time Decay ($\Theta$) Confirmed Out-of-Sample**:
   - Even as `VELVETFRUIT_EXTRACT` drifted *up* `+8.88` from `Day 0` (`5,246.51`) to `Day 2` (`5,255.39`), `VEV_5200..5500` decayed monotonically every single day (`VEV_5300`: `48.89 -> 46.91 -> 44.48 -> 32.14` by `R4 Day 3`; `VEV_5400`: `18.47 -> 15.65 -> 13.73 -> 8.50`). Note how bot market makers clearly use a Black-Scholes / diffusive theta schedule with decaying time-to-expiry!
4. **One-Sided Bot Dumping Flow at `K >= 5200` (`90%–100%` Seller-Initiated)**:
   - Practically every print on `VEV_5200..6500` executes at or below `bid_price_1`, meaning liquidity takers aggressively dump these strikes. Note also that `182–196` prints/day on `VEV_6000` & `VEV_6500` occur at `price == 0.0` (hitting resting `0`-bids), carrying zero economic edge and requiring explicit schema handling.
5. **Deep-ITM Liquidity & Empirical vs. Model Delta Divergence**:
   - Empirical regression deltas ($\hat{\Delta}_{\text{emp}}$) run `20%–35%` lower than theoretical $\Phi(d_1)$ (`0.431` vs `0.575` at `K=5200`; `0.272` vs `0.417` at `K=5300`) due to bid-ask bounce / quote noise attenuation in tick-level OLS. Meanwhile, `VEV_4000` / `VEV_4500` exhibit `bid - intrinsic = -10.37` and `-7.89`, leaving virtually zero time value in the mid (`+0.01`).

## 4. Candidate Hypotheses & Risk Limits

Two economic tensions govern Round 3 strategy design:
- **Volatility-Smile vs. Stationary Fair-Value Risk**: Because market makers quote `VEV_5000..5500` along a smooth diffusive volatility curve ($\hat{\sigma}_{\text{BS}} \approx 0.226\text{–}0.244$ on a `5`-day assumption) that decays monotonically toward expiry (`VEV_5300`: `48.89 -> 46.91 -> 44.48 -> 32.14` across Days `0 -> 3`), while `VELVETFRUIT_EXTRACT` stays confined inside a stationary band (`std = 14.18`, `ADF t = -3.53`, half-life `206.1` ticks), slightly OTM options trade well above stationary fair value (`+46.83` excess bid on `VEV_5300` while consuming only `~0.27–0.42` spot delta per call—easily fitting `300` options inside the `200`-unit spot hedge cap).
- **Spread-Cost Caution on `HYDROGEL_PACK`**: With a `15.7`-tick spread and slow `188.8`-tick mean reversion, crossing the spread destroys profitability quickly; passive market-making inside resting walls must be evaluated separately from aggressive delta crossing.

## 5. Architecture, Day-Invariant Option Valuation & OOS Verification

A critical failure mode uncovered when backtesting naive textbook Black-Scholes strategies in Round 3 (`PM-004`) is **expiry-schedule misspecification**. Prosperity's `TradingState` does not reveal settlement maturity $\tau$ programmatically (`Day 0` through `Day 3`), and back-inverting the `Day 0 -> Day 2` term decay shows liquidity bots pricing calls on an effective `~8`-day schedule ($\hat{\sigma} \approx 0.20$) rather than `5` days. Hardcoding `T = 5 - d` misvalued `VEV_5100..5500` systematically, causing our parametric baseline (`OptionsVolatilityContract`) to pay/cross bad prices (`-1,222.00` IS, `-7,604.00` OOS).

[`traders/round3/submission.py`](file:///c:/Users/pierr/Desktop/imc-prosperity-4-toolkit-writeup/traders/round3/submission.py) eliminates expiry clock assumptions via three orthogonal mechanisms:

1. **Day-Invariant Total Implied Volatility (`VEV_5200..5500`)**: Under $r = 0$, Black-Scholes depends solely on total variance $v = \sigma \sqrt{\tau}$:
   $$C_{\text{BS}}(S, K, v) = S\,\Phi\!\left(\frac{\ln(S/K) + \frac{1}{2}v^2}{v}\right) - K\,\Phi\!\left(\frac{\ln(S/K) - \frac{1}{2}v^2}{v}\right)$$
   Each tick, the submission inverts $v_K$ directly from contemporaneous wall-filtered spot (`VELVETFRUIT_EXTRACT`) and option mids via bounded bisection (`40` iterations), maintains a slow EWMA total-vol anchor ($\alpha = 0.05$) resilient to intra-day bounce, computes exact BS deltas $\Delta_K = \Phi(d_1)$, and quotes passive two-sided width around the smoothed surface without hardcoding calendar time.
2. **Deep-ITM Parity Capture (`VEV_4000`, `VEV_4500`, `±300`)**: Deep in-the-money calls (`VEV_4000` `20.8`-tick spread, `VEV_4500` `15.8`-tick spread) carry negligible optionality; treating them as `+1.0`-delta spot equivalents around $S_{\text{wall}} - K$ (`half_edge = 2.5`) captures wide passive market-making edge while transferring delta into `VELVETFRUIT_EXTRACT`.
3. **Spot Delta Neutralization Inside `HEDGE_BAND = 10`**: Aggregating portfolio delta $\Delta_{\text{net}} = q_{\text{spot}} + \sum_K q_K \Delta_K$ keeps net option gamma/delta exposure bounded, crossing `VELVETFRUIT_EXTRACT` top-of-book only when $|\Delta_{\text{net}}| > 10.0$ while passively market-making `HYDROGEL_PACK` (`±200`) inside wide `15.7`-tick spreads.

### 5.1 Statistical Validation Gates (`Day 0` & `Day 1` IS) & OOS (`Day 2`) Results

Sweeping `mm_edge in {1.5, 2.5, 3.5, 4.5}` $\times$ `mm_skew in {0.02, 0.04, 0.07, 0.10}` across `Day 0` & `Day 1` (`r3_sensitivity_grid.csv`) shows Sharpe improving monotonically as passive edge widens (`0.1297 -> 0.4351`) because crossing wide `HYDROGEL_PACK` / `VEV_4000` walls is punished by spread leakage:
- **Selected Plateau**: `mm_edge = 4.5, mm_skew = 0.10` (`IS Sharpe_252 = 0.4351`, `3x3` local mean `0.3684`, local std `0.0535`, `N_eff = 1.12`, **`CSCV PBO = 0.0000`**, **`DSR = 0.9921`**).

| Strategy | Fill Mode | IS PnL (`Day 0, 1`) | OOS PnL (`Day 2`) | OOS `Sharpe_252` | OOS Max DD | OOS Fills | Mean Latency |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| `NoOpBaseline` | `queue_aware` | 0.00 | 0.00 | 0.0000 | 0.00 | 0 | — |
| `SymmetricSpotMM` | `queue_aware` | 11,573.00 | $-7{,}160.00$ | $-0.0616$ | 14,245.00 | 382 | — |
| `OptionsVolatilityContract` | `queue_aware` | $-1{,}222.00$ | $-7{,}604.00$ | $-0.0646$ | 8,719.00 | 390 | — |
| **`Round3Submission`** | `conservative` | 28,373.00 | **7,275.00** | **0.2214** | **1,957.00** | 721 | 0.2186 ms |
| **`Round3Submission`** | `queue_aware` | 28,955.00 | **7,525.50** | **0.2276** | **1,936.00** | 726 | **0.1872 ms** |
| **`Round3Submission`** | `touch` | 33,214.00 | **8,490.00** | **0.1800** | **2,393.50** | 988 | 0.1706 ms |

### 5.2 Per-Instrument Attribution, Bootstrap & Coupled Options Monte Carlo

Dissecting held-out `Day 2` (`queue_aware`) attribution cleanly explains both edge sources and remaining friction:
- **Positive Attribution**: `HYDROGEL_PACK` **`+4,730.00`**, `VEV_4000` **`+2,553.00`**, `VEV_5200` **`+382.00`**, `VEV_4500` **`+117.00`**, `VEV_5300` **`+72.00`**.
- **Spot Hedging Friction (`-328.50`)**: `VELVETFRUIT_EXTRACT` absorbs crossing half-spread (`~2.5` ticks) during delta-rebalancing against counterparty adverse selection—directly motivating Round 4's counterparty flow classification (`Mark 67` / `Mark 49`).
- **Circular Block Bootstrap (`Day 2`, `block=100, B=1,000`)**: `Sharpe_252` 95% CI **`[0.0097, 0.4392]`**; PnL 95% CI **`[319.19, 15,054.22]`**.
- **Coupled Options+Spot MC (`N=25`, `1,000` steps)**: Mean PnL **`2,448.56`**, `VaR95 = 1,137.00`, `CVaR95 = 1,121.25`, **`ProbLoss = 0.0000`**, Mean `Sharpe_252 = 0.5189`, Worst Max DD `1,641.00`. *(See [`EXP-R3-001`](../../reports/experiments/EXP-R3-001_round3_options_and_spot.md).)*


