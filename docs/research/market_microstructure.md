# Quantitative Research: Market Microstructure

## 1. Limit Order Book Mechanics

The order book represents the latent supply and demand schedule in continuous double auctions.

Let $b_t(p)$ denote available resting bid volume at price $p$ and $a_t(p)$ denote available resting ask volume. The Level 1 top-of-book is defined by:
$$P_{\text{bid}}^*(t) = \max \{ p : b_t(p) > 0 \}, \quad P_{\text{ask}}^*(t) = \min \{ p : a_t(p) > 0 \}$$

The quoted spread is:
$$S_t = P_{\text{ask}}^*(t) - P_{\text{bid}}^*(t)$$

## 2. Order Book Imbalance (OBI) & Microprice

Order book imbalance captures short-term order flow pressure:
$$\text{OBI}_t = \frac{V_{\text{bid}, 1}(t) - V_{\text{ask}, 1}(t)}{V_{\text{bid}, 1}(t) + V_{\text{ask}, 1}(t)} \in [-1, 1]$$

The volume-weighted microprice $P_t^{\text{micro}}$ accounts for immediate queue imbalances:
$$P_t^{\text{micro}} = \frac{V_{\text{ask}, 1}(t) P_{\text{bid}}^*(t) + V_{\text{bid}, 1}(t) P_{\text{ask}}^*(t)}{V_{\text{bid}, 1}(t) + V_{\text{ask}, 1}(t)} = P_{\text{mid}}(t) + \frac{S_t}{2} \cdot \text{OBI}_t$$

When $\text{OBI}_t > 0$ (bid queue exceeds ask queue), $P_t^{\text{micro}} > P_{\text{mid}}(t)$, signaling upward tick pressure.
