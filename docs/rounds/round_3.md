# Round 3: Multi-Asset Basket & Cointegration Arbitrage

## 1. Tradable Instruments
- Slate reset: Introduces **HYDROGEL_PACK**, **VELVETFRUIT_EXTRACT**, and **VEV_*** synthetic derivative baskets.
- Round 1 and Round 2 instruments are delisted.

## 2. Research Focus
- Component basket cointegration:
  $$\text{Spread}_t = P_{\text{basket}, t} - \sum_{i=1}^K w_i P_{\text{component}, i, t}$$
- Mean-reversion trading when standardized $z$-score exceeds entry thresholds:
  $$z_t = \frac{\text{Spread}_t - \mu_{\text{spread}}}{\sigma_{\text{spread}}}$$
