"""Unit tests for IMC Prosperity 4 Round 1-5 manual challenge solvers."""

from __future__ import annotations

import math

import numpy as np
import pytest

from prosperity_toolkit.analysis.manual_challenges import (
    AuctionOrder,
    ExoticContractSpec,
    annualized_to_step_sigma,
    clear_opening_auction,
    evaluate_gardeners_pair,
    optimal_research_given_speed,
    price_aether_crystal_contract,
    research_return,
    scale_factor,
    solve_round1_auction,
    solve_round1_uncertain_demand,
    solve_round2_cognitive_hierarchy,
    solve_round2_invest_and_expand,
    solve_round3_bayesian_belief,
    solve_round3_gardeners_guild,
    solve_round4_exotic_portfolio,
    solve_round5_extra_extra,
    solve_round5_risk_adjusted,
)


def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def test_round1_auction_clearing_tiebreak_and_late_priority() -> None:
    resting = [
        AuctionOrder(price=31, quantity=10),
        AuctionOrder(price=29, quantity=15),
        AuctionOrder(price=27, quantity=-10),
        AuctionOrder(price=29, quantity=-15),
    ]
    # At p=29: demand=25, supply=25 -> matched=25. At p=30: demand=10, supply=25 -> 10.
    base = clear_opening_auction(resting, buyback_price=30.0)
    assert base.clearing_price == 29
    assert base.matched_volume == 25
    assert base.participant_filled == 0

    # Highest-price tie-breaker when volume ties across two prices
    tied_book = [
        AuctionOrder(price=25, quantity=10),
        AuctionOrder(price=20, quantity=-10),
    ]
    tied_res = clear_opening_auction(tied_book, buyback_price=30.0)
    assert tied_res.matched_volume == 10
    assert tied_res.clearing_price == 25

    # Late entrant at clearing price queues behind resting at same price, ahead of lower bids
    queue_book = [
        AuctionOrder(price=32, quantity=10),
        AuctionOrder(price=30, quantity=10),
        AuctionOrder(price=28, quantity=-25),
    ]
    # Clearing price without entrant is 30 with vol 20. If participant bids 30 for 10,
    # total demand at 30 becomes 30, supply at 30 is 25 -> matched 25.
    # Resting at 32 gets 10, resting at 30 gets 10 -> participant gets 5.
    late_same = clear_opening_auction(
        queue_book,
        participant_order=AuctionOrder(price=30, quantity=10),
        buyback_price=35.0,
    )
    assert late_same.clearing_price == 30
    assert late_same.matched_volume == 25
    assert late_same.participant_filled == 5

    # Bidding strictly above 30 jumps ahead of resting at 30 and gets full 10 units
    late_jump = clear_opening_auction(
        queue_book,
        participant_order=AuctionOrder(price=31, quantity=10),
        buyback_price=35.0,
    )
    assert late_jump.participant_filled == 10
    assert late_jump.participant_pnl == pytest.approx(50.0)

    # Empty book returns zero match
    empty_order, empty_res = solve_round1_auction([], buyback_price=30.0)
    assert empty_order.quantity == 0
    assert empty_res.matched_volume == 0

    best_order, best_res = solve_round1_auction(queue_book, buyback_price=35.0, max_order_qty=20)
    assert best_res.participant_pnl >= late_jump.participant_pnl
    assert best_order.quantity != 0


def test_round2_invest_and_expand_tradeoffs() -> None:
    assert research_return(0.0) == pytest.approx(0.0)
    assert research_return(100.0) == pytest.approx(200_000.0)
    assert scale_factor(10.0) == pytest.approx(0.7)

    with pytest.raises(ValueError):
        research_return(-1.0)
    with pytest.raises(ValueError):
        scale_factor(-0.5)

    # Constant speed multiplier => optimal Speed share = 0%
    const_res = solve_round2_invest_and_expand(lambda _p: 0.5, total_budget=50_000.0, grid_step=1.0)
    assert const_res.speed_pct == pytest.approx(0.0)
    assert const_res.research_pct + const_res.scale_pct == pytest.approx(100.0)
    assert const_res.net_pnl > 0.0

    # Steeply rewarding speed CDF should pull allocation into Speed > 0
    def logistic_speed(p: float) -> float:
        return 0.1 + 0.8 / (1.0 + math.exp(-(p - 15.0) / 3.0))

    comp_res = solve_round2_invest_and_expand(logistic_speed, total_budget=50_000.0, grid_step=1.0)
    assert comp_res.speed_pct > 0.0
    assert comp_res.research_pct + comp_res.scale_pct + comp_res.speed_pct <= 100.0 + 1e-6


