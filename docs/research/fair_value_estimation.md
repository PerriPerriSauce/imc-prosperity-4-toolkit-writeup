# Quantitative Research: Fair Value Estimation

## 1. Mathematical Formulation

Let $S_t$ denote the observable mid-price and $FV_t$ denote the unobservable true continuous fair value.

In continuous time, mean-reverting fair value dynamics follow an **Ornstein-Uhlenbeck (OU)** stochastic differential equation:
$$d FV_t = \theta (\mu - FV_t) dt + \sigma d W_t$$
where:
- $\theta > 0$ is the rate of mean reversion.
- $\mu$ is the long-term equilibrium price.
- $\sigma > 0$ is the diffusion volatility.
- $W_t$ is a standard Brownian motion.

The half-life of mean reversion is given by:
$$t_{1/2} = \frac{\ln 2}{\theta}$$

## 2. Server Fair Value Extraction

In discrete simulated exchange environments with deterministic or bot-driven market dynamics, the server's fair value can be extracted empirically by evaluating the PnL of a static hold-1 inventory unit:
$$FV_t = \text{PnL}_t^{\text{hold-1}} - \text{PnL}_{t-1}^{\text{hold-1}} + FV_{t-1}$$
This technique allows recovering the ground-truth fair value trajectory for bot calibration without look-ahead contamination.
