# IMC Prosperity 4 — Quantitative Research, Strategy Engineering & Final Writeup

> **Artifacts**: Open [`reports/dashboard.html`](dashboard.html) for interactive tearsheet tabs or [`IMC_Prosperity4_Research_Writeup.pdf`](IMC_Prosperity4_Research_Writeup.pdf) for the compiled A4 monograph.

## Executive Summary

Across five competition rounds of **IMC Prosperity 4**, we developed a reproducible Python 3.11 research toolkit ([`src/prosperity_toolkit/`](../src/prosperity_toolkit)) and five dependency-free competition submissions (`traders/round{1..5}/submission.py`). Single-pass chronological held-out **Out-of-Sample (`OOS`)** backtests under queue-priority matching (`queue_aware`) and verified official position limits (`±80` R1–R2, `±200/±300` R3–R4, `±10` R5) earn:

- **Phase 1 Simulated OOS Algorithmic Subtotal (R1 Day 0 + R2 Day 1)**: **`+185,307.00` XIRECs** (`+91,098.00` R1, `+94,209.00` R2).
- **Phase 2 Simulated OOS Algorithmic Subtotal (R3 Day 2 + R4 Day 3 + R5 Day 4)**: **`+453,261.00` XIRECs** (`+95,093.00` R3, `+260,540.00` R4, `+97,628.00` R5).
- **Cumulative 5-Day Simulated OOS Total**: **`+638,568.00` XIRECs**, clearing `DSR_block >= 0.9783` across all five rounds with peak execution latency `0.5518 ms/tick` across 50 simultaneous Round 5 books.

All historical backtest figures, Monte Carlo distributions, and **offline ex-ante Manual Challenge models** (`225,094.01` R2 EV; `855,944.53` R5 risk-adjusted KKT EV) are kept strictly distinct and never presented as live competition portal results.

## 1. End-to-End Methodology & Epistemic Discipline

1. **Strict Chronological Isolation**: Calibration and feature discovery run strictly In-Sample (`IS`: `(-2,-1)` R1, `(-1,0)` R2, `(0,1)` R3, `(1,2)` R4, `(2,3)` R5); the final day of each round is evaluated once OOS after freezing submission defaults. *(Note: archived R3 Day 2 and R4 Day 2 share identical price CSVs and differing trade prints; IS/OOS splits keep R3 OOS Day 2 chronologically non-overlapping with R4 OOS Day 3.)*
2. **Causal Queue-Conserving Execution** ([`simulator.py`](../src/prosperity_toolkit/execution/simulator.py), [`replay.py`](../src/prosperity_toolkit/backtesting/replay.py)): Deliveries of `market_trades` and `own_trades` are strictly lagged from `t - 100` (zero same-tick look-ahead); passive resting orders execute behind observed book liquidity in strict price-time queue priority without double-counting trade volume.
3. **Unannualized Metrics & Correlated-Grid Validation** ([`metrics.py`](../src/prosperity_toolkit/backtesting/metrics.py), [`diagnostics.py`](../src/prosperity_toolkit/analysis/diagnostics.py)):
   - Performance is reported in unscaled per-tick Information Ratio (`IR_tick`), disjoint 1,000-tick block Sharpe (`BlkSR_1k`), and intraday `PnL/MaxDD`—never inflated by `sqrt(252)`.
   - `require_interior=True` selects `3x3` neighborhood plateaus rather than boundary edge picks.
   - `DSR_block` evaluates 100-tick block Sharpes penalized by effective independent trials `N_eff` rather than inflated raw tick counts.

## 2. Algorithmic Results & Empirical Discoveries (Rounds 1–5)

### 2.1 Held-Out OOS & Overfitting Gate Scorecard (`queue_aware`)

