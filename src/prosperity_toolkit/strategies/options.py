"""Volatility-surface option valuation and delta-neutral hedging strategies."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Literal

from prosperity_toolkit.analysis.options import (
    bachelier_call,
    bachelier_call_delta,
    black_scholes_call,
    black_scholes_call_delta,
    implied_volatility_bs,
)
from prosperity_toolkit.core.models import OrderRequest, Symbol
from prosperity_toolkit.market.market_state import MarketStateSnapshot
from prosperity_toolkit.strategies.base import BaseStrategy


class OptionsStrategyContract(BaseStrategy):
    """Protocol contract for options pricing, implied vol, and delta-neutral strategies."""


@dataclass(frozen=True, slots=True)
class OptionStrikeSpec:
    """Per-strike trading configuration for Prosperity option vouchers."""

    symbol: Symbol
    strike: float
    position_limit: int = 300
    take_edge: float = 1.5
    quote_half_spread: float = 1.5
    quote_size: int = 12


@dataclass(frozen=True, slots=True)
class OptionsVolatilityConfig:
    """Configuration for volatility-smile valuation and spot delta hedging."""

    spot_symbol: Symbol = "VELVETFRUIT_EXTRACT"
    spot_limit: int = 200
    day_index: int = 0
    total_days: float = 5.0
    steps_per_day: float = 10000.0
    base_vol: float = 0.238
    tte_scale_days: float = 250.0
    pricing_model: Literal["bs", "bachelier"] = "bs"
    hedge_band: float = 8.0
    spot_take_edge: float = 1.5
    spot_half_spread: float = 1.5
    spot_skew: float = 0.04
    iv_ema_alpha: float = 0.05
    strikes: tuple[OptionStrikeSpec, ...] = field(
        default_factory=lambda: (
            OptionStrikeSpec("VEV_5100", 5100.0),
            OptionStrikeSpec("VEV_5200", 5200.0),
            OptionStrikeSpec("VEV_5300", 5300.0),
            OptionStrikeSpec("VEV_5400", 5400.0),
            OptionStrikeSpec("VEV_5500", 5500.0),
        ),
    )


class OptionsVolatilityStrategy(OptionsStrategyContract):
    """Priced-by-smile options taker/quoter with capped spot delta hedging."""

    def __init__(
        self,
        config: OptionsVolatilityConfig | None = None,
        name: str = "OptionsVolatility",
    ) -> None:
        super().__init__(name=name)
        self.config = config or OptionsVolatilityConfig()
        self._spot_ema: float | None = None
        self._atm_vol: float = self.config.base_vol

    def _time_to_expiry(self, timestamp: int) -> float:
        elapsed_day_frac = max(0.0, float(timestamp) / (100.0 * self.config.steps_per_day))
        days_left = max(0.01, self.config.total_days - self.config.day_index - elapsed_day_frac)
        return days_left / self.config.tte_scale_days

    def _theo_and_delta(
        self,
        spot: float,
        strike: float,
        tte: float,
    ) -> tuple[float, float]:
        if self.config.pricing_model == "bachelier":
            steps_left = max(1.0, tte * self.config.tte_scale_days * self.config.steps_per_day)
            # Convert annualized lognormal vol estimate to per-step arithmetic tick sigma
            sigma_per_step = (
                self._atm_vol
                * spot
                / math.sqrt(self.config.tte_scale_days * self.config.steps_per_day)
            )
            fair = bachelier_call(spot, strike, steps_left, sigma_per_step)
            delta = bachelier_call_delta(spot, strike, steps_left, sigma_per_step)
            return fair, delta
        fair = black_scholes_call(spot, strike, tte, self._atm_vol)
        delta = black_scholes_call_delta(spot, strike, tte, self._atm_vol)
        return fair, delta

    def generate_orders(self, state: MarketStateSnapshot) -> list[OrderRequest]:
        """Compute option fair values vs BS/Bachelier, trade edge, and hedge net delta."""
        spot_book = state.get_book(self.config.spot_symbol)
        if spot_book is None:
            return []

        if spot_book.best_bid is not None and spot_book.best_ask is not None:
            wmid = spot_book.weighted_mid_price
            obs_spot = wmid if wmid is not None else (
                (spot_book.best_bid + spot_book.best_ask) / 2.0
            )
            self._spot_ema = (
                obs_spot
                if self._spot_ema is None
                else 0.25 * obs_spot + 0.75 * self._spot_ema
            )
        if self._spot_ema is None:
            return []

        spot_fv = self._spot_ema
        tte = self._time_to_expiry(state.timestamp)
        orders: list[OrderRequest] = []
        net_option_delta = 0.0

        # Online ATM vol smoothing from nearest active strike in BS mode
        if self.config.pricing_model == "bs":
            nearest_specs = sorted(
                self.config.strikes,
                key=lambda s: abs(s.strike - spot_fv),
            )
            for spec in nearest_specs:
                if abs(spec.strike - spot_fv) > 150.0:
                    break
                ob = state.get_book(spec.symbol)
                if ob is not None and ob.best_bid is not None and ob.best_ask is not None:
                    mid_opt = (ob.best_bid + ob.best_ask) / 2.0
                    iv = implied_volatility_bs(mid_opt, spot_fv, spec.strike, tte)
                    if iv is not None and 0.05 <= iv <= 1.0:
                        a = self.config.iv_ema_alpha
                        self._atm_vol = a * iv + (1.0 - a) * self._atm_vol
                    break

        for spec in self.config.strikes:
            ob = state.get_book(spec.symbol)
            if ob is None:
                continue
            fair, delta = self._theo_and_delta(spot_fv, spec.strike, tte)
            pos = state.get_position(spec.symbol)
            net_option_delta += pos * delta

            buy_cap = max(0, spec.position_limit - pos)
            sell_cap = max(0, spec.position_limit + pos)
            taken_buy = 0
            taken_sell = 0

            for ask_px in sorted(ob.asks.keys()):
                if ask_px > fair - spec.take_edge or buy_cap - taken_buy <= 0:
                    break
                qty = min(abs(ob.asks[ask_px]), buy_cap - taken_buy)
                if qty > 0:
                    orders.append(OrderRequest(symbol=spec.symbol, price=ask_px, quantity=qty))
                    taken_buy += qty

            for bid_px in sorted(ob.bids.keys(), reverse=True):
                if bid_px < fair + spec.take_edge or sell_cap - taken_sell <= 0:
                    break
                qty = min(abs(ob.bids[bid_px]), sell_cap - taken_sell)
                if qty > 0:
                    orders.append(OrderRequest(symbol=spec.symbol, price=bid_px, quantity=-qty))
                    taken_sell += qty

            rem_buy = max(0, buy_cap - taken_buy)
            rem_sell = max(0, sell_cap - taken_sell)
            q_bid = math.floor(fair - spec.quote_half_spread)
            q_ask = math.ceil(fair + spec.quote_half_spread)
            if ob.best_ask is not None and q_bid >= ob.best_ask:
                q_bid = ob.best_ask - 1
            if ob.best_bid is not None and q_ask <= ob.best_bid:
                q_ask = ob.best_bid + 1
            if q_bid < q_ask and q_bid > 0:
                if rem_buy > 0:
                    orders.append(
                        OrderRequest(
                            symbol=spec.symbol,
                            price=q_bid,
                            quantity=min(spec.quote_size, rem_buy),
                        ),
                    )
                if rem_sell > 0:
                    orders.append(
                        OrderRequest(
                            symbol=spec.symbol,
                            price=q_ask,
                            quantity=-min(spec.quote_size, rem_sell),
                        ),
                    )

        # Spot delta hedge + reservation market-making on spot
        spot_pos = state.get_position(self.config.spot_symbol)
        spot_buy_cap = max(0, self.config.spot_limit - spot_pos)
        spot_sell_cap = max(0, self.config.spot_limit + spot_pos)
        total_delta = float(spot_pos) + net_option_delta
        hedged_buy = 0
        hedged_sell = 0

        if total_delta < -self.config.hedge_band and spot_book.best_ask is not None:
            desired_buy = math.floor(-total_delta)
            qty = min(
                desired_buy,
                abs(spot_book.asks[spot_book.best_ask]),
                spot_buy_cap,
            )
            if qty > 0 and spot_book.best_ask <= spot_fv + self.config.spot_take_edge:
                orders.append(
                    OrderRequest(
                        symbol=self.config.spot_symbol,
                        price=spot_book.best_ask,
                        quantity=qty,
                    ),
                )
                hedged_buy = qty
        elif total_delta > self.config.hedge_band and spot_book.best_bid is not None:
            desired_sell = math.floor(total_delta)
            qty = min(
                desired_sell,
                abs(spot_book.bids[spot_book.best_bid]),
                spot_sell_cap,
            )
            if qty > 0 and spot_book.best_bid >= spot_fv - self.config.spot_take_edge:
                orders.append(
                    OrderRequest(
                        symbol=self.config.spot_symbol,
                        price=spot_book.best_bid,
                        quantity=-qty,
                    ),
                )
                hedged_sell = qty

        rem_s_buy = max(0, spot_buy_cap - hedged_buy)
        rem_s_sell = max(0, spot_sell_cap - hedged_sell)
        res = spot_fv - self.config.spot_skew * total_delta
        s_bid = math.floor(res - self.config.spot_half_spread)
        s_ask = math.ceil(res + self.config.spot_half_spread)
        if spot_book.best_ask is not None and s_bid >= spot_book.best_ask:
            s_bid = spot_book.best_ask - 1
        if spot_book.best_bid is not None and s_ask <= spot_book.best_bid:
            s_ask = spot_book.best_bid + 1
        if s_bid < s_ask and s_bid > 0:
            if rem_s_buy > 0:
                orders.append(
                    OrderRequest(
                        symbol=self.config.spot_symbol,
                        price=s_bid,
                        quantity=min(15, rem_s_buy),
                    ),
                )
            if rem_s_sell > 0:
                orders.append(
                    OrderRequest(
                        symbol=self.config.spot_symbol,
                        price=s_ask,
                        quantity=-min(15, rem_s_sell),
                    ),
                )

        return orders
