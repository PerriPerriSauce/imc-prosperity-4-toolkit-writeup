"""Standalone Prosperity 4 Round 3 competition submission trader.

Economic rationale:
- ``HYDROGEL_PACK`` and ``VELVETFRUIT_EXTRACT`` exhibit stationary OU
  mean reversion on Round 3 IS Days 0 and 1. Maintaining Bayesian-updated
  long-run anchors (mu_H, mu_S) allows directional reversion positioning plus
  spread capture.
- ``VEV_4000..5500`` call vouchers are priced via Black-Scholes total-volatility
  implied inversion around the OU mean-reverting spot fair value mu_S
  (using intrinsic parity for deep-ITM K <= 4500 and skipping worthless
  deep-OTM K >= 6000). Spot and voucher exposure is held unhedged rather than
  cross-hedged in spot because Round 3 IS ablation confirms spot delta hedging
  adds adverse taker slippage across wide spreads without reducing risk.
- Default ``spot_scale=30.0, enter_band=10.0`` comes from the strictly
  in-sample (Days 0 and 1) interior risk-adjusted plateau.
"""

from __future__ import annotations

import json
import math
from statistics import NormalDist
from typing import Any

from datamodel import Order, OrderDepth, Symbol, TradingState

_NORM = NormalDist(0.0, 1.0)

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

ACTIVE_STRIKES: tuple[int, ...] = (4000, 4500, 5000, 5100, 5200, 5300, 5400, 5500)


def _bs_call_total_v(spot: float, strike: float, total_v: float) -> float:
    if spot <= 0.0:
        return 0.0
    if total_v <= 1e-6:
        return max(0.0, spot - strike)
    d1 = (math.log(spot / strike) + 0.5 * total_v * total_v) / total_v
    d2 = d1 - total_v
    return spot * _NORM.cdf(d1) - strike * _NORM.cdf(d2)


def _inv_total_v(price: float, spot: float, strike: float) -> float | None:
    if spot <= 0.0:
        return None
    intr = max(0.0, spot - strike)
    if price <= intr + 0.2 or price >= spot:
        return None
    lo, hi = 1e-4, 0.5
    for _ in range(28):
        mid = 0.5 * (lo + hi)
        if _bs_call_total_v(spot, strike, mid) > price:
            hi = mid
        else:
            lo = mid
    return 0.5 * (lo + hi)


def _wall_mid(order_depth: OrderDepth) -> float | None:
    bids: dict[int, int] = {int(p): int(v) for p, v in order_depth.buy_orders.items() if v > 0}
    asks: dict[int, int] = {int(p): int(v) for p, v in order_depth.sell_orders.items() if v < 0}
    if not bids or not asks:
        return None
    wall_bid = max(bids.items(), key=lambda kv: (abs(kv[1]), kv[0]))[0]
    wall_ask = max(asks.items(), key=lambda kv: (abs(kv[1]), -kv[0]))[0]
    return 0.5 * (float(wall_bid) + float(wall_ask))


def _load_state(raw: str) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except (json.JSONDecodeError, TypeError, ValueError):
        return {}


