# Quantitative Research: Optimal Market Making

## 1. The Avellaneda-Stoikov Framework

A market maker continuously posts bid quotes $r^b$ and ask quotes $r^a$ around fair value $s$, taking inventory risk $q \in [-Q_{\max}, Q_{\max}]$.

Under CARA utility with risk aversion $\gamma > 0$ and terminal horizon $T$, the optimal reservation (indifference) price $r(s, q, t)$ is:
$$r(s, q, t) \approx s - q \gamma \sigma^2 (T - t)$$

The optimal quoted half-spread $\delta(t)$ balances fee capture against adverse selection:
$$\delta^*(t) = \frac{1}{\gamma} \ln \left( 1 + \frac{\gamma}{\kappa} \right)$$
where $\kappa$ is the Poisson intensity parameter of trade arrivals.

The optimal bid and ask quotes are:
$$r^b(s, q, t) = r(s, q, t) - \frac{\delta^*(t)}{2}, \quad r^a(s, q, t) = r(s, q, t) + \frac{\delta^*(t)}{2}$$

## 2. Discrete Integer Optimization

In Prosperity, quotes are constrained to discrete integer ticks:
$$r^b_{\text{int}} = \lfloor r^b \rfloor, \quad r^a_{\text{int}} = \lceil r^a \rceil$$
Furthermore, passive order sizing is constrained by aggregate position limits:
$$q + \sum \Delta q_{\text{buy}} \le Q_{\max}, \quad q + \sum \Delta q_{\text{sell}} \ge -Q_{\max}$$
