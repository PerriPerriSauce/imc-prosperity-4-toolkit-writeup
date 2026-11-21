# IMC Prosperity 4 — Team `63-bit integers` Portfolio & Research Writeup

Our team, `63-bit integers` came `60th Worldwide`, `8th in Australia`, and `13th in APAC` with an official PnL of `+700,334` XIRECs

This repository chronicles **Team `63-bit integers`' live participation in IMC Prosperity 4** alongside the **reproducible post-contest Python 3.11 research toolkit** built afterward to audit live hypotheses, eliminate overfitting and look-ahead pitfalls, enforce causal `t - 100` queue-aware execution, and systematically redesign our Round 5 strategy.

![Diddy Blud](images\Prosperity_4_Winscreen_60th.jpg)

Every algorithmic submission in [`traders/`](traders/round5/README.md) runs cleanly behind an AST-enforced runtime boundary (`datamodel` + Python stdlib only) and reproduces single-pass chronological out-of-sample replays via `load_competition_trader` and [`ExecutionSimulator`](src/prosperity_toolkit/execution/simulator.py).

---

## 1. Official Live Competition Results

| Round | Phase | Live Algo PnL | Live Manual PnL | Official Round Total | Post-Contest 1-Day Sim OOS (`QA`) | Contest-to-Post-Contest Audit Notes |
| :---: | :---: | ---: | ---: | ---: | ---: | :--- |
| **R1** | Phase 1 | **`+116,927`** | `+87,995` | **`+204,922`** | `+91,098.00` | Fixed `10k` Osmium MM + Pepper `+0.10/tick` carry; R1 Uniform Clearing manual |
| **R2** | Phase 1 | **`+115,543`** | `+200,716` | **`+316,259`** | `+94,209.00` | Multi-day carry & MAF arrival boost reconcile `+115.5k` live vs. `+94.2k` 1-day OOS |
| **P1** | **Phase 1** | **`+232,470`** | **`+288,711`** | **`+521,181`** | **`+185,307.00`** | Qualified smoothly into Ranked Phase 2 |
| **R3** | Phase 2 | **`+213,104`** | `+78,225` | **`+291,329`** | `+95,093.00` | Leaderboard reset; OU spots + unhedged `VEV_4000..5500` calls & Bayesian screening manual |
| **R4** | Phase 2 | **`+220,783`** | `+36,969` | **`+257,752`** | `+260,540.00` | Causal prior-tick counterparty flow (`Mark 14` SELL / `Mark 55` BUY) + `Aether Crystal` hedge |
| **R5** | Phase 2 | **`+31,087`** | `+120,165` | **`+151,252`** | `+97,628.00` | Live 50-asset sprint slowed by uncalibrated guesses; redesigned post-contest to `+97.6k` (`1.66x` PnL/DD) |
| **P2** | **Phase 2** | **`+464,974`** | **`+235,359`** | **`+700,334`**\* | **`+453,261.00`** | Ranked Finals total |
| **All** | **R1–R5** | **`+697,444`** | **`+524,070`** | **`+1,221,515`**\* | **`+638,568.00`** | Canonical ledger archived in [`competition_results.csv`](reports/tables/competition_results.csv) |


![Team 63-bit integers Official Competition PnL vs. Post-Contest 1-Day OOS Audit](reports/figures/competition_vs_postcontest.png)
---

## 2. Post-Contest Quantitative Audit & Held-Out Simulated OOS (`queue_aware`)

*Whereas Section 1 reports **actual live contest results** achieved by Team `63-bit integers`, all tables below report **post-contest single-day chronological replays** on archived historical CSVs under strict [`FillMode.QUEUE_AWARE`](src/prosperity_toolkit/execution/simulator.py), causal `t - 100` `own_trades`/`market_trades` lag, and verified official position limits.*

