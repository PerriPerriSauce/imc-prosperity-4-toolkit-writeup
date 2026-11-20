# Quantitative Research: Cointegration, Basket Invariants & Predictive Lead-Lag

Cross-asset signals only justify strategy complexity when statistical invariants survive transaction costs (bid-ask spreads) and structural eigenvectors remain stable out-of-sample. This note contrasts three structures tested in Round 5 (`IS Days 2–3`, `OOS Day 4`) and explains why **`Pebbles` arbitrage and `Snackpack` triplets were rejected** in favor of discrete **`MICROCHIP_CIRCLE` causal lead-lag**.

## 1. Multivariate Cointegration & PCA Condition Ratios

Let $P_t = (P_{1, t}, \dots, P_{K, t})^\top$ denote contemporaneous two-sided mid-prices. In [`cross_asset.py`](../../src/prosperity_toolkit/analysis/cross_asset.py), `fit_cointegrating_basket` decomposes level covariance $\hat{\Sigma}_P = V \Lambda V^\top$:
$$\mathbf{w}^* = \arg\min_{\|\mathbf{w}\|_2 = 1} \mathbf{w}^\top \hat{\Sigma}_P \mathbf{w} = \mathbf{v}_K, \qquad \kappa = \frac{\lambda_1}{\lambda_K}$$
Every candidate structure faces two gates before production allocation: (1) stable eigenvector weights across IS days, and (2) residual dispersion sufficiently wider than combined multi-leg execution spreads.

## 2. Empirical Structures in Round 5 (`r5_baskets_summary.csv`, `r5_microchips_leadlag.csv`)

| Structure | Split | Mean | Residual Std | `ADF t` | Half-Life | Research Disposition |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| **`Pebbles` (`XS+S+M+L+XL`)** | IS `Day 2` / `3` | `49,999.91` / `.97` | `2.816` / `2.758` | `-71.14` / `-71.24` | `0.18` / `0.12` t | **Pruned**: std (`2.82`) sits completely inside `12–14` tick 5-leg touch spreads |
| **`Pebbles` (`XS+S+M+L+XL`)** | OOS `Day 4` | `49,999.94` | `2.821` | `-70.16` | `0.16` t | Confirmed book-sum invariant (`49,981.5..50,016.0`), zero crossing alpha |
| **`Snackpack Choc + Van`** | IS `Day 2` / `3` | `20,025.04` / `19,926.89` | `42.48` / `31.60` | `-2.04` / `-2.80` | `375` / `197` t | **Pruned**: daily equilibrium shifts `-98.2` ticks across days |
| **`Snackpack Choc + Van`** | OOS `Day 4` | `19,870.09` | `48.22` | `-1.17` | `527` t | High diff corr (`-0.912`) is contemporaneous, non-predictive |
| **`Snackpack Pis/Straw/Rasp`** | IS `Day 2` / OOS `Day 4` | `16,746` / `14,929` | `55.33` / `44.06` | `-1.24` / `-2.47` | `806` / `383` t | **Rejected**: eigenvector rotated `[0.493, 0.418, 0.763] -> [0.776, 0.135, 0.616]` |
| **`MICROCHIP_CIRCLE` Lead-Lag** | IS `Day 2–3` | `beta = 0.078–0.130` | Discrete lags | — | `50 / 100 / 150 / 200` t | **Promoted**: exact causal lag `OVAL (50), SQUARE (100), RECT (150), TRI (200)` |

### Why `Pebbles` Arbitrage Fails Execution Verification
Although `PEBBLES_XS + S + M + L + XL` satisfies $\sum P_i = 50{,}000 \pm 2.82$ (`ADF t = -70.16`, `0.16`-tick half-life), a `2.82`-tick basket standard deviation rarely clears the combined half-spreads across `12–14` tick markets (`min=49,981.5, max=50,016.0` represents single-side ask-wall noise rather than sweepable edge). Resting passive quotes biased toward implied values suffered adverse fills after snapback, while strict IOC cross-taking produced zero net fills—so `traders/round5/submission.py` cleanly prunes `Pebbles` cross-trading (`OOS +350.0` pure MM vs wasted complexity).

### Why `MICROCHIP_CIRCLE` Discrete Lead-Lag Works Out-of-Sample
Strictly on IS Days `2–3` ([`r5_microchips_leadlag.csv`](../../reports/tables/r5_microchips_leadlag.csv)), differenced `MICROCHIP_CIRCLE` returns predict downstream follower moves at exact discrete lags while neighboring lags (`±1` tick) stay near zero:
- `MICROCHIP_OVAL` (`lag = 50`): `r_d2 = 0.0494`, `r_d3 = 0.0533`, pooled $\hat{\beta} = 0.0781$.
- `MICROCHIP_SQUARE` (`lag = 100`): `r_d2 = 0.0450`, `r_d3 = 0.0723`, pooled $\hat{\beta} = 0.1296$.
- `MICROCHIP_RECTANGLE` (`lag = 150`): `r_d2 = 0.0553`, `r_d3 = 0.0682`, pooled $\hat{\beta} = 0.0907$.
- `MICROCHIP_TRIANGLE` (`lag = 200`): `r_d2 = 0.0470`, `r_d3 = 0.0750`, pooled $\hat{\beta} = 0.1025$.

Applying a single common multiplier `mc_beta = 0.16` in `traders/round5/submission.py` improves OOS PnL by **`+2,215.50`** (`+97,628.00` vs `+95,412.50` for `Round5NoLeadLag`, nearly doubling `Microchips` category PnL) while cutting `MaxDD` from `15,692.50` to `14,961.50`.

## 3. Spatial / Conversion Arbitrage Schema Readiness

Although [`datamodel.py`](../../traders/datamodel.py) and `prosperity_toolkit.data.schemas` implement full `ConversionObservation` support, auditing all `34` historical CSVs verifies zero `observations_round_*.csv` feeds in Prosperity 4 Rounds 0–5.
