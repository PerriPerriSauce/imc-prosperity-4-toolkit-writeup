"""In-sample 2D sensitivity analysis, CSCV/PBO, DSR, and single-pass OOS check for Round 1."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

from prosperity_toolkit.analysis.diagnostics import OverfittingDiagnostics
from prosperity_toolkit.backtesting.engine import BacktestEngine
from prosperity_toolkit.backtesting.metrics import PerformanceMetrics
from prosperity_toolkit.backtesting.replay import build_snapshots_from_dataframes
from prosperity_toolkit.competition.adapter import CompetitionStrategyAdapter
from prosperity_toolkit.competition.specifications import get_round_position_limits
from prosperity_toolkit.data.loader import DataLoader
from prosperity_toolkit.execution.simulator import ExecutionSimulator, FillMode
from prosperity_toolkit.market.market_state import MarketStateSnapshot
from prosperity_toolkit.optimisation.sensitivity import SensitivityAnalyzer


def main() -> int:
    """Run independent-day IS 2D sweep, CSCV/PBO, block DSR, and single-pass OOS check."""
    repo_root = str(Path(__file__).resolve().parents[1])
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

    from scripts.evaluate_round0_round1 import _load_round1_trader

    loader = DataLoader()
    limits = get_round_position_limits(1)

    is_days: dict[int, list[MarketStateSnapshot]] = {
        day: build_snapshots_from_dataframes(
            loader.load_day_prices(1, day),
            loader.load_day_trades(1, day),
        )
        for day in (-2, -1)
    }

    edges = [1.5, 2.0, 2.5, 3.0, 3.5]
    skews = [0.10, 0.25, 0.40, 0.55, 0.70]

    ir_grid = np.zeros((len(edges), len(skews)), dtype=np.float64)
    pnl_grid = np.zeros((len(edges), len(skews)), dtype=np.float64)
    returns_cols: list[np.ndarray] = []

    print("=== In-Sample 2D Sweep (Round 1 Day -2 & Day -1 independent, queue_aware, +/-80) ===")
    for i, edge in enumerate(edges):
        for j, skew in enumerate(skews):
            day_rets: list[np.ndarray] = []
            tot_pnl = 0.0
            for snaps in is_days.values():
                sim = ExecutionSimulator(position_limits=limits, fill_mode="queue_aware")
                trader = _load_round1_trader(min_edge=edge, inventory_skew=skew)
                strat = CompetitionStrategyAdapter(
                    trader,
                    name=f"R1(e={edge},k={skew})",
                )
                res = BacktestEngine(simulator=sim).run(strat, snaps)
                tot_pnl += res.total_pnl
                day_rets.append(np.diff(np.asarray(res.equity_curve, dtype=np.float64)))
            rets = np.concatenate(day_rets)
            ir = PerformanceMetrics.calculate_sharpe_ratio(rets.tolist(), annualization_factor=1.0)
            ir_grid[i, j] = ir
            pnl_grid[i, j] = tot_pnl
            returns_cols.append(rets)

    print("\nIn-Sample Tick Information Ratio (IR_tick, rows=min_edge, cols=inventory_skew):")
    header = "edge\\skew | " + " | ".join(f"{s:>6.2f}" for s in skews)
    print(header)
    for i, edge in enumerate(edges):
        row_str = " | ".join(f"{ir_grid[i, j]:>6.4f}" for j in range(len(skews)))
        print(f"{edge:>9.1f} | {row_str}")

    plateau = SensitivityAnalyzer.select_stable_plateau_2d(
        edges,
        skews,
        ir_grid,
        std_penalty=1.0,
        require_interior=True,
    )
    print(
        f"\nSelected Interior Plateau: min_edge={plateau.x_value}, "
        f"inventory_skew={plateau.y_value} (raw_IR={plateau.raw_score:.5f}, "
        f"local_mean={plateau.local_mean:.5f}, local_std={plateau.local_std:.5f}, "
        f"max_drop={plateau.max_neighbor_drop:.5f})",
    )

    mat = np.column_stack(returns_cols)
    cscv = OverfittingDiagnostics.compute_cscv_pbo(mat, n_slices=8)
    selected_idx = plateau.x_index * len(skews) + plateau.y_index
    dsr, n_eff = OverfittingDiagnostics.evaluate_block_matrix_dsr(
        mat,
        selected_idx,
        block_size=100,
    )

    print(
        f"CSCV PBO (100-tick slices/blocks): pbo={cscv.pbo:.3f} "
        f"(passes <0.15: {cscv.passes_pbo_threshold}), prob_oos_neg={cscv.prob_oos_negative:.3f}, "
        f"mean_IS_SR={cscv.mean_is_best_sharpe:.4f}, "
        f"mean_OOS_SR={cscv.mean_oos_selected_sharpe:.4f}",
    )
    print(
        f"Block DSR (100-tick blocks, N_eff={n_eff:.2f} / 25 trials): "
        f"obs_sr={dsr.observed_sharpe:.4f}, sr*={dsr.expected_max_sharpe:.4f}, "
        f"DSR={dsr.deflated_sharpe_ratio:.4f} (passes >=0.95: {dsr.passes_95pct})",
    )

    oos_snaps = build_snapshots_from_dataframes(
        loader.load_day_prices(1, 0),
        loader.load_day_trades(1, 0),
    )
    modes: tuple[FillMode, ...] = ("conservative", "queue_aware", "touch")
    for mode in modes:
        sim = ExecutionSimulator(position_limits=limits, fill_mode=mode)
        trader = _load_round1_trader(min_edge=plateau.x_value, inventory_skew=plateau.y_value)
        strat = CompetitionStrategyAdapter(trader, name="Round1Submission")
        res = BacktestEngine(simulator=sim).run(strat, oos_snaps)
        rets_oos = np.diff(np.asarray(res.equity_curve, dtype=np.float64)).tolist()
        blk_sr = PerformanceMetrics.calculate_block_sharpe(rets_oos, block_size=1000)
        p2dd = PerformanceMetrics.calculate_pnl_to_drawdown(res.total_pnl, res.max_drawdown)
        print(
            f"OOS Day 0 ({mode:<12}): PnL={res.total_pnl:>10.2f}, "
            f"MaxDD={res.max_drawdown:>8.2f}, IR_tick={res.sharpe_ratio:.5f}, "
            f"BlkSR1k={blk_sr:.3f}, PnL/DD={p2dd:.2f}, Fills={len(res.fills)}",
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
