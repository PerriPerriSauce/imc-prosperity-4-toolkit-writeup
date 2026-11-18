"""Joint correlated multi-asset and options+spot Monte Carlo scenario engines."""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass

import numpy as np

from prosperity_toolkit.analysis.options import bachelier_call, black_scholes_call
from prosperity_toolkit.backtesting.engine import BacktestEngine, BacktestResult
from prosperity_toolkit.core.models import Symbol
from prosperity_toolkit.execution.simulator import ExecutionSimulator, FillMode
from prosperity_toolkit.market.market_state import MarketStateSnapshot
from prosperity_toolkit.market.order_book import OrderBookL2
from prosperity_toolkit.market.order_flow import TradePrint
from prosperity_toolkit.simulation.processes import OrnsteinUhlenbeckParams, simulate_ou_paths
from prosperity_toolkit.simulation.pulses import TradeArrivalConfig
from prosperity_toolkit.simulation.scenario import (
    AssetScenarioConfig,
    MonteCarloEngine,
    MonteCarloSummary,
)
from prosperity_toolkit.simulation.synthetic_book import BotBookConfig, build_synthetic_book
from prosperity_toolkit.strategies.base import BaseStrategy


def _summarize_mc_results(
    results: list[BacktestResult],
    n_sessions: int,
    n_steps: int,
    seed: int,
) -> MonteCarloSummary:
    """Aggregate BacktestResult realizations into a standard MonteCarloSummary."""
    pnls = np.array([r.total_pnl for r in results], dtype=np.float64)
    sharpes = np.array([r.sharpe_ratio for r in results], dtype=np.float64)
    drawdowns = np.array([r.max_drawdown for r in results], dtype=np.float64)

    var_95 = float(np.percentile(pnls, 5.0))
    tail_mask = pnls <= var_95
    cvar_95 = float(np.mean(pnls[tail_mask])) if np.any(tail_mask) else var_95

    return MonteCarloSummary(
        strategy_name=results[0].strategy_name,
        n_sessions=n_sessions,
        n_steps=n_steps,
        seed=seed,
        pnl_distribution=tuple(float(x) for x in pnls),
        mean_pnl=float(np.mean(pnls)),
        std_pnl=float(np.std(pnls, ddof=1)) if n_sessions > 1 else 0.0,
        median_pnl=float(np.median(pnls)),
        var_95=var_95,
        cvar_95=cvar_95,
        prob_loss=float(np.mean(pnls < 0.0)),
        mean_sharpe=float(np.mean(sharpes)),
        mean_max_drawdown=float(np.mean(drawdowns)),
        worst_max_drawdown=float(np.max(drawdowns)),
    )


def simulate_arrival_sensitivity(
    strategy_factory: Callable[[], BaseStrategy],
    asset_configs: Sequence[AssetScenarioConfig],
    arrival_rates: Sequence[float],
    n_sessions: int = 30,
    n_steps: int = 1000,
    fill_mode: FillMode = "queue_aware",
    seed: int = 42,
) -> dict[float, MonteCarloSummary]:
    """Run Monte Carlo arrival-rate sensitivity sweeps (MAF valuation diagnostics)."""
    out: dict[float, MonteCarloSummary] = {}
    for idx, arrival_rate in enumerate(arrival_rates):
        scaled_cfgs = [
            AssetScenarioConfig(
                symbol=cfg.symbol,
                position_limit=cfg.position_limit,
                process=cfg.process,
                book=cfg.book,
                arrivals=TradeArrivalConfig(
                    arrival_prob=float(np.clip(arrival_rate, 0.0, 1.0)),
                    buy_prob=cfg.arrivals.buy_prob,
                    min_size=cfg.arrivals.min_size,
                    max_size=cfg.arrivals.max_size,
                ),
            )
            for cfg in asset_configs
        ]
        engine = MonteCarloEngine(
            assets=scaled_cfgs,
            conservative_fills=(fill_mode == "conservative"),
        )
        out[float(arrival_rate)] = engine.run(
            strategy_factory=strategy_factory,
            n_sessions=n_sessions,
            n_steps=n_steps,
            seed=seed + idx * 100,
        )
    return out


