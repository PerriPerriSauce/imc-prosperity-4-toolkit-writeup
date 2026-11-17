"""Stage 6 Parameter Sensitivity, CSCV/PBO, and DSR Validation on Round 1 IS Data."""

from __future__ import annotations

import math

import numpy as np

from prosperity_toolkit.analysis.diagnostics import OverfittingDiagnostics
from prosperity_toolkit.backtesting.engine import BacktestEngine
from prosperity_toolkit.backtesting.replay import build_snapshots_from_dataframes
from prosperity_toolkit.core.models import OrderRequest, Symbol
from prosperity_toolkit.data.loader import DataLoader
from prosperity_toolkit.execution.simulator import ExecutionSimulator, FillMode
from prosperity_toolkit.market.market_state import MarketStateSnapshot
from prosperity_toolkit.market.order_book import OrderBookL2
from prosperity_toolkit.optimisation.sensitivity import SensitivityAnalyzer
from prosperity_toolkit.strategies.base import BaseStrategy


def _popular_wall_mid(book: OrderBookL2) -> float | None:
    """Estimate fair value from max-volume resting bot walls (filtering thin inside noise)."""
    if not book.bids or not book.asks:
        return None
    wall_bid = max(book.bids.items(), key=lambda kv: (abs(kv[1]), kv[0]))[0]
    wall_ask = max(book.asks.items(), key=lambda kv: (abs(kv[1]), -kv[0]))[0]
    return float((wall_bid + wall_ask) / 2.0)


class ParameterizedRound1Strategy(BaseStrategy):
    """Refined Round 1 strategy with bot-wall FV, penny-joining, and inventory skew."""

    def __init__(
        self,
        min_edge: float = 1.5,
        inventory_skew: float = 0.25,
        position_limit: int = 20,
    ) -> None:
        super().__init__(name=f"RefinedR1(edge={min_edge},skew={inventory_skew})")
        self.min_edge = min_edge
        self.inventory_skew = inventory_skew
        self.position_limit = position_limit
        self._fv: dict[Symbol, float] = {}
        self._drift: dict[Symbol, float] = {}
        self._last_ts: dict[Symbol, int] = {}

    def _update_fv(self, sym: Symbol, state: MarketStateSnapshot) -> float | None:
        book = state.get_book(sym)
        if book is None:
            return self._fv.get(sym)

        obs = _popular_wall_mid(book)
        if sym == "ASH_COATED_OSMIUM":
            if obs is not None:
                prev = self._fv.get(sym, obs)
                self._fv[sym] = 0.25 * obs + 0.75 * prev
            return self._fv.get(sym)

        # INTARIAN_PEPPER_ROOT: alpha-beta drift filter on structural wall mid
        last_ts = self._last_ts.get(sym, state.timestamp)
        dt_steps = (
            max(1.0, (state.timestamp - last_ts) / 100.0)
            if state.timestamp > last_ts
            else 1.0
        )
        if obs is not None:
            if sym not in self._fv:
                self._fv[sym] = obs
                self._drift[sym] = 0.0
            else:
                pred = self._fv[sym] + self._drift[sym] * dt_steps
                innov = obs - pred
                self._fv[sym] = pred + 0.25 * innov
                self._drift[sym] += 0.01 * (innov / dt_steps)
            self._last_ts[sym] = state.timestamp
            return self._fv[sym]

        if sym in self._fv:
            self._fv[sym] += self._drift.get(sym, 0.0) * dt_steps
            self._last_ts[sym] = state.timestamp
            return self._fv[sym]
        return None

    def generate_orders(self, state: MarketStateSnapshot) -> list[OrderRequest]:
        """Take mispriced liquidity, clear excess inventory, and penny-improve bot quotes."""
        orders: list[OrderRequest] = []
        for sym in ("ASH_COATED_OSMIUM", "INTARIAN_PEPPER_ROOT"):
            book = state.get_book(sym)
            if book is None:
                continue
            fv = self._update_fv(sym, state)
            if fv is None:
                continue

            start_pos = state.get_position(sym)
            buy_cap = max(0, self.position_limit - start_pos)
            sell_cap = max(0, self.position_limit + start_pos)
            taken_buy = 0
            taken_sell = 0

            # 1. Taker leg against mispriced quotes
            for ask_px in sorted(book.asks.keys()):
                if ask_px > fv - 1.0 or buy_cap - taken_buy <= 0:
                    break
                qty = min(abs(book.asks[ask_px]), buy_cap - taken_buy)
                if qty > 0:
                    orders.append(OrderRequest(symbol=sym, price=ask_px, quantity=qty))
                    taken_buy += qty

            for bid_px in sorted(book.bids.keys(), reverse=True):
                if bid_px < fv + 1.0 or sell_cap - taken_sell <= 0:
                    break
                qty = min(abs(book.bids[bid_px]), sell_cap - taken_sell)
                if qty > 0:
                    orders.append(OrderRequest(symbol=sym, price=bid_px, quantity=-qty))
                    taken_sell += qty

            # 2. Reservation price + penny-joining inside wide spreads
            rem_buy = max(0, buy_cap - taken_buy)
            rem_sell = max(0, sell_cap - taken_sell)
            reservation = fv - self.inventory_skew * start_pos

            max_bid = math.floor(reservation - self.min_edge)
            min_ask = math.ceil(reservation + self.min_edge)

            # Penny-improve the resting bot wall when spread is wide, without crossing min_edge
            quote_bid = min(max_bid, book.best_bid + 1) if book.best_bid is not None else max_bid
            quote_ask = max(min_ask, book.best_ask - 1) if book.best_ask is not None else min_ask

            if book.best_ask is not None and quote_bid >= book.best_ask:
                quote_bid = book.best_ask - 1
            if book.best_bid is not None and quote_ask <= book.best_bid:
                quote_ask = book.best_bid + 1

            if quote_bid >= quote_ask or quote_bid <= 0:
                continue

            if rem_buy > 0:
                orders.append(OrderRequest(symbol=sym, price=quote_bid, quantity=min(5, rem_buy)))
            if rem_sell > 0:
                orders.append(OrderRequest(symbol=sym, price=quote_ask, quantity=-min(5, rem_sell)))

        return orders


