# Quantitative Research: Cointegration, Basket Invariants & Execution Horizon

Cross-asset strategies only earn durable edge in short historical samples when statistical co-movement reflects a structural accounting constraint rather than transient sample correlation. This note documents how PCA eigendecomposition distinguishes genuine cointegration from unstable factor exposure in Round 5, and why execution horizon must match the half-life of the spread.

## 1. Multivariate Cointegration & PCA Condition Ratios

Let $P_t = (P_{1, t}, \dots, P_{K, t})^\top$ denote the contemporaneous two-sided mid-price vector of $K$ related instruments. Even when each individual leg follows a unit-root random walk $I(1)$, a linear combination $z_t = \mathbf{w}^\top P_t$ can be stationary $I(0)$ when an underlying synthetic pricing rule constrains the basket sum or relative level.

In [`cross_asset.py`](file:///c:/Users/pierr/Desktop/imc-prosperity-4-toolkit-writeup/src/prosperity_toolkit/analysis/cross_asset.py), `fit_cointegrating_basket` decomposes the sample level covariance matrix $\hat{\Sigma}_P = V \Lambda V^\top$ with eigenvalues $\lambda_1 \ge \lambda_2 \ge \dots \ge \lambda_K \ge 0$:
$$\mathbf{w}^* = \arg\min_{\|\mathbf{w}\|_2 = 1} \mathbf{w}^\top \hat{\Sigma}_P \mathbf{w} = \mathbf{v}_K, \qquad \kappa = \frac{\lambda_1}{\lambda_K}$$
In practice, we treat two empirical thresholds as non-negotiable prior to trading any multi-leg spread:
1. A sharp **spectral condition ratio** ($\kappa \gg 10^2$) alongside weight stability across calendar days (no rotation in $\mathbf{v}_K$).
2. Significant **Augmented Dickey-Fuller rejection** ($t < -2.863$ at 5%) on $z_t$ with a clear discrete AR(1) reversion rate $\theta = 1 - \hat{\phi}_1$ and half-life $\tau_{1/2} = -\ln 2 / \ln \hat{\phi}_1$.

## 2. Empirical Structures in Round 5 (`r5_baskets_summary.csv`)

Testing all ten Round 5 categories strictly on In-Sample (`Day 2` & `Day 3`) before held-out OOS (`Day 4`) reveals eight decoupled random-walk clusters (`max |r| <= 0.0294`) and **two** co-moving groups whose stability differs fundamentally ([`r5_baskets_summary.csv`](file:///c:/Users/pierr/Desktop/imc-prosperity-4-toolkit-writeup/reports/tables/r5_baskets_summary.csv)):

| Basket / Pair Structure | Split | Sum Mean | Residual Std | `ADF t` | Half-Life | Empirical Regime Diagnosis |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| **`Pebbles` (`XS+S+M+L+XL`)** | IS `Day 2` / `3` | `49,999.91` / `.97` | `2.82` / `2.76` | `-71.14` / `-71.24` | `0.18` / `0.12` t | **Exact structural invariant** (`50,000`, $\kappa > 1.66 \times 10^6$) |
| **`Pebbles` (`XS+S+M+L+XL`)** | **OOS `Day 4`** | **`49,999.94`** | **`2.82`** | **`-70.16`** | **`0.16` t** | Identical uniform weights $[1,1,1,1,1]/\sqrt{5}$ |
| **`Snackpack Choc + Van`** | IS `Day 2` / `3` | `20,025.04` / `19,926.89` | `42.48` / `31.60` | `-2.04` / `-2.80` | `375` / `197` t | Shifting daily equilibrium (`-98.2` step shift across days) |
| **`Snackpack Choc + Van`** | **OOS `Day 4`** | **`19,870.09`** | `48.22` | `-1.17` | `527` t | High diff corr (`r = -0.912`); requires slow rolling `K_day` |
| **`Snackpack Pis/Straw/Rasp`** | IS `Day 2` | `16,746.18` | `55.33` | `-1.24` | `806` t | Factor weights `[0.493, 0.418, 0.763]` |
| **`Snackpack Pis/Straw/Rasp`** | **OOS `Day 4`** | `14,929.18` | `44.06` | `-2.47` | `383` t | **Rejected**: eigenvector rotated to `[0.776, 0.135, 0.616]` |

### Why `Snackpack Pis/Straw/Rasp` Fails Out-of-Sample Inclusion
Even though `SNACKPACK_PISTACHIO`, `STRAWBERRY`, and `RASPBERRY` exhibit `0.927` IS (`0.918` OOS) pairwise tick-difference correlation, their minimum-variance eigenvector changes sharply from `[0.493, 0.418, 0.763]` on `Day 2` to `[0.776, 0.135, 0.616]` on `Day 4`. Hardcoding a 3-leg hedge ratio off two days of prices is fragile cointegration overfitting; excluding that triplet from [`traders/round5/submission.py`](file:///c:/Users/pierr/Desktop/imc-prosperity-4-toolkit-writeup/traders/round5/submission.py) protects capital without losing true spread capture.

### Why `Pebbles` Requires Atomic IOC Execution Rather Than Passive Fair-Value Shifting
In our initial Round 5 passive implementation, shifting passive resting quotes on `PEBBLES_*` toward $\hat{P}_i = 50{,}000 - \sum_{j \ne i} \text{wall\_mid}_j$ degraded performance compared to ignoring the sum invariant altogether (`PM-005`). Why? With an empirical AR(1) half-life of `0.16` ticks (`88%` decay per simulation step!), any `±15`-tick discrepancy observed at timestamp $t$ comes from transient resting depth jitter on one leg that snaps back **before** a passive quote submitted for timestamp $t + 100$ can collect flow—leaving only skewed resting orders that adverse-select against genuine synchronized pulse moves.

Decoupling the two horizons resolves the tension cleanly in [`traders/round5/submission.py`](file:///c:/Users/pierr/Desktop/imc-prosperity-4-toolkit-writeup/traders/round5/submission.py): passive MM quotes stay anchored on each leg's unbiased `wall_mid`, while an independent **atomic cross-taking rule** lifts asks (`best_ask <= peb_imp - TAKE_EDGE - PEBBLES_TAKE_BUFFER`) and hits bids immediately whenever `peb_full` confirms an instantaneous multi-leg discount (`> 3` ticks).

## 3. Spatial / Conversion Arbitrage Schema Readiness

Although [`datamodel.py`](file:///c:/Users/pierr/Desktop/imc-prosperity-4-toolkit-writeup/traders/datamodel.py) and `prosperity_toolkit.data.schemas` implement full `ConversionObservation` support (`bidPrice`, `askPrice`, `transportFees`, `exportTariff`, `importTariff`, `sugarPrice`, `sunlightIndex`):
$$\Pi_{\text{import}} = P_{\text{local bid}} - (P_{\text{foreign ask}} + c_{\text{trans}} + \tau_{\text{imp}}), \qquad \Pi_{\text{export}} = (P_{\text{foreign bid}} - c_{\text{trans}} - \tau_{\text{exp}}) - P_{\text{local ask}}$$
auditing all `34` historical CSVs verifies **zero `observations_round_*.csv` feeds in Prosperity 4 Rounds 0–5**. The toolkit retains full conversion-arbitrage parity math at the unit-test level while focusing live submission capital on observed domestic book invariants.

