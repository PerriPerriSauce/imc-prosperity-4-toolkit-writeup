"""Mean-reversion and drift-aware quoting strategy implementations."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from prosperity_toolkit.core.models import OrderRequest, Symbol
from prosperity_toolkit.market.market_state import MarketStateSnapshot
from prosperity_toolkit.strategies.base import BaseStrategy


@dataclass(frozen=True, slots=True)
class OUMeanReversionConfig:
    """Configuration for Ornstein-Uhlenbeck fair-value mean reversion."""

    symbol: Symbol
    mu: float = 10000.0
    sigma: float = 4.5
    entry_z: float = 1.5
    position_limit: int = 20
    order_size: int = 5


class OUMeanReversionStrategy(BaseStrategy):
    """Mean-reversion strategy trading deviations from stationary OU equilibrium."""

    def __init__(
        self,
        configs: Sequence[OUMeanReversionConfig],
        name: str = "OUMeanReversion",
    ) -> None:
        super().__init__(name=name)
        self.configs = {cfg.symbol: cfg for cfg in configs}

    def generate_orders(self, state: MarketStateSnapshot) -> list[OrderRequest]:
        """Take liquidity when best bid/ask deviates significantly from OU equilibrium."""
        orders: list[OrderRequest] = []
        for sym, cfg in self.configs.items():
            book = state.get_book(sym)
            if book is None:
                continue

            pos = state.get_position(sym)
            buy_cap = max(0, cfg.position_limit - pos)
            sell_cap = max(0, cfg.position_limit + pos)
            threshold = cfg.entry_z * cfg.sigma

            if book.best_ask is not None and book.best_ask <= cfg.mu - threshold and buy_cap > 0:
                avail = abs(book.asks.get(book.best_ask, 0))
                qty = min(cfg.order_size, avail, buy_cap)
                if qty > 0:
                    orders.append(OrderRequest(symbol=sym, price=book.best_ask, quantity=qty))
            elif book.best_bid is not None and book.best_bid >= cfg.mu + threshold and sell_cap > 0:
                avail = abs(book.bids.get(book.best_bid, 0))
                qty = min(cfg.order_size, avail, sell_cap)
                if qty > 0:
                    orders.append(OrderRequest(symbol=sym, price=book.best_bid, quantity=-qty))

        return orders


@dataclass(frozen=True, slots=True)
class DriftAwareConfig:
    """Configuration for an alpha-beta (drift-compensated) fair-value quoter."""

    symbol: Symbol
    position_limit: int = 20
    alpha: float = 0.25
    beta: float = 0.01
    half_spread: float = 2.0
    quote_size: int = 5
    take_edge: float = 1.0
    inventory_skew: float = 0.25


class DriftAwareQuoter(BaseStrategy):
    """Alpha-beta fair-value tracker and market maker for drifting instruments."""

    def __init__(
        self,
        configs: Sequence[DriftAwareConfig],
        name: str = "DriftAwareQuoter",
    ) -> None:
        super().__init__(name=name)
        self.configs = {cfg.symbol: cfg for cfg in configs}
        self._fv: dict[Symbol, float] = {}
        self._drift_per_tick: dict[Symbol, float] = {}
        self._last_ts: dict[Symbol, int] = {}

    def _update_alpha_beta(
        self,
        sym: Symbol,
        cfg: DriftAwareConfig,
        state: MarketStateSnapshot,
    ) -> float | None:
        book = state.get_book(sym)
        if book is None:
            return self._fv.get(sym)

        dt_steps = 1.0
        if sym in self._last_ts and state.timestamp > self._last_ts[sym]:
            dt_steps = max(1.0, (state.timestamp - self._last_ts[sym]) / 100.0)

        if book.best_bid is not None and book.best_ask is not None:
            obs = book.weighted_mid_price or ((book.best_bid + book.best_ask) / 2.0)
            if sym not in self._fv:
                self._fv[sym] = obs
                self._drift_per_tick[sym] = 0.0
            else:
                pred = self._fv[sym] + self._drift_per_tick[sym] * dt_steps
                innov = obs - pred
                self._fv[sym] = pred + cfg.alpha * innov
                self._drift_per_tick[sym] += cfg.beta * (innov / dt_steps)
            self._last_ts[sym] = state.timestamp
            return self._fv[sym]

        if sym in self._fv:
            # Propagate forward with estimated drift during one-sided/empty ticks
            pred = self._fv[sym] + self._drift_per_tick[sym] * dt_steps
            self._fv[sym] = pred
            self._last_ts[sym] = state.timestamp
            return pred

        return None

    def generate_orders(self, state: MarketStateSnapshot) -> list[OrderRequest]:
        """Take mispriced liquidity and post drift-adjusted inventory-skewed quotes."""
        orders: list[OrderRequest] = []
        for sym, cfg in self.configs.items():
            book = state.get_book(sym)
            if book is None:
                continue
            fv = self._update_alpha_beta(sym, cfg, state)
            if fv is None:
                continue

            start_pos = state.get_position(sym)
            buy_cap = max(0, cfg.position_limit - start_pos)
            sell_cap = max(0, cfg.position_limit + start_pos)
            taken_buy = 0
            taken_sell = 0

            for ask_px in sorted(book.asks.keys()):
                if ask_px > fv - cfg.take_edge or buy_cap - taken_buy <= 0:
                    break
                avail = abs(book.asks[ask_px])
                qty = min(avail, buy_cap - taken_buy)
                if qty > 0:
                    orders.append(OrderRequest(symbol=sym, price=ask_px, quantity=qty))
                    taken_buy += qty

            for bid_px in sorted(book.bids.keys(), reverse=True):
                if bid_px < fv + cfg.take_edge or sell_cap - taken_sell <= 0:
                    break
                avail = abs(book.bids[bid_px])
                qty = min(avail, sell_cap - taken_sell)
                if qty > 0:
                    orders.append(OrderRequest(symbol=sym, price=bid_px, quantity=-qty))
                    taken_sell += qty

            rem_buy = max(0, buy_cap - taken_buy)
            rem_sell = max(0, sell_cap - taken_sell)
            reservation = fv - cfg.inventory_skew * start_pos

            quote_bid = math.floor(reservation - cfg.half_spread)
            quote_ask = math.ceil(reservation + cfg.half_spread)

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
