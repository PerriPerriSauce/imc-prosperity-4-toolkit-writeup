# Manual Challenges: Game Theory, Derivatives & Ex-Ante Models (Rounds 1–5)

Unlike the algorithmic exchange rounds—where historical order-book ticks let us replay strategies deterministically against resting bot depth—each manual challenge in IMC Prosperity 4 involves a one-shot allocation submitted without local replay data. Because opponent choices and stochastic payoffs are unobserved locally, every model below is evaluated **strictly as an ex-ante offline mathematical policy** parameterized by explicit assumptions—never as actual live portal telemetry.

![Round 1-5 Manual Challenges Comparative Statics](../../reports/figures/manual_challenges_analysis.png)

## Summary of Ex-Ante Offline Model Policies (`manual_challenges_summary.csv`)

| Round | Challenge Name | Ex-Ante Model Policy | Model Metric / Analytical Basis |
| :---: | :--- | :--- | :--- |
| **R1** | *An Intarian Welcome* | **`DRYLAND_FLAX`: `Bid 30, Qty 65`**; **`EMBER_MUSHROOM`: `Bid 20, Qty 10`** | Guards `96%` fill prob (`68.12` Expected PnL) under $\mathcal{N}(45, 22^2)$ human shocks on Flax; caps Mushroom (`9.81` EV) against `0.10`/unit fee |
| **R2** | *Invest & Expand* | **`Research = 15%` (`14.71%`), `Scale = 43%` (`43.29%`), `Speed = 42%`** | Level-3 Cognitive Hierarchy focal equilibrium (`246,036.10` L3 EV; `225,094.01` under full CH blend) |
| **R3** | *Celestial Gardeners' Guild* | **`Bid 1 = 775, Bid 2 = 880`** | Bayesian optimization across $\bar{b}_2 \sim \mathcal{N}(875, 15^2)$ (`76.00` EV/unit vs `63.73` single bid; shields cubic penalty cliff) |
| **R4** | *Aether Crystal Exotics* | **`AC_50_CO: -50`, `AC_40_BP: -50`, `AC_45_KO: +183`, `AC_50_C15: +53`, `AC_50_P15: +74`** | Exploits discrete `4/day` KO survival (`0.2113` fair vs `0.175` ask; `0.1562` at `24/day`) + Day-15 MV hedge (`EV = 40.96`, `std = 393.7`, `-70.1%` std cut, `Sharpe = 0.104`) |
| **R5** | *Extra! Extra! (Ignith)* | **KKT**: `39.0 / 30.5 / -17.5 / -10.5 / +2.5%`<br>**Risk-Adj (`kappa=3`)**: `36.3 / 30.3 / -17.3 / -11.1 / +5.1%` *(0% others)* | Exact KKT (`857,400.00` EV) and variance-adjusted (`855,944.53` EV vs `524,444` equal `1/9`) under bounded `-0.92` Phoenix floor (`-92%`) |

## 1. Round 1 — *An Intarian Welcome* (Walrasian Auction & Queue Depletion)

### Auction Rules and Queue Mechanics
Round 1 opens with a sealed uniform-price auction across two commodities backed by fixed merchant guild buybacks:
- **Dryland Flax**: guaranteed guild buyback at $V = 30$ with zero transaction fee ($c = 0$).
- **Ember Mushroom**: guild buyback at $V = 20$ with a $c = 0.10\text{/unit}$ clearing fee.

All orders clear simultaneously at the price $p^*$ maximizing traded volume:
$$p^* = \arg\max_p \min\bigl(D(p), S(p)\bigr), \qquad D(p) = \sum_{p_i \ge p,\; q_i > 0} q_i, \quad S(p) = \sum_{p_j \le p,\; q_j < 0} (-q_j)$$
with two rules that completely reshape optimal sizing:
1. If multiple prices tie on matched volume, the exchange selects the **strictly highest tied price**.
2. Orders match by **price priority first, then arrival order**—meaning any late human order sits at the **very back of the queue** at its submitted price level.

