# Quantitative Research: Statistical & Conversion Arbitrage

## 1. Cointegration & Vector Error Correction (VECM)

Let $P_t = (P_{1, t}, \dots, P_{K, t})'$ be a vector of asset prices integrated of order 1 ($I(1)$).

If a cointegrating vector $\beta$ exists such that:
$$z_t = \beta' P_t \sim I(0)$$
then the linear combination $z_t$ is stationary with finite variance and mean-reverting properties.

We test for cointegration using the **Engle-Granger two-step method** and the multivariate **Johansen trace test**.

## 2. Spatial & Conversion Arbitrage

In the presence of physical or digital conversion mechanisms between an asset in location $A$ and location $B$:
$$\Pi_{\text{long-conv}} = P_B(t) - (P_A(t) + \text{Fee}_{\text{transport}} + \text{Tariff}_{\text{import}})$$
$$\Pi_{\text{short-conv}} = (P_A(t) - \text{Fee}_{\text{transport}} - \text{Tariff}_{\text{export}}) - P_B(t)$$

Conversions are initiated only when expected profit exceeds parameter-estimated transaction slippage:
$$\max(\Pi_{\text{long-conv}}, \Pi_{\text{short-conv}}) > \epsilon_{\text{threshold}}$$
