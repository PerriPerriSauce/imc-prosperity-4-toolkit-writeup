"""Reproducible Round 2-5 evaluation, IS/OOS ablations, overfitting gates, and MC suites."""

from __future__ import annotations

import csv
import importlib.util
import math
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from numpy.typing import NDArray

from prosperity_toolkit.analysis.diagnostics import OverfittingDiagnostics
from prosperity_toolkit.backtesting.engine import BacktestEngine
from prosperity_toolkit.backtesting.replay import build_snapshots_from_dataframes
from prosperity_toolkit.backtesting.results import BacktestResult
from prosperity_toolkit.competition import (
    PROSPERITY4_R5_CATEGORIES,
    get_round_position_limits,
    get_round_products,
)
from prosperity_toolkit.competition.adapter import (
    CompetitionStrategyAdapter,
    CompetitionTraderProtocol,
)
from prosperity_toolkit.core.models import OrderRequest, Symbol
from prosperity_toolkit.data.loader import DataLoader
from prosperity_toolkit.execution.fills import FillEvent
from prosperity_toolkit.execution.simulator import ExecutionSimulator, FillMode
from prosperity_toolkit.market.market_state import MarketStateSnapshot
from prosperity_toolkit.market.order_book import OrderBookL2
from prosperity_toolkit.optimisation.sensitivity import SensitivityAnalyzer
from prosperity_toolkit.simulation import (
    AssetScenarioConfig,
    BotBookConfig,
    CoupledOptionsMonteCarloEngine,
    OptionsSpotScenarioConfig,
    OrnsteinUhlenbeckParams,
    RandomWalkParams,
    Round5JointMonteCarloEngine,
    TradeArrivalConfig,
    simulate_arrival_sensitivity,
)
from prosperity_toolkit.strategies import (
    BaseStrategy,
    DriftAwareConfig,
    DriftAwareQuoter,
    InventorySkewedMarketMaker,
    MarketMakingConfig,
    NoOpBaselineStrategy,
    OptionsVolatilityStrategy,
    SymmetricMarketMaker,
)