| Round | Submission | OOS Day | OOS PnL | `IR_tick` | `BlkSR_1k` | `Max DD` | `PnL/DD` | `CSCV PBO` | `N_eff` | `DSR_block` | Latency |
| :---: | :--- | :---: | ---: | ---: | ---: | ---: | ---: | :---: | :---: | :---: | ---: |
| **R1** | [`round1`](../traders/round1/submission.py) | `Day 0` | **`+91,098.00`** | `0.05445` | `9.327` | `1,405.00` | `64.84` | `0.1286` | `1.02` | `1.0000` | `0.020 ms` |
| **R2** | [`round2`](../traders/round2/submission.py) | `Day 1` | **`+94,209.00`** | `0.05466` | `8.237` | `1,401.00` | `67.24` | `0.3000` | `1.04` | `1.0000` | `0.028 ms` |
| **R3** | [`round3`](../traders/round3/submission.py) | `Day 2` | **`+95,093.00`** | `0.00584` | `0.573` | `75,774.00` | `1.26` | `0.0000` | `1.01` | `0.9966` | `0.325 ms` |
| **R4** | [`round4`](../traders/round4/submission.py) | `Day 3` | **`+260,540.00`** | `0.01680` | `0.646` | `71,177.00` | `3.66` | `0.0143` | `1.02` | `0.9783` | `0.293 ms` |
| **R5** | [`round5`](../traders/round5/submission.py) | `Day 4` | **`+97,628.00`** | `0.02624` | `1.108` | `14,961.50` | `6.53` | `0.5429` | `1.14` | `1.0000` | `0.552 ms` |
| **Total** | — | 5 Days | **`+638,568.00`** | — | — | — | — | — | — | `>= 0.978` | `<= 0.552 ms` |

> *Note on CSCV PBO in Rounds 2 & 5*: When adjacent parameter grid points generate nearly identical tick streams (`N_eff = 1.04` R2, `1.14` R5) and `3x3` surfaces are flat (`locStd = 0.00011` and `0.00055`), slice rank swaps happen near-randomly, producing elevated `PBO` (`0.300`, `0.543`) despite strong out-of-sample generalization and `DSR_block = 1.0000`.

![Normalized OOS Equity Trajectories](figures/r2_to_r5_oos_equity_summary.png)

### 2.2 Round-by-Round Microstructure Alpha & Honest Negative Results

- **Rounds 1 & 2 (`ASH_COATED_OSMIUM`, `INTARIAN_PEPPER_ROOT`, `±80`)**:
  `ASH_COATED_OSMIUM` mean-reverts tightly around `10,000` (`spread = 16`, `half-life = 5.4–10.5` ticks) while `INTARIAN_PEPPER_ROOT` exhibits an exact deterministic linear drift of `+0.10000/tick` (`+1,000/day`, `R^2 = 1.0000`). Anchoring Osmium at `10,000` with `inventory_skew = 0.40` while accumulating `+80` carry on Pepper Root generates `+91,098.00` (R1 OOS) and `+94,209.00` (R2 OOS), whereas naive `SymmetricMM_80` loses `-20,294.50` OOS on R2. Under `N=40` synthetic MC runs, boosting bot arrival rate from `0.08` to `0.10` (+25% MAF leverage) lifts mean 1,000-tick PnL from `10,966.54` to `12,631.66`.
- **Round 3 (`HYDROGEL_PACK`, `VELVETFRUIT_EXTRACT`, `VEV_4000..6500`, `±200/±300`)**:
  - *Negative result*: Dynamic delta-hedging option inventory via taker spot orders destroys edge across wide spot spreads and was **removed**. Deep-OTM `VEV_6000` / `VEV_6500` always center around `0.5` (`0` value) and are skipped.
  - *Strategy*: Bayesian-updated OU anchors on `HYDROGEL_PACK` (`mu ~ 9,991`) and `VELVETFRUIT_EXTRACT` (`mu ~ 5,250`) combined with Black-Scholes total-volatility inversion across `VEV_4000..5500` (`spot_scale = 30.0`, `enter_band = 10.0`) earns **`+95,093.00`** OOS on Day 2 (vs. `-7,160.00` `SymmetricSpotMM`).
