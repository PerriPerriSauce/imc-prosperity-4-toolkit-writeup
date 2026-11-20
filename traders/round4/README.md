# Round 4 Submission Trader (Counterparty Flow + Options)

- **Official Position Limits**: Spot `±200`; Vouchers (`VEV_4000..6500`) `±300`.
- **Submission File**: [`traders/round4/submission.py`](submission.py) (`spot_scale=30.0, flow_weight=1.5, enter_band=10.0`).

## Strategy Logic
- Extends Round 3's Bayesian OU + Black-Scholes total-volatility engine with strictly causal prior-tick counterparty flow on `VELVETFRUIT_EXTRACT`: positive tilt after `Mark 14 SELL` (`t = +4.58` IS OU-adjusted drift) and `Mark 55 BUY` (`t = +4.07`), explicitly excluding `Mark 67` (non-causal 1-tick bounce).

## Verification & Held-Out OOS (`Day 3`, `queue_aware`)
- **IS Plateau (`Days 1 & 2`)**: `IR_tick = 0.01137`, `N_eff = 1.02`, `CSCV PBO = 0.0143`, `DSR_block = 0.9783`.
- **OOS Day 3**: **`+260,540.00` XIRECs** (`IR_tick = 0.01680`, `BlkSR_1k = 0.646`, `MaxDD = 71,177.00`, `3,669` fills, `0.293 ms/tick`; `+11,153.50` uplift above `Round3NoFlow`).
