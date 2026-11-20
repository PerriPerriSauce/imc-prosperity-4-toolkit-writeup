"""Mathematical & Monte Carlo solvers for IMC Prosperity 4 manual challenges."""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from statistics import NormalDist
from typing import Literal

import numpy as np
from numpy.typing import NDArray
from scipy.optimize import minimize

_STD_NORM = NormalDist(0.0, 1.0)


# ---------------------------------------------------------------------------
# Round 1: "An Intarian Welcome" (Volume-Maximizing Clearing Auction)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AuctionOrder:
    """Single limit order in the Round 1 sealed opening auction."""

    price: int
    quantity: int  # > 0 for buy/bid, < 0 for sell/ask


@dataclass(frozen=True, slots=True)
class AuctionClearingResult:
    """Result of clearing a discrete single-price opening auction."""

    clearing_price: int
    matched_volume: int
    participant_filled: int
    participant_pnl: float


def clear_opening_auction(
    resting_orders: Sequence[AuctionOrder],
    participant_order: AuctionOrder | None = None,
    buyback_price: float = 30.0,
    fee_per_unit: float = 0.0,
) -> AuctionClearingResult:
    """Evaluate single clearing price maximizing traded volume (tie -> highest price).

    Note: Resting orders arrive ahead of `participant_order` under price-time priority.
    """
    all_orders = list(resting_orders)
    if participant_order is not None and participant_order.quantity != 0:
        all_orders.append(participant_order)

    if not all_orders:
        return AuctionClearingResult(
            clearing_price=0,
            matched_volume=0,
            participant_filled=0,
            participant_pnl=0.0,
        )

    prices = sorted({o.price for o in all_orders})
    best_price = prices[0]
    best_vol = -1

    for p in prices:
        demand = sum(o.quantity for o in all_orders if o.quantity > 0 and o.price >= p)
        supply = sum(-o.quantity for o in all_orders if o.quantity < 0 and o.price <= p)
        vol = min(demand, supply)
        # Tie-breaker: select strictly higher clearing price when matched volume ties
        if vol >= best_vol:
            best_vol = vol
            best_price = p

    if best_vol <= 0:
        return AuctionClearingResult(
            clearing_price=best_price,
            matched_volume=0,
            participant_filled=0,
            participant_pnl=0.0,
        )

    if participant_order is None or participant_order.quantity == 0:
        return AuctionClearingResult(
            clearing_price=best_price,
            matched_volume=best_vol,
            participant_filled=0,
            participant_pnl=0.0,
        )

    # Compute late participant fill under price-first, then resting-before-participant time priority
    p_qty = participant_order.quantity
    p_px = participant_order.price
    if p_qty > 0:
        if p_px < best_price:
            filled = 0
        else:
            # Only bids strictly higher than p_px plus earlier bids at p_px precede participant
            strictly_ahead = sum(
                o.quantity for o in resting_orders if o.quantity > 0 and o.price > p_px
            )
            same_px_ahead = sum(
                o.quantity for o in resting_orders if o.quantity > 0 and o.price == p_px
            )
            rem_supply = max(0, best_vol - strictly_ahead - same_px_ahead)
            filled = min(p_qty, rem_supply)
        pnl = filled * (buyback_price - best_price - fee_per_unit)
    else:
        sell_abs = -p_qty
        if p_px > best_price:
            filled = 0
        else:
            strictly_ahead = sum(
                -o.quantity for o in resting_orders if o.quantity < 0 and o.price < p_px
            )
            same_px_ahead = sum(
                -o.quantity for o in resting_orders if o.quantity < 0 and o.price == p_px
            )
            rem_demand = max(0, best_vol - strictly_ahead - same_px_ahead)
            filled = -min(sell_abs, rem_demand)
        pnl = abs(filled) * (best_price - buyback_price - fee_per_unit)

    return AuctionClearingResult(
        clearing_price=best_price,
        matched_volume=best_vol,
        participant_filled=filled,
        participant_pnl=float(pnl),
    )


