# Research Methodology

## 1. Quantitative Research Standards

Every strategy developed in this repository follows the scientific method:
1. **Microstructural Hypothesis**: We first formulate a grounded economic or microstructural explanation for an observed price phenomenon.
2. **Descriptive Empirical Analysis**: We inspect distribution moments, order book imbalances, autocorrelation, and cross-correlations before proposing trading rules.
3. **Model Formulation**: Strategies are parameterized explicitly with mathematical expressions.
4. **Baseline Comparison**: All candidate alpha strategies are benchmarked against null models (e.g. passive mid-spread quoting, hold-1 baseline).
5. **Ablation & Sensitivity**: Parameters are stressed across neighboring values to identify regime cliffs and overfitting.

## 2. Distinction of Knowledge Layers

To prevent cognitive bias and misleading portfolio metrics, we maintain strict distinctions between:
- **Observed Data**: Direct empirical records from historical CSV files.
- **Estimated Parameters**: Quantities estimated via statistical regressions or calibrations (e.g. mean-reversion speed $\theta$, volatility $\sigma$).
- **Simulated Outcomes**: PnL and execution metrics produced by our backtesting framework.
- **Actual Competition Results**: Official leaderboard submissions and portal returns.
