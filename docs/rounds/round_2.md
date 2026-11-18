# Round 2: Regime Continuity, MAF Auction Economics & Microstructure EDA

## 1. Round Context & Market Structure

Unlike earlier Prosperity editions that introduced basket ETFs in Round 2, **IMC Prosperity 4 Round 2** kept the exact two-asset instrument universe from Round 1 while shifting the strategic boundary along two axes:

1. **Instrument Continuity (`±80` Position Limit Cap)**:
   - `ASH_COATED_OSMIUM`: Stationary Ornstein-Uhlenbeck asset oscillating around `10,000` with wide `16`-tick median spreads and recurrent missing-side quotes.
   - `INTARIAN_PEPPER_ROOT`: Steady linear-drift asset advancing at roughly `+0.108` XIRECs per `100`-unit step across three fresh trading days (`Day -1`, `Day 0`, `Day 1`), climbing cleanly from `~11,501` (`Day -1`) through `~12,501` (`Day 0`) to `~13,500` (`Day 1` OOS).
2. **Market Access Fee (MAF) Sealed Auction**:
   - Competing teams submitted a one-time fixed bid in XIRECs for elevated exchange access.
   - The **top 50%** of bids paid their bid upfront against Round 2 PnL in exchange for `+25%` incremental order book liquidity; losing teams kept their capital and traded the unboosted flow.
3. **Manual Challenge ("Invest & Expand")**:
   - Allocation optimization across **Research** ($200{,}000 \cdot \frac{\ln(1+r)}{\ln(101)}$), **Scale** ($0.07 \cdot s$), and rank-based **Speed** ($\in [0.1, 0.9]$) subject to $r + s + p \le 100$ against a `50,000`-XIRECs budget.

*(Note: Official `prosperity4bt` / `ADnocap` configs specify a `±80` unit position limit per symbol for Rounds 1–2; earlier Round 1 stress runs conservatively fixed $Q_{\max} = 20$ as a capacity bound.)*

---

## 2. Historical Data Partition & Descriptive Microstructure Audit

To guard against look-ahead bias during strategy optimization, we partition the three Round 2 days (`60,000` total price rows, `2,391` public trades; generated via [`scripts/eda_rounds2_to_5.py`](../../scripts/eda_rounds2_to_5.py)) strictly into **Calibration (`Day -1`, `Day 0`)** and **Held-Out Out-of-Sample (`Day 1`)**:

| Split | Day | Product | Two-Sided | One-Sided | Empty (`mid=0`) | Mid Mean | Spread Med | $\text{Std}(\Delta P_{\text{mid}})$ | Lag-1 ACF $\rho(1)$ | Trades | Touch % |
| :--- | ---: | :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **IS** | -1 | `ASH_COATED_OSMIUM` | 9,237 | 748 | 15 | 10,000.83 | 16.0 | 1.8948 | $-0.4886$ | 459 | 100.0% |
| **IS** | 0 | `ASH_COATED_OSMIUM` | 9,257 | 727 | 16 | 10,001.58 | 16.0 | 1.8631 | $-0.4686$ | 471 | 100.0% |
| **OOS** | 1 | `ASH_COATED_OSMIUM` | 9,214 | 764 | 22 | 10,000.15 | 16.0 | 1.8872 | $-0.4880$ | 465 | 100.0% |
| **IS** | -1 | `INTARIAN_PEPPER_ROOT` | 9,246 | 741 | 13 | 11,501.16 | 13.0 | 1.7460 | $-0.4922$ | 331 | 100.0% |
| **IS** | 0 | `INTARIAN_PEPPER_ROOT` | 9,230 | 752 | 18 | 12,501.43 | 14.0 | 1.8749 | $-0.4956$ | 332 | 100.0% |
| **OOS** | 1 | `INTARIAN_PEPPER_ROOT` | 9,248 | 736 | 16 | 13,500.11 | 15.0 | 2.0303 | $-0.4958$ | 333 | 100.0% |

*(Source: [`reports/tables/r2_microstructure_summary.csv`](../../reports/tables/r2_microstructure_summary.csv).)*

