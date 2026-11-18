# Quantitative Research: Inventory Risk & Position Limit Management

## 1. Why Unhedged Market Making Is Secretly Directional

A naive market maker that quotes symmetric offsets around an observed mid-price appears market-neutral on paper—it posts equal bid and ask sizes every tick. In practice, **order arrivals are not symmetric conditional on price trajectory**.

When an asset drifts systematically (`INTARIAN_PEPPER_ROOT` climbing $+1{,}000$ XIRECS per day) or trends temporarily during an Ornstein-Uhlenbeck excursion (`ASH_COATED_OSMIUM`), passive quotes experience **one-sided fill pressure**. In Round 2 (`±80` cap), unskewed `SymmetricMM_80` suffered `-20,294.50` XIRECS OOS losses precisely because resting asks absorbed buy flow early in each rally and left the book pinned short against a trending tape. Under tighter limits or higher volatility (`±10` cap in Round 5), even two consecutive fills on a `15`-tick random walk without skew expose a quarter of the day's expected spread budget.

## 2. Reservation Price Skewing & Capacity Calibration

Following Avellaneda–Stoikov CARA utility over a local clearing horizon $(T - t)_{\text{eff}}$, we quote symmetrically around the **reservation (indifference) price**:
$$r_t = FV_t - \tilde{\gamma} \cdot q_{\text{start}}$$
where $\tilde{\gamma}$ scales inversely with position capacity $Q_{\max}$ and proportionally with local innovation variance $\sigma_{\Delta P}^2$:
- **Round 1 (`Q_max = 20`)**: $\tilde{\gamma} = 0.80$ keeps `INTARIAN_PEPPER_ROOT` inventory tightly mean-centered (`267.00` MaxDD vs `886.00` for `SymmetricMM`, cutting Monte Carlo `ProbLoss` from `20%` to `0%`).
- **Round 2 (`Q_max = 80`)**: $\tilde{\gamma} = 0.75$ with `min_edge = 3.5` captures full scale capacity (`+27,463.00` OOS, `419.50` MaxDD).
- **Rounds 3–4 (`Q_max = 200` Spot / `300` Options)**: Option net delta ($\sum_K q_K \Delta_K$) aggregates across strikes and re-centers inside `±HEDGE_BAND = 10` on `VELVETFRUIT_EXTRACT` so option inventory never leaves naked directional exposure beyond the `±200` spot limit.
- **Round 5 (`Q_max = 10` across `50` Assets)**: Raising skew to `1.25` (and `1.875` on high-volatility `Robots`/`Microchips`) while sizing passive quotes to `QUOTE_CLIP = min(10, rem_cap)` maximizes turnover inside tight caps without letting single-direction pulse runs trap full inventory near $\pm 10$.

![INTARIAN_PEPPER_ROOT Inventory Trajectory on Day 0 OOS](file:///c:/Users/pierr/Desktop/imc-prosperity-4-toolkit-writeup/reports/figures/r1_inventory_trajectory.png)

## 3. Prosperity's Starting-Position Limit Constraint

A subtle exchange mechanic in IMC Prosperity causes many theoretically sound market makers to fail silently in production: **the exchange evaluates position limits simultaneously across ALL orders submitted in a tick against the tick's starting inventory $q_{\text{start}}$**, *not* sequentially after your own aggressive taker orders fill.

### Concrete Failure Example
Suppose $Q_{\max} = 20$ and you enter the tick with $q_{\text{start}} = -15$. Your taker logic buys `+10` against a mispriced ask (assuming `post_take_pos = -5`) and then tries to quote passively short `-15` (assuming `-5 - 15 = -20`). Because the exchange evaluates both legs independently against starting inventory:
$$q_{\text{start}} + \sum_{Q_o < 0} Q_o = -15 - 15 = -30 < -20$$
the engine **cancels your entire order batch for that product**!

To guarantee zero silent cancellations across all 50 securities:
$$q_{\text{rem, buy}} = \max(0, Q_{\max} - q_{\text{start}} - q_{\text{take, buy}}), \qquad q_{\text{rem, sell}} = \max(0, Q_{\max} + q_{\text{start}} - q_{\text{take, sell}})$$
where $q_{\text{take, buy}}, q_{\text{take, sell}} \ge 0$ accumulate strictly across taker legs before computing remaining passive capacity. Every submission trader (`traders/round{1..5}/submission.py`), `ExecutionSimulator.validate_orders_against_limits`, and integration suite verifies zero worst-case limit breaches under this rule.