### Queue Jumping Without Price Tipping
Submitting a passive buy right at the resting clearing price $p_{\text{rest}}^*$ leaves late entrants behind resting bids. Stepping up one tick to $p = p_{\text{rest}}^* + 1$ jumps the queue at $p_{\text{rest}}^*$, provided quantity $q$ does not tip the high-price tie-breaker. On our illustrative **Dryland Flax** book solved in [`clear_opening_auction`](../../src/prosperity_toolkit/analysis/manual_challenges.py):
- Without our order, clearing sits at $p_{\text{rest}}^* = 28$ (`150` matched lots); bidding `(px=29, qty=66)` captures **`132.00` XIRECs**.
- Integrating expected PnL over `250` random human demand draws ($\mathcal{N}(45, 22^2)$ on Flax, $\mathcal{N}(30, 15^2)$ on Mushroom) via [`solve_round1_uncertain_demand`](../../src/prosperity_toolkit/analysis/manual_challenges.py) favors **`(px=30, qty=65)`** (`68.12` Expected PnL, defending fill against minor clearing shifts) on Flax and **`(px=20, qty=10)`** (`9.81` Expected PnL, avoiding uncapped fee erosion) on Ember Mushroom.

## 2. Round 2 — *Invest & Expand* (Cognitive Hierarchy Equilibrium & Speed Allocation)

Given a `50,000`-XIREC budget normalized across percentages $(r, s, p) \ge 0$ ($r + s + p \le 100$):
$$\text{Research}(r) = 200{,}000 \cdot \frac{\ln(1 + r)}{\ln(101)}, \qquad \text{Scale}(s) = 0.07 \cdot s, \qquad \text{Speed}(p) \in [0.1, 0.9]$$
$$\Pi_{\text{net}}(r, s, p) = \text{Research}(r) \cdot \text{Scale}(s) \cdot \text{Speed}(p) - 500(r + s + p)$$

For any fixed Speed share $p$ and remaining budget $R = 100 - p$, exact interior optimality between Research and Scale satisfies:
$$\frac{R - r^*}{1 + r^*} = \ln(1 + r^*)$$

Under **Poisson Cognitive Hierarchy** (`solve_round2_cognitive_hierarchy`, $\tau = 1.5$):
- **Level-1**: Best response **`p = 29.5%`** (`r = 17.30%, s = 53.20%`, Net EV `305,185.10`).
- **Level-2**: Best response **`p = 37.5%`** (`r = 15.65%, s = 46.85%`, Net EV `277,759.71`).
- **Level-3 Focal Benchmark**: **`p = 42.0%`** (`r = 14.71%, s = 43.29%` $\to$ discrete **`15% / 43% / 42%`**, Net EV `246,036.10` L3 best response; **`225,094.01`** under full CH population blend; `226,942.80` continuous QRE stress check).

## 3. Round 3 — *The Celestial Gardeners' Guild* (Bayesian Reserve Screening)

Sellers draw private reserves uniformly from $\mathcal{R} = \{670, 675, \dots, 920\}$, and acquired inventory resells at `920`. Second bids ($b_1 \le b_2 < 920$) face cubic shrinkage below the cohort average $\bar{b}_2$:
$$\phi(b_2; \bar{b}_2) = \min\!\left(1, \;\left(\frac{920 - \bar{b}_2}{920 - b_2}\right)^3\right)$$
Because second-bid volume collapses cubically whenever $b_2 < \bar{b}_2$, quadratic integration over $\bar{b}_2 \sim \mathcal{N}(875, 15^2)$ (`solve_round3_bayesian_belief`) recommends **`Bid 1 = 775, Bid 2 = 880`** (**`76.00` XIRECs/unit** EV, vs. `83.14`/unit under a softer `avg_b2 = 860` point belief and `63.73`/unit single bid).

## 4. Round 4 — *Vanilla Just Isn't Exotic Enough* (`Aether Crystal` Exotics)

