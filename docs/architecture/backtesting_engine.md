# Architecture: Backtesting & Execution Engine

## 1. Disentangling Backtester Components

A core design principle of this repository is distinguishing between:
- **Historical Market Replay**: Feeds static historical states tick-by-tick to strategies.
- **Order Matching Simulation**: Evaluates order validity, priority, and fills.
- **Strategy Evaluation**: Measures risk, return, drawdown, and statistical metrics.
- **Monte Carlo Simulation**: Generates synthetic market sessions to test passive quoting strategies against endogenous bot counterparties.

## 2. Order Matching Mechanics

### A. Taker Execution (Crossing Top of Book)
When a strategy submits an order with price $P_{\text{order}}$ crossing the prevailing book:
- For a buy order ($Q > 0$): matches if $P_{\text{order}} \ge P_{\text{ask}, 1}$. Fills at $P_{\text{ask}, 1}$ up to available depth $V_{\text{ask}, 1}$.
- For a sell order ($Q < 0$): matches if $P_{\text{order}} \le P_{\text{bid}, 1}$. Fills at $P_{\text{bid}, 1}$ up to available depth $V_{\text{bid}, 1}$.

### B. Maker Execution (Passive Liquidity Provision)
In historical replay, resting passive limit orders cannot endogenously attract trades. We support three configurable fill regimes:
1. **Conservative Fill Model**: A resting limit order at price $P_{\text{limit}}$ is executed if and only if a historical trade occurs *through* the level:
   $$\text{Fill Condition}_{\text{Buy}} \iff P_{\text{trade}} < P_{\text{limit}}$$
   $$\text{Fill Condition}_{\text{Sell}} \iff P_{\text{trade}} > P_{\text{limit}}$$
2. **Touch Fill Model**: Fills when $P_{\text{trade}} = P_{\text{limit}}$. (Recognized as subject to optimistic fill bias).
3. **Queue-Aware Fill Model**: Tracks historical volume executed at $P_{\text{limit}}$ to simulate queue depletion.

### C. Position Limit Enforcement
Prosperity enforces limits across all active orders against the starting tick position $pos_{\text{start}}$:
$$\text{Worst-case Long} = pos_{\text{start}} + \sum_{o \in \text{Orders}, Q_o > 0} Q_o \le \text{Limit}$$
$$\text{Worst-case Short} = pos_{\text{start}} + \sum_{o \in \text{Orders}, Q_o < 0} Q_o \ge -\text{Limit}$$
If either condition is violated, the exchange cancels all submitted orders for that product on that tick.