@dataclass(frozen=True, slots=True)
class CoupledOptionStrikeConfig:
    """Configuration for a coupled European call voucher in Monte Carlo."""

    symbol: Symbol
    strike: float
    position_limit: int = 300
    half_spread: float = 1.5
    wall_volume: int = 20
    vol: float = 0.24
    arrival_prob: float = 0.08
    seller_initiated_prob: float = 0.95
    mean_qty: int = 5


@dataclass(frozen=True, slots=True)
class OptionsSpotScenarioConfig:
    """Coupled spot + options smile Monte Carlo environment (Round 3-4 calibration)."""

    spot_symbol: Symbol = "VELVETFRUIT_EXTRACT"
    spot_limit: int = 200
    spot_params: OrnsteinUhlenbeckParams = OrnsteinUhlenbeckParams(
        mu=5250.0,
        theta=0.0034,
        sigma=1.13,
        initial_price=5250.0,
    )
    spot_spread: float = 2.5
    spot_arrival_prob: float = 0.09
    hydrogel_symbol: Symbol | None = "HYDROGEL_PACK"
    hydrogel_limit: int = 200
    hydrogel_params: OrnsteinUhlenbeckParams = OrnsteinUhlenbeckParams(
        mu=9992.0,
        theta=0.0037,
        sigma=2.17,
        initial_price=9992.0,
    )
    hydrogel_spread: float = 7.5
    option_strikes: tuple[CoupledOptionStrikeConfig, ...] = (
        CoupledOptionStrikeConfig("VEV_5200", 5200.0, half_spread=1.5, seller_initiated_prob=0.90),
        CoupledOptionStrikeConfig("VEV_5300", 5300.0, half_spread=1.0, seller_initiated_prob=0.98),
        CoupledOptionStrikeConfig("VEV_5400", 5400.0, half_spread=1.0, seller_initiated_prob=1.00),
        CoupledOptionStrikeConfig("VEV_5500", 5500.0, half_spread=0.6, seller_initiated_prob=1.00),
    )
    tte_start_days: float = 5.0
    steps_per_day: int = 10000
    pricing_model: str = "bs"
    pricing_scale: float = 250.0


