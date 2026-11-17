# Workflow: Quantitative Research Experiment

When exploring alpha, signals, or market microstructure:

1. **Hypothesis Formulation**:
   - Clearly define the economic or microstructural rationale in `docs/research/`.
   - Specify equations in LaTeX format.

2. **Empirical Data Validation**:
   - Inspect raw data using `scripts/inspect_data.py`.
   - Run stationarity (ADF), autocorrelation, and spread distribution checks in `notebooks/`.

3. **Backtest Replay vs. Monte Carlo**:
   - Run historical replay for execution verification.
   - Run Monte Carlo simulation for market-making fill dynamics.

4. **Overfitting Correction**:
   - Calculate Deflated Sharpe Ratio (DSR) and probability of overfitting across parameter runs.
