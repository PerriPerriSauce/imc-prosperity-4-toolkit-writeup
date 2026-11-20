# Strategy & Simulation Postmortems

Documenting structural failures and refuted hypotheses keeps quantitative modeling honest and prevents regressions across strategies.

---

## `PM-001` — Naive Symmetric L1 Quoting Suffers Quote Jitter & Drift Saturation (Rounds 1–2)

- **Incident Context**: Naive symmetric market makers (`SymmetricMM` in R1, `SymmetricMM_80` in R2) quoted equidistantly around noisy L1 midpoints or slow moving averages without inventory skew or drift filtering.
- **Root Cause**:
  1. Thin insider/repricing L1 prints create artificial high-frequency variance (`dmid_std ~ 1.75–1.92` ticks in R1–R2 IS) with `-0.45` lag-1 bounce autocorrelation, triggering fill-and-fade adverse selection.
  2. Without drift-aware carrying and strong inventory skew, quotes on `INTARIAN_PEPPER_ROOT` ride the deterministic `+0.10000/tick` trend (`R^2 = 1.0000`) into maximum short saturation (`-80`).
- **Observed Impact (`queue_aware`, `±80`)**:
  - Round 1 `Day 0`: `SymmetricMM` achieved `+21,731.00` (`MaxDD = 2,455.00`, `IR_tick = 0.02034`) vs. **`+91,098.00`** (`MaxDD = 1,405.00`, `IR_tick = 0.05445`) for `Round1Submission`; in R1 MC (`N=40`), `SymmetricMM` lost money on `37.5%` of sessions (`CVaR95 = -5,711.00`).
  - Round 2 `Day 1`: `SymmetricMM_80` collapsed to **`-20,294.50` OOS PnL (`IR_tick = -0.02109`, `MaxDD = 21,729.50`)**, whereas `Round2Submission` earned **`+94,209.00` (`MaxDD = 1,401.00`, `IR_tick = 0.05466`)**.
- **Permanent Control**: Anchor `ASH_COATED_OSMIUM` strictly on `10,000` (with wall-mid fallback) and carry long `INTARIAN_PEPPER_ROOT` against max-volume resting ask/bid walls with asymmetric inventory skew.

---

## `PM-002` — Misspecified Calendar TTE & Destructive Spot Delta Hedging (Round 3)

- **Incident Context**: Initial options modeling (`OptionsVolatilityContract`) hardcoded calendar `TTE = 5 - d` days and hedged net option delta passively/actively on `VELVETFRUIT_EXTRACT`.
- **Root Cause**:
  1. Exchange option makers price `VEV` implied vols along an effective longer horizon rather than literal remaining days; fixed `T = 5` pricing systematically misvalued strikes and bled `-1,051.00` OOS (`Day 2`, `IR_tick = -0.00030`, `MaxDD = 24,608.50`).
  2. Attempting to mechanically delta-hedge option inventory via `VELVETFRUIT_EXTRACT` crosses wide spot spreads (`~5` ticks) repeatedly while underlying OU moves revert cleanly around `~5,250`, destroying options edge.
- **Permanent Control**: Quote `VEV_4000..5500` off EWMA **horizon-free total implied volatility** $v_K = \sigma_K \sqrt{\tau}$ (dropping worthless `VEV_6000/6500` `0/1` noise contracts) with **zero spot delta hedging** (`Round3Submission`: **`+95,093.00` OOS**, `IR_tick = 0.00584`).

---

## `PM-003` — Conflating 1-Tick Spread Bounce (`Mark 67`) with Informed Flow (Round 4)

- **Incident Context**: Naive mark-out studies pooling `t -> t+k` starting at `t = 0` identified `Mark 67` buyer (`+1.97` ticks at `t -> t+50`) as a strong directional predictor in Round 4 `VELVETFRUIT_EXTRACT`.
- **Root Cause**: Separating the immediate execution bounce (`t -> t+1`, unobserved at decision time anyway under causal `t - 100` delivery) from true subsequent drift (`t+1 -> t+200`) on IS Days `1–2` (`r4_counterparty_velvet_midmoves.csv`) proved `Mark 67 BUY` (`n=119`) is strictly a `-1.765` pre-dip + `+1.924` 1-tick bounce followed by insignificant `causal_1_to_200 = +0.113` (`ou_adj t = 1.56`). Meanwhile, `Mark 14 SELL` (`n=215`, `ou_adj_h200 = +3.788`, `t = +4.58`) and `Mark 55 BUY` (`n=404`, `ou_adj_h200 = +2.460`, `t = +4.07`) carry zero 1-tick bounce and persistent causal drift.
- **Permanent Control**: Condition strictly on causal `t+1 -> t+H` mark-outs (`state.market_trades` delayed by `t - 100`), discard `Mark 67`, and trade only `Mark 14 SELL` and `Mark 55 BUY` signals (`Round4Submission` gains **`+11,153.50` OOS** above `Round3NoFlow`: `+260,540.00` vs. `+249,386.50` with `-2,581.00` lower MaxDD).

---

## `PM-004` — EMA Lag Toxicity on Wide Random Walks (Round 5)

- **Incident Context**: Reusing smoothed EMA fair-value estimators on Round 5's `50` volatile assets (`Robots`, `Panels`, `Microchips`, tight `±10` limit) left quotes trailing large martingale steps.
- **Root Cause**: A lagged EMA after random-walk shocks creates stale one-sided limit orders picked off by fast takers (`EmaSymmetricMM_All50` suffered `44,486.50` IS / `29,130.00` OOS MaxDD, `PnL/MaxDD = 3.94`).
- **Observed Resolution**: Zero-lag wall-midpoint anchoring scaled by online step-volatility EWMAs (`vol_skew_mult = 0.18`, `edge_frac = 0.14`) plus discrete `MICROCHIP_CIRCLE` 50/100/150/200-tick lag adjustments halved OOS MaxDD (`29,130.00 -> 14,961.50`) and lifted `PnL/MaxDD` `1.66x` (`3.94 -> 6.53`, `+97,628.00` OOS).

---

## `PM-005` — Non-Actionable `Pebbles` Arbitrage & Counterproductive `VOL_GUARD` Halts (Round 5)

- **Incident Context**: Early Round 5 prototypes cross-traded `Pebbles` deviations around $\sum_{i=1}^5 P_i = 50{,}000$ and hard-halted quoting on `Robots`/`Microchips` when short-window volatility spiked (`VOL_GUARD`).
- **Root Cause**:
  1. **`Pebbles`**: Although $\sum P_i = 50{,}000 \pm 2.82$ (`ADF t = -70.16`, `0.16`-tick half-life) holds structurally, `2.82`-tick basket dispersion sits completely inside the combined `12–14` tick quoted spreads of five legs—attempting spread-crossing IOC arbitrage produces zero profitable fills while resting passive skew suffers adverse lag.
  2. **`VOL_GUARD` Halts**: Shutting down quoting completely during active pulses forfeited spread capture on re-anchoring books, whereas proportional volatility-scaled skew (`vol_skew_mult * vol_ema`) protects inventory without shutting off maker EV.
- **Permanent Control**: Pruned `Pebbles` crossing and hard `VOL_GUARD` halts from `traders/round5/submission.py`, keeping only verified passive vol-scaled AS quoting and `MICROCHIP_CIRCLE` causal lag adjustment.
