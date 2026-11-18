# Strategy & Simulation Postmortems

Documenting structural failures and refuted hypotheses keeps quantitative intuition honest and prevents regressions across future strategies.

---

## `PM-001` — Naive Symmetric L1 Quoting Suffers Severe Lag & Adverse Selection (Rounds 1–2)

- **Incident Context**: Early Round 1–2 symmetric market makers (`SymmetricMM` in R1, `SymmetricMM_80` in R2) quoted equidistantly around raw L1 mid-price or slowly smoothed EMA values without filtering thin penny-quotes or inventory skewing.
- **Root Cause**:
  1. Thin insider/repricing L1 prints create artificial high-frequency variance (`Std(Delta P_L1) = 1.78–1.92` ticks in Round 1 IS) with strong `-0.50` bounce autocorrelation, triggering fill-and-fade losses on passive limit quotes.
  2. Without inventory-proportional reservation shading ($\gamma q$), quotes sit flush at the market while riding linear trends (`INTARIAN_PEPPER_ROOT` drift $\approx +0.108$/tick) all the way into full position-limit saturation (`Q_max = ±80`).
- **Observed Impact**:
  - Round 1 `Day 0` (`queue_aware`): `SymmetricMM` earned `+10,825.00` with `886.00` drawdown vs `+22,157.00` (`267.00` drawdown) for `Round1Submission`; in R1 Monte Carlo (`N=30`), `SymmetricMM` experienced `20%` probability of loss (`CVaR95 = -774.25`).
  - Round 2 `Day 1` (`queue_aware`, `±80`): `SymmetricMM_80` collapsed to **`-20,294.50` OOS PnL (`Sharpe_252 = -0.3348`, MaxDD `21,729.50`)**, whereas `Round2Submission` earned **`+27,463.00` (`419.50` MaxDD)**.
- **Permanent Control**: Quote fair values around deep resting bot walls (`_popular_wall_mid`, `-31%` to `-40%` step-noise std) and couple affine drift estimation with strong linear inventory skew before every quote generation call.

---

## `PM-002` — Single-Parameter Grid Cherry-Picking Fails Out-of-Sample Generalization

- **Incident Context**: Fine-grid optimization across isolated 2D hyperparameter peaks risks selecting narrow parameter islands driven by historical realization luck rather than structural microstructure.
- **Root Cause**: Evaluating an unconstrained `min_edge` $\times$ `inventory_skew` grid strictly by raw IS Sharpe without penalizing effective trial count $N_{\text{eff}}$ or testing contiguous block stability can accept brittle boundaries.
- **Observed Impact**: Enforcing `CSCV / PBO (< 0.15)`, `Deflated Sharpe Ratio (>= 0.95)`, and `3x3` neighborhood stability rejected brittle sharp-peak combinations across Rounds 1–5 and isolated smooth structural plateaus (`R1: 1.419 ± 0.020`, `R2: 1.360 ± 0.018`, `R3: 0.368 ± 0.054`, `R4: 0.350 ± 0.019`, `R5: 0.736 ± 0.064`).
- **Permanent Control**: Every production strategy commit must attach `r2_to_r5_overfitting_gates.csv`-style CSCV PBO, DSR, and single-pass OOS checks before deployment.

---

## `PM-003` — Hardcoded Black-Scholes Time-to-Expiry `T = 5` Blowout on `VEV_*` Options (Round 3)

