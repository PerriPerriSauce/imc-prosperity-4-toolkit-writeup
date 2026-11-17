# Architecture: System Overview

## 1. System Philosophy

The **IMC Prosperity 4 Research Toolkit** is engineered as a dual-layer quantitative research platform:
1. **The Research & Simulation Engine (`src/prosperity_toolkit/`)**: A modular, type-safe Python 3.11 environment designed for statistical exploration, order book reconstruction, and execution simulation.
2. **The Competition Submission Archive (`traders/`)**: Fully isolated, standalone single-file strategies that satisfy the execution constraints of the IMC Prosperity exchange.

```
+--------------------------------------------------------------------------+
|                             Research Layer                               |
|                                                                          |
|  +--------------------+    +---------------------+    +---------------+  |
|  |   data/ (Parquet)  |--->| market/ (L2 Books)  |--->|  analysis/    |  |
|  +--------------------+    +---------------------+    +---------------+  |
|            |                          |                       |          |
|            v                          v                       v          |
|  +--------------------+    +---------------------+    +---------------+  |
|  | backtesting/Replay |--->| execution/Simulator |--->| optimisation/ |  |
|  +--------------------+    +---------------------+    +---------------+  |
+--------------------------------------------------------------------------+
                                     | (Validation & Packaging)
                                     v
+--------------------------------------------------------------------------+
|                          Competition Boundary                            |
|                                                                          |
|  +------------------------+             +-----------------------------+  |
|  |  traders/datamodel.py  | <=========> | traders/roundN/submission.py|  |
|  |  (Authoritative Spec)  |             | (Single-file Autonomous Bot)|  |
|  +------------------------+             +-----------------------------+  |
+--------------------------------------------------------------------------+
```

## 2. Key System Subsystems

- **Core (`core/`)**: Immutable primitives (`Symbol`, `Price`, `Quantity`, `Timestamp`), custom domain exceptions, and event definitions.
- **Data Pipeline (`data/`)**: Parsers for semicolon CSV files, schema validators, monotonicity checkers, and Parquet caching.
- **Market Dynamics (`market/`)**: Level 2 Order Book (`OrderBookL2`), volume-weighted mid-prices, trade flow accumulation, and rolling volatility estimators.
- **Execution Simulation (`execution/`)**: Realistic fill logic supporting passive limit queue models, aggressive crossing orders, and strict position limit enforcement.
- **Backtesting & Accounting (`backtesting/`)**: Deterministic historical market replay, marked-to-market valuation, and Sharpe/drawdown calculation.
- **Systematic Optimization (`optimisation/`)**: Multi-dimensional parameter grid generation, cross-validation, and sensitivity analysis.
- **Documentation & Analysis (`docs/`, `notebooks/`)**: Comprehensive technical reports demonstrating hypothesis-driven quantitative finance.