| Round | Refined Strategy Architecture & Limits | OOS Day | Post-Contest OOS (`QA`) | `IR_tick` (`95% Boot CI`) | `BlkSR_1k` | `MaxDD` (`PnL/DD`) | `PBO` ($N_{\text{eff}}$) | `DSR_block` | Latency | Card |
| :---: | :--- | :---: | ---: | :--- | :---: | ---: | :---: | :---: | :---: | :--- |
| **R1** | `10k` OU Osmium MM + max-wall Pepper carry (`±80`) | `Day 0` | **`+91,098.00`** | `0.05445` `[0.0505, 0.0587]` | `9.327` | `1,405.00` (`64.84`) | `0.129` (`1.02`) | `1.0000` | `0.0204 ms` | [`round1`](traders/round1/README.md) |
| **R2** | Refined `±80` skew/edge plateau + MAF elasticity (`±80`) | `Day 1` | **`+94,209.00`** | `0.05466` `[0.0509, 0.0584]` | `8.237` | `1,401.00` (`67.24`) | `0.300*` (`1.04`) | `1.0000` | `0.0281 ms` | [`round2`](traders/round2/README.md) |
| **R3** | Bayesian OU + BS total-vol `VEV_4000..5500`, zero hedge (`±200/300`) | `Day 2` | **`+95,093.00`** | `0.00584` `[-0.0112, 0.0213]` | `0.573` | `75,774.00` (`1.26`) | `0.000` (`1.01`) | `0.9966` | `0.3249 ms` | [`round3`](traders/round3/README.md) |
| **R4** | R3 core + causal `t-100` `Mark 14`/`Mark 55` flow (`±200/300`) | `Day 3` | **`+260,540.00`** | `0.01680` `[0.0010, 0.0335]` | `0.646` | `71,177.00` (`3.66`) | `0.014` (`1.02`) | `0.9783` | `0.2925 ms` | [`round4`](traders/round4/README.md) |
| **R5** | Vol-scaled AS + `MICROCHIP_CIRCLE` 50–200t lag (`±10 x 50`) | `Day 4` | **`+97,628.00`** | `0.02624` `[0.0105, 0.0412]` | `1.108` | `14,961.50` (`6.53`) | `0.543*` (`1.14`) | `1.0000` | `0.5518 ms` | [`round5`](traders/round5/README.md) |
| **All** | **Cumulative 5-Day Post-Contest Simulated OOS Total** | **5 Days** | **`+638,568.00`** | — | — | — | — | **`>= 0.978`** | **`<= 0.552 ms`** | [`FINAL_WRITEUP.md`](reports/FINAL_WRITEUP.md) |

*\*Note on CSCV PBO in Rounds 2 & 5*: On flat, tightly correlated interior plateaus (`R2 local_std = 0.000107`, `N_eff = 1.04`; `R5 local_std = 0.000551`, `N_eff = 1.14`), near-identical grid neighbors tie-swap ranks across 8-slice CSCV partitions even while `DSR_block = 1.0000` and OOS stays profitable (`+94,209.00` / `+97,628.00`).

![Normalized Out-of-Sample Equity Curves Across Rounds 2 through 5](reports/figures/r2_to_r5_oos_equity_summary.png)

---

## 3. Microstructure Discoveries, Pruned Hypotheses & Live Postmortems

1. **Bot-Wall Fair Value & Trend Carry (`R1–R2`, `±80` -> `+116,927` & `+115,543` Live Algo)**:
   - Raw L1 midpoints fluctuate `~31%–40%` more step-to-step due to thin inside-spread quotes on `~92.4%` two-sided books (`13–22` empty ticks/day). Anchoring `ASH_COATED_OSMIUM` around `10,000` and riding `INTARIAN_PEPPER_ROOT`'s deterministic `+0.10000/tick` trend (`R^2 = 1.0000`) avoided symmetric inventory blowout (`SymmetricMM_80: -20,294.50` OOS R2) and generated **`+91,098.00`** (`R1`) and **`+94,209.00`** (`R2`) on single-day OOS replays. Calibrated MAF sweeps show `+25%` arrival flow boosts 1,000-step MC EV `+15.18%` (`10,966.54 -> 12,631.66`), reconciling live multi-day Round 2 outperformance (`+115,543`).
2. **Horizon-Free Volatility Surface & Pruning Spot Delta Hedging (`R3`, `±200/300` -> `+213,104` Live Algo)**:
   - Fixed calendar-TTE Black-Scholes lost `-1,051.00` OOS (`OptionsVolatilityContract`). Solving for rolling EWMA total implied volatility $v_K = \sigma_K \sqrt{\tau}$ across `VEV_4000..5500` while dropping worthless `0/1` strikes (`6000/6500`) and **removing destructive `VELVETFRUIT_EXTRACT` delta hedging** delivered **`+95,093.00`** OOS on Day 2 (with honestly wide bootstrap CI `[-184,416.62, +355,675.89]` from unhedged inventory swings).