def solve_round1_auction(
    resting_orders: Sequence[AuctionOrder],
    buyback_price: float,
    fee_per_unit: float = 0.0,
    price_candidates: Sequence[int] | None = None,
    max_order_qty: int = 100,
) -> tuple[AuctionOrder, AuctionClearingResult]:
    """Find optimal late single limit order given resting field demand/supply."""
    if not resting_orders:
        order = AuctionOrder(price=int(buyback_price), quantity=0)
        return order, clear_opening_auction([], None, buyback_price, fee_per_unit)

    lo = min(o.price for o in resting_orders) - 2
    hi = max(o.price for o in resting_orders) + 2
    cands = list(price_candidates) if price_candidates is not None else list(range(lo, hi + 1))
    qty_grid = [q for q in range(1, max_order_qty + 1, max(1, max_order_qty // 20))]
    if max_order_qty not in qty_grid:
        qty_grid.append(max_order_qty)

    best_order = AuctionOrder(price=int(buyback_price), quantity=0)
    best_res = clear_opening_auction(resting_orders, None, buyback_price, fee_per_unit)

    for px in cands:
        for qty in qty_grid:
            for signed_q in (qty, -qty):
                cand = AuctionOrder(price=px, quantity=signed_q)
                res = clear_opening_auction(resting_orders, cand, buyback_price, fee_per_unit)
                if res.participant_pnl > best_res.participant_pnl:
                    best_res = res
                    best_order = cand

    return best_order, best_res


# ---------------------------------------------------------------------------
# Round 2: "Invest & Expand" (Budget Allocation & Competitive Speed Rank)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class InvestExpandResult:
    """Optimal or equilibrium allocation across Research, Scale, and Speed."""

    research_pct: float
    scale_pct: float
    speed_pct: float
    speed_multiplier: float
    gross_pnl: float
    net_pnl: float


def research_return(research_pct: float) -> float:
    """Concave Research edge: 200,000 * ln(1 + r) / ln(101)."""
    if research_pct < 0.0:
        msg = f"research_pct must be non-negative, got {research_pct}"
        raise ValueError(msg)
    return float(200000.0 * math.log1p(research_pct) / math.log(101.0))


def scale_factor(scale_pct: float) -> float:
    """Linear Scale factor: 0.07 * s."""
    if scale_pct < 0.0:
        msg = f"scale_pct must be non-negative, got {scale_pct}"
        raise ValueError(msg)
    return float(0.07 * scale_pct)


def solve_round2_invest_and_expand(
    speed_multiplier_fn: Callable[[float], float],
    total_budget: float = 50000.0,
    grid_step: float = 0.5,
) -> InvestExpandResult:
    """Solve R2 best-response budget allocation over Research, Scale, and Speed.

    Evaluates all feasible percentages `(r, s, p >= 0, r + s + p <= 100)` with
    budget cost `(total_budget / 100.0) * (r + s + p)` and net payoff
    `research_return(r) * scale_factor(s) * speed_multiplier_fn(p) - spend`.
    """
    n_steps = int(round(100.0 / grid_step))
    best: InvestExpandResult | None = None

    for i_p in range(n_steps + 1):
        p = i_p * grid_step
        spd = float(np.clip(speed_multiplier_fn(p), 0.1, 0.9))
        rem = 100.0 - p
        # Fine search along spending level total_spend in [0, rem] and optimal (r, s)
        n_r = int(round(rem / grid_step))
        for i_r in range(n_r + 1):
            r = i_r * grid_step
            r_val = research_return(r)
            s_max = rem - r
            # Because gross is linear in s, at any fixed p and r either s=s_max or s=0 maximizes net
            for s in (0.0, s_max):
                spend = (total_budget / 100.0) * (r + s + p)
                gross = r_val * scale_factor(s) * spd
                net = gross - spend
                if best is None or net > best.net_pnl:
                    best = InvestExpandResult(
                        research_pct=r,
                        scale_pct=s,
                        speed_pct=p,
                        speed_multiplier=spd,
                        gross_pnl=gross,
                        net_pnl=net,
                    )

    assert best is not None
    # Smooth continuous polish around coarse winner keeping p fixed
    p_opt = best.speed_pct
    spd_opt = best.speed_multiplier
    rem_opt = 100.0 - p_opt
    if rem_opt > 1e-6:
        res = minimize(
            lambda x: -(
                research_return(float(x[0]))
                * scale_factor(rem_opt - float(x[0]))
                * spd_opt
                - total_budget
            ),
            x0=np.array([best.research_pct], dtype=np.float64),
            bounds=[(0.0, rem_opt)],
        )
        if res.success:
            r_ref = float(res.x[0])
            s_ref = max(0.0, rem_opt - r_ref)
            gross_ref = research_return(r_ref) * scale_factor(s_ref) * spd_opt
            spend_ref = (total_budget / 100.0) * (r_ref + s_ref + p_opt)
            net_ref = gross_ref - spend_ref
            if net_ref > best.net_pnl:
                best = InvestExpandResult(
                    research_pct=r_ref,
                    scale_pct=s_ref,
                    speed_pct=p_opt,
                    speed_multiplier=spd_opt,
                    gross_pnl=gross_ref,
                    net_pnl=net_ref,
                )

    return best


# ---------------------------------------------------------------------------
# Round 3: "The Celestial Gardeners' Guild" (Two-Bid Auction + Cubic Penalty)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class GardenersGuildResult:
    """Optimal two-stage bids `(b1, b2)` under uniform reserves and cubic penalty."""

    bid_1: int
    bid_2: int
    expected_profit_per_unit: float
    expected_accept_prob: float
    avg_b2_belief: float


def evaluate_gardeners_pair(
    b1: int,
    b2: int,
    avg_b2_belief: float,
    reserve_grid: Sequence[int] | None = None,
    resale_price: int = 920,
) -> tuple[float, float]:
    """Compute exact expected profit/unit and acceptance probability for `(b1, b2)`."""
    reserves = list(reserve_grid) if reserve_grid is not None else list(range(670, 925, 5))
    if b1 > b2 or b2 >= resale_price:
        return 0.0, 0.0

    if b2 >= avg_b2_belief:
        penalty = 1.0
    else:
        penalty = ((resale_price - avg_b2_belief) / (resale_price - b2)) ** 3

    n = len(reserves)
    ev_sum = 0.0
    acc_sum = 0.0
    for r in reserves:
        if r <= b1:
            ev_sum += float(resale_price - b1)
            acc_sum += 1.0
        elif r <= b2:
            ev_sum += penalty * float(resale_price - b2)
            acc_sum += penalty

    return ev_sum / float(n), acc_sum / float(n)


def solve_round3_gardeners_guild(
    avg_b2_belief: float = 875.0,
    reserve_grid: Sequence[int] | None = None,
    resale_price: int = 920,
    bid_step: int = 1,
) -> GardenersGuildResult:
    """Find exact discrete optimal `(b1*, b2*)` maximizing expected profit."""
    reserves = list(reserve_grid) if reserve_grid is not None else list(range(670, 925, 5))
    lo = min(reserves)
    hi = resale_price - 1

    best_b1, best_b2 = lo, lo
    best_ev = -1.0
    best_acc = 0.0

    for b1 in range(lo, hi + 1, bid_step):
        for b2 in range(b1, hi + 1, bid_step):
            ev, acc = evaluate_gardeners_pair(
                b1,
                b2,
                avg_b2_belief=avg_b2_belief,
                reserve_grid=reserves,
                resale_price=resale_price,
            )
            if ev > best_ev:
                best_ev = ev
                best_acc = acc
                best_b1 = b1
                best_b2 = b2

    return GardenersGuildResult(
        bid_1=best_b1,
        bid_2=best_b2,
        expected_profit_per_unit=best_ev,
        expected_accept_prob=best_acc,
        avg_b2_belief=avg_b2_belief,
    )


# ---------------------------------------------------------------------------
# Round 4: "Vanilla Just Isn't Exotic Enough" (Aether Crystal Exotics)
# ---------------------------------------------------------------------------


ExoticKind = Literal[
    "spot",
    "vanilla_call",
    "vanilla_put",
    "binary_put",
    "knockout_put",
    "chooser",
]


@dataclass(frozen=True, slots=True)
class ExoticContractSpec:
    """Contract specification on AETHER_CRYSTAL (discrete-monitoring GBM)."""

    name: str
    kind: ExoticKind
    strike: float = 50.0
    horizon_days: float = 14.0
    steps_per_day: int = 4
    barrier: float = 0.0
    choice_day: float = 7.0
    binary_payout: float = 100.0
    ask_price: float = 0.0


@dataclass(frozen=True, slots=True)
class ExoticValuationResult:
    """Monte Carlo fair value, standard error, and knock-out rate for an exotic."""

    name: str
    fair_value: float
    std_error: float
    knockout_prob: float
    delta_fd: float


def _bs_price(spot: float, strike: float, tte_years: float, vol_ann: float, is_call: bool) -> float:
    if tte_years <= 0.0 or vol_ann <= 0.0:
        return max(0.0, spot - strike) if is_call else max(0.0, strike - spot)
    st = math.sqrt(tte_years)
    d1 = (math.log(spot / strike) + 0.5 * vol_ann * vol_ann * tte_years) / (vol_ann * st)
    d2 = d1 - vol_ann * st
    if is_call:
        return float(spot * _STD_NORM.cdf(d1) - strike * _STD_NORM.cdf(d2))
    return float(strike * _STD_NORM.cdf(-d2) - spot * _STD_NORM.cdf(-d1))


def _bs_delta(spot: float, strike: float, tte_years: float, vol_ann: float, is_call: bool) -> float:
    if tte_years <= 0.0 or vol_ann <= 0.0:
        if is_call:
            return 1.0 if spot > strike else 0.0
        return -1.0 if spot < strike else 0.0
    st = math.sqrt(tte_years)
    d1 = (math.log(spot / strike) + 0.5 * vol_ann * vol_ann * tte_years) / (vol_ann * st)
    return float(_STD_NORM.cdf(d1)) if is_call else float(_STD_NORM.cdf(d1) - 1.0)


def price_aether_crystal_contract(
    spec: ExoticContractSpec,
    spot: float = 50.0,
    step_sigma_log: float = 0.0251,
    n_paths: int = 40000,
    seed: int = 42,
    days_per_year: float = 252.0,
) -> ExoticValuationResult:
    """Price AETHER_CRYSTAL spot, vanilla, binary, chooser (exact BS/Rubinstein), or barrier KO.

    Closed-form Black-Scholes and Rubinstein (1991) formulas are used for path-independent
    vanillas, digital puts, and simple choosers (eliminating MC put-call parity noise).
    Path-dependent discrete-monitoring knock-out puts use antithetic GBM Monte Carlo.
    """
    if spec.kind == "spot":
        return ExoticValuationResult(
            name=spec.name,
            fair_value=float(spot),
            std_error=0.0,
            knockout_prob=0.0,
            delta_fd=1.0,
        )

    total_steps = max(1, int(round(spec.horizon_days * spec.steps_per_day)))
    choice_step = min(
        total_steps,
        max(1, int(round(spec.choice_day * spec.steps_per_day))),
    )
    ann_vol = step_sigma_log * math.sqrt(spec.steps_per_day * days_per_year)
    total_years = total_steps / (spec.steps_per_day * days_per_year)
    choice_years = choice_step / (spec.steps_per_day * days_per_year)

    if spec.kind == "vanilla_call":
        fair = _bs_price(spot, spec.strike, total_years, ann_vol, is_call=True)
        delta = _bs_delta(spot, spec.strike, total_years, ann_vol, is_call=True)
        return ExoticValuationResult(spec.name, fair, 0.0, 0.0, delta)

    if spec.kind == "vanilla_put":
        fair = _bs_price(spot, spec.strike, total_years, ann_vol, is_call=False)
        delta = _bs_delta(spot, spec.strike, total_years, ann_vol, is_call=False)
        return ExoticValuationResult(spec.name, fair, 0.0, 0.0, delta)

    if spec.kind == "binary_put":
        st = math.sqrt(total_years)
        d2 = (math.log(spot / spec.strike) - 0.5 * ann_vol * ann_vol * total_years) / (
            ann_vol * st
        )
        fair = float(spec.binary_payout * _STD_NORM.cdf(-d2))
        delta = float(-spec.binary_payout * _STD_NORM.pdf(-d2) / (spot * ann_vol * st))
        return ExoticValuationResult(spec.name, fair, 0.0, 0.0, delta)

    if spec.kind == "chooser":
        # Rubinstein (1991) exact zero-rate simple chooser: C(S, K, T) + P(S, K, t_c)
        fair = _bs_price(spot, spec.strike, total_years, ann_vol, is_call=True) + _bs_price(
            spot,
            spec.strike,
            choice_years,
            ann_vol,
            is_call=False,
        )
        delta = _bs_delta(spot, spec.strike, total_years, ann_vol, is_call=True) + _bs_delta(
            spot,
            spec.strike,
            choice_years,
            ann_vol,
            is_call=False,
        )
        return ExoticValuationResult(spec.name, fair, 0.0, 0.0, delta)

    if spec.kind != "knockout_put":
        msg = f"Unsupported exotic contract kind: {spec.kind}"
        raise ValueError(msg)

    n_half = max(1000, n_paths // 2)
    rng = np.random.default_rng(seed)
    z_half = rng.standard_normal((n_half, total_steps))
    z = np.vstack([z_half, -z_half])

    # Martingale-consistent risk-neutral GBM steps: E[S_{t+1} | S_t] = S_t
    drift_step = -0.5 * step_sigma_log * step_sigma_log

    def _simulate_ko(s0: float) -> tuple[NDArray[np.float64], float]:
        log_rets = drift_step + step_sigma_log * z
        paths = s0 * np.exp(np.cumsum(log_rets, axis=1))
        s_T = paths[:, -1]
        min_path = np.min(paths, axis=1)
        knocked = (min_path <= spec.barrier) | (s0 <= spec.barrier)
        ko_prob = float(np.mean(knocked))
        pay = np.where(knocked, 0.0, np.maximum(spec.strike - s_T, 0.0))
        return pay, ko_prob

    payoffs, ko_p = _simulate_ko(spot)
    fair = float(np.mean(payoffs))
    se = float(np.std(payoffs, ddof=1) / math.sqrt(payoffs.size))

    eps = max(0.05, 0.005 * spot)
    up_pay, _ = _simulate_ko(spot + eps)
    dn_pay, _ = _simulate_ko(max(1e-4, spot - eps))
    delta = float((np.mean(up_pay) - np.mean(dn_pay)) / (2.0 * eps))

    return ExoticValuationResult(
        name=spec.name,
        fair_value=fair,
        std_error=se,
        knockout_prob=ko_p,
        delta_fd=delta,
    )


# ---------------------------------------------------------------------------
# Round 5: "Extra! Extra!" (Ignith Quadratic-Fee Portfolio Optimization)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ExtraExtraResult:
    """Exact KKT solution under Ignith quadratic fee structure."""

    weights_pct: dict[str, float]
    gross_exposure_pct: float
    expected_gross_pnl: float
    total_fees: float
    expected_net_pnl: float
    shadow_price_lambda: float


def solve_round5_extra_extra(
    expected_returns: Mapping[str, float],
    budget: float = 1_000_000.0,
) -> ExtraExtraResult:
    """Solve Ignith quadratic-fee allocation exactly via KKT shrinkage thresholding.

    For fractional edge `mu_i` per currency unit invested (`w_i = q_i / 100`),
    maximizes `sum_i (mu_i * w_i - w_i^2) * budget` subject to `sum_i |w_i| <= 1`.
    Any weak or ambiguous belief with `|mu_i| <= lambda*` shrinks strictly to zero.
    """
    if not expected_returns or budget <= 0.0:
        return ExtraExtraResult(
            weights_pct={},
            gross_exposure_pct=0.0,
            expected_gross_pnl=0.0,
            total_fees=0.0,
            expected_net_pnl=0.0,
            shadow_price_lambda=0.0,
        )

    abs_edges = sorted((abs(mu) for mu in expected_returns.values()), reverse=True)
    # Test interior unconstrained optimum (lambda = 0)
    lam = 0.0
    if 0.5 * sum(abs_edges) > 1.0:
        # Find exact KKT multiplier lambda > 0 so sum_i 0.5 * max(0, |mu_i| - lambda) == 1.0
        running_sum = 0.0
        for k, edge in enumerate(abs_edges, start=1):
            running_sum += edge
            cand_lam = (running_sum - 2.0) / float(k)
            next_edge = abs_edges[k] if k < len(abs_edges) else -1.0
            if cand_lam >= next_edge:
                lam = max(0.0, cand_lam)
                break

    weights_pct: dict[str, float] = {}
    gross_pnl = 0.0
    fees = 0.0
    gross_pct = 0.0

    for sym, mu in expected_returns.items():
        mag = max(0.0, 0.5 * (abs(mu) - lam))
        w = math.copysign(mag, mu) if mag > 1e-12 else 0.0
        q_pct = 100.0 * w
        weights_pct[sym] = round(q_pct, 6)
        gross_pct += abs(q_pct)
        gross_pnl += budget * mu * w
        fees += budget * (w * w)

    return ExtraExtraResult(
        weights_pct=weights_pct,
        gross_exposure_pct=round(gross_pct, 6),
        expected_gross_pnl=float(gross_pnl),
        total_fees=float(fees),
        expected_net_pnl=float(gross_pnl - fees),
        shadow_price_lambda=float(lam),
    )


# ---------------------------------------------------------------------------
# Advanced Extensions: Behavioral Game Theory, Exotic Hedging & Risk KKT
# ---------------------------------------------------------------------------


def solve_round1_uncertain_demand(
    base_book: Sequence[AuctionOrder],
    buyback_price: float,
    fee_per_unit: float = 0.0,
    crowd_qty_mean: float = 40.0,
    crowd_qty_std: float = 20.0,
    crowd_price_loc: int | None = None,
    n_draws: int = 200,
    seed: int = 42,
    max_order_qty: int = 100,
) -> tuple[AuctionOrder, float, float]:
    """Optimize Round 1 bid over stochastic human demand shocks around resting book.

    Returns `(best_order, expected_pnl, win_fill_rate)`.
    """
    if not base_book:
        return AuctionOrder(price=int(buyback_price), quantity=0), 0.0, 0.0

    rng = np.random.default_rng(seed)
    mid_px = crowd_price_loc if crowd_price_loc is not None else int(buyback_price) - 1
    shocks: list[list[AuctionOrder]] = []
    for _ in range(n_draws):
        q_shock = max(0, int(round(float(rng.normal(crowd_qty_mean, crowd_qty_std)))))
        px_jitter = int(rng.integers(-1, 2))
        extra = [AuctionOrder(price=mid_px + px_jitter, quantity=q_shock)] if q_shock > 0 else []
        shocks.append(list(base_book) + extra)

    lo = min(o.price for o in base_book) - 1
    hi = int(buyback_price)
    best_order = AuctionOrder(price=int(buyback_price), quantity=0)
    best_ev = 0.0
    best_fill_rate = 0.0

    qty_grid = list(range(5, max_order_qty + 1, 5))
    for px in range(lo, hi + 1):
        for qty in qty_grid:
            cand = AuctionOrder(price=px, quantity=qty)
            pnls = [
                clear_opening_auction(bk, cand, buyback_price, fee_per_unit).participant_pnl
                for bk in shocks
            ]
            fills = [
                clear_opening_auction(bk, cand, buyback_price, fee_per_unit).participant_filled > 0
                for bk in shocks
            ]
            ev = float(np.mean(pnls))
            if ev > best_ev:
                best_ev = ev
                best_order = cand
                best_fill_rate = float(np.mean(fills))

    return best_order, best_ev, best_fill_rate


@dataclass(frozen=True, slots=True)
class Round2CognitiveHierarchyResult:
    """Round 2 Level-k cognitive hierarchy equilibrium and focal benchmark."""

    level_solutions: dict[str, InvestExpandResult]
    ex_ante_recommended: InvestExpandResult
    focal_benchmark: InvestExpandResult


def optimal_research_given_speed(speed_pct: float) -> tuple[float, float]:
    """Return exact optimal `(research_pct, scale_pct)` maximizing Research*Scale at Speed p."""
    rem = max(0.0, 100.0 - speed_pct)
    if rem <= 1e-9:
        return 0.0, 0.0
    # Solve (rem - r)/(1 + r) = ln(1 + r) via bounded bisection
    lo, hi = 0.0, rem
    for _ in range(50):
        mid = 0.5 * (lo + hi)
        lhs = (rem - mid) / (1.0 + mid)
        rhs = math.log1p(mid)
        if lhs > rhs:
            lo = mid
        else:
            hi = mid
    r_star = 0.5 * (lo + hi)
    return r_star, max(0.0, rem - r_star)


def _smoothed_cdf_from_samples(
    samples: NDArray[np.float64], bandwidth: float
) -> Callable[[float], float]:
    def _fn(p: float) -> float:
        z = (p - samples) / max(1e-6, bandwidth)
        # Smooth logistic rank kernel in [0.1, 0.9]
        probs = 1.0 / (1.0 + np.exp(-np.clip(z, -20.0, 20.0)))
        return 0.1 + 0.8 * float(np.mean(probs))

    return _fn


def solve_round2_cognitive_hierarchy(
    total_budget: float = 50_000.0,
    target_speed_pct: float | None = None,
) -> Round2CognitiveHierarchyResult:
    """Solve Round 2 best responses along Level-0/1/2/3 tournament escalation.

    Produces iterative best responses across Poisson cognitive-hierarchy strata
    together with the Level-3 focal fixed-point allocation (`target_speed_pct`
    defaults to `l3_res.speed_pct`, i.e. 42.0%).
    """
    # Level-0 anchor mixture: naive low-speed / uniform splits
    l0_samples = np.array([2.0, 8.0, 15.0, 22.0, 33.0], dtype=np.float64)
    l0_cdf = _smoothed_cdf_from_samples(l0_samples, bandwidth=4.5)
    l1_res = solve_round2_invest_and_expand(l0_cdf, total_budget=total_budget, grid_step=0.5)

    # Poisson Cognitive Hierarchy (Camerer-Ho-Chong): Level-2 best-responds to L0 + L1
    l1_cluster = np.full(8, l1_res.speed_pct, dtype=np.float64) + np.linspace(-3.0, 3.0, 8)
    mix_12 = np.concatenate([l0_samples, l1_cluster])
    l2_cdf = _smoothed_cdf_from_samples(mix_12, bandwidth=4.0)
    l2_res = solve_round2_invest_and_expand(l2_cdf, total_budget=total_budget, grid_step=0.5)

    # Level-3 best-responds to L0 + L1 + L2 tournament blend
    l2_cluster = np.full(8, l2_res.speed_pct, dtype=np.float64) + np.linspace(-2.5, 2.5, 8)
    mix_123 = np.concatenate([l0_samples, l1_cluster, l2_cluster])
    l3_cdf = _smoothed_cdf_from_samples(mix_123, bandwidth=3.5)
    l3_res = solve_round2_invest_and_expand(l3_cdf, total_budget=total_budget, grid_step=0.5)

    # Ex-ante blended CH mixture policy across all cohort sophistication strata
    l3_cluster = np.full(4, l3_res.speed_pct, dtype=np.float64) + np.linspace(-2.0, 2.0, 4)
    ex_ante_cdf = _smoothed_cdf_from_samples(
        np.concatenate([l0_samples, l1_cluster, l2_cluster, l3_cluster]),
        bandwidth=3.8,
    )
    ex_ante = solve_round2_invest_and_expand(ex_ante_cdf, total_budget=total_budget, grid_step=0.5)

    focal_p = float(l3_res.speed_pct if target_speed_pct is None else target_speed_pct)
    r_focal, s_focal = optimal_research_given_speed(focal_p)
    spd_focal = float(ex_ante_cdf(focal_p))
    gross_focal = research_return(r_focal) * scale_factor(s_focal) * spd_focal
    focal_bench = InvestExpandResult(
        research_pct=r_focal,
        scale_pct=s_focal,
        speed_pct=focal_p,
        speed_multiplier=spd_focal,
        gross_pnl=gross_focal,
        net_pnl=gross_focal - total_budget,
    )

    return Round2CognitiveHierarchyResult(
        level_solutions={"L1": l1_res, "L2": l2_res, "L3": l3_res},
        ex_ante_recommended=ex_ante,
        focal_benchmark=focal_bench,
    )


def solve_round3_bayesian_belief(
    mean_b2: float = 875.0,
    std_b2: float = 15.0,
    n_quad: int = 21,
    reserve_grid: Sequence[int] | None = None,
    resale_price: int = 920,
    bid_step: int = 1,
) -> GardenersGuildResult:
    """Solve Round 3 optimal `(b1*, b2*)` integrating uncertainty in crowd avg_b2."""
    reserves = list(reserve_grid) if reserve_grid is not None else list(range(670, 925, 5))
    lo = min(reserves)
    hi = resale_price - 1

    z_pts = np.linspace(-2.5, 2.5, max(3, n_quad))
    raw_w = np.exp(-0.5 * z_pts * z_pts)
    weights = raw_w / np.sum(raw_w)
    b2_nodes = np.clip(mean_b2 + std_b2 * z_pts, float(lo), float(hi))

    best_b1, best_b2 = lo, lo
    best_ev = -1.0
    best_acc = 0.0

    for b1 in range(lo, hi + 1, bid_step):
        for b2 in range(b1, hi + 1, bid_step):
            ev_weighted = 0.0
            acc_weighted = 0.0
            for w, avg_b2 in zip(weights, b2_nodes, strict=True):
                ev_k, acc_k = evaluate_gardeners_pair(
                    b1, b2, float(avg_b2), reserve_grid=reserves, resale_price=resale_price
                )
                ev_weighted += float(w) * ev_k
                acc_weighted += float(w) * acc_k
            if ev_weighted > best_ev:
                best_ev = ev_weighted
                best_acc = acc_weighted
                best_b1 = b1
                best_b2 = b2

    return GardenersGuildResult(
        bid_1=best_b1,
        bid_2=best_b2,
        expected_profit_per_unit=best_ev,
        expected_accept_prob=best_acc,
        avg_b2_belief=mean_b2,
    )


def annualized_to_step_sigma(
    annual_vol: float = 2.51,
    steps_per_day: int = 4,
    days_per_year: int = 252,
) -> float:
    """Convert annualized GBM volatility to per-discrete-step log volatility."""
    return float(annual_vol / math.sqrt(float(steps_per_day * days_per_year)))


@dataclass(frozen=True, slots=True)
class ExoticPortfolioResult:
    """Mean-variance & CVaR portfolio over Round 4 Aether Crystal contracts."""

    names: tuple[str, ...]
    optimal_lots: dict[str, float]
    contract_edges: dict[str, float]
    expected_pnl: float
    pnl_std: float
    sharpe_ratio: float
    cvar_95: float
    unhedged_sharpe: float
    std_reduction_pct: float


def _pathwise_payoffs(
    spec: ExoticContractSpec,
    spot: float,
    step_sigma_log: float,
    paths: NDArray[np.float64],
    days_per_year: float,
) -> NDArray[np.float64]:
    total_steps = paths.shape[1]
    s_t = paths[:, -1]
    if spec.kind == "spot":
        return s_t
    if spec.kind == "vanilla_call":
        return np.maximum(s_t - spec.strike, 0.0)
    if spec.kind == "vanilla_put":
        return np.maximum(spec.strike - s_t, 0.0)
    if spec.kind == "binary_put":
        return np.where(s_t < spec.strike, spec.binary_payout, 0.0)
    if spec.kind == "knockout_put":
        knocked = (np.min(paths, axis=1) <= spec.barrier) | (spot <= spec.barrier)
        return np.where(knocked, 0.0, np.maximum(spec.strike - s_t, 0.0))
    if spec.kind == "chooser":
        # Realized terminal Day-T payoff after optimal call/put election at choice_day
        # Under r=0 symmetric lognormal diffusion, C(S_c, K, T-t_c) >= P(S_c, K, T-t_c) iff S_c >= K
        c_step = min(total_steps, max(1, int(round(spec.choice_day * spec.steps_per_day))))
        s_choice = paths[:, c_step - 1]
        ann_vol = step_sigma_log * math.sqrt(spec.steps_per_day * days_per_year)
        rem_years = max(0.0, (total_steps - c_step) / (spec.steps_per_day * days_per_year))
        if rem_years <= 0.0:
            choose_call = s_choice >= spec.strike
        else:
            choose_call = np.array(
                [
                    _bs_price(float(sc), spec.strike, rem_years, ann_vol, is_call=True)
                    >= _bs_price(float(sc), spec.strike, rem_years, ann_vol, is_call=False)
                    for sc in s_choice
                ],
                dtype=bool,
            )
        call_pay = np.maximum(s_t - spec.strike, 0.0)
        put_pay = np.maximum(spec.strike - s_t, 0.0)
        return np.where(choose_call, call_pay, put_pay)
    msg = f"Unsupported exotic contract kind: {spec.kind}"
    raise ValueError(msg)


def solve_round4_exotic_portfolio(
    specs: Sequence[ExoticContractSpec],
    lot_bounds: Mapping[str, tuple[float, float]],
    spot: float = 50.0,
    annual_vol: float = 2.51,
    n_paths: int = 30_000,
    risk_aversion: float = 0.002,
    seed: int = 42,
    days_per_year: float = 252.0,
) -> ExoticPortfolioResult:
    """Optimize multi-contract portfolio PnL minus variance penalty on terminal Day-T payoffs."""
    if not specs:
        return ExoticPortfolioResult(
            names=(),
            optimal_lots={},
            contract_edges={},
            expected_pnl=0.0,
            pnl_std=0.0,
            sharpe_ratio=0.0,
            cvar_95=0.0,
            unhedged_sharpe=0.0,
            std_reduction_pct=0.0,
        )

    steps_per_day = max(s.steps_per_day for s in specs)
    max_days = max(s.horizon_days for s in specs)
    total_steps = max(1, int(round(max_days * steps_per_day)))
    step_sigma = annualized_to_step_sigma(annual_vol, steps_per_day, int(days_per_year))

    n_half = max(1000, n_paths // 2)
    rng = np.random.default_rng(seed)
    z_half = rng.standard_normal((n_half, total_steps))
    z = np.vstack([z_half, -z_half])
    log_rets = -0.5 * step_sigma * step_sigma + step_sigma * z
    paths = spot * np.exp(np.cumsum(log_rets, axis=1))

    # Build pathwise terminal P&L matrix `(n_samples, n_assets)` and closed-form edges where exact
    pnl_cols: list[NDArray[np.float64]] = []
    names: list[str] = []
    edges: dict[str, float] = {}
    mu_vec: list[float] = []
    bounds: list[tuple[float, float]] = []

    for spec in specs:
        c_steps = min(total_steps, max(1, int(round(spec.horizon_days * steps_per_day))))
        payoffs = _pathwise_payoffs(spec, spot, step_sigma, paths[:, :c_steps], days_per_year)
        net = payoffs - spec.ask_price
        pnl_cols.append(net)
        names.append(spec.name)
        if spec.kind == "knockout_put":
            edge = float(np.mean(net))
        else:
            edge = (
                price_aether_crystal_contract(
                    spec,
                    spot=spot,
                    step_sigma_log=annualized_to_step_sigma(
                        annual_vol,
                        spec.steps_per_day,
                        int(days_per_year),
                    ),
                    n_paths=n_paths,
                    seed=seed,
                    days_per_year=days_per_year,
                ).fair_value
                - spec.ask_price
            )
        edges[spec.name] = edge
        mu_vec.append(edge)
        bounds.append(lot_bounds.get(spec.name, (-50.0, 50.0)))

    mat = np.column_stack(pnl_cols)
    mu = np.asarray(mu_vec, dtype=np.float64)
    cov = np.cov(mat, rowvar=False, ddof=1)
    if cov.ndim == 0:
        cov = np.array([[float(cov)]], dtype=np.float64)

    # Unhedged standalone greedy corner benchmark
    unhedged_w = np.array(
        [hi if m >= 0 else lo for m, (lo, hi) in zip(mu, bounds, strict=True)],
        dtype=np.float64,
    )
    u_pnls = mat @ unhedged_w
    u_std = float(np.std(u_pnls, ddof=1))
    u_sharpe = float(float(mu @ unhedged_w) / u_std) if u_std > 1e-9 else 0.0

    # Mean-variance optimization with SLSQP
    x0 = unhedged_w * 0.5
    opt = minimize(
        lambda w: -(float(mu @ w) - 0.5 * risk_aversion * float(w @ cov @ w)),
        x0=x0,
        bounds=bounds,
        method="SLSQP",
    )
    w_opt = opt.x if opt.success else unhedged_w
    port_pnls = mat @ w_opt
    exp_pnl = float(mu @ w_opt)
    p_std = float(np.std(port_pnls, ddof=1))
    p_sharpe = float(exp_pnl / p_std) if p_std > 1e-9 else 0.0
    var95 = float(np.percentile(port_pnls, 5.0))
    tail = port_pnls[port_pnls <= var95]
    cvar95 = float(np.mean(tail)) if tail.size > 0 else var95
    red_pct = 100.0 * (1.0 - p_std / u_std) if u_std > 1e-9 else 0.0

    return ExoticPortfolioResult(
        names=tuple(names),
        optimal_lots={n: round(float(w), 2) for n, w in zip(names, w_opt, strict=True)},
        contract_edges=edges,
        expected_pnl=exp_pnl,
        pnl_std=p_std,
        sharpe_ratio=p_sharpe,
        cvar_95=cvar95,
        unhedged_sharpe=u_sharpe,
        std_reduction_pct=red_pct,
    )


def solve_round5_risk_adjusted(
    expected_returns: Mapping[str, float],
    return_vols: Mapping[str, float],
    risk_aversion: float = 0.25,
    budget: float = 1_000_000.0,
) -> ExtraExtraResult:
    """Solve Round 5 Ignith allocation under quadratic fees + diagonal variance penalty.

    Objective per weight `w_i = q_i / 100`:
      `max_w sum_i (mu_i * w_i - c_i * w_i^2) * B` s.t. `sum |w_i| <= 1`,
      where `c_i = 1 + 0.5 * risk_aversion * vol_i^2`.
    """
    if not expected_returns or budget <= 0.0:
        return solve_round5_extra_extra(expected_returns, budget=budget)

    costs: dict[str, float] = {
        sym: 1.0 + 0.5 * risk_aversion * (float(return_vols.get(sym, 0.0)) ** 2)
        for sym in expected_returns
    }

    def _gross_at(lam: float) -> float:
        return sum(
            max(0.0, (abs(mu) - lam) / (2.0 * costs[sym]))
            for sym, mu in expected_returns.items()
        )

    if _gross_at(0.0) <= 1.0:
        lam = 0.0
    else:
        lo, hi = 0.0, max(abs(mu) for mu in expected_returns.values())
        for _ in range(60):
            mid = 0.5 * (lo + hi)
            if _gross_at(mid) > 1.0:
                lo = mid
            else:
                hi = mid
        lam = 0.5 * (lo + hi)

    weights_pct: dict[str, float] = {}
    gross_pnl = 0.0
    fees = 0.0
    gross_pct = 0.0
    for sym, mu in expected_returns.items():
        mag = max(0.0, (abs(mu) - lam) / (2.0 * costs[sym]))
        w = math.copysign(mag, mu) if mag > 1e-12 else 0.0
        q_pct = 100.0 * w
        weights_pct[sym] = round(q_pct, 6)
        gross_pct += abs(q_pct)
        gross_pnl += budget * mu * w
        fees += budget * (w * w)

    return ExtraExtraResult(
        weights_pct=weights_pct,
        gross_exposure_pct=round(gross_pct, 6),
        expected_gross_pnl=float(gross_pnl),
        total_fees=float(fees),
        expected_net_pnl=float(gross_pnl - fees),
        shadow_price_lambda=float(lam),
    )
