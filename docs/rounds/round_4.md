# Round 4: Counterparty Flow Identification & Stratified Mark-Out Profiling

## 1. Round Context & Telemetry Evolution

Round 4 carried over the exact **12-product universe** from Round 3 (`HYDROGEL_PACK` [cap `200`], `VELVETFRUIT_EXTRACT` [cap `200`], `VEV_4000..6500` [cap `300` each]) across `Day 1`, `Day 2`, and fresh `Day 3`, while introducing a decisive structural revelation: **explicit counterparty identifiers (`buyer` and `seller`) in `trades_round_4_day_{1,2,3}.csv`**.

- **Historical File Structure Audit**:
  - `prices_round_4_day_1.csv` and `day_2.csv` share exact cryptographic SHA-256 parity with `prices_round_3_day_1.csv` and `day_2.csv`, whereas `trades_round_4_day_{1,2}.csv` replace empty `buyer`/`seller` columns with seven named market participants: `Mark 01`, `Mark 14`, `Mark 22`, `Mark 38`, `Mark 49`, `Mark 55`, and `Mark 67`.
  - `prices_round_4_day_3.csv` (`120,000` rows) and `trades_round_4_day_3.csv` (`1,541` trades) are preserved strictly as our **Held-Out Out-of-Sample (`OOS`) split** (`Day 1–2` = IS calibration).
- **Manual Challenge ("Vanilla Just Isn't Exotic Enough")**: Standalone pricing & portfolio selection across `12` Aether Crystal contracts (`GBM`, `sigma = 2.51`, `4` steps/day, discrete barrier knock-outs `AC_45_KO`, binaries `AC_40_BP`, and choosers `AC_50_CO`).

---

## 2. Counterparty Flow Profiling & The Confounding Trap

To classify which counterparties are passive market makers, random noise takers, forced flow dumpers, or informed alpha traders, [`scripts/eda_rounds2_to_5.py`](../../scripts/eda_rounds2_to_5.py) aggregates volume, initiator aggressiveness, and weighted execution mark-outs ($\text{dir} \cdot (M_{t+h} - P_{\text{trade}})$) across horizons $h \in \{1, 5, 20, 50\}$ ticks:

| Counterparty | Split | Trade Sides | Buy Qty | Sell Qty | Net Qty | Aggressive % | $h=1$ Mark-Out | $h=5$ Mark-Out | $h=20$ Mark-Out | $h=50$ Mark-Out |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **`Mark 01`** | IS / OOS | 1,123 / 720 | 3,689 / 2,364 | 986 / 389 | +2,703 / +1,975 | **0.0% / 0.0%** | +1.499 / +1.276 | +1.477 / +1.246 | +1.416 / +1.243 | +1.453 / +1.266 |
| **`Mark 14`** | IS / OOS | 1,432 / 740 | 2,958 / 1,552 | 2,790 / 1,418 | +168 / +134 | **0.0% / 0.0%** | **+5.832 / +5.581** | +5.852 / +5.434 | +5.822 / +5.271 | +5.836 / +5.461 |
| **`Mark 22`** | IS / OOS | 945 / 639 | 138 / 68 | 3,472 / 2,211 | **$-3,334$ / $-2,143$** | 88.9% / 93.3% | $-0.543$ / $-0.529$ | $-0.564$ / $-0.448$ | $-0.548$ / $-0.453$ | $-0.691$ / $-0.524$ |
| **`Mark 38`** | IS / OOS | 983 / 495 | 1,680 / 813 | 1,643 / 864 | +37 / $-51$ | **100.0% / 100.0%** | **$-8.464$ / $-8.175$** | $-8.521$ / $-7.980$ | $-8.668$ / $-7.897$ | $-8.865$ / $-8.473$ |
| **`Mark 49`** | IS / OOS | 83 / 39 | 78 / 37 | 742 / 329 | $-664$ / $-292$ | 2.4% / 0.0% | $-1.110$ / $-1.350$ | $-1.048$ / $-1.357$ | $-1.005$ / $-1.377$ | $-1.432$ / $-0.041$ |
| **`Mark 55`** | IS / OOS | 795 / 403 | 2,201 / 1,053 | 2,197 / 1,100 | +4 / $-47$ | **100.0% / 100.0%** | $-2.456$ / $-2.452$ | $-2.417$ / $-2.399$ | $-2.178$ / $-2.206$ | $-2.040$ / $-1.983$ |
| **`Mark 67`** | IS / OOS | 119 / 46 | **1,086 / 424** | **0 / 0** | **+1,086 / +424** | **100.0% / 97.8%** | **+1.167 / +1.416** | +1.196 / +1.171 | +1.012 / +1.065 | +1.624 / $-0.041$ |

*(Source: [`reports/tables/r4_counterparty_profiles.csv`](../../reports/tables/r4_counterparty_profiles.csv).)*

![Round 4 Counterparty Flow Volumes and Multi-Horizon Mark-Outs](../../reports/figures/r4_counterparty_markouts.png)

