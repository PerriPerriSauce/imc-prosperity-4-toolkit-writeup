"""Cross-asset basket, constant-sum identity, and cointegrated pair strategies."""

from __future__ import annotations

import math
from dataclasses import dataclass

from prosperity_toolkit.core.models import OrderRequest, Symbol
from prosperity_toolkit.market.market_state import MarketStateSnapshot
from prosperity_toolkit.strategies.base import BaseStrategy


class BasketStrategyContract(BaseStrategy):
    """Protocol contract for multi-leg ETF and basket arbitrage strategies."""


@dataclass(frozen=True, slots=True)
class ConstantSumBasketConfig:
    """Configuration for constant-sum 5-leg basket arbitrage and quoting."""

    symbols: tuple[Symbol, ...] = (
        "PEBBLES_XS",
        "PEBBLES_S",
        "PEBBLES_M",
        "PEBBLES_L",
        "PEBBLES_XL",
    )
    target_sum: float = 50000.0
    position_limit: int = 10
    trigger_threshold: float = 6.0
    quote_edge: float = 2.0
    max_clip: int = 4


class ConstantSumBasketArbStrategy(BasketStrategyContract):
    """Trades cross-leg dislocations around an exact structural sum constraint."""

    def __init__(
        self,
        config: ConstantSumBasketConfig | None = None,
        name: str = "ConstantSumBasketArb",
    ) -> None:
        super().__init__(name=name)
        self.config = config or ConstantSumBasketConfig()

    def generate_orders(self, state: MarketStateSnapshot) -> list[OrderRequest]:
        """Compute synthetic sum residual and trade legs within strict position limits."""
        orders: list[OrderRequest] = []
        mids: dict[Symbol, float] = {}
        best_bids: dict[Symbol, int] = {}
        best_asks: dict[Symbol, int] = {}

        for sym in self.config.symbols:
            book = state.get_book(sym)
            if book is None or book.best_bid is None or book.best_ask is None:
                return []
            best_bids[sym] = book.best_bid
            best_asks[sym] = book.best_ask
            mids[sym] = (book.best_bid + book.best_ask) / 2.0

        sum_mids = sum(mids.values())
        residual = sum_mids - self.config.target_sum
        if abs(residual) < self.config.trigger_threshold:
            return []

        n_legs = len(self.config.symbols)
        # Positive residual => basket sum is rich => sell across legs proportional to residual
        per_leg_fair_adj = residual / float(n_legs)

        for sym in self.config.symbols:
            pos = state.get_position(sym)
            fair_leg = mids[sym] - per_leg_fair_adj
            if residual > 0.0:
                sell_cap = max(0, self.config.position_limit + pos)
                if sell_cap <= 0:
                    continue
                if best_bids[sym] >= fair_leg + self.config.quote_edge:
                    book = state.get_book(sym)
                    avail = abs(book.bids[best_bids[sym]]) if book is not None else 0
                    qty = min(self.config.max_clip, sell_cap, avail)
                    if qty > 0:
                        orders.append(OrderRequest(symbol=sym, price=best_bids[sym], quantity=-qty))
            else:
                buy_cap = max(0, self.config.position_limit - pos)
                if buy_cap <= 0:
                    continue
                if best_asks[sym] <= fair_leg - self.config.quote_edge:
                    book = state.get_book(sym)
                    avail = abs(book.asks[best_asks[sym]]) if book is not None else 0
                    qty = min(self.config.max_clip, buy_cap, avail)
                    if qty > 0:
                        orders.append(OrderRequest(symbol=sym, price=best_asks[sym], quantity=qty))

        return orders


@dataclass(frozen=True, slots=True)
class PairSumConfig:
    """Configuration for rolling-equilibrium negatively correlated pair trading."""

    leg_a: Symbol = "SNACKPACK_CHOCOLATE"
    leg_b: Symbol = "SNACKPACK_VANILLA"
    position_limit: int = 10
    ema_alpha: float = 0.005
    entry_threshold: float = 15.0
    half_spread: float = 7.0
    inventory_skew: float = 0.6
    max_clip: int = 3


class PairSumMeanReversionStrategy(BasketStrategyContract):
    """Adaptive pair-sum mean-reversion + wide-spread MM for correlated pairs."""

    def __init__(
        self,
        config: PairSumConfig | None = None,
        name: str = "PairSumMeanReversion",
    ) -> None:
        super().__init__(name=name)
        self.config = config or PairSumConfig()
        self._sum_ema: float | None = None

    def generate_orders(self, state: MarketStateSnapshot) -> list[OrderRequest]:
        """Track adaptive pair-sum equilibrium K_day and emit residual-skewed quotes."""
        book_a = state.get_book(self.config.leg_a)
        book_b = state.get_book(self.config.leg_b)
        if (
            book_a is None
            or book_b is None
            or book_a.best_bid is None
            or book_a.best_ask is None
            or book_b.best_bid is None
            or book_b.best_ask is None
        ):
            return []

        mid_a = (book_a.best_bid + book_a.best_ask) / 2.0
        mid_b = (book_b.best_bid + book_b.best_ask) / 2.0
        pair_sum = mid_a + mid_b

        if self._sum_ema is None:
            self._sum_ema = pair_sum
        else:
            self._sum_ema = (
                self.config.ema_alpha * pair_sum + (1.0 - self.config.ema_alpha) * self._sum_ema
            )

        residual = pair_sum - self._sum_ema
        coeff = -0.35 if abs(residual) >= self.config.entry_threshold else -0.15
        fv_shift = coeff * residual

        orders: list[OrderRequest] = []
        for sym, book, mid in (
            (self.config.leg_a, book_a, mid_a),
            (self.config.leg_b, book_b, mid_b),
        ):
            pos = state.get_position(sym)
            buy_cap = max(0, self.config.position_limit - pos)
            sell_cap = max(0, self.config.position_limit + pos)
            if book.best_bid is None or book.best_ask is None:
                continue

            fv = mid + fv_shift
            reservation = fv - self.config.inventory_skew * pos
            quote_bid = min(math.floor(reservation - self.config.half_spread), book.best_bid + 1)
            quote_ask = max(math.ceil(reservation + self.config.half_spread), book.best_ask - 1)
            if quote_bid >= book.best_ask:
                quote_bid = book.best_ask - 1
            if quote_ask <= book.best_bid:
                quote_ask = book.best_bid + 1
            if quote_bid >= quote_ask or quote_bid <= 0:
                continue

            if buy_cap > 0:
                orders.append(
                    OrderRequest(
                        symbol=sym,
                        price=quote_bid,
                        quantity=min(self.config.max_clip, buy_cap),
                    ),
                )
            if sell_cap > 0:
                orders.append(
                    OrderRequest(
                        symbol=sym,
                        price=quote_ask,
                        quantity=-min(self.config.max_clip, sell_cap),
                    ),
                )

        return orders