class Trader:
    """Prosperity 4 Round 3 Trader calibrated strictly on Days 0 and 1."""

    def __init__(self, spot_scale: float = 30.0, enter_band: float = 10.0) -> None:
        self.spot_scale = float(spot_scale)
        self.enter_band = float(enter_band)
        self.h_n: int = 1500
        self.h_sum: float = 1500.0 * 9991.0
        self.s_n: int = 2500
        self.s_sum: float = 2500.0 * 5250.0
        self.v_map: dict[str, float] = {}

    def _hydrate_state(self, raw: str) -> None:
        persisted = _load_state(raw)
        if isinstance(persisted.get("h_n"), int) and persisted["h_n"] > 0:
            self.h_n = persisted["h_n"]
        if isinstance(persisted.get("h_sum"), (int, float)):
            self.h_sum = float(persisted["h_sum"])
        if isinstance(persisted.get("s_n"), int) and persisted["s_n"] > 0:
            self.s_n = persisted["s_n"]
        if isinstance(persisted.get("s_sum"), (int, float)):
            self.s_sum = float(persisted["s_sum"])
        raw_v = persisted.get("v")
        if isinstance(raw_v, dict):
            for sym, val in raw_v.items():
                if isinstance(sym, str) and isinstance(val, (int, float)) and val > 0.0:
                    self.v_map.setdefault(sym, float(val))

    def _trade_hydrogel(self, ob: OrderDepth, pos: int) -> list[Order]:
        bids = {p: v for p, v in ob.buy_orders.items() if v > 0}
        asks = {p: v for p, v in ob.sell_orders.items() if v < 0}
        if not bids or not asks:
            return []

        wm = _wall_mid(ob)
        if wm is not None:
            self.h_n += 1
            self.h_sum += wm
        mu_h = self.h_sum / max(1, self.h_n)
        if wm is None:
            return []

        dev_h = wm - mu_h
        limit = POSITION_LIMITS["HYDROGEL_PACK"]
        tgt = round(max(-1.0, min(1.0, -dev_h / 40.0)) * limit)
        bc = max(0, limit - pos)
        sc = max(0, limit + pos)
        orders: list[Order] = []
        tb = 0
        ts_q = 0

        if tgt > pos and dev_h <= -10.0:
            need = min(tgt - pos, bc)
            for ap in sorted(asks):
                if ap <= mu_h - 4.0 and need > 0:
                    q = min(abs(asks[ap]), need)
                    if q > 0:
                        orders.append(Order("HYDROGEL_PACK", int(ap), int(q)))
                        tb += q
                        need -= q
        elif tgt < pos and dev_h >= 10.0:
            need = min(pos - tgt, sc)
            for bp in sorted(bids, reverse=True):
                if bp >= mu_h + 4.0 and need > 0:
                    q = min(abs(bids[bp]), need)
                    if q > 0:
                        orders.append(Order("HYDROGEL_PACK", int(bp), -int(q)))
                        ts_q += q
                        need -= q

        proj = pos + tb - ts_q
        fv_h = 0.35 * wm + 0.65 * mu_h
        res = fv_h - 0.05 * (proj - tgt)
        bb = max(bids)
        ba = min(asks)
        qb = min(math.floor(res - 4.5), bb + 1)
        qa = max(math.ceil(res + 4.5), ba - 1)
        if qb >= ba:
            qb = ba - 1
        if qa <= bb:
            qa = bb + 1
        if qb < qa and qb > 0:
            if bc - tb > 0:
                orders.append(Order("HYDROGEL_PACK", int(qb), int(min(60, bc - tb))))
            if sc - ts_q > 0:
                orders.append(Order("HYDROGEL_PACK", int(qa), -int(min(60, sc - ts_q))))
        return orders

    def run(self, state: TradingState) -> tuple[dict[Symbol, list[Order]], int, str]:
        """Generate competition-compliant Round 3 orders."""
        if self.h_n == 1500 and self.s_n == 2500 and not self.v_map:
            self._hydrate_state(getattr(state, "traderData", ""))

        result: dict[Symbol, list[Order]] = {}
        order_depths = getattr(state, "order_depths", {}) or {}
        positions = getattr(state, "position", {}) or {}

        h_ob = order_depths.get("HYDROGEL_PACK")
        if h_ob is not None:
            h_orders = self._trade_hydrogel(h_ob, int(positions.get("HYDROGEL_PACK", 0)))
            if h_orders:
                result["HYDROGEL_PACK"] = h_orders

        s_ob = order_depths.get("VELVETFRUIT_EXTRACT")
        s_wm = _wall_mid(s_ob) if s_ob is not None else None
        if s_ob is not None and s_wm is not None:
            s_bids = {p: v for p, v in s_ob.buy_orders.items() if v > 0}
            s_asks = {p: v for p, v in s_ob.sell_orders.items() if v < 0}
            if s_bids and s_asks:
                self.s_n += 1
                self.s_sum += s_wm
                mu_s = self.s_sum / max(1, self.s_n)
                dev_s = s_wm - mu_s
                tgt_frac = (
                    0.0
                    if abs(dev_s) <= 2.0
                    else max(-1.0, min(1.0, -dev_s / self.spot_scale))
                )

                s_pos = int(positions.get("VELVETFRUIT_EXTRACT", 0))
                s_limit = POSITION_LIMITS["VELVETFRUIT_EXTRACT"]
                s_tgt = round(tgt_frac * s_limit)
                bc = max(0, s_limit - s_pos)
                sc = max(0, s_limit + s_pos)
                s_orders: list[Order] = []
                tb = 0
                ts_q = 0

                if s_tgt > s_pos and (dev_s <= -self.enter_band or (s_pos < 0 and dev_s <= 2.0)):
                    need = min(s_tgt - s_pos, bc)
                    for ap in sorted(s_asks):
                        if ap <= mu_s + 1.0 and need > 0:
                            q = min(abs(s_asks[ap]), need)
                            if q > 0:
                                s_orders.append(Order("VELVETFRUIT_EXTRACT", int(ap), int(q)))
                                tb += q
                                need -= q
                elif s_tgt < s_pos and (dev_s >= self.enter_band or (s_pos > 0 and dev_s >= -2.0)):
                    need = min(s_pos - s_tgt, sc)
                    for bp in sorted(s_bids, reverse=True):
                        if bp >= mu_s - 1.0 and need > 0:
                            q = min(abs(s_bids[bp]), need)
                            if q > 0:
                                s_orders.append(Order("VELVETFRUIT_EXTRACT", int(bp), -int(q)))
                                ts_q += q
                                need -= q

                proj = s_pos + tb - ts_q
                s_res = (0.25 * s_wm + 0.75 * mu_s) - 0.02 * (proj - s_tgt)
                s_bb = max(s_bids)
                s_ba = min(s_asks)
                qb = min(math.floor(s_res - 1.5), s_bb + 1)
                qa = max(math.ceil(s_res + 1.5), s_ba - 1)
                if qb >= s_ba:
                    qb = s_ba - 1
                if qa <= s_bb:
                    qa = s_bb + 1
                if qb < qa and qb > 0:
                    if bc - tb > 0:
                        s_orders.append(
                            Order("VELVETFRUIT_EXTRACT", int(qb), int(min(60, bc - tb))),
                        )
                    if sc - ts_q > 0:
                        s_orders.append(
                            Order("VELVETFRUIT_EXTRACT", int(qa), -int(min(60, sc - ts_q))),
                        )
                if s_orders:
                    result["VELVETFRUIT_EXTRACT"] = s_orders

                for strike in ACTIVE_STRIKES:
                    sym = f"VEV_{strike}"
                    v_ob = order_depths.get(sym)
                    if v_ob is None:
                        continue
                    v_bids = {p: v for p, v in v_ob.buy_orders.items() if v > 0}
                    v_asks = {p: v for p, v in v_ob.sell_orders.items() if v < 0}
                    if not v_bids or not v_asks:
                        continue
                    v_bb = max(v_bids)
                    v_ba = min(v_asks)
                    mid_opt = 0.5 * (v_bb + v_ba)

                    if strike <= 4500:
                        fair_mu = max(0.0, mu_s - strike)
                        fair_now = max(0.0, s_wm - strike)
                    else:
                        v_obs = _inv_total_v(mid_opt, s_wm, float(strike))
                        if v_obs is not None:
                            self.v_map[sym] = 0.02 * v_obs + 0.98 * self.v_map.get(sym, v_obs)
                        if sym not in self.v_map:
                            continue
                        fair_mu = _bs_call_total_v(mu_s, float(strike), self.v_map[sym])
                        fair_now = _bs_call_total_v(s_wm, float(strike), self.v_map[sym])

                    pos = int(positions.get(sym, 0))
                    o_limit = POSITION_LIMITS[sym]
                    sp_opt = v_ba - v_bb
                    o_tgt = round(tgt_frac * o_limit)
                    obc = max(0, o_limit - pos)
                    osc = max(0, o_limit + pos)
                    o_orders: list[Order] = []
                    otb = 0
                    ots = 0
                    req = max(1.0, 0.25 * sp_opt)

                    if o_tgt > pos and v_ba <= fair_mu - req:
                        need = min(o_tgt - pos, obc)
                        for ap in sorted(v_asks):
                            if ap <= fair_mu - req and need > 0:
                                q = min(abs(v_asks[ap]), need)
                                if q > 0:
                                    o_orders.append(Order(sym, int(ap), int(q)))
                                    otb += q
                                    need -= q
                    elif o_tgt < pos and v_bb >= fair_mu + req:
                        need = min(pos - o_tgt, osc)
                        for bp in sorted(v_bids, reverse=True):
                            if bp >= fair_mu + req and need > 0:
                                q = min(abs(v_bids[bp]), need)
                                if q > 0:
                                    o_orders.append(Order(sym, int(bp), -int(q)))
                                    ots += q
                                    need -= q

                    oproj = pos + otb - ots
                    ores = (0.25 * fair_now + 0.75 * fair_mu) - 0.004 * (oproj - o_tgt)
                    oqb = min(math.floor(ores - 1.0), v_bb + 1)
                    oqa = max(math.ceil(ores + 1.0), v_ba - 1)
                    if oqb >= v_ba:
                        oqb = v_ba - 1
                    if oqa <= v_bb:
                        oqa = v_bb + 1
                    if oqb < oqa and oqb > 0:
                        if obc - otb > 0:
                            o_orders.append(Order(sym, int(oqb), int(min(40, obc - otb))))
                        if osc - ots > 0:
                            o_orders.append(Order(sym, int(oqa), -int(min(40, osc - ots))))
                    if o_orders:
                        result[sym] = o_orders

        next_data = json.dumps(
            {
                "h_n": self.h_n,
                "h_sum": round(self.h_sum, 4),
                "s_n": self.s_n,
                "s_sum": round(self.s_sum, 4),
                "v": {k: round(val, 6) for k, val in self.v_map.items()},
            },
        )
        return result, 0, next_data
