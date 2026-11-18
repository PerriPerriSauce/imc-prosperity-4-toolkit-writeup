"""Standalone IMC Prosperity 4 Round 1 Submission Trader.

Microstructure Design:
- Uses max-volume resting bot-wall midpoint (`_popular_wall_mid`) to filter out
  transient L1 inside-spread noise on two-sided books.
- Uses EMA smoothing on stationary `ASH_COATED_OSMIUM` and an alpha-beta
  drift-compensated filter on linearly drifting `INTARIAN_PEPPER_ROOT`.
- Captures mispriced liquidity as taker, then penny-improves the resting bot
  touch (`best_bid + 1` / `best_ask - 1`) clamped by `reservation +/- min_edge`
  (`min_edge=1.5`, `inventory_skew=0.80`, selected via 2D plateau stability).
- Enforces starting-position aggregate worst-case limits before all quotes.

Compliance & Assumptions:
- Imports strictly from `datamodel` and Python standard library (zero toolkit imports).
- POSITION_LIMITS defaults to 20 per product as a configurable assumption
  (exact official Prosperity 4 Round 1 limits remain unverified without portal logs).
"""

from __future__ import annotations

import json
import math
from typing import Any

from datamodel import Order, OrderDepth, Symbol, TradingState

# Explicit configurable position-limit assumption (UNVERIFIED against official wiki)
POSITION_LIMITS: dict[str, int] = {
    "ASH_COATED_OSMIUM": 20,
    "INTARIAN_PEPPER_ROOT": 20,
}


def _popular_wall_mid(depth: OrderDepth) -> float | None:
    """Estimate fair value from max-volume resting bot walls on two-sided books."""
    if not depth.buy_orders or not depth.sell_orders:
        return None
    wall_bid = max(depth.buy_orders.items(), key=lambda kv: (abs(kv[1]), kv[0]))[0]
    wall_ask = max(depth.sell_orders.items(), key=lambda kv: (abs(kv[1]), -kv[0]))[0]
    return float((wall_bid + wall_ask) / 2.0)


def _execute_refined_mm(
    symbol: Symbol,
    depth: OrderDepth,
    fv: float,
    start_pos: int,
    limit: int,
    take_edge: float = 1.0,
    min_edge: float = 1.5,
    inventory_skew: float = 0.80,
    quote_size: int = 5,
) -> list[Order]:
    """Take mispriced liquidity and penny-improve bot quotes around reservation price."""
    orders: list[Order] = []
    buy_cap = max(0, limit - start_pos)
    sell_cap = max(0, limit + start_pos)
    taken_buy = 0
    taken_sell = 0

    for ask_px in sorted(depth.sell_orders.keys()):
        if ask_px > fv - take_edge or buy_cap - taken_buy <= 0:
            break
        avail = abs(depth.sell_orders[ask_px])
        qty = min(avail, buy_cap - taken_buy)
        if qty > 0:
            orders.append(Order(symbol, ask_px, qty))
            taken_buy += qty

    for bid_px in sorted(depth.buy_orders.keys(), reverse=True):
        if bid_px < fv + take_edge or sell_cap - taken_sell <= 0:
            break
        avail = abs(depth.buy_orders[bid_px])
        qty = min(avail, sell_cap - taken_sell)
        if qty > 0:
            orders.append(Order(symbol, bid_px, -qty))
            taken_sell += qty

    rem_buy = max(0, buy_cap - taken_buy)
    rem_sell = max(0, sell_cap - taken_sell)
    reservation = fv - inventory_skew * start_pos

    max_bid = math.floor(reservation - min_edge)
    min_ask = math.ceil(reservation + min_edge)

    best_bid = max(depth.buy_orders.keys()) if depth.buy_orders else None
    best_ask = min(depth.sell_orders.keys()) if depth.sell_orders else None

    quote_bid = min(max_bid, best_bid + 1) if best_bid is not None else max_bid
    quote_ask = max(min_ask, best_ask - 1) if best_ask is not None else min_ask

    if best_ask is not None and quote_bid >= best_ask:
        quote_bid = best_ask - 1
    if best_bid is not None and quote_ask <= best_bid:
        quote_ask = best_bid + 1

    if quote_bid < quote_ask and quote_bid > 0:
        if rem_buy > 0:
            orders.append(Order(symbol, quote_bid, min(quote_size, rem_buy)))
        if rem_sell > 0:
            orders.append(Order(symbol, quote_ask, -min(quote_size, rem_sell)))

    return orders


class Trader:
    """Competition-facing Round 1 algorithmic trader."""

    def _load_state(self, trader_data: str) -> dict[str, Any]:
        if not trader_data:
            return {}
        try:
            loaded = json.loads(trader_data)
            return loaded if isinstance(loaded, dict) else {}
        except (json.JSONDecodeError, TypeError):
            return {}

    def _update_osmium_fv(self, depth: OrderDepth, mem: dict[str, Any]) -> float | None:
        obs = _popular_wall_mid(depth)
        if obs is not None:
            prev_fv = float(mem.get("fv", obs))
            fv = 0.25 * obs + 0.75 * prev_fv
            mem["fv"] = fv
            return fv
        return float(mem["fv"]) if "fv" in mem else None

    def _update_pepper_fv(
        self,
        timestamp: int,
        depth: OrderDepth,
        mem: dict[str, Any],
    ) -> float | None:
        last_ts = int(mem.get("ts", timestamp))
        dt_steps = max(1.0, (timestamp - last_ts) / 100.0) if timestamp > last_ts else 1.0
        obs = _popular_wall_mid(depth)

        if obs is not None:
            if "fv" not in mem:
                fv = obs
                drift = 0.0
            else:
                drift = float(mem.get("drift", 0.0))
                pred = float(mem["fv"]) + drift * dt_steps
                innov = obs - pred
                fv = pred + 0.25 * innov
                drift = drift + 0.01 * (innov / dt_steps)
            mem["fv"] = fv
            mem["drift"] = drift
            mem["ts"] = timestamp
            return fv

        if "fv" in mem:
            drift = float(mem.get("drift", 0.0))
            fv = float(mem["fv"]) + drift * dt_steps
            mem["fv"] = fv
            mem["ts"] = timestamp
            return fv

        return None

    def run(self, state: TradingState) -> tuple[dict[Symbol, list[Order]], int, str]:
        """Process current tick state and emit orders, conversions, and serialized state."""
        persisted = self._load_state(state.traderData)
        result: dict[Symbol, list[Order]] = {}

        if "ASH_COATED_OSMIUM" in state.order_depths:
            sym = "ASH_COATED_OSMIUM"
            depth = state.order_depths[sym]
            mem = persisted.setdefault(sym, {})
            fv = self._update_osmium_fv(depth, mem)
            if fv is not None:
                result[sym] = _execute_refined_mm(
                    symbol=sym,
                    depth=depth,
                    fv=fv,
                    start_pos=state.position.get(sym, 0),
                    limit=POSITION_LIMITS.get(sym, 20),
                )

        if "INTARIAN_PEPPER_ROOT" in state.order_depths:
            sym = "INTARIAN_PEPPER_ROOT"
            depth = state.order_depths[sym]
            mem = persisted.setdefault(sym, {})
            fv = self._update_pepper_fv(state.timestamp, depth, mem)
            if fv is not None:
                result[sym] = _execute_refined_mm(
                    symbol=sym,
                    depth=depth,
                    fv=fv,
                    start_pos=state.position.get(sym, 0),
                    limit=POSITION_LIMITS.get(sym, 20),
                )

        return result, 0, json.dumps(persisted, separators=(",", ":"))
