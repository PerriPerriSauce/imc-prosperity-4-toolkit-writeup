# IMC Prosperity 4 — Quantitative Research Toolkit & Writeup

[![CI](https://github.com/ADnocap/IMC_Prosperity4/actions/workflows/ci.yml/badge.svg)](https://github.com)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/release/python-3118/)
[![Code Style: Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Type Checked: mypy](https://img.shields.io/badge/type%20checked-mypy-blue.svg)](http://mypy-lang.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A high-performance, reproducible quantitative trading research toolkit, backtesting framework, and strategy writeup for the **IMC Prosperity 4** algorithmic trading competition (April 2026).

---

## 1. Project Overview

**IMC Prosperity 4** was an international algorithmic trading competition organized by IMC Trading spanning 5 rounds, challenging participants to design automated trading algorithms across diverse asset classes (including mean-reverting minerals, drifting agricultural products, spatial conversion arbitrage, and cross-sectional 50-asset joint books).

This repository serves as both:
1. **A Quantitative Research & Simulation Toolkit (`prosperity_toolkit`)**: A Python-first modular backtester, Level 2 order book reconstructor, execution simulator, and statistical optimization suite.
2. **A Strategy Writeup & Technical Archive (`docs/`, `notebooks/`)**: An exhaustive record of mathematical models, microstructure hypotheses, parameter calibration experiments, and post-mortems demonstrating institutional-grade quantitative workflow.

---

## 2. Repository Structure

```text
imc-prosperity-4-toolkit-writeup/
│
├── .agent/workflows/         # Agentic research & execution workflow instructions
├── .agents/rules/            # Project rules (documentation, research, testing, trading)
├── .github/                  # CI automation (GitHub Actions) & issue templates
├── config/                   # Declarative YAML configurations (replay, search, defaults)
│   ├── default.yaml
│   ├── backtest.yaml
│   └── optimisation.yaml
│
├── data/                     # Historical market data (strictly separated & immutable)
│   ├── raw/                  # Immutable raw competition CSVs (read-only)
│   ├── interim/              # Intermediate data representations
│   ├── processed/            # Cleaned, schema-validated binary Parquet files
│   └── README.md             # Data provenance policy and checksum manifest
│
├── docs/                     # Comprehensive quantitative writeup & documentation
│   ├── architecture/         # System design, data pipeline, and backtester engine
│   ├── methodology/          # Research standards, backtesting protocols, statistical tests
│   ├── rounds/               # Round-by-round asset dynamics and mechanics (R1 to R5)
│   ├── research/             # Microstructure, fair value, market making, arbitrage, options
│   ├── experiments/          # Empirical hypothesis and trial registry
│   ├── postmortem.md         # Anomaly post-mortems and root cause analysis (RCA)
│   └── limitations.md        # Explicit simulation bounds and modeling assumptions
│
├── notebooks/                # Exploratory Jupyter research notebooks (EDA, calibration)
│   ├── 01_data_exploration.ipynb
│   ├── 02_market_microstructure.ipynb
│   ├── 03_fair_value_analysis.ipynb
│   ├── 04_strategy_comparison.ipynb
│   └── 05_parameter_optimisation.ipynb
│
├── reports/                  # Generated research artifacts
│   ├── figures/              # Exported publication-grade matplotlib figures
│   ├── tables/               # Formatted summary metric tables
│   └── experiments/          # Output records from parameter optimization runs
│
├── scripts/                  # Standalone CLI tools & utility wrappers
│   ├── inspect_data.py       # Data integrity and schema validation utility
│   ├── run_backtest.py       # Historical replay runner
│   ├── run_optimisation.py   # Parameter search runner
│   ├── generate_report.py    # Report synthesis script
│   └── validate_submission.py# Single-file submission verification tool
│
├── src/prosperity_toolkit/   # Core installable Python package
│   ├── core/                 # Primitives (models, events, interfaces, exceptions)
│   ├── data/                 # Loaders, parsers, normalizers, schemas, validators
│   ├── market/               # L2 order book, order flow, indicators, fair value
│   ├── strategies/           # Base contracts and strategy archetypes
│   ├── execution/            # Simulators, fill models, position limit checking
│   ├── backtesting/          # Portfolio accounting, replay loop, metrics, results
│   ├── optimisation/         # Grid search, objectives, sensitivity analysis
│   ├── analysis/             # Descriptive statistics, risk metrics, DSR diagnostics
│   ├── competition/          # Authoritative datamodel, state adapter, AST validator
│   └── visualisation/        # Standardized tearsheet charts and markdown dashboards
│
├── traders/                  # Standalone competition submissions (competition boundary)
│   ├── datamodel.py          # Standalone competition datamodel (zero toolkit dependencies)
│   └── round{1..5}/          # Round submission artifacts
│
├── tests/                    # Comprehensive automated test suite
│   ├── conftest.py           # Shared fixtures
│   ├── fixtures/             # Synthetic market test fixtures
│   ├── unit/                 # Unit tests (math, metrics, order book, accounting)
│   └── integration/          # End-to-end replay and strategy lifecycle tests
│
├── .gitattributes            # Line ending normalization
├── .gitignore                # Build artifact and credential exclusions
├── .python-version           # Pinned Python version (3.11)
├── AGENTS.md                 # Agent instructions and system requirements
├── LICENSE                   # MIT License
├── pyproject.toml            # Project dependencies and tool configurations
└── uv.lock                   # Deterministic dependency lockfile
```

---

## 3. Installation Instructions

This project requires **Python 3.11** and uses [`uv`](https://github.com/astral-sh/uv) for fast, deterministic dependency and virtual environment management.

### Prerequisites

- [uv](https://docs.astral.sh/uv/getting-started/installation/) installed.
- Python 3.11 available on the system.

### One-Command Setup

```bash
# Clone the repository
git clone https://github.com/your-username/imc-prosperity-4-toolkit-writeup.git
cd imc-prosperity-4-toolkit-writeup

# Synchronize virtual environment and install in editable mode
uv sync
```

---

## 4. Development & Verification Commands

```bash
# Run complete test suite with coverage
uv run pytest

# Static type checking across src/ and tests/
uv run mypy .

# Code linting and style enforcement
uv run ruff check .

# Code formatting check
uv run ruff format --check .

# Validate a competition submission script for sandbox compliance
uv run python scripts/validate_submission.py traders/round1/submission.py
```

---

## 5. Data Provenance Policy

In accordance with strict quantitative research ethics (Rule 7):
- **Raw Data Immutability**: All original historical CSV files stored under `data/raw/` are treated as read-only and never mutated.
- **Traceability**: All derived tables in `data/processed/` are generated via reproducible scripts recorded with SHA-256 checksums in `data/manifest.json`.
- **Attribution**: Source filenames, dates of acquisition, and schema invariants are cataloged in [`data/README.md`](data/README.md).

---

## 6. Research Methodology Principles

1. **Hypothesis-Driven Alpha**: Every strategy begins with an economic rationale or microstructure inefficiency before any parameters are tuned.
2. **Conservative Execution Modeling**: We deliberately penalize passive limit fills in historical replay to avoid optimistic fill bias.
3. **Overfitting Corrections**: We apply the **Deflated Sharpe Ratio (DSR)** and **Combinatorial Symmetric Cross-Validation (CSCV)** to correct for multiple testing across parameter trials.
4. **Separation of Concerns**: Competition-facing code (`traders/`) is kept strictly decoupled from research infrastructure (`src/prosperity_toolkit/`) to guarantee sandbox compatibility.
