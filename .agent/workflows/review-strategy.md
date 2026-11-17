# Workflow: Review Trading Strategy

Before marking a round strategy ready for deployment or evaluation:

1. **Platform Compatibility Audit**:
   - Verify strategy lives in a single standalone file.
   - Confirm it imports only from standard Python library, `datamodel`, and basic `numpy`.
   - Ensure zero imports from `src/prosperity_toolkit`.

2. **Position Limit Defense**:
   - Check that worst-case aggregate orders do not exceed position limits relative to `state.position`.
   - Verify negative quantities for sell orders.

3. **Performance Profiling**:
   - Verify per-tick runtime remains strictly under 1.5 ms on average.
   - Check state persistence via `traderData` JSON serialization.
