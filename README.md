# IMC Prosperity 4 — Quantitative Trading Research & Multi-Round Strategy Portfolio

> **Executive Deliverables**: Start with [FINAL_WRITEUP.md](file:///c:/Users/pierr/Desktop/imc-prosperity-4-toolkit-writeup/reports/FINAL_WRITEUP.md), the standalone PDF monograph [IMC_Prosperity4_Research_Writeup.pdf](file:///c:/Users/pierr/Desktop/imc-prosperity-4-toolkit-writeup/reports/IMC_Prosperity4_Research_Writeup.pdf), the interactive portfolio tearsheet [dashboard.html](file:///c:/Users/pierr/Desktop/imc-prosperity-4-toolkit-writeup/reports/dashboard.html), and the manual-challenge monograph [MANUAL_CHALLENGES.md](file:///c:/Users/pierr/Desktop/imc-prosperity-4-toolkit-writeup/docs/manual/MANUAL_CHALLENGES.md).

An end-to-end **Python 3.11** quantitative research toolkit, queue-aware event replay simulator, vectorized Monte Carlo stress engine, combinatorial overfitting gate suite (`CSCV PBO`, `DSR`, block bootstrap), and competition-compliant strategy library for all five rounds of **IMC Prosperity 4**—built with strict separation between research infrastructure (`src/prosperity_toolkit/`) and zero-dependency submission traders (`traders/round{1..5}/submission.py`).

---

## Key Verified Results (`queue_aware` Held-Out Out-of-Sample Replay)

*Disclaimer: Every trading metric below reflects **simulated chronological out-of-sample replays** on archived historical books under [`FillMode.QUEUE_AWARE`](file:///c:/Users/pierr/Desktop/imc-prosperity-4-toolkit-writeup/src/prosperity_toolkit/execution/simulator.py), **not** live leaderboard outcomes.*

| Round | Focus & Active Universe | `Q_max` | Held-Out OOS Day | OOS PnL (`queue_aware`) | OOS `Sharpe_252` (`95% CI`) | `CSCV PBO` | `DSR` | Mean Latency / Tick | Submission |
| :--- | :--- | :---: | :---: | ---: | :--- | :---: | :---: | ---: | :--- |
| **Round 1** | Bot-wall FV, affine drift, penny-join (`2` assets) | `20` *(stressed)* | `Day 0` | **`+22,157.00`** | `1.1894` `[1.046, 1.329]` | `0.0860` | `1.0000` | `0.0340 ms` | [`round1/submission.py`](file:///c:/Users/pierr/Desktop/imc-prosperity-4-toolkit-writeup/traders/round1/submission.py) |
| **Round 2** | Scaled skew + MAF auction MC (`2` assets) | `80` | `Day 1` | **`+27,463.00`** | `1.3972` `[1.2314, 1.5823]` | `0.0000` | `1.0000` | `0.0406 ms` | [`round2/submission.py`](file:///c:/Users/pierr/Desktop/imc-prosperity-4-toolkit-writeup/traders/round2/submission.py) |
| **Round 3** | Total-vol BS options & delta band (`12` assets) | `200`/`300` | `Day 2` | **`+7,525.50`** | `0.2276` `[0.0097, 0.4392]` | `0.0000` | `0.9921` | `0.1872 ms` | [`round3/submission.py`](file:///c:/Users/pierr/Desktop/imc-prosperity-4-toolkit-writeup/traders/round3/submission.py) |
| **Round 4** | Live `Mark 67` counterparty flow (`12` assets) | `200`/`300` | `Day 3` | **`+11,741.00`** | `0.3613` `[0.0932, 0.6302]` | `0.0571` | `0.9975` | `0.1871 ms` | [`round4/submission.py`](file:///c:/Users/pierr/Desktop/imc-prosperity-4-toolkit-writeup/traders/round4/submission.py) |
| **Round 5** | Lag-free 50-asset MM, vol-guard & atomic `Pebbles` | **`10`** (`x50`) | `Day 4` | **`+123,173.00`** | `0.8109` `[0.5789, 1.0627]` | `0.1000` | `1.0000` | `0.6920 ms` | [`round5/submission.py`](file:///c:/Users/pierr/Desktop/imc-prosperity-4-toolkit-writeup/traders/round5/submission.py) |
| **Total** | — | — | — | **`+192,059.50`** | — | `<= 0.100` | `>= 0.992` | `<= 0.6920 ms` | — |

- **Manual Challenges (`R1–R5`)**: Uncertain-demand auction optimization (`R1`: Flax `(30, 65)`, Mushroom `(20, 10)`), Poisson Cognitive Hierarchy (`R2`: `L1–L3` converging to submitted `42%` Speed / `15%` Research / `43%` Scale), Bayesian two-bid screening (`R3`: submitted `(775, 880)`), `251%` annualized discrete `6h` Broadie–Glasserman–Kou exotic Monte Carlo + hedged 5-contract portfolio (`R4`: `-15 / -50 / +198 / +5 / +21`), and 9 Ignith goods exact KKT + quadratic-variance portfolio optimization (`R5`: `+35 / +29 / -23 / -10 / +3%`) implemented in [`manual_challenges.py`](file:///c:/Users/pierr/Desktop/imc-prosperity-4-toolkit-writeup/src/prosperity_toolkit/analysis/manual_challenges.py).

## Repository Architecture

```text
.
├── src/prosperity_toolkit/
│   ├── analysis/           # Microstructure EDA, CSCV PBO, DSR, N_eff, bootstrap, manual solvers
│   ├── backtesting/        # Deterministic replay engine, position limits, batch cancellation
│   ├── competition/        # Local Prosperity 4 datamodel, submission validator, strategy adapter
│   ├── data/               # Prosperity CSV ingestion, SHA-256 dataset manifest & integrity checks
│   ├── execution/          # conservative / queue_aware / touch execution matching
│   ├── optimisation/       # Grid sweep, neighborhood stability, sensitivity surface helpers
│   ├── simulation/         # Vectorized OU/RW/Jump/Options MC engine with synthetic bot books
│   ├── strategies/         # Research & ablation baselines (NoOp, SymmetricMM, EMA, Options, etc.)
│   └── visualisation/      # Matplotlib performance plots + self-contained HTML portfolio tearsheet
├── traders/round{1..5}/    # Standalone competition-ready Trader implementations & local runner tests
├── scripts/                # Reproducible CLI pipelines for EDA, R1-R5 backtests, manual solvers & dashboard
├── tests/                  # Unit and end-to-end integration test suites (pytest, ruff, mypy clean)
├── docs/
│   ├── competition/        # Verified rules, product limits & CSV format specification
│   ├── architecture/       # System, backtester, Monte Carlo, and data pipeline blueprints
│   ├── methodology/        # Backtesting, research workflow & anti-overfitting mathematics
│   ├── research/           # Cross-round microstructure, FV, MM, options & arbitrage studies
│   ├── rounds/             # Per-round analyses (`round_1.md`..`round_5.md`, `final_round.md`)
│   ├── manual/             # Manual Challenges documentation (`MANUAL_CHALLENGES.md`)
│   ├── experiments/        # Registered experiment index (`EXP-R1-001`..`EXP-R5-001`)
│   ├── limitations.md      # Modeling boundaries, simulation approximations & epistemic tags
│   └── postmortem.md       # Incident log (`PM-001`..`PM-005`) documenting resolved strategy failures
├── notebooks/              # Exploratory Jupyter research notebooks (01-05)
└── reports/                # Generated CSV tables, figures, FINAL_WRITEUP.md & dashboard.html
```

---

## Reproducible Setup & Verification

Using `uv` (Python 3.11+):

```bash
uv sync --all-extras
```

### Run Quality & Submission Verification Gates

```bash
# Unit and integration tests
uv run pytest

# Lint and strict static type checks
uv run ruff check .
uv run mypy .

# Validate every standalone competition submission interface & runtime constraints
uv run python scripts/validate_submission.py traders/round1/submission.py
uv run python scripts/validate_submission.py traders/round2/submission.py
uv run python scripts/validate_submission.py traders/round3/submission.py
uv run python scripts/validate_submission.py traders/round4/submission.py
uv run python scripts/validate_submission.py traders/round5/submission.py
```

### Reproduce Research Tables, Figures & HTML Tearsheet

```bash
# Dataset integrity verification against data/manifests/prosperity4_manifest.json
uv run python scripts/audit_all_datasets.py

# Round 1 IS/OOS ablations, CSCV, DSR, bootstrap & MC artifacts
uv run python scripts/generate_report.py

# Rounds 2-5 cross-round EDA, strategy ablations, validation gates & MC stress suites
uv run python scripts/eda_rounds2_to_5.py
uv run python scripts/evaluate_rounds2_to_5.py

# Manual Challenges (R1-R5), HTML dashboard & standalone PDF monograph
uv run python scripts/evaluate_manual_challenges.py
uv run python scripts/build_dashboard.py
uv run python scripts/build_pdf_writeup.py
```

---

## Epistemic Standards & Attribution

- Raw historical market data files reside untouched under `data/raw/prosperity4/` with filenames and SHA-256 hashes audited in [`prosperity4_manifest.json`](file:///c:/Users/pierr/Desktop/imc-prosperity-4-toolkit-writeup/data/manifests/prosperity4_manifest.json).
- All empirical claims cleanly separate **observed order books**, **in-sample estimated parameters**, **queue-aware simulated replays**, **synthetic Monte Carlo runs**, and **parameterized manual-challenge beliefs**.
- Full engineering caveats, unverified competition edge limits, and carried action items are maintained in [`limitations.md`](file:///c:/Users/pierr/Desktop/imc-prosperity-4-toolkit-writeup/docs/limitations.md) and [`postmortem.md`](file:///c:/Users/pierr/Desktop/imc-prosperity-4-toolkit-writeup/docs/postmortem.md).