def test_round3_gardeners_guild_exact_ev_and_two_bid_dominance() -> None:
    # Single point check: b1 >= avg_b2 not reached -> penalty = 1 if b2 >= avg_b2
    reserves = [670, 770, 870, 920]
    ev_no_pen, acc_no_pen = evaluate_gardeners_pair(
        700, 880, avg_b2_belief=875.0, reserve_grid=reserves, resale_price=920
    )
    # 670 fills at 700 (+220); 770, 870 fill at 880 (+40 each); 920 rejects (+0) -> (220+80)/4 = 75
    assert ev_no_pen == pytest.approx(75.0)
    assert acc_no_pen == pytest.approx(0.75)

    # Penalty kicks in when b2 < avg_b2_belief
    ev_pen, acc_pen = evaluate_gardeners_pair(
        700, 860, avg_b2_belief=880.0, reserve_grid=reserves, resale_price=920
    )
    expected_pen = ((920.0 - 880.0) / (920.0 - 860.0)) ** 3
    assert acc_pen == pytest.approx((1.0 + expected_pen) / 4.0)
    assert ev_pen == pytest.approx((220.0 + expected_pen * 60.0) / 4.0)

    # Full Round 3 optimization: two distinct bids beat single-bid strategy (b1 == b2)
    opt = solve_round3_gardeners_guild(avg_b2_belief=875.0, bid_step=2)
    assert opt.bid_1 < opt.bid_2 < 920
    single_best = max(
        evaluate_gardeners_pair(b, b, avg_b2_belief=875.0)[0] for b in range(670, 920, 2)
    )
    assert opt.expected_profit_per_unit > single_best


