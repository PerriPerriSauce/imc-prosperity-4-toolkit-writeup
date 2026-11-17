# System Limitations & Known Assumptions

## 1. Simulation Limitations

1. **Market Impact Non-Endogeneity in Replay**:
   - In pure historical replay, our submitted orders do not alter counterparty quote behavior or future price formation.
   - For large orders or aggressive market taking, market impact is strictly unmodeled in historical replay.
2. **Adverse Selection Approximations**:
   - Touch fills overestimate market-maker profitability. Conservative through-the-level fills underestimate liquidity capture.
3. **Queue Position Uncertainty**:
   - The exchange does not publish explicit order queue timestamps for resting orders at price levels. Queue priority must be approximated probabilistically.

## 2. Computational Constraints

1. **Per-Tick Time Budget**:
   - The competition platform allocates approximately 2–3 ms per tick. Complex nonlinear regressions or deep learning models cannot be run online tick-by-tick.
2. **State Memory Footprint**:
   - Python objects stored across ticks must be bounded (e.g. using `collections.deque(maxlen=N)`) to avoid triggering memory limits.
