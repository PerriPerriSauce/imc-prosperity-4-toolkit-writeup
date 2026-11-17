# Architecture: Backtesting & Execution Engine

## 1. Disentangling Simulation Components

A frequent pitfall in retail backtesting frameworks is conflating data replay, matching mechanics, accounting, and stochastic stress-testing inside a single monolithic loop. This toolkit isolates four distinct responsibilities:

```mermaid
flowchart LR
    Data["Historical CSV /<br/>Synthetic Path"] --> Replay["1. Replay Loop<br/>(MarketStateSnapshot)"]
    Replay --> Strat["Strategy /<br/>CompetitionAdapter"]
    Strat --> Limits["2a. Aggregate Starting-Pos<br/>Limit Gate"]
    Limits --> Taker["2b. Multi-Level Taker<br/>Book Walk"]
    Taker --> Maker["2c. Maker Matching<br/>(conservative | queue_aware | touch)"]
    Maker --> Port["3. PortfolioTracker<br/>(Cash + Carry-Forward Marks)"]
    Port --> Metrics["4. Risk & Diagnostics<br/>(Sharpe, MaxDD, VaR/CVaR, DSR, PBO)"]
```

---

## 2. Order Matching & Limit Mechanics (`execution/simulator.py`)

### A. Starting-Position Limit Verification
Before any fill executes on tick $t$, `validate_orders_against_limits` checks the aggregate worst-case buy and sell exposure against the tick's **starting inventory** $q_{\text{start}}$:
$$q_{\text{start}} + \sum_{o:\,Q_o > 0} Q_o \le Q_{\max}, \qquad q_{\text{start}} + \sum_{o:\,Q_o < 0} Q_o \ge -Q_{\max}$$
When `reject_on_limit_breach=True` (mirroring exchange behavior), any violation cancels the entire batch of orders for that product on that tick; when `False` (strict unit/integration tests), `PositionLimitExceededError` is raised immediately.

### B. Multi-Level Taker Matching (`match_taker_with_remainder`)
Crossing orders walk the sorted opposite book ladder (`sorted(asks)` for buys, `sorted(bids, reverse=True)` for sells), filling sequentially across L1, L2, and L3 levels up to available resting depth. Remaining resting liquidity is decremented inside the tick so multiple orders cannot double-consume the same level. Any unfilled remainder passes to passive maker matching.

### C. Maker Fill Regimes (`match_maker_orders`)
Passive orders are evaluated against contemporaneous market trades under three explicit fill models:
1. **`conservative`**: Fills a resting buy only if a trade prints *strictly through* the limit ($P_{\text{trade}} < P_{\text{limit}}$), and a resting sell only if $P_{\text{trade}} > P_{\text{limit}}$.
2. **`queue_aware`**: When $P_{\text{trade}} == P_{\text{limit}}$, looks up resting book volume $V_{\text{ahead}}$ at $P_{\text{limit}}$ on `OrderBookL2`. Only trade volume *exceeding* $V_{\text{ahead}}$ fills our order; quotes strictly inside the spread ($V_{\text{ahead}} = 0$) receive zero-queue fill priority.
3. **`touch`**: Fills immediately whenever $P_{\text{trade}}$ reaches or crosses $P_{\text{limit}}$ (used strictly as an upper sensitivity bound to expose touch-fill inflation).

---

## 3. Portfolio Accounting & Missing-Book Mark Continuity (`backtesting/engine.py`)

At the end of every tick, `PortfolioTracker` computes marked equity $V_t = C_t + \sum_i q_{i,t} M_{i,t}$. Because historical rounds (notably Round 1) contain one-sided (`~7.5%`) and completely empty (`~0.17%`) books where instantaneous `mid_price` is undefined (`None`), `BacktestEngine` maintains `last_marks[sym]`—carrying forward the last valid two-sided mid-price across empty/one-sided ticks rather than falsely marking inventory to `0.0` (see [PM-001](../postmortem.md)).