### Disentangling Instrument Mix from Genuine Information (`r4_counterparty_velvet_midmoves.csv`)

A naive observer looking solely at pooled mark-outs might mistake **`Mark 14`** (`+5.83`) for a superhuman directional predictor and underestimate **`Mark 67`** (`+1.17`). Symbol stratification reveals why that conclusion is backward:

| Counterparty | Trades on `VELVETFRUIT_EXTRACT` | Side | $\mathbb{E}[M_{t+1} - M_t]$ | $\mathbb{E}[M_{t+5} - M_t]$ | $\mathbb{E}[M_{t+20} - M_t]$ | $\mathbb{E}[M_{t+50} - M_t]$ | True Market Role |
| :--- | ---: | :--- | ---: | ---: | ---: | ---: | :--- |
| **`Mark 67`** | `165` | Buyer | **+1.970** | **+1.945** | **+1.845** | **+1.918** | **Informed Directional Taker** |
| **`Mark 49`** | `105` | Seller | **+1.900** | +1.819 | +1.795 | +1.986 | **Adversely Selected Passive Seller** |
| **`Mark 55`** | `598` / `600` | Buy / Sell | +0.010 / $-0.036$ | +0.199 / +0.052 | +0.409 / $-0.106$ | +0.387 / $-0.394$ | **Uninformed Two-Sided Noise Taker** |
| **`Mark 01`** | `260` | Buyer | +0.233 | +0.290 | +0.006 | $-0.135$ | **Passive Maker + Option Buyer** |
| **`Mark 14`** | `316` | Buyer | $-0.187$ | $-0.033$ | $-0.237$ | $-0.530$ | **Wide-Spread Passive Maker** |

*(Source: [`reports/tables/r4_counterparty_velvet_midmoves.csv`](../../reports/tables/r4_counterparty_velvet_midmoves.csv).)*

### Complete Botanical Ecosystem Reconstruction of Round 4 Counterparties
1. **`Mark 14` & `Mark 01` (Core Liquidity Providers, `0.0%` Aggressive)**:
   - `Mark 14` makes markets on wide-spread books (`HYDROGEL_PACK` `1,989`/`2,033`, `VEV_4000` `458`/`412`, `VELVETFRUIT_EXTRACT` `1,761`/`1,763`), collecting the full half-spread rather than forecasting price moves (note its actual `VELVETFRUIT_EXTRACT` mid-move is slightly negative `-0.187`). `Mark 01` makes `VELVETFRUIT_EXTRACT` and passively absorbs the structured option sales from `Mark 22`.
2. **`Mark 22` (The Structural Option Seller)**:
   - Aggressively hits bids across `VEV_5200..6500` (`5,093` contracts sold vs. `12` bought across `VEV_*`), driving the `90%–100%` seller-initiated flow discovered in Round 3. Posting inside `Mark 01`/`Mark 14`'s bids lets a competitor intercept `Mark 22` directly on overvalued strikes.
3. **`Mark 38` & `Mark 55` (Symmetrically Uninformed Takers, `100.0%` Aggressive)**:
   - `Mark 38` crosses `~8.5`-tick half-spreads evenly on `HYDROGEL_PACK` & `VEV_4000`; `Mark 55` crosses `~2.45`-tick half-spreads symmetrically on `VELVETFRUIT_EXTRACT` with `~0` subsequent mid-price drift. Both provide clean passive spread-capture flow.
4. **`Mark 67` vs. `Mark 49` (Pure Adverse-Selection Signal Pair)**:
   - Every single trade by `Mark 67` across all 3 days is an aggressive purchase (`1,510` contracts, `0` sells) in `VELVETFRUIT_EXTRACT` immediately followed by a permanent **`+1.97`-tick upward jump at `h = 1`**, persisting `+1.92` ticks out to `h = 50`. Conversely, `Mark 49` serves as the passive sell counterparty getting picked off right ahead of those upward jumps.

## 3. Hypotheses & Risk Controls

- **Counterparty-Gated Execution on `VELVETFRUIT_EXTRACT` (`Day 3` OOS)**: Detecting a `Mark 67` buy print on tick $t-1$ justifies temporarily lifting/skewing quotes upward and widening resting asks on tick $t$ to avoid adverse selection against the persistent `+1.97`-tick price jump, while testing whether moderate bumping beats aggressive spot chasing out-of-sample.
- **Late-Lifecycle `Day 3` Option Decay**: With `VEV_5300` stepping down from `48.89 -> 32.14` and `VEV_5400` falling to `8.50` by `Day 3`, day-invariant total implied volatility ($v_K = \sigma_K \sqrt{\tau}$) and slow smoothing must adapt cleanly without hardcoded strike or calendar offsets.

## 4. Counterparty Flow Gating, Plateau Alignment & OOS Evaluation (`Day 3`)

