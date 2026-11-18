# Scope, Modeling Assumptions & Known Limitations

Every finding in this repository separates **observed historical order-book data** (`data/raw/`), **estimated in-sample parameters**, **model assumptions**, and **simulated replay / Monte Carlo results**. No metric in this workspace represents an actual live IMC Prosperity 4 portal score.

---

## 1. Competition Specification & Data Coverage Boundaries

| Aspect | Current Status / Coverage | Implication & Mitigation |
| :--- | :--- | :--- |
| **Algorithmic Datasets** | Complete public CSV archives for Round 1 (`Day -2..0`), Round 2 (`Day -1..1`), Round 3 (`Day 0..2`), Round 4 (`Day 1..3`), and Round 5 (`Day 2..4`), audited in [`prosperity4_manifest.json`](../data/manifests/prosperity4_manifest.json). | One chronological day per round (`Day 0` R1, `Day 1` R2, `Day 2` R3, `Day 3` R4, `Day 4` R5) is reserved exclusively for single-pass out-of-sample evaluation. Three daily trajectories per round remain narrow for regime exhaustion; circular block bootstrap and synthetic Monte Carlo stress-tests supplement single-day OOS estimates. |
| **Per-Tick Lambda / Runtime Limits** | Exact numeric server timeout and `lambda` payload bounds were not embedded in historical raw CSVs ([`COMPETITION_SPECIFICATION.md`](competition/COMPETITION_SPECIFICATION.md)). | Measured per-tick runtime stays between `0.034 ms` (R1) and `0.692 ms` (50-asset R5), keeping at least `4x–25x` headroom below standard sub-`3 ms` contest thresholds. |
| **Position Limits** | Confirmed in archived rules/docs for `±80` (R2), `±200/300` (R3–R4), and `±10` (R5). Round 1 `±20` (`ASH_COATED_OSMIUM`, `INTARIAN_PEPPER_ROOT`) is treated as a configurable assumption where earlier Tutorial vs R1 docs diverged. | [`Round1Submission`](../traders/round1/submission.py) enforces `±20` defensively via a single constant (`POSITION_LIMITS`). |
| **Live Competition Execution** | No live submission scorecard or portal leaderboard fills are stored locally. | All PnL, Sharpe ratios, and drawdowns are explicitly tagged as **simulated historical replay** or **synthetic Monte Carlo** outcomes. |

---

## 2. Backtesting & Execution Simulator Limitations

1. **Resting Queue Approximation (`queue_aware` vs Matching Engine)**:
   - Historical snapshots provide aggregated L1–L3 levels rather than per-order arrival queues or full message-by-message L3 feeds. Under [`FillMode.QUEUE_AWARE`](../src/prosperity_toolkit/execution/simulator.py), passive fills only trigger when an observed historical counterparty trade or opposite-side price move sweeps through our price level minus conservatively modeled queue ahead.
   - True competitive queue priority against **other human participants** on the live Prosperity exchange cannot be reconstructed purely from anonymized historical bot replays—every strategy is therefore stress-tested across `conservative`, `queue_aware`, and `touch` fill modes.
2. **Simultaneous Batch Limit Cancellation**:
   - In accordance with Prosperity rules, any symbol whose resting bid sum (`pos + sum(buy_qty) > Q_max`) or ask sum (`pos - sum(|sell_qty|) < -Q_max`) exceeds the position bound triggers full-batch cancellation for that symbol on that tick. Backtests enforce this check strictly, which constrains aggressive multi-level stacking—especially under Round 5's `±10` cap.
3. **Zero Explicit Fee Schedule on Exchange Trades**:
   - Standard Prosperity 4 spot/options order-book trades incur zero per-lot exchange fees (unlike Manual R1 Ember Mushroom `0.10`/unit and Manual R5 quadratic impact fees), meaning adverse selection and spread-crossing slip act as the primary transaction costs simulated.

---

## 3. Strategy & Statistical Validation Limitations

1. **In-Sample / Out-of-Sample Sample Size**:
   - Even with `10,000` timestamps per day, cross-day structural drift (such as `SNACKPACK_CHOCOLATE + VANILLA` equilibrium shifting `-98.2` ticks between `Day 2` and `Day 3`, or `ROBOT_DISHES` volatility jumping `2.8x` on `Day 4`) demonstrates that three trading days cannot span all macro regimes.
2. **Round 4 Edge-Turnover Trade-Off (`EXP-R4-001`)**:
   - After aligning `M67_BUMP = 0.5` cleanly to the validated IS plateau (`m67_bump = 0.5, mm_edge = 5.5`), `Round4Submission` outperforms `Round3Ungated` on annualized `Sharpe_252` across every fill mode (`0.3613` vs `0.3488` `queue_aware`), flips `VELVETFRUIT_EXTRACT` from `-328.50` to **`+1,027.00`**, and cuts max drawdown **`-10.8%`** (`3,250.50 -> 2,901.00`), while trading slightly fewer `HYDROGEL_PACK` fills (`11,741.00` vs `12,048.00` `queue_aware`, vs `13,259.50` vs `12,284.50` under `touch`). Separately, aggressive Round 4 spot-chasing parameters (`s_alpha = 0.85`) remain intentionally excluded after failing CSCV/DSR (`PBO = 0.9714`).
3. **Round 5 Sub-Tick Cointegration (`0.16` ticks) & Single-Day Flow Scope**:
   - Shifting resting passive quotes on `PEBBLES_*` underperformed unbiased wall-mid quoting (`PM-005`), so `traders/round5/submission.py` decouples passive quoting from atomic IOC cross-taking (`+15,469.00` OOS on `Pebbles`), capturing `88.3%` of the historical single-day public-trade spread ceiling (`+123,173.00` vs `~139.4k`). Full live portal rounds aggregate multi-day sessions and interactive order flow beyond single-day historical replays.
4. **Executed Notebook & Validation Sync**:
   - All five research notebooks (`01`–`05`) execute cleanly in place via `nbconvert --execute`, directly matching CLI evaluation tables (`r1_*`–`r5_*` and `manual_challenges_summary.csv`).

## 4. Manual Challenge Uncertainty (`docs/manual/`)

Unlike exchange CSVs, opponent manual submissions are unobserved during each live round:
- Exact payoff formulas (`251%` annualized `Aether Crystal` vol, `AC_40_BP` payoff `10`, `9` Ignith goods, Round 3 cubic penalty) come directly from round problem statements (`MANUAL_CHALLENGES.md`), while uncertain opponent variables (competing human auction demand in R1, peer Speed distributions in R2, cohort mean second-bid $\bar{b}_2$ in R3, and Ignith edge dispersion $\sigma_i$ in R5) are modeled strictly via **ex-ante Bayesian priors and Cognitive Hierarchy sensitivity sweeps** supporting each round's final portal submission.
