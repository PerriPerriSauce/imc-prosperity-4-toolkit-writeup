# Round 1: Market Fundamentals & Microstructure

## 1. Tradable Instruments
- **ASH_COATED_OSMIUM**: Mean-reverting stable asset with discrete integer valuation and active market-maker bots.
- **INTARIAN_PEPPER_ROOT**: Directionally drifting agricultural commodity exhibiting momentum and trend persistence.

## 2. Research Focus & Microstructure Hypotheses
1. **OSMIUM Market Making**:
   - Order book spreads oscillate between 2 and 4 ticks.
   - Hypothesis: Market-maker bots quote fixed offsets around an unobserved fair value $FV_t$.
2. **PEPPER Trend Following**:
   - Drift process can be modeled via exponential moving averages or Kalman filtering.

## 3. Position & Risk Constraints
- Position Limits: $\pm 20$ units per product.
- Exchange Order Limit: Aggregate simultaneous order quantity check against starting position.