- **Round 4 (`VELVETFRUIT_EXTRACT` Counterparty Decomposition, `±200/±300`)**:
  - *Negative result*: Strictly In-Sample Days 1–2 decomposition ([`r4_counterparty_velvet_midmoves.csv`](tables/r4_counterparty_velvet_midmoves.csv)) proved that `Mark 67`'s large fill mark-out reflects a `-1.765` pre-trade dip (`t-1 -> t`) plus a mechanical `+1.924` 1-tick bounce (`t -> t+1`), with `0.113` causal drift thereafter (`OU-adj t = 1.56`).
  - *True causal signal*: `Mark 14 SELL` (`ou_adj_h200 = +3.788`, `t = +4.58`) and `Mark 55 BUY` (`ou_adj_h200 = +2.460`, `t = +4.07`) predict genuine post-trade appreciation using **prior-tick** (`t - 100`) market trades. At plateau `flow_weight = 1.5`, OOS Day 3 PnL reaches **`+260,540.00`**, adding **`+11,153.50`** OOS and trimming MaxDD (`73,758 -> 71,177`) vs. `Round3NoFlow`.
- **Round 5 (`50` Symbols Across `10` Categories, `±10`)**:
  - *Negative results*: `Pebbles` constant-sum deviations (`std = 2.82`) sit inside the `12–14` tick spread (zero crossing profit), `Snackpacks` correlations are contemporaneous across shifting day anchors, `Robots` carry zero 1-tick lag, and hard `VOL_GUARD` halts choke profitable quoting.
  - *Strategy*: Volatility-scaled Avellaneda-Stoikov MM (`vol_skew_mult = 0.18, edge_frac = 0.14`) captures `226,217.5` IS (`IR_tick = 0.03398`); layering the discrete `MICROCHIP_CIRCLE` 50/100/150/200-tick causal lead-lag overlay (`mc_beta = 0.16`, concave interior IS IR peak at `0.03531`) increases IS profit to `237,928.5` (`MaxDD = 23,671.0`) and earns **`+97,628.00`** on Day 4 OOS (`+2,215.50` over `Round5NoLeadLag`, lower `MaxDD = 14,961.50`, and `1.66x` higher `PnL/MaxDD` than `EmaSymmetricMM_All50`).

![Round 4 Counterparty Causal Decomposition](figures/r4_counterparty_markouts.png)

## 3. Monte Carlo Risk Analysis: Calibrated vs. Adverse-Selection Stress (`N=40 x 1,000`)

From [`r1_mc_risk_summary.csv`](tables/r1_mc_risk_summary.csv) and [`r2_to_r5_mc_risk_summary.csv`](tables/r2_to_r5_mc_risk_summary.csv):

| Round | Scenario | Mean PnL | `VaR 95%` | `CVaR 95%` | `ProbLoss` (`Wilson 95% Up`) | `Mean IR_tick` | Worst DD |
| :---: | :--- | ---: | ---: | ---: | :---: | ---: | ---: |
| **R1** | `Round1Submission_QA` / `Conservative` | `6,675.06` | `3,431.15` | `2,845.75` | `0.000` (`<= 0.088`) | `0.0571` | `3,870.50` |
| **R1** | `Round1Submission_AdverseStress (p=0.30)` | `3,783.54` | `-253.65` | `-2,503.00` | `0.075` (`<= 0.199`) | `0.0224` | `6,179.50` |
| **R2** | `Round2Submission_BaselineFlow` / `MAF+25%` | `10,966.54` / `12,631.66` | `6,556.43` / `6,491.52` | `4,548.00` / `5,525.75` | `0.000` (`<= 0.088`) | `0.0764` / `0.0893` | `3,668.50` |
| **R2** | `Round2Submission_AdverseStress (p=0.30)` | `5,572.65` | `-789.07` | `-2,163.50` | `0.100` (`<= 0.231`) | `0.0299` | `9,857.00` |
| **R3** | `CalibratedQA` / `AdverseStress` | `29,852.01` / `13,225.06` | `2,010.05` / `-53,416.30` | `-127.75` / `-91,007.50` | `0.025` (`<=0.129`) / `0.300` | `0.0259` / `0.0088` | `53,851.50` |
| **R4** | `CalibratedQA` / `AdverseStress` | `27,562.95` / `12,042.42` | `-17,878.60` / `-59,763.20` | `-24,536.25` / `-66,346.50` | `0.125` (`<=0.261`) / `0.275` | `0.0244` / `0.0082` | `75,356.00` |
| **R5** | `11AssetRepPulseMC` / `AdverseStress` | `15,279.26` / `12,994.25` | `9,767.02` / `8,720.42` | `8,334.00` / `8,013.75` | `0.000` (`<= 0.088`) | `0.1410` / `0.1200` | `3,946.00` |