- **Incident Context**: Initial Round 3 pricing benchmark [`OptionsVolatilityContract`](../reports/experiments/EXP-R3-001_round3_options_and_spot.md) plugged a hardcoded 5-day calendar horizon (`T = 5 / 252` to `2 / 252`) and historical underlying vol into standard Black-Scholes to value `VEV_4000..6500`.
- **Root Cause**: Exchange market makers priced `VEV_5000..5500` implied volatilities along an effective `~8`-day maturity schedule (`\hat{\sigma} \approx 0.20`). Evaluating Black-Scholes with `T = 5` systematically underpriced option fair value on every tick, causing the strategy to dump cheap asks relentlessly into counterparty bids and accumulate toxic naked delta/vega exposure.
- **Observed Impact**: Both IS (`-1,222.00` on `Day 0–1`) and held-out OOS (`-7,604.00` on `Day 2`, `Sharpe_252 = -0.0646`, MaxDD `8,719.00`) suffered persistent losses under `queue_aware` matching.
- **Permanent Control**: Value options via **calendar-invariant total implied volatility** ($v_K = \sigma_K \sqrt{\tau}$) inverted directly from live option mid-quotes (`_iv_and_bs_greeks` / total variance) and hedge portfolio net delta cleanly inside `HEDGE_BAND = 10` on `VELVETFRUIT_EXTRACT`, yielding **`+7,525.50` OOS** (`1,936.00` MaxDD).

## `PM-004` — Exponential Moving Average (EMA) Fair-Value Lag Blowout on High-Volatility Random Walks (Round 5)

- **Incident Context**: Early Round 5 multi-asset prototypes reused smoothed EMA fair-value estimators ($\alpha < 1$) designed for low-volatility stationary products (`Round 1`–`2`) across Round 5's `50` new assets ($\sigma_{\Delta P} \approx 10–30$ ticks/step, tight `±10` position limit).
- **Root Cause**: When underlying true value follows a martingale random walk with large per-step innovation variance, any lagged moving average trails true spot by multiple spread widths after every random jump. Waiting behind stale quotes turns our passive orders into free options picked off by fast takers (`-7.66M` collapse in initial smoothed prototype; `29,130.00` drawdown even on symmetric `EmaSymmetricMM_All50`).
- **Observed Resolution**: Comparing [`EmaSymmetricMM_All50`](../reports/tables/r5_ablation_summary.csv) vs [`Round5Submission`](../traders/round5/submission.py) on held-out `Day 4` (`queue_aware`): removing EMA lag + gating `Robots`/`Microchips` via dynamic step volatility cut MaxDD **`-78.7%`** (`29,130.00 -> 6,205.50`) and lifted `Sharpe_252` **`2.49x`** (`0.3260 -> 0.8109`).
- **Permanent Control**: Classify every instrument via rolling ADF/ACF_1/step-volatility diagnostics first; enforce **zero-lag fair value** ($\alpha = 1.0$ on resting bot walls) whenever `|ACF_1|` and unit-root tests reject fast mean reversion.

## `PM-005` — Resting Skew Interference & Static Basket Anchors on `Pebbles` and `Snackpacks` (Round 5)

- **Incident Context**: Even verified structural invariants behave differently depending on **reversion speed** (`Pebbles`) vs **drift speed** (`Snackpacks`) relative to our 1-tick decision loop.
- **Root Cause**:
  1. **`Pebbles` (`half-life = 0.16` ticks)**: Deviations from $\sum_{i=1}^5 P_i = 50{,}000$ snap back *within a single tick*. Shifting passive resting bids/asks on tick $t$ using `(sum - 50,000)` left quotes off-center on tick $t+1$ after the excursion had already vanished (costing `~4,000` XIRECs of passive capture vs unbiased wall-mid quoting).
  2. **`Snackpacks` (`K_day` shift `-98.2` ticks)**: Hardcoding `Day 2`'s pair mean `20,025.0` breaks on `Day 3` (`19,926.9`) and `Day 4` (`19,870.1`), producing persistent one-sided inventory saturation.
- **Permanent Control**: Track slow-moving cointegration intercepts online via an adaptive scalar in `traderData` (`K_day` EMA $\alpha = 0.005$ on `SNACKPACK_CHOCOLATE + VANILLA`), and decouple **atomic IOC cross-leg taking** (`take_fv_buy`/`sell` against `peb_imp`) from **unbiased passive MM quotes** when residual half-life is strictly sub-tick—capturing **`+15,469.00` OOS** on `Pebbles` while raising total `Round5Submission` IS/OOS Sharpe cleanly above `LagFreeMM_All50_NoBaskets`.
