# Quantitative Research: Inventory Risk & Position Limit Management

## 1. Why Unhedged Market Making Is Secretly Directional

A naive market maker that quotes symmetric offsets around an observed mid-price appears market-neutral on paper—it posts equal bid and ask sizes every tick. In practice, **order arrivals are not symmetric conditional on price trajectory**.

When an asset drifts upward (such as `INTARIAN_PEPPER_ROOT` rising $+1,000$ XIRECS per day) or trends temporarily during an Ornstein-Uhlenbeck excursion (`ASH_COATED_OSMIUM`), passive quotes experience **one-sided fill pressure**:
- In a downward micro-move, incoming sellers hit our bid repeatedly while our ask sits untouched. We accumulate long inventory $q > 0$ into a falling tape.
- Without inventory skewing, a symmetric quoter either hits its hard limit $+Q_{\max}$ and stops quoting buyside liquidity altogether, or holds a locked-in directional bet whose mark-to-market variance dwarfs spread capture.

That mechanism explains the wild variance observed in our `SymmetricMM` baseline on Round 1:
- On `Day -2`, `SymmetricMM` accumulated adverse directional inventory and suffered a **`1,723.00` XIRECS** drawdown with only `2,544.00` net PnL.
- In 30 calibrated Monte Carlo sessions (`conservative` fills), `SymmetricMM` lost money in **20% of runs** with $\text{CVaR}_{95} = -774.25$.

---

## 2. Reservation Price Skewing

To price inventory risk into quotes continuously, we adapt the Avellaneda-Stoikov reservation (indifference) price. Under CARA utility with risk aversion $\gamma > 0$, fair value $FV_t$, variance $\sigma^2$, and inventory $q_t$:
$$r(FV_t, q_t, t) = FV_t - q_t \gamma \sigma^2 (T - t)$$

For discrete intraday quoting over a rolling operational horizon, we parameterize the effective linear inventory penalty $\tilde{\gamma} = \gamma \sigma^2 (T - t)_{\text{eff}}$:
$$r_t = FV_t - \tilde{\gamma} \cdot q_{\text{start}}$$
Quotes are then centered around $r_t$ rather than $FV_t$:
- **When $q_{\text{start}} > 0$ (long inventory)**: $r_t < FV_t$, shifting both bid and ask downward. This simultaneously lowers our bid (reducing the chance of adding more long exposure) and brings our ask closer to the market (accelerating inventory mean reversion back toward zero).
- **When $q_{\text{start}} < 0$ (short inventory)**: $r_t > FV_t$, raising both quotes to discourage further shorts and incentivize covering.

### How Much Skew Is Optimal?
If $\tilde{\gamma}$ is too small (`0.10`), inventory lingers near $\pm Q_{\max}$ during trending segments; if $\tilde{\gamma}$ is too large relative to the half-spread, a moderate position shifts quotes across $FV_t$, sacrificing spread edge unnecessarily. Across our Round 1 2D plateau sweep (`Day -2` & `-1`), increasing $\tilde{\gamma}$ from `0.25` to `0.80` (with `min_edge = 1.5`) kept `INTARIAN_PEPPER_ROOT` inventory tightly mean-centered around `0` rather than pinning at `+20` or `-20`:

![INTARIAN_PEPPER_ROOT Inventory Trajectory on Day 0 OOS](../../reports/figures/r1_inventory_trajectory.png)

Notice in the OOS `Day 0` comparison above how `SymmetricMM` pins at `-20` and `+20` for thousands of consecutive ticks (creating huge exposure to adverse moves), whereas `Round1Submission` ($\tilde{\gamma} = 0.80$) cycles cleanly around neutral inventory—cutting OOS drawdown by **70%** (`886.00 -> 267.00`) and eliminating negative Monte Carlo tail sessions (`ProbLoss: 0.20 -> 0.00`, $\text{CVaR}_{95}: -774.25 \to +344.25$).

---

## 3. Prosperity's Starting-Position Limit Constraint

A subtle exchange mechanic in IMC Prosperity causes many theoretically sound market makers to fail silently in production: **the exchange evaluates position limits simultaneously across ALL orders submitted in a tick against the tick's starting inventory $q_{\text{start}}$**, *not* sequentially after your own aggressive taker orders fill.

### Concrete Failure Example
Suppose $Q_{\max} = 20$ and you enter the tick with $q_{\text{start}} = +12$:
1. Your taker logic spots a mispriced ask of size `5` and submits `Order(SYM, ask, +5)`.
2. **Buggy allocation**: You track a local `post_take_pos = 12 + 5 = 17`, compute `sell_capacity = 20 + 17 = 37`, and post a passive ask of size `-25` (or think `buy_capacity = 20 - 17 = 3` and forget worst-case checks if multiple passive orders exist). Even worse: if you enter at `q_start = -15`, take `+10` (thinking `post_take_pos = -5`), and then try to sell `-15` passively because `-5 - (-20) = 15`, the exchange checks:
   $$q_{\text{start}} + q_{\text{sell, total}} = -15 - 15 = -30 < -20$$
   and **cancels your entire order batch for that product**!
3. **Correct invariant**: Always allocate passive capacities strictly from `start_pos` minus same-direction taker quantities:
   $$q_{\text{rem, buy}} = \max(0, Q_{\max} - q_{\text{start}} - q_{\text{take, buy}})$$
   $$q_{\text{rem, sell}} = \max(0, Q_{\max} + q_{\text{start}} - q_{\text{take, sell}})$$
   Our `ExecutionSimulator.validate_orders_against_limits` and `tests/unit/test_strategies.py` enforce this exact exchange invariant on every tick.