class CoupledOptionsMonteCarloEngine:
    """Simulates coupled OU spot, hydrogel, and arbitrage-consistent option chains."""

    def __init__(
        self,
        config: OptionsSpotScenarioConfig,
        fill_mode: FillMode = "queue_aware",
    ) -> None:
        self.config = config
        self.fill_mode: FillMode = fill_mode
        limits: dict[str, int] = {
            config.spot_symbol: config.spot_limit,
            **{opt.symbol: opt.position_limit for opt in config.option_strikes},
        }
        if config.hydrogel_symbol is not None:
            limits[config.hydrogel_symbol] = config.hydrogel_limit
        self.position_limits = limits

    def _option_theo(self, spot: float, opt: CoupledOptionStrikeConfig, tte: float) -> float:
        if self.config.pricing_model == "bachelier":
            return float(bachelier_call(spot, opt.strike, tte * self.config.steps_per_day, opt.vol))
        return float(
            black_scholes_call(spot, opt.strike, tte / self.config.pricing_scale, opt.vol),
        )

    def run(
        self,
        strategy_factory: Callable[[], BaseStrategy],
        n_sessions: int = 30,
        n_steps: int = 1000,
        seed: int = 42,
    ) -> MonteCarloSummary:
        """Execute Monte Carlo simulation across coupled spot/option/hydrogel paths."""
        if n_sessions <= 0 or n_steps <= 0:
            msg = "n_sessions and n_steps must be positive"
            raise ValueError(msg)

        rng = np.random.default_rng(seed)
        spot_paths = simulate_ou_paths(self.config.spot_params, n_sessions, n_steps, rng)
        hydro_paths = (
            simulate_ou_paths(self.config.hydrogel_params, n_sessions, n_steps, rng)
            if self.config.hydrogel_symbol is not None
            else None
        )

        spot_book_cfg = BotBookConfig(
            half_spread_l1=self.config.spot_spread,
            depth_l1=18,
            step_l2=2,
            depth_l2=4,
        )
        hydro_book_cfg = BotBookConfig(
            half_spread_l1=self.config.hydrogel_spread,
            depth_l1=20,
            step_l2=3,
            depth_l2=4,
        )

        sim = ExecutionSimulator(position_limits=self.position_limits, fill_mode=self.fill_mode)
        engine = BacktestEngine(simulator=sim)
        results: list[BacktestResult] = []

        for s_idx in range(n_sessions):
            snapshots: list[MarketStateSnapshot] = []
            for t in range(n_steps):
                ts = t * 100
                spot_fv = float(spot_paths[s_idx, t])
                books: dict[str, OrderBookL2] = {
                    self.config.spot_symbol: build_synthetic_book(
                        self.config.spot_symbol,
                        spot_fv,
                        spot_book_cfg,
                    ),
                }
                trades: dict[str, list[TradePrint]] = {}

                if rng.random() < self.config.spot_arrival_prob:
                    side_px = (
                        books[self.config.spot_symbol].best_ask
                        if rng.random() < 0.5
                        else books[self.config.spot_symbol].best_bid
                    )
                    if side_px is not None:
                        qty = int(rng.integers(1, 10))
                        buyer = "BOT" if side_px == books[self.config.spot_symbol].best_ask else ""
                        seller = "" if buyer else "BOT"
                        trades[self.config.spot_symbol] = [
                            TradePrint(
                                timestamp=ts,
                                symbol=self.config.spot_symbol,
                                price=int(side_px),
                                quantity=qty,
                                buyer=buyer,
                                seller=seller,
                            ),
                        ]

                if self.config.hydrogel_symbol is not None and hydro_paths is not None:
                    h_fv = float(hydro_paths[s_idx, t])
                    h_book = build_synthetic_book(
                        self.config.hydrogel_symbol,
                        h_fv,
                        hydro_book_cfg,
                    )
                    books[self.config.hydrogel_symbol] = h_book
                    if rng.random() < 0.08:
                        px = h_book.best_ask if rng.random() < 0.5 else h_book.best_bid
                        if px is not None:
                            trades[self.config.hydrogel_symbol] = [
                                TradePrint(
                                    timestamp=ts,
                                    symbol=self.config.hydrogel_symbol,
                                    price=int(px),
                                    quantity=int(rng.integers(1, 8)),
                                    buyer="",
                                    seller="",
                                ),
                            ]

                tte = max(0.01, self.config.tte_start_days - (t / self.config.steps_per_day))
                for opt in self.config.option_strikes:
                    opt_fv = self._option_theo(spot_fv, opt, tte)
                    half = opt.half_spread
                    bid_px = max(0, math.floor(opt_fv - half))
                    ask_px = max(bid_px + 1, math.ceil(opt_fv + half))
                    bids = {bid_px: opt.wall_volume} if bid_px > 0 else {0: opt.wall_volume}
                    asks = {ask_px: -opt.wall_volume}
                    books[opt.symbol] = OrderBookL2(symbol=opt.symbol, bids=bids, asks=asks)

                    if rng.random() < opt.arrival_prob:
                        is_sell_init = rng.random() < opt.seller_initiated_prob
                        px = bid_px if is_sell_init else ask_px
                        qty = int(rng.integers(1, max(2, opt.mean_qty * 2)))
                        trades[opt.symbol] = [
                            TradePrint(
                                timestamp=ts,
                                symbol=opt.symbol,
                                price=int(px),
                                quantity=qty,
                                seller="Mark 22" if is_sell_init else "",
                                buyer="" if is_sell_init else "BOT",
                            ),
                        ]

                snapshots.append(
                    MarketStateSnapshot(timestamp=ts, books=books, market_trades=trades),
                )

            results.append(engine.run(strategy_factory(), snapshots))

        return _summarize_mc_results(results, n_sessions=n_sessions, n_steps=n_steps, seed=seed)


