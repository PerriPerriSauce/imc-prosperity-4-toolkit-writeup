# Post-Mortem & Trading Review

## 1. Post-Mortem Framework

When a live submission underperforms local backtests or encounters execution anomalies, a structured post-mortem is conducted:

1. **Anomaly Description**: Exact tick timestamp, symbol, and symptom (e.g. unexpected inventory breach, missed fills, execution timeout).
2. **Root Cause Analysis (RCA)**:
   - *Sandbox Environment Mismatch*: Differences between local Python 3.11 environment and platform sandbox.
   - *Adverse Selection Miscalculation*: Quoting too aggressively during directional trends.
   - *Order Cancellation Bug*: Over-allocating orders beyond starting inventory limits.
3. **Corrective Action**: Architecture or logic modification implemented to permanently prevent recurrence.
