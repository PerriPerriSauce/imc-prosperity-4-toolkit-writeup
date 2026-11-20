"""Reproducible evaluation of Round 0 and Round 1 baseline vs candidate strategies."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np

from prosperity_toolkit.backtesting.engine import BacktestEngine
from prosperity_toolkit.backtesting.metrics import PerformanceMetrics
from prosperity_toolkit.backtesting.replay import build_snapshots_from_dataframes
from prosperity_toolkit.competition.adapter import (
    CompetitionStrategyAdapter,
    CompetitionTraderProtocol,
)
from prosperity_toolkit.competition.specifications import get_round_position_limits
from prosperity_toolkit.data.loader import DataLoader
from prosperity_toolkit.execution.simulator import ExecutionSimulator, FillMode
from prosperity_toolkit.simulation import (
    AssetScenarioConfig,
    BotBookConfig,
    MonteCarloEngine,
    OrnsteinUhlenbeckParams,
    RandomWalkParams,
    TradeArrivalConfig,
    wilson_ci_upper,
)
from prosperity_toolkit.strategies import (
    BaseStrategy,
    DriftAwareConfig,
    DriftAwareQuoter,
    InventorySkewedMarketMaker,
    MarketMakingConfig,
    NoOpBaselineStrategy,
    SymmetricMarketMaker,
)


def _load_round1_trader(**kwargs: float) -> CompetitionTraderProtocol:
    """Load standalone Round 1 Trader using traders/datamodel.py."""
    repo_root = Path(__file__).resolve().parents[1]
    traders_dir = str(repo_root / "traders")
    if traders_dir not in sys.path:
        sys.path.insert(0, traders_dir)
    sub_path = repo_root / "traders" / "round1" / "submission.py"
    spec = importlib.util.spec_from_file_location("round1_sub", sub_path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    trader: CompetitionTraderProtocol = mod.Trader(**kwargs)
    return trader


def evaluate_replay(
    round_num: int,
    day: int,
    limits: dict[str, int],
    fill_modes: tuple[FillMode, ...] = ("conservative", "queue_aware", "touch"),
) -> None:
    """Run replay evaluation across fill regimes for a given round and day."""
    loader = DataLoader()
    prices_df = loader.load_day_prices(round_num, day)
    trades_df = loader.load_day_trades(round_num, day)
    snapshots = build_snapshots_from_dataframes(prices_df, trades_df)

    print(f"\n=== Historical Replay: Round {round_num}, Day {day} (ticks={len(snapshots)}) ===")
    for mode in fill_modes:
        print(f"\n-- Fill Regime: {mode} --")
        strategies: list[BaseStrategy] = [NoOpBaselineStrategy()]
        if round_num == 0:
            r0_cfgs = [
                MarketMakingConfig(symbol="EMERALDS", position_limit=20, anchor_fv=10000.0),
                MarketMakingConfig(symbol="TOMATOES", position_limit=20),
            ]
            strategies.extend([
                SymmetricMarketMaker(r0_cfgs),
                InventorySkewedMarketMaker(r0_cfgs),
            ])
        else:
            r1_cfgs = [
                MarketMakingConfig(
                    symbol="ASH_COATED_OSMIUM",
                    position_limit=limits["ASH_COATED_OSMIUM"],
                    quote_size=25,
                ),
                MarketMakingConfig(
                    symbol="INTARIAN_PEPPER_ROOT",
                    position_limit=limits["INTARIAN_PEPPER_ROOT"],
                    quote_size=25,
                ),
            ]
            pepper_cfg = DriftAwareConfig(
                symbol="INTARIAN_PEPPER_ROOT",
                position_limit=limits["INTARIAN_PEPPER_ROOT"],
                quote_size=25,
            )
            strategies.extend([
                SymmetricMarketMaker(r1_cfgs),
                InventorySkewedMarketMaker(r1_cfgs),
                DriftAwareQuoter([pepper_cfg]),
                CompetitionStrategyAdapter(
                    trader=_load_round1_trader(),
                    name="Round1Submission",
                ),
            ])

        for strat in strategies:
            sim = ExecutionSimulator(position_limits=limits, fill_mode=mode)
            engine = BacktestEngine(simulator=sim)
            res = engine.run(strat, snapshots)
            rets = np.diff(np.asarray(res.equity_curve, dtype=np.float64)).tolist()
            block_sr = PerformanceMetrics.calculate_block_sharpe(rets, block_size=1000)
            p2dd = PerformanceMetrics.calculate_pnl_to_drawdown(res.total_pnl, res.max_drawdown)
            extra = ""
            if isinstance(strat, CompetitionStrategyAdapter):
                extra = f", mean_latency_ms={strat.mean_latency_ms:.4f}"
            print(
                f"  {res.strategy_name:<22} | PnL={res.total_pnl:>10.2f} | "
                f"MaxDD={res.max_drawdown:>8.2f} | IR_tick={res.sharpe_ratio:>6.4f} | "
                f"BlkSR1k={block_sr:>5.2f} | PnL/DD={p2dd:>6.2f} | "
                f"Fills={len(res.fills):>5}{extra}",
            )


def evaluate_monte_carlo() -> None:
    """Run calibrated & stress-tested Round 1 MC using Day -2/-1 estimates (+/-80 limits)."""
    limits = get_round_position_limits(1)
    osmium_cfg = AssetScenarioConfig(
        symbol="ASH_COATED_OSMIUM",
        process=OrnsteinUhlenbeckParams(mu=10000.5, theta=0.11, sigma=1.90, initial_price=10000.5),
        book=BotBookConfig(half_spread_l1=8.0, depth_l1=18),
        arrivals=TradeArrivalConfig(arrival_prob=0.05, buy_prob=0.5, min_size=1, max_size=10),
        position_limit=limits["ASH_COATED_OSMIUM"],
    )
    pepper_cfg = AssetScenarioConfig(
        symbol="INTARIAN_PEPPER_ROOT",
        process=RandomWalkParams(initial_price=11000.0, mu_drift=0.10, sigma=1.75),
        book=BotBookConfig(half_spread_l1=6.5, depth_l1=16),
        arrivals=TradeArrivalConfig(arrival_prob=0.04, buy_prob=0.5, min_size=1, max_size=10),
        position_limit=limits["INTARIAN_PEPPER_ROOT"],
    )

    r1_cfgs = [
        MarketMakingConfig(symbol="ASH_COATED_OSMIUM", position_limit=80, quote_size=25),
        MarketMakingConfig(symbol="INTARIAN_PEPPER_ROOT", position_limit=80, quote_size=25),
    ]

    def _make_sym(cfgs: list[MarketMakingConfig] = r1_cfgs) -> BaseStrategy:
        return SymmetricMarketMaker(cfgs)

    def _make_sub() -> BaseStrategy:
        return CompetitionStrategyAdapter(trader=_load_round1_trader(), name="Round1Submission")

    scenarios: list[tuple[str, FillMode, float, float]] = [
        ("queue_aware", "queue_aware", 0.0, 0.0),
        ("conservative", "conservative", 0.0, 0.0),
        ("adverse_stress_qa", "queue_aware", 0.30, 6.0),
    ]
    print("\n=== Calibrated Round 1 Monte Carlo (40 sessions x 1,000 ticks, +/-80) ===")
    for label, fill_mode, adv_p, adv_j in scenarios:
        print(f"\n-- MC Regime: {label} (fill_mode={fill_mode}, adv_p={adv_p}) --")
        mc = MonteCarloEngine(
            assets=[osmium_cfg, pepper_cfg],
            fill_mode=fill_mode,
            adverse_selection_prob=adv_p,
            adverse_jump_size=adv_j,
        )
        for factory in (NoOpBaselineStrategy, _make_sym, _make_sub):
            summary = mc.run(factory, n_sessions=40, n_steps=1000, seed=42)
            k_loss = sum(1 for x in summary.pnl_distribution if x < 0.0)
            p_up = wilson_ci_upper(k_loss, summary.n_sessions)
            print(
                f"  {summary.strategy_name:<22} | MeanPnL={summary.mean_pnl:>9.2f} | "
                f"Std={summary.std_pnl:>8.2f} | VaR95={summary.var_95:>8.2f} | "
                f"CVaR95={summary.cvar_95:>8.2f} | ProbLoss={summary.prob_loss:.3f} "
                f"(95% up<={p_up:.3f})",
            )


def main() -> int:
    """Run Round 0 and Round 1 strategy comparisons."""
    if not Path("data/raw/prosperity4").exists():
        print("Raw data directory not found.")
        return 1

    r0_limits = {"EMERALDS": 20, "TOMATOES": 20}
    r1_limits = get_round_position_limits(1)

    evaluate_replay(0, -2, r0_limits)
    evaluate_replay(0, -1, r0_limits)
    evaluate_replay(1, -2, r1_limits)
    evaluate_replay(1, -1, r1_limits)
    evaluate_replay(1, 0, r1_limits)
    evaluate_monte_carlo()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
