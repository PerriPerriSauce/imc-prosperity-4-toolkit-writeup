# Experiment EXP-R2-001: Round 2 Limit Scaling ($\pm 80$), Inventory Skew & MAF Valuation

- **Hypothesis**:
  1. Scaling bot-wall filtering and alpha-beta drift estimation from $Q_{\max}=20$ to Round 2's $\pm 80$ limit while raising inventory skew ($\gamma$) and minimum half-spread (`min_edge`) preserves zero overfitting (`CSCV PBO < 0.15`, `DSR >= 0.95`) and expands risk-adjusted PnL proportionally across both stationary (`ASH_COATED_OSMIUM`) and linearly trending (`INTARIAN_PEPPER_ROOT`) regimes.
  2. Under enlarged `±80` inventory capacity and `14–16`-tick bot walls, winning Round 2's `+25%` Market Access Fee (MAF) liquidity auction scales expected session PnL super-linearly enough to justify a calibrated positive bid ceiling.
- **Calibration Split (IS)**: Round 2 `Day -1` & `Day 0` (`20,000` independent daily ticks total, `queue_aware` matching, `Q_max = 80`).
- **Held-Out Out-of-Sample Split (OOS)**: Round 2 `Day 1` (`10,000` ticks) evaluated single-pass across `conservative`, `queue_aware`, and `touch` fill regimes + `N=25` Monte Carlo sessions per arrival rate.

---

## 1. In-Sample 2D Plateau, CSCV PBO & DSR (`Day -1` & `Day 0`)

Sweeping `min_edge in {1.5, 2.5, 3.5, 4.5}` $\times$ `inventory_skew in {0.15, 0.30, 0.45, 0.60, 0.75}` (`20` configurations, `clip=30`):

- **Selected Stable Plateau**: `min_edge = 3.5`, `inventory_skew = 0.75`
- **Local Neighborhood Stability**: Raw `Sharpe_252 = 1.3715`, `3x3` local mean `1.3602`, local std `0.0176`
- **Effective Independent Trials ($N_{\text{eff}}$)**: `1.22` (monotone structural response surface)
- **CSCV / PBO ($S=8$, `70` splits)**: **`PBO = 0.000`** (`passes < 0.15`)
- **Deflated Sharpe Ratio (`20` trials)**: **`DSR = 1.0000`** (`passes >= 0.95`)

*(Source: [`reports/tables/r2_sensitivity_grid.csv`](../tables/r2_sensitivity_grid.csv), [`reports/tables/r2_to_r5_overfitting_gates.csv`](../tables/r2_to_r5_overfitting_gates.csv).)*

---

## 2. Out-of-Sample Ablation & Asset Attribution (`Day 1`, Held-Out OOS)

| Strategy | Fill Mode | IS PnL (`Day -1, 0`) | OOS PnL (`Day 1`) | OOS `Sharpe_252` | OOS Max DD | OOS Fills | Mean Latency |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| `NoOpBaseline` | `queue_aware` | 0.00 | 0.00 | 0.0000 | 0.00 | 0 | — |
| `SymmetricMM_80` | `queue_aware` | $-40{,}165.50$ | $-20{,}294.50$ | $-0.3348$ | 21,729.50 | 709 | — |
| `DriftAwareQuoter_Pepper` | `queue_aware` | 14,432.00 | 6,344.50 | 0.3290 | 2,896.00 | 519 | — |
| `InventorySkewedMM_80` | `queue_aware` | 17,331.50 | 7,736.50 | 0.2445 | 3,784.50 | 1,016 | — |
| **`Round2Submission`** | `conservative` | 50,025.00 | **27,378.00** | **1.3934** | **419.50** | 1,020 | 0.0401 ms |
| **`Round2Submission`** | `queue_aware` | 50,225.00 | **27,463.00** | **1.3972** | **419.50** | 1,022 | **0.0384 ms** |
| **`Round2Submission`** | `touch` | 51,257.00 | **28,040.50** | **1.4117** | **392.50** | 1,053 | 0.0397 ms |

- **OOS Balanced Asset Split (`queue_aware`)**: `ASH_COATED_OSMIUM` contributes **`+15,312.00`** (`55.8%`), `INTARIAN_PEPPER_ROOT` contributes **`+12,151.00`** (`44.2%`).
- **Circular Block Bootstrap (`block=100, B=1,000`)**: `Sharpe_252` 95% CI **`[1.2314, 1.5823]`**, OOS PnL 95% CI **`[24,264.69, 30,509.05]`**.

---

## 3. Monte Carlo Arrival-Rate Sensitivity & MAF Auction Valuation (`N=25`, `1,000` steps)

| Arrival Rate | Mean PnL | Std PnL | `VaR95` | `CVaR95` | `ProbLoss` | Mean `Sharpe_252` |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `0.04` | 2,688.30 | 735.77 | 1,310.90 | 1,155.25 | 0.0000 | 1.6470 |
| `0.06` | 3,899.84 | 776.74 | 2,770.00 | 2,173.75 | 0.0000 | 2.3115 |
| `0.08` *(Baseline)* | **5,065.52** | 788.72 | 3,578.20 | 3,463.25 | **0.0000** | 2.8362 |
| `0.10` *(+25% MAF)* | **6,755.98** | 724.54 | 5,578.00 | 5,487.25 | **0.0000** | **3.6416** |
| `0.12` | 8,360.10 | 849.40 | 6,877.10 | 6,416.25 | 0.0000 | 4.3442 |

*(Source: [`reports/tables/r2_maf_sensitivity.csv`](../tables/r2_maf_sensitivity.csv).)*

Increasing taker arrival rate by `+25%` (`0.08 -> 0.10`) boosts calibrated `1,000`-step MC PnL by **`+1,690.46` XIRECs (`+33.4%`)** because tighter inventory skew keeps resting quotes away from limit walls, preventing queue saturation. Scaled to a full `10,000`-tick trading day (`~16,900` incremental XIRECs ignoring auction-winner congestion), a risk-adjusted bid below **`~8,000–12,000` XIRECs** clears a strict positive-EV safety margin.

## Conclusion
Accepted. Moving from naive symmetric quoting (`-20,294.50` OOS) to wall-mid filtering and strong `±80` inventory skew delivers `+27,463.00` OOS PnL with a `419.50`-XIREC drawdown and `PBO = 0.000`.