3. **Causal Counterparty Flow vs. 1-Tick Bounce Illusion (`R4`, `±200/300` -> `+220,783` Live Algo)**:
   - *Falsified Hypothesis (`Mark 67`)*: Strictly In-Sample `Days 1–2` decomposition on `VELVETFRUIT_EXTRACT` ([`r4_counterparty_velvet_midmoves.csv`](reports/tables/r4_counterparty_velvet_midmoves.csv)) proved `Mark 67` BUY is a `-1.765` pre-dip + `+1.924` unobservable 1-tick bounce followed by insignificant causal drift (`t+1 -> t+200 = +0.113`, `OU-adj t = 1.56`).
   - *Verified Causal Signal (`Mark 14` & `Mark 55`)*: `Mark 14` SELL (`ou_adj_h200 = +3.788, t = +4.58`) and `Mark 55` BUY (`ou_adj_h200 = +2.460, t = +4.07`) show genuine post-execution appreciation. Filtering strictly causal `t - 100` prior-tick `state.market_trades` (`flow_weight = 1.5`) lifts OOS PnL **`+11,153.50`** (`+260,540.00` vs `+249,386.50` for `Round3NoFlow`) and lowers MaxDD **`-2,581.00`**.
4. **Diagnosing the Live Round 5 Sprint (`+31,087` Live -> `+97,628.00` Post-Contest OOS, `50 x ±10`)**:
   - *What Happened Live (`+31,087`)*: Under time pressure across 50 brand-new assets with tight `±10` caps and zero counterparty IDs, chasing unverified basket spreads (`Pebbles`, `Snackpacks`) and lagging volatility spikes suppressed live Algo PnL to `+31,087`.
   - *Post-Contest Diagnosis & Redesign (`+97,628.00`)*: Rigorous IS testing proved `Pebbles` constant-sum (`50,000 ± 2.82`, `ADF t = -70.16`) lies inside `12–14`-tick touch spreads (zero crossing profit), `Snackpacks` shift `-98.2` ticks across days with rotating triplet weights, and hard `VOL_GUARD` halts forfeit re-anchoring spread. Pruning those traps and pairing zero-lag volatility-scaled AS quoting (`vol_skew_mult = 0.18, edge_frac = 0.14`) with discrete `MICROCHIP_CIRCLE` 50/100/150/200-tick lag adjustments (`mc_beta = 0.16`) lifts OOS PnL **`+2,215.50`** over `Round5NoLeadLag`, achieves **`1.66x`** higher `PnL/MaxDD` (`6.53` vs `3.94`) than `EmaSymmetricMM_All50`, and runs in `0.5518 ms/tick`.

![Round 4 Counterparty Causal Mark-Out Decomposition](reports/figures/r4_counterparty_markouts.png)

![Round 5 IS Plateau and OOS Category Attribution](reports/figures/r5_sensitivity_and_category_oos.png)

---

## 4. Manual Challenges: Ex-Ante Models vs. Live Realized Payouts (`+524,070` Total)

All five manual challenges contributed heavily to Team `63-bit integers`' final placement (**`+524,070` XIRECs** total across R1–R5), led by `+200,716` in Round 2 (*Invest & Expand*) and `+120,165` in Round 5 (*Extra! Extra!*). See [`MANUAL_CHALLENGES.md`](docs/manual/MANUAL_CHALLENGES.md) and [`manual_challenges_summary.csv`](reports/tables/manual_challenges_summary.csv).

| Round | Challenge | Ex-Ante Policy & Analytical Model | Model Benchmark | Live Realized Manual | Reconciliation / Insight |
| :---: | :--- | :--- | :---: | ---: | :--- |
| **R1** | *An Intarian Welcome* | Uniform clearing + back-of-queue over `N(45, 22^2)` demand shocks (`Flax (30, 65)`, `Mushroom (20, 10)`) | `68.12` / `9.81` EV | **`+87,995`** | Defended clearing fill probability above static queue without overpaying |
| **R2** | *Invest & Expand* | Research/Scale FOC + Poisson Cognitive Hierarchy (`tau=1.5`, L3 `15% / 43% / 42%`) | `225,094.01` CH EV | **`+200,716`** | Slightly faster field Speed dispersion vs. idealized L3 prior (`~89%` of EV) |
| **R3** | *Celestial Gardeners' Guild* | Bayesian two-bid screening (`Bid 1 = 775, Bid 2 = 880`) over $\bar{b}_2 \sim \mathcal{N}(875, 15^2)$ | `76.00`/unit EV | **`+78,225`** | Matched Bayesian expected payout closely while avoiding cubic cliff |
| **R4** | *Aether Crystal Exotics* | Exact BS/Rubinstein + 100k `4/day` GBM KO (`AC_45_KO=0.2113`) + straddle MV hedge (`CO -50, BP -50, KO +183, C15 +53, P15 +74`) | `EV 40.96, -70.1% std` | **`+36,969`** | Captured discrete `4/d` barrier mispricing under controlled Day-15 variance |
| **R5** | *Extra! Extra!* | Ignith `9`-asset quadratic-fee KKT + variance penalty ($\kappa=3.0$, bounded `-92%` Phoenix floor; `5/9` active) | `855,944.53` net EV | **`+120,165`** | Concentrating in highest-conviction catalysts prevented quadratic fee bleed |

