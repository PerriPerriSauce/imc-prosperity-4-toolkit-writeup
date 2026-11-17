# Backtesting Methodology

## 1. Simulation Protocols

A rigorous backtesting protocol guarantees that backtest results are reproducible and immune to look-ahead bias:
- **Strict Information Barrier**: Strategies only observe market state up to timestamp $t$. Past trades and order depths from $t' > t$ are strictly inaccessible.
- **Order Timing & Tick Alignment**: Orders placed at timestamp $t$ are matched against book depths prevailing at $t$ or subsequent incoming trades at $t+100$.
- **Adverse Selection Modeling**: Passive fills in directional markets must account for toxic flow—passive orders are disproportionately executed when the market moves adversely.

## 2. PnL Accounting Formulation

At any tick $t$, the portfolio state consists of cash balance $C_t$ and inventory positions $q_{i, t}$ across symbols $i \in \{1, \dots, M\}$.

Total marked portfolio value $V_t$ is computed via marked mid-prices $M_{i, t}$:
$$V_t = C_t + \sum_{i=1}^M q_{i, t} M_{i, t}$$

For conservative risk evaluation, we also track liquidation value $V_t^{\text{liq}}$ using the prevailing bid/ask top-of-book prices:
$$V_t^{\text{liq}} = C_t + \sum_{i=1}^M \begin{cases} q_{i, t} P_{\text{bid}, i}(t), & \text{if } q_{i, t} > 0 \\ q_{i, t} P_{\text{ask}, i}(t), & \text{if } q_{i, t} < 0 \\ 0, & \text{if } q_{i, t} = 0 \end{cases}$$
