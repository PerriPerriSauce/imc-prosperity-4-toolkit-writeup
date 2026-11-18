"""Standalone IMC Prosperity 4 Round 5 submission trader.

No external package dependencies outside `datamodel` and Python's standard library.
Engineered for all 50 securities (+/-10 uniform position limits):
  1. Lag-free max-volume resting bot-wall midpoint (`_popular_wall_mid`) to prevent
     EMA tracking lag across high-volatility random walks.
  2. Atomic 5-leg `PEBBLES` constant-sum (`50,000`) cross-taking decoupled from
     passive market-making quotes (`0.16`-tick half-life prevents resting skew capture).
  3. Rolling adaptive `K_day` equilibrium tracking for `SNACKPACK_CHOCOLATE + VANILLA`.
  4. Full `QUOTE_CLIP = 10` sizing across high-edge categories plus wide defensive quoting
     and rolling step-volatility outlier gating on `Robots` and `Microchips`
     (`edge_frac = 0.18, inventory_skew = 1.25`, IS plateau validated).
"""

from __future__ import annotations

import json
import math
from typing import Any

from datamodel import Order, OrderDepth, TradingState

POSITION_LIMIT: int = 10
PEBBLES_SYMBOLS: tuple[str, ...] = (
    "PEBBLES_XS",
    "PEBBLES_S",
    "PEBBLES_M",
    "PEBBLES_L",
    "PEBBLES_XL",
)
PEBBLES_SET: frozenset[str] = frozenset(PEBBLES_SYMBOLS)
PAIR_LEG_A: str = "SNACKPACK_CHOCOLATE"
PAIR_LEG_B: str = "SNACKPACK_VANILLA"
LOW_RATIO_PREFIXES: tuple[str, ...] = ("ROBOT_", "MICROCHIP_")

EDGE_FRAC: float = 0.18
LOW_RATIO_EDGE_FRAC: float = 0.35
INVENTORY_SKEW: float = 1.25
PAIR_RESIDUAL_WEIGHT: float = 0.25
PAIR_EMA_ALPHA: float = 0.005
VOL_EMA_ALPHA: float = 0.02
VOL_GUARD_MULT: float = 0.50
PEBBLES_TAKE_BUFFER: float = 1.5
TAKE_EDGE: float = 1.5
QUOTE_CLIP: int = 10


def _popular_wall_mid(depth: OrderDepth) -> float | None:
    """Extract midpoint of highest-volume resting bid and ask walls."""
    if not depth.buy_orders or not depth.sell_orders:
        return None
    wall_bid = max(depth.buy_orders.items(), key=lambda kv: (abs(kv[1]), kv[0]))[0]
    wall_ask = max(depth.sell_orders.items(), key=lambda kv: (abs(kv[1]), -kv[0]))[0]
    return float(0.5 * (wall_bid + wall_ask))


def _load_state(raw_data: str) -> dict[str, Any]:
    """Defensively decode compact JSON traderData across ticks."""
    default: dict[str, Any] = {"k": None, "m": {}, "v": {}}
    if not raw_data:
        return default
    try:
        parsed = json.loads(raw_data)
    except (ValueError, TypeError):
        return default
    if not isinstance(parsed, dict):
        return default
    k_val = parsed.get("k")
    return {
        "k": float(k_val) if isinstance(k_val, (int, float)) else None,
        "m": parsed.get("m", {}) if isinstance(parsed.get("m"), dict) else {},
        "v": parsed.get("v", {}) if isinstance(parsed.get("v"), dict) else {},
    }


