"""Reproducible evaluation of Round 0 and Round 1 baseline vs candidate strategies."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from prosperity_toolkit.backtesting.engine import BacktestEngine
from prosperity_toolkit.backtesting.replay import build_snapshots_from_dataframes
from prosperity_toolkit.competition.adapter import (
    CompetitionStrategyAdapter,
    CompetitionTraderProtocol,
)
from prosperity_toolkit.data.loader import DataLoader
from prosperity_toolkit.execution.simulator import ExecutionSimulator, FillMode
from prosperity_toolkit.simulation import (
    AssetScenarioConfig,
    BotBookConfig,
    MonteCarloEngine,
    OrnsteinUhlenbeckParams,
    RandomWalkParams,
    TradeArrivalConfig,
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


def _load_round1_trader() -> CompetitionTraderProtocol:
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
    trader: CompetitionTraderProtocol = mod.Trader()
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
                MarketMakingConfig(symbol="ASH_COATED_OSMIUM", position_limit=20),
                MarketMakingConfig(symbol="INTARIAN_PEPPER_ROOT", position_limit=20),
            ]
            pepper_cfg = DriftAwareConfig(symbol="INTARIAN_PEPPER_ROOT", position_limit=20)
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
            extra = ""
            if isinstance(strat, CompetitionStrategyAdapter):
                extra = f", mean_latency_ms={strat.mean_latency_ms:.4f}"
            print(
                f"  {res.strategy_name:<22} | PnL={res.total_pnl:>10.2f} | "
                f"MaxDD={res.max_drawdown:>8.2f} | Sharpe={res.sharpe_ratio:>6.2f} | "
                f"Fills={len(res.fills):>5}{extra}",
            )


def evaluate_monte_carlo() -> None:
    """Run calibrated Monte Carlo simulation using Day -2/-1 Round 1 empirical estimates."""
    osmium_cfg = AssetScenarioConfig(
        symbol="ASH_COATED_OSMIUM",
        process=OrnsteinUhlenbeckParams(mu=9999.5, theta=0.11, sigma=1.97),
        book=BotBookConfig(half_spread_l1=8.0, depth_l1=14),
        arrivals=TradeArrivalConfig(arrival_prob=0.042, buy_prob=0.5, min_size=1, max_size=9),
        position_limit=20,
    )
    pepper_cfg = AssetScenarioConfig(
        symbol="INTARIAN_PEPPER_ROOT",
        process=RandomWalkParams(initial_price=11000.0, mu_drift=0.10, sigma=1.68),
        book=BotBookConfig(half_spread_l1=6.5, depth_l1=11),
        arrivals=TradeArrivalConfig(arrival_prob=0.034, buy_prob=0.5, min_size=1, max_size=9),
        position_limit=20,
    )

    print("\n=== Calibrated Round 1 Monte Carlo (30 sessions x 500 ticks, seed=42) ===")
    for conservative in (True, False):
        label = "conservative" if conservative else "touch"
        print(f"\n-- MC Fill Regime: {label} --")
        mc = MonteCarloEngine(assets=[osmium_cfg, pepper_cfg], conservative_fills=conservative)

        r1_cfgs = [
            MarketMakingConfig(symbol="ASH_COATED_OSMIUM", position_limit=20),
            MarketMakingConfig(symbol="INTARIAN_PEPPER_ROOT", position_limit=20),
        ]
        def _make_sym(cfgs: list[MarketMakingConfig] = r1_cfgs) -> BaseStrategy:
            return SymmetricMarketMaker(cfgs)

        def _make_sub() -> BaseStrategy:
            return CompetitionStrategyAdapter(
                trader=_load_round1_trader(),
                name="Round1Submission",
            )

        factories = [
            NoOpBaselineStrategy,
            _make_sym,
            _make_sub,
        ]
        for factory in factories:
            summary = mc.run(factory, n_sessions=30, n_steps=500, seed=42)
            print(
                f"  {summary.strategy_name:<22} | MeanPnL={summary.mean_pnl:>9.2f} | "
                f"Std={summary.std_pnl:>8.2f} | VaR95={summary.var_95:>8.2f} | "
                f"CVaR95={summary.cvar_95:>8.2f} | ProbLoss={summary.prob_loss:.2f}",
            )


def main() -> int:
    """Run Round 0 and Round 1 strategy comparisons."""
    if not Path("data/raw/prosperity4").exists():
        print("Raw data directory not found.")
        return 1

    r0_limits = {"EMERALDS": 20, "TOMATOES": 20}
    r1_limits = {"ASH_COATED_OSMIUM": 20, "INTARIAN_PEPPER_ROOT": 20}

    evaluate_replay(0, -2, r0_limits)
    evaluate_replay(0, -1, r0_limits)
    evaluate_replay(1, -2, r1_limits)
    evaluate_replay(1, -1, r1_limits)
    evaluate_replay(1, 0, r1_limits)
    evaluate_monte_carlo()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