def test_round4_aether_crystal_exotic_mc_and_identities() -> None:
    spot = 50.0
    step_sigma = 0.0251
    days = 14.0
    steps_per_day = 4
    total_vol = step_sigma * math.sqrt(days * steps_per_day)

    # Closed-form zero-rate Black-Scholes call at K=50
    d1 = 0.5 * total_vol
    d2 = -0.5 * total_vol
    bs_call = spot * _norm_cdf(d1) - spot * _norm_cdf(d2)

    spot_val = price_aether_crystal_contract(ExoticContractSpec(name="AC_SPOT", kind="spot"), spot)
    assert spot_val.fair_value == pytest.approx(50.0)
    assert spot_val.delta_fd == pytest.approx(1.0)

    call_spec = ExoticContractSpec(
        name="AC_14D_50C", kind="vanilla_call", strike=50.0, horizon_days=days
    )
    put_spec = ExoticContractSpec(
        name="AC_14D_50P", kind="vanilla_put", strike=50.0, horizon_days=days
    )
    ko_spec = ExoticContractSpec(
        name="AC_14D_45_KO", kind="knockout_put", strike=50.0, barrier=38.0, horizon_days=days
    )
    bin_spec = ExoticContractSpec(
        name="AC_14D_45_BP", kind="binary_put", strike=45.0, binary_payout=100.0, horizon_days=days
    )
    chooser_spec = ExoticContractSpec(
        name="AC_14D_CHOOSER", kind="chooser", strike=50.0, horizon_days=days, choice_day=7.0
    )

    call_res = price_aether_crystal_contract(call_spec, spot=spot, n_paths=30_000, seed=7)
    put_res = price_aether_crystal_contract(put_spec, spot=spot, n_paths=30_000, seed=7)
    ko_res = price_aether_crystal_contract(ko_spec, spot=spot, n_paths=30_000, seed=7)
    bin_res = price_aether_crystal_contract(bin_spec, spot=spot, n_paths=30_000, seed=7)
    ch_res = price_aether_crystal_contract(chooser_spec, spot=spot, n_paths=30_000, seed=7)

    assert abs(call_res.fair_value - bs_call) < 1e-10
    # Exact Put-Call Parity at K=S0 under zero rate (zero MC sampling discrepancy)
    assert call_res.fair_value == pytest.approx(put_res.fair_value, abs=1e-12)
    # Knock-out put strictly dominated by same-strike vanilla put
    assert 0.0 <= ko_res.knockout_prob < 1.0
    assert ko_res.fair_value < put_res.fair_value
    assert 0.0 < bin_res.fair_value < 100.0
    # Exact Rubinstein (1991) chooser exceeds vanilla at same strike
    assert ch_res.fair_value > call_res.fair_value
    assert ch_res.std_error == 0.0
    assert 0.0 < call_res.delta_fd < 1.0
    assert -1.0 < put_res.delta_fd < 0.0

    # Day-T realized chooser payoff std must strictly exceed Day-tc conditional BS std
    from prosperity_toolkit.analysis.manual_challenges import _bs_price, _pathwise_payoffs

    rng = np.random.default_rng(7)
    paths = spot * np.exp(
        np.cumsum(-0.5 * step_sigma**2 + step_sigma * rng.standard_normal((4000, 56)), axis=1)
    )
    realized_pays = _pathwise_payoffs(chooser_spec, spot, step_sigma, paths, 252.0)
    assert abs(float(np.mean(realized_pays)) - ch_res.fair_value) < 0.6
    ann_v = step_sigma * math.sqrt(steps_per_day * 252.0)
    rem_yr = 7.0 / 252.0
    cond_tc = np.array([
        max(
            _bs_price(float(sc), 50.0, rem_yr, ann_v, True),
            _bs_price(float(sc), 50.0, rem_yr, ann_v, False),
        )
        for sc in paths[:, 27]
    ])
    assert float(np.std(realized_pays, ddof=1)) > float(np.std(cond_tc, ddof=1)) + 1.0


def test_round5_extra_extra_kkt_complementarity() -> None:
    empty = solve_round5_extra_extra({})
    assert empty.expected_net_pnl == 0.0

    # Interior unconstrained case: 0.5 * (0.4 + 0.3) = 0.35 < 1.0 => lambda == 0
    interior = solve_round5_extra_extra({"GOOD_A": 0.40, "GOOD_B": -0.30}, budget=1_000_000.0)
    assert interior.shadow_price_lambda == pytest.approx(0.0)
    assert interior.weights_pct["GOOD_A"] == pytest.approx(20.0)
    assert interior.weights_pct["GOOD_B"] == pytest.approx(-15.0)
    assert interior.gross_exposure_pct == pytest.approx(35.0)

    # Binding gross exposure constraint: verify weak asset is pruned & active KKT marginal equalized
    edges = {"STRONG": 1.80, "MEDIUM": -1.20, "WEAK": 0.25, "FLAT": 0.05}
    res = solve_round5_extra_extra(edges, budget=1_000_000.0)
    assert res.gross_exposure_pct == pytest.approx(100.0, abs=1e-4)
    assert res.shadow_price_lambda > 0.25
    assert res.weights_pct["WEAK"] == 0.0
    assert res.weights_pct["FLAT"] == 0.0

    # Active KKT condition: |mu_i| - 2*|w_i| == lambda for every non-zero asset
    for sym, q_pct in res.weights_pct.items():
        if q_pct != 0.0:
            marginal = abs(edges[sym]) - 2.0 * abs(q_pct / 100.0)
            assert marginal == pytest.approx(res.shadow_price_lambda, abs=1e-5)

    # Verify solver strictly dominates putting 100% into the single best asset
    single_best_net = 1_000_000.0 * (1.80 * 1.0 - 1.0**2)
    assert res.expected_net_pnl > single_best_net