def main() -> int:
    """Run IS 2D sensitivity sweep, CSCV/PBO, DSR, and single-pass OOS check."""
    loader = DataLoader()
    limits = {"ASH_COATED_OSMIUM": 20, "INTARIAN_PEPPER_ROOT": 20}

    # Strict In-Sample concatenation: Day -2 followed by Day -1
    is_snapshots = []
    for day in (-2, -1):
        p_df = loader.load_day_prices(1, day)
        t_df = loader.load_day_trades(1, day)
        is_snapshots.extend(build_snapshots_from_dataframes(p_df, t_df))

    edges = [1.0, 1.5, 2.0, 2.5, 3.0]
    skews = [0.10, 0.25, 0.40, 0.60, 0.80]

    sharpe_grid = np.zeros((len(edges), len(skews)), dtype=np.float64)
    pnl_grid = np.zeros((len(edges), len(skews)), dtype=np.float64)
    returns_cols: list[np.ndarray] = []
    trial_sharpes: list[float] = []

    print("=== In-Sample 2D Sensitivity Sweep (Round 1 Day -2 & Day -1, queue_aware) ===")
    for i, edge in enumerate(edges):
        for j, skew in enumerate(skews):
            sim = ExecutionSimulator(position_limits=limits, fill_mode="queue_aware")
            engine = BacktestEngine(simulator=sim)
            strat = ParameterizedRound1Strategy(min_edge=edge, inventory_skew=skew)
            res = engine.run(strat, is_snapshots)
            eq = np.asarray(res.equity_curve, dtype=np.float64)
            rets = np.diff(eq)
            sr = float(np.mean(rets) / np.std(rets, ddof=1)) if np.std(rets, ddof=1) > 0 else 0.0

            sharpe_grid[i, j] = res.sharpe_ratio
            pnl_grid[i, j] = res.total_pnl
            returns_cols.append(rets)
            trial_sharpes.append(sr)

    print("\nIn-Sample Annualized Sharpe Grid (rows=min_edge, cols=inventory_skew):")
    header = "edge\\skew | " + " | ".join(f"{s:>6.2f}" for s in skews)
    print(header)
    for i, edge in enumerate(edges):
        row_str = " | ".join(f"{sharpe_grid[i, j]:>6.3f}" for j in range(len(skews)))
        print(f"{edge:>9.1f} | {row_str}")

    plateau = SensitivityAnalyzer.select_stable_plateau_2d(
        edges,
        skews,
        sharpe_grid,
        std_penalty=1.0,
    )
    print(
        f"\nSelected Stable Plateau: min_edge={plateau.x_value}, inventory_skew={plateau.y_value} "
        f"(raw_sharpe={plateau.raw_score:.3f}, local_mean={plateau.local_mean:.3f}, "
        f"local_std={plateau.local_std:.3f}, max_neighbor_drop={plateau.max_neighbor_drop:.3f})",
    )

    mat = np.column_stack(returns_cols)
    cscv = OverfittingDiagnostics.compute_cscv_pbo(mat, n_slices=8)
    selected_idx = plateau.x_index * len(skews) + plateau.y_index
    dsr = OverfittingDiagnostics.evaluate_trial_dsr(mat[:, selected_idx], trial_sharpes)

    print(
        f"CSCV PBO: pbo={cscv.pbo:.3f} (passes <0.15: {cscv.passes_pbo_threshold}), "
        f"prob_oos_neg={cscv.prob_oos_negative:.3f}, "
        f"mean_IS_SR={cscv.mean_is_best_sharpe:.4f}, "
        f"mean_OOS_SR={cscv.mean_oos_selected_sharpe:.4f}",
    )
    print(
        f"DSR (25 trials): obs_sr={dsr.observed_sharpe:.4f}, sr*={dsr.expected_max_sharpe:.4f}, "
        f"DSR={dsr.deflated_sharpe_ratio:.4f} (passes >=0.95: {dsr.passes_95pct})",
    )

    # Single-pass OOS check on Day 0
    p0 = loader.load_day_prices(1, 0)
    t0 = loader.load_day_trades(1, 0)
    oos_snaps = build_snapshots_from_dataframes(p0, t0)
    modes: tuple[FillMode, ...] = ("conservative", "queue_aware", "touch")
    for mode in modes:
        sim = ExecutionSimulator(position_limits=limits, fill_mode=mode)
        res = BacktestEngine(simulator=sim).run(
            ParameterizedRound1Strategy(min_edge=plateau.x_value, inventory_skew=plateau.y_value),
            oos_snaps,
        )
        print(
            f"OOS Day 0 ({mode:<12}): PnL={res.total_pnl:>9.2f}, "
            f"MaxDD={res.max_drawdown:>7.2f}, Sharpe={res.sharpe_ratio:.3f}, "
            f"Fills={len(res.fills)}",
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