### Three Quantitative Diagnostics Emerge Immediately

1. **Stationarity & Drift Invariance Across Rounds 1 $\to$ 2**:
   - `ASH_COATED_OSMIUM` rejects the unit-root null overwhelmingly across every day (`ADF t = -14.53`, `-10.52` IS; `-12.27` OOS) with discrete AR(1)-implied OU speed $\hat{\theta} \in [0.0658, 0.1289]$ (half-life `5.38–10.54` ticks).
   - `INTARIAN_PEPPER_ROOT` remains strictly trend-stationary (`ADF t = -0.21` to `-0.25` in levels; OLS linear $R^2 = 1.0000$ every single day) with an unbroken step slope of **`+0.1080` to `+0.1083`** per `100`-timestamp increment (`~1,000` XIRECs/day baseline advance).
2. **Proportional Spread Widening on `INTARIAN_PEPPER_ROOT` (Crucial Microstructural Shift)**:
   - While `ASH_COATED_OSMIUM` retains a fixed `16.0`-tick median spread from `10,000`, `INTARIAN_PEPPER_ROOT`'s median quoted spread **widens mechanically as price climbs**: `13.0` ticks at `mid ≈ 11,501` (`Day -1`), `14.0` ticks at `mid ≈ 12,501` (`Day 0`), and `15.0` ticks at `mid ≈ 13,500` (`Day 1`)! Similarly, $\text{Std}(\Delta P_{\text{mid}})$ rises monotonically from `1.7460 -> 1.8749 -> 2.0303`.
   - **Causal Mechanism**: As underlying fair value grows ($FV_t \approx 13{,}500$), resting market-maker bots quote proportional half-spread offsets ($\text{floor}(FV_t (1 - K))$ / $\text{ceil}(FV_t (1 + K))$), automatically expanding the absolute bid-ask spread in XIRECs as spot appreciates. A fixed absolute half-spread floor (`min_edge = 1.5` from Round 1) leaves money on the table when $S_t > 13{,}000$.
3. **100% Touch-Executed Order Flow & Persistent Quote-Bounce**:
   - Across all `2,391` Round 2 trades, **`100.0%`** printed directly at contemporaneous `bid_price_1` or `ask_price_1`, and lag-1 return autocorrelation remains fixed near $\rho(1) \in [-0.496, -0.469]$, confirming that inside-spread thin bot quotes still create mechanical OBI correlations ($r_{h=1} \approx 0.58$–$0.59$) rather than latent fundamental drift.

---

## 3. Formalizing the Market Access Fee (MAF) Break-Even Condition

In historical CSV replay without portal flow boost telemetry, the marginal value of winning the MAF auction cannot be directly read out of `prices_round_2_*.csv`. Instead, we treat it as an explicit capital allocation problem before calibrating synthetic arrival sweeps:

$$\text{EV}_{\text{MAF}}(b) = \mathbb{P}(\text{bid } b \ge \text{median\_field\_bid}) \cdot \Big(\underbrace{\Delta \text{PnL}_{+25\%\text{ flow}}}_{\text{Scaled from R1 live/MC fill elasticity}} - b\Big)$$

