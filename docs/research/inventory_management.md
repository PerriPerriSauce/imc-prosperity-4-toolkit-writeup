# Quantitative Research: Inventory Risk Management

## 1. Inventory Penalties & Quadratic Costs

Accumulating directional inventory in a market-making strategy exposes the portfolio to uncompensated drift risk and toxic flow.

We formulate the inventory penalty as a quadratic loss function:
$$\mathcal{L}_{\text{inv}}(q) = \lambda_{\text{inv}} \cdot q^2$$
where $\lambda_{\text{inv}} > 0$ controls the penalty intensity.

## 2. Dynamic Asymmetric Quoting

When inventory $q > 0$ (long bias):
- The market maker skews quotes downward to discourage additional buy fills and incentivize sell fills:
  $$\Delta_{\text{bid}} = \delta_0 + \alpha q, \quad \Delta_{\text{ask}} = \max(1, \delta_0 - \alpha q)$$
- If inventory approaches the position boundary $q \to Q_{\max}$, the buy quote is pulled entirely ($\Delta_{\text{bid}} \to \infty$) while the ask is placed aggressively at the best ask or inside the spread.