![Manual Challenges Analytical Comparative Statics (R1-R5)](reports/figures/manual_challenges_analysis.png)

---

## 5. Simulator Fidelity & Stressed Monte Carlo Risk (`N = 40`)

[`ExecutionSimulator`](src/prosperity_toolkit/execution/simulator.py) enforces starting-position batch limit cancellation, multi-level taker book depletion without double-counting, strict price-time maker queue conservation (`conservative`, `queue_aware`, `touch`), and causal `t - 100` `own_trades` / `prior_market_trades` lag. Synthetic stress testing (`N = 40`, `1,000` ticks) pairs calibrated `queue_aware` sessions with an explicit `AdverseStress` regime and exact 95% Wilson binomial upper bounds (`0.0876` = `8.76%` for `0/40` losses):

| Round | Scenario | Mean MC PnL | `VaR 95%` | `CVaR 95%` | `Prob(Loss)` | `Wilson 95% Upper` | Mean `IR_tick` | Source Table |
| :---: | :--- | ---: | ---: | ---: | :---: | :---: | ---: | :--- |
| **R1** | `SymmetricMM` *(baseline)* | `562.46` | `-4,609.05` | `-5,711.00` | `37.5%` | `53.0%` | `0.01035` | [`r1_mc_risk_summary.csv`](reports/tables/r1_mc_risk_summary.csv) |
| **R1** | `Round1Submission_QA` / `AdverseStress` | `6,675.06` / `3,783.54` | `3,431.15` / `-253.65` | `2,845.75` / `-2,503.00` | `0.0%` / `7.5%` | `8.8%` / `19.9%` | `0.05715` / `0.02242` | [`r1_mc_risk_summary.csv`](reports/tables/r1_mc_risk_summary.csv) |
| **R2** | `BaselineFlow` / `MAFPlus25` / `AdverseStress` | `10,966.5` / `12,631.7` / `5,572.7` | `6,556.4` / `6,491.5` / `-789.1` | `4,548.0` / `5,525.8` / `-2,163.5` | `0.0%` / `0.0%` / `10.0%` | `8.8%` / `8.8%` / `23.1%` | `0.0764` / `0.0893` / `0.0299` | [`r2_to_r5_mc_risk_summary.csv`](reports/tables/r2_to_r5_mc_risk_summary.csv) |
| **R3** | `CalibratedQA` / `AdverseStress` | `29,852.0` / `13,225.1` | `2,010.1` / `-53,416.3` | `-127.8` / `-91,007.5` | `2.5%` / `30.0%` | `12.9%` / `45.4%` | `0.0259` / `0.0088` | [`r2_to_r5_mc_risk_summary.csv`](reports/tables/r2_to_r5_mc_risk_summary.csv) |
| **R4** | `CalibratedQA` / `AdverseStress` | `27,563.0` / `12,042.4` | `-17,878.6` / `-59,763.2` | `-24,536.3` / `-66,346.5` | `12.5%` / `27.5%` | `26.1%` / `42.8%` | `0.0244` / `0.0082` | [`r2_to_r5_mc_risk_summary.csv`](reports/tables/r2_to_r5_mc_risk_summary.csv) |
| **R5** | `11AssetRepPulseMC` / `AdverseStress` | `15,279.3` / `12,994.3` | `9,767.0` / `8,720.4` | `8,334.0` / `8,013.8` | `0.0%` / `0.0%` | `8.8%` / `8.8%` | `0.1410` / `0.1200` | [`r2_to_r5_mc_risk_summary.csv`](reports/tables/r2_to_r5_mc_risk_summary.csv) |

---

## 6. Repository Structure & Reviewer Navigation

