# Architecture: Vectorized Monte Carlo Simulator

## 1. Motivation & Role in the Backtesting Stack

Historical CSV replay suffers from **passive fill non-endogeneity**: recorded public trades do not react to resting quotes placed by a candidate strategy. To stress market-making and inventory-skewed strategies under controlled arrival intensity, spread width, and adverse selection, `prosperity_toolkit.simulation` generates synthetic market sessions driven by calibrated fair-value dynamics and configurable execution stress.

---

## 2. Stochastic Fair-Value Processes (`simulation/processes.py`, `joint_scenarios.py`)

### A. Exact Ornstein-Uhlenbeck (OU) Discretization
For mean-reverting assets, fair value $S_t$ follows:
$$dS_t = \theta (\mu - S_t)\,dt + \sigma\,dW_t$$
Rather than Euler-Maruyama discretization (which biases persistence when $\theta \Delta t$ is non-negligible), we sample from the exact Gaussian transition density:
$$S_{t+\Delta t} = \mu + (S_t - \mu)e^{-\theta \Delta t} + \sigma \sqrt{\frac{1 - e^{-2\theta \Delta t}}{2\theta}}\,Z_t, \quad Z_t \sim \mathcal{N}(0, 1)$$

### B. Arithmetic Random Walk with Drift & Coupled Suites
For trending instruments (`INTARIAN_PEPPER_ROOT`), fair value follows $S_{t+\Delta t} = S_t + \mu_{\text{drift}}\,\Delta t + \sigma\sqrt{\Delta t}\,Z_t$. Multi-asset scenario builders (`run_joint_mc_suite`, `run_round5_pulse_mc_suite`) generate coupled spot/call voucher books (`R3`/`R4`), counterparty impulse prints (`R4`), and synchronized 11-asset representative pulse clusters (`R5`).

---

## 3. Fill Regimes, Adverse Selection Stress & Statistical Bounds (`simulation/scenario.py`)

To guard against optimistic synthetic quoting results:
1. **`fill_mode` Propagation**: `ExecutionSimulator` runs every Monte Carlo path with explicit `fill_mode` (`queue_aware` or `conservative`, rather than collapsing maker fills to `touch`).
2. **Adverse-Selection Stress Parameter (`adverse_selection_prob`)**: Under the `AdverseStress` regime (`adverse_selection_prob > 0`), taker fills precede an immediate adversarial jump in the synthetic fair value in the direction of the aggressor, directly taxing stale resting quotes (e.g., `Round3Submission_AdverseStress` exhibits `30.0%` loss frequency vs. `2.5%` calibrated `QA`; `Round1Submission_AdverseStress` rises from `0.0%` to `7.5%`).
3. **Finite-Sample Wilson Upper Bounds (`wilson_ci_upper`)**: When `0` of `N = 40` synthetic sessions lose money, reporting "0% probability of loss" overstates certainty. `MonteCarloSummary` reports `prob_loss_ci95_upper` using the 95% Wilson binomial upper bound (`0.0876` = `8.76%` upper bound for `0/40` losses).

---

## 4. Tail-Risk & Distributional Evaluation

Across $N = 40$ independent `1,000`-step sessions, `MonteCarloSummary` reports:
- **Location & Dispersion**: Mean PnL, Median PnL, Standard Deviation of PnL, Mean Unannualized `IR_tick`.
- **Value at Risk ($\text{VaR}_{95}$)** & **Conditional Value at Risk ($\text{CVaR}_{95}$)**: Empirical 5th percentile and tail expectation ($\text{CVaR}_{95} \le \text{VaR}_{95}$).
- **Loss Rate & Bounds**: Sample `prob_loss` alongside 95% Wilson upper bound `prob_loss_ci95_upper`, Mean Max Drawdown, and Worst Max Drawdown.

---

## 5. Model Assumptions & Limitations

1. **Gaussian Innovation Assumption**: Standard OU and Brownian motion innovations assume thin-tailed normal increments unless augmented with jump pulses; extreme tail events may still be understated.
2. **Exogenous Arrival Intensity**: Counterparty arrival probability is exogenous rather than price-impact-endogenous beyond the injected adverse-selection stress probability.
3. **Synthetic vs. Actual**: Monte Carlo outputs represent *simulated* stress distributions under parametric assumptions and must never be presented as actual competition results.
