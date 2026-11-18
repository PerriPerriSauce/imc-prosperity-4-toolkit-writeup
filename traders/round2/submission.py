"""Standalone IMC Prosperity 4 Round 2 submission trader.

No external package dependencies outside `datamodel` and Python's standard library.
Implements max-volume resting bot-wall fair value filtering, alpha-beta drift
estimation for `INTARIAN_PEPPER_ROOT`, taker arbitrage, and inventory-skewed
penny-improving market making tuned for +/-80 position limits (IS Plateau:
min_edge=3.5, inventory_skew=0.75; Clip=30).
"""

from __future__ import annotations

import json
import math
from typing import Any

from datamodel import Order, OrderDepth, TradingState

POSITION_LIMITS: dict[str, int] = {
    "ASH_COATED_OSMIUM": 80,
    "INTARIAN_PEPPER_ROOT": 80,
}

MIN_EDGE: float = 3.5
TAKE_EDGE: float = 1.0
INVENTORY_SKEW: float = 0.75
QUOTE_CLIP: int = 30
EMA_ALPHA: float = 0.25
DRIFT_BETA: float = 0.01


def _popular_wall_mid(depth: OrderDepth) -> float | None:
    """Extract midpoint of maximum-volume resting bid and ask walls."""
    if not depth.buy_orders or not depth.sell_orders:
        return None
    wall_bid = max(depth.buy_orders.items(), key=lambda kv: (abs(kv[1]), kv[0]))[0]
    wall_ask = max(depth.sell_orders.items(), key=lambda kv: (abs(kv[1]), -kv[0]))[0]
    return float(0.5 * (wall_bid + wall_ask))


def _load_state(raw_data: str) -> dict[str, Any]:
    """Defensively decode JSON traderData."""
    default: dict[str, Any] = {"fv": {}, "drift": {}, "ts": {}}
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
        "drift": parsed.get("drift", {}) if isinstance(parsed.get("drift"), dict) else {},
        "ts": parsed.get("ts", {}) if isinstance(parsed.get("ts"), dict) else {},
    }


class Trader:
    """Prosperity 4 Round 2 standalone competition trader."""

    def _update_fair_value(
        self,
        symbol: str,
        depth: OrderDepth,
        timestamp: int,
        state_mem: dict[str, Any],
    ) -> float | None:
        obs_mid = _popular_wall_mid(depth)
        fv_map: dict[str, float] = state_mem["fv"]
        drift_map: dict[str, float] = state_mem["drift"]
        ts_map: dict[str, int] = state_mem["ts"]

        if symbol == "ASH_COATED_OSMIUM":
            if obs_mid is not None:
                prev = float(fv_map.get(symbol, obs_mid))
                fv_map[symbol] = EMA_ALPHA * obs_mid + (1.0 - EMA_ALPHA) * prev
            return float(fv_map[symbol]) if symbol in fv_map else None

        # INTARIAN_PEPPER_ROOT: alpha-beta drift-compensated wall-mid tracker
        last_ts = int(ts_map.get(symbol, timestamp))
        dt_steps = max(1.0, (timestamp - last_ts) / 100.0) if timestamp > last_ts else 1.0

        if obs_mid is not None:
            if symbol not in fv_map:
                fv_map[symbol] = obs_mid
                drift_map[symbol] = 0.0
            else:
                pred = float(fv_map[symbol]) + float(drift_map.get(symbol, 0.0)) * dt_steps
                innov = obs_mid - pred
                fv_map[symbol] = pred + EMA_ALPHA * innov
                drift_map[symbol] = float(drift_map.get(symbol, 0.0)) + DRIFT_BETA * (
                    innov / dt_steps
                )
            ts_map[symbol] = timestamp
            return float(fv_map[symbol])

        if symbol in fv_map:
            pred = float(fv_map[symbol]) + float(drift_map.get(symbol, 0.0)) * dt_steps
            fv_map[symbol] = pred
            ts_map[symbol] = timestamp
            return pred

        return None

    def _trade_symbol(
        self,
        symbol: str,
        depth: OrderDepth,
        fv: float,
        start_pos: int,
    ) -> list[Order]:
        orders: list[Order] = []
        limit = POSITION_LIMITS[symbol]
        buy_cap = max(0, limit - start_pos)
        sell_cap = max(0, limit + start_pos)
        taken_buy = 0
        taken_sell = 0

        if depth.sell_orders:
            best_ask = min(depth.sell_orders.keys())
            if best_ask <= fv - TAKE_EDGE and buy_cap > 0:
                for ask_px in sorted(depth.sell_orders.keys()):
                    if ask_px > fv - TAKE_EDGE or buy_cap - taken_buy <= 0:
                        break
                    qty = min(abs(depth.sell_orders[ask_px]), buy_cap - taken_buy)
                    if qty > 0:
                        orders.append(Order(symbol, ask_px, qty))
                        taken_buy += qty
        else:
            best_ask = None

        if depth.buy_orders:
            best_bid = max(depth.buy_orders.keys())
            if best_bid >= fv + TAKE_EDGE and sell_cap > 0:
                for bid_px in sorted(depth.buy_orders.keys(), reverse=True):
                    if bid_px < fv + TAKE_EDGE or sell_cap - taken_sell <= 0:
                        break
                    qty = min(abs(depth.buy_orders[bid_px]), sell_cap - taken_sell)
                    if qty > 0:
                        orders.append(Order(symbol, bid_px, -qty))
                        taken_sell += qty
        else:
            best_bid = None

        rem_buy = max(0, buy_cap - taken_buy)
        rem_sell = max(0, sell_cap - taken_sell)
        reservation = fv - INVENTORY_SKEW * start_pos

        max_bid = math.floor(reservation - MIN_EDGE)
        min_ask = math.ceil(reservation + MIN_EDGE)
        quote_bid = min(max_bid, best_bid + 1) if best_bid is not None else max_bid
        quote_ask = max(min_ask, best_ask - 1) if best_ask is not None else min_ask

        if best_ask is not None and quote_bid >= best_ask:
            quote_bid = best_ask - 1
        if best_bid is not None and quote_ask <= best_bid:
            quote_ask = best_bid + 1

        if quote_bid < quote_ask and quote_bid > 0:
            if rem_buy > 0:
                orders.append(Order(symbol, quote_bid, min(QUOTE_CLIP, rem_buy)))
            if rem_sell > 0:
                orders.append(Order(symbol, quote_ask, -min(QUOTE_CLIP, rem_sell)))

        return orders

    def run(self, state: TradingState) -> tuple[dict[str, list[Order]], int, str]:
        """Execute one Round 2 tick under Prosperity submission protocol."""
        result: dict[str, list[Order]] = {}
        state_mem = _load_state(state.traderData)

        for symbol in POSITION_LIMITS:
            depth = state.order_depths.get(symbol)
            if depth is None:
                continue
            fv = self._update_fair_value(symbol, depth, state.timestamp, state_mem)
            if fv is None:
                continue
            start_pos = int(state.position.get(symbol, 0))
            sym_orders = self._trade_symbol(symbol, depth, fv, start_pos)
            if sym_orders:
                result[symbol] = sym_orders

        return result, 0, json.dumps(state_mem, separators=(",", ":"))
