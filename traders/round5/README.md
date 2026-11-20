# Round 5 Submission Trader (50-Asset Market Making + Microchip Lead-Lag)

- **Official Position Limits**: Uniform `±10` contracts across all `50` symbols in `10` categories.
- **Submission File**: [`traders/round5/submission.py`](submission.py) (`vol_skew_mult=0.18, edge_frac=0.14, mc_beta=0.16`).

## Strategy Logic
- Volatility-scaled Avellaneda-Stoikov market making across all 50 books using online step-volatility EMAs, projected post-taker inventory skew, and discrete causal lead-lag shifts (`50/100/150/200` ticks) from `MICROCHIP_CIRCLE` to `OVAL/SQUARE/RECTANGLE/TRIANGLE` on large jumps (`|dx| >= 15`). Unprofitable `Pebbles` spread-crossing and `VOL_GUARD` halts are omitted.

## Verification & Held-Out OOS (`Day 4`, `queue_aware`)
- **IS Plateau (`Days 2 & 3`)**: `IR_tick = 0.03531` at `mc_beta = 0.16` (IS PnL `237,928.50`, `N_eff = 1.14`, `DSR_block = 1.0000`).
- **OOS Day 4**: **`+97,628.00` XIRECs** (`IR_tick = 0.02624`, `BlkSR_1k = 1.108`, `MaxDD = 14,961.50`, `PnL/MaxDD = 6.53`, `8,325` fills, `0.552 ms/tick`).