- **Executive Summary & Reports**: [`reports/FINAL_WRITEUP.md`](reports/FINAL_WRITEUP.md) · [`reports/IMC_Prosperity4_Research_Writeup.pdf`](reports/IMC_Prosperity4_Research_Writeup.pdf) · [`reports/dashboard.html`](reports/dashboard.html)
- **Round Research Cards**: [`round_1.md`](docs/rounds/round_1.md) · [`round_2.md`](docs/rounds/round_2.md) · [`round_3.md`](docs/rounds/round_3.md) · [`round_4.md`](docs/rounds/round_4.md) · [`round_5.md`](docs/rounds/round_5.md) · [`final_round.md`](docs/rounds/final_round.md)
- **Quantitative Monographs**: [`market_microstructure.md`](docs/research/market_microstructure.md) · [`fair_value_estimation.md`](docs/research/fair_value_estimation.md) · [`market_making.md`](docs/research/market_making.md) · [`inventory_management.md`](docs/research/inventory_management.md) · [`options_pricing.md`](docs/research/options_pricing.md) · [`arbitrage.md`](docs/research/arbitrage.md)
- **Engine, Validation & Postmortems**: [`system_overview.md`](docs/architecture/system_overview.md) · [`backtesting_engine.md`](docs/architecture/backtesting_engine.md) · [`data_pipeline.md`](docs/architecture/data_pipeline.md) · [`monte_carlo_simulator.md`](docs/architecture/monte_carlo_simulator.md) · [`statistical_validation.md`](docs/methodology/statistical_validation.md) · [`limitations.md`](docs/limitations.md) · [`postmortem.md`](docs/postmortem.md)
- **Executed Research Notebooks**: [`01_data_exploration.ipynb`](notebooks/01_data_exploration.ipynb) · [`02_market_microstructure.ipynb`](notebooks/02_market_microstructure.ipynb) · [`03_fair_value_analysis.ipynb`](notebooks/03_fair_value_analysis.ipynb) · [`04_strategy_comparison.ipynb`](notebooks/04_strategy_comparison.ipynb) · [`05_parameter_optimisation.ipynb`](notebooks/05_parameter_optimisation.ipynb)

```text
.
├── .github/workflows/      # CI: SHA-256 manifest verification, ruff, mypy, 5x AST checks, pytest
├── src/prosperity_toolkit/ # Modular Python 3.11 package (data, execution, backtesting, simulation, analysis, cli)
├── traders/round{1..5}/    # Standalone AST-verified Trader implementations + round cards
├── scripts/                # Reproducible pipelines (audit, replay, EDA, R1-R5 eval, manual solvers, dashboard, PDF)
├── tests/                  # Unit & integration test suite (124 tests)
├── docs/                   # Architecture, methodology, microstructure research, rounds R1-R5, manual models
├── notebooks/              # Executed Jupyter notebooks (01-05)
├── data/                   # Immutable raw CSVs (round0-5) + SHA-256 manifest registry
└── reports/                # Figures, CSV summary tables, HTML tearsheet & standalone PDF monograph
```

---

## 7. Reproducible Verification & Execution

```bash
# Sync locked environment (Python >=3.11,<3.13)
uv sync --locked --group dev

# 1. Verify immutable data SHA-256 manifest (34 raw CSVs), lint, types & full test suite (124 tests)
uv run python scripts/audit_all_datasets.py --verify-only
uv run ruff check .
uv run mypy .
uv run pytest

# 2. Validate standalone AST, stdlib & datamodel restrictions on all 5 competition files
uv run python scripts/validate_submission.py traders/round1/submission.py
uv run python scripts/validate_submission.py traders/round2/submission.py
uv run python scripts/validate_submission.py traders/round3/submission.py
uv run python scripts/validate_submission.py traders/round4/submission.py
uv run python scripts/validate_submission.py traders/round5/submission.py

# 3. Replay any standalone submission via CLI or runner
uv run python scripts/run_backtest.py --round 1 --submission traders/round1/submission.py --day 0 --fill-mode queue_aware
uv run python -m prosperity_toolkit.cli replay --round 1 --submission traders/round1/submission.py --day 0 --fill-mode queue_aware

# 4. Regenerate full research tables, competition summary, figures, HTML dashboard & PDF writeup
uv run python scripts/generate_report.py
uv run python scripts/eda_rounds2_to_5.py
uv run python scripts/evaluate_rounds2_to_5.py
uv run python scripts/evaluate_manual_challenges.py
uv run python scripts/generate_competition_summary.py
uv run python scripts/build_dashboard.py
uv run python scripts/build_pdf_writeup.py
```