"""Standalone IMC Prosperity 4 Round 3 submission trader.

No external package dependencies outside `datamodel` and Python's standard library.
Combines:
  1. Wide-spread wall-mid market making on `HYDROGEL_PACK` (+/-200).
  2. Deep-ITM spot-parity quoting on `VEV_4000` and `VEV_4500` (+/-300).
  3. Day-invariant total-volatility (`v = sigma * sqrt(T)`) Black-Scholes quoting
     and mispricing capture across `VEV_5200..VEV_5500` (+/-300).
  4. Capped delta-neutral spot hedging + market making on `VELVETFRUIT_EXTRACT` (+/-200).

IS Plateau Parameters (`Day 0 & Day 1`): `MM_EDGE=4.5, MM_SKEW=0.10`.
"""

from __future__ import annotations

import json
import math
from statistics import NormalDist
from typing import Any

from datamodel import Order, OrderDepth, TradingState

POSITION_LIMITS: dict[str, int] = {
    "HYDROGEL_PACK": 200,
    "VELVETFRUIT_EXTRACT": 200,
    "VEV_4000": 300,
    "VEV_4500": 300,
    "VEV_5000": 300,
    "VEV_5100": 300,
    "VEV_5200": 300,
    "VEV_5300": 300,
    "VEV_5400": 300,
    "VEV_5500": 300,
    "VEV_6000": 300,
    "VEV_6500": 300,
}

DEEP_ITM_STRIKES: tuple[tuple[str, float], ...] = (
    ("VEV_4000", 4000.0),
    ("VEV_4500", 4500.0),
)
OPTION_STRIKES: tuple[tuple[str, float], ...] = (
    ("VEV_5200", 5200.0),
    ("VEV_5300", 5300.0),
    ("VEV_5400", 5400.0),
    ("VEV_5500", 5500.0),
)

MM_EDGE: float = 4.5
MM_SKEW: float = 0.10
OPT_EDGE: float = 0.5
HEDGE_BAND: float = 10.0

_STD_NORM = NormalDist(0.0, 1.0)


def _popular_wall_mid(depth: OrderDepth) -> float | None:
    """Extract midpoint of highest-volume resting bid and ask walls."""
    if not depth.buy_orders or not depth.sell_orders:
        return None
    wall_bid = max(depth.buy_orders.items(), key=lambda kv: (abs(kv[1]), kv[0]))[0]
    wall_ask = max(depth.sell_orders.items(), key=lambda kv: (abs(kv[1]), -kv[0]))[0]
    return float(0.5 * (wall_bid + wall_ask))


def _bs_call_total_v(spot: float, strike: float, total_v: float) -> tuple[float, float]:
    """Price a call and return delta as a function of total vol v = sigma*sqrt(T)."""
    if total_v <= 1e-6 or spot <= 0.0 or strike <= 0.0:
        return max(0.0, spot - strike), (1.0 if spot > strike else 0.0)
    d1 = (math.log(spot / strike) + 0.5 * total_v * total_v) / total_v
    d2 = d1 - total_v
    delta = _STD_NORM.cdf(d1)
    return spot * delta - strike * _STD_NORM.cdf(d2), delta


def _invert_total_v(price: float, spot: float, strike: float) -> float | None:
    """Invert Black-Scholes total volatility v = sigma*sqrt(T) by bisection."""
    intrinsic = max(0.0, spot - strike)
    if spot <= 0.0 or strike <= 0.0 or price <= intrinsic + 0.2 or price >= spot:
        return None
    lo, hi = 1e-4, 0.5
    for _ in range(28):
        mid = 0.5 * (lo + hi)
        est, _ = _bs_call_total_v(spot, strike, mid)
        if est < price:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def _load_state(raw_data: str) -> dict[str, Any]:
    """Defensively decode JSON traderData."""
    default: dict[str, Any] = {"fv": {}, "v": {}}
    if not raw_data:
        return default
    try:
        parsed = json.loads(raw_data)
    except (ValueError, TypeError):
        return default
    if not isinstance(parsed, dict):
        return default
    return {
        "fv": parsed.get("fv", {}) if isinstance(parsed.get("fv"), dict) else {},
        "v": parsed.get("v", {}) if isinstance(parsed.get("v"), dict) else {},
    }


def _place_mm_orders(
    symbol: str,
    depth: OrderDepth,
    fv: float,
    start_pos: int,
    limit: int,
    half_edge: float,
    skew: float,
    clip: int,
    take_edge: float | None = None,
) -> list[Order]:
    """Construct simultaneous limit-clamped taker + penny-improving maker orders."""
    orders: list[Order] = []
    buy_cap = max(0, limit - start_pos)
    sell_cap = max(0, limit + start_pos)
    taken_buy = 0
    taken_sell = 0

    best_ask = min(depth.sell_orders.keys()) if depth.sell_orders else None
    best_bid = max(depth.buy_orders.keys()) if depth.buy_orders else None

    if take_edge is not None:
        if best_ask is not None and best_ask <= fv - take_edge and buy_cap > 0:
            for ask_px in sorted(depth.sell_orders.keys()):
                if ask_px > fv - take_edge or buy_cap - taken_buy <= 0:
                    break
                qty = min(abs(depth.sell_orders[ask_px]), buy_cap - taken_buy)
                if qty > 0:
                    orders.append(Order(symbol, ask_px, qty))
                    taken_buy += qty
        if best_bid is not None and best_bid >= fv + take_edge and sell_cap > 0:
            for bid_px in sorted(depth.buy_orders.keys(), reverse=True):
                if bid_px < fv + take_edge or sell_cap - taken_sell <= 0:
                    break
                qty = min(abs(depth.buy_orders[bid_px]), sell_cap - taken_sell)
                if qty > 0:
                    orders.append(Order(symbol, bid_px, -qty))
                    taken_sell += qty

    rem_buy = max(0, buy_cap - taken_buy)
    rem_sell = max(0, sell_cap - taken_sell)
    res = fv - skew * start_pos

    q_bid = min(math.floor(res - half_edge), best_bid + 1) if best_bid is not None else math.floor(
        res - half_edge,
    )
    q_ask = max(math.ceil(res + half_edge), best_ask - 1) if best_ask is not None else math.ceil(
        res + half_edge,
    )
    if best_ask is not None and q_bid >= best_ask:
        q_bid = best_ask - 1
    if best_bid is not None and q_ask <= best_bid:
        q_ask = best_bid + 1

    if q_bid < q_ask and q_bid > 0:
        if rem_buy > 0:
            orders.append(Order(symbol, q_bid, min(clip, rem_buy)))
        if rem_sell > 0:
            orders.append(Order(symbol, q_ask, -min(clip, rem_sell)))

    return orders


class Trader:
    """Prosperity 4 Round 3 standalone competition trader."""

    def run(self, state: TradingState) -> tuple[dict[str, list[Order]], int, str]:
        """Execute one Round 3 tick across spot and option vouchers."""
        result: dict[str, list[Order]] = {}
        mem = _load_state(state.traderData)
        fv_map: dict[str, float] = mem["fv"]
        v_map: dict[str, float] = mem["v"]

        # 1. HYDROGEL_PACK wide-spread MM (+/-200)
        h_depth = state.order_depths.get("HYDROGEL_PACK")
        if h_depth is not None:
            h_obs = _popular_wall_mid(h_depth)
            if h_obs is not None:
                prev_h = float(fv_map.get("HYDROGEL_PACK", h_obs))
                fv_map["HYDROGEL_PACK"] = 0.25 * h_obs + 0.75 * prev_h
            if "HYDROGEL_PACK" in fv_map:
                h_orders = _place_mm_orders(
                    symbol="HYDROGEL_PACK",
                    depth=h_depth,
                    fv=float(fv_map["HYDROGEL_PACK"]),
                    start_pos=int(state.position.get("HYDROGEL_PACK", 0)),
                    limit=POSITION_LIMITS["HYDROGEL_PACK"],
                    half_edge=MM_EDGE,
                    skew=MM_SKEW,
                    clip=60,
                    take_edge=1.5,
                )
                if h_orders:
                    result["HYDROGEL_PACK"] = h_orders

        # 2. VELVETFRUIT_EXTRACT spot fair value update
        s_depth = state.order_depths.get("VELVETFRUIT_EXTRACT")
        if s_depth is None:
            return result, 0, json.dumps(mem, separators=(",", ":"))
        s_obs = _popular_wall_mid(s_depth)
        if s_obs is not None:
            prev_s = float(fv_map.get("VELVETFRUIT_EXTRACT", s_obs))
            fv_map["VELVETFRUIT_EXTRACT"] = 0.45 * s_obs + 0.55 * prev_s
        if "VELVETFRUIT_EXTRACT" not in fv_map:
            return result, 0, json.dumps(mem, separators=(",", ":"))
        sfv = float(fv_map["VELVETFRUIT_EXTRACT"])

        net_opt_delta = 0.0

        # 3. Deep-ITM calls (VEV_4000 & VEV_4500): parity MM (+/-300)
        for sym, strike in DEEP_ITM_STRIKES:
            ob = state.order_depths.get(sym)
            if ob is None:
                continue
            pos = int(state.position.get(sym, 0))
            net_opt_delta += float(pos)
            deep_orders = _place_mm_orders(
                symbol=sym,
                depth=ob,
                fv=sfv - strike,
                start_pos=pos,
                limit=POSITION_LIMITS[sym],
                half_edge=2.5,
                skew=0.025,
                clip=40,
                take_edge=2.0,
            )
            if deep_orders:
                result[sym] = deep_orders

        # 4. Option chain (VEV_5200..5500): self-calibrating BS total-vol quoting
        for sym, strike in OPTION_STRIKES:
            ob = state.order_depths.get(sym)
            if ob is None or not ob.buy_orders or not ob.sell_orders:
                continue
            best_bid = max(ob.buy_orders.keys())
            best_ask = min(ob.sell_orders.keys())
            mid_opt = 0.5 * (best_bid + best_ask)
            v_obs = _invert_total_v(mid_opt, sfv, strike)
            if v_obs is not None:
                prev_v = float(v_map.get(sym, v_obs))
                v_map[sym] = 0.05 * v_obs + 0.95 * prev_v
            if sym not in v_map:
                continue

            fair_opt, delta = _bs_call_total_v(sfv, strike, float(v_map[sym]))
            pos = int(state.position.get(sym, 0))
            net_opt_delta += float(pos) * delta

            buy_cap = max(0, POSITION_LIMITS[sym] - pos)
            sell_cap = max(0, POSITION_LIMITS[sym] + pos)
            tb = 0
            ts_q = 0
            opt_orders: list[Order] = []

            if best_ask <= fair_opt - 1.5 and buy_cap > 0:
                q = min(10, abs(ob.sell_orders[best_ask]), buy_cap)
                if q > 0:
                    opt_orders.append(Order(sym, best_ask, q))
                    tb = q
            if best_bid >= fair_opt + 1.5 and sell_cap > 0:
                q = min(10, abs(ob.buy_orders[best_bid]), sell_cap)
                if q > 0:
                    opt_orders.append(Order(sym, best_bid, -q))
                    ts_q = q

            res_opt = fair_opt - 0.005 * pos
            q_bid = min(math.floor(res_opt - OPT_EDGE), best_bid + 1)
            q_ask = max(math.ceil(res_opt + OPT_EDGE), best_ask - 1)
            if q_bid >= best_ask:
                q_bid = best_ask - 1
            if q_ask <= best_bid:
                q_ask = best_bid + 1
            if q_bid < q_ask and q_bid > 0:
                if buy_cap - tb > 0:
                    opt_orders.append(Order(sym, q_bid, min(15, buy_cap - tb)))
                if sell_cap - ts_q > 0:
                    opt_orders.append(Order(sym, q_ask, -min(15, sell_cap - ts_q)))

            if opt_orders:
                result[sym] = opt_orders

        # 5. Delta hedge + residual spot MM on VELVETFRUIT_EXTRACT (+/-200)
        s_pos = int(state.position.get("VELVETFRUIT_EXTRACT", 0))
        tot_delta = float(s_pos) + net_opt_delta
        s_buy_cap = max(0, POSITION_LIMITS["VELVETFRUIT_EXTRACT"] - s_pos)
        s_sell_cap = max(0, POSITION_LIMITS["VELVETFRUIT_EXTRACT"] + s_pos)
        s_orders: list[Order] = []
        hb = 0
        hs = 0

        s_best_ask = min(s_depth.sell_orders.keys()) if s_depth.sell_orders else None
        s_best_bid = max(s_depth.buy_orders.keys()) if s_depth.buy_orders else None

        if tot_delta < -HEDGE_BAND and s_best_ask is not None and s_best_ask <= sfv + 2.5:
            q = min(math.floor(-tot_delta), abs(s_depth.sell_orders[s_best_ask]), s_buy_cap)
            if q > 0:
                s_orders.append(Order("VELVETFRUIT_EXTRACT", s_best_ask, q))
                hb = q
        elif tot_delta > HEDGE_BAND and s_best_bid is not None and s_best_bid >= sfv - 2.5:
            q = min(math.floor(tot_delta), abs(s_depth.buy_orders[s_best_bid]), s_sell_cap)
            if q > 0:
                s_orders.append(Order("VELVETFRUIT_EXTRACT", s_best_bid, -q))
                hs = q

        s_res = sfv - 0.03 * tot_delta
        sq_bid = (
            min(math.floor(s_res - 1.5), s_best_bid + 1)
            if s_best_bid is not None
            else math.floor(s_res - 1.5)
        )
        sq_ask = (
            max(math.ceil(s_res + 1.5), s_best_ask - 1)
            if s_best_ask is not None
            else math.ceil(s_res + 1.5)
        )
        if s_best_ask is not None and sq_bid >= s_best_ask:
            sq_bid = s_best_ask - 1
        if s_best_bid is not None and sq_ask <= s_best_bid:
            sq_ask = s_best_bid + 1
        if sq_bid < sq_ask and sq_bid > 0:
            if s_buy_cap - hb > 0:
                s_orders.append(Order("VELVETFRUIT_EXTRACT", sq_bid, min(35, s_buy_cap - hb)))
            if s_sell_cap - hs > 0:
                s_orders.append(Order("VELVETFRUIT_EXTRACT", sq_ask, -min(35, s_sell_cap - hs)))

        if s_orders:
            result["VELVETFRUIT_EXTRACT"] = s_orders

        return result, 0, json.dumps(mem, separators=(",", ":"))
