"""Unit and integration tests for the vectorized Monte Carlo simulator."""

from __future__ import annotations

import math

import numpy as np

from prosperity_toolkit.cli import main as cli_main
from prosperity_toolkit.core.models import OrderRequest
from prosperity_toolkit.market.market_state import MarketStateSnapshot
from prosperity_toolkit.simulation import (
    AssetScenarioConfig,
    BotBookConfig,
    MonteCarloEngine,
    OrnsteinUhlenbeckParams,
    RandomWalkParams,
    TradeArrivalConfig,
    build_synthetic_book,
    generate_correlated_pulses,
    simulate_ou_paths,
    simulate_random_walk_paths,
    simulate_trade_arrivals,
)
from prosperity_toolkit.strategies.base import BaseStrategy
from prosperity_toolkit.strategies.baseline import NoOpBaselineStrategy


class _TestQuotingProbeStrategy(BaseStrategy):
    """Test-only passive quoting probe for verifying Monte Carlo fill mechanics."""

    def __init__(self) -> None:
        super().__init__(name="TestQuotingProbe")

    def generate_orders(self, state: MarketStateSnapshot) -> list[OrderRequest]:
        book = state.get_book("MC_ASSET")
        if book is None or book.best_bid is None or book.best_ask is None:
            return []
        pos = state.get_position("MC_ASSET")
        orders: list[OrderRequest] = []
        if pos < 5:
            orders.append(OrderRequest(symbol="MC_ASSET", price=book.best_bid + 1, quantity=1))
        if pos > -5:
            orders.append(OrderRequest(symbol="MC_ASSET", price=book.best_ask - 1, quantity=-1))
        return orders


def test_ou_stationary_moments_against_analytical() -> None:
    """Simulated OU terminal distribution must match theoretical mean and stationary std."""
    params = OrnsteinUhlenbeckParams(mu=10000.0, theta=0.2, sigma=4.0, initial_price=10000.0)
    rng = np.random.default_rng(12345)
    paths = simulate_ou_paths(params, n_sessions=2000, n_steps=100, rng=rng)

    assert paths.shape == (2000, 100)
    terminal = paths[:, -1]
    theoretical_std = params.stationary_std  # 4.0 / sqrt(0.4) ~= 6.324555

    assert abs(float(np.mean(terminal)) - params.mu) < 0.6
    assert abs(float(np.std(terminal, ddof=1)) - theoretical_std) < 0.6


def test_random_walk_variance_scaling() -> None:
    """Random walk terminal variance must scale linearly with time: sigma^2 * (n_steps - 1)."""
    params = RandomWalkParams(initial_price=5000.0, mu_drift=0.5, sigma=2.0, dt=1.0)
    rng = np.random.default_rng(99)
    n_steps = 50
    paths = simulate_random_walk_paths(params, n_sessions=3000, n_steps=n_steps, rng=rng)

    terminal = paths[:, -1]
    expected_mean = 5000.0 + 0.5 * (n_steps - 1)
    expected_std = 2.0 * math.sqrt(n_steps - 1)

    assert abs(float(np.mean(terminal)) - expected_mean) < 1.0
    assert abs(float(np.std(terminal, ddof=1)) - expected_std) < 1.0


def test_synthetic_book_invariants() -> None:
    """Synthetic order books must never cross and must use negative ask quantities."""
    cfg = BotBookConfig(half_spread_l1=0.0, depth_l1=15, step_l2=2, depth_l2=25)
    book = build_synthetic_book("OSMIUM", fair_value=10000.0, config=cfg)

    assert book.best_bid is not None and book.best_ask is not None
    assert book.best_bid < book.best_ask
    assert book.bids[book.best_bid] == 15
    assert book.asks[book.best_ask] == -15
    assert len(book.bids) == 2
    assert len(book.asks) == 2


def test_correlated_pulses_identical_across_assets() -> None:
    """Shared cross-asset pulses must be identical across the asset dimension."""
    rng = np.random.default_rng(7)
    pulses = generate_correlated_pulses(
        n_assets=3,
        n_sessions=10,
        n_steps=20,
        pulse_prob=0.2,
        pulse_sigma=5.0,
        rng=rng,
    )
    assert pulses.shape == (3, 10, 20)
    assert np.array_equal(pulses[0], pulses[1])
    assert np.array_equal(pulses[1], pulses[2])


def test_trade_arrivals_bounds() -> None:
    """Generated counterparty trade arrivals must respect size bounds."""
    cfg = TradeArrivalConfig(arrival_prob=0.5, buy_prob=0.5, min_size=2, max_size=4)
    arr = simulate_trade_arrivals(cfg, n_sessions=50, n_steps=100, rng=np.random.default_rng(1))
    non_zero = np.abs(arr[arr != 0])
    assert non_zero.size > 0
    assert int(np.min(non_zero)) >= 2
    assert int(np.max(non_zero)) <= 4


def test_monte_carlo_engine_deterministic_and_risk_metrics() -> None:
    """MonteCarloEngine must be deterministic for a fixed seed and satisfy CVaR <= VaR."""
    asset = AssetScenarioConfig(
        symbol="MC_ASSET",
        process=OrnsteinUhlenbeckParams(mu=10000.0, theta=0.1, sigma=2.0),
        book=BotBookConfig(half_spread_l1=2.0, depth_l1=10),
        arrivals=TradeArrivalConfig(arrival_prob=0.5, buy_prob=0.5, min_size=1, max_size=3),
        position_limit=10,
    )
    mc = MonteCarloEngine(assets=[asset], conservative_fills=False)

    noop_summary = mc.run(NoOpBaselineStrategy, n_sessions=10, n_steps=50, seed=42)
    assert noop_summary.mean_pnl == 0.0
    assert noop_summary.std_pnl == 0.0

    res1 = mc.run(_TestQuotingProbeStrategy, n_sessions=20, n_steps=60, seed=42)
    res2 = mc.run(_TestQuotingProbeStrategy, n_sessions=20, n_steps=60, seed=42)

    assert res1.pnl_distribution == res2.pnl_distribution
    assert res1.cvar_95 <= res1.var_95


def test_cli_mc_command() -> None:
    """Verify CLI mc subcommand executes cleanly."""
    exit_code = cli_main(["mc", "--sessions", "5", "--steps", "20", "--seed", "7"])
    assert exit_code == 0
