"""Market making baseline and inventory-skewed strategies."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from prosperity_toolkit.core.models import OrderRequest, Symbol
from prosperity_toolkit.market.market_state import MarketStateSnapshot
from prosperity_toolkit.strategies.base import BaseStrategy


@dataclass(frozen=True, slots=True)
class MarketMakingConfig:
    """Explicit configuration for market making strategies.

    Note: Round 0/1 position limits are configurable assumptions (default 20)
    until confirmed against official competition portal rules.
    """

    symbol: Symbol
    position_limit: int = 20
    half_spread: float = 2.0
    quote_size: int = 5
    take_edge: float = 1.0
    inventory_skew: float = 0.25
    ema_alpha: float = 0.25
    anchor_fv: float | None = None
    anchor_weight: float = 0.0


class SymmetricMarketMaker(BaseStrategy):
    """Simple symmetric passive market-making baseline without taking or skew."""

    def __init__(self, configs: Sequence[MarketMakingConfig], name: str = "SymmetricMM") -> None:
        super().__init__(name=name)
        self.configs = {cfg.symbol: cfg for cfg in configs}
        self._last_mid: dict[Symbol, float] = {}

    def generate_orders(self, state: MarketStateSnapshot) -> list[OrderRequest]:
        """Emit symmetric bid/ask quotes around two-sided mid-price."""
        orders: list[OrderRequest] = []
        for sym, cfg in self.configs.items():
            book = state.get_book(sym)
            if book is None:
                continue

            if book.best_bid is not None and book.best_ask is not None:
                mid = (book.best_bid + book.best_ask) / 2.0
                self._last_mid[sym] = mid
            elif sym in self._last_mid:
                mid = self._last_mid[sym]
            elif cfg.anchor_fv is not None:
                mid = cfg.anchor_fv
            else:
                continue

            pos = state.get_position(sym)
            buy_cap = max(0, cfg.position_limit - pos)
            sell_cap = max(0, cfg.position_limit + pos)

            bid_px = math.floor(mid - cfg.half_spread)
            ask_px = math.ceil(mid + cfg.half_spread)
            if book.best_ask is not None and bid_px >= book.best_ask:
                bid_px = book.best_ask - 1
            if book.best_bid is not None and ask_px <= book.best_bid:
                ask_px = book.best_bid + 1
            if bid_px >= ask_px or bid_px <= 0:
                continue

            if buy_cap > 0:
                qty = min(cfg.quote_size, buy_cap)
                orders.append(OrderRequest(symbol=sym, price=bid_px, quantity=qty))
            if sell_cap > 0:
                qty = min(cfg.quote_size, sell_cap)
                orders.append(OrderRequest(symbol=sym, price=ask_px, quantity=-qty))

        return orders


class InventorySkewedMarketMaker(BaseStrategy):
    """Candidate market maker combining two-sided FV tracking, taking, and inventory skew."""

    def __init__(
        self,
        configs: Sequence[MarketMakingConfig],
        name: str = "InventorySkewedMM",
    ) -> None:
        super().__init__(name=name)
        self.configs = {cfg.symbol: cfg for cfg in configs}
        self._ema_fv: dict[Symbol, float] = {}

    def _update_fair_value(
        self,
        sym: Symbol,
        cfg: MarketMakingConfig,
        state: MarketStateSnapshot,
    ) -> float | None:
        book = state.get_book(sym)
        if book is not None and book.best_bid is not None and book.best_ask is not None:
            wmid = book.weighted_mid_price
            obs = wmid if wmid is not None else ((book.best_bid + book.best_ask) / 2.0)
            prev = self._ema_fv.get(sym, obs)
            ema = cfg.ema_alpha * obs + (1.0 - cfg.ema_alpha) * prev
            self._ema_fv[sym] = ema
        elif sym in self._ema_fv:
            ema = self._ema_fv[sym]
        elif cfg.anchor_fv is not None:
            return cfg.anchor_fv
        else:
            return None

        if cfg.anchor_fv is not None and cfg.anchor_weight > 0.0:
            return float(cfg.anchor_weight * cfg.anchor_fv + (1.0 - cfg.anchor_weight) * ema)
        return float(ema)

    def generate_orders(self, state: MarketStateSnapshot) -> list[OrderRequest]:
        """Take mispriced liquidity and post inventory-skewed passive quotes."""
        orders: list[OrderRequest] = []
        for sym, cfg in self.configs.items():
            book = state.get_book(sym)
            if book is None:
                continue
            fv = self._update_fair_value(sym, cfg, state)
            if fv is None:
                continue

            start_pos = state.get_position(sym)
            buy_cap = max(0, cfg.position_limit - start_pos)
            sell_cap = max(0, cfg.position_limit + start_pos)
            taken_buy = 0
            taken_sell = 0

            # 1. Taker leg against mispriced resting levels
            for ask_px in sorted(book.asks.keys()):
                if ask_px > fv - cfg.take_edge or buy_cap - taken_buy <= 0:
                    break
                avail = abs(book.asks[ask_px])
                take_qty = min(avail, buy_cap - taken_buy)
                if take_qty > 0:
                    orders.append(OrderRequest(symbol=sym, price=ask_px, quantity=take_qty))
                    taken_buy += take_qty

            for bid_px in sorted(book.bids.keys(), reverse=True):
                if bid_px < fv + cfg.take_edge or sell_cap - taken_sell <= 0:
                    break
                avail = abs(book.bids[bid_px])
                take_qty = min(avail, sell_cap - taken_sell)
                if take_qty > 0:
                    orders.append(OrderRequest(symbol=sym, price=bid_px, quantity=-take_qty))
                    taken_sell += take_qty

            # 2. Passive maker leg with Avellaneda-Stoikov style reservation skew
            rem_buy = max(0, buy_cap - taken_buy)
            rem_sell = max(0, sell_cap - taken_sell)
            reservation = fv - cfg.inventory_skew * start_pos

            quote_bid = math.floor(reservation - cfg.half_spread)
            quote_ask = math.ceil(reservation + cfg.half_spread)

            # Avoid penny-crossing prevailing book opposite side
            if book.best_ask is not None and quote_bid >= book.best_ask:
                quote_bid = book.best_ask - 1
            if book.best_bid is not None and quote_ask <= book.best_bid:
                quote_ask = book.best_bid + 1

            if quote_bid >= quote_ask or quote_bid <= 0:
                continue

            if rem_buy > 0:
                orders.append(
                    OrderRequest(
                        symbol=sym,
                        price=quote_bid,
                        quantity=min(cfg.quote_size, rem_buy),
                    ),
                )
            if rem_sell > 0:
                orders.append(
                    OrderRequest(
                        symbol=sym,
                        price=quote_ask,
                        quantity=-min(cfg.quote_size, rem_sell),
                    ),
                )

        return orders
