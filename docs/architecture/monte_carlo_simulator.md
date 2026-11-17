# Architecture: Vectorized Monte Carlo Simulator

## 1. Motivation & Role in the Backtesting Stack

Historical CSV replay suffers from **passive fill non-endogeneity**: recorded public trades do not react to resting quotes placed by a candidate strategy. To evaluate market-making and inventory-skewed quoting without optimistic fill bias, the simulator generates synthetic market sessions driven by calibrated stochastic fair-value processes and autonomous counterparty order flow.

---

## 2. Stochastic Fair-Value Processes (`simulation/processes.py`)

### A. Exact Ornstein-Uhlenbeck (OU) Discretization
For mean-reverting assets, fair value $S_t$ follows:
$$dS_t = \theta (\mu - S_t)\,dt + \sigma\,dW_t$$
Rather than using Euler-Maruyama (which introduces discretization bias when $\theta \Delta t$ is non-negligible), we sample from the exact Gaussian transition density:
$$S_{t+\Delta t} = \mu + (S_t - \mu)e^{-\theta \Delta t} + \sigma \sqrt{\frac{1 - e^{-2\theta \Delta t}}{2\theta}}\,Z_t, \quad Z_t \sim \mathcal{N}(0, 1)$$
As $t \to \infty$, the process converges to the stationary distribution:
$$S_\infty \sim \mathcal{N}\left(\mu, \frac{\sigma^2}{2\theta}\right)$$

### B. Arithmetic Random Walk with Drift
For trending or non-stationary instruments:
$$S_{t+\Delta t} = S_t + \mu_{\text{drift}}\,\Delta t + \sigma\sqrt{\Delta t}\,Z_t$$

---

## 3. Synthetic Book & Counterparty Flow (`simulation/synthetic_book.py`, `pulses.py`)

1. **Market-Maker Bot Book**: Around each simulated $FV_t$, discrete integer top-of-book quotes are constructed:
   $$P_{\text{bid}, 1} = \lfloor FV_t - \delta_1 \rfloor, \quad P_{\text{ask}, 1} = \lceil FV_t + \delta_1 \rceil$$
   with strict non-crossing enforcement ($P_{\text{bid}, 1} < P_{\text{ask}, 1}$) and optional L2 ladder depth.
2. **Counterparty Order Arrivals**: Vectorized Bernoulli/uniform-size draws generate signed taker arrivals $Q_t \in \mathbb{Z}$ across `(n_sessions, n_steps)`, converted into synthetic `TradePrint` events at the prevailing touch.
3. **Correlated Multi-Asset Pulses**: `generate_correlated_pulses` models simultaneous cross-asset liquidity/price shocks across instrument groups.

---

## 4. Tail-Risk & Distributional Evaluation (`simulation/scenario.py`)

Across $N$ independent sessions, `MonteCarloSummary` reports:
- **Location & Dispersion**: Mean PnL, Median PnL, Standard Deviation of PnL.
- **Value at Risk ($\text{VaR}_{95}$)**: Empirical 5th percentile of terminal session PnL.
- **Conditional Value at Risk ($\text{CVaR}_{95}$ / Expected Shortfall)**: Mean terminal PnL across the worst 5% of sessions ($\text{CVaR}_{95} \le \text{VaR}_{95}$).
- **Probability of Loss**: $\mathbb{P}(\text{PnL}_T < 0)$.

---

## 5. Model Assumptions & Limitations

1. **Gaussian Innovation Assumption**: Standard OU and Brownian motion innovations assume thin-tailed normal increments unless augmented with jump pulses; extreme tail events may be understated.
2. **Exogenous Arrival Intensity**: Counterparty arrival probability is currently constant per tick rather than state-dependent (e.g., Hawkes self-exciting or spread-elastic).
3. **Synthetic vs. Actual**: Monte Carlo outputs represent *simulated* distributions under explicit parametric assumptions and must never be presented as actual competition results.
