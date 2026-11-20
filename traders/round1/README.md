# Round 1 Submission Trader (`ASH_COATED_OSMIUM`, `INTARIAN_PEPPER_ROOT`)

- **Official Position Limits**: `±80` contracts per product.
- **Submission File**: [`traders/round1/submission.py`](submission.py) (`min_edge=2.0, inventory_skew=0.40`).

## Strategy Logic
1. `ASH_COATED_OSMIUM`: `10,000`-anchored market making taking crossed asks/bids against `10,000` and posting penny-improved quotes clamped around `10,000 - inventory_skew * projected_pos ± min_edge`.
2. `INTARIAN_PEPPER_ROOT`: Wall-mid fair value tracking structural `+0.10/tick` drift (`R^2 = 1.0000`) to accumulate up to the `+80` carry limit while harvesting aggressive asks/bids.

## Verification & Held-Out OOS (`Day 0`, `queue_aware`)
- **IS Plateau (`Days -2 & -1`)**: `IR_tick = 0.05802`, `N_eff = 1.02`, `CSCV PBO = 0.1286`, `DSR_block = 1.0000`.
- **OOS Day 0**: **`+91,098.00` XIRECs** (`IR_tick = 0.05445`, `BlkSR_1k = 9.327`, `MaxDD = 1,405.00`, `712` fills, `0.020 ms/tick`; `ASH_COATED_OSMIUM +11,371`, `INTARIAN_PEPPER_ROOT +79,727`).
