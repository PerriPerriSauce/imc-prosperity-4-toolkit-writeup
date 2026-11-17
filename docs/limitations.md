# System Limitations, Modeling Assumptions & Unverified Scope

Quantitative transparency requires separating what our simulation framework proves from what it necessarily approximates. No backtest result in this repository should be interpreted as a guarantee of live competition performance.

---

## 1. Historical Replay & Execution Limitations

1. **Non-Endogenous Counterparty Flow**:
   - Historical CSV replay treats recorded `prices_round_N_day_D.csv` and `trades_round_N_day_D.csv` files as an immutable tape. Submitting passive orders or taking L1 liquidity does **not** alter subsequent bot quote placement, cancellation rates, or competing participants' reactions.
   - Consequently, taking large blocks repeatedly can appear artificially repeatable on static historical snapshots.
2. **Queue Position Uncertainty**:
   - The exchange CSV format reports aggregate resting volume at price levels 1–3 (`bid_volume_{1..3}`, `ask_volume_{1..3}`), without individual order timestamps or queue identifiers.
   - Our `queue_aware` fill model conservatively places our joining order *behind* existing resting depth at the touch (`rem_trade_vol > queue_ahead`), and assigns zero queue ahead only when our quote strictly price-improves the prevailing touch (`best_bid + 1` or `best_ask - 1`). However, it cannot observe competing human/bot penny-jumpers or order cancellations ahead of us within a 100-tick interval.
3. **Fill-Regime Bounds (`conservative` vs. `queue_aware` vs. `touch`)**:
   - We run every strategy across all three fill regimes. Any alpha that survives only in `touch` mode and disappears in `conservative`/`queue_aware` mode is rejected as optimistic fill bias.

---

## 2. Monte Carlo Simulator Assumptions

1. **Parametric Fair-Value Processes**:
   - `MonteCarloEngine` currently models mean-reverting dynamics via Gaussian Ornstein-Uhlenbeck transitions and trending dynamics via Gaussian arithmetic random walks. Empirical excess kurtosis in order-book jumps or state-dependent regime switches may cause parametric confidence bands to understate extreme tail risk unless augmented with jump pulses.
2. **Constant-Intensity Exogenous Trade Arrivals**:
   - `simulate_trade_arrivals` samples taker order arrivals independently with constant `arrival_prob` and uniform size bounds, rather than state-dependent (Hawkes self-exciting or spread-elastic) arrival intensity. In live exchange runs, narrowing spreads often attract higher arrival intensity and potentially higher adverse-selection toxicity.

---

## 3. Competition Specification Uncertainties

As tracked in [COMPETITION_SPECIFICATION.md](competition/COMPETITION_SPECIFICATION.md):
- **Unverified Position Limits**: Official per-product position limits for Rounds 0–4 have not yet been verified against official IMC Prosperity 4 portal documentation; simulations currently assume $Q_{\max} = 20$ as an explicit configurable constant.
- **Unverified Sandbox Resource Caps**: Exact container RAM limits, stdout truncation thresholds, `traderData` max byte sizes, and exact per-tick timeout ceilings are unverified locally (we benchmark submissions below `0.10 ms/tick`, an order of magnitude below typical 2–3 ms limits).
- **Incomplete Round Ingestion**: Rounds 2–5 historical datasets and manual challenges have not yet been ingested or modeled.
