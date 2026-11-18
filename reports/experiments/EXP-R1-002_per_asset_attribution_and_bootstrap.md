# Experiment EXP-R1-002: Bot-Wall Noise Reduction, Per-Asset Attribution & Block-Bootstrap Uncertainty

- **Hypothesis**:
  1. Anchoring fair value on max-volume resting bot walls (`_popular_wall_mid`) strictly reduces high-frequency quote jitter variance relative to L1 mid-price.
  2. Refined `Round1Submission` generates balanced alpha across *both* Round 1 instruments (`ASH_COATED_OSMIUM` and `INTARIAN_PEPPER_ROOT`) rather than relying on a single directional windfall.
  3. Out-of-sample `Day 0` performance remains statistically robust under serial-correlation-preserving circular block-bootstrap resampling.
- **Data Splits**:
  - Variance comparison: Round 1 `Day -2` & `Day -1` (IS).
  - Attribution & bootstrap: Round 1 `Day 0` (held-out OOS, `queue_aware` matching, assumed $Q_{\max} = 20$).

---

## 1. Fair-Value Noise Attenuation (IS `Day -2` & `Day -1`)
Comparing step-to-step differences of two-sided L1 mid-price ($\Delta P_{\text{L1}}$) against resting bot-wall midpoint ($\Delta P_{\text{wall}}$):

| Day | Instrument | $\text{Std}(\Delta P_{\text{L1}})$ | $\text{ACF}_1(\Delta P_{\text{L1}})$ | $\text{Std}(\Delta P_{\text{wall}})$ | $\text{ACF}_1(\Delta P_{\text{wall}})$ | Std Reduction |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Day -2 | `ASH_COATED_OSMIUM` | 1.9113 | $-0.5055$ | **1.1724** | $-0.4589$ | **$-38.7\%$** |
| Day -2 | `INTARIAN_PEPPER_ROOT` | 1.5782 | $-0.4928$ | **1.0906** | $-0.5079$ | **$-30.9\%$** |
| Day -1 | `ASH_COATED_OSMIUM` | 1.9216 | $-0.4868$ | **1.1521** | $-0.4573$ | **$-40.0\%$** |
| Day -1 | `INTARIAN_PEPPER_ROOT` | 1.7761 | $-0.4911$ | **1.1628** | $-0.4923$ | **$-34.5\%$** |

Filtering thin inside-spread quotes eliminates 31–40% of high-frequency step-size noise standard deviation (roughly 52–64% of variance) before any EMA smoothing is applied.

---

## 2. Out-of-Sample Per-Asset PnL & Execution Attribution (`Day 0`, `queue_aware`)
| Instrument | Simulated PnL | Share of Total | Fills (Maker / Taker) | Ending Inventory |
| :--- | :--- | :--- | :--- | :--- |
| `ASH_COATED_OSMIUM` | **+11,440.00** | 51.6% | 528 (277 / 251) | +13 |
| `INTARIAN_PEPPER_ROOT` | **+10,717.00** | 48.4% | 475 (178 / 297) | 0 |
| **Combined Portfolio** | **+22,157.00** | **100.0%** | **1,003 (455 / 548)** | — |

Alpha is evenly split (`51.6%` vs `48.4%`) across mean-reverting and linearly drifting regimes, with `INTARIAN_PEPPER_ROOT` closing completely flat (`end_pos = 0`).

---

## 3. Effective Trials ($N_{\text{eff}}$) & Block-Bootstrap Confidence Intervals
- **In-Sample 25-Trial Correlation Rank**: $N_{\text{eff}} = 1.11$ (confirming smooth grid coherence across `EXP-R1-001`).
- **OOS `Day 0` Circular Block Bootstrap** (`block_size = 100` ticks, $B = 1,000$ resamples, `seed = 42`):
  - **Annualized Sharpe**: Mean `1.190`, **95% CI `[1.046, 1.329]`**
  - **Total PnL**: Mean `22,140.8`, **95% CI `[19,772.5, 24,425.5]`**

## Conclusion
Accepted. Empirical attribution confirms balanced dual-asset edge and tight out-of-sample bootstrap confidence bounds.