With the expanded `±80` limit (`4x` larger than Round 1's conservative `±20` bound) and wider proportional spreads on `INTARIAN_PEPPER_ROOT`, a strategy capturing passive spread inside the `14–16`-tick bot walls scales near-linearly with aggressive taker arrival rates until inventory-limit saturation binds. Determining whether the `25%` taker-flow boost scales net daily PnL by `+5%` or `+25%` under `Q_max = 80` is tested directly via Monte Carlo arrival-rate sweeps before assigning a concrete Round 2 MAF valuation band.

## 4. Candidate Hypotheses & Risk Controls

- **Scale Transition ($Q_{\max} = 20 \to 80$)**: Does increasing `inventory_skew` or keeping `min_edge` proportional to prevailing bot spread prevent adverse-selection tail risk at larger `±80` caps without suffocating fill volume?
- **Empty & One-Sided Book Defense**: With `1,479–1,500` one-sided ticks and `28–38` empty ticks per day persisting in Round 2, all online filters must continue masking missing sides and skipping quotes when `bid_1` or `ask_1` vanishes.
- **Drift Regime Fragility**: `INTARIAN_PEPPER_ROOT`'s `+1,000`/day linear trend persisted cleanly across Round 1 and Round 2, but remains an exogenous competition regime—any Round 2 strategy must cap unhedged directional tilt strictly within the worst-case position limit check.

---

## 5. Strategy Architecture, Validation Gates & MAF Auction Evaluation

Building directly on the Round 2 EDA findings, [`traders/round2/submission.py`](file:///c:/Users/pierr/Desktop/imc-prosperity-4-toolkit-writeup/traders/round2/submission.py) retains bot-wall fair-value extraction (`_popular_wall_mid`), causal alpha-beta drift estimation on `INTARIAN_PEPPER_ROOT`, and simultaneous `±80` limit checks, scaling reservation skew and minimum edge upward to monetize `4x` larger position caps without getting caught one-way on directional trends.

### 5.1 Why Scaling Limit Capacity (`20 -> 80`) Breaks Unskewed Quoters
Increasing maximum capacity by `4x` without retuning reservation parameters amplifies directional inventory variance quadratically relative to spread revenue. On a stationary mean-reverting book like `ASH_COATED_OSMIUM` (`mean spread = 16`, OU $\hat{\theta} \approx 0.066–0.129$), hitting `±80` happens slowly unless an adverse excursion runs deep. On `INTARIAN_PEPPER_ROOT` (`+0.108`/step continuous upward drift), a symmetric quoter fills asks immediately during every leg higher and rides full `-80` short exposure against an unstoppable tape—losing `-40,165.50` IS (`Day -1, 0`) and `-20,294.50` OOS (`Day 1`) with a `21,729.50` drawdown. Conversely, restricting trading purely to directional drift (`DriftAwareQuoter_Pepper`) leaves more than half of Round 2's passive spread capture on the table (`+6,344.50` OOS). Only pairing wall-filtered passive quoting on both assets with stiff inventory skew ($\gamma = 0.75$) and wide minimum edge ($3.5$ ticks) captures scale capacity while locking drawdown near `420` XIRECs.

### 5.2 Overfitting Controls & 2D Plateau Selection (`Day -1` & `Day 0` IS)

Sweeping `min_edge in {1.5, 2.5, 3.5, 4.5}` $\times$ `inventory_skew in {0.15, 0.30, 0.45, 0.60, 0.75}` (`20` configurations, `clip=30`, `queue_aware` simulation via [`evaluate_rounds2_to_5.py`](file:///c:/Users/pierr/Desktop/imc-prosperity-4-toolkit-writeup/scripts/evaluate_rounds2_to_5.py)) reveals a broad, monotonic stability ridge at high skew (`r2_sensitivity_grid.csv`):
- At light skew (`0.15`), IS PnL (`50.9k–53.4k`) accompanies severely depressed Sharpe (`0.578–0.914`) from large inventory swings.
- Across `inventory_skew >= 0.60`, IS Sharpe stabilizes cleanly inside `[1.320, 1.400]` while `3x3` plateau optimization selects `min_edge = 3.5, inventory_skew = 0.75` (`IS Sharpe_252 = 1.3715`, local neighborhood mean `1.3602`, std `0.0176`).
- **CSCV / PBO (`S = 8`, `70` partitions)**: **`PBO = 0.0000`**; **Deflated Sharpe Ratio (`N_eff = 1.22`)**: **`DSR = 1.0000`**.

### 5.3 Held-Out Out-of-Sample (`Day 1`) Ablation & Attribution

| Strategy | Fill Regime | IS PnL (`Day -1, 0`) | OOS PnL (`Day 1`) | OOS `Sharpe_252` | OOS Max DD | OOS Fills | Mean Latency |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| `NoOpBaseline` | `queue_aware` | 0.00 | 0.00 | 0.0000 | 0.00 | 0 | — |
| `SymmetricMM_80` | `queue_aware` | $-40{,}165.50$ | $-20{,}294.50$ | $-0.3348$ | 21,729.50 | 709 | — |
| `DriftAwareQuoter_Pepper` | `queue_aware` | 14,432.00 | 6,344.50 | 0.3290 | 2,896.00 | 519 | — |
| `InventorySkewedMM_80` | `queue_aware` | 17,331.50 | 7,736.50 | 0.2445 | 3,784.50 | 1,016 | — |
| **`Round2Submission`** | `conservative` | 50,025.00 | **27,378.00** | **1.3934** | **419.50** | 1,020 | 0.0425 ms |
| **`Round2Submission`** | `queue_aware` | 50,225.00 | **27,463.00** | **1.3972** | **419.50** | 1,022 | **0.0406 ms** |
| **`Round2Submission`** | `touch` | 51,257.00 | **28,040.50** | **1.4117** | **392.50** | 1,053 | 0.0428 ms |

Notice how insensitive `Round2Submission` is to passive queue assumptions: moving from strict price-through (`conservative: 27,378.00`) to `queue_aware` (`27,463.00`) and optimistic `touch` (`28,040.50`) spans only `2.4%` of terminal PnL because penny-improving inside `13–16`-tick walls clears queue priority almost every tick. Asset attribution remains balanced (`ASH_COATED_OSMIUM +15,312.00` [`55.8%`], `INTARIAN_PEPPER_ROOT +12,151.00` [`44.2%`]), and circular block-bootstrap (`block=100, B=1,000`) bounds OOS `Sharpe_252` within **`[1.2314, 1.5823]`** and PnL within **`[24,264.69, 30,509.05]`**.

### 5.4 Quantitative MAF Valuation & Monte Carlo Flow Elasticity

![Round 2 IS Sharpe Surface and Arrival-Rate MAF Valuation](../../reports/figures/r2_sensitivity_and_maf_valuation.png)

Simulating `25` calibrated `1,000`-tick sessions across counterparty arrival intensities `0.04 -> 0.12` (`simulate_arrival_sensitivity`, `r2_maf_sensitivity.csv`) quantifies exact fill elasticity under `±80` inventory caps:

| Counterparty Arrival Rate ($\lambda$) | Scenario Role | Mean MC PnL | Std Dev | `VaR 95%` | `CVaR 95%` | `Prob(Loss)` | Mean `Sharpe_252` |
| :---: | :--- | ---: | ---: | ---: | ---: | :---: | ---: |
| `0.04` | Thin Liquidity Stress | `2,688.30` | `735.77` | `1,310.90` | `1,155.25` | `0.0000` | `1.6470` |
| `0.06` | Mild Flow Compression | `3,899.84` | `776.74` | `2,770.00` | `2,173.75` | `0.0000` | `2.3115` |
| **`0.08`** | **Baseline Exchange Flow** | **`5,065.52`** | `788.72` | `3,578.20` | `3,463.25` | `0.0000` | **`2.8362`** |
| **`0.10`** | **`+25%` MAF Winner Uplift** | **`6,755.98`** | `724.54` | `5,578.00` | `5,487.25` | `0.0000` | **`3.6416`** |
| `0.12` | High-Flow Expansion | `8,360.10` | `849.40` | `6,877.10` | `6,416.25` | `0.0000` | `4.3442` |

Why is PnL uplift super-linear (`+33.4%`, `+1,690.46` / `1,000` steps) on a `+25%` arrival boost from `0.08 -> 0.10`? Under `±80` caps and zero-inventory cycling (`skew = 0.75`), faster two-way taker flow accelerates inventory mean reversion back to zero between drift moves, *reducing* time pinned near cap while harvesting additional bid-ask crossings (`std_pnl` actually falls from `788.72` to `724.54` while Sharpe jumps `2.8362 -> 3.6416`). Extrapolated to a `10,000`-tick live round (`~16,900` gross flow uplift before competitive crowding among winning MAF qualifiers), a sealed MAF bid up to `8,000–12,000` XIRECs maintains positive net expected surplus—paralleling the competitive auction shading logic in the Round 2 *Invest & Expand* manual challenge. *(All quantitative outputs above represent calibrated historical replays and synthetic Monte Carlo models, never live portal payouts.)*


