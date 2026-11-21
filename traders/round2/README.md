# Round 2 Submission Trader (`ASH_COATED_OSMIUM`, `INTARIAN_PEPPER_ROOT`)

- **Official Live Result (`Team 63-bit integers`)**: Algo **`+115,543`** · Manual `+200,716` · Total `+316,259` XIRECs (`Phase 1: +521,181`).
- **Official Position Limits**: `±80` contracts per product.
- **Submission File**: [`traders/round2/submission.py`](submission.py) (`min_edge=2.5, inventory_skew=0.40`).

## Strategy Logic
- Applies the stationary `10,000`-anchored Osmium MM and `+0.10/tick` structural Pepper Root carry architecture under Round 2 IS (`Days -1 & 0`) calibration.

## Post-Contest Audit & Held-Out OOS (`Day 1`, `queue_aware`)
- **IS Plateau (`Days -1 & 0`)**: `IR_tick = 0.06052`, `N_eff = 1.04`, `CSCV PBO = 0.3000`, `DSR_block = 1.0000`.
- **OOS Day 1**: **`+94,209.00` XIRECs** (`IR_tick = 0.05466`, `BlkSR_1k = 8.237`, `MaxDD = 1,401.00`, `832` fills, `0.028 ms/tick`; vs. `-20,294.50` unskewed `SymmetricMM_80`).
