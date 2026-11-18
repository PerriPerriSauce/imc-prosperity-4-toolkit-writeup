# Market Making Mechanics Across Position & Spread Regimes (Rounds 1–5)

Our production market-making engines evolve across Rounds 1 through 5 around a single invariant core—**reservation-adjusted Avellaneda–Stoikov quoting bounded by non-crossing fair-value margins**—while scaling risk aversion, spread selectivity, sizing clips, and hedging controls strictly to each round's position-limit and microstructure geometry.

## 1. Unified Quoting Architecture

Given estimated fair value $V_t$, current inventory $q_t$, position cap $Q_{\max}$, inventory aversion $\gamma$, and minimum half-spread $e_{\min}$, every strategy computes its reservation price:

$$r_t = V_t - \gamma \cdot q_t, \qquad b_t^* = \lfloor \min(b_{\text{penny}}, \, r_t - e_{\min}) \rfloor, \qquad a_t^* = \lceil \max(a_{\text{penny}}, \, r_t + e_{\min}) \rceil$$

where penny-joining quotes improve best resting bot depth only inside `[r_t - e_min, r_t + e_min]` boundaries so passive quotes never chase adverse order flow across our edge floor. Simultaneous resting quantities strictly enforce:

$$q_t + \sum_{k} Q^{\text{buy}}_{t,k} \le Q_{\max}, \qquad q_t - \sum_{k} |Q^{\text{sell}}_{t,k}| \ge -Q_{\max}$$

preventing Prosperity's symbol-wide batch cancellation rule ([`COMPETITION_SPECIFICATION.md`](file:///c:/Users/pierr/Desktop/imc-prosperity-4-toolkit-writeup/docs/competition/COMPETITION_SPECIFICATION.md)).

## 2. Parameter Regimes Verified Through Validation Gates (R1–R5)

| Round | Inventory Cap $Q_{\max}$ | Validated Plateau | OOS PnL (`queue_aware`) | OOS `Sharpe_252` | OOS Max DD | Primary Market-Making Lesson |
| :--- | :---: | :--- | ---: | ---: | ---: | :--- |
| **Round 1** | `20` *(assumed)* | `min_edge = 1.5`, `skew = 0.80` | `+22,157.00` | `1.1894` | `267.00` | Bot-wall FV + penny-joining beats naive L1 MM (`+10,825`) by `>2x` |
| **Round 2** | `80` | `min_edge = 3.5`, `skew = 0.75` | `+27,463.00` | `1.3972` | `419.50` | Unskewed `SymmetricMM_80` bleeds `-20,294.50` riding `+0.108`/tick trends |
| **Round 3** | `200` / `300` | `mm_edge = 4.5`, `mm_skew = 0.10` | `+7,525.50` | `0.2276` | `1,936.00` | Wide-spread `HYDROGEL_PACK` (`15.7`-tick spread) + ITM `VEV_4000` carry options hedging costs |
| **Round 4** | `200` / `300` | `m67_bump = 0.5`, `mm_edge = 5.5` | `+11,741.00` | `0.3613` | `2,901.00` | Live `Mark 67` flow gating flips `VELVETFRUIT_EXTRACT` to `+1,027.00` & cuts MaxDD `-10.8%` vs R3 |
| **Round 5** | **`10`** (`50` assets) | `edge_frac = 0.18`, `skew = 1.25` | **`+123,173.00`** | **`0.8109`** | `6,205.50` | Full `QUOTE_CLIP = 10` + dynamic `VOL_GUARD` + atomic `Pebbles` captures `88.3%` of single-day public ceiling while cutting DD `-78.7%` vs lagged EMA (`29,130`) |

## 3. Dynamic Selectivity & Clip Sizing Under Tight Limits (`Round 5`)

In Round 5, position caps tighten from `200–300` down to **`±10`** across **`50` securities**, exposing a fundamental execution trade-off parameterized by each symbol's spread-to-innovation ratio:

$$\text{MM Opportunity Index}_i = \frac{\text{Median Bid-Ask Spread}_i}{\sigma_{\Delta P, i}}$$

1. **High-Margin Categories**: `Snackpacks` (`2.10–3.04`, e.g., `SNACKPACK_PISTACHIO = 3.035`), `UV-Visors` (`1.25–1.32`), `Galaxy Sounds` (`1.25–1.29`), and `Oxygen Shakes` (`1.06–1.30`) compensate inventory variance `1.1x–3.0x` per spread capture. Under tight `±10` bounds, quoting the full `QUOTE_CLIP = 10` capacity captures multi-unit synchronized pulse sweeps (`Galaxy Sounds +24,662.00`, `Oxygen Shakes +16,875.50`).
2. **Adaptive Guarding on `Robots` & `Microchips`**: These two categories trade at narrow `0.54–0.89` ratios, and `ROBOT_DISHES` spiked `2.8x` in step volatility on held-out `Day 4` (`9.83 -> 27.48`). Rather than losing profitable ticks everywhere or blowing up during volatility spikes, [`traders/round5/submission.py`](file:///c:/Users/pierr/Desktop/imc-prosperity-4-toolkit-writeup/traders/round5/submission.py) applies a wider `LOW_RATIO_EDGE_FRAC = 0.35`, `1.5x` inventory skew, and a dynamic rolling step-volatility guard (`spread >= 0.50 * vol_ema`)—delivering **`+7,124.00`** on `Microchips` and **`+1,240.00`** on `Robots` OOS (`Day 4`) while preserving `PBO = 0.1000` (`DSR = 1.0000`).

## 4. Queue-Aware Discipline vs Touch Bias

Across every round (`r1_ablation_summary.csv`, `r2..r5_ablation_summary.csv`), passive `touch` matching systematically overstates realized PnL by allowing fills without clearing resting bot depth ahead (`R1: 22,667` vs `22,157`; `R2: 28,040.5` vs `27,463.0`; `R3: 8,490.0` vs `7,525.5`; `R4: 13,259.5` vs `11,741.0`; `R5: 140,545.5` vs `123,173.0`). All parameter selection and validation gates in this toolkit run strictly under `queue_aware` matching and cross-verify against worst-case `conservative` execution before acceptance.
