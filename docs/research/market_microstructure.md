# Quantitative Research: Market Microstructure

## 1. Limit Order Book Mechanics

The order book represents the latent supply and demand schedule in continuous double auctions.

Let $b_t(p)$ denote available resting bid volume at price $p$ and $a_t(p)$ denote available resting ask volume. The Level 1 top-of-book is defined by:
$$P_{\text{bid}}^*(t) = \max \{ p : b_t(p) > 0 \}, \quad P_{\text{ask}}^*(t) = \min \{ p : a_t(p) > 0 \}$$

The quoted spread is:
$$S_t = P_{\text{ask}}^*(t) - P_{\text{bid}}^*(t)$$

---

## 2. Order Book Imbalance (OBI) & Microprice

Order book imbalance captures short-term order flow pressure:
$$\text{OBI}_t = \frac{V_{\text{bid}, 1}(t) - V_{\text{ask}, 1}(t)}{V_{\text{bid}, 1}(t) + V_{\text{ask}, 1}(t)} \in [-1, 1]$$

The volume-weighted microprice $P_t^{\text{micro}}$ accounts for immediate queue imbalances:
$$P_t^{\text{micro}} = \frac{V_{\text{ask}, 1}(t) P_{\text{bid}}^*(t) + V_{\text{bid}, 1}(t) P_{\text{ask}}^*(t)}{V_{\text{bid}, 1}(t) + V_{\text{ask}, 1}(t)} = P_{\text{mid}}(t) + \frac{S_t}{2} \cdot \text{OBI}_t$$

When $\text{OBI}_t > 0$ (bid queue exceeds ask queue), $P_t^{\text{micro}} > P_{\text{mid}}(t)$, signaling upward tick pressure.

---

## 3. Empirical Findings: Round 0 & Round 1 Microstructure

Analysis generated via `scripts/analyze_microstructure.py` on `data/raw/prosperity4/{round0,round1}/`:

### A. Quote-Bounce Negative Autocorrelation ($\rho(1) \approx -0.49$)
Across `EMERALDS`, `ASH_COATED_OSMIUM`, and `INTARIAN_PEPPER_ROOT`, two-sided mid-price differences $\Delta P_t = P_t - P_{t-1}$ exhibit lag-1 autocorrelation $\rho(1) \in [-0.506, -0.482]$ and near-zero $\rho(2)$:
- **Cause**: When $P_t = FV_t + \varepsilon_t$ with transitory i.i.d. quote-jitter $\varepsilon_t$ (such as temporary inside-spread bot quotes), $\Delta P_t = \Delta FV_t + \varepsilon_t - \varepsilon_{t-1}$ yields:
  $$\rho(1) = \frac{\text{Cov}(\Delta P_t, \Delta P_{t-1})}{\text{Var}(\Delta P_t)} = \frac{-\sigma_\varepsilon^2}{\sigma_{FV}^2 + 2\sigma_\varepsilon^2} \to -0.5 \quad \text{as } \sigma_\varepsilon^2 \gg \sigma_{FV}^2$$
- **Trading Implication**: Negative $\rho(1)$ reflects **transient book noise**, not permanent alpha—chasing tick-to-tick mid jumps incurs negative expectancy.

### B. Distinguishing Correlation from Causation in OBI
In Round 0 (`EMERALDS`) and Round 1 (`ASH_COATED_OSMIUM`, `INTARIAN_PEPPER_ROOT`), $\text{OBI}_t$ exhibits $r \approx 0.52\text{–}0.64$ ($p < 10^{-100}$) against $\Delta P_{t+h}$ for $h \in \{1, 5, 10\}$:
- **Why this occurs**: When a small-volume bot steps inside the full spread on one side (e.g., posting a thin ask inside the 16-tick spread of `EMERALDS`), two things happen simultaneously: (1) mid-price shifts downward temporarily, and (2) L1 volume on that inside side is small, making $\text{OBI}_t > 0$. Once the thin quote cancels or fills, mid-price reverts back to $FV_t$.
- **Caveat**: OBI predicts **reversion of temporary quote asymmetry** rather than permanent directional drift in $FV_t$. In `TOMATOES` (Round 0), where the underlying fair value diffuses as a random walk, OBI correlation decays monotonically across horizons ($r = 0.34 \to 0.27 \to 0.22$).

### C. Trade Execution Location
Joining public trade prints against contemporaneous L1 quotes across all 5 ingested Round 0–1 days (`4,199` total prints) shows that **99.98%** (`4,198` of `4,199` two-sided prints) execute directly at `bid_price_1` or `ask_price_1`, with only `1` print inside the spread.
