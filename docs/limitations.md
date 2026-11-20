# Scope, Modeling Assumptions & Known Limitations

Every finding in this repository strictly separates **observed historical order-book data** (`data/raw/`), **estimated in-sample parameters**, **model assumptions**, **simulated replay / Monte Carlo results**, and **ex-ante offline manual models**. No metric in this workspace represents an actual live IMC Prosperity 4 portal score.

---

## 1. Competition Specification & Data Coverage Boundaries

| Aspect | Current Status / Coverage | Implication & Mitigation |
| :--- | :--- | :--- |
| **Algorithmic Datasets** | Complete public CSV archives for Round 0 (`Day -2..-1`), Round 1 (`Day -2..0`), Round 2 (`Day -1..1`), Round 3 (`Day 0..2`), Round 4 (`Day 1..3`), and Round 5 (`Day 2..4`), hashed in [`prosperity4_manifest.json`](../data/manifests/prosperity4_manifest.json). | One chronological terminal day per round (`Day 0` R1, `Day 1` R2, `Day 2` R3, `Day 3` R4, `Day 4` R5) is reserved strictly for single-pass out-of-sample evaluation. Furthermore, Round 3 and Round 4 share **byte-identical `prices` CSVs on `Day 1` and `Day 2`**. Three daily trajectories per round remain narrow for regime exhaustion—for instance, `R3` Day 2 OOS bootstrap CI spans `[-184,416.62, +355,675.89]` even with `+95,093.00` point PnL—so block bootstrap CIs and stressed MC suites always accompany point PnL. |
| **Official Position Limits** | Verified across public CSVs and `prosperity4bt` constants: `±80` (R0–R2), `±200` spot / `±300` options (R3–R4), and `±10` across all 50 assets (R5). | Every production strategy ([`traders/round1`](../traders/round1/submission.py)–[`traders/round5`](../traders/round5/submission.py)) and [`ExecutionSimulator`](../src/prosperity_toolkit/execution/simulator.py) enforce the exact same verified limits. |
| **Per-Tick Lambda / Runtime Limits** | Exact AWS Lambda server timeout and RAM cutoff bounds are not publicly disclosed inside the historical CSVs ([`COMPETITION_SPECIFICATION.md`](competition/COMPETITION_SPECIFICATION.md)). | Measured per-tick mean runtime ranges from `0.0204 ms` (R1) to `0.5518 ms` (50-asset R5), leaving comfortable sub-1ms execution headroom. |
| **Live Competition Execution** | No live submission scorecard or exchange leaderboard fills are stored locally. | All algorithmic PnL, IR, drawdowns, and MC summaries are explicitly tagged as **simulated historical replay** or **synthetic Monte Carlo** outcomes. |

---

## 2. Backtesting & Execution Simulator Limitations

1. **Passive Queue Model Is an Approximation (`queue_aware` vs. Live Matching Engine)**:
   - Historical CSVs expose aggregated L1–L3 levels rather than per-order arrival queue updates. Under `FillMode.QUEUE_AWARE`, passive orders follow strict price-time priority (`(-price, idx)` / `(price, idx)`) sharing a finite per-tick public-trade volume budget (`remaining_trade_volumes`), deducting resting book depth $V_{\text{ahead}}$ when matching at touch.
   - True queue priority against **other human participants** on the live Prosperity exchange cannot be reconstructed purely from anonymized historical bot replays—every strategy is therefore evaluated across all three fill modes (`conservative`, `queue_aware`, `touch`).
2. **Causal `t - 100` Trade Delivery & Batch Limit Cancellation**:
   - Following exchange mechanics, `own_trades` and `prior_market_trades` arrive strictly at $t - 100$ (never contemporaneously at $t$), and any symbol batch whose worst-case buy or sell sum exceeds `[-Q_max, +Q_max]` from starting inventory $q_{\text{start}}$ is canceled in full.
3. **Zero Explicit Fee Schedule on Historical Order-Book Trades**:
   - Standard Prosperity 4 spot/options exchange CSVs incur zero per-lot transaction fees (unlike Manual R1 Ember Mushroom `0.10`/unit and Manual R5 quadratic fee `(q/100)^2 * 1M`), leaving adverse selection and spread crossing as the primary execution costs simulated.

---

## 3. Strategy & Statistical Validation Limitations

1. **Flat Correlated Grids & Slice-Rank Ties (`CSCV PBO`)**:
   - Across our `2D` coarse parameter surfaces, neighboring candidates correlate tightly ($N_{\text{eff}} = 1.01\text{--}1.14$). In Round 2 (`local_std = 0.000107`, `PBO = 0.300`) and Round 5 (`local_std = 0.000551`, `PBO = 0.543`), near-identical interior grid points swap ranks randomly across 8-slice CSCV partitions even though `DSR_block = 1.0000` and held-out OOS remains positive (`+94,209.00` R2, `+97,628.00` R5). `CSCV PBO` should therefore be read jointly with `N_eff`, `local_std`, and `DSR_block`, not as an isolated threshold.
2. **Round 3 / Round 4 Volatility & Sample Variance**:
   - Holding large directional/volatility inventory across 10 `VEV` strikes and `±200` spot caps (`R3` `MaxDD = 75,774.00`, `R4` `MaxDD = 71,177.00`) produces wide OOS bootstrap intervals (`R3`: `[-184.4k, +355.7k]`; `R4`: `[+14.7k, +525.4k]`) and non-zero adverse-selection stress loss rates (`30.0%` R3, `27.5%` R4 in `N = 40` stressed MC).
3. **Honest Pruned Alpha Hypotheses**:
   - Testing R3 spot delta hedging, R4 `Mark 67` 1-tick spread bounce (`causal_1_to_200 = +0.113`, `t = 1.56`), R5 `Pebbles` crossing (basket `std = 2.82` trapped inside `12–14` tick spreads), and R5 `VOL_GUARD` halts on strictly IS data rejected all four before OOS deployment.
4. **Finite MC Wilson Uncertainty**:
   - Zero observed losses across `N = 40` synthetic sessions implies an exact 95% Wilson upper loss-rate bound of `8.76%` (`0.0876`), never "0% true risk of loss".

---

## 4. Manual Challenge Uncertainty (`docs/manual/`)

Unlike exchange CSVs, opponent manual submissions are unobserved:
- Structural payoff rules (`251%` `Aether Crystal` vol, `AC_40_BP` binary payout `10`, `9` Ignith catalysts, Round 3 cubic cliff) follow the problem specifications ([`MANUAL_CHALLENGES.md`](manual/MANUAL_CHALLENGES.md)), while uncertain crowd parameters (competing auction demand in R1, Speed CDFs in R2, cohort mean $\bar{b}_2$ in R3, Ignith edge beliefs/vols in R5, with `Ashes of the Phoenix` floored at `-0.92 > -1.00`) represent **explicit ex-ante model assumptions** rather than live portal telemetry.
