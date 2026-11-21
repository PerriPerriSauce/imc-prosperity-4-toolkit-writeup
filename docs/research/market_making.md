# Market Making Mechanics Across Position & Spread Regimes (Rounds 1–5)

Our production market-making engines evolve across Rounds 1 through 5 around a consistent core—**reservation-adjusted Avellaneda–Stoikov quoting bounded by fair-value margins**—while matching limits, volatility scaling, and selective edge additions strictly to verified microstructure geometry.

## 1. Unified Quoting Architecture

Given fair value $V_t$, starting inventory $q_t$, position cap $Q_{\max}$, effective inventory skew $\gamma_t$, and edge floor $e_t$:
$$r_t = V_t - \gamma_t \cdot q_t, \qquad b_t^* \le \lfloor r_t - e_t \rfloor, \qquad a_t^* \ge \lceil r_t + e_t \rceil$$
after first taking mispriced resting depth inside `[FV - take_edge, FV + take_edge]` and deducting taken size from `q_rem_buy` / `q_rem_sell` under Prosperity's starting-position batch limit rule ([`COMPETITION_SPECIFICATION.md`](../competition/COMPETITION_SPECIFICATION.md)).

## 2. Production Scorecard Verified Through Validation Gates (R1–R5 OOS, `queue_aware`)

| Round | Inventory Cap $Q_{\max}$ | Interior Plateau (`IS`) | OOS PnL (`QA`) | `IR_tick` | `BlkSR_1k` | `MaxDD` | Key Microstructural Takeaway |
| :---: | :---: | :--- | ---: | ---: | ---: | ---: | :--- |
| **R1** | `±80` | `min_edge=2.0, skew=0.40` | **`+91,098.00`** | `0.05445` | `9.327` | `1,405.00` | Fixed `10k` Osmium MM + max-wall Pepper carry (`Osmium +11.4k, Pepper +79.7k`) |
| **R2** | `±80` | `min_edge=2.5, skew=0.40` | **`+94,209.00`** | `0.05466` | `8.237` | `1,401.00` | Unskewed `SymmetricMM_80` bleeds `-20,294.50` riding `+0.10/tick` trend |
| **R3** | `±200` / `±300` | `spot_scale=30.0, enter_band=10.0` | **`+95,093.00`** | `0.00584` | `0.573` | `75,774.00` | Bayesian OU + BS total-vol `VEV_4000..5500` **without** destructive spot delta hedging |
| **R4** | `±200` / `±300` | `spot_scale=30.0, flow_weight=1.5` | **`+260,540.00`** | `0.01680` | `0.646` | `71,177.00` | Strictly causal `Mark 14` SELL / `Mark 55` BUY flow adds `+11,153.50` vs `Round3NoFlow` |
| **R5** | `±10` (`50` assets) | `vsm=0.18, ef=0.14, mc=0.16` | **`+97,628.00`** | `0.02624` | `1.108` | `14,961.50` | Vol-scaled AS + discrete `MICROCHIP_CIRCLE` lag beats `Round5NoLeadLag` (`+2,215.50`), `1.66x` `PnL/DD` vs EMA MM |

## 3. Adaptive Volatility Scaling Without Hard Halts (`Round 5`)

With uniform `±10` position caps across `50` assets (`Galaxy Sounds`, `Sleep Pods`, `Microchips`, `Pebbles`, `Robots`, `UV-Visors`, `Translators`, `Panels`, `Oxygen Shakes`, `Snackpacks`), categories split between wide high-ratio MM books (`Oxygen Shakes +28,934.5`, `Galaxy Sounds +21,013.5`, `Sleep Pods +13,606.5`, `Snackpacks +11,085.5`, `UV-Visors +11,077.0` OOS) and volatile narrow-ratio random walks (`Robots -1,228.0`, `Panels -1,386.5` OOS). Scaling skew and reservation margins proportionally to rolling step volatility (`vol_skew_mult * vol_ema`, `edge_frac * vol_ema`) protects downside (`14,961.50` MaxDD vs `29,130.00` `EmaSymmetricMM_All50`) without sacrificing profitable re-quoting flow as hard `VOL_GUARD` halts did.

## 4. Queue-Aware Price-Time Conservation vs. Touch Sensitivity

Under `ExecutionSimulator`, `queue_aware` enforces strict price-time priority and a shared non-renewable public-trade volume budget per tick (while `conservative` fills strictly through limit prices and `touch` ignores queue ahead). Across R1–R5 OOS, `conservative` (`91,098` R1; `94,209` R2; `95,093` R3; `260,537` R4; `97,514` R5) closely tracks `queue_aware` (`91,098` R1; `94,209` R2; `95,093` R3; `260,540` R4; `97,628` R5), demonstrating that alpha does not rely on touch-optimistic queue assumptions (`touch`: `91,743` R1 .. `114,924` R5).