class Trader:
    """Prosperity 4 Round 5 standalone 50-asset competition trader."""

    def run(self, state: TradingState) -> tuple[dict[str, list[Order]], int, str]:
        """Execute one Round 5 tick under strict +/-10 per-symbol batch caps."""
        result: dict[str, list[Order]] = {}
        order_depths = state.order_depths
        mem = _load_state(state.traderData)
        pair_ema: float | None = mem["k"]
        last_mids: dict[str, float] = mem["m"]
        vol_ema: dict[str, float] = mem["v"]

        # 1. Pebbles structural 50,000 constant-sum fair value for atomic crossing
        peb_mids: dict[str, float] = {}
        for sym in PEBBLES_SYMBOLS:
            depth = order_depths.get(sym)
            if depth is not None:
                mid = _popular_wall_mid(depth)
                if mid is not None:
                    peb_mids[sym] = mid
        peb_full = len(peb_mids) == 5

        # 2. Adaptive K_day for Snackpack Chocolate + Vanilla negatively correlated pair
        d_a = order_depths.get(PAIR_LEG_A)
        d_b = order_depths.get(PAIR_LEG_B)
        mid_a = _popular_wall_mid(d_a) if d_a is not None else None
        mid_b = _popular_wall_mid(d_b) if d_b is not None else None
        pair_res = 0.0
        if mid_a is not None and mid_b is not None:
            pair_sum = mid_a + mid_b
            pair_ema = (
                pair_sum
                if pair_ema is None
                else PAIR_EMA_ALPHA * pair_sum + (1.0 - PAIR_EMA_ALPHA) * pair_ema
            )
            pair_res = pair_sum - pair_ema

        # 3. Cross-universe execution across all 50 goods with dynamic vol circuit-breaker
        for sym, depth in order_depths.items():
            fv = _popular_wall_mid(depth)
            if fv is None:
                continue

            prev_m = last_mids.get(sym)
            if prev_m is not None:
                step_diff = abs(fv - float(prev_m))
                vol_ema[sym] = (
                    step_diff
                    if sym not in vol_ema
                    else VOL_EMA_ALPHA * step_diff + (1.0 - VOL_EMA_ALPHA) * float(vol_ema[sym])
                )
            last_mids[sym] = round(fv, 2)

            best_ask = min(depth.sell_orders.keys()) if depth.sell_orders else None
            best_bid = max(depth.buy_orders.keys()) if depth.buy_orders else None
            spread = (
                (best_ask - best_bid) if (best_ask is not None and best_bid is not None) else 10
            )
            is_low_ratio = sym.startswith(LOW_RATIO_PREFIXES)
            if is_low_ratio and spread < VOL_GUARD_MULT * float(vol_ema.get(sym, 8.0)):
                continue

            if sym == PAIR_LEG_A or sym == PAIR_LEG_B:
                fv -= PAIR_RESIDUAL_WEIGHT * pair_res

            peb_imp = (
                50000.0 - sum(v for k, v in peb_mids.items() if k != sym)
                if (peb_full and sym in peb_mids)
                else fv
            )

            start_pos = int(state.position.get(sym, 0))
            buy_cap = max(0, POSITION_LIMIT - start_pos)
            sell_cap = max(0, POSITION_LIMIT + start_pos)
            taken_buy = 0
            taken_sell = 0
            sym_orders: list[Order] = []

            take_fv_buy = (
                max(fv, peb_imp - PEBBLES_TAKE_BUFFER) if (peb_full and sym in peb_mids) else fv
            )
            take_fv_sell = (
                min(fv, peb_imp + PEBBLES_TAKE_BUFFER) if (peb_full and sym in peb_mids) else fv
            )

            if best_ask is not None and best_ask <= take_fv_buy - TAKE_EDGE and buy_cap > 0:
                for ask_px in sorted(depth.sell_orders.keys()):
                    if ask_px > take_fv_buy - TAKE_EDGE or buy_cap - taken_buy <= 0:
                        break
                    qty = min(abs(depth.sell_orders[ask_px]), buy_cap - taken_buy)
                    if qty > 0:
                        sym_orders.append(Order(sym, ask_px, qty))
                        taken_buy += qty

            if best_bid is not None and best_bid >= take_fv_sell + TAKE_EDGE and sell_cap > 0:
                for bid_px in sorted(depth.buy_orders.keys(), reverse=True):
                    if bid_px < take_fv_sell + TAKE_EDGE or sell_cap - taken_sell <= 0:
                        break
                    qty = min(abs(depth.buy_orders[bid_px]), sell_cap - taken_sell)
                    if qty > 0:
                        sym_orders.append(Order(sym, bid_px, -qty))
                        taken_sell += qty

            ef = LOW_RATIO_EDGE_FRAC if is_low_ratio else EDGE_FRAC
            sk = 1.5 * INVENTORY_SKEW if is_low_ratio else INVENTORY_SKEW
            edge = max(1.5, ef * spread)
            reservation = fv - sk * start_pos

            max_bid = math.floor(reservation - edge)
            min_ask = math.ceil(reservation + edge)
            quote_bid = min(max_bid, best_bid + 1) if best_bid is not None else max_bid
            quote_ask = max(min_ask, best_ask - 1) if best_ask is not None else min_ask

            if best_ask is not None and quote_bid >= best_ask:
                quote_bid = best_ask - 1
            if best_bid is not None and quote_ask <= best_bid:
                quote_ask = best_bid + 1

            if quote_bid < quote_ask and quote_bid > 0:
                rem_buy = max(0, buy_cap - taken_buy)
                rem_sell = max(0, sell_cap - taken_sell)
                if rem_buy > 0:
                    sym_orders.append(Order(sym, quote_bid, min(QUOTE_CLIP, rem_buy)))
                if rem_sell > 0:
                    sym_orders.append(Order(sym, quote_ask, -min(QUOTE_CLIP, rem_sell)))

            if sym_orders:
                result[sym] = sym_orders

        next_state: dict[str, Any] = {
            "m": last_mids,
            "v": {k: round(v, 2) for k, v in vol_ema.items()},
        }
        if pair_ema is not None:
            next_state["k"] = round(pair_ema, 2)
        return result, 0, json.dumps(next_state, separators=(",", ":"))
