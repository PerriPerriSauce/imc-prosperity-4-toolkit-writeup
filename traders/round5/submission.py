"""Standalone Prosperity 4 Round 5 competition submission trader.

Economic rationale:
- Official Round 5 position limit is +/-10 across all 50 products spanned over
  10 commodity/product categories.
- Core engine: volatility-scaled Avellaneda-Stoikov market making across every
  active book (`sigma` via EMA of absolute wall-mid moves, `skew = max(0.8,
  vol_skew_mult * sigma)`, `edge = max(1.5, edge_frac * spread, 0.20 * sigma)`),
  using projected post-taker inventory before posting penny-improved maker
  quotes inside the spread.
- Microchip lead-lag overlay: Strictly in-sample Days 2-3 EDA uncovered exact
  discrete causal delays from ``MICROCHIP_CIRCLE`` at 50/100/150/200 ticks to
  ``OVAL``/``SQUARE``/``RECTANGLE``/``TRIANGLE`` respectively (lag-1 and +/-1
  lags ~0). Tilting fair value on large ``CIRCLE`` jumps (`|dx| >= 15`) with
  ``mc_beta=0.16`` improves IS both PnL and risk-adjusted IR while lowering
  drawdown.
- Negative results explicitly omitted: zero-fill inside-spread ``Pebbles``
  crossing, hard ``VOL_GUARD`` quoting halts, ``Robots`` cross-signals, and
  contemporaneous ``Snackpack`` correlation.
"""

from __future__ import annotations

import json
import math
from collections import deque
from typing import Any

from datamodel import Order, OrderDepth, Symbol, TradingState

POSITION_LIMIT: int = 10

MICROCHIP_LAGS: dict[str, int] = {
    "MICROCHIP_OVAL": 50,
    "MICROCHIP_SQUARE": 100,
    "MICROCHIP_RECTANGLE": 150,
    "MICROCHIP_TRIANGLE": 200,
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
    """Prosperity 4 Round 5 Trader calibrated strictly on Days 2 and 3."""

    def __init__(
        self,
        vol_skew_mult: float = 0.18,
        edge_frac: float = 0.14,
        mc_beta: float = 0.16,
    ) -> None:
        self.vol_skew_mult = float(vol_skew_mult)
        self.edge_frac = float(edge_frac)
        self.mc_beta = float(mc_beta)
        self.last_m: dict[str, float] = {}
        self.vol_ema: dict[str, float] = {}
        self.prev_circ: float | None = None
        self.circ_dx: deque[float] = deque(maxlen=205)

    def _hydrate_state(self, raw: str) -> None:
        persisted = _load_state(raw)
        raw_lm = persisted.get("last_m")
        if isinstance(raw_lm, dict):
            for sym, val in raw_lm.items():
                if isinstance(sym, str) and isinstance(val, (int, float)):
                    self.last_m[sym] = float(val)
        raw_vol = persisted.get("vol_ema")
        if isinstance(raw_vol, dict):
            for sym, val in raw_vol.items():
                if isinstance(sym, str) and isinstance(val, (int, float)):
                    self.vol_ema[sym] = float(val)
        prev_c = persisted.get("prev_circ")
        if isinstance(prev_c, (int, float)):
            self.prev_circ = float(prev_c)
        raw_cdx = persisted.get("circ_dx")
        if isinstance(raw_cdx, list):
            for val in raw_cdx[-205:]:
                if isinstance(val, (int, float)):
                    self.circ_dx.append(float(val))

    def run(self, state: TradingState) -> tuple[dict[Symbol, list[Order]], int, str]:
        """Generate competition-compliant Round 5 orders across all 50 books."""
        if not self.last_m and not self.circ_dx:
            self._hydrate_state(getattr(state, "traderData", ""))

        order_depths = getattr(state, "order_depths", {}) or {}
        positions = getattr(state, "position", {}) or {}
        result: dict[Symbol, list[Order]] = {}

        if self.mc_beta != 0.0 and "MICROCHIP_CIRCLE" in order_depths:
            cwm = _wall_mid(order_depths["MICROCHIP_CIRCLE"])
            if cwm is not None:
                dx_c = (cwm - self.prev_circ) if self.prev_circ is not None else 0.0
                self.circ_dx.append(dx_c)
                self.prev_circ = cwm

        for sym, ob in order_depths.items():
            bids: dict[int, int] = {int(p): int(v) for p, v in ob.buy_orders.items() if v > 0}
            asks: dict[int, int] = {int(p): int(v) for p, v in ob.sell_orders.items() if v < 0}
            if not bids or not asks:
                continue

            fv = _wall_mid(ob)
            if fv is None:
                continue

            if sym in self.last_m:
                dx = abs(fv - self.last_m[sym])
                self.vol_ema[sym] = 0.05 * dx + 0.95 * self.vol_ema.get(sym, dx)
            self.last_m[sym] = fv
            sig = self.vol_ema.get(sym, 8.0)

            lag = MICROCHIP_LAGS.get(sym)
            if self.mc_beta != 0.0 and lag is not None and len(self.circ_dx) >= lag:
                pred = self.circ_dx[-lag]
                if abs(pred) >= 15.0:
                    fv += self.mc_beta * pred

            pos = int(positions.get(sym, 0))
            buy_cap = max(0, POSITION_LIMIT - pos)
            sell_cap = max(0, POSITION_LIMIT + pos)
            sym_orders: list[Order] = []
            taken_buy = 0
            taken_sell = 0
            req_take = max(1.0, 0.10 * sig)

            for ap in sorted(asks):
                if ap <= fv - req_take and buy_cap - taken_buy > 0:
                    qty = min(abs(asks[ap]), buy_cap - taken_buy)
                    if qty > 0:
                        sym_orders.append(Order(sym, int(ap), int(qty)))
                        taken_buy += qty

            for bp in sorted(bids, reverse=True):
                if bp >= fv + req_take and sell_cap - taken_sell > 0:
                    qty = min(abs(bids[bp]), sell_cap - taken_sell)
                    if qty > 0:
                        sym_orders.append(Order(sym, int(bp), -int(qty)))
                        taken_sell += qty

            proj = pos + taken_buy - taken_sell
            bb = max(bids)
            ba = min(asks)
            sp = max(0, ba - bb)
            sk = max(0.8, self.vol_skew_mult * sig)
            edge = max(1.5, self.edge_frac * sp, 0.20 * sig)
            res = fv - sk * proj

            qb = min(math.floor(res - edge), bb + 1)
            qa = max(math.ceil(res + edge), ba - 1)
            if qb >= ba:
                qb = ba - 1
            if qa <= bb:
                qa = bb + 1

            if qb < qa and qb > 0:
                rem_buy = buy_cap - taken_buy
                rem_sell = sell_cap - taken_sell
                if rem_buy > 0:
                    sym_orders.append(Order(sym, int(qb), int(rem_buy)))
                if rem_sell > 0:
                    sym_orders.append(Order(sym, int(qa), -int(rem_sell)))
            if sym_orders:
                result[sym] = sym_orders

        next_data = json.dumps(
            {
                "last_m": {k: round(v, 2) for k, v in self.last_m.items()},
                "vol_ema": {k: round(v, 3) for k, v in self.vol_ema.items()},
                "prev_circ": round(self.prev_circ, 2) if self.prev_circ is not None else None,
                "circ_dx": [round(x, 2) for x in self.circ_dx],
            },
        )
        return result, 0, next_data
