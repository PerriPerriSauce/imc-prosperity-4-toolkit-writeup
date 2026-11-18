# IMC Prosperity 4 — Quantitative Research, Strategy Engineering & Final Writeup

> **Interactive Tearsheet**: Open [`reports/dashboard.html`](file:///c:/Users/pierr/Desktop/imc-prosperity-4-toolkit-writeup/reports/dashboard.html) in any browser for interactive KPI summaries, full ablation matrices, CSCV/MC risk metrics, and embedded diagnostic figures.

## Executive Summary

Across five competition rounds of **IMC Prosperity 4**, we built a modular Python 3.11 research library ([`src/prosperity_toolkit/`](file:///c:/Users/pierr/Desktop/imc-prosperity-4-toolkit-writeup/src/prosperity_toolkit/)) and five dependency-free competition submissions (`traders/round{1..5}/submission.py`), uniting **market microstructure diagnosis**, **queue-aware event replay**, **combinatorial overfitting controls (`CSCV PBO`, `DSR`, neighborhood stability, circular block bootstrap)**, **vectorized Monte Carlo tail-risk testing**, and **game-theoretic / exotic manual-challenge solvers**.

Evaluating every production submission single-pass on its chronological held-out **Out-of-Sample (`OOS`)** session under conservative queue modeling (`FillMode.QUEUE_AWARE`) delivers **`+192,059.50` XIRECs** cumulative simulated OOS PnL across Rounds 1–5 while maintaining **`PBO <= 0.1000`** (`< 0.15`), **`DSR >= 0.9921`** (`>= 0.95`), **`0.00%` loss probability** across calibrated Monte Carlo stress sessions, and **`<= 0.6920 ms/tick` execution latency** across `50` simultaneous Round 5 securities. All metrics cleanly separate immutable raw exchange books, simulated queue-aware replays, synthetic stress tests, and explicit manual-challenge crowd beliefs.

## 1. End-to-End Methodology & Validation Discipline

To prevent post-hoc data leakage and cherry-picked parameters across narrow 3-day historical sessions:

1. **Strict Chronological Split**: Each round freezes its final chronological day exclusively for single-pass evaluation (`Day 0` R1, `Day 1` R2, `Day 2` R3, `Day 3` R4, `Day 4` R5). All microstructural discovery, mark-out studies, cointegration checks, and grid sweeps operate strictly In-Sample (`IS`).
2. **Queue-Aware Execution Simulation**: Rather than trusting optimistic fills whenever prints merely touch a quote (`touch`), [`ExecutionSimulator`](file:///c:/Users/pierr/Desktop/imc-prosperity-4-toolkit-writeup/src/prosperity_toolkit/execution/simulator.py) models resting bot queue priority (`queue_aware`) alongside worst-case `conservative` and upper-bound `touch` bands and enforces Prosperity's symbol-wide starting-inventory batch cancellation rule.
3. **Anti-Overfitting Gating Stack** ([`statistical_validation.md`](file:///c:/Users/pierr/Desktop/imc-prosperity-4-toolkit-writeup/docs/methodology/statistical_validation.md)):
   - `3x3` neighborhood plateau selection ($\mu_{\mathcal{N}} - \lambda\sigma_{\mathcal{N}}$) over brittle isolated peaks.
   - Combinatorially Symmetric Cross-Validation (`CSCV`, $S=8$, `70` splits) requiring `PBO < 0.15`.
   - Bailey–López de Prado **Deflated Sharpe Ratio** adjusted for effective trial count $N_{\text{eff}}$, skewness, and excess kurtosis (`DSR >= 0.95`).
   - Circular block bootstrap (`block_size = 100`, $B = 1{,}000$) 95% confidence bounds and calibrated Monte Carlo stress suites (`VaR95`, `CVaR95`, `ProbLoss`).

## 2. Algorithmic Trading Results & Quantitative Insights (Rounds 1–5)

### 2.1 Consolidated Out-of-Sample & Overfitting Gate Scorecard (`queue_aware`)

| Round | Submission Module | Held-Out OOS Day | OOS PnL | OOS `Sharpe_252` (`95% Boot CI`) | OOS Max DD | `CSCV PBO` | `DSR` | Mean Latency / Tick |
| :---: | :--- | :---: | ---: | :--- | ---: | :---: | :---: | ---: |
| **Round 1** | [`traders/round1/submission.py`](file:///c:/Users/pierr/Desktop/imc-prosperity-4-toolkit-writeup/traders/round1/submission.py) | `Day 0` | **`+22,157.00`** | `1.1894` `[1.046, 1.329]` | `267.00` | `0.0860` | `1.0000` | `0.0340 ms` |
| **Round 2** | [`traders/round2/submission.py`](file:///c:/Users/pierr/Desktop/imc-prosperity-4-toolkit-writeup/traders/round2/submission.py) | `Day 1` | **`+27,463.00`** | `1.3972` `[1.2314, 1.5823]` | `419.50` | `0.0000` | `1.0000` | `0.0406 ms` |
| **Round 3** | [`traders/round3/submission.py`](file:///c:/Users/pierr/Desktop/imc-prosperity-4-toolkit-writeup/traders/round3/submission.py) | `Day 2` | **`+7,525.50`** | `0.2276` `[0.0097, 0.4392]` | `1,936.00` | `0.0000` | `0.9921` | `0.1872 ms` |
| **Round 4** | [`traders/round4/submission.py`](file:///c:/Users/pierr/Desktop/imc-prosperity-4-toolkit-writeup/traders/round4/submission.py) | `Day 3` | **`+11,741.00`** | `0.3613` `[0.0932, 0.6302]` | `2,901.00` | `0.0571` | `0.9975` | `0.1871 ms` |
| **Round 5** | [`traders/round5/submission.py`](file:///c:/Users/pierr/Desktop/imc-prosperity-4-toolkit-writeup/traders/round5/submission.py) | `Day 4` | **`+123,173.00`** | `0.8109` `[0.5789, 1.0627]` | `6,205.50` | `0.1000` | `1.0000` | `0.6920 ms` |
| **Total** | — | — | **`+192,059.50`** | — | — | `<= 0.100` | `>= 0.992` | `<= 0.6920 ms` |

![Normalized OOS Equity Trajectories Across Rounds 2 through 5](file:///c:/Users/pierr/Desktop/imc-prosperity-4-toolkit-writeup/reports/figures/r2_to_r5_oos_equity_summary.png)

### 2.2 Core Round-by-Round Economic Discoveries

- **Rounds 1 & 2 (`ASH_COATED_OSMIUM`, `INTARIAN_PEPPER_ROOT`, $Q_{\max}: 20 \to 80$)**: Anchoring valuation on max-volume resting bot walls (`_popular_wall_mid`) reduced high-frequency step-difference noise standard deviation by `30.9%–40.0%` IS ([`EXP-R1-002`](file:///c:/Users/pierr/Desktop/imc-prosperity-4-toolkit-writeup/reports/experiments/EXP-R1-002_per_asset_attribution_and_bootstrap.md)). In Round 2 (`±80` limit), unskewed `SymmetricMM_80` bled `-20,294.50` OOS by passively riding `+0.108`/tick `INTARIAN_PEPPER_ROOT` drift, whereas combining affine trend tracking with linear inventory skew (`min_edge = 3.5, skew = 0.75`) generated `+27,463.00` (`419.50` MaxDD). Calibrated Monte Carlo confirms a `+25%` Market Access Fee arrival-rate uplift expands 1,000-step EV by `+33.4%` (`5,065.52 -> 6,755.98`).
- **Round 3 (`HYDROGEL_PACK`, `VELVETFRUIT_EXTRACT`, `VEV_4000..6500`, $Q_{\max}: 200/300$)**: Hardcoding a `5`-day calendar expiry in Black-Scholes mispriced `VEV_5000..5500` (market-implied schedule $\approx 8$ days) and lost `-7,604.00` OOS (`OptionsVolatilityContract`). Solving for **calendar-invariant total implied volatility** $v_K = \sigma_K \sqrt{\tau}$, capturing deep-ITM parity (`VEV_4000 +2,553.00`), quoting `15.7`-tick `HYDROGEL_PACK` spreads (`+4,730.00`), and delta-hedging inside `HEDGE_BAND = 10` produced `+7,525.50` OOS (`MaxDD 1,936.00`).
- **Round 4 (`Mark 67` Flow Gating & Overfit Veto)**: Event-study mark-outs strictly inside `VELVETFRUIT_EXTRACT` isolated `Mark 67` (`100%` buyer, `+1.970`-tick permanent price jump across `h = +1..50`) against absorbed seller `Mark 49`. An aggressive spot-chasing candidate (`s_alpha = 0.85`) failed CSCV (`PBO = 0.9714`) and DSR (`0.9390 < 0.95`) in-sample and was rejected; aligning [`traders/round4/submission.py`](file:///c:/Users/pierr/Desktop/imc-prosperity-4-toolkit-writeup/traders/round4/submission.py) directly to its IS plateau (`M67_BUMP = 0.5, MM_EDGE = 5.5`) flipped `VELVETFRUIT_EXTRACT` OOS from `-328.50` (R3) to **`+1,027.00`**, cut MaxDD **`-10.8%`** (`3,250.50 -> 2,901.00`), and beat `Round3Ungated` on annualized `Sharpe_252` across all three fill regimes (`0.3613` vs `0.3488` `queue_aware`; `+13,259.50` vs `+12,284.50` `touch`).
- **Round 5 (`50` Spot Goods Across `10` Categories, Uniform `±10` Caps)**: Auditing IS covariance and arrival timestamps uncovered (1) **zero noise trades**—all prints cluster inside **three synchronized Poisson pulse blocks** (`Group V` `40` assets, `Pebbles` `5`, `Microchips` `5`) with `100%` uniform side/qty per event; (2) exact constant sum $\sum_{i=1}^5 \text{Pebbles}_i = 50{,}000 \pm 2.82$ (`ADF t = -70.16`, `half-life = 0.16` ticks OOS); and (3) a shifting `SNACKPACK_CHOCOLATE + VANILLA` daily anchor $K_{\text{day}}$ (`-98.2` ticks across Days 2–3). Using instantaneous `_popular_wall_mid` (`edge_frac = 0.18, skew = 1.25`), full `QUOTE_CLIP = 10` sizing, dynamic step-volatility gating (`spread >= 0.50 * vol_ema`, `LOW_RATIO_EDGE_FRAC = 0.35`) on `Robots`/`Microchips`, decoupled **atomic `PEBBLES` IOC crossing**, and slow online $K_{\text{day}}$ tracking (`alpha = 0.005`) cut OOS MaxDD by **`-78.7%`** vs lagged `EmaSymmetricMM_All50` (`29,130.00 -> 6,205.50`), kept **all `10` categories net profitable** (`+123,173.00` total, `88.3%` of single-day public-tape ceiling `139,448.5`), and lifted `Sharpe_252` **`2.49x`** (`0.3260 -> 0.8109`).

![Round 5 IS Sensitivity Plateau and Category OOS Attribution](file:///c:/Users/pierr/Desktop/imc-prosperity-4-toolkit-writeup/reports/figures/r5_sensitivity_and_category_oos.png)

## 3. Monte Carlo Tail-Risk Benchmarks

Calibrated synthetic Monte Carlo ensembles verify robustness off historical paths ([`r1_mc_risk_summary.csv`](file:///c:/Users/pierr/Desktop/imc-prosperity-4-toolkit-writeup/reports/tables/r1_mc_risk_summary.csv), [`r2_to_r5_mc_risk_summary.csv`](file:///c:/Users/pierr/Desktop/imc-prosperity-4-toolkit-writeup/reports/tables/r2_to_r5_mc_risk_summary.csv)):

| Round | Scenario / Strategy | Mean MC PnL | `VaR 95%` | `CVaR 95%` | Prob. of Loss | Mean `Sharpe_252` | Worst Max DD |
| :---: | :--- | ---: | ---: | ---: | :---: | ---: | ---: |
| **R1** | `SymmetricMM` *(baseline, N=30, 500t)* | `359.52` | `-451.87` | `-774.25` | `20.0%` | `0.5393` | `1,081.50` |
| **R1** | `Round1Submission` *(N=30, 500t)* | **`900.48`** | `446.18` | `344.25` | **`0.0%`** | `1.7084` | `572.00` |
| **R2** | `Round2Submission` (`BaselineFlow` / `+25% MAF`) | `5,065.52` / `6,755.98` | `3,578.20` / `5,578.00` | `3,463.25` / `5,487.25` | **`0.0%`** | `2.8362` / `3.6416` | `679.00` / `721.00` |
| **R3** | `Round3Submission` *(coupled options+spot, 1000t)* | `2,448.56` | `1,137.00` | `1,121.25` | **`0.0%`** | `0.5189` | `1,641.00` |
| **R4** | `Round4Submission` *(flow + options, 1000t)* | `2,345.10` | `1,692.40` | `1,116.75` | **`0.0%`** | `0.4966` | `1,905.50` |
| **R5** | `Round5Submission_JointMC` *(50-asset joint, 1000t)* | **`14,876.42`** | `6,495.55` | `2,649.00` | **`0.0%`** | `1.6066` | `5,497.50` |

## 4. Manual Challenges Summary (Rounds 1–5)

Full derivations, Poisson Cognitive Hierarchy tables, and sensitivity sweeps live in [`MANUAL_CHALLENGES.md`](file:///c:/Users/pierr/Desktop/imc-prosperity-4-toolkit-writeup/docs/manual/MANUAL_CHALLENGES.md) (`manual_challenges.py` + `evaluate_manual_challenges.py`):

- **R1 (*An Intarian Welcome*)**: Uniform clearing with late-entrant priority rewards shading bids just above resting demand (`p = 29, qty = 66 -> 132.00` static on Flax vs `0.00` queued out at `p = 28`), and under uncertain stochastic clearing shifts optimal policy to `px = 30, qty = 65` (`68.12` EV at `96%` fill rate on Flax; `px = 20, qty = 10 -> 9.81` on Mushroom). **Final Portal Inputs**: `DRYLAND_FLAX = (30, 65)`, `EMBER_MUSHROOM = (20, 10)`.
- **R2 (*Invest & Expand*)**: Interior allocation obeys $(100 - p - r^*)/(1+r^*) = \ln(1+r^*)$, while tournament Speed is governed by iterative best-response crowding. Ex-ante Poisson Cognitive Hierarchy (`tau = 1.5`) escalates Speed monotonically (`L1: 29.5% -> 305.2k`, `L2: 37.5% -> 277.8k`, `L3: 42.0% -> 246.0k`), peaking at the Level-3 focal equilibrium (`Speed = 42.0%`, `Research = 14.71%`, `Scale = 43.29%`) with `225,094.01` net EV under the bounded-rationality stress mixture (whose own unconstrained best response sits at `44.0% -> 226.9k`). **Final Portal Inputs**: `Speed = 42%`, `Research = 15%` (`14.71%`), `Scale = 43%` (`43.29%`).
- **R3 (*Celestial Gardeners' Guild*)**: Bayesian updating on uncertain cohort mean second bid ($\bar{b}_2 \sim \mathcal{N}(875, 15^2)$) gives optimal two-bid split `(775, 880)` (`76.00`/unit EV, `76.8%` acceptance vs `63.73` single bid), with a conservative cohort point sensitivity at $\bar{b}_2 = 860$ documented in [`MANUAL_CHALLENGES.md`](file:///c:/Users/pierr/Desktop/imc-prosperity-4-toolkit-writeup/docs/manual/MANUAL_CHALLENGES.md). **Final Portal Inputs**: `Bid 1 = 775`, `Bid 2 = 880`.
- **R4 (*Vanilla Just Isn't Exotic Enough*)**: Under exact specification ($\sigma_{\text{ann}} = 251\%$, `15d` maturity, `6h` discrete resets, `AC_40_BP` paying `10`), Broadie–Glasserman–Kou discrete monitoring shifts the `35` barrier down smoothly, making `AC_45_KO` cheap (`fair = 0.2108` vs `ask = 0.175`, `BUY +0.0358`, `61.78%` KO vs `63.85%` at `24/day`), while `AC_50_CO` (`fair = 21.8134` vs `22.200`) and `AC_40_BP` (`fair = 4.7610` vs `5.000`) price rich (`SELL`). Sizing a minimum-variance 5-contract exotic hedge cuts portfolio std by **`-90.3%`** (`std = 297.48`, `CVaR95 = -575.5`, Sharpe `0.0797` vs `0.0221` unhedged). **Final Portal Inputs**: `AC_50_CO = -15`, `AC_40_BP = -50`, `AC_45_KO = +198`, `AC_50_C15 = +5`, `AC_50_P15 = +21`.
- **R5 (*Extra! Extra!*)**: Exact KKT quadratic-fee optimization across all `9` authentic *Ashflow Alpha* Ignith goods zeroes out weak edges cleanly (`lambda* = 0.6060, gross = 100.0%, fees = 289,380, net = 895,380.00` across `5/9` active bets: `Thermalite Core +37.2%, Sulfur Reactor +28.7%, Ashes of the Phoenix -24.7%, Pyroflex Cells -8.7%, Scoria Paste +0.7%` vs `544,444` naive `1/9`), while variance penalty $\kappa = 3.0$ moderates fee burn slightly to `lambda* = 0.5271, net = 893,543.96`. **Final Portal Inputs**: `Thermalite Core +35%`, `Sulfur Reactor +29%`, `Ashes of the Phoenix -23%`, `Pyroflex Cells -10%`, `Scoria Paste +3%`, remaining `4` goods `0%`.

![Round 1-5 Manual Challenges Comparative Statics](file:///c:/Users/pierr/Desktop/imc-prosperity-4-toolkit-writeup/reports/figures/manual_challenges_analysis.png)

## 5. Limitations, Engineering Failure Modes & Portfolio Takeaways

Three concrete structural lessons govern the final codebase ([`limitations.md`](file:///c:/Users/pierr/Desktop/imc-prosperity-4-toolkit-writeup/docs/limitations.md), [`postmortem.md`](file:///c:/Users/pierr/Desktop/imc-prosperity-4-toolkit-writeup/docs/postmortem.md)):
1. **Execution Horizon Must Match Mean-Reversion Speed**: Sub-tick `PEBBLES` invariants (`0.16`-tick half-life) require **atomic IOC leg crossing** decoupled from unbiased passive MM quoting (`+15,469.00` OOS on `Pebbles`) rather than lagged resting skew adjustments.
2. **Scale-Free Calibration & Overfit Vetoes Prevail**: Total implied volatility ($v_K = \sigma_K\sqrt{\tau}$), online slow-tracked anchors (`K_day`), and adaptive step-vol guards transfer across unseen days cleanly, while strict `CSCV < 0.15` / `DSR >= 0.95` vetoes block brittle high-PBO tweaks before OOS testing.
3. **Simulation Boundaries vs. Exchange Scale**: Historical replay figures represent single-day `queue_aware` backtests (`+123,173.00` OOS = `88.3%` of historical single-day public-tape capture) rather than multi-day exchange totals aggregating interactive participant order flow.

## 6. Verification Ledger & Compiled Monograph
All metrics above are reproducible via [`evaluate_r1.py`](file:///c:/Users/pierr/Desktop/imc-prosperity-4-toolkit-writeup/scripts/evaluate_r1.py), [`evaluate_rounds2_to_5.py`](file:///c:/Users/pierr/Desktop/imc-prosperity-4-toolkit-writeup/scripts/evaluate_rounds2_to_5.py), [`evaluate_manual_challenges.py`](file:///c:/Users/pierr/Desktop/imc-prosperity-4-toolkit-writeup/scripts/evaluate_manual_challenges.py), [`build_dashboard.py`](file:///c:/Users/pierr/Desktop/imc-prosperity-4-toolkit-writeup/scripts/build_dashboard.py), [`build_pdf_writeup.py`](file:///c:/Users/pierr/Desktop/imc-prosperity-4-toolkit-writeup/scripts/build_pdf_writeup.py), and [`audit_all_datasets.py`](file:///c:/Users/pierr/Desktop/imc-prosperity-4-toolkit-writeup/scripts/audit_all_datasets.py). Also available as a standalone compiled PDF monograph: [`IMC_Prosperity4_Research_Writeup.pdf`](file:///c:/Users/pierr/Desktop/imc-prosperity-4-toolkit-writeup/reports/IMC_Prosperity4_Research_Writeup.pdf).
