# Market Microstructure Across IMC Prosperity 4 (Rounds 1–5)

Quantitative edge in IMC Prosperity 4 originates in classifying order-book depth structure, return autocorrelation, counterparty toxicity, and cross-asset trade synchronization prior to designing quoting logic. Every property below was audited strictly In-Sample (`IS`) before confirmation on held-out Out-of-Sample (`OOS`) sessions ([`prosperity4_manifest.json`](file:///c:/Users/pierr/Desktop/imc-prosperity-4-toolkit-writeup/data/manifests/prosperity4_manifest.json)).

## 1. Cross-Round Microstructure Taxonomy

| Round | Instruments | Two-Sided Depth | L1 Return $\text{ACF}_1$ | Step Noise vs Fundamental Process | Key Structural Signal |
| :--- | :--- | :---: | :---: | :--- | :--- |
| **R1–R2** | `ASH_COATED_OSMIUM` | `~92.3%` ticks (`16`-tick median wall) | `-0.469` to `-0.489` | Mean-reverting OU ($\theta \approx 0.07–0.13$, `hl = 5.4–10.5` ticks) | Rest wall mid reduces $\sigma(\Delta P)$ by `38.7–40.0%`; `OBI` correlates `+0.58–0.59` with `h=1` mid move |
| **R1–R2** | `INTARIAN_PEPPER_ROOT` | `~92.4%` ticks (`13–15`-tick spread) | `-0.492` to `-0.496` | Deterministic linear slope `+0.108/tick` (`R^2 = 1.0`) + bid-ask bounce | Affine trend tracking prevents passive inventory lockup; `+25%` MAF arrival boosts MC EV `+33.4%` |
| **R3–R4** | `HYDROGEL_PACK`, `VELVETFRUIT_EXTRACT`, `VEV_4000..6500` | Continuous two-sided quotes | Weak OU (`hl ≈ 189–206` ticks) | `HYDROGEL_PACK` wide spread (`15.7` ticks); `VEV_5200..5500` IV `23–24%` (`90–100%` seller-initiated) | Day-invariant total vol $v_K = \sigma_K \sqrt{\tau}$; R4 reveals **`Mark 67`** (`+1.97` perm buyer) & **`Mark 49`** (`+1.90` perm seller) |
| **R5** | `50` Spot Goods (`10` categories $\times$ `5`) | Dense L1–L3 levels | Near-zero (`RW` steps $\sigma_{\Delta P} = 10–30$) | `42` independent random walks + `2` invariant categories (`Pebbles`, `Snackpacks`); **no counterparty IDs** | All trades arrive in **three shared Poisson pulse clusters** (`Group V` `40` assets, `P` `5`, `M` `5`) with `100%` identical side & qty |

## 2. Counterparty Toxicity & Stratified Mark-Outs (Round 4)

Round 4 populated explicit trader IDs on public `market_trades` for `HYDROGEL_PACK` and `VELVETFRUIT_EXTRACT`. A naive pooled mark-out across all symbols falsely ranks `Mark 14` (`+5.83`) ahead of `Mark 67` simply because `Mark 14` happens to lift wider-spread `HYDROGEL_PACK` and `VEV_4000` quotes. Conditioning strictly inside `VELVETFRUIT_EXTRACT` isolates genuine information from product-mix bias ([`r4_counterparty_velvet_midmoves.csv`](file:///c:/Users/pierr/Desktop/imc-prosperity-4-toolkit-writeup/reports/tables/r4_counterparty_velvet_midmoves.csv)):

| Counterparty (`VELVETFRUIT_EXTRACT`) | Role / Count (`IS`) | `h = +1` Tick Move | `h = +5` Tick Move | `h = +20` Tick Move | `h = +50` Tick Move | Classification |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **`Mark 67`** | `100%` buyer (`n = 165`) | **`+1.970`** | `+1.945` | `+1.845` | **`+1.918`** | **Informed toxic buyer** (permanent step shift) |
| **`Mark 49`** | `100%` seller (`n = 105`) | **`+1.900`** | `+1.819` | `+1.795` | **`+1.986`** | **Passive liquidity seller** (absorbed by buyers pushing mid up) |
| **`Mark 55`** | Balanced (`598` buy / `600` sell) | `+0.010` / `-0.036` | `+0.199` / `+0.052` | `+0.409` / `-0.106` | `+0.387` / `-0.394` | Noise / liquidity trader (near-zero immediate impact) |
| **`Mark 14`** | `100%` buyer (`n = 316`) | `-0.187` | `-0.033` | `-0.237` | `-0.530` | Uninformed / mean-reverting flow |

Notice why the bump size requires discipline: on IS validation grids, moderate bumping (`M67_BUMP = 0.5`, decaying `0.80x` per tick) flips `VELVETFRUIT_EXTRACT` OOS cleanly profitable while cutting portfolio drawdown (`2,901.0` vs `3,250.5` ungated), whereas over-aggressive spot bumping (`m67_bump >= 1.5` or aggressive crossing) lifts adverse selection (`PBO > 0.15` rejection). Separately, `Mark 22` dominates seller-initiated taker prints across OTM calls (`VEV_5200..6500`, `90%–100%` seller-initiated), corroborating excess option premium decay across Days `0 -> 3`.

## 3. Hidden Multi-Asset Generative Structure (Round 5)

Synchronized arrival analysis (`detect_trade_pulses`, [`r5_category_pca_and_pulses.csv`](file:///c:/Users/pierr/Desktop/imc-prosperity-4-toolkit-writeup/reports/tables/r5_category_pca_and_pulses.csv)) and eigen-decomposition uncovered the hidden generator behind all `50` Round 5 goods:

1. **Zero Independent Noise Trades**: Every public print belongs to one of three synchronized Poisson clusters—a **`40`-asset Mega-Cluster (`Group V`, `484` IS / `249` OOS pulses, $\lambda \approx 0.0242–0.0249$)**, **`Pebbles` (`Group P`, `442` / `202`)**, and **`Microchips` (`Group M`, `368` / `201`)**—with **`100.0%` identical trade side and quantity** across every active asset on each pulse timestamp. Because 40 books hit simultaneously in one direction, portfolio correlation matters during extreme ticks even when fundamental prices are uncorrelated.
2. **Co-Movement vs Independence**: Despite firing on identical pulse timestamps, pairwise return differences across the `8` categories in `Group V` are mutually uncorrelated (`max |corr| <= 0.0294`) *except* **`Snackpacks`** (`max |corr| = 0.9268` IS / `0.9176` OOS; `CHOCOLATE` vs `VANILLA` `-0.918` IS / `-0.912` OOS) and **`Pebbles`** (`condition ratio > 1.66 x 10^6`, constant `50,000` sum across all `5` pebbles with `0.16`-tick half-life OOS).
3. **Volatility Regime Non-Stationarity (`Day 4`)**: Multi-day linear drifts detected on `Day 2–3` (`MICROCHIP_SQUARE +3,134.4`, `SLEEP_POD_SUEDE +1,490.2`) reversed sign completely OOS (`-1,315.8`, `-367.9`), while `ROBOT_DISHES` step volatility surged `2.8x` (`9.83 -> 27.48`). Rather than blindly hard-banning `Robots` and `Microchips` or chasing transient trends, adaptive spread-to-step-volatility filtering (`spread >= 0.50 * vol_ema`) plus zero-lag `_popular_wall_mid` preserves positive capture when spreads compensate risk while standing aside during volatility spikes.
