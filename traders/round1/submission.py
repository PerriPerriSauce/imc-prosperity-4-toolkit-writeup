"""Standalone Prosperity 4 Round 1 competition submission trader.

Economic rationale:
- ``ASH_COATED_OSMIUM`` mean-reverts tightly around 10,000 XIRECs with a wide
  16-XIREC stationary spread; market making with inventory-skewed reservation
  prices around 10,000 and taking crossed quotes captures spread plus mean
  reversion without ad-hoc directional exposure.
- ``INTARIAN_PEPPER_ROOT`` exhibits a deterministic +0.10 XIREC/tick upward
  drift (+1,000 XIRECs/day across 10,000 ticks) on Round 0/IS logs; accumulating
  up to the official +80 position limit against conservative wall-mid fair
  value captures structural carry while passive upper quotes harvest extreme
  liquidity demand.
"""

from __future__ import annotations

import json
import math
from typing import Any

from datamodel import Order, OrderDepth, Symbol, TradingState

POSITION_LIMITS: dict[str, int] = {
    "ASH_COATED_OSMIUM": 80,
    "INTARIAN_PEPPER_ROOT": 80,
}


def _wall_mid(order_depth: OrderDepth) -> float | None:
    """Compute midpoint of highest-volume bid and ask levels."""
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
    """Prosperity 4 Round 1 Trader calibrated strictly on Days -2 and -1."""

    def __init__(self, min_edge: float = 2.0, inventory_skew: float = 0.40) -> None:
        self.min_edge = float(min_edge)
        self.inventory_skew = float(inventory_skew)
        self.last_pepper_mid: float | None = None

    def _trade_osmium(
        self,
        order_depth: OrderDepth,
        position: int,
    ) -> list[Order]:
        bids = {p: v for p, v in order_depth.buy_orders.items() if v > 0}
        asks = {p: v for p, v in order_depth.sell_orders.items() if v < 0}
        if not bids or not asks:
            return []

        limit = POSITION_LIMITS["ASH_COATED_OSMIUM"]
        best_bid = max(bids)
        best_ask = min(asks)
        fv = 10000.0
        buy_cap = max(0, limit - position)
        sell_cap = max(0, limit + position)
        orders: list[Order] = []
        taken_buy = 0
        taken_sell = 0

        for ask_price in sorted(asks):
            if ask_price < fv and buy_cap - taken_buy > 0:
                qty = min(abs(asks[ask_price]), buy_cap - taken_buy)
                if qty > 0:
                    orders.append(Order("ASH_COATED_OSMIUM", int(ask_price), int(qty)))
                    taken_buy += qty

        for bid_price in sorted(bids, reverse=True):
            if bid_price > fv and sell_cap - taken_sell > 0:
                qty = min(abs(bids[bid_price]), sell_cap - taken_sell)
                if qty > 0:
                    orders.append(Order("ASH_COATED_OSMIUM", int(bid_price), -int(qty)))
                    taken_sell += qty

        proj_pos = position + taken_buy - taken_sell
        res = fv - self.inventory_skew * proj_pos
        quote_bid = min(math.floor(res - self.min_edge), best_bid + 1)
        quote_ask = max(math.ceil(res + self.min_edge), best_ask - 1)
        if quote_bid >= best_ask:
            quote_bid = best_ask - 1
        if quote_ask <= best_bid:
            quote_ask = best_bid + 1

        if quote_bid < quote_ask and quote_bid > 0:
            rem_buy = buy_cap - taken_buy
            rem_sell = sell_cap - taken_sell
            if rem_buy > 0:
                orders.append(Order("ASH_COATED_OSMIUM", int(quote_bid), int(rem_buy)))
            if rem_sell > 0:
                orders.append(Order("ASH_COATED_OSMIUM", int(quote_ask), -int(rem_sell)))
        return orders

    def _trade_pepper_root(
        self,
        order_depth: OrderDepth,
        position: int,
    ) -> list[Order]:
        bids = {p: v for p, v in order_depth.buy_orders.items() if v > 0}
        asks = {p: v for p, v in order_depth.sell_orders.items() if v < 0}
        if not bids or not asks:
            return []

        wm = _wall_mid(order_depth)
        if wm is not None:
            self.last_pepper_mid = wm
        fv = wm if wm is not None else self.last_pepper_mid
        if fv is None:
            return []

        limit = POSITION_LIMITS["INTARIAN_PEPPER_ROOT"]
        best_bid = max(bids)
        best_ask = min(asks)
        buy_cap = max(0, limit - position)
        sell_cap = max(0, limit + position)
        orders: list[Order] = []
        taken_buy = 0

        for ask_price in sorted(asks):
            if ask_price <= fv - 1.5 and buy_cap - taken_buy > 0:
                qty = min(abs(asks[ask_price]), buy_cap - taken_buy)
                if qty > 0:
                    orders.append(Order("INTARIAN_PEPPER_ROOT", int(ask_price), int(qty)))
                    taken_buy += qty

        proj_pos = position + taken_buy
        rem_buy = buy_cap - taken_buy
        if rem_buy > 0:
            quote_bid = min(math.floor(fv - 1.0), best_bid + 1)
            if quote_bid >= best_ask:
                quote_bid = best_ask - 1
            if quote_bid > 0:
                orders.append(Order("INTARIAN_PEPPER_ROOT", int(quote_bid), int(rem_buy)))

        if proj_pos > 40 and sell_cap > 0:
            quote_ask = max(math.ceil(fv + 5.0), best_ask - 1)
            if quote_ask <= best_bid:
                quote_ask = best_bid + 1
            if quote_ask > 0:
                orders.append(
                    Order("INTARIAN_PEPPER_ROOT", int(quote_ask), -int(min(20, sell_cap))),
                )
        return orders

    def run(self, state: TradingState) -> tuple[dict[Symbol, list[Order]], int, str]:
        """Generate competition-compliant Round 1 orders."""
        persisted = _load_state(getattr(state, "traderData", ""))
        pepper_state = persisted.get("INTARIAN_PEPPER_ROOT")
        if (
            self.last_pepper_mid is None
            and isinstance(pepper_state, dict)
            and isinstance(pepper_state.get("last_mid"), (int, float))
        ):
            self.last_pepper_mid = float(pepper_state["last_mid"])

        result: dict[Symbol, list[Order]] = {}
        order_depths = getattr(state, "order_depths", {}) or {}
        positions = getattr(state, "position", {}) or {}

        if "ASH_COATED_OSMIUM" in order_depths:
            orders = self._trade_osmium(
                order_depths["ASH_COATED_OSMIUM"],
                int(positions.get("ASH_COATED_OSMIUM", 0)),
            )
            if orders:
                result["ASH_COATED_OSMIUM"] = orders

        if "INTARIAN_PEPPER_ROOT" in order_depths:
            orders = self._trade_pepper_root(
                order_depths["INTARIAN_PEPPER_ROOT"],
                int(positions.get("INTARIAN_PEPPER_ROOT", 0)),
            )
            if orders:
                result["INTARIAN_PEPPER_ROOT"] = orders

        next_data = json.dumps(
            {
                "ASH_COATED_OSMIUM": {"anchor": 10000.0},
                "INTARIAN_PEPPER_ROOT": {"last_mid": self.last_pepper_mid},
            },
        )
        return result, 0, next_data
