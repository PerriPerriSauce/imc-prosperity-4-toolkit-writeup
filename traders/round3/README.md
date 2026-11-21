# Round 3 Submission Trader (Spot + European Call Vouchers `VEV_4000..6500`)

- **Official Live Result (`Team 63-bit integers`)**: Algo **`+213,104`** · Manual `+78,225` · Total `+291,329` XIRECs *(Phase 2 leaderboard reset)*.
- **Official Position Limits**: Spot (`HYDROGEL_PACK`, `VELVETFRUIT_EXTRACT`) `±200`; Vouchers (`VEV_4000..6500`) `±300`.
- **Submission File**: [`traders/round3/submission.py`](submission.py) (`spot_scale=30.0, enter_band=10.0`).

## Strategy Logic
- Maintains Bayesian-updated OU anchors on `HYDROGEL_PACK` and `VELVETFRUIT_EXTRACT` and prices `VEV_5000..5500` via scale-free Black-Scholes total implied volatility (`VEV_4000/4500` intrinsic parity; worthless `VEV_6000/6500` omitted). Deliberately omits spot delta hedging after IS ablation proved it adds adverse taker slippage.

## Post-Contest Audit & Held-Out OOS (`Day 2`, `queue_aware`)
- **IS Plateau (`Days 0 & 1`)**: `IR_tick = 0.01593`, `N_eff = 1.01`, `CSCV PBO = 0.0000`, `DSR_block = 0.9966`.
- **OOS Day 2**: **`+95,093.00` XIRECs** (`IR_tick = 0.00584`, `BlkSR_1k = 0.573`, `MaxDD = 75,774.00`, `2,939` fills, `0.325 ms/tick`).
