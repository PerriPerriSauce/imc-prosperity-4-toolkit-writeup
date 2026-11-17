# Quantitative Research: Fair Value Estimation

## 1. Mathematical Formulation

Let $S_t$ denote the observable two-sided mid-price and $FV_t$ denote the unobservable continuous fair value.

### A. Ornstein-Uhlenbeck (OU) Mean-Reverting Model
In continuous time, mean-reverting fair value dynamics follow:
$$d FV_t = \theta (\mu - FV_t)\,dt + \sigma\,d W_t$$
where $\theta > 0$ is mean-reversion speed, $\mu$ is long-term equilibrium, and $\sigma > 0$ is diffusion volatility. The half-life is $t_{1/2} = \frac{\ln 2}{\theta}$.

Discretizing at uniform step $\Delta t$ yields an exact AR(1) representation $S_t = a + b S_{t-1} + \eta_t$:
$$\hat{\theta} = -\frac{\ln \hat{b}}{\Delta t}, \quad \hat{\mu} = \frac{\hat{a}}{1 - \hat{b}}, \quad \hat{\sigma} = \hat{\sigma}_\eta \sqrt{\frac{-2\ln \hat{b}}{\Delta t (1 - \hat{b}^2)}}$$

### B. Deterministic Linear Drift Model
For assets with deterministic drift $FV_t = \alpha + \beta t + \varepsilon_t$:
$$\hat{\beta} = \frac{\text{Cov}(t, S_t)}{\text{Var}(t)}, \quad \hat{\alpha} = \bar{S} - \hat{\beta}\bar{t}$$

---

## 2. Server Fair Value Extraction

In simulated exchange environments with deterministic or bot-driven quoting, the server's fair value can be extracted empirically by evaluating the mark-to-market PnL of holding 1 unit:
$$FV_t = \text{PnL}_t^{\text{hold-1}} - \text{PnL}_{t-1}^{\text{hold-1}} + FV_{t-1}$$
*(Note: No live hold-1 portal submissions have been executed in this repository; all parameters below are estimated strictly from historical CSV order books.)*

---

## 3. Empirical Parameter Estimates (Round 0 & Round 1)

| Instrument | Round | Regime Classification | Calibration Split (In-Sample) | OOS Verification |
| :--- | :--- | :--- | :--- | :--- |
| `EMERALDS` | R0 | Constant FV + quote jitter | Day -2: $\hat{\mu}=10000.00$, ADF $t=-58.68$ | Day -1: $\hat{\mu}=10000.00$, ADF $t=-56.87$ |
| `TOMATOES` | R0 | Near-unit-root random walk | Day -2: $\hat{b}=0.9914$, ADF $t=-3.32$ | Day -1: $\hat{b}=0.9957$, ADF $t=-2.57$ (non-stationary) |
| `ASH_COATED_OSMIUM` | R1 | Stationary OU ($\mu \approx 10000$) | Day -2/-1: $\hat{\theta} \in [0.085, 0.135]$, $t_{1/2} \in [5.1, 8.1]$ | Day 0: $\hat{\theta}=0.073$, $\hat{\mu}=10001.63$, $t_{1/2}=9.47$ |
| `INTARIAN_PEPPER_ROOT` | R1 | Linear drift $+0.10$/step + noise | Day -2/-1: slope $= +0.1000$/step ($R^2=1.0000$) | Day 0: slope $= +0.1000$/step ($R^2=1.0000$), resid std $= 1.34$ |

### Model Assumptions & Limitations
- **Bid-Ask / Microstructure Attenuation**: Measuring AR(1) directly on noisy two-sided mid-prices biases $\hat{b}$ downward (attenuation bias) relative to the latent $FV_t$, especially when transient quote noise $\sigma_\varepsilon$ is large compared to innovation volatility $\sigma_{FV}$.
- **Structural Regime Shift Risk**: Although `INTARIAN_PEPPER_ROOT` exhibited exact $+0.10$/step drift across all 3 observed days (`Day -2` to `Day 0`), extrapolating linear drift into future rounds without online drift-change detection carries severe regime-shift risk.
