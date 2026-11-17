# Quantitative Research: Option Pricing & Volatility Dynamics

## 1. The Black-Scholes Formulation

For a European call option with spot price $S$, strike price $K$, risk-free rate $r$, time-to-maturity $\tau = T - t$, and constant volatility $\sigma$:
$$C(S, K, \tau, r, \sigma) = S \Phi(d_1) - K e^{-r \tau} \Phi(d_2)$$
where:
$$d_1 = \frac{\ln(S / K) + \left(r + \frac{1}{2}\sigma^2\right)\tau}{\sigma \sqrt{\tau}}, \quad d_2 = d_1 - \sigma \sqrt{\tau}$$
and $\Phi(\cdot)$ is the cumulative standard normal distribution function.

## 2. Greeks & Dynamic Delta Hedging

The option's sensitivity to the underlying price is delta ($\Delta$):
$$\Delta_{\text{call}} = \frac{\partial C}{\partial S} = \Phi(d_1)$$

To construct a delta-neutral portfolio $\Pi = C - \Delta \cdot S$, the trader continuously hedges option positions with underlying spot contracts.

## 3. Implied Volatility Inversion

Given observed market option price $C_{\text{obs}}$, we solve for implied volatility $\sigma_{\text{imp}}$ via the Newton-Raphson method or Brent's root-finding algorithm:
$$\sigma_{n+1} = \sigma_n - \frac{C(\sigma_n) - C_{\text{obs}}}{\mathcal{V}(\sigma_n)}$$
where $\mathcal{V} = \frac{\partial C}{\partial \sigma} = S \sqrt{\tau} \phi(d_1)$ is Vega.