[`traders/round4/submission.py`](../../traders/round4/submission.py) extends Round 3's spot + total-volatility option hedging architecture with real-time counterparty trade inspection (`state.market_trades`):
- **`Mark 67` Adverse-Selection Defense**: Whenever a trade print on `VELVETFRUIT_EXTRACT` records `buyer == "Mark 67"`, the trader adds an exponentially decaying impulse (`M67_BUMP = 0.5`, decay `0.80x`/tick) to its effective spot valuation (`sfv_eff`), taking undervalued asks and widening passive asks by `+0.8 * m67_signal` to avoid selling into the informed jump.
- **`HYDROGEL_PACK` Plateau (`Day 1` & `Day 2` IS) & Overfit Rejection**: Sweeping `m67_bump in {0.5..2.0}` $\times$ `mm_edge in {2.5..5.5}` (`mm_skew = 0.08`) selects the stable boundary ridge `m67_bump = 0.5, mm_edge = 5.5` (`IS Sharpe_252 = 0.3725`, `3x3` local mean `0.3498`, std `0.0186`, `N_eff = 1.08`, **`CSCV PBO = 0.0571`**, **`DSR = 0.9975`**). Notably, an earlier aggressive spot-chasing parameterization (`s_alpha = 0.85` plus unconstrained near-ATM option crossing) was tested in-sample and explicitly **rejected** by our statistical validation gate (`PBO = 0.9714 > 0.15`, `DSR = 0.9390 < 0.95`), whereas aligning the submitted binary directly to the `(0.5, 5.5)` IS plateau eliminated excess crossing drag out-of-sample.

| Strategy | Fill Mode | IS PnL (`Day 1, 2`) | OOS PnL (`Day 3`) | OOS `Sharpe_252` | OOS Max DD | OOS Fills | Mean Latency |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| `NoOpBaseline` | `queue_aware` | 0.00 | 0.00 | 0.0000 | 0.00 | 0 | — |
| `Round3Ungated` *(m67=0, edge=4.5)* | `conservative` | 23,764.00 | 11,942.00 | 0.3462 | 3,214.50 | 755 | 0.2125 ms |
| `Round3Ungated` *(m67=0, edge=4.5)* | `queue_aware` | 23,998.50 | 12,048.00 | 0.3488 | 3,250.50 | 758 | 0.1933 ms |
| `Round3Ungated` *(m67=0, edge=4.5)* | `touch` | 28,480.00 | 12,284.50 | 0.2347 | 4,099.00 | 1,053 | 0.1735 ms |
| **`Round4Submission`** *(m67=0.5, edge=5.5)* | `conservative` | 23,035.00 | **11,635.00** | **0.3587** | **2,865.00** | 728 | 0.1919 ms |
| **`Round4Submission`** *(m67=0.5, edge=5.5)* | `queue_aware` | 23,091.50 | **11,741.00** | **0.3613** | **2,901.00** | 731 | **0.1871 ms** |
| **`Round4Submission`** *(m67=0.5, edge=5.5)* | `touch` | 26,941.50 | **13,259.50** | **0.2780** | **3,560.00** | 1,041 | 0.2017 ms |

![Round 3 and 4 OOS Attribution and Coupled Monte Carlo Distribution](../../reports/figures/r3_r4_oos_attribution_and_mc.png)

### OOS Attribution, Robustness & Portfolio Trade-Off (`Day 3`)
- **Per-Asset Attribution (`Day 3`, `queue_aware`)**: `HYDROGEL_PACK` **`+8,407.00`**, `VEV_4000` **`+2,493.00`**, **`VELVETFRUIT_EXTRACT` `+1,027.00`** *(flipped from `-328.50` in Round 3 and `+393.00` under overly aggressive `m67 = 1.0`)*, `VEV_4500` `-74.00`, `VEV_5200` `-41.00`, `VEV_5300` `-71.00`.
- **Sharpe & Drawdown Improvement Over Ungated R3**: Aligning `M67_BUMP = 0.5` beats `Round3Ungated` on annualized `Sharpe_252` across **all three fill modes** (`0.3613` vs `0.3488` `queue_aware`; `0.3587` vs `0.3462` `conservative`; `0.2780` vs `0.2347` `touch`), cuts `queue_aware` max drawdown by **`-10.8%`** (`3,250.50 -> 2,901.00`), and leads `touch` PnL outright (`+13,259.50` vs `+12,284.50`), while keeping total `queue_aware` PnL within `~307` XIRECs of narrower-spread `Round3Ungated` (`11,741.00` vs `12,048.00`).
- **Bootstrap (`Day 3`, `block=100, B=1,000`) & Coupled MC (`N=25`)**: `Sharpe_252` 95% CI **`[0.0932, 0.6302]`**, OOS PnL CI **`[3,079.11, 20,064.41]`**; Coupled MC Mean PnL **`2,345.10`**, `VaR95 = 1,692.40`, `CVaR95 = 1,116.75`, **`ProbLoss = 0.0000`**, Mean `Sharpe_252 = 0.4966`, Worst Max DD `1,905.50`. *(See [`EXP-R4-001`](../../reports/experiments/EXP-R4-001_round4_counterparty_flow.md).)*