## 4. Ex-Ante Offline Manual Challenge Models (Rounds 1–5)

Full derivations live in [`MANUAL_CHALLENGES.md`](../docs/manual/MANUAL_CHALLENGES.md) ([`manual_challenges.py`](../src/prosperity_toolkit/analysis/manual_challenges.py)):

- **R1 (*An Intarian Welcome*)**: Stochastic-clearing optimal bids `DRYLAND_FLAX = (30, 65)` (`68.12` EV) and `EMBER_MUSHROOM = (20, 10)` (`9.81` EV).
- **R2 (*Invest & Expand*)**: Poisson Cognitive Hierarchy (`tau = 1.5`) converging to Level-3 focal allocation `Research = 15% (14.71%)`, `Scale = 43% (43.29%)`, `Speed = 42% (42.0%)` (`225,094.01` Net EV).
- **R3 (*Celestial Gardeners' Guild*)**: Bayesian screening `(b1 = 775, b2 = 880)` over uncertain crowd mean `N(875, 15^2)` (`76.00/unit` EV).
- **R4 (*Aether Crystal Exotics*)**: Exact Black-Scholes & Rubinstein chooser values (`AC_50_C15 = AC_50_P15 = 12.0269`, `AC_40_BP = 4.7679`, `AC_50_CO = 21.8977`) plus 100k-path discrete `4/d` GBM (`AC_45_KO = 0.2113` vs. `0.175` ask; `24/d = 0.1562`). Day-15 min-variance hedged portfolio (`AC_50_CO: -50, AC_40_BP: -50, AC_45_KO: +183, AC_50_C15: +53, AC_50_P15: +74` at `risk_aversion=0.00015`) achieves `40.96` EV (`-70.1%` std reduction vs. unhedged, Sharpe `0.104` vs. `0.044`).
- **R5 (*Extra! Extra!*)**: Exact KKT quadratic-fee optimization under finite `-92%` downside (`Ashes of the Phoenix` floored above `-1.0`) yields `857,400.00` KKT net EV (`855,944.53` with `kappa = 3.0`) across `5/9` active bets (`vs. 524,444` naive `1/9`).

## 5. Limitations & Verification Commands

1. **Sample Length**: Each round provides only 2 IS days and 1 held-out OOS day; block-bootstrap CIs in R3 span zero (`[-184k, +356k]`) due to wide unhedged spot variance.
2. **Round 5 11-Asset MC**: `Round5JointMonteCarloEngine` simulates an 11-asset representative pulse model (not full 50-symbol simultaneous paths).
3. **Reproducibility**: All scripts and artifacts verify via `audit_all_datasets.py --verify-only`, `eda_rounds2_to_5.py`, `generate_report.py`, `evaluate_rounds2_to_5.py`, `evaluate_manual_challenges.py`, `build_dashboard.py`, and `build_pdf_writeup.py`.
