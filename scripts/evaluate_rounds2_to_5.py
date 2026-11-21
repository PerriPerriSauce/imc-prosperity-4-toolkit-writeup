"""Reproducible Round 2-5 evaluation, IS/OOS ablations, overfitting gates, and MC suites."""

from __future__ import annotations

import csv
import importlib.util
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from numpy.typing import NDArray

from prosperity_toolkit.analysis.diagnostics import OverfittingDiagnostics
from prosperity_toolkit.backtesting.engine import BacktestEngine
from prosperity_toolkit.backtesting.metrics import PerformanceMetrics
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
from prosperity_toolkit.data.loader import DataLoader
from prosperity_toolkit.execution.fills import FillEvent
from prosperity_toolkit.execution.simulator import ExecutionSimulator, FillMode
from prosperity_toolkit.market.market_state import MarketStateSnapshot
from prosperity_toolkit.optimisation.sensitivity import SensitivityAnalyzer
from prosperity_toolkit.simulation import (
    AssetScenarioConfig,
    BotBookConfig,
    CoupledOptionsMonteCarloEngine,
    MonteCarloEngine,
    MonteCarloSummary,
    OptionsSpotScenarioConfig,
    OrnsteinUhlenbeckParams,
    RandomWalkParams,
    Round5JointConfig,
    Round5JointMonteCarloEngine,
    TradeArrivalConfig,
    simulate_arrival_sensitivity,
    wilson_ci_upper,
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


def _load_trader(round_num: int, **kwargs: float) -> CompetitionTraderProtocol:
    """Dynamically load standalone submission Trader with optional constructor overrides."""
    repo_root = Path(__file__).resolve().parents[1]
    traders_dir = str(repo_root / "traders")
    if traders_dir not in sys.path:
        sys.path.insert(0, traders_dir)
    sub_path = repo_root / "traders" / f"round{round_num}" / "submission.py"
    spec = importlib.util.spec_from_file_location(f"round{round_num}_eval_sub", sub_path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    trader: CompetitionTraderProtocol = mod.Trader(**kwargs)
    return trader


def _make_sub_factory(
    round_num: int,
    name: str,
    **kwargs: float,
) -> Callable[[], BaseStrategy]:
    def _factory() -> BaseStrategy:
        return CompetitionStrategyAdapter(_load_trader(round_num, **kwargs), name=name)

    return _factory


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


def _run_day_set(
    day_snaps: dict[int, list[MarketStateSnapshot]],
    limits: dict[str, int],
    factory: Callable[[], BaseStrategy],
    fill_mode: FillMode = "queue_aware",
) -> tuple[
    float,
    float,
    float,
    float,
    float,
    int,
    float,
    NDArray[np.float64],
    NDArray[np.float64],
    dict[str, float],
]:
    """Run independent per-day simulations (zero overnight carry) and aggregate stats."""
    total_pnl = 0.0
    max_dd = 0.0
    total_fills = 0
    latencies: list[float] = []
    rets_list: list[NDArray[np.float64]] = []
    full_rets_list: list[NDArray[np.float64]] = []
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
        full_rets_list.append(np.diff(eq, prepend=0.0))
        merged_curve.extend((eq + curve_offset).tolist())
        curve_offset += res.total_pnl
        for sym, val in _per_symbol_pnl(res.fills, snaps).items():
            per_sym[sym] = per_sym.get(sym, 0.0) + val

    rets = np.concatenate(rets_list)
    full_rets = np.concatenate(full_rets_list)
    rets_list_py = rets.tolist()
    ir_tick = PerformanceMetrics.calculate_sharpe_ratio(rets_list_py, annualization_factor=1.0)
    blk_sr_1k = PerformanceMetrics.calculate_block_sharpe(rets_list_py, block_size=1000)
    pnl_to_dd = PerformanceMetrics.calculate_pnl_to_drawdown(total_pnl, max_dd)
    mean_lat = float(np.mean(latencies)) if latencies else 0.0
    _ = full_rets
    return (
        total_pnl,
        ir_tick,
        blk_sr_1k,
        pnl_to_dd,
        max_dd,
        total_fills,
        mean_lat,
        rets,
        np.asarray(merged_curve, dtype=np.float64),
        per_sym,
    )


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
    float,
]:
    """Evaluate 2D IS grid under unscaled tick IR, interior plateau, CSCV, block DSR & N_eff."""
    ir_grid = np.zeros((len(x_vals), len(y_vals)), dtype=np.float64)
    pnl_grid = np.zeros((len(x_vals), len(y_vals)), dtype=np.float64)
    returns_cols: list[NDArray[np.float64]] = []

    for i, x in enumerate(x_vals):
        for j, y in enumerate(y_vals):

            def _cell_factory(xx: float = x, yy: float = y) -> BaseStrategy:
                return factory_fn(xx, yy)

            pnl, ir_tick, _bsr, _p2dd, _dd, _nf, _lat, rets, _curve, _ps = _run_day_set(
                day_snaps,
                limits,
                _cell_factory,
                fill_mode="queue_aware",
            )
            ir_grid[i, j] = ir_tick
            pnl_grid[i, j] = pnl
            returns_cols.append(rets)
        print(f"  [R{round_num} grid row {i + 1}/{len(x_vals)} complete]", flush=True)

    plateau = SensitivityAnalyzer.select_stable_plateau_2d(
        x_vals,
        y_vals,
        ir_grid,
        std_penalty=1.0,
        require_interior=True,
    )
    mat = np.column_stack(returns_cols)
    cscv = OverfittingDiagnostics.compute_cscv_pbo(mat, n_slices=8)
    sel_idx = plateau.x_index * len(y_vals) + plateau.y_index
    dsr, n_eff = OverfittingDiagnostics.evaluate_block_matrix_dsr(mat, sel_idx, block_size=100)

    with table_path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow([x_label, y_label, "is_ir_tick", "is_total_pnl"])
        for i, x in enumerate(x_vals):
            for j, y in enumerate(y_vals):
                w.writerow([
                    x,
                    y,
                    round(float(ir_grid[i, j]), 6),
                    round(float(pnl_grid[i, j]), 2),
                ])

    print(
        f"R{round_num} IS Interior Plateau: {x_label}={plateau.x_value}, "
        f"{y_label}={plateau.y_value} | IR_tick={plateau.raw_score:.5f}, "
        f"locMean={plateau.local_mean:.5f}, locStd={plateau.local_std:.5f} | "
        f"N_eff={n_eff:.2f} | PBO={cscv.pbo:.3f} | DSR_block={dsr.deflated_sharpe_ratio:.4f}",
        flush=True,
    )
    return (
        ir_grid,
        pnl_grid,
        float(plateau.x_value),
        float(plateau.y_value),
        plateau.raw_score,
        plateau.local_mean,
        plateau.local_std,
        n_eff,
        cscv.pbo,
        dsr.deflated_sharpe_ratio,
    )


def _mc_row(round_num: int, scenario: str, ms: MonteCarloSummary) -> list[object]:
    k_loss = sum(1 for x in ms.pnl_distribution if x < 0.0)
    p_up = wilson_ci_upper(k_loss, ms.n_sessions)
    return [
        round_num,
        scenario,
        round(ms.mean_pnl, 2),
        round(ms.std_pnl, 2),
        round(ms.median_pnl, 2),
        round(ms.var_95, 2),
        round(ms.cvar_95, 2),
        round(ms.prob_loss, 4),
        round(p_up, 4),
        round(ms.mean_sharpe, 4),
        round(ms.worst_max_drawdown, 2),
    ]


def _write_ablation_csv(path: Path, rows: list[list[object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow([
            "split",
            "fill_mode",
            "strategy",
            "total_pnl",
            "ir_tick",
            "block_sharpe_1k",
            "pnl_to_max_dd",
            "max_drawdown",
            "total_fills",
            "mean_latency_ms",
        ])
        w.writerows(rows)


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
    mc_rows: list[list[object]] = []
    oos_equity_curves: dict[int, NDArray[np.float64]] = {}

    # ------------------------------------------------------------------
    # ROUND 2: IS (Day -1, 0) & OOS (Day 1)
    # ------------------------------------------------------------------
    print("\n=== Evaluating Round 2 (+/-80 limits) ===", flush=True)
    lim2 = get_round_position_limits(2)
    r2_is = {
        d: build_snapshots_from_dataframes(
            loader.load_day_prices(2, d),
            loader.load_day_trades(2, d),
        )
        for d in (-1, 0)
    }
    r2_oos = {
        1: build_snapshots_from_dataframes(
            loader.load_day_prices(2, 1),
            loader.load_day_trades(2, 1),
        ),
    }
    r2_edges = [1.5, 2.0, 2.5, 3.0, 3.5]
    r2_skews = [0.10, 0.25, 0.40, 0.55, 0.70]
    r2_grid, _, x2, y2, ir2_raw, locm2, locs2, neff2, pbo2, dsr2 = _evaluate_is_grid(
        2,
        r2_is,
        lim2,
        r2_edges,
        r2_skews,
        "min_edge",
        "inventory_skew",
        lambda e, k: CompetitionStrategyAdapter(
            _load_trader(2, min_edge=e, inventory_skew=k),
            name=f"R2(e={e},k={k})",
        ),
        table_dir / "r2_sensitivity_grid.csv",
    )

    r2_ab_rows: list[list[object]] = []
    for split, days_map in (("IS", r2_is), ("OOS", r2_oos)):
        for mode in modes:
            factories: list[tuple[str, Callable[[], BaseStrategy]]] = [
                ("NoOpBaseline", lambda: NoOpBaselineStrategy()),
                (
                    "SymmetricMM_80",
                    lambda: SymmetricMarketMaker([
                        MarketMakingConfig("ASH_COATED_OSMIUM", position_limit=80, quote_size=25),
                        MarketMakingConfig(
                            "INTARIAN_PEPPER_ROOT",
                            position_limit=80,
                            quote_size=25,
                        ),
                    ]),
                ),
                (
                    "InventorySkewedMM_80",
                    lambda: InventorySkewedMarketMaker([
                        MarketMakingConfig("ASH_COATED_OSMIUM", position_limit=80, quote_size=25),
                        MarketMakingConfig(
                            "INTARIAN_PEPPER_ROOT",
                            position_limit=80,
                            quote_size=25,
                        ),
                    ]),
                ),
                (
                    "DriftAwareQuoter_Pepper",
                    lambda: DriftAwareQuoter([
                        DriftAwareConfig("INTARIAN_PEPPER_ROOT", position_limit=80, quote_size=25),
                    ]),
                ),
                (
                    "Round2Submission",
                    _make_sub_factory(2, "Round2Submission", min_edge=x2, inventory_skew=y2),
                ),
            ]
            for sname, fac in factories:
                pnl, ir, bsr, p2dd, dd, nf, lat, _rets, curve, ps = _run_day_set(
                    days_map,
                    lim2,
                    fac,
                    fill_mode=mode,
                )
                r2_ab_rows.append([
                    split,
                    mode,
                    sname,
                    round(pnl, 2),
                    round(ir, 6),
                    round(bsr, 4),
                    round(p2dd, 4),
                    round(dd, 2),
                    nf,
                    round(lat, 4),
                ])
                if split == "OOS" and mode == "queue_aware" and sname == "Round2Submission":
                    b2 = OverfittingDiagnostics.block_bootstrap_ci(
                        np.diff(curve),
                        block_size=100,
                        n_bootstraps=1000,
                        seed=42,
                        scale_factor=1.0,
                    )
                    oos_equity_curves[2] = curve
                    overfit_rows.append([
                        2,
                        f"edge={x2},skew={y2}",
                        round(ir2_raw, 6),
                        round(locm2, 6),
                        round(locs2, 6),
                        round(neff2, 4),
                        round(pbo2, 4),
                        round(dsr2, 4),
                        round(pnl, 2),
                        round(ir, 6),
                        round(bsr, 4),
                    ])
                    bootstrap_rows.append([
                        2,
                        "portfolio",
                        "PORTFOLIO",
                        round(pnl, 2),
                        round(b2.sharpe_ci_low, 6),
                        round(b2.sharpe_ci_high, 6),
                        round(b2.pnl_ci_low, 2),
                        round(b2.pnl_ci_high, 2),
                    ])
                    for sym, val in ps.items():
                        bootstrap_rows.append([2, "asset", sym, round(val, 2), "", "", "", ""])
                    print(
                        f"R2 OOS queue_aware Round2Submission: PnL={pnl:,.2f}, IR_tick={ir:.5f}, "
                        f"BlkSR1k={bsr:.3f}, BootIR_CI=[{b2.sharpe_ci_low:.5f}, "
                        f"{b2.sharpe_ci_high:.5f}], sym={ps}",
                        flush=True,
                    )

    _write_ablation_csv(table_dir / "r2_ablation_summary.csv", r2_ab_rows)

    # Round 2 MAF Arrival-Rate Valuation MC (+0.1000/tick drift, N=40) + Adverse Stress
    r2_mc_assets = [
        AssetScenarioConfig(
            symbol="ASH_COATED_OSMIUM",
            position_limit=80,
            process=OrnsteinUhlenbeckParams(
                mu=10001.0,
                theta=0.09,
                sigma=1.88,
                initial_price=10001.0,
            ),
            book=BotBookConfig(half_spread_l1=8.0, depth_l1=20, step_l2=2, depth_l2=4),
            arrivals=TradeArrivalConfig(arrival_prob=0.08, min_size=1, max_size=12),
        ),
        AssetScenarioConfig(
            symbol="INTARIAN_PEPPER_ROOT",
            position_limit=80,
            process=RandomWalkParams(initial_price=12500.0, mu_drift=0.10, sigma=1.81),
            book=BotBookConfig(half_spread_l1=7.0, depth_l1=20, step_l2=2, depth_l2=4),
            arrivals=TradeArrivalConfig(arrival_prob=0.06, min_size=1, max_size=12),
        ),
    ]
    maf_rates = [0.04, 0.06, 0.08, 0.10, 0.12]
    maf_summaries = simulate_arrival_sensitivity(
        lambda: CompetitionStrategyAdapter(
            _load_trader(2, min_edge=x2, inventory_skew=y2),
            name="Round2Submission",
        ),
        r2_mc_assets,
        arrival_rates=maf_rates,
        n_sessions=40,
        n_steps=1000,
        fill_mode="queue_aware",
        seed=102,
    )
    with (table_dir / "r2_maf_sensitivity.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow([
            "arrival_rate",
            "mean_pnl",
            "std_pnl",
            "median_pnl",
            "var_95",
            "cvar_95",
            "prob_loss",
            "prob_loss_ci95_upper",
            "mean_ir_tick",
        ])
        for rate, ms in maf_summaries.items():
            k_loss = sum(1 for x in ms.pnl_distribution if x < 0.0)
            w.writerow([
                rate,
                round(ms.mean_pnl, 2),
                round(ms.std_pnl, 2),
                round(ms.median_pnl, 2),
                round(ms.var_95, 2),
                round(ms.cvar_95, 2),
                round(ms.prob_loss, 4),
                round(wilson_ci_upper(k_loss, ms.n_sessions), 4),
                round(ms.mean_sharpe, 4),
            ])
    mc_rows.append(_mc_row(2, "Round2Submission_BaselineFlow", maf_summaries[0.08]))
    mc_rows.append(_mc_row(2, "Round2Submission_MAFPlus25", maf_summaries[0.10]))
    r2_stress = MonteCarloEngine(
        assets=r2_mc_assets,
        fill_mode="queue_aware",
        adverse_selection_prob=0.30,
        adverse_jump_size=6.0,
    ).run(
        lambda: CompetitionStrategyAdapter(
            _load_trader(2, min_edge=x2, inventory_skew=y2),
            name="Round2Submission_AdverseStress",
        ),
        n_sessions=40,
        n_steps=1000,
        seed=202,
    )
    mc_rows.append(_mc_row(2, "Round2Submission_AdverseStress", r2_stress))

    # ------------------------------------------------------------------
    # ROUND 3: IS (Day 0, 1) & OOS (Day 2)
    # ------------------------------------------------------------------
    print("\n=== Evaluating Round 3 (Spot +/-200, VEV +/-300) ===", flush=True)
    lim3 = get_round_position_limits(3)
    r3_is = {
        d: build_snapshots_from_dataframes(
            loader.load_day_prices(3, d),
            loader.load_day_trades(3, d),
        )
        for d in (0, 1)
    }
    r3_oos = {
        2: build_snapshots_from_dataframes(
            loader.load_day_prices(3, 2),
            loader.load_day_trades(3, 2),
        ),
    }
    r3_scales = [18.0, 22.0, 26.0, 30.0, 34.0]
    r3_bands = [4.0, 6.0, 8.0, 10.0, 12.0]
    _r3_g, _, x3, y3, ir3_raw, locm3, locs3, neff3, pbo3, dsr3 = _evaluate_is_grid(
        3,
        r3_is,
        lim3,
        r3_scales,
        r3_bands,
        "spot_scale",
        "enter_band",
        lambda sc, eb: CompetitionStrategyAdapter(
            _load_trader(3, spot_scale=sc, enter_band=eb),
            name=f"R3(s={sc},b={eb})",
        ),
        table_dir / "r3_sensitivity_grid.csv",
    )

    r3_ab_rows: list[list[object]] = []
    r3_oos_persym: dict[str, float] = {}
    for split, days_map in (("IS", r3_is), ("OOS", r3_oos)):
        for mode in modes:
            factories_r3: list[tuple[str, Callable[[], BaseStrategy]]] = [
                ("NoOpBaseline", lambda: NoOpBaselineStrategy()),
                (
                    "SymmetricSpotMM",
                    lambda: SymmetricMarketMaker([
                        MarketMakingConfig("HYDROGEL_PACK", position_limit=200, quote_size=30),
                        MarketMakingConfig(
                            "VELVETFRUIT_EXTRACT",
                            position_limit=200,
                            quote_size=25,
                        ),
                    ]),
                ),
                ("OptionsVolatilityContract", lambda: OptionsVolatilityStrategy()),
                (
                    "Round3Submission",
                    _make_sub_factory(3, "Round3Submission", spot_scale=x3, enter_band=y3),
                ),
            ]
            for sname, fac in factories_r3:
                pnl, ir, bsr, p2dd, dd, nf, lat, _rets, curve, ps = _run_day_set(
                    days_map,
                    lim3,
                    fac,
                    fill_mode=mode,
                )
                r3_ab_rows.append([
                    split,
                    mode,
                    sname,
                    round(pnl, 2),
                    round(ir, 6),
                    round(bsr, 4),
                    round(p2dd, 4),
                    round(dd, 2),
                    nf,
                    round(lat, 4),
                ])
                if split == "OOS" and mode == "queue_aware" and sname == "Round3Submission":
                    b3 = OverfittingDiagnostics.block_bootstrap_ci(
                        np.diff(curve),
                        block_size=100,
                        n_bootstraps=1000,
                        seed=42,
                        scale_factor=1.0,
                    )
                    oos_equity_curves[3] = curve
                    r3_oos_persym = ps
                    overfit_rows.append([
                        3,
                        f"spot_scale={x3},enter_band={y3}",
                        round(ir3_raw, 6),
                        round(locm3, 6),
                        round(locs3, 6),
                        round(neff3, 4),
                        round(pbo3, 4),
                        round(dsr3, 4),
                        round(pnl, 2),
                        round(ir, 6),
                        round(bsr, 4),
                    ])
                    bootstrap_rows.append([
                        3,
                        "portfolio",
                        "PORTFOLIO",
                        round(pnl, 2),
                        round(b3.sharpe_ci_low, 6),
                        round(b3.sharpe_ci_high, 6),
                        round(b3.pnl_ci_low, 2),
                        round(b3.pnl_ci_high, 2),
                    ])
                    for sym, val in ps.items():
                        bootstrap_rows.append([3, "asset", sym, round(val, 2), "", "", "", ""])
                    print(
                        f"R3 OOS queue_aware Round3Submission: PnL={pnl:,.2f}, IR_tick={ir:.5f}, "
                        f"BlkSR1k={bsr:.3f}, BootIR_CI=[{b3.sharpe_ci_low:.5f}, "
                        f"{b3.sharpe_ci_high:.5f}]",
                        flush=True,
                    )

    _write_ablation_csv(table_dir / "r3_ablation_summary.csv", r3_ab_rows)

    # ------------------------------------------------------------------
    # ROUND 4: IS (Day 1, 2) & OOS (Day 3)
    # ------------------------------------------------------------------
    print("\n=== Evaluating Round 4 (Causal Mark 14/55 Flow Intelligence) ===", flush=True)
    r4_is = {
        d: build_snapshots_from_dataframes(
            loader.load_day_prices(4, d),
            loader.load_day_trades(4, d),
        )
        for d in (1, 2)
    }
    r4_oos = {
        3: build_snapshots_from_dataframes(
            loader.load_day_prices(4, 3),
            loader.load_day_trades(4, 3),
        ),
    }
    r4_scales = [18.0, 22.0, 26.0, 30.0, 34.0]
    r4_fws = [0.0, 0.5, 1.0, 1.5, 2.0]
    _r4_g, _, x4, y4, ir4_raw, locm4, locs4, neff4, pbo4, dsr4 = _evaluate_is_grid(
        4,
        r4_is,
        lim3,
        r4_scales,
        r4_fws,
        "spot_scale",
        "flow_weight",
        lambda sc, fw: CompetitionStrategyAdapter(
            _load_trader(4, spot_scale=sc, flow_weight=fw, enter_band=y3),
            name=f"R4(s={sc},fw={fw})",
        ),
        table_dir / "r4_sensitivity_grid.csv",
    )

    r4_ab_rows: list[list[object]] = []
    r4_oos_persym: dict[str, float] = {}
    for split, days_map in (("IS", r4_is), ("OOS", r4_oos)):
        for mode in modes:
            factories_r4: list[tuple[str, Callable[[], BaseStrategy]]] = [
                ("NoOpBaseline", lambda: NoOpBaselineStrategy()),
                (
                    "Round3NoFlow",
                    _make_sub_factory(
                        4,
                        "Round3NoFlow",
                        spot_scale=x4,
                        flow_weight=0.0,
                        enter_band=y3,
                    ),
                ),
                (
                    "Round4Submission",
                    _make_sub_factory(
                        4,
                        "Round4Submission",
                        spot_scale=x4,
                        flow_weight=y4,
                        enter_band=y3,
                    ),
                ),
            ]
            for sname, fac in factories_r4:
                pnl, ir, bsr, p2dd, dd, nf, lat, _rets, curve, ps = _run_day_set(
                    days_map,
                    lim3,
                    fac,
                    fill_mode=mode,
                )
                r4_ab_rows.append([
                    split,
                    mode,
                    sname,
                    round(pnl, 2),
                    round(ir, 6),
                    round(bsr, 4),
                    round(p2dd, 4),
                    round(dd, 2),
                    nf,
                    round(lat, 4),
                ])
                if split == "OOS" and mode == "queue_aware" and sname == "Round4Submission":
                    b4 = OverfittingDiagnostics.block_bootstrap_ci(
                        np.diff(curve),
                        block_size=100,
                        n_bootstraps=1000,
                        seed=42,
                        scale_factor=1.0,
                    )
                    oos_equity_curves[4] = curve
                    r4_oos_persym = ps
                    overfit_rows.append([
                        4,
                        f"spot_scale={x4},flow_weight={y4}",
                        round(ir4_raw, 6),
                        round(locm4, 6),
                        round(locs4, 6),
                        round(neff4, 4),
                        round(pbo4, 4),
                        round(dsr4, 4),
                        round(pnl, 2),
                        round(ir, 6),
                        round(bsr, 4),
                    ])
                    bootstrap_rows.append([
                        4,
                        "portfolio",
                        "PORTFOLIO",
                        round(pnl, 2),
                        round(b4.sharpe_ci_low, 6),
                        round(b4.sharpe_ci_high, 6),
                        round(b4.pnl_ci_low, 2),
                        round(b4.pnl_ci_high, 2),
                    ])
                    for sym, val in ps.items():
                        bootstrap_rows.append([4, "asset", sym, round(val, 2), "", "", "", ""])
                    print(
                        f"R4 OOS queue_aware Round4Submission: PnL={pnl:,.2f}, IR_tick={ir:.5f}, "
                        f"BlkSR1k={bsr:.3f}, BootIR_CI=[{b4.sharpe_ci_low:.5f}, "
                        f"{b4.sharpe_ci_high:.5f}]",
                        flush=True,
                    )

    _write_ablation_csv(table_dir / "r4_ablation_summary.csv", r4_ab_rows)

    # Coupled Options + Spot Monte Carlo (Rounds 3 & 4, calibrated + adverse stress, N=40)
    coupled_cal = CoupledOptionsMonteCarloEngine(
        OptionsSpotScenarioConfig(),
        fill_mode="queue_aware",
    )
    coupled_stress = CoupledOptionsMonteCarloEngine(
        OptionsSpotScenarioConfig(adverse_selection_prob=0.30, adverse_jump_size=5.0),
        fill_mode="queue_aware",
    )
    r3_mc = coupled_cal.run(
        lambda: CompetitionStrategyAdapter(
            _load_trader(3, spot_scale=x3, enter_band=y3),
            name="Round3Submission",
        ),
        n_sessions=40,
        n_steps=1000,
        seed=303,
    )
    r3_mc_s = coupled_stress.run(
        lambda: CompetitionStrategyAdapter(
            _load_trader(3, spot_scale=x3, enter_band=y3),
            name="Round3Submission_AdverseStress",
        ),
        n_sessions=40,
        n_steps=1000,
        seed=304,
    )
    r4_mc = coupled_cal.run(
        lambda: CompetitionStrategyAdapter(
            _load_trader(4, spot_scale=x4, flow_weight=y4, enter_band=y3),
            name="Round4Submission",
        ),
        n_sessions=40,
        n_steps=1000,
        seed=404,
    )
    r4_mc_s = coupled_stress.run(
        lambda: CompetitionStrategyAdapter(
            _load_trader(4, spot_scale=x4, flow_weight=y4, enter_band=y3),
            name="Round4Submission_AdverseStress",
        ),
        n_sessions=40,
        n_steps=1000,
        seed=405,
    )
    mc_rows.append(_mc_row(3, "Round3Submission_CalibratedQA", r3_mc))
    mc_rows.append(_mc_row(3, "Round3Submission_AdverseStress", r3_mc_s))
    mc_rows.append(_mc_row(4, "Round4Submission_CalibratedQA", r4_mc))
    mc_rows.append(_mc_row(4, "Round4Submission_AdverseStress", r4_mc_s))

    # ------------------------------------------------------------------
    # ROUND 5: IS (Day 2, 3) & OOS (Day 4) across 50 products (+/-10)
    # ------------------------------------------------------------------
    print("\n=== Evaluating Round 5 (50 Assets, +/-10 limits) ===", flush=True)
    lim5 = get_round_position_limits(5)
    r5_is = {
        d: build_snapshots_from_dataframes(
            loader.load_day_prices(5, d),
            loader.load_day_trades(5, d),
        )
        for d in (2, 3)
    }
    r5_oos = {
        4: build_snapshots_from_dataframes(
            loader.load_day_prices(5, 4),
            loader.load_day_trades(5, 4),
        ),
    }
    r5_vsms = [0.06, 0.10, 0.14, 0.18, 0.22]
    r5_efs = [0.10, 0.14, 0.18, 0.22, 0.26]
    r5_grid, _, x5, y5, ir5_raw, locm5, locs5, neff5, pbo5, dsr5 = _evaluate_is_grid(
        5,
        r5_is,
        lim5,
        r5_vsms,
        r5_efs,
        "vol_skew_mult",
        "edge_frac",
        lambda vsm, ef: CompetitionStrategyAdapter(
            _load_trader(5, vol_skew_mult=vsm, edge_frac=ef, mc_beta=0.0),
            name=f"R5(v={vsm},ef={ef})",
        ),
        table_dir / "r5_sensitivity_grid.csv",
    )

    # Strictly IS MC lag selection around fixed (x5, y5)
    best_mc_beta = 0.0
    best_mc_ir = ir5_raw
    for cand_beta in (0.0, 0.12, 0.16, 0.20, 0.24):
        tot_b, ir_b, _bsr, _p2dd, dd_b, _nf, _lat, _rets, _curve, _ps = _run_day_set(
            r5_is,
            lim5,
            _make_sub_factory(
                5,
                f"R5_MC({cand_beta})",
                vol_skew_mult=x5,
                edge_frac=y5,
                mc_beta=cand_beta,
            ),
            fill_mode="queue_aware",
        )
        print(
            f"  R5 IS MC-Lag check beta={cand_beta:.2f}: PnL={tot_b:,.1f}, IR_tick={ir_b:.5f}, "
            f"MaxDD={dd_b:,.1f}",
            flush=True,
        )
        if ir_b > best_mc_ir:
            best_mc_ir = ir_b
            best_mc_beta = cand_beta
    print(f"R5 IS selected mc_beta={best_mc_beta:.2f} (IR_tick={best_mc_ir:.5f})", flush=True)

    r5_ab_rows: list[list[object]] = []
    r5_oos_cat_sub: dict[str, float] = {}
    r5_oos_cat_noll: dict[str, float] = {}
    r5_cfgs_all = [
        MarketMakingConfig(symbol=sym, position_limit=10, quote_size=10)
        for sym in get_round_products(5)
    ]

    for split, days_map in (("IS", r5_is), ("OOS", r5_oos)):
        for mode in modes:
            factories_r5: list[tuple[str, Callable[[], BaseStrategy]]] = [
                ("NoOpBaseline", lambda: NoOpBaselineStrategy()),
                ("EmaSymmetricMM_All50", lambda: SymmetricMarketMaker(r5_cfgs_all)),
                (
                    "Round5NoLeadLag",
                    _make_sub_factory(
                        5,
                        "Round5NoLeadLag",
                        vol_skew_mult=x5,
                        edge_frac=y5,
                        mc_beta=0.0,
                    ),
                ),
                (
                    "Round5Submission",
                    _make_sub_factory(
                        5,
                        "Round5Submission",
                        vol_skew_mult=x5,
                        edge_frac=y5,
                        mc_beta=best_mc_beta,
                    ),
                ),
            ]
            for sname, fac in factories_r5:
                pnl, ir, bsr, p2dd, dd, nf, lat, _rets, curve, ps = _run_day_set(
                    days_map,
                    lim5,
                    fac,
                    fill_mode=mode,
                )
                r5_ab_rows.append([
                    split,
                    mode,
                    sname,
                    round(pnl, 2),
                    round(ir, 6),
                    round(bsr, 4),
                    round(p2dd, 4),
                    round(dd, 2),
                    nf,
                    round(lat, 4),
                ])
                if split == "OOS" and mode == "queue_aware":
                    if sname == "Round5NoLeadLag":
                        r5_oos_cat_noll = {
                            cat: sum(ps.get(s, 0.0) for s in syms)
                            for cat, syms in PROSPERITY4_R5_CATEGORIES.items()
                        }
                    elif sname == "Round5Submission":
                        b5 = OverfittingDiagnostics.block_bootstrap_ci(
                            np.diff(curve),
                            block_size=100,
                            n_bootstraps=1000,
                            seed=42,
                            scale_factor=1.0,
                        )
                        oos_equity_curves[5] = curve
                        r5_oos_cat_sub = {
                            cat: sum(ps.get(s, 0.0) for s in syms)
                            for cat, syms in PROSPERITY4_R5_CATEGORIES.items()
                        }
                        overfit_rows.append([
                            5,
                            f"vsm={x5},ef={y5},mc={best_mc_beta:.2f}",
                            round(ir5_raw, 6),
                            round(locm5, 6),
                            round(locs5, 6),
                            round(neff5, 4),
                            round(pbo5, 4),
                            round(dsr5, 4),
                            round(pnl, 2),
                            round(ir, 6),
                            round(bsr, 4),
                        ])
                        bootstrap_rows.append([
                            5,
                            "portfolio",
                            "PORTFOLIO",
                            round(pnl, 2),
                            round(b5.sharpe_ci_low, 6),
                            round(b5.sharpe_ci_high, 6),
                            round(b5.pnl_ci_low, 2),
                            round(b5.pnl_ci_high, 2),
                        ])
                        for cat, val in r5_oos_cat_sub.items():
                            bootstrap_rows.append([
                                5,
                                "category",
                                f"Category:{cat}",
                                round(val, 2),
                                "",
                                "",
                                "",
                                "",
                            ])
                        print(
                            f"R5 OOS queue_aware Round5Submission: PnL={pnl:,.2f}, "
                            f"IR_tick={ir:.5f}, BlkSR1k={bsr:.3f}, "
                            f"BootIR_CI=[{b5.sharpe_ci_low:.5f}, {b5.sharpe_ci_high:.5f}]",
                            flush=True,
                        )

    _write_ablation_csv(table_dir / "r5_ablation_summary.csv", r5_ab_rows)

    # Round 5 11-Asset Representative Joint MC (calibrated + adverse stress, N=40)
    r5_mc_cal = Round5JointMonteCarloEngine(Round5JointConfig(), fill_mode="queue_aware").run(
        lambda: CompetitionStrategyAdapter(
            _load_trader(5, vol_skew_mult=x5, edge_frac=y5, mc_beta=best_mc_beta),
            name="Round5Submission_11AssetRepPulseMC",
        ),
        n_sessions=40,
        n_steps=1000,
        seed=505,
    )
    r5_mc_stress = Round5JointMonteCarloEngine(
        Round5JointConfig(adverse_selection_prob=0.25, adverse_jump_size=8.0),
        fill_mode="queue_aware",
    ).run(
        lambda: CompetitionStrategyAdapter(
            _load_trader(5, vol_skew_mult=x5, edge_frac=y5, mc_beta=best_mc_beta),
            name="Round5Submission_11AssetAdverseStress",
        ),
        n_sessions=40,
        n_steps=1000,
        seed=506,
    )
    mc_rows.append(_mc_row(5, "Round5Submission_11AssetRepPulseMC", r5_mc_cal))
    mc_rows.append(_mc_row(5, "Round5Submission_11AssetAdverseStress", r5_mc_stress))

    with (table_dir / "r2_to_r5_overfitting_gates.csv").open(
        "w",
        newline="",
        encoding="utf-8",
    ) as fh:
        w = csv.writer(fh)
        w.writerow([
            "round",
            "plateau_params",
            "is_ir_tick",
            "local_mean",
            "local_std",
            "n_eff",
            "cscv_pbo",
            "dsr_block",
            "oos_pnl",
            "oos_ir_tick",
            "oos_block_sharpe_1k",
        ])
        w.writerows(overfit_rows)

    with (table_dir / "r2_to_r5_bootstrap_and_attribution.csv").open(
        "w",
        newline="",
        encoding="utf-8",
    ) as fh:
        w = csv.writer(fh)
        w.writerow([
            "round",
            "scope",
            "bucket",
            "oos_pnl",
            "boot_ir_tick_lo",
            "boot_ir_tick_hi",
            "boot_pnl_lo",
            "boot_pnl_hi",
        ])
        w.writerows(bootstrap_rows)

    with (table_dir / "r2_to_r5_mc_risk_summary.csv").open(
        "w",
        newline="",
        encoding="utf-8",
    ) as fh:
        w = csv.writer(fh)
        w.writerow([
            "round",
            "scenario",
            "mean_pnl",
            "std_pnl",
            "median_pnl",
            "var_95",
            "cvar_95",
            "prob_loss",
            "prob_loss_ci95_upper",
            "mean_ir_tick",
            "worst_max_dd",
        ])
        w.writerows(mc_rows)

    # ------------------------------------------------------------------
    # DIAGNOSTIC FIGURES (reports/figures/)
    # ------------------------------------------------------------------
    fig, axes = plt.subplots(1, 2, figsize=(13.0, 4.8))
    im = axes[0].imshow(r2_grid, cmap="viridis", aspect="auto")
    axes[0].set_xticks(range(len(r2_skews)), labels=[f"{s:.2f}" for s in r2_skews])
    axes[0].set_yticks(range(len(r2_edges)), labels=[f"{e:.1f}" for e in r2_edges])
    axes[0].set_xlabel("Inventory Skew Factor")
    axes[0].set_ylabel("Minimum Edge Floor (ticks)")
    axes[0].set_title(f"R2 IS Tick IR Surface (PBO={pbo2:.3f}, DSR_blk={dsr2:.4f})")
    for i in range(len(r2_edges)):
        for j in range(len(r2_skews)):
            axes[0].text(
                j,
                i,
                f"{r2_grid[i, j]:.4f}",
                ha="center",
                va="center",
                color="white",
                fontsize=8,
            )
    fig.colorbar(im, ax=axes[0], label="Tick Information Ratio (IR_tick)")

    maf_means = [maf_summaries[r].mean_pnl for r in maf_rates]
    maf_stds = [maf_summaries[r].std_pnl for r in maf_rates]
    axes[1].errorbar(
        maf_rates,
        maf_means,
        yerr=maf_stds,
        marker="o",
        linewidth=2.2,
        color="#2a9d8f",
        capsize=4,
    )
    axes[1].axvspan(0.08, 0.10, color="#e9c46a", alpha=0.25, label="Baseline -> +25% MAF Boost")
    axes[1].set_title("Round 2 MC PnL vs. Counterparty Arrival Rate (N=40 x 1k)")
    axes[1].set_xlabel("Arrival Rate per Step")
    axes[1].set_ylabel("Mean Session PnL (+/- 1 SD)")
    axes[1].grid(True, linestyle="--", alpha=0.4)
    axes[1].legend()
    fig.tight_layout()
    fig.savefig(fig_dir / "r2_sensitivity_and_maf_valuation.png", dpi=200)
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(14.5, 4.8))
    syms34 = [
        "HYDROGEL_PACK",
        "VELVETFRUIT_EXTRACT",
        "VEV_4000",
        "VEV_4500",
        "VEV_5000",
        "VEV_5100",
        "VEV_5200",
        "VEV_5300",
        "VEV_5400",
        "VEV_5500",
    ]
    labels34 = [
        "HYDRO",
        "VELVET",
        "VEV4k",
        "VEV4.5k",
        "VEV5k",
        "VEV5.1k",
        "VEV5.2k",
        "VEV5.3k",
        "VEV5.4k",
        "VEV5.5k",
    ]
    vals3 = [r3_oos_persym.get(s, 0.0) for s in syms34]
    vals4 = [r4_oos_persym.get(s, 0.0) for s in syms34]
    xpos = np.arange(len(syms34))
    axes[0].bar(xpos - 0.18, vals3, width=0.36, label="R3 OOS (Day 2)", color="#264653")
    axes[0].bar(xpos + 0.18, vals4, width=0.36, label="R4 OOS (Day 3)", color="#e76f51")
    axes[0].set_xticks(xpos, labels=labels34, rotation=28, ha="right")
    axes[0].set_title("Round 3 & 4 OOS 10-Asset Attribution (Queue-Aware)")
    axes[0].set_ylabel("OOS PnL (XIRECs)")
    axes[0].grid(True, axis="y", linestyle="--", alpha=0.4)
    axes[0].legend()

    axes[1].hist(
        r3_mc.pnl_distribution,
        bins=14,
        alpha=0.55,
        color="#264653",
        label=f"R3 Calibrated (Mean={r3_mc.mean_pnl:,.0f})",
    )
    axes[1].hist(
        r4_mc.pnl_distribution,
        bins=14,
        alpha=0.55,
        color="#2a9d8f",
        label=f"R4 Calibrated (Mean={r4_mc.mean_pnl:,.0f})",
    )
    axes[1].hist(
        r4_mc_s.pnl_distribution,
        bins=14,
        alpha=0.45,
        color="#e76f51",
        label=f"R4 AdverseStress (Mean={r4_mc_s.mean_pnl:,.0f})",
    )
    axes[1].set_title("Coupled Spot+Options MC PnL Distribution (N=40 x 1k steps)")
    axes[1].set_xlabel("Session PnL (XIRECs)")
    axes[1].set_ylabel("Session Count")
    axes[1].grid(True, linestyle="--", alpha=0.4)
    axes[1].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(fig_dir / "r3_r4_oos_attribution_and_mc.png", dpi=200)
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(14.0, 5.2))
    im5 = axes[0].imshow(r5_grid, cmap="viridis", aspect="auto")
    axes[0].set_xticks(range(len(r5_efs)), labels=[f"{e:.2f}" for e in r5_efs])
    axes[0].set_yticks(range(len(r5_vsms)), labels=[f"{v:.2f}" for v in r5_vsms])
    axes[0].set_xlabel("Spread Edge Fraction")
    axes[0].set_ylabel("Volatility Skew Multiplier")
    axes[0].set_title(f"R5 IS Tick IR Surface (PBO={pbo5:.3f}, DSR_blk={dsr5:.4f})")
    for i in range(len(r5_vsms)):
        for j in range(len(r5_efs)):
            axes[0].text(
                j,
                i,
                f"{r5_grid[i, j]:.4f}",
                ha="center",
                va="center",
                color="white",
                fontsize=8,
            )
    fig.colorbar(im5, ax=axes[0], label="Tick Information Ratio (IR_tick)")

    cats = list(PROSPERITY4_R5_CATEGORIES.keys())
    c_xpos = np.arange(len(cats))
    axes[1].bar(
        c_xpos - 0.18,
        [r5_oos_cat_noll.get(c, 0.0) for c in cats],
        width=0.36,
        color="#8d99ae",
        label="Round5NoLeadLag (mc_beta=0)",
    )
    axes[1].bar(
        c_xpos + 0.18,
        [r5_oos_cat_sub.get(c, 0.0) for c in cats],
        width=0.36,
        color="#2a9d8f",
        label=f"Round5Submission (mc_beta={best_mc_beta:.2f})",
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

    fig, axes = plt.subplots(2, 2, figsize=(12.5, 8.0))
    colors = {2: "#1d3557", 3: "#2a9d8f", 4: "#e76f51", 5: "#6a4c93"}
    titles = {
        2: "Round 2 OOS (Day 1, +/-80)",
        3: "Round 3 OOS (Day 2, Options+Spot)",
        4: "Round 4 OOS (Day 3, Causal Flow+Options)",
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

    print("\nCompleted all Round 2-5 tables and figures cleanly.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