`AETHER_CRYSTAL` starts at $S_0 = 50$ with zero drift and **`251%` annualized volatility** across `252` days/year sampled at `4` discrete 6-hour steps/day ($\sigma_{\text{step}} = 2.51 / \sqrt{1008} \approx 0.07906$). Rather than estimating vanilla or chooser options via Monte Carlo noise, `price_aether_crystal_contract` prices European vanillas (`AC_50_C15`, `AC_50_P15`), the `15d` binary put (`AC_40_BP`, pays `10`), and the `10d/15d` chooser (`AC_50_CO`) via **exact Black-Scholes and Rubinstein (1991) closed-form formulas**, reserving `100,000`-path antithetic GBM exclusively for the path-dependent `4/day` down-and-out put (`AC_45_KO`, $B=35$):

| Contract | Method (`15d`, `4/day`) | Portal Quote | Model Fair Value | Action |
| :--- | :--- | :---: | :---: | :---: |
| **`AC_50_CO`** | Exact Rubinstein Chooser (`10d`/`15d`, $K=50$) | `22.200` | **`21.8977`** | **SELL** (`-0.3023`) |
| **`AC_40_BP`** | Exact BS Binary Put ($K=40$, pays `10`) | `5.000` | **`4.7679`** | **SELL** (`-0.2321`) |
| **`AC_45_KO`** | Discrete `4/day` Antithetic GBM ($K=45, B=35$) | `0.175` | **`0.2113`** | **BUY** (`+0.0363`) |
| **`AC_45_KO (24/d)`** | Fine `24/day` GBM counterfactual | `0.175` | `0.1562` | *(Shows discrete monitoring premium)* |
| **`AC_50_C15` / `P15`** | Exact BS ATM `15d` Call / Put | `11.920 / 12.000` | `12.0269 / 12.0269` | Straddle hedge |

### Day-15 Terminal Mean-Variance Portfolio (`solve_round4_exotic_portfolio`)
Optimizing integer contract bounds across all `100,000` Day-15 terminal payoff paths (`risk_aversion = 0.00015`) selects **`AC_50_CO: -50`, `AC_40_BP: -50`, `AC_45_KO: +183`, `AC_50_C15: +53`, `AC_50_P15: +74`**, cutting portfolio terminal standard deviation by **`-70.1%`** (`std = 393.7`, `CVaR95 = -389.9`, `EV = 40.96` vs asks) and raising Sharpe ratio from `0.044` (unhedged) to **`0.104`**.

## 5. Round 5 — *Extra! Extra!* (Ashflow Alpha KKT Shrinkage)

Given nine **Ashflow Alpha** catalysts on a $B = 1{,}000{,}000$ budget with quadratic fee $F_i(q_i) = (|q_i|/100)^2 \cdot 1{,}000{,}000$, short returns are naturally bounded below `-100%` (resurfaced sourcing shock on `Ashes of the Phoenix` uses **`-0.92`** (`-92%`) rather than an impossible `-110%`). Both exact KKT soft-thresholding (`lambda* = 0.5700`) and quadratic variance penalization ($\kappa = 3.0$, `lambda* = 0.4916`) activate `5/9` clear catalysts and zero out four noisy goods:

| Ignith Good | Catalyst Edge $\mu_i$ | Vol $\sigma_i$ | Exact KKT (`857,400.00` EV) | Risk-Adj KKT (`855,944.53` EV) |
| :--- | :---: | :---: | :---: | :---: |
| **`Thermalite Core`** | `+1.35` | `0.35` | `+39.00%` | `+36.26%` |
| **`Sulfur Reactor`** | `+1.18` | `0.30` | `+30.50%` | `+30.33%` |
| **`Ashes of the Phoenix`** | `-0.92` | `0.40` | `-17.50%` | `-17.28%` |
| **`Pyroflex Cells`** | `-0.78` | `0.45` | `-10.50%` | `-11.06%` |
| **`Scoria Paste`** | `+0.62` | `0.42` | `+2.50%` | `+5.08%` |
| **4 Noisy Goods (`Obsidian`..`Lava`)** | `-0.42`..`+0.06` | `0.60`..`0.90` | `0.00%` | `0.00%` |

Naive equal-weight spreading (`1/9` across all 9 goods) earns only **`524,444.44`** net EV due to fee dilution on weak catalysts.
