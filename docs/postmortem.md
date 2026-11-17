# Engineering & Quantitative Post-Mortems

This log records material defects, backtester discrepancies, and strategy failures discovered during development, along with root-cause diagnoses and permanent safeguards.

---

## PM-001: The `818,356` XIRECS Mark-to-Market Phantom Drawdown (`BacktestEngine`)

- **Date Discovered**: `2026-11-18` (Stage 5 evaluation on Round 1 raw CSVs)
- **Symptom**: While Round 0 strategies exhibited sensible drawdowns (`250–443` XIRECS) and Sharpe ratios (`0.29–0.43`), running the exact same market-making code on Round 1 produced catastrophic drawdowns (`591,153–818,378` XIRECS) and a Sharpe ratio of `0.00` despite generating `+14,000` terminal PnL.

### Root Cause Analysis (RCA)
1. **Unverified Assumption About Historical Order Books**: Round 0 (`EMERALDS`, `TOMATOES`) has two-sided books on 100% of ticks (`10,000 / 10,000`). We implicitly expected Round 1 books to follow suit.
2. **Missing-Book Regimes in Round 1**: Inspecting the raw Round 1 CSVs revealed that `7.5%–8.0%` of ticks (`726–795`/day) are **one-sided** (`bid` or `ask` completely absent) and `14–21` ticks/day are **completely empty** (recorded with `mid_price == 0.0`).
3. **Faulty Mark-to-Market Fallback**: In `BacktestEngine.run()`, portfolio equity was originally marked using:
   ```python
   marks = {sym: book.mid_price or 0.0 for sym, book in snap.books.items()}
   ```
   Because `OrderBookL2.mid_price` returns `None` whenever either side is empty, holding `20` units of `INTARIAN_PEPPER_ROOT` (`~12,000`/unit) on a one-sided tick caused `book.mid_price or 0.0` to value a `240,000` position at `0.0` for a single tick—creating a fake `-240,000` equity crash followed by a `+240,000` rebound one tick later. Across `1,000+` one-sided ticks, step return variance exploded, driving Sharpe to `0.00` and `MaxDD` past `800,000`.

### Corrective Action & Safeguards
1. Updated [engine.py](file:///c:/Users/pierr/Desktop/imc-prosperity-4-toolkit-writeup/src/prosperity_toolkit/backtesting/engine.py) to persist `last_marks[sym]`, carrying forward the last valid two-sided mid-price across empty and one-sided ticks (only falling back to `best_bid` / `best_ask` if no two-sided quote has ever been seen).
2. Updated [validation.py](file:///c:/Users/pierr/Desktop/imc-prosperity-4-toolkit-writeup/src/prosperity_toolkit/data/validation.py) to explicitly warn on empty-book `mid_price == 0.0` rows while rejecting `mid_price == 0.0` on non-empty books.
3. Added explicit empty-book and one-sided book test coverage across strategy and execution tests.

---

## PM-002: Spread Under-Capture in Stage 5 (`half_spread = 2.0` vs. Bot-Wall Quoting)

- **Date Discovered**: `2026-11-18` (Stage 5 $\to$ Stage 6 diagnostic audit)
- **Symptom**: Stage 5 `InventorySkewedMM` earned `9,067`–`9,714` on Round 1 OOS `Day 0` (`Sharpe = 0.40–0.43`), underperforming naive `SymmetricMM` on `Day 0` PnL (`10,825`) and capturing less than half of theoretical spread edge.

### Root Cause Analysis (RCA)
1. **Arbitrary Spread Heuristic**: We initialized `half_spread = 2.0` from generic Prosperity 2/3 intuition without measuring Round 1's actual L1–L3 spread distribution first.
2. **Empirical Reality**: Round 1 median spreads are **`16` ticks** on `ASH_COATED_OSMIUM` and **`12–14` ticks** on `INTARIAN_PEPPER_ROOT`, backed by two-tier market-maker bot walls. Quoting at `FV ± 2` inside a 16-tick spread voluntarily gave away `5–6` ticks of price improvement per leg and absorbed unnecessary adverse selection on L1 microprice flicker.

### Corrective Action & Safeguards
1. Replaced raw L1 microprice with **max-volume resting bot-wall midpoint** (`_popular_wall_mid`) to suppress inside-spread quote-jitter.
2. Replaced fixed `FV ± 2` quoting with **penny-improving** (`min(floor(r - min_edge), best_bid + 1)` / `max(ceil(r + min_edge), best_ask - 1)`), verified via 2D plateau selection (`PBO = 0.086`, `DSR = 1.0000`).
3. OOS `Day 0` `queue_aware` performance improved from `9,714.00` (`MaxDD 840.50`, `Sharpe 0.43`) to **`22,157.00`** (`MaxDD 267.00`, `Sharpe 1.19`).
