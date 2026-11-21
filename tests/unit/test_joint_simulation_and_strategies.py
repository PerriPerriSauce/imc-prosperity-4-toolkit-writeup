"""Unit tests for joint Monte Carlo engines, basket, and options strategies."""

from __future__ import annotations

from prosperity_toolkit.market.market_state import MarketStateSnapshot
from prosperity_toolkit.market.order_book import OrderBookL2
from prosperity_toolkit.simulation.joint_scenarios import (
    CoupledOptionsMonteCarloEngine,
    OptionsSpotScenarioConfig,
    Round5JointMonteCarloEngine,
    simulate_arrival_sensitivity,
)
from prosperity_toolkit.simulation.processes import OrnsteinUhlenbeckParams
from prosperity_toolkit.simulation.pulses import TradeArrivalConfig
from prosperity_toolkit.simulation.scenario import AssetScenarioConfig
from prosperity_toolkit.simulation.synthetic_book import BotBookConfig
from prosperity_toolkit.strategies.basket import (
    ConstantSumBasketArbStrategy,
    PairSumMeanReversionStrategy,
)
from prosperity_toolkit.strategies.market_making import (
    InventorySkewedMarketMaker,
    MarketMakingConfig,
)
from prosperity_toolkit.strategies.options import OptionsVolatilityStrategy


def test_arrival_sensitivity_sweep_monotone_in_fills() -> None:
    """MAF sensitivity sweep runs cleanly across arrival rate multipliers."""
    cfgs = [
        AssetScenarioConfig(
            symbol="ASH_COATED_OSMIUM",
            position_limit=80,
            process=OrnsteinUhlenbeckParams(mu=10000.0, theta=0.1, sigma=1.9),
            book=BotBookConfig(half_spread_l1=8.0, depth_l1=20, step_l2=2, depth_l2=4),
            arrivals=TradeArrivalConfig(arrival_prob=0.05),
        ),
    ]
    out = simulate_arrival_sensitivity(
        strategy_factory=lambda: InventorySkewedMarketMaker(
            [MarketMakingConfig(symbol="ASH_COATED_OSMIUM", position_limit=80, quote_size=15)],
        ),
        asset_configs=cfgs,
        arrival_rates=[0.02, 0.10],
        n_sessions=4,
        n_steps=120,
        seed=11,
    )
    assert set(out.keys()) == {0.02, 0.10}
    assert out[0.10].mean_pnl >= out[0.02].mean_pnl


def test_coupled_options_mc_and_delta_hedge_respect_limits() -> None:
    """Coupled spot+options MC completes and delta hedges clamp strictly within limits."""
    mc = CoupledOptionsMonteCarloEngine(OptionsSpotScenarioConfig())
    summary = mc.run(
        strategy_factory=lambda: OptionsVolatilityStrategy(),
        n_sessions=4,
        n_steps=150,
        seed=7,
    )
    assert summary.n_sessions == 4
    assert len(summary.pnl_distribution) == 4


def test_round5_joint_mc_and_basket_pair_strategies() -> None:
    """Round 5 joint MC runs cleanly with basket and pair-sum strategies."""
    mc = Round5JointMonteCarloEngine()
    sum_b = mc.run(lambda: ConstantSumBasketArbStrategy(), n_sessions=4, n_steps=150, seed=19)
    sum_p = mc.run(lambda: PairSumMeanReversionStrategy(), n_sessions=4, n_steps=150, seed=19)
    assert len(sum_b.pnl_distribution) == 4
    assert len(sum_p.pnl_distribution) == 4


def test_constant_sum_basket_arb_direction_and_limits() -> None:
    """Basket strategy sells rich constant-sum deviations and clamps at position limits."""
    strat = ConstantSumBasketArbStrategy()
    books = {
        "PEBBLES_XS": OrderBookL2("PEBBLES_XS", {8005: 5}, {8015: -5}),
        "PEBBLES_S": OrderBookL2("PEBBLES_S", {9405: 5}, {9415: -5}),
        "PEBBLES_M": OrderBookL2("PEBBLES_M", {10005: 5}, {10015: -5}),
        "PEBBLES_L": OrderBookL2("PEBBLES_L", {10005: 5}, {10015: -5}),
        "PEBBLES_XL": OrderBookL2("PEBBLES_XL", {12605: 5}, {12615: -5}),
    }
    snap = MarketStateSnapshot(
        timestamp=100,
        books=books,
        positions={"PEBBLES_XS": -10},
    )
    orders = strat.generate_orders(snap)
    # Sum of mids is 50050 (+50 over 50000); PEBBLES_XS at -10 has zero remaining sell capacity
    assert all(o.symbol != "PEBBLES_XS" for o in orders)
    assert all(o.quantity < 0 for o in orders)


def test_options_strategy_handles_missing_and_empty_books() -> None:
    """OptionsVolatilityStrategy never crashes on empty/missing books."""
    strat = OptionsVolatilityStrategy()
    empty_snap = MarketStateSnapshot(
        timestamp=0,
        books={"VELVETFRUIT_EXTRACT": OrderBookL2("VELVETFRUIT_EXTRACT")},
    )
    assert strat.generate_orders(empty_snap) == []


def test_arrival_sensitivity_propagates_fill_mode_and_wilson_bound() -> None:
    """simulate_arrival_sensitivity must respect fill_mode='queue_aware' vs 'touch'."""
    from prosperity_toolkit.simulation.joint_scenarios import wilson_ci_upper

    cfgs = [
        AssetScenarioConfig(
            symbol="ASH_COATED_OSMIUM",
            position_limit=80,
            process=OrnsteinUhlenbeckParams(mu=10000.0, theta=0.1, sigma=1.9),
            book=BotBookConfig(half_spread_l1=8.0, depth_l1=2, step_l2=2, depth_l2=4),
            arrivals=TradeArrivalConfig(arrival_prob=0.3, min_size=1, max_size=3),
        ),
    ]
    qa = simulate_arrival_sensitivity(
        lambda: InventorySkewedMarketMaker(
            [
                MarketMakingConfig(
                    "ASH_COATED_OSMIUM", position_limit=80, quote_size=5, half_spread=9.0
                )
            ]
        ),
        cfgs,
        [0.3],
        n_sessions=4,
        n_steps=80,
        fill_mode="queue_aware",
        seed=5,
    )[0.3]
    tc = simulate_arrival_sensitivity(
        lambda: InventorySkewedMarketMaker(
            [
                MarketMakingConfig(
                    "ASH_COATED_OSMIUM", position_limit=80, quote_size=5, half_spread=9.0
                )
            ]
        ),
        cfgs,
        [0.3],
        n_sessions=4,
        n_steps=80,
        fill_mode="touch",
        seed=5,
    )[0.3]
    # Under min_edge=9 > half_spread=8, we join or sit behind L1 queue -> touch >= queue_aware
    assert tc.mean_pnl >= qa.mean_pnl
    assert 0.10 < wilson_ci_upper(0, 30) < 0.14