@dataclass(frozen=True, slots=True)
class Round5JointConfig:
    """Representative multi-category Round 5 joint simulation configuration."""

    position_limit: int = 10
    pebbles_sum_target: float = 50000.0
    pebbles_sum_noise: float = 2.8
    pebbles_sigma: float = 15.1
    pebbles_pulse_prob: float = 0.022
    snackpack_pair_target: float = 20000.0
    snackpack_pair_sigma: float = 6.5
    snackpack_pair_corr: float = -0.91
    snackpack_spread: float = 8.5
    group_v_pulse_prob: float = 0.024
    mm_symbols: tuple[str, ...] = (
        "GALAXY_SOUNDS_DARK_MATTER",
        "UV_VISOR_RED",
        "OXYGEN_SHAKE_MINT",
        "ROBOT_IRONING",
    )
    mm_sigmas: tuple[float, ...] = (10.3, 10.6, 10.1, 11.2)
    mm_half_spreads: tuple[float, ...] = (6.5, 7.0, 6.5, 3.0)


class Round5JointMonteCarloEngine:
    """Two-layer Round 5 Monte Carlo simulator (baskets + wide/tight MM + sync pulses)."""

    PEBBLES: tuple[str, ...] = (
        "PEBBLES_XS",
        "PEBBLES_S",
        "PEBBLES_M",
        "PEBBLES_L",
        "PEBBLES_XL",
    )
    SNACKPACK_PAIR: tuple[str, str] = ("SNACKPACK_CHOCOLATE", "SNACKPACK_VANILLA")

    def __init__(
        self,
        config: Round5JointConfig | None = None,
        fill_mode: FillMode = "queue_aware",
    ) -> None:
        self.config = config or Round5JointConfig()
        self.fill_mode: FillMode = fill_mode
        all_syms = [*self.PEBBLES, *self.SNACKPACK_PAIR, *self.config.mm_symbols]
        self.position_limits = dict.fromkeys(all_syms, self.config.position_limit)

    def run(
        self,
        strategy_factory: Callable[[], BaseStrategy],
        n_sessions: int = 20,
        n_steps: int = 1000,
        seed: int = 42,
    ) -> MonteCarloSummary:
        """Execute joint Round 5 Monte Carlo backtest."""
        if n_sessions <= 0 or n_steps <= 0:
            msg = "n_sessions and n_steps must be positive"
            raise ValueError(msg)

        rng = np.random.default_rng(seed)
        sim = ExecutionSimulator(position_limits=self.position_limits, fill_mode=self.fill_mode)
        engine = BacktestEngine(simulator=sim)
        results: list[BacktestResult] = []

        pebble_book_cfgs = [
            BotBookConfig(half_spread_l1=s, depth_l1=12, step_l2=2, depth_l2=3)
            for s in (5.5, 6.0, 6.5, 6.5, 8.5)
        ]
        pair_book_cfg = BotBookConfig(
            half_spread_l1=self.config.snackpack_spread,
            depth_l1=15,
            step_l2=2,
            depth_l2=3,
        )
        mm_book_cfgs = [
            BotBookConfig(half_spread_l1=hs, depth_l1=15, step_l2=2, depth_l2=3)
            for hs in self.config.mm_half_spreads
        ]

        for _ in range(n_sessions):
            peb_fvs = np.array([8000.0, 9400.0, 10000.0, 10000.0, 12600.0], dtype=np.float64)
            choc_fv = self.config.snackpack_pair_target * 0.5
            van_fv = self.config.snackpack_pair_target * 0.5
            mm_fvs = np.full(len(self.config.mm_symbols), 10000.0, dtype=np.float64)

            snapshots: list[MarketStateSnapshot] = []
            rho = self.config.snackpack_pair_corr
            orth = math.sqrt(max(0.0, 1.0 - rho * rho))

            for t in range(n_steps):
                ts = t * 100
                # Evolve first 4 Pebbles random walks, constrain 5th leg near target_sum
                peb_fvs[:4] += rng.normal(0.0, self.config.pebbles_sigma, size=4)
                noise_sum = float(rng.normal(0.0, self.config.pebbles_sum_noise))
                peb_fvs[4] = (
                    self.config.pebbles_sum_target - float(np.sum(peb_fvs[:4])) + noise_sum
                )

                # Evolve negatively correlated Snackpack pair around equilibrium
                z1, z2 = rng.normal(size=2)
                d_choc = self.config.snackpack_pair_sigma * z1
                d_van = self.config.snackpack_pair_sigma * (rho * z1 + orth * z2)
                choc_fv += d_choc
                van_fv += d_van
                # Weak mean reversion of sum toward target
                pair_dev = (choc_fv + van_fv) - self.config.snackpack_pair_target
                choc_fv -= 0.002 * pair_dev
                van_fv -= 0.002 * pair_dev

                mm_fvs += rng.normal(0.0, self.config.mm_sigmas)

                books: dict[str, OrderBookL2] = {}
                trades: dict[str, list[TradePrint]] = {}

                gv_pulse = rng.random() < self.config.group_v_pulse_prob
                gv_pulse_buy = bool(rng.random() < 0.5)
                gv_pulse_qty = int(rng.integers(1, 4))

                peb_pulse = rng.random() < self.config.pebbles_pulse_prob
                peb_pulse_buy = bool(rng.random() < 0.5)
                peb_pulse_qty = int(rng.integers(1, 4))

                for p_idx, sym in enumerate(self.PEBBLES):
                    book = build_synthetic_book(
                        sym,
                        float(peb_fvs[p_idx]),
                        pebble_book_cfgs[p_idx],
                    )
                    books[sym] = book
                    if peb_pulse:
                        px = book.best_ask if peb_pulse_buy else book.best_bid
                        if px is not None:
                            trades[sym] = [TradePrint(ts, sym, int(px), peb_pulse_qty, "", "")]
                    elif rng.random() < 0.12:
                        px = book.best_ask if rng.random() < 0.5 else book.best_bid
                        if px is not None:
                            qty = int(rng.integers(1, 4))
                            trades[sym] = [TradePrint(ts, sym, int(px), qty, "", "")]

                pair_specs = (
                    (self.SNACKPACK_PAIR[0], choc_fv),
                    (self.SNACKPACK_PAIR[1], van_fv),
                )
                for pair_sym, fv in pair_specs:
                    book = build_synthetic_book(pair_sym, float(fv), pair_book_cfg)
                    books[pair_sym] = book
                    if gv_pulse:
                        px = book.best_ask if gv_pulse_buy else book.best_bid
                        if px is not None:
                            trades[pair_sym] = [
                                TradePrint(ts, pair_sym, int(px), gv_pulse_qty, "", ""),
                            ]
                    elif rng.random() < 0.14:
                        px = book.best_ask if rng.random() < 0.5 else book.best_bid
                        if px is not None:
                            qty = int(rng.integers(1, 4))
                            trades[pair_sym] = [
                                TradePrint(ts, pair_sym, int(px), qty, "", ""),
                            ]

                for m_idx, sym in enumerate(self.config.mm_symbols):
                    book = build_synthetic_book(sym, float(mm_fvs[m_idx]), mm_book_cfgs[m_idx])
                    books[sym] = book
                    if gv_pulse:
                        px = book.best_ask if gv_pulse_buy else book.best_bid
                        if px is not None:
                            trades[sym] = [TradePrint(ts, sym, int(px), gv_pulse_qty, "", "")]
                    elif rng.random() < 0.14:
                        px = book.best_ask if rng.random() < 0.5 else book.best_bid
                        if px is not None:
                            qty = int(rng.integers(1, 4))
                            trades[sym] = [
                                TradePrint(ts, sym, int(px), qty, "", ""),
                            ]

                snapshots.append(
                    MarketStateSnapshot(timestamp=ts, books=books, market_trades=trades),
                )

            results.append(engine.run(strategy_factory(), snapshots))

        return _summarize_mc_results(results, n_sessions=n_sessions, n_steps=n_steps, seed=seed)
