# Final Round & Multi-Round Architecture Synthesis (Tutorial – Round 5)

## 1. Cross-Round Structural Progression

Across Tutorial/Round 1 through Round 5, **IMC Prosperity 4** deliberately escalated both the statistical complexity of price processes and the portfolio/risk-limit geometry imposed on [`Trader.run`](file:///c:/Users/pierr/Desktop/imc-prosperity-4-toolkit-writeup/src/prosperity_toolkit/competition/datamodel.py):

| Round | Active Universe | Position Limit $Q_{\max}$ | Core Alpha / Hedging Thesis | Validated Bot Module | Manual Challenge |
| :--- | :--- | :---: | :--- | :--- | :--- |
| **Tutorial & Round 1** | `ASH_COATED_OSMIUM` (OU stationary), `INTARIAN_PEPPER_ROOT` (linear trend) | `20` *(stressed)* | Bot-wall midpoint filtering ($\Delta P$ std `-30.9%` to `-40.0%`), affine drift tracker, penny-joining inside wide walls | [`traders/round1/submission.py`](file:///c:/Users/pierr/Desktop/imc-prosperity-4-toolkit-writeup/traders/round1/submission.py) | *An Intarian Welcome* (`Flax 30x65`, `Mushroom 20x10`) |
| **Round 2** | `ASH_COATED_OSMIUM`, `INTARIAN_PEPPER_ROOT` (`+3x` depth/scale regime) | `80` | Scaled inventory skew (`0.75`), wider minimum half-spread (`3.5`), `+25%` MAF liquidity auction valuation | [`traders/round2/submission.py`](file:///c:/Users/pierr/Desktop/imc-prosperity-4-toolkit-writeup/traders/round2/submission.py) | *Invest & Expand* (`Research 15% / Scale 43% / Speed 42%`) |
| **Round 3** | `HYDROGEL_PACK`, `VELVETFRUIT_EXTRACT`, `VEV_4000..6500` (`10` calls) | `200` / `300` | Day-invariant total implied volatility ($v_K = \sigma_K \sqrt{\tau}$), `HEDGE_BAND = 10` spot delta hedging, deep-ITM conversion | [`traders/round3/submission.py`](file:///c:/Users/pierr/Desktop/imc-prosperity-4-toolkit-writeup/traders/round3/submission.py) | *Celestial Gardeners' Guild* (`Bid 1 = 775, Bid 2 = 880`) |
| **Round 4** | Same `12` instruments with live `buyer` / `seller` counterparty telemetry | `200` / `300` | Counterparty flow classification (`Mark 67` 100%-buyer `+1.97` jump signal on `VELVETFRUIT_EXTRACT`, `M67_BUMP=0.5`, `MM_EDGE=5.5`) | [`traders/round4/submission.py`](file:///c:/Users/pierr/Desktop/imc-prosperity-4-toolkit-writeup/traders/round4/submission.py) | *Vanilla Just Isn't Exotic Enough* (`CO -15, BP -50, KO +198, C15 +5, P15 +21`) |
| **Round 5** | **`50` brand-new spot assets** (`10` categories $\times$ `5`, blank counterparty IDs) | **`10`** (`max_gross = 500`) | Zero-lag bot-wall valuation (`ef=0.18, sk=1.25`), `QUOTE_CLIP = 10`, adaptive `Robots`/`Microchips` `VOL_GUARD`, atomic `PEBBLES = 50,000` IOC crossing & rolling `SNACKPACK` $K_{\text{day}}$ | [`traders/round5/submission.py`](file:///c:/Users/pierr/Desktop/imc-prosperity-4-toolkit-writeup/traders/round5/submission.py) | *Extra! Extra!* (`Thermalite +35%, Sulfur +29%, Ashes -23%, Pyroflex -10%, Scoria +3%`) |

## 2. Algorithmic Portfolio Summary (`queue_aware` Held-Out Out-of-Sample Replay)

Every round was calibrated strictly on **In-Sample (IS)** days (`Day -2/-1` for R1, `Day -1/0` for R2, `Day 0/1` for R3, `Day 1/2` for R4, `Day 2/3` for R5), gated through `CSCV / PBO (< 0.15)` and `Deflated Sharpe Ratio (>= 0.95)`, and evaluated single-pass on the held-out **Out-of-Sample (OOS)** day under strict resting-queue modeling:

| Round | Held-Out OOS Day | Baseline Benchmark (`queue_aware`) | Submission OOS PnL | OOS `Sharpe_252` (95% Boot CI) | OOS Max Drawdown | `CSCV PBO` | `DSR` | Mean Latency / Tick |
| :---: | :---: | :--- | ---: | :--- | ---: | :---: | :---: | ---: |
| **R1** | `Day 0` | `SymmetricMM` (`10,825.00`, DD `886.0`) | **`+22,157.00`** | `1.1894` `[1.046, 1.329]` | **`267.00`** | `0.0860` | `1.0000` | `0.0340 ms` |
| **R2** | `Day 1` | `SymmetricMM_80` (`-20,294.50`, DD `21,729.5`) | **`+27,463.00`** | `1.3972` `[1.2314, 1.5823]` | **`419.50`** | `0.0000` | `1.0000` | `0.0406 ms` |
| **R3** | `Day 2` | `OptionsVolatilityContract` (`-7,604.00`, DD `8,719.0`) | **`+7,525.50`** | `0.2276` `[0.0097, 0.4392]` | **`1,936.00`** | `0.0000` | `0.9921` | `0.1872 ms` |
| **R4** | `Day 3` | `Round3Ungated` (`+12,048.00`, DD `3,250.5`, SR `0.3488`) | **`+11,741.00`** | **`0.3613`** `[0.0932, 0.6302]` | **`2,901.00`** | `0.0571` | `0.9975` | `0.1871 ms` |
| **R5** | `Day 4` | `EmaSymmetricMM_All50` (`+114,851.00`, DD `29,130.0`, SR `0.3260`) | **`+123,173.00`** | **`0.8109`** `[0.5789, 1.0627]` | **`6,205.50`** | `0.1000` | `1.0000` | `0.6920 ms` |
| **Total** | — | — | **`+192,059.50`** | — | — | `<= 0.100` | `>= 0.992` | `<= 0.6920 ms` |

Notice how calibrating strictly to real single-day historical books establishes concrete empirical ceilings (`R1 D0 ~21.6k`, `R2 D1 ~24.1k`, `R3 D2 ~14.3k`, `R4 D3 ~15.4k`, `R5 D4 ~139.4k` in passive public-trade spread capture). Our `Round5Submission` captures **`88.3%`** of the single-day historical public-trade spread ceiling (`+123,173.00` vs `139,448.5`) while staying strictly sub-millisecond (`0.692 ms/tick` across all `50` symbols). All algorithmic figures reflect single-day `queue_aware` historical replays (whereas multi-day live exchange runs aggregate multiple session horizons and interactive counterparty fills).

## 3. Structural Principles That Transferred Across Every Round

1. **Structural Valuation Anchors Beat Tick-by-Tick Price Chasing**:
   - In Rounds 1–2, replacing L1 microprice with maximum-volume resting bot-wall midpoints removed `31%–40%` of step volatility noise before quoting.
   - In Round 5 (`50` high-vol random walks under tight `±10` limits), removing lagged EMA filtering cut out-of-sample portfolio drawdown **`-78.7%`** (`29,130.00 -> 6,205.50`) and lifted annualized Sharpe **`2.49x`** (`0.3260 -> 0.8109`).
2. **Model Calibration Must Respect Scale-Free & Regime Invariants**:
   - Hardcoding Black-Scholes `T = 5` days in Round 3 produced `-7,604.00` OOS loss; solving for **total implied volatility** $v_K = \sigma_K \sqrt{\tau}$ eliminated expiry-calendar misspecification immediately (`+7,525.50` OOS).
   - Hardcoding a static basket constant $K$ for `SNACKPACK_CHOCOLATE + VANILLA` fails when $K_{\text{day}}$ shifts `-98.2` ticks between `Day 2` and `Day 3`; tracking $K_{\text{day}}$ with an ultra-slow EMA inside `traderData` adapts automatically across sessions.
3. **Horizon Matching & Adaptive Risk Guarding Determine Realized Alpha**:
   - In Round 5, shifting passive resting quotes against `Pebbles`' `0.16`-tick half-life constant-sum invariant bled alpha into stale quotes; decoupling **atomic IOC cross-taking** from unbiased resting market making preserved full passive edge (`Pebbles +15,469.00` OOS).
   - Simultaneously, dynamically gating `Robots` and `Microchips` via rolling step-volatility (`spread >= 0.50 * vol_ema`) plus `LOW_RATIO_EDGE_FRAC = 0.35` allowed positive capture on `Microchips` (`+7,124.00`) and `Robots` (`+1,240.00`) even when `ROBOT_DISHES` volatility surged `2.8x` on `Day 4`.
4. **Overfitting Controls Actively Reject Fragile Curves**:
   - An aggressive Round 4 spot-chasing parameterization (`s_alpha = 0.85`) failed `CSCV` (`PBO = 0.9714 > 0.15`, `DSR = 0.9390 < 0.95`) and was vetoed before touching `Day 3`, keeping `Round4Submission` pinned cleanly to its stable `(m67_bump=0.5, mm_edge=5.5)` ridge (`+11,741.00` OOS).
5. **Out-of-Exchange Manual Optimization Uses Matching Decision Discipline**:
   - Across the five manual rounds ([`MANUAL_CHALLENGES.md`](file:///c:/Users/pierr/Desktop/imc-prosperity-4-toolkit-writeup/docs/manual/MANUAL_CHALLENGES.md)), uncertain-demand auction shading (R1), Level-3 Cognitive Hierarchy equilibrium allocation (`Research 14.71% / Scale 43.29% / Speed 42.0%` in R2), Bayesian two-bid screening (`775, 880` in R3), discrete `6h` Broadie–Glasserman–Kou exotics & risk-minimized hedged portfolios (`sigma_ann = 251%`, R4), and exact variance-adjusted KKT Ignith portfolios (R5) apply identical risk-adjusted first principles under explicit contemporaneous priors.

For full cross-round conclusions, comparative tearsheets, and manual-challenge breakdowns, proceed to [FINAL_WRITEUP.md](file:///c:/Users/pierr/Desktop/imc-prosperity-4-toolkit-writeup/reports/FINAL_WRITEUP.md) and [dashboard.html](file:///c:/Users/pierr/Desktop/imc-prosperity-4-toolkit-writeup/reports/dashboard.html).
