# Final Round & Multi-Round Architecture Synthesis (Rounds 1–5)

## 1. Cross-Round Structural Progression

Across Rounds 1 through 5, **IMC Prosperity 4** escalated both price-process diversity and portfolio constraints on [`Trader.run`](../../src/prosperity_toolkit/competition/datamodel.py):

| Round | Active Universe | Official Limits | Promoted Microstructural Signal | Pruned / Negative Finding | Submission |
| :---: | :--- | :---: | :--- | :--- | :--- |
| **R1** | `ASH_COATED_OSMIUM`, `INTARIAN_PEPPER_ROOT` | `±80` | Fixed `10k` OU anchor + max-wall carry on `+0.10/tick` trend | Naive L1 `SymmetricMM` variance & `37.5%` MC loss | [`traders/round1/submission.py`](../../traders/round1/submission.py) |
| **R2** | `ASH_COATED_OSMIUM`, `INTARIAN_PEPPER_ROOT` | `±80` | `min_edge=2.5, skew=0.40` plateau; `+25%` MAF arrival lift (`+15.2%` MC) | Unskewed `SymmetricMM_80` (`-20,294.50` OOS bleed) | [`traders/round2/submission.py`](../../traders/round2/submission.py) |
| **R3** | `HYDROGEL_PACK`, `VELVETFRUIT_EXTRACT`, `VEV_4000..5500` | `±200` / `±300` | Bayesian OU + Black-Scholes total-vol $v_K = \sigma_K \sqrt{\tau}$ | Fixed-TTE BS (`-1,051` OOS) & spot delta-hedging drag | [`traders/round3/submission.py`](../../traders/round3/submission.py) |
| **R4** | Same `12` assets + `Mark 01..67` prints | `±200` / `±300` | Strictly causal prior-tick `Mark 14` SELL / `Mark 55` BUY flow (`+11,153.50` OOS) | `Mark 67` BUY (`+1.924` 1-tick bounce, zero causal edge) | [`traders/round4/submission.py`](../../traders/round4/submission.py) |
| **R5** | `50` new spot securities (`10` categories) | `±10` (`max 500`) | Vol-scaled AS (`vsm=0.18, ef=0.14`) + `MICROCHIP_CIRCLE` 50–200 lag | `Pebbles` crossing (`std=2.82` < `12–14`t spread) & `VOL_GUARD` halts | [`traders/round5/submission.py`](../../traders/round5/submission.py) |

## 2. Held-Out Simulated Out-of-Sample Scorecard (`queue_aware`)

*Epistemic disclosure: Algorithmic metrics below represent single-day held-out chronological replays under strict price-time queue conservation (`queue_aware`) and causal `t - 100` trade lag—**never** live portal scores. Round 1–2 form Phase 1 (`+185,307.00`); Round 3–5 form Phase 2 (`+453,261.00`); Cumulative 5-Day OOS = `+638,568.00` XIRECs.*

| Round | Held-Out OOS Day | Key Baseline (`queue_aware`) | Submission OOS PnL | `IR_tick` (`95% Boot CI`) | `BlkSR_1k` | `MaxDD` (`PnL/DD`) | `PBO` ($N_{\text{eff}}$) | `DSR_block` | Latency |
| :---: | :---: | :--- | ---: | :--- | :---: | ---: | :---: | :---: | :---: |
| **R1** | `Day 0` | `SymmetricMM` (`21,731.00`) | **`+91,098.00`** | `0.05445` `[0.0505, 0.0587]` | `9.327` | `1,405.00` (`64.84`) | `0.129` (`1.02`) | `1.0000` | `0.0204 ms` |
| **R2** | `Day 1` | `SymmetricMM_80` (`-20,294.50`) | **`+94,209.00`** | `0.05466` `[0.0509, 0.0584]` | `8.237` | `1,401.00` (`67.24`) | `0.300` (`1.04`) | `1.0000` | `0.0281 ms` |
| **R3** | `Day 2` | `OptionsVolContract` (`-1,051.00`) | **`+95,093.00`** | `0.00584` `[-0.0112, 0.0213]` | `0.573` | `75,774.00` (`1.26`) | `0.000` (`1.01`) | `0.9966` | `0.3249 ms` |
| **R4** | `Day 3` | `Round3NoFlow` (`249,386.50`) | **`+260,540.00`** | `0.01680` `[0.0010, 0.0335]` | `0.646` | `71,177.00` (`3.66`) | `0.014` (`1.02`) | `0.9783` | `0.2925 ms` |
| **R5** | `Day 4` | `EmaSymMM_All50` (`114,851.00`) | **`+97,628.00`** | `0.02624` `[0.0105, 0.0412]` | `1.108` | `14,961.50` (`6.53`) | `0.543` (`1.14`) | `1.0000` | `0.5518 ms` |
| **Total** | **5 Days** | **Phase 1: `+185,307` / Phase 2: `+453,261`** | **`+638,568.00`** | — | — | — | — | **`>= 0.978`** | **`<= 0.552 ms`** |

## 3. Structural Principles Verified Across All Five Rounds

1. **Separating Causal Drift from Mechanical Execution Bounce**: Both Round 1–2 inside-spread flutter and Round 4 `Mark 67` (`+1.924` at `t -> t+1`, insignificant thereafter) prove why `t -> t+k` correlations fail under causal `t - 100` latency—only `Mark 14 SELL` (`t = +4.58`) and `Mark 55 BUY` (`t = +4.07`) survive strict post-execution causal attribution.
2. **Pruning Unprofitable Complexity**: Dropping R3 spot delta hedging, R5 `Pebbles` spread-trapped arbitrage, and R5 hard `VOL_GUARD` halts kept competition code fast (`<= 0.552 ms`), out-of-sample durable, and resilient under `conservative` matching (`91,098` R1 .. `260,537` R4 .. `97,514` R5).
3. **Matching Decision Discipline on Ex-Ante Manual Challenges**: Separately from exchange replays ([`MANUAL_CHALLENGES.md`](../manual/MANUAL_CHALLENGES.md)), Bayesian demand integration (`R1`), Level-3 Cognitive Hierarchy (`R2: 225,094.01`), Bayesian reserve screening (`R3: 76.00/u`), exact BS/Rubinstein + `4/d` KO MV hedging (`R4: -70.1%` std cut), and variance-adjusted KKT optimization under `-0.92` Phoenix floor (`R5: 855,944.53` EV) apply disciplined analytical optimization under explicit priors.

Proceed to [FINAL_WRITEUP.md](../../reports/FINAL_WRITEUP.md), [IMC_Prosperity4_Research_Writeup.pdf](../../reports/IMC_Prosperity4_Research_Writeup.pdf), and [dashboard.html](../../reports/dashboard.html) for full tables and interactive charts.