def test_advanced_manual_extensions_rounds_1_to_5() -> None:
    # R1 Bayesian clearing over random demand shocks
    flax = [
        AuctionOrder(30, 40),
        AuctionOrder(28, 60),
        AuctionOrder(26, -50),
        AuctionOrder(28, -50),
    ]
    r1_ord, r1_ev, r1_fr = solve_round1_uncertain_demand(
        flax, buyback_price=30.0, crowd_qty_mean=25.0, crowd_qty_std=10.0, n_draws=60, seed=42
    )
    assert r1_ord.quantity > 0
    assert r1_ev > 0.0
    assert 0.0 < r1_fr <= 1.0

    # R2 exact balance equation at Level-3 equilibrium 42% speed & Level-k escalation
    r42, s42 = optimal_research_given_speed(42.0)
    assert r42 + s42 == pytest.approx(58.0)
    assert (58.0 - r42) / (1.0 + r42) == pytest.approx(math.log1p(r42), abs=1e-5)

    ch_res = solve_round2_cognitive_hierarchy(total_budget=50_000.0, target_speed_pct=42.0)
    assert ch_res.level_solutions["L2"].speed_pct >= ch_res.level_solutions["L1"].speed_pct
    assert ch_res.focal_benchmark.speed_pct == pytest.approx(42.0)
    assert ch_res.ex_ante_recommended.net_pnl > 0.0

    # R3 Bayesian belief over uncertain cohort average b2
    b_res = solve_round3_bayesian_belief(mean_b2=875.0, std_b2=15.0, n_quad=11, bid_step=3)
    assert b_res.bid_1 < b_res.bid_2 < 920
    assert b_res.expected_profit_per_unit > 65.0

    # R4 authentic AETHER_CRYSTAL specs (sigma_ann=2.51, 4/day, 15d chooser, payout=10 binary)
    step_s = annualized_to_step_sigma(2.51, steps_per_day=4, days_per_year=252)
    assert step_s == pytest.approx(2.51 / math.sqrt(1008.0))
    specs = [
        ExoticContractSpec(
            name="AC_50_CO", kind="chooser", strike=50.0, horizon_days=15.0,
            choice_day=10.0, ask_price=22.20,
        ),
        ExoticContractSpec(
            name="AC_40_BP", kind="binary_put", strike=40.0, horizon_days=15.0,
            binary_payout=10.0, ask_price=5.00,
        ),
        ExoticContractSpec(
            name="AC_45_KO", kind="knockout_put", strike=45.0, barrier=35.0,
            horizon_days=15.0, steps_per_day=4, ask_price=0.175,
        ),
        ExoticContractSpec(
            name="AC_50_C15", kind="vanilla_call", strike=50.0, horizon_days=15.0, ask_price=11.92
        ),
        ExoticContractSpec(
            name="AC_50_P15", kind="vanilla_put", strike=50.0, horizon_days=15.0, ask_price=12.00
        ),
    ]
    bounds = {
        "AC_50_CO": (-50.0, 50.0),
        "AC_40_BP": (-50.0, 50.0),
        "AC_45_KO": (-500.0, 500.0),
        "AC_50_C15": (-100.0, 100.0),
        "AC_50_P15": (-100.0, 100.0),
    }
    port = solve_round4_exotic_portfolio(
        specs, lot_bounds=bounds, spot=50.0, annual_vol=2.51, n_paths=12_000, risk_aversion=0.0005
    )
    assert port.contract_edges["AC_50_CO"] < 0.0
    assert port.contract_edges["AC_40_BP"] < 0.0
    assert port.contract_edges["AC_45_KO"] > 0.0
    assert port.optimal_lots["AC_50_CO"] < 0.0
    assert port.optimal_lots["AC_45_KO"] > 0.0
    assert port.sharpe_ratio > port.unhedged_sharpe

    # R5 variance-penalized Ignith KKT allocation shrinks volatile assets relatively more
    r5_ra = solve_round5_risk_adjusted(
        expected_returns={"LOW_VOL": 0.60, "HIGH_VOL": 0.60},
        return_vols={"LOW_VOL": 0.10, "HIGH_VOL": 0.80},
        risk_aversion=1.0,
        budget=1_000_000.0,
    )
    assert r5_ra.weights_pct["LOW_VOL"] > r5_ra.weights_pct["HIGH_VOL"]
    assert r5_ra.gross_exposure_pct <= 100.0 + 1e-4
