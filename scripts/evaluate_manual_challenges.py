"""Reproducible Round 1-5 manual challenge evaluation and comparative statics."""

from __future__ import annotations

import csv
import math
from collections.abc import Callable
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

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


def _logistic_speed_factory(
    midpoint_pct: float, scale_pct: float = 3.0
) -> Callable[[float], float]:
    def _cdf(p: float) -> float:
        return 0.1 + 0.8 / (1.0 + math.exp(-(p - midpoint_pct) / scale_pct))

    return _cdf


def main() -> None:
    """Solve R1-R5 manual challenges across exact rules, Level-k game theory, and MC."""
    out_table_dir = Path("reports/tables")
    out_fig_dir = Path("reports/figures")
    out_table_dir.mkdir(parents=True, exist_ok=True)
    out_fig_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, object]] = []

    # ------------------------------------------------------------------
    # Round 1: "An Intarian Welcome" (Walrasian Auction + Demand Shocks)
    # ------------------------------------------------------------------
    flax_book = [
        AuctionOrder(32, 30),
        AuctionOrder(30, 50),
        AuctionOrder(28, 70),
        AuctionOrder(26, 90),
        AuctionOrder(25, -40),
        AuctionOrder(27, -60),
        AuctionOrder(28, -50),
        AuctionOrder(31, -40),
    ]
    ember_book = [
        AuctionOrder(22, 25),
        AuctionOrder(20, 45),
        AuctionOrder(18, 60),
        AuctionOrder(16, -35),
        AuctionOrder(18, -50),
        AuctionOrder(21, -45),
    ]
    flax_base = clear_opening_auction(flax_book, None, buyback_price=30.0, fee_per_unit=0.0)
    flax_opt, flax_res = solve_round1_auction(
        flax_book, buyback_price=30.0, fee_per_unit=0.0, max_order_qty=100
    )
    flax_at_clear = clear_opening_auction(
        flax_book,
        AuctionOrder(flax_base.clearing_price, flax_opt.quantity),
        buyback_price=30.0,
        fee_per_unit=0.0,
    )
    flax_bayes_ord, flax_bayes_ev, flax_bayes_fr = solve_round1_uncertain_demand(
        flax_book,
        buyback_price=30.0,
        fee_per_unit=0.0,
        crowd_qty_mean=45.0,
        crowd_qty_std=22.0,
        crowd_price_loc=29,
        n_draws=250,
        seed=42,
    )
    ember_opt, ember_res = solve_round1_auction(
        ember_book, buyback_price=20.0, fee_per_unit=0.10, max_order_qty=100
    )
    ember_bayes_ord, ember_bayes_ev, ember_bayes_fr = solve_round1_uncertain_demand(
        ember_book,
        buyback_price=20.0,
        fee_per_unit=0.10,
        crowd_qty_mean=30.0,
        crowd_qty_std=15.0,
        crowd_price_loc=19,
        n_draws=250,
        seed=42,
    )

    rows.extend(
        [
            {
                "round": "R1",
                "challenge": "An Intarian Welcome",
                "scenario": "DRYLAND_FLAX (static book)",
                "parameter": (
                    f"rest_clear={flax_base.clearing_price}, vol={flax_base.matched_volume}"
                ),
                "optimal_action": f"bid px={flax_opt.price}, qty={flax_opt.quantity}",
                "expected_metric": round(flax_res.participant_pnl, 2),
                "metric_unit": "XIRECs PnL",
                "assumption_note": "Buyback=30, fee=0; shaded below tipping size",
            },
            {
                "round": "R1",
                "challenge": "An Intarian Welcome",
                "scenario": "DRYLAND_FLAX (stochastic human demand)",
                "parameter": f"fill_rate={flax_bayes_fr:.2f}, crowd_N(45,22)",
                "optimal_action": (
                    f"bid px={flax_bayes_ord.price}, qty={flax_bayes_ord.quantity}"
                ),
                "expected_metric": round(flax_bayes_ev, 2),
                "metric_unit": "XIRECs Expected PnL",
                "assumption_note": "250 demand shocks around clearing threshold",
            },
            {
                "round": "R1",
                "challenge": "An Intarian Welcome",
                "scenario": "EMBER_MUSHROOM (stochastic human demand)",
                "parameter": f"fill_rate={ember_bayes_fr:.2f}, fee=0.10/unit",
                "optimal_action": (
                    f"bid px={ember_bayes_ord.price}, qty={ember_bayes_ord.quantity}"
                ),
                "expected_metric": round(ember_bayes_ev, 2),
                "metric_unit": "XIRECs Expected PnL",
                "assumption_note": (
                    f"Buyback=20, fee=0.10 (static opt={ember_res.participant_pnl:.2f})"
                ),
            },
        ]
    )

    # ------------------------------------------------------------------
    # Round 2: "Invest & Expand" (Level-k / CH Equilibrium Optimization)
    # ------------------------------------------------------------------
    ch_r2 = solve_round2_cognitive_hierarchy(total_budget=50_000.0)
    midpoints = [10.0, 18.0, 26.0, 34.0, 42.0]
    r2_sweep = [
        (
            mid,
            solve_round2_invest_and_expand(
                _logistic_speed_factory(midpoint_pct=mid, scale_pct=4.0),
                total_budget=50_000.0,
                grid_step=0.5,
            ),
        )
        for mid in midpoints
    ]

    for lvl_name in ("L1", "L2", "L3"):
        lv = ch_r2.level_solutions[lvl_name]
        rows.append(
            {
                "round": "R2",
                "challenge": "Invest & Expand",
                "scenario": f"Cognitive Hierarchy ({lvl_name} Best Response)",
                "parameter": f"speed_mult={lv.speed_multiplier:.3f}",
                "optimal_action": (
                    f"r={lv.research_pct:.2f}%, s={lv.scale_pct:.2f}%, p={lv.speed_pct:.1f}%"
                ),
                "expected_metric": round(lv.net_pnl, 2),
                "metric_unit": "XIRECs Net EV",
                "assumption_note": f"Iterated best-response step {lvl_name} against field belief",
            }
        )
    ea = ch_r2.ex_ante_recommended
    focal = ch_r2.focal_benchmark
    rows.extend(
        [
            {
                "round": "R2",
                "challenge": "Invest & Expand",
                "scenario": "Final Submitted Allocation (L3 Focal Equilibrium)",
                "parameter": f"speed_mult={focal.speed_multiplier:.3f}",
                "optimal_action": (
                    f"r={focal.research_pct:.2f}%, "
                    f"s={focal.scale_pct:.2f}%, p={focal.speed_pct:.1f}%"
                ),
                "expected_metric": round(focal.net_pnl, 2),
                "metric_unit": "XIRECs Net EV",
                "assumption_note": (
                    "Portal input (15%/43%/42% rounded); Level-3 stopping point on 42-44% ridge"
                ),
            },
            {
                "round": "R2",
                "challenge": "Invest & Expand",
                "scenario": "CH Mixture Stress Check (Unregularized QRE)",
                "parameter": f"speed_mult={ea.speed_multiplier:.3f}",
                "optimal_action": (
                    f"r={ea.research_pct:.2f}%, s={ea.scale_pct:.2f}%, p={ea.speed_pct:.1f}%"
                ),
                "expected_metric": round(ea.net_pnl, 2),
                "metric_unit": "XIRECs Net EV",
                "assumption_note": "Continuous L0-L3 best-response sensitivity upper edge",
            },
        ]
    )

    # ------------------------------------------------------------------
    # Round 3: "Celestial Gardeners' Guild" (Deterministic + Bayesian)
    # ------------------------------------------------------------------
    beliefs = [845.0, 860.0, 875.0, 885.0, 895.0, 905.0]
    r3_results = []
    for avg_b2 in beliefs:
        res_r3 = solve_round3_gardeners_guild(avg_b2_belief=avg_b2, bid_step=1)
        single_ev = max(
            evaluate_gardeners_pair(b, b, avg_b2_belief=avg_b2)[0] for b in range(670, 920)
        )
        r3_results.append((avg_b2, res_r3, single_ev))

    r3_bayes = solve_round3_bayesian_belief(mean_b2=875.0, std_b2=15.0, n_quad=17, bid_step=1)
    r3_cons = solve_round3_gardeners_guild(avg_b2_belief=860.0, bid_step=1)
    rows.extend(
        [
            {
                "round": "R3",
                "challenge": "Celestial Gardeners Guild",
                "scenario": "Final Submitted Bayesian Policy (avg_b2 ~ N(875, 15^2))",
                "parameter": f"resale=920, exp_acc={r3_bayes.expected_accept_prob:.3f}",
                "optimal_action": f"b1={r3_bayes.bid_1}, b2={r3_bayes.bid_2}",
                "expected_metric": round(r3_bayes.expected_profit_per_unit, 2),
                "metric_unit": "XIRECs EV/unit",
                "assumption_note": "Integrates asymmetric cubic cliff over cohort uncertainty",
            },
            {
                "round": "R3",
                "challenge": "Celestial Gardeners Guild",
                "scenario": "Conservative Cohort Point Sensitivity (avg_b2=860)",
                "parameter": f"resale=920, acc={r3_cons.expected_accept_prob:.3f}",
                "optimal_action": f"b1={r3_cons.bid_1}, b2={r3_cons.bid_2}",
                "expected_metric": round(r3_cons.expected_profit_per_unit, 2),
                "metric_unit": "XIRECs EV/unit",
                "assumption_note": "Ex-ante lower-crowd aggressiveness sensitivity bound",
            },
        ]
    )

    # ------------------------------------------------------------------
    # Round 4: "Vanilla Just Isn't Exotic Enough" (Exact sigma_ann=2.51)
    # ------------------------------------------------------------------
    step_sigma_real = annualized_to_step_sigma(annual_vol=2.51, steps_per_day=4, days_per_year=252)
    exotic_specs = [
        ExoticContractSpec(
            name="AC_50_CO",
            kind="chooser",
            strike=50.0,
            horizon_days=15.0,
            steps_per_day=4,
            choice_day=10.0,
            ask_price=22.20,
        ),
        ExoticContractSpec(
            name="AC_40_BP",
            kind="binary_put",
            strike=40.0,
            horizon_days=15.0,
            steps_per_day=4,
            binary_payout=10.0,
            ask_price=5.00,
        ),
        ExoticContractSpec(
            name="AC_45_KO",
            kind="knockout_put",
            strike=45.0,
            barrier=35.0,
            horizon_days=15.0,
            steps_per_day=4,
            ask_price=0.175,
        ),
        ExoticContractSpec(
            name="AC_50_C15",
            kind="vanilla_call",
            strike=50.0,
            horizon_days=15.0,
            steps_per_day=4,
            ask_price=11.92,
        ),
        ExoticContractSpec(
            name="AC_50_P15",
            kind="vanilla_put",
            strike=50.0,
            horizon_days=15.0,
            steps_per_day=4,
            ask_price=12.00,
        ),
    ]
    r4_vals = [
        price_aether_crystal_contract(
            spec, spot=50.0, step_sigma_log=step_sigma_real, n_paths=60_000, seed=42
        )
        for spec in exotic_specs
    ]
    # Continuous approximation counterfactual for AC_45_KO (hourly 24/d)
    ko_hourly = price_aether_crystal_contract(
        ExoticContractSpec(
            name="AC_45_KO_24H",
            kind="knockout_put",
            strike=45.0,
            barrier=35.0,
            horizon_days=15.0,
            steps_per_day=24,
            ask_price=0.175,
        ),
        spot=50.0,
        step_sigma_log=annualized_to_step_sigma(2.51, steps_per_day=24, days_per_year=252),
        n_paths=60_000,
        seed=42,
    )

    for spec, val in zip(exotic_specs, r4_vals, strict=True):
        edge = val.fair_value - spec.ask_price
        side = "BUY" if edge > 0.02 else ("SELL" if edge < -0.02 else "HEDGE")
        rows.append(
            {
                "round": "R4",
                "challenge": "Aether Crystal Exotics",
                "scenario": f"{spec.name} (ask={spec.ask_price:.3f})",
                "parameter": f"ko_p={val.knockout_prob:.3f}, delta={val.delta_fd:+.3f}",
                "optimal_action": f"{side} (edge={edge:+.4f})",
                "expected_metric": round(val.fair_value, 4),
                "metric_unit": "Fair Value (XIRECs)",
                "assumption_note": "S0=50, sigma_ann=251%, 15 trading days, 4/day GBM",
            }
        )
    rows.append(
        {
            "round": "R4",
            "challenge": "Aether Crystal Exotics",
            "scenario": "AC_45_KO (fine 24/day barrier)",
            "parameter": f"ko_p={ko_hourly.knockout_prob:.3f}, se={ko_hourly.std_error:.4f}",
            "optimal_action": "Shows BGK continuous-limit discount (< 4/day discrete)",
            "expected_metric": round(ko_hourly.fair_value, 4),
            "metric_unit": "Fair Value (XIRECs)",
            "assumption_note": "Explains why discrete monitoring commands positive ask edge",
        }
    )

    lot_bounds = {
        "AC_50_CO": (-50.0, 50.0),
        "AC_40_BP": (-50.0, 50.0),
        "AC_45_KO": (-500.0, 500.0),
        "AC_50_C15": (-100.0, 100.0),
        "AC_50_P15": (-100.0, 100.0),
    }
    r4_port = solve_round4_exotic_portfolio(
        exotic_specs,
        lot_bounds=lot_bounds,
        spot=50.0,
        annual_vol=2.51,
        n_paths=40_000,
        risk_aversion=0.00015,
        seed=42,
    )
    rows.append(
        {
            "round": "R4",
            "challenge": "Aether Crystal Exotics",
            "scenario": "Mean-Variance Hedged Basket",
            "parameter": (
                f"std_cut=-{r4_port.std_reduction_pct:.1f}%, CVaR95={r4_port.cvar_95:,.1f}"
            ),
            "optimal_action": (
                f"Sharpe={r4_port.sharpe_ratio:.3f} vs unhedged {r4_port.unhedged_sharpe:.3f}"
            ),
            "expected_metric": round(r4_port.expected_pnl, 2),
            "metric_unit": "Expected Portfolio EV",
            "assumption_note": "Short AC_50_CO & AC_40_BP, Long 500 AC_45_KO + straddle hedge",
        }
    )

    # ------------------------------------------------------------------
    # Round 5: "Extra! Extra!" (All 9 Ashflow Alpha Ignith Goods)
    # ------------------------------------------------------------------
    ashflow_edges = {
        "Thermalite Core": 1.35,      # Strong active-user smart-home expansion
        "Sulfur Reactor": 1.18,       # Elemental Index 118 passive tracker demand
        "Ashes of the Phoenix": -1.10, # Resurfaced negative sourcing video
        "Pyroflex Cells": -0.78,      # Tax-cut repeal headwind
        "Scoria Paste": 0.62,         # Stockpiling / maintenance demand
        "Obsidian Cutlery": -0.42,    # Assembly outage vs recovery uncertainty
        "Volcanic Incense": 0.24,     # Whiff Nostralico social hype noise
        "Magma Ink": -0.15,           # Ambiguous supply-chain chatter
        "Lava Cake": 0.06,            # Low-catalyst confectionery backdrop
    }
    ashflow_vols = {
        "Thermalite Core": 0.35,
        "Sulfur Reactor": 0.30,
        "Ashes of the Phoenix": 0.40,
        "Pyroflex Cells": 0.45,
        "Scoria Paste": 0.42,
        "Obsidian Cutlery": 0.60,
        "Volcanic Incense": 0.90,
        "Magma Ink": 0.70,
        "Lava Cake": 0.65,
    }
    r5_kkt = solve_round5_extra_extra(ashflow_edges, budget=1_000_000.0)
    r5_ra = solve_round5_risk_adjusted(
        ashflow_edges, ashflow_vols, risk_aversion=3.0, budget=1_000_000.0
    )

    n_goods = len(ashflow_edges)
    w_u = 1.0 / n_goods
    naive_net = 1_000_000.0 * (sum(abs(v) * w_u for v in ashflow_edges.values()) - n_goods * w_u**2)

    rows.extend(
        [
            {
                "round": "R5",
                "challenge": "Extra! Extra!",
                "scenario": "Ashflow Alpha Exact KKT (9 Ignith Goods)",
                "parameter": (
                    f"lambda*={r5_kkt.shadow_price_lambda:.4f}, "
                    f"gross={r5_kkt.gross_exposure_pct:.1f}%"
                ),
                "optimal_action": (
                    f"fees={r5_kkt.total_fees:,.0f}, "
                    f"active={sum(1 for v in r5_kkt.weights_pct.values() if abs(v) > 0)}/9"
                ),
                "expected_metric": round(r5_kkt.expected_net_pnl, 2),
                "metric_unit": "XIRECs Net EV",
                "assumption_note": (
                    f"Prunes noisy hype/mixed goods; vs naive 1/9 ({naive_net:,.0f})"
                ),
            },
            {
                "round": "R5",
                "challenge": "Extra! Extra!",
                "scenario": "Ashflow Alpha Risk-Adjusted KKT (kappa=3.0)",
                "parameter": (
                    f"lambda*={r5_ra.shadow_price_lambda:.4f}, "
                    f"gross={r5_ra.gross_exposure_pct:.1f}%"
                ),
                "optimal_action": (
                    f"fees={r5_ra.total_fees:,.0f}, "
                    f"active={sum(1 for v in r5_ra.weights_pct.values() if abs(v) > 0)}/9"
                ),
                "expected_metric": round(r5_ra.expected_net_pnl, 2),
                "metric_unit": "XIRECs Net EV",
                "assumption_note": "Down-weights high-variance uncertain catalysts to cap CVaR",
            },
        ]
    )

    csv_path = out_table_dir / "manual_challenges_summary.csv"
    fieldnames = [
        "round",
        "challenge",
        "scenario",
        "parameter",
        "optimal_action",
        "expected_metric",
        "metric_unit",
        "assumption_note",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    # ------------------------------------------------------------------
    # 6-Panel Portfolio Visualisation
    # ------------------------------------------------------------------
    plt.style.use("seaborn-v0_8-whitegrid")
    fig, axes = plt.subplots(2, 3, figsize=(16.5, 9.8), dpi=160)

    # Panel A: R1 Auction Clearing & Queue Priority
    ax = axes[0, 0]
    px_grid = list(range(24, 34))
    dem = [sum(o.quantity for o in flax_book if o.quantity > 0 and o.price >= p) for p in px_grid]
    sup = [sum(-o.quantity for o in flax_book if o.quantity < 0 and o.price <= p) for p in px_grid]
    ax.step(px_grid, dem, where="mid", label="Resting Demand", color="#1f77b4", lw=2.2)
    ax.step(px_grid, sup, where="mid", label="Resting Supply", color="#d62728", lw=2.2)
    ax.axvline(
        flax_base.clearing_price,
        color="#2ca02c",
        ls="--",
        lw=1.6,
        label=f"Clear p*={flax_base.clearing_price}",
    )
    ax.set_title(
        f"R1 Auction Clearing (Opt={flax_res.participant_pnl:.0f} "
        f"vs At-Clear={flax_at_clear.participant_pnl:.0f})",
        fontsize=10,
        fontweight="bold",
    )
    ax.set_xlabel("Auction Price")
    ax.set_ylabel("Cumulative Quantity")
    ax.legend(fontsize=8, loc="upper right")

    # Panel B: R2 Invest & Expand Allocation Curve + Level-3 / Mixture Speed Band
    ax = axes[0, 1]
    p_vals = np.linspace(0.0, 75.0, 151)
    r_curve = []
    s_curve = []
    base_k = []
    for pv in p_vals:
        rv, sv = optimal_research_given_speed(float(pv))
        r_curve.append(rv)
        s_curve.append(sv)
        base_k.append(research_return(rv) * scale_factor(sv) / 1000.0)
    h_r = ax.plot(p_vals, r_curve, label="Optimal Research r*(p)", color="#1f77b4", lw=2.0)
    h_s = ax.plot(p_vals, s_curve, label="Optimal Scale s*(p)", color="#ff7f0e", lw=2.0)
    ax.axvline(
        focal.speed_pct,
        color="#d62728",
        ls=":",
        lw=2.0,
        label=f"Submitted L3 Focal {focal.speed_pct:.0f}%",
    )
    ax.axvline(
        ea.speed_pct, color="#2ca02c", ls="--", lw=1.8, label=f"Mixture Stress {ea.speed_pct:.0f}%"
    )
    ax2 = ax.twinx()
    h_b = ax2.plot(p_vals, base_k, "--", color="#9467bd", lw=1.6, label="Base Res*Scale (k)")
    ax2.grid(False)
    ax2.set_ylabel("Base Research*Scale (k)", color="#9467bd", fontsize=9)
    ax.set_title("R2 Invest & Expand: Budget Frontier vs Speed (p)", fontsize=10, fontweight="bold")
    ax.set_xlabel("Speed Allocation p (%)")
    ax.set_ylabel("Optimal Research / Scale Share (%)")
    h_b_all = h_r + h_s + h_b
    lines, labels = ax.get_legend_handles_labels()
    l2, lb2 = ax2.get_legend_handles_labels()
    ax.legend(lines + l2, labels + lb2, fontsize=7.5, loc="upper right")
    _ = h_b_all

    # Panel C: R3 Gardeners' Guild EV & (b1*, b2*) vs Crowd Avg b2
    ax = axes[0, 2]
    b_beliefs = [x[0] for x in r3_results]
    b1_stars = [x[1].bid_1 for x in r3_results]
    b2_stars = [x[1].bid_2 for x in r3_results]
    ev_two = [x[1].expected_profit_per_unit for x in r3_results]
    ev_one = [x[2] for x in r3_results]
    c1 = ax.plot(b_beliefs, b1_stars, "o-", label="Optimal b1*", color="#1f77b4")
    c2 = ax.plot(b_beliefs, b2_stars, "s-", label="Optimal b2*", color="#d62728")
    ax.axvline(875.0, color="gray", ls=":", lw=1.6, label="Bayesian Prior Mean=875")
    ax3 = ax.twinx()
    c3 = ax3.plot(b_beliefs, ev_two, "^--", color="#2ca02c", label="2-Bid EV")
    c4 = ax3.plot(b_beliefs, ev_one, "x:", color="#8c564b", label="1-Bid EV")
    ax3.grid(False)
    ax3.set_ylabel("Expected Profit / Unit", color="#2ca02c", fontsize=9)
    ax.set_title("R3 Gardeners' Guild Optimal Bids vs Crowd Avg b2", fontsize=10, fontweight="bold")
    ax.set_xlabel("Crowd Mean Second-Bid Belief")
    ax.set_ylabel("Bid Price")
    l1, lb1 = ax.get_legend_handles_labels()
    l3, lb3 = ax3.get_legend_handles_labels()
    _ = c1 + c2 + c3 + c4
    ax.legend(l1 + l3, lb1 + lb3, fontsize=7.5, loc="center left")

    # Panel D: R4 Aether Crystal Market Quote vs Exact Fair Value (sigma_ann=251%)
    ax = axes[1, 0]
    labels_d = ["AC_50_CO\n(SELL 22.2)", "AC_40_BP\n(SELL 5.0)", "AC_45_KO\n(BUY 0.175)"]
    fairs_d = [r4_vals[0].fair_value, r4_vals[1].fair_value, r4_vals[2].fair_value]
    asks_d = [22.20, 5.00, 0.175]
    x_d = np.arange(3)
    w_d = 0.36
    b_fair = ax.bar(x_d - w_d / 2, fairs_d, w_d, label="MC Fair Value", color="#1f77b4")
    b_ask = ax.bar(x_d + w_d / 2, asks_d, w_d, label="Market Quote", color="#ff7f0e")
    for bar, v in zip(b_fair, fairs_d, strict=True):
        ax.text(
            bar.get_x() + bar.get_width() / 2.0,
            v + 0.4,
            f"{v:.2f}",
            ha="center",
            va="bottom",
            fontsize=7.5,
        )
    for bar, v in zip(b_ask, asks_d, strict=True):
        ax.text(
            bar.get_x() + bar.get_width() / 2.0,
            v + 0.4,
            f"{v:.3f}" if v < 1 else f"{v:.2f}",
            ha="center",
            va="bottom",
            fontsize=7.5,
        )
    ax.set_ylim(0, max(asks_d) * 1.18)
    ax.set_xticks(x_d)
    ax.set_xticklabels(labels_d, fontsize=8)
    ax.set_title("R4 Aether Crystal Mispricings (251% Ann Vol)", fontsize=10, fontweight="bold")
    ax.set_ylabel("Option Price (XIRECs)")
    ax.legend(fontsize=8)

    # Panel E: R4 Discrete 4/d vs 24/d Barrier Monitoring (BGK Effect)
    ax = axes[1, 1]
    barriers = [30.0, 32.5, 35.0, 37.5, 40.0, 42.5]
    s4 = annualized_to_step_sigma(2.51, 4, 252)
    s24 = annualized_to_step_sigma(2.51, 24, 252)
    ko_4 = [
        price_aether_crystal_contract(
            ExoticContractSpec(
                name=f"KO4_{b}",
                kind="knockout_put",
                strike=45.0,
                barrier=b,
                horizon_days=15.0,
                steps_per_day=4,
            ),
            spot=50.0,
            step_sigma_log=s4,
            n_paths=25_000,
            seed=42,
        ).fair_value
        for b in barriers
    ]
    ko_24 = [
        price_aether_crystal_contract(
            ExoticContractSpec(
                name=f"KO24_{b}",
                kind="knockout_put",
                strike=45.0,
                barrier=b,
                horizon_days=15.0,
                steps_per_day=24,
            ),
            spot=50.0,
            step_sigma_log=s24,
            n_paths=25_000,
            seed=42,
        ).fair_value
        for b in barriers
    ]
    ax.plot(barriers, ko_4, "o-", label="4/day Discrete Monitoring", color="#1f77b4", lw=2.0)
    ax.plot(barriers, ko_24, "s--", label="24/day Near-Continuous", color="#d62728", lw=2.0)
    ax.axhline(0.175, color="#2ca02c", ls=":", lw=1.6, label="AC_45_KO Ask (0.175)")
    ax.axvline(35.0, color="gray", ls="--", lw=1.2)
    ax.set_title("R4 AC_45_KO Discrete Monitoring Survival Edge", fontsize=10, fontweight="bold")
    ax.set_xlabel("Down-and-Out Barrier")
    ax.set_ylabel("Fair Value (XIRECs)")
    ax.legend(fontsize=8)

    # Panel F: R5 Ignith 9-Good KKT vs Risk-Adjusted Allocation
    ax = axes[1, 2]
    goods = list(ashflow_edges.keys())
    short_g = [g.replace("of the ", "") for g in goods]
    w_pure = [r5_kkt.weights_pct[g] for g in goods]
    w_ra = [r5_ra.weights_pct[g] for g in goods]
    xg = np.arange(len(goods))
    wg = 0.38
    ax.bar(xg - wg / 2, w_pure, wg, label="Pure KKT", color="#2ca02c")
    ax.bar(xg + wg / 2, w_ra, wg, label="Risk-Adj KKT", color="#1f77b4", alpha=0.85)
    ax.axhline(0.0, color="black", lw=0.8)
    ax.set_xticks(xg)
    ax.set_xticklabels(short_g, rotation=32, ha="right", fontsize=7.0)
    ax.set_title(
        f"R5 Ashflow Alpha KKT (Net {r5_kkt.expected_net_pnl / 1e3:.0f}k vs "
        f"1/9 {naive_net / 1e3:.0f}k)",
        fontsize=9.5,
        fontweight="bold",
    )
    ax.set_ylabel("Portfolio Weight (% of 1M)")
    ax.legend(fontsize=8)

    fig.suptitle(
        "IMC Prosperity 4 — Manual Challenges Analytical & Monte Carlo Summary",
        fontsize=13,
        fontweight="bold",
        y=0.99,
    )
    plt.tight_layout(rect=(0.0, 0.0, 1.0, 0.96))
    fig_path = out_fig_dir / "manual_challenges_analysis.png"
    fig.savefig(fig_path, dpi=160)
    plt.close(fig)

    print(f"Wrote {csv_path} ({len(rows)} rows) and {fig_path}")
    print(
        f"R1 Flax static={flax_opt}->{flax_res.participant_pnl:.2f}; "
        f"Bayes={flax_bayes_ord}->{flax_bayes_ev:.2f} (fr={flax_bayes_fr:.2f})"
    )
    print(f"R1 Ember Bayes={ember_bayes_ord}->{ember_bayes_ev:.2f} (fr={ember_bayes_fr:.2f})")
    for k, lv in ch_r2.level_solutions.items():
        print(
            f"R2 {k}: r={lv.research_pct:.2f}%, s={lv.scale_pct:.2f}%, "
            f"p={lv.speed_pct:.1f}%, net={lv.net_pnl:,.2f}"
        )
    print(
        f"R2 Mixture={ea.research_pct:.2f}%/{ea.scale_pct:.2f}%/{ea.speed_pct:.1f}% "
        f"net={ea.net_pnl:,.2f} | SubmittedL3={focal.research_pct:.2f}%/{focal.scale_pct:.2f}%/"
        f"{focal.speed_pct:.1f}% net={focal.net_pnl:,.2f}"
    )
    for b_mid, b_r2 in r2_sweep:
        print(
            f"  R2 logistic mid={b_mid:.0f}% -> r={b_r2.research_pct:.1f}, "
            f"s={b_r2.scale_pct:.1f}, p={b_r2.speed_pct:.1f}, net={b_r2.net_pnl:,.0f}"
        )
    print(
        f"R3 Bayes N(875,15): b1={r3_bayes.bid_1}, b2={r3_bayes.bid_2}, "
        f"EV={r3_bayes.expected_profit_per_unit:.2f} | "
        f"Cons860: ({r3_cons.bid_1},{r3_cons.bid_2}) "
        f"EV={r3_cons.expected_profit_per_unit:.2f}"
    )
    for spec, val in zip(exotic_specs, r4_vals, strict=True):
        print(
            f"R4 {spec.name}: fair={val.fair_value:.4f} (SE={val.std_error:.4f}) "
            f"ask={spec.ask_price:.3f} edge={val.fair_value - spec.ask_price:+.4f} "
            f"KO={val.knockout_prob:.4f} delta={val.delta_fd:+.4f}"
        )
    print(f"R4 KO_24H: fair={ko_hourly.fair_value:.4f}, KO={ko_hourly.knockout_prob:.4f}")
    print(
        f"R4 Portfolio: lots={r4_port.optimal_lots}, EV={r4_port.expected_pnl:,.2f}, "
        f"std={r4_port.pnl_std:,.2f}, Sharpe={r4_port.sharpe_ratio:.4f} "
        f"(unhedged={r4_port.unhedged_sharpe:.4f}, std_cut=-{r4_port.std_reduction_pct:.1f}%)"
    )
    print(
        f"R5 KKT: lam={r5_kkt.shadow_price_lambda:.4f}, "
        f"gross={r5_kkt.gross_exposure_pct:.1f}%, "
        f"fees={r5_kkt.total_fees:,.0f}, net={r5_kkt.expected_net_pnl:,.2f} "
        f"(naive={naive_net:,.0f})"
    )
    print(f"  R5 KKT w={r5_kkt.weights_pct}")
    print(
        f"R5 Risk-Adj: lam={r5_ra.shadow_price_lambda:.4f}, "
        f"gross={r5_ra.gross_exposure_pct:.1f}%, net={r5_ra.expected_net_pnl:,.2f}"
    )
    print(f"  R5 Risk-Adj w={r5_ra.weights_pct}")


if __name__ == "__main__":
    main()