def _load_trader(round_num: int) -> CompetitionTraderProtocol:
    repo_root = Path(__file__).resolve().parents[1]
    traders_dir = str(repo_root / "traders")
    if traders_dir not in sys.path:
        sys.path.insert(0, traders_dir)
    sub_path = repo_root / "traders" / f"round{round_num}" / "submission.py"
    spec = importlib.util.spec_from_file_location(f"round{round_num}_eval_sub", sub_path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    trader: CompetitionTraderProtocol = mod.Trader()
    return trader


def _popular_wall_mid(book: OrderBookL2) -> float | None:
    if not book.bids or not book.asks:
        return None
    wb = max(book.bids.items(), key=lambda kv: (abs(kv[1]), kv[0]))[0]
    wa = max(book.asks.items(), key=lambda kv: (abs(kv[1]), -kv[0]))[0]
    return float(0.5 * (wb + wa))


def _per_symbol_pnl(
    fills: Sequence[FillEvent],
    snapshots: Sequence[MarketStateSnapshot],
) -> dict[str, float]:
    last_marks: dict[str, float] = {}
    for snap in snapshots:
        for sym, book in snap.books.items():
            mid = book.mid_price
            if mid is not None:
                last_marks[sym] = mid
    cash: dict[str, float] = {}
    pos: dict[str, int] = {}
    for fill in fills:
        cash[fill.symbol] = cash.get(fill.symbol, 0.0) - fill.price * fill.quantity - fill.fee
        pos[fill.symbol] = pos.get(fill.symbol, 0) + fill.quantity
    return {
        sym: cash.get(sym, 0.0) + pos.get(sym, 0) * last_marks.get(sym, 0.0)
        for sym in sorted(set(cash) | set(pos))
    }


def _bs_call_total_v(spot: float, strike: float, tv: float) -> tuple[float, float]:
    from statistics import NormalDist

    norm = NormalDist(0.0, 1.0)
    if tv <= 1e-6 or spot <= 0.0 or strike <= 0.0:
        return max(0.0, spot - strike), (1.0 if spot > strike else 0.0)
    d1 = (math.log(spot / strike) + 0.5 * tv * tv) / tv
    d2 = d1 - tv
    delta = norm.cdf(d1)
    return spot * delta - strike * norm.cdf(d2), delta


def _invert_total_v(price: float, spot: float, strike: float) -> float | None:
    intr = max(0.0, spot - strike)
    if spot <= 0.0 or strike <= 0.0 or price <= intr + 0.2 or price >= spot:
        return None
    lo, hi = 1e-4, 0.5
    for _ in range(28):
        mid = 0.5 * (lo + hi)
        est, _ = _bs_call_total_v(spot, strike, mid)
        if est < price:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


class ParameterizedR2Strategy(BaseStrategy):
    """Parameterized Round 2 candidate matching `traders/round2/submission.py`."""

    def __init__(self, min_edge: float, inventory_skew: float, clip: int = 30) -> None:
        super().__init__(name=f"ParamR2(e={min_edge},k={inventory_skew})")
        self.min_edge = min_edge
        self.inventory_skew = inventory_skew
        self.clip = clip
        self._fv: dict[Symbol, float] = {}
        self._drift: dict[Symbol, float] = {}
        self._last_ts: dict[Symbol, int] = {}

    def generate_orders(self, state: MarketStateSnapshot) -> list[OrderRequest]:
        orders: list[OrderRequest] = []
        for sym in ("ASH_COATED_OSMIUM", "INTARIAN_PEPPER_ROOT"):
            b = state.get_book(sym)
            if b is None:
                continue
            obs = _popular_wall_mid(b)
            if sym == "ASH_COATED_OSMIUM":
                if obs is not None:
                    self._fv[sym] = 0.25 * obs + 0.75 * self._fv.get(sym, obs)
            else:
                lt = self._last_ts.get(sym, state.timestamp)
                dt = max(1.0, (state.timestamp - lt) / 100.0) if state.timestamp > lt else 1.0
                if obs is not None:
                    if sym not in self._fv:
                        self._fv[sym], self._drift[sym] = obs, 0.0
                    else:
                        pred = self._fv[sym] + self._drift[sym] * dt
                        inn = obs - pred
                        self._fv[sym] = pred + 0.25 * inn
                        self._drift[sym] += 0.01 * (inn / dt)
                    self._last_ts[sym] = state.timestamp
                elif sym in self._fv:
                    self._fv[sym] += self._drift[sym] * dt
                    self._last_ts[sym] = state.timestamp
            fv = self._fv.get(sym)
            if fv is None:
                continue
            pos = state.get_position(sym)
            bcap, scap = max(0, 80 - pos), max(0, 80 + pos)
            tb = ts_q = 0
            if b.best_ask is not None and b.best_ask <= fv - 1.0 and bcap > 0:
                for ap in sorted(b.asks):
                    if ap > fv - 1.0 or bcap - tb <= 0:
                        break
                    q = min(abs(b.asks[ap]), bcap - tb)
                    if q > 0:
                        orders.append(OrderRequest(sym, ap, q))
                        tb += q
            if b.best_bid is not None and b.best_bid >= fv + 1.0 and scap > 0:
                for bp in sorted(b.bids, reverse=True):
                    if bp < fv + 1.0 or scap - ts_q <= 0:
                        break
                    q = min(abs(b.bids[bp]), scap - ts_q)
                    if q > 0:
                        orders.append(OrderRequest(sym, bp, -q))
                        ts_q += q
            res = fv - self.inventory_skew * pos
            qb = (
                min(math.floor(res - self.min_edge), b.best_bid + 1)
                if b.best_bid is not None
                else math.floor(res - self.min_edge)
            )
            qa = (
                max(math.ceil(res + self.min_edge), b.best_ask - 1)
                if b.best_ask is not None
                else math.ceil(res + self.min_edge)
            )
            if b.best_ask is not None and qb >= b.best_ask:
                qb = b.best_ask - 1
            if b.best_bid is not None and qa <= b.best_bid:
                qa = b.best_bid + 1
            if qb < qa and qb > 0:
                if bcap - tb > 0:
                    orders.append(OrderRequest(sym, qb, min(self.clip, bcap - tb)))
                if scap - ts_q > 0:
                    orders.append(OrderRequest(sym, qa, -min(self.clip, scap - ts_q)))
        return orders


class ParameterizedR3R4Strategy(BaseStrategy):
    """Parameterized Round 3/4 candidate matching `traders/round{3,4}/submission.py`."""

    def __init__(self, mm_edge: float, mm_skew: float, m67_bump: float = 0.0) -> None:
        super().__init__(name=f"ParamR3R4(e={mm_edge},k={mm_skew},m67={m67_bump})")
        self.mm_edge = mm_edge
        self.mm_skew = mm_skew
        self.m67_bump = m67_bump
        self._fv: dict[Symbol, float] = {}
        self._v_ema: dict[Symbol, float] = {}
        self._m67 = 0.0

    def generate_orders(self, state: MarketStateSnapshot) -> list[OrderRequest]:
        orders: list[OrderRequest] = []
        hb = state.get_book("HYDROGEL_PACK")
        if hb is not None:
            obs = _popular_wall_mid(hb)
            if obs is not None:
                self._fv["HYDROGEL_PACK"] = 0.25 * obs + 0.75 * self._fv.get("HYDROGEL_PACK", obs)
            hfv = self._fv.get("HYDROGEL_PACK")
            if hfv is not None:
                pos = state.get_position("HYDROGEL_PACK")
                bcap, scap = max(0, 200 - pos), max(0, 200 + pos)
                tb = ts_q = 0
                if hb.best_ask is not None and hb.best_ask <= hfv - 1.5 and bcap > 0:
                    for ap in sorted(hb.asks):
                        if ap > hfv - 1.5 or bcap - tb <= 0:
                            break
                        q = min(abs(hb.asks[ap]), bcap - tb)
                        if q > 0:
                            orders.append(OrderRequest("HYDROGEL_PACK", ap, q))
                            tb += q
                if hb.best_bid is not None and hb.best_bid >= hfv + 1.5 and scap > 0:
                    for bp in sorted(hb.bids, reverse=True):
                        if bp < hfv + 1.5 or scap - ts_q <= 0:
                            break
                        q = min(abs(hb.bids[bp]), scap - ts_q)
                        if q > 0:
                            orders.append(OrderRequest("HYDROGEL_PACK", bp, -q))
                            ts_q += q
                res = hfv - self.mm_skew * pos
                qb = (
                    min(math.floor(res - self.mm_edge), hb.best_bid + 1)
                    if hb.best_bid is not None
                    else math.floor(res - self.mm_edge)
                )
                qa = (
                    max(math.ceil(res + self.mm_edge), hb.best_ask - 1)
                    if hb.best_ask is not None
                    else math.ceil(res + self.mm_edge)
                )
                if hb.best_ask is not None and qb >= hb.best_ask:
                    qb = hb.best_ask - 1
                if hb.best_bid is not None and qa <= hb.best_bid:
                    qa = hb.best_bid + 1
                if qb < qa and qb > 0:
                    if bcap - tb > 0:
                        orders.append(OrderRequest("HYDROGEL_PACK", qb, min(60, bcap - tb)))
                    if scap - ts_q > 0:
                        orders.append(OrderRequest("HYDROGEL_PACK", qa, -min(60, scap - ts_q)))

        sb = state.get_book("VELVETFRUIT_EXTRACT")
        if sb is None:
            return orders
        sobs = _popular_wall_mid(sb)
        if sobs is not None:
            self._fv["VELVETFRUIT_EXTRACT"] = 0.45 * sobs + 0.55 * self._fv.get(
                "VELVETFRUIT_EXTRACT",
                sobs,
            )
        sfv = self._fv.get("VELVETFRUIT_EXTRACT")
        if sfv is None:
            return orders

        if self.m67_bump > 0.0:
            v_tr = state.market_trades.get("VELVETFRUIT_EXTRACT", [])
            if any(tr.buyer == "Mark 67" for tr in v_tr):
                self._m67 = self.m67_bump
            else:
                self._m67 *= 0.80
        sfv_eff = sfv + self._m67

        net_delta = 0.0
        for sym, strike in (("VEV_4000", 4000.0), ("VEV_4500", 4500.0)):
            ob = state.get_book(sym)
            if ob is None:
                continue
            pos = state.get_position(sym)
            net_delta += float(pos)
            fair = sfv_eff - strike
            bcap, scap = max(0, 300 - pos), max(0, 300 + pos)
            tb = ts_q = 0
            if ob.best_ask is not None and ob.best_ask <= fair - 2.0 and bcap > 0:
                q = min(abs(ob.asks[ob.best_ask]), bcap)
                if q > 0:
                    orders.append(OrderRequest(sym, ob.best_ask, q))
                    tb = q
            if ob.best_bid is not None and ob.best_bid >= fair + 2.0 and scap > 0:
                q = min(abs(ob.bids[ob.best_bid]), scap)
                if q > 0:
                    orders.append(OrderRequest(sym, ob.best_bid, -q))
                    ts_q = q
            res = fair - 0.025 * pos
            qb = (
                min(math.floor(res - 2.5), ob.best_bid + 1)
                if ob.best_bid is not None
                else math.floor(res - 2.5)
            )
            qa = (
                max(math.ceil(res + 2.5), ob.best_ask - 1)
                if ob.best_ask is not None
                else math.ceil(res + 2.5)
            )
            if ob.best_ask is not None and qb >= ob.best_ask:
                qb = ob.best_ask - 1
            if ob.best_bid is not None and qa <= ob.best_bid:
                qa = ob.best_bid + 1
            if qb < qa and qb > 0:
                if bcap - tb > 0:
                    orders.append(OrderRequest(sym, qb, min(40, bcap - tb)))
                if scap - ts_q > 0:
                    orders.append(OrderRequest(sym, qa, -min(40, scap - ts_q)))

        for sym, strike in (
            ("VEV_5200", 5200.0),
            ("VEV_5300", 5300.0),
            ("VEV_5400", 5400.0),
            ("VEV_5500", 5500.0),
        ):
            ob = state.get_book(sym)
            if ob is None or ob.best_bid is None or ob.best_ask is None:
                continue
            mid_o = 0.5 * (ob.best_bid + ob.best_ask)
            v_obs = _invert_total_v(mid_o, sfv_eff, strike)
            if v_obs is not None:
                self._v_ema[sym] = 0.05 * v_obs + 0.95 * self._v_ema.get(sym, v_obs)
            v_fair = self._v_ema.get(sym)
            if v_fair is None:
                continue
            fair, delta = _bs_call_total_v(sfv_eff, strike, v_fair)
            pos = state.get_position(sym)
            net_delta += float(pos) * delta
            bcap, scap = max(0, 300 - pos), max(0, 300 + pos)
            tb = ts_q = 0
            if ob.best_ask <= fair - 1.5 and bcap > 0:
                q = min(10, abs(ob.asks[ob.best_ask]), bcap)
                if q > 0:
                    orders.append(OrderRequest(sym, ob.best_ask, q))
                    tb = q
            if ob.best_bid >= fair + 1.5 and scap > 0:
                q = min(10, abs(ob.bids[ob.best_bid]), scap)
                if q > 0:
                    orders.append(OrderRequest(sym, ob.best_bid, -q))
                    ts_q = q
            res_o = fair - 0.005 * pos
            qb = min(math.floor(res_o - 0.5), ob.best_bid + 1)
            qa = max(math.ceil(res_o + 0.5), ob.best_ask - 1)
            if qb >= ob.best_ask:
                qb = ob.best_ask - 1
            if qa <= ob.best_bid:
                qa = ob.best_bid + 1
            if qb < qa and qb > 0:
                if bcap - tb > 0:
                    orders.append(OrderRequest(sym, qb, min(15, bcap - tb)))
                if scap - ts_q > 0:
                    orders.append(OrderRequest(sym, qa, -min(15, scap - ts_q)))

        spos = state.get_position("VELVETFRUIT_EXTRACT")
        tot_delta = float(spos) + net_delta
        bcap, scap = max(0, 200 - spos), max(0, 200 + spos)
        hb_q = hs_q = 0
        if tot_delta < -10.0 and sb.best_ask is not None and sb.best_ask <= sfv_eff + 2.5:
            q = min(math.floor(-tot_delta), abs(sb.asks[sb.best_ask]), bcap)
            if q > 0:
                orders.append(OrderRequest("VELVETFRUIT_EXTRACT", sb.best_ask, q))
                hb_q = q
        elif tot_delta > 10.0 and sb.best_bid is not None and sb.best_bid >= sfv_eff - 2.5:
            q = min(math.floor(tot_delta), abs(sb.bids[sb.best_bid]), scap)
            if q > 0:
                orders.append(OrderRequest("VELVETFRUIT_EXTRACT", sb.best_bid, -q))
                hs_q = q
        if (
            self._m67 > 0.6
            and sb.best_ask is not None
            and sb.best_ask <= sfv_eff + 0.2
            and bcap - hb_q > 0
        ):
            q = min(abs(sb.asks[sb.best_ask]), bcap - hb_q)
            if q > 0:
                orders.append(OrderRequest("VELVETFRUIT_EXTRACT", sb.best_ask, q))
                hb_q += q
        res = sfv_eff - 0.03 * tot_delta
        ask_guard = 1.5 + (0.8 * self._m67 if self._m67 > 0.4 else 0.0)
        qb = (
            min(math.floor(res - 1.5), sb.best_bid + 1)
            if sb.best_bid is not None
            else math.floor(res - 1.5)
        )
        qa = (
            max(math.ceil(res + ask_guard), sb.best_ask - 1)
            if sb.best_ask is not None
            else math.ceil(res + ask_guard)
        )
        if sb.best_ask is not None and qb >= sb.best_ask:
            qb = sb.best_ask - 1
        if sb.best_bid is not None and qa <= sb.best_bid:
            qa = sb.best_bid + 1
        if qb < qa and qb > 0:
            if bcap - hb_q > 0:
                orders.append(OrderRequest("VELVETFRUIT_EXTRACT", qb, min(35, bcap - hb_q)))
            if scap - hs_q > 0:
                orders.append(OrderRequest("VELVETFRUIT_EXTRACT", qa, -min(35, scap - hs_q)))
        return orders


class ParameterizedR5Strategy(BaseStrategy):
    """Parameterized Round 5 candidate matching `traders/round5/submission.py`."""

    def __init__(
        self,
        edge_frac: float,
        skew: float,
        skip_low_ratio: bool = False,
        use_baskets: bool = True,
        vol_guard: bool = True,
        clip: int = 10,
        name: str | None = None,
    ) -> None:
        super().__init__(name=name or f"ParamR5(ef={edge_frac},sk={skew})")
        self.edge_frac = edge_frac
        self.skew = skew
        self.skip_low_ratio = skip_low_ratio
        self.use_baskets = use_baskets
        self.vol_guard = vol_guard
        self.clip = clip
        self.pair_ema: float | None = None
        self.last_mids: dict[str, float] = {}
        self.vol_ema: dict[str, float] = {}
        self.pebbles = PROSPERITY4_R5_CATEGORIES["Pebbles"]
        self.low_ratio_set = set(PROSPERITY4_R5_CATEGORIES["Robots"]) | set(
            PROSPERITY4_R5_CATEGORIES["Microchips"],
        )

    def generate_orders(self, state: MarketStateSnapshot) -> list[OrderRequest]:
        orders: list[OrderRequest] = []
        peb: dict[Symbol, float] = {}
        peb_full = False
        pair_res = 0.0
        if self.use_baskets:
            for s in self.pebbles:
                b = state.get_book(s)
                if b is not None:
                    m = _popular_wall_mid(b)
                    if m is not None:
                        peb[s] = m
            peb_full = len(peb) == 5

            cb = state.get_book("SNACKPACK_CHOCOLATE")
            vb = state.get_book("SNACKPACK_VANILLA")
            cm = _popular_wall_mid(cb) if cb is not None else None
            vm = _popular_wall_mid(vb) if vb is not None else None
            if cm is not None and vm is not None:
                ps = cm + vm
                self.pair_ema = ps if self.pair_ema is None else 0.005 * ps + 0.995 * self.pair_ema
                pair_res = ps - self.pair_ema

        for sym, b in state.books.items():
            fv = _popular_wall_mid(b)
            if fv is None:
                continue

            prev_m = self.last_mids.get(sym)
            if prev_m is not None:
                step_d = abs(fv - prev_m)
                self.vol_ema[sym] = (
                    step_d
                    if sym not in self.vol_ema
                    else 0.02 * step_d + 0.98 * self.vol_ema[sym]
                )
            self.last_mids[sym] = round(fv, 2)

            is_low = sym in self.low_ratio_set
            if self.skip_low_ratio and is_low:
                continue

            best_ask = b.best_ask
            best_bid = b.best_bid
            spr = (best_ask - best_bid) if (best_ask is not None and best_bid is not None) else 10
            if self.vol_guard and is_low and spr < 0.50 * self.vol_ema.get(sym, 8.0):
                continue

            if self.use_baskets and sym in ("SNACKPACK_CHOCOLATE", "SNACKPACK_VANILLA"):
                fv -= 0.25 * pair_res

            peb_imp = (
                50000.0 - sum(v for k, v in peb.items() if k != sym)
                if (self.use_baskets and peb_full and sym in peb)
                else fv
            )

            pos = state.get_position(sym)
            bcap = 10 - pos if pos < 10 else 0
            scap = 10 + pos if pos > -10 else 0
            tb = ts_q = 0
            take_b = (
                max(fv, peb_imp - 1.5)
                if (self.use_baskets and peb_full and sym in peb)
                else fv
            )
            take_s = (
                min(fv, peb_imp + 1.5)
                if (self.use_baskets and peb_full and sym in peb)
                else fv
            )
            if best_ask is not None and best_ask <= take_b - 1.5 and bcap > 0:
                for ap in sorted(b.asks):
                    if ap > take_b - 1.5 or bcap - tb <= 0:
                        break
                    q = min(abs(b.asks[ap]), bcap - tb)
                    if q > 0:
                        orders.append(OrderRequest(sym, ap, q))
                        tb += q
            if best_bid is not None and best_bid >= take_s + 1.5 and scap > 0:
                for bp in sorted(b.bids, reverse=True):
                    if bp < take_s + 1.5 or scap - ts_q <= 0:
                        break
                    q = min(abs(b.bids[bp]), scap - ts_q)
                    if q > 0:
                        orders.append(OrderRequest(sym, bp, -q))
                        ts_q += q

            ef = 0.35 if is_low else self.edge_frac
            sk = 1.5 * self.skew if is_low else self.skew
            edge = max(1.5, ef * spr)
            res = fv - sk * pos
            qb = (
                min(math.floor(res - edge), best_bid + 1)
                if best_bid is not None
                else math.floor(res - edge)
            )
            qa = (
                max(math.ceil(res + edge), best_ask - 1)
                if best_ask is not None
                else math.ceil(res + edge)
            )
            if best_ask is not None and qb >= best_ask:
                qb = best_ask - 1
            if best_bid is not None and qa <= best_bid:
                qa = best_bid + 1
            if qb < qa and qb > 0:
                if bcap - tb > 0:
                    orders.append(OrderRequest(sym, qb, min(self.clip, bcap - tb)))
                if scap - ts_q > 0:
                    orders.append(OrderRequest(sym, qa, -min(self.clip, scap - ts_q)))
        return orders


def _run_day_set(
    day_snaps: dict[int, list[MarketStateSnapshot]],
    limits: dict[str, int],
    factory: Callable[[], BaseStrategy],
    fill_mode: FillMode = "queue_aware",
) -> tuple[float, float, float, int, float, NDArray[np.float64], dict[str, float]]:
    """Run independent per-day simulations (zero overnight carry) and aggregate stats."""
    total_pnl = 0.0
    max_dd = 0.0
    total_fills = 0
    latencies: list[float] = []
    rets_list: list[NDArray[np.float64]] = []
    per_sym: dict[str, float] = {}
    curve_offset = 0.0
    merged_curve: list[float] = [0.0]

    for snaps in day_snaps.values():
        strat = factory()
        sim = ExecutionSimulator(position_limits=limits, fill_mode=fill_mode)
        res: BacktestResult = BacktestEngine(simulator=sim).run(strat, snaps)
        total_pnl += res.total_pnl
        max_dd = max(max_dd, res.max_drawdown)
        total_fills += len(res.fills)
        if isinstance(strat, CompetitionStrategyAdapter) and strat.latencies_ms:
            latencies.extend(strat.latencies_ms)
        eq = np.asarray(res.equity_curve, dtype=np.float64)
        rets_list.append(np.diff(eq))
        merged_curve.extend((eq[1:] + curve_offset).tolist())
        curve_offset += res.total_pnl
        for sym, val in _per_symbol_pnl(res.fills, snaps).items():
            per_sym[sym] = per_sym.get(sym, 0.0) + val

    rets = np.concatenate(rets_list)
    std = float(np.std(rets, ddof=1)) if rets.size > 1 else 0.0
    sharpe_252 = (float(np.mean(rets)) / std) * math.sqrt(252.0) if std > 0.0 else 0.0
    mean_lat = float(np.mean(latencies)) if latencies else 0.0
    _ = merged_curve
    return total_pnl, sharpe_252, max_dd, total_fills, mean_lat, rets, per_sym


def _evaluate_is_grid(
    round_num: int,
    day_snaps: dict[int, list[MarketStateSnapshot]],
    limits: dict[str, int],
    x_vals: Sequence[float],
    y_vals: Sequence[float],
    x_label: str,
    y_label: str,
    factory_fn: Callable[[float, float], BaseStrategy],
    table_path: Path,
) -> tuple[
    NDArray[np.float64],
    NDArray[np.float64],
    float,
    float,
    float,
    float,
    float,
    float,
    float,
]:
    """Evaluate 2D IS grid under sqrt(252) Sharpe, compute plateau, CSCV, DSR, and N_eff."""
    sharpe_grid = np.zeros((len(x_vals), len(y_vals)), dtype=np.float64)
    pnl_grid = np.zeros((len(x_vals), len(y_vals)), dtype=np.float64)
    returns_cols: list[NDArray[np.float64]] = []
    trial_sharpes: list[float] = []

    for i, x in enumerate(x_vals):
        for j, y in enumerate(y_vals):

            def _cell_factory(xx: float = x, yy: float = y) -> BaseStrategy:
                return factory_fn(xx, yy)

            pnl, sr_252, _dd, _nf, _lat, rets, _ps = _run_day_set(
                day_snaps,
                limits,
                _cell_factory,
                fill_mode="queue_aware",
            )
            std = float(np.std(rets, ddof=1))
            sr_step = float(np.mean(rets) / std) if std > 0.0 else 0.0
            sharpe_grid[i, j] = sr_252
            pnl_grid[i, j] = pnl
            returns_cols.append(rets)
            trial_sharpes.append(sr_step)

    plateau = SensitivityAnalyzer.select_stable_plateau_2d(
        x_vals,
        y_vals,
        sharpe_grid,
        std_penalty=1.0,
    )
    mat = np.column_stack(returns_cols)
    cscv = OverfittingDiagnostics.compute_cscv_pbo(mat, n_slices=8)
    sel_idx = plateau.x_index * len(y_vals) + plateau.y_index
    dsr = OverfittingDiagnostics.evaluate_trial_dsr(mat[:, sel_idx], trial_sharpes)
    n_eff = OverfittingDiagnostics.estimate_effective_trials(mat)

    with table_path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow([x_label, y_label, "is_sharpe_252", "is_total_pnl"])
        for i, x in enumerate(x_vals):
            for j, y in enumerate(y_vals):
                w.writerow(
                    [x, y, round(float(sharpe_grid[i, j]), 4), round(float(pnl_grid[i, j]), 2)]
                )

    print(
        f"R{round_num} IS Plateau: {x_label}={plateau.x_value}, {y_label}={plateau.y_value} | "
        f"SR_252={plateau.raw_score:.3f}, locMean={plateau.local_mean:.3f}, "
        f"locStd={plateau.local_std:.3f} | N_eff={n_eff:.2f} | "
        f"PBO={cscv.pbo:.3f} | DSR={dsr.deflated_sharpe_ratio:.4f}",
    )
    return (
        sharpe_grid,
        pnl_grid,
        float(plateau.x_value),
        float(plateau.y_value),
        plateau.raw_score,
        plateau.local_mean,
        plateau.local_std,
        cscv.pbo,
        dsr.deflated_sharpe_ratio,
    )


def main() -> int:
    """Execute complete reproducible Round 2-5 evaluation and generate tables/figures."""
    table_dir = Path("reports/tables")
    fig_dir = Path("reports/figures")
    table_dir.mkdir(parents=True, exist_ok=True)
    fig_dir.mkdir(parents=True, exist_ok=True)

    loader = DataLoader()
    modes: tuple[FillMode, ...] = ("conservative", "queue_aware", "touch")
    overfit_rows: list[list[object]] = []
    bootstrap_rows: list[list[object]] = []
    oos_equity_curves: dict[int, NDArray[np.float64]] = {}

    # ------------------------------------------------------------------
    # ROUND 2: IS (Day -1, 0) & OOS (Day 1)
    # ------------------------------------------------------------------
    print("\n=== Evaluating Round 2 (+/-80 limits) ===")
    lim2 = get_round_position_limits(2)
    r2_is = {
        d: build_snapshots_from_dataframes(
            loader.load_day_prices(2, d), loader.load_day_trades(2, d)
        )
        for d in (-1, 0)
    }
    r2_oos = {
        1: build_snapshots_from_dataframes(
            loader.load_day_prices(2, 1), loader.load_day_trades(2, 1)
        ),
    }
    r2_edges = [1.5, 2.5, 3.5, 4.5]
    r2_skews = [0.15, 0.30, 0.45, 0.60, 0.75]
    r2_grid, _, x2, y2, sr2_raw, locm2, locs2, pbo2, dsr2 = _evaluate_is_grid(
        2,
        r2_is,
        lim2,
        r2_edges,
        r2_skews,
        "min_edge",
        "inventory_skew",
        lambda e, k: ParameterizedR2Strategy(e, k),
        table_dir / "r2_sensitivity_grid.csv",
    )

    r2_ab_rows: list[list[object]] = []
    for split, days_map in (("IS", r2_is), ("OOS", r2_oos)):
        for mode in modes:
            factories: list[tuple[str, Callable[[], BaseStrategy]]] = [
                ("NoOpBaseline", lambda: NoOpBaselineStrategy()),
                (
                    "SymmetricMM_80",
                    lambda: SymmetricMarketMaker(
                        [
                            MarketMakingConfig(
                                "ASH_COATED_OSMIUM", position_limit=80, quote_size=25
                            ),
                            MarketMakingConfig(
                                "INTARIAN_PEPPER_ROOT", position_limit=80, quote_size=25
                            ),
                        ]
                    ),
                ),
                (
                    "InventorySkewedMM_80",
                    lambda: InventorySkewedMarketMaker(
                        [
                            MarketMakingConfig(
                                "ASH_COATED_OSMIUM", position_limit=80, quote_size=25
                            ),
                            MarketMakingConfig(
                                "INTARIAN_PEPPER_ROOT", position_limit=80, quote_size=25
                            ),
                        ]
                    ),
                ),
                (
                    "DriftAwareQuoter_Pepper",
                    lambda: DriftAwareQuoter(
                        [
                            DriftAwareConfig(
                                "INTARIAN_PEPPER_ROOT", position_limit=80, quote_size=25
                            ),
                        ]
                    ),
                ),
                (
                    "Round2Submission",
                    lambda: CompetitionStrategyAdapter(_load_trader(2), name="Round2Submission"),
                ),
            ]
            for sname, fac in factories:
                pnl, sr, dd, nf, lat, rets, ps = _run_day_set(days_map, lim2, fac, fill_mode=mode)
                r2_ab_rows.append(
                    [
                        split,
                        mode,
                        sname,
                        round(pnl, 2),
                        round(sr, 4),
                        round(dd, 2),
                        nf,
                        round(lat, 4),
                    ]
                )
                if split == "OOS" and mode == "queue_aware" and sname == "Round2Submission":
                    b2 = OverfittingDiagnostics.block_bootstrap_ci(
                        rets, block_size=100, n_bootstraps=1000, seed=42
                    )
                    oos_equity_curves[2] = np.concatenate([[0.0], np.cumsum(rets)])
                    overfit_rows.append(
                        [
                            2,
                            f"edge={x2},skew={y2}",
                            round(sr2_raw, 4),
                            round(locm2, 4),
                            round(locs2, 4),
                            round(pbo2, 4),
                            round(dsr2, 4),
                            round(pnl, 2),
                            round(sr, 4),
                        ]
                    )
                    for sym, val in ps.items():
                        bootstrap_rows.append(
                            [
                                2,
                                sym,
                                round(val, 2),
                                round(b2.sharpe_ci_low, 4),
                                round(b2.sharpe_ci_high, 4),
                                round(b2.pnl_ci_low, 2),
                                round(b2.pnl_ci_high, 2),
                            ]
                        )
                    print(
                        f"R2 OOS queue_aware Round2Submission: PnL={pnl:,.2f}, SR={sr:.3f}, "
                        f"BootSR_CI=[{b2.sharpe_ci_low:.3f}, {b2.sharpe_ci_high:.3f}], "
                        f"lat={lat:.4f}ms, sym={ps}"
                    )

    with (table_dir / "r2_ablation_summary.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(
            [
                "split",
                "fill_mode",
                "strategy",
                "total_pnl",
                "sharpe_252",
                "max_drawdown",
                "total_fills",
                "mean_latency_ms",
            ]
        )
        w.writerows(r2_ab_rows)

    # Round 2 MAF Arrival-Rate Valuation MC
    r2_mc_assets = [
        AssetScenarioConfig(
            symbol="ASH_COATED_OSMIUM",
            position_limit=80,
            process=OrnsteinUhlenbeckParams(
                mu=10001.0, theta=0.09, sigma=1.88, initial_price=10001.0
            ),
            book=BotBookConfig(half_spread_l1=8.0, depth_l1=20, step_l2=2, depth_l2=4),
            arrivals=TradeArrivalConfig(arrival_prob=0.08, min_size=1, max_size=12),
        ),
        AssetScenarioConfig(
            symbol="INTARIAN_PEPPER_ROOT",
            position_limit=80,
            process=RandomWalkParams(initial_price=12500.0, mu_drift=0.108, sigma=1.81),
            book=BotBookConfig(half_spread_l1=7.0, depth_l1=20, step_l2=2, depth_l2=4),
            arrivals=TradeArrivalConfig(arrival_prob=0.06, min_size=1, max_size=12),
        ),
    ]
    maf_rates = [0.04, 0.06, 0.08, 0.10, 0.12]
    maf_summaries = simulate_arrival_sensitivity(
        lambda: CompetitionStrategyAdapter(_load_trader(2), name="Round2Submission"),
        r2_mc_assets,
        arrival_rates=maf_rates,
        n_sessions=25,
        n_steps=1000,
        fill_mode="queue_aware",
        seed=102,
    )
    mc_rows: list[list[object]] = []
    with (table_dir / "r2_maf_sensitivity.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(
            [
                "arrival_rate",
                "mean_pnl",
                "std_pnl",
                "median_pnl",
                "var_95",
                "cvar_95",
                "prob_loss",
                "mean_sharpe",
            ]
        )
        for rate, ms in maf_summaries.items():
            w.writerow(
                [
                    rate,
                    round(ms.mean_pnl, 2),
                    round(ms.std_pnl, 2),
                    round(ms.median_pnl, 2),
                    round(ms.var_95, 2),
                    round(ms.cvar_95, 2),
                    round(ms.prob_loss, 4),
                    round(ms.mean_sharpe, 4),
                ]
            )
    r2_base_mc = maf_summaries[0.08]
    mc_rows.append(
        [
            2,
            "Round2Submission_BaselineFlow",
            round(r2_base_mc.mean_pnl, 2),
            round(r2_base_mc.std_pnl, 2),
            round(r2_base_mc.median_pnl, 2),
            round(r2_base_mc.var_95, 2),
            round(r2_base_mc.cvar_95, 2),
            round(r2_base_mc.prob_loss, 4),
            round(r2_base_mc.mean_sharpe, 4),
            round(r2_base_mc.worst_max_drawdown, 2),
        ]
    )
    r2_maf_mc = maf_summaries[0.10]
    mc_rows.append(
        [
            2,
            "Round2Submission_MAFPlus25",
            round(r2_maf_mc.mean_pnl, 2),
            round(r2_maf_mc.std_pnl, 2),
            round(r2_maf_mc.median_pnl, 2),
            round(r2_maf_mc.var_95, 2),
            round(r2_maf_mc.cvar_95, 2),
            round(r2_maf_mc.prob_loss, 4),
            round(r2_maf_mc.mean_sharpe, 4),
            round(r2_maf_mc.worst_max_drawdown, 2),
        ]
    )

    # ------------------------------------------------------------------
    # ROUND 3: IS (Day 0, 1) & OOS (Day 2)
    # ------------------------------------------------------------------
    print("\n=== Evaluating Round 3 (Spot +/-200, VEV +/-300) ===")
    lim3 = get_round_position_limits(3)
    r3_is = {
        d: build_snapshots_from_dataframes(
            loader.load_day_prices(3, d), loader.load_day_trades(3, d)
        )
        for d in (0, 1)
    }
    r3_oos = {
        2: build_snapshots_from_dataframes(
            loader.load_day_prices(3, 2), loader.load_day_trades(3, 2)
        ),
    }
    r3_edges = [1.5, 2.5, 3.5, 4.5]
    r3_skews = [0.02, 0.04, 0.07, 0.10]
    _r3_g, _, x3, y3, sr3_raw, locm3, locs3, pbo3, dsr3 = _evaluate_is_grid(
        3,
        r3_is,
        lim3,
        r3_edges,
        r3_skews,
        "mm_edge",
        "mm_skew",
        lambda e, k: ParameterizedR3R4Strategy(e, k, m67_bump=0.0),
        table_dir / "r3_sensitivity_grid.csv",
    )

    r3_ab_rows: list[list[object]] = []
    r3_oos_persym: dict[str, float] = {}
    for split, days_map in (("IS", r3_is), ("OOS", r3_oos)):
        for mode in modes:
            factories = [
                ("NoOpBaseline", lambda: NoOpBaselineStrategy()),
                (
                    "SymmetricSpotMM",
                    lambda: SymmetricMarketMaker(
                        [
                            MarketMakingConfig("HYDROGEL_PACK", position_limit=200, quote_size=30),
                            MarketMakingConfig(
                                "VELVETFRUIT_EXTRACT", position_limit=200, quote_size=25
                            ),
                        ]
                    ),
                ),
                ("OptionsVolatilityContract", lambda: OptionsVolatilityStrategy()),
                (
                    "Round3Submission",
                    lambda: CompetitionStrategyAdapter(_load_trader(3), name="Round3Submission"),
                ),
            ]
            for sname, fac in factories:
                pnl, sr, dd, nf, lat, rets, ps = _run_day_set(days_map, lim3, fac, fill_mode=mode)
                r3_ab_rows.append(
                    [
                        split,
                        mode,
                        sname,
                        round(pnl, 2),
                        round(sr, 4),
                        round(dd, 2),
                        nf,
                        round(lat, 4),
                    ]
                )
                if split == "OOS" and mode == "queue_aware" and sname == "Round3Submission":
                    b3 = OverfittingDiagnostics.block_bootstrap_ci(
                        rets, block_size=100, n_bootstraps=1000, seed=42
                    )
                    oos_equity_curves[3] = np.concatenate([[0.0], np.cumsum(rets)])
                    r3_oos_persym = ps
                    overfit_rows.append(
                        [
                            3,
                            f"edge={x3},skew={y3}",
                            round(sr3_raw, 4),
                            round(locm3, 4),
                            round(locs3, 4),
                            round(pbo3, 4),
                            round(dsr3, 4),
                            round(pnl, 2),
                            round(sr, 4),
                        ]
                    )
                    for sym, val in ps.items():
                        bootstrap_rows.append(
                            [
                                3,
                                sym,
                                round(val, 2),
                                round(b3.sharpe_ci_low, 4),
                                round(b3.sharpe_ci_high, 4),
                                round(b3.pnl_ci_low, 2),
                                round(b3.pnl_ci_high, 2),
                            ]
                        )
                    print(
                        f"R3 OOS queue_aware Round3Submission: PnL={pnl:,.2f}, SR={sr:.3f}, "
                        f"BootSR_CI=[{b3.sharpe_ci_low:.3f}, {b3.sharpe_ci_high:.3f}], "
                        f"lat={lat:.4f}ms"
                    )

    with (table_dir / "r3_ablation_summary.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(
            [
                "split",
                "fill_mode",
                "strategy",
                "total_pnl",
                "sharpe_252",
                "max_drawdown",
                "total_fills",
                "mean_latency_ms",
            ]
        )
        w.writerows(r3_ab_rows)

    # ------------------------------------------------------------------
    # ROUND 4: IS (Day 1, 2) & OOS (Day 3)
    # ------------------------------------------------------------------
    print("\n=== Evaluating Round 4 (Counterparty Flow Intelligence) ===")
    r4_is = {
        d: build_snapshots_from_dataframes(
            loader.load_day_prices(4, d), loader.load_day_trades(4, d)
        )
        for d in (1, 2)
    }
    r4_oos = {
        3: build_snapshots_from_dataframes(
            loader.load_day_prices(4, 3), loader.load_day_trades(4, 3)
        ),
    }
    r4_bumps = [0.5, 1.0, 1.5, 2.0]
    r4_edges = [2.5, 3.5, 4.5, 5.5]
    _r4_g, _, x4, y4, sr4_raw, locm4, locs4, pbo4, dsr4 = _evaluate_is_grid(
        4,
        r4_is,
        lim3,
        r4_bumps,
        r4_edges,
        "m67_bump",
        "mm_edge",
        lambda b, e: ParameterizedR3R4Strategy(mm_edge=e, mm_skew=0.08, m67_bump=b),
        table_dir / "r4_sensitivity_grid.csv",
    )

    r4_ab_rows: list[list[object]] = []
    r4_oos_persym: dict[str, float] = {}
    for split, days_map in (("IS", r4_is), ("OOS", r4_oos)):
        for mode in modes:
            factories = [
                ("NoOpBaseline", lambda: NoOpBaselineStrategy()),
                (
                    "Round3Ungated",
                    lambda: CompetitionStrategyAdapter(_load_trader(3), name="Round3Ungated"),
                ),
                (
                    "Round4Submission",
                    lambda: CompetitionStrategyAdapter(_load_trader(4), name="Round4Submission"),
                ),
            ]
            for sname, fac in factories:
                pnl, sr, dd, nf, lat, rets, ps = _run_day_set(days_map, lim3, fac, fill_mode=mode)
                r4_ab_rows.append(
                    [
                        split,
                        mode,
                        sname,
                        round(pnl, 2),
                        round(sr, 4),
                        round(dd, 2),
                        nf,
                        round(lat, 4),
                    ]
                )
                if split == "OOS" and mode == "queue_aware" and sname == "Round4Submission":
                    b4 = OverfittingDiagnostics.block_bootstrap_ci(
                        rets, block_size=100, n_bootstraps=1000, seed=42
                    )
                    oos_equity_curves[4] = np.concatenate([[0.0], np.cumsum(rets)])
                    r4_oos_persym = ps
                    overfit_rows.append(
                        [
                            4,
                            f"m67={x4},edge={y4}",
                            round(sr4_raw, 4),
                            round(locm4, 4),
                            round(locs4, 4),
                            round(pbo4, 4),
                            round(dsr4, 4),
                            round(pnl, 2),
                            round(sr, 4),
                        ]
                    )
                    for sym, val in ps.items():
                        bootstrap_rows.append(
                            [
                                4,
                                sym,
                                round(val, 2),
                                round(b4.sharpe_ci_low, 4),
                                round(b4.sharpe_ci_high, 4),
                                round(b4.pnl_ci_low, 2),
                                round(b4.pnl_ci_high, 2),
                            ]
                        )
                    print(
                        f"R4 OOS queue_aware Round4Submission: PnL={pnl:,.2f}, SR={sr:.3f}, "
                        f"BootSR_CI=[{b4.sharpe_ci_low:.3f}, {b4.sharpe_ci_high:.3f}], "
                        f"lat={lat:.4f}ms"
                    )

    with (table_dir / "r4_ablation_summary.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(
            [
                "split",
                "fill_mode",
                "strategy",
                "total_pnl",
                "sharpe_252",
                "max_drawdown",
                "total_fills",
                "mean_latency_ms",
            ]
        )
        w.writerows(r4_ab_rows)

    # Coupled Options + Spot Monte Carlo (Rounds 3 & 4)
    coupled_mc = CoupledOptionsMonteCarloEngine(
        OptionsSpotScenarioConfig(), fill_mode="queue_aware"
    )
    r3_mc = coupled_mc.run(
        lambda: CompetitionStrategyAdapter(_load_trader(3), name="Round3Submission"),
        n_sessions=25,
        n_steps=1000,
        seed=303,
    )
    r4_mc = coupled_mc.run(
        lambda: CompetitionStrategyAdapter(_load_trader(4), name="Round4Submission"),
        n_sessions=25,
        n_steps=1000,
        seed=404,
    )
    mc_rows.append(
        [
            3,
            "Round3Submission",
            round(r3_mc.mean_pnl, 2),
            round(r3_mc.std_pnl, 2),
            round(r3_mc.median_pnl, 2),
            round(r3_mc.var_95, 2),
            round(r3_mc.cvar_95, 2),
            round(r3_mc.prob_loss, 4),
            round(r3_mc.mean_sharpe, 4),
            round(r3_mc.worst_max_drawdown, 2),
        ]
    )
    mc_rows.append(
        [
            4,
            "Round4Submission",
            round(r4_mc.mean_pnl, 2),
            round(r4_mc.std_pnl, 2),
            round(r4_mc.median_pnl, 2),
            round(r4_mc.var_95, 2),
            round(r4_mc.cvar_95, 2),
            round(r4_mc.prob_loss, 4),
            round(r4_mc.mean_sharpe, 4),
            round(r4_mc.worst_max_drawdown, 2),
        ]
    )

    # ------------------------------------------------------------------
    # ROUND 5: IS (Day 2, 3) & OOS (Day 4) across 50 products (+/-10)
    # ------------------------------------------------------------------
    print("\n=== Evaluating Round 5 (50 Assets, +/-10 limits) ===")
    lim5 = get_round_position_limits(5)
    r5_is = {
        d: build_snapshots_from_dataframes(
            loader.load_day_prices(5, d), loader.load_day_trades(5, d)
        )
        for d in (2, 3)
    }
    r5_oos = {
        4: build_snapshots_from_dataframes(
            loader.load_day_prices(5, 4), loader.load_day_trades(5, 4)
        ),
    }
    r5_ef = [0.18, 0.22, 0.26, 0.30]
    r5_sk = [0.65, 0.85, 1.05, 1.25]
    r5_grid, _, x5, y5, sr5_raw, locm5, locs5, pbo5, dsr5 = _evaluate_is_grid(
        5,
        r5_is,
        lim5,
        r5_ef,
        r5_sk,
        "edge_frac",
        "inventory_skew",
        lambda ef, sk: ParameterizedR5Strategy(edge_frac=ef, skew=sk),
        table_dir / "r5_sensitivity_grid.csv",
    )

    r5_ab_rows: list[list[object]] = []
    r5_oos_cat_sub: dict[str, float] = {}
    r5_oos_cat_all50: dict[str, float] = {}
    r5_cfgs_all = [
        MarketMakingConfig(symbol=sym, position_limit=10, quote_size=10)
        for sym in get_round_products(5)
    ]

    for split, days_map in (("IS", r5_is), ("OOS", r5_oos)):
        for mode in modes:
            factories = [
                ("NoOpBaseline", lambda: NoOpBaselineStrategy()),
                ("EmaSymmetricMM_All50", lambda: SymmetricMarketMaker(r5_cfgs_all)),
                (
                    "LagFreeMM_All50_NoBaskets",
                    lambda: ParameterizedR5Strategy(
                        0.18,
                        1.25,
                        skip_low_ratio=False,
                        use_baskets=False,
                        vol_guard=False,
                        clip=10,
                        name="LagFreeAll50",
                    ),
                ),
                (
                    "Round5Submission",
                    lambda: CompetitionStrategyAdapter(_load_trader(5), name="Round5Submission"),
                ),
            ]
            for sname, fac in factories:
                pnl, sr, dd, nf, lat, rets, ps = _run_day_set(days_map, lim5, fac, fill_mode=mode)
                r5_ab_rows.append(
                    [
                        split,
                        mode,
                        sname,
                        round(pnl, 2),
                        round(sr, 4),
                        round(dd, 2),
                        nf,
                        round(lat, 4),
                    ]
                )
                if split == "OOS" and mode == "queue_aware":
                    if sname == "LagFreeMM_All50_NoBaskets":
                        r5_oos_cat_all50 = {
                            cat: sum(ps.get(s, 0.0) for s in syms)
                            for cat, syms in PROSPERITY4_R5_CATEGORIES.items()
                        }
                    elif sname == "Round5Submission":
                        b5 = OverfittingDiagnostics.block_bootstrap_ci(
                            rets, block_size=100, n_bootstraps=1000, seed=42
                        )
                        oos_equity_curves[5] = np.concatenate([[0.0], np.cumsum(rets)])
                        r5_oos_cat_sub = {
                            cat: sum(ps.get(s, 0.0) for s in syms)
                            for cat, syms in PROSPERITY4_R5_CATEGORIES.items()
                        }
                        overfit_rows.append(
                            [
                                5,
                                f"ef={x5},sk={y5}",
                                round(sr5_raw, 4),
                                round(locm5, 4),
                                round(locs5, 4),
                                round(pbo5, 4),
                                round(dsr5, 4),
                                round(pnl, 2),
                                round(sr, 4),
                            ]
                        )
                        for cat, val in r5_oos_cat_sub.items():
                            bootstrap_rows.append(
                                [
                                    5,
                                    f"Category:{cat}",
                                    round(val, 2),
                                    round(b5.sharpe_ci_low, 4),
                                    round(b5.sharpe_ci_high, 4),
                                    round(b5.pnl_ci_low, 2),
                                    round(b5.pnl_ci_high, 2),
                                ]
                            )
                        print(
                            f"R5 OOS queue_aware Round5Submission: PnL={pnl:,.2f}, SR={sr:.3f}, "
                            f"BootSR_CI=[{b5.sharpe_ci_low:.3f}, {b5.sharpe_ci_high:.3f}], "
                            f"lat={lat:.4f}ms"
                        )

    with (table_dir / "r5_ablation_summary.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(
            [
                "split",
                "fill_mode",
                "strategy",
                "total_pnl",
                "sharpe_252",
                "max_drawdown",
                "total_fills",
                "mean_latency_ms",
            ]
        )
        w.writerows(r5_ab_rows)

    # Round 5 Two-Layer Joint MC
    r5_mc_engine = Round5JointMonteCarloEngine(fill_mode="queue_aware")
    r5_mc = r5_mc_engine.run(
        lambda: CompetitionStrategyAdapter(_load_trader(5), name="Round5Submission"),
        n_sessions=20,
        n_steps=1000,
        seed=505,
    )
    mc_rows.append(
        [
            5,
            "Round5Submission_JointMC",
            round(r5_mc.mean_pnl, 2),
            round(r5_mc.std_pnl, 2),
            round(r5_mc.median_pnl, 2),
            round(r5_mc.var_95, 2),
            round(r5_mc.cvar_95, 2),
            round(r5_mc.prob_loss, 4),
            round(r5_mc.mean_sharpe, 4),
            round(r5_mc.worst_max_drawdown, 2),
        ]
    )

    with (table_dir / "r2_to_r5_overfitting_gates.csv").open(
        "w", newline="", encoding="utf-8"
    ) as fh:
        w = csv.writer(fh)
        w.writerow(
            [
                "round",
                "plateau_params",
                "is_sharpe_252",
                "local_mean",
                "local_std",
                "cscv_pbo",
                "dsr",
                "oos_pnl",
                "oos_sharpe_252",
            ]
        )
        w.writerows(overfit_rows)

    with (table_dir / "r2_to_r5_bootstrap_and_attribution.csv").open(
        "w", newline="", encoding="utf-8"
    ) as fh:
        w = csv.writer(fh)
        w.writerow(
            [
                "round",
                "bucket",
                "oos_pnl",
                "boot_sr252_lo",
                "boot_sr252_hi",
                "boot_pnl_lo",
                "boot_pnl_hi",
            ]
        )
        w.writerows(bootstrap_rows)

    with (table_dir / "r2_to_r5_mc_risk_summary.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(
            [
                "round",
                "scenario",
                "mean_pnl",
                "std_pnl",
                "median_pnl",
                "var_95",
                "cvar_95",
                "prob_loss",
                "mean_sharpe_252",
                "worst_max_dd",
            ]
        )
        w.writerows(mc_rows)

    # ------------------------------------------------------------------
    # DIAGNOSTIC FIGURES (reports/figures/)
    # ------------------------------------------------------------------
    # Fig 1: R2 sensitivity heatmap & MAF valuation curve
    fig, axes = plt.subplots(1, 2, figsize=(13.0, 4.8))
    im = axes[0].imshow(r2_grid, cmap="viridis", aspect="auto")
    axes[0].set_xticks(range(len(r2_skews)), labels=[f"{s:.2f}" for s in r2_skews])
    axes[0].set_yticks(range(len(r2_edges)), labels=[f"{e:.1f}" for e in r2_edges])
    axes[0].set_xlabel("Inventory Skew Factor")
    axes[0].set_ylabel("Minimum Edge Floor (ticks)")
    axes[0].set_title(f"R2 IS Sharpe Surface (PBO={pbo2:.3f}, DSR={dsr2:.4f})")
    for i in range(len(r2_edges)):
        for j in range(len(r2_skews)):
            axes[0].text(
                j, i, f"{r2_grid[i, j]:.2f}", ha="center", va="center", color="white", fontsize=8
            )
    fig.colorbar(im, ax=axes[0], label="Sharpe (sqrt 252)")

    maf_means = [maf_summaries[r].mean_pnl for r in maf_rates]
    maf_stds = [maf_summaries[r].std_pnl for r in maf_rates]
    axes[1].errorbar(
        maf_rates, maf_means, yerr=maf_stds, marker="o", linewidth=2.2, color="#2a9d8f", capsize=4
    )
    axes[1].axvspan(0.08, 0.10, color="#e9c46a", alpha=0.25, label="Baseline -> +25% MAF Boost")
    axes[1].set_title("Round 2 MC PnL vs. Counterparty Arrival Rate (1,000 steps)")
    axes[1].set_xlabel("Arrival Rate per Step")
    axes[1].set_ylabel("Mean Session PnL (+/- 1 SD)")
    axes[1].grid(True, linestyle="--", alpha=0.4)
    axes[1].legend()
    fig.tight_layout()
    fig.savefig(fig_dir / "r2_sensitivity_and_maf_valuation.png", dpi=200)
    plt.close(fig)

    # Fig 2: R3 & R4 OOS asset attribution + Coupled MC PnL distributions
    fig, axes = plt.subplots(1, 2, figsize=(13.5, 4.8))
    syms34 = [
        "HYDROGEL_PACK",
        "VELVETFRUIT_EXTRACT",
        "VEV_4000",
        "VEV_4500",
        "VEV_5200",
        "VEV_5300",
    ]
    vals3 = [r3_oos_persym.get(s, 0.0) for s in syms34]
    vals4 = [r4_oos_persym.get(s, 0.0) for s in syms34]
    xpos = np.arange(len(syms34))
    axes[0].bar(xpos - 0.18, vals3, width=0.36, label="R3 OOS (Day 2)", color="#264653")
    axes[0].bar(xpos + 0.18, vals4, width=0.36, label="R4 OOS (Day 3)", color="#e76f51")
    axes[0].set_xticks(
        xpos, labels=["HYDRO", "VELVET", "VEV4k", "VEV4.5k", "VEV5.2k", "VEV5.3k"], rotation=20
    )
    axes[0].set_title("Round 3 & 4 OOS Per-Asset Attribution (Queue-Aware)")
    axes[0].set_ylabel("OOS PnL (XIRECs)")
    axes[0].grid(True, axis="y", linestyle="--", alpha=0.4)
    axes[0].legend()

    axes[1].hist(
        r3_mc.pnl_distribution,
        bins=12,
        alpha=0.6,
        color="#264653",
        label=f"R3 MC (Mean={r3_mc.mean_pnl:.0f})",
    )
    axes[1].hist(
        r4_mc.pnl_distribution,
        bins=12,
        alpha=0.6,
        color="#e76f51",
        label=f"R4 MC (Mean={r4_mc.mean_pnl:.0f})",
    )
    axes[1].set_title("Coupled Spot+Options MC PnL Distribution (N=25, 1k steps)")
    axes[1].set_xlabel("Session PnL (XIRECs)")
    axes[1].set_ylabel("Session Count")
    axes[1].grid(True, linestyle="--", alpha=0.4)
    axes[1].legend()
    fig.tight_layout()
    fig.savefig(fig_dir / "r3_r4_oos_attribution_and_mc.png", dpi=200)
    plt.close(fig)

    # Fig 3: R5 IS Sharpe heatmap + Category OOS PnL (Submitted Tiered vs Unfiltered All-50)
    fig, axes = plt.subplots(1, 2, figsize=(14.0, 5.2))
    im5 = axes[0].imshow(r5_grid, cmap="viridis", aspect="auto")
    axes[0].set_xticks(range(len(r5_sk)), labels=[f"{s:.2f}" for s in r5_sk])
    axes[0].set_yticks(range(len(r5_ef)), labels=[f"{e:.2f}" for e in r5_ef])
    axes[0].set_xlabel("Inventory Skew Factor")
    axes[0].set_ylabel("Spread Edge Fraction")
    axes[0].set_title(f"R5 IS Sharpe Surface (PBO={pbo5:.3f}, DSR={dsr5:.4f})")
    for i in range(len(r5_ef)):
        for j in range(len(r5_sk)):
            axes[0].text(
                j, i, f"{r5_grid[i, j]:.2f}", ha="center", va="center", color="white", fontsize=8
            )
    fig.colorbar(im5, ax=axes[0], label="Sharpe (sqrt 252)")

    cats = list(PROSPERITY4_R5_CATEGORIES.keys())
    c_xpos = np.arange(len(cats))
    axes[1].bar(
        c_xpos - 0.18,
        [r5_oos_cat_all50.get(c, 0.0) for c in cats],
        width=0.36,
        color="#8d99ae",
        label="All-50 Unfiltered (No Baskets)",
    )
    axes[1].bar(
        c_xpos + 0.18,
        [r5_oos_cat_sub.get(c, 0.0) for c in cats],
        width=0.36,
        color="#2a9d8f",
        label="Round5Submission (Tiered+Baskets)",
    )
    axes[1].axhline(0.0, color="black", linewidth=0.9)
    axes[1].set_xticks(c_xpos, labels=cats, rotation=30, ha="right")
    axes[1].set_title("Round 5 Held-Out OOS (Day 4) PnL by Category")
    axes[1].set_ylabel("OOS PnL (XIRECs)")
    axes[1].grid(True, axis="y", linestyle="--", alpha=0.4)
    axes[1].legend()
    fig.tight_layout()
    fig.savefig(fig_dir / "r5_sensitivity_and_category_oos.png", dpi=200)
    plt.close(fig)

    # Fig 4: Multi-Round Normalized OOS Equity Curves (XIREC equity trajectories)
    fig, axes = plt.subplots(2, 2, figsize=(12.5, 8.0))
    colors = {2: "#1d3557", 3: "#2a9d8f", 4: "#e76f51", 5: "#6a4c93"}
    titles = {
        2: "Round 2 OOS (Day 1, +/-80)",
        3: "Round 3 OOS (Day 2, Options+Spot)",
        4: "Round 4 OOS (Day 3, Counterparty+Options)",
        5: "Round 5 OOS (Day 4, 50 Assets +/-10)",
    }
    for idx_r, rnum in enumerate((2, 3, 4, 5)):
        ax = axes[idx_r // 2, idx_r % 2]
        eq = oos_equity_curves[rnum]
        ax.plot(eq, color=colors[rnum], linewidth=1.8)
        ax.set_title(f"{titles[rnum]} | End PnL={eq[-1]:,.0f}")
        ax.set_xlabel("Tick Index (Day OOS)")
        ax.set_ylabel("Cumulative Equity (XIRECs)")
        ax.grid(True, linestyle="--", alpha=0.4)
    fig.tight_layout()
    fig.savefig(fig_dir / "r2_to_r5_oos_equity_summary.png", dpi=200)
    plt.close(fig)

    print("\nCompleted all Round 2-5 tables and figures cleanly.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
