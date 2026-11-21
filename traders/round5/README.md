# Round 5 Submission Trader (50-Asset Market Making + Microchip Lead-Lag)

- **Official Live Result (`Team 63-bit integers`)**: Algo **`+31,087`** · Manual `+120,165` · Total `+151,252` XIRECs *(capped live during fast 50-asset sprint before post-contest redesign; Phase 2 Official Total `+700,334`, 60th Worldwide / 8th AU / 13th APAC)*.
- **Official Position Limits**: Uniform `±10` contracts across all `50` symbols in `10` categories.
- **Submission File**: [`traders/round5/submission.py`](submission.py) (`vol_skew_mult=0.18, edge_frac=0.14, mc_beta=0.16`).

## Strategy Logic (Post-Contest Redesign)
- Volatility-scaled Avellaneda-Stoikov market making across all 50 books using online step-volatility EMAs, projected post-taker inventory skew, and discrete causal lead-lag shifts (`50/100/150/200` ticks) from `MICROCHIP_CIRCLE` to `OVAL/SQUARE/RECTANGLE/TRIANGLE` on large jumps (`|dx| >= 15`). Unprofitable `Pebbles` spread-crossing and `VOL_GUARD` halts (which hurt live experimentation) are omitted.

## Post-Contest Audit & Held-Out OOS (`Day 4`, `queue_aware`)
- **IS Plateau (`Days 2 & 3`)**: `IR_tick = 0.03531` at `mc_beta = 0.16` (IS PnL `237,928.50`, `N_eff = 1.14`, `DSR_block = 1.0000`).
- **OOS Day 4**: **`+97,628.00` XIRECs** (`IR_tick = 0.02624`, `BlkSR_1k = 1.108`, `MaxDD = 14,961.50`, `PnL/MaxDD = 6.53`, `8,325` fills, `0.552 ms/tick`).
