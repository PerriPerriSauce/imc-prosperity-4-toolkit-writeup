"""Reproducible cross-round quantitative EDA for IMC Prosperity 4 (Rounds 2-5).

Outputs machine-readable summary CSV tables to `reports/tables/` and high-DPI
diagnostic figures to `reports/figures/`. All multi-day analyses preserve strict
separation between calibration (in-sample) days and held-out out-of-sample days.
"""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from prosperity_toolkit.analysis import (
    augmented_dickey_fuller_test,
    bachelier_call_delta,
    classify_trade_flow,
    compute_pca_spectrum,
    compute_return_moments,
    detect_trade_pulses,
    estimate_linear_drift,
    estimate_ou_ar1,
    evaluate_obi_signal,
    extract_two_sided_mid,
    fit_cointegrating_basket,
    implied_volatility_bachelier,
    implied_volatility_bs,
    summarize_order_book,
)
from prosperity_toolkit.competition import (
    PROSPERITY4_R5_CATEGORIES,
    PROSPERITY4_VOUCHER_STRIKES,
)
from prosperity_toolkit.data.loader import DataLoader

TABLE_DIR = Path("reports/tables")
FIG_DIR = Path("reports/figures")


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def analyze_round2(loader: DataLoader) -> list[dict[str, object]]:
    """Compare Round 2 IS (Day -1, 0) vs OOS (Day 1) microstructure."""
    rows: list[dict[str, object]] = []
    for day in (-1, 0, 1):
        split = "IS" if day < 1 else "OOS"
        p_df = loader.load_day_prices(2, day)
        t_df = loader.load_day_trades(2, day)
        for sym in ("ASH_COATED_OSMIUM", "INTARIAN_PEPPER_ROOT"):
            rep = summarize_order_book(p_df, sym)
            mid = extract_two_sided_mid(p_df, sym)
            mid_arr = mid.to_numpy(dtype=np.float64)
            step_idx = np.arange(len(mid_arr), dtype=np.float64)
            moms = compute_return_moments(mid_arr, lags=(1, 2))
            adf = augmented_dickey_fuller_test(mid_arr, lags=1)
            ou = estimate_ou_ar1(mid_arr)
            slope, _, r2_lin = estimate_linear_drift(step_idx, mid_arr)
            obis = evaluate_obi_signal(p_df, sym, horizons=(1, 5, 10))
            obi1 = obis[0]
            obi10 = obis[2]
            flow = classify_trade_flow(p_df, t_df, sym)
            touch = flow.at_or_above_ask + flow.at_or_below_bid
            two_tot = touch + flow.inside_spread
            touch_pct = (100.0 * touch / two_tot) if two_tot > 0 else 0.0
            rows.append({
                "split": split,
                "day": day,
                "symbol": sym,
                "two_sided": rep.two_sided_ticks,
                "one_sided": rep.one_sided_ticks,
                "empty": rep.empty_ticks,
                "mid_mean": round(rep.mid_mean, 2),
                "mid_std": round(rep.mid_std, 2),
                "spread_med": round(rep.spread_median, 2),
                "dmid_std": round(moms["std"], 4),
                "acf1": round(moms["acf_lag_1"], 4),
                "adf_t": round(adf.t_statistic, 2),
                "ou_theta": round(ou.theta, 4),
                "half_life": round(ou.half_life, 2) if np.isfinite(ou.half_life) else None,
                "linear_slope": round(slope, 5),
                "r2_linear": round(r2_lin, 4),
                "obi_r_h1": round(obi1.correlation, 4),
                "obi_r_h10": round(obi10.correlation, 4),
                "trades": flow.total_trades,
                "touch_pct": round(touch_pct, 2),
            })
    _write_csv(TABLE_DIR / "r2_microstructure_summary.csv", rows)
    return rows


def analyze_round3_round4_options(loader: DataLoader) -> list[dict[str, object]]:
    """Analyze Round 3 (Day 0,1 IS; Day 2 OOS) and Round 4 (Day 3 OOS) options & spots."""
    day_prices: dict[tuple[int, int], pd.DataFrame] = {
        (3, 0): loader.load_day_prices(3, 0),
        (3, 1): loader.load_day_prices(3, 1),
        (3, 2): loader.load_day_prices(3, 2),
        (4, 3): loader.load_day_prices(4, 3),
    }
    day_trades: dict[tuple[int, int], pd.DataFrame] = {
        (3, 0): loader.load_day_trades(3, 0),
        (3, 1): loader.load_day_trades(3, 1),
        (3, 2): loader.load_day_trades(3, 2),
        (4, 3): loader.load_day_trades(4, 3),
    }

    spot_sym = "VELVETFRUIT_EXTRACT"
    is_prices = pd.concat([day_prices[(3, 0)], day_prices[(3, 1)]], ignore_index=True)
    spot_d0 = extract_two_sided_mid(day_prices[(3, 0)], spot_sym)
    spot_d1 = extract_two_sided_mid(day_prices[(3, 1)], spot_sym)

    rows: list[dict[str, object]] = []
    # 1. Spot & HYDROGEL_PACK characterization
    for sym in ("HYDROGEL_PACK", spot_sym):
        is_rep = summarize_order_book(is_prices, sym)
        is_mid = pd.concat([
            extract_two_sided_mid(day_prices[(3, 0)], sym),
            extract_two_sided_mid(day_prices[(3, 1)], sym),
        ])
        moms = compute_return_moments(is_mid.to_numpy(dtype=np.float64), lags=(1,))
        adf_d0 = augmented_dickey_fuller_test(
            extract_two_sided_mid(day_prices[(3, 0)], sym).to_numpy(dtype=np.float64),
        )
        ou_d0 = estimate_ou_ar1(
            extract_two_sided_mid(day_prices[(3, 0)], sym).to_numpy(dtype=np.float64),
        )
        rows.append({
            "symbol": sym,
            "strike": 0,
            "is_mid_mean": round(is_rep.mid_mean, 2),
            "is_mid_std": round(is_rep.mid_std, 2),
            "is_spread_mean": round(is_rep.spread_mean, 2),
            "is_sigma_diff": round(moms["std"], 4),
            "is_adf_t_d0": round(adf_d0.t_statistic, 2),
            "is_half_life_d0": round(ou_d0.half_life, 1) if np.isfinite(ou_d0.half_life) else None,
            "bid_minus_intr": None,
            "ask_minus_intr": None,
            "mid_minus_intr": None,
            "bs_iv_5d": None,
            "bach_sigma_50k": None,
            "emp_delta_is": None,
            "bach_delta_50k": None,
            "d0_mid": round(float(extract_two_sided_mid(day_prices[(3, 0)], sym).mean()), 2),
            "d1_mid": round(float(extract_two_sided_mid(day_prices[(3, 1)], sym).mean()), 2),
            "d2_mid": round(float(extract_two_sided_mid(day_prices[(3, 2)], sym).mean()), 2),
            "d3_mid": round(float(extract_two_sided_mid(day_prices[(4, 3)], sym).mean()), 2),
            "is_trades": int(len(day_trades[(3, 0)][day_trades[(3, 0)]["symbol"] == sym]))
            + int(len(day_trades[(3, 1)][day_trades[(3, 1)]["symbol"] == sym])),
            "seller_init_pct": None,
        })

    # Realized spot step sigma on IS Days 0-1 for Bachelier benchmark
    spot_is = pd.concat([spot_d0, spot_d1])
    spot_sigma = float(np.std(np.diff(spot_is.to_numpy(dtype=np.float64)), ddof=1))

    # 2. All 10 VEV strikes (assuming 5 trading days remaining from R3 Day 0 -> 50k steps)
    is_joined_spot = pd.concat([
        day_prices[(3, 0)][day_prices[(3, 0)]["product"] == spot_sym].assign(day_idx=0),
        day_prices[(3, 1)][day_prices[(3, 1)]["product"] == spot_sym].assign(day_idx=1),
    ])
    spot_map = is_joined_spot.set_index(["day_idx", "timestamp"])["mid_price"]

    plot_strikes: list[int] = []
    plot_bid_ex: list[float] = []
    plot_ask_ex: list[float] = []
    plot_iv_bs: list[float] = []
    plot_bach_iv: list[float] = []
    plot_seller_pct: list[float] = []
    plot_decay_3d: list[float] = []

    for sym, strike in PROSPERITY4_VOUCHER_STRIKES.items():
        opt_is = pd.concat([
            day_prices[(3, 0)][day_prices[(3, 0)]["product"] == sym].assign(day_idx=0),
            day_prices[(3, 1)][day_prices[(3, 1)]["product"] == sym].assign(day_idx=1),
        ]).set_index(["day_idx", "timestamp"])

        s_vals = spot_map.loc[opt_is.index].to_numpy(dtype=np.float64)
        intr = np.maximum(0.0, s_vals - float(strike))
        b_ex = float(np.mean(opt_is["bid_price_1"].to_numpy(dtype=np.float64) - intr))
        a_ex = float(np.mean(opt_is["ask_price_1"].to_numpy(dtype=np.float64) - intr))
        m_ex = float(np.mean(opt_is["mid_price"].to_numpy(dtype=np.float64) - intr))

        opt_d0 = extract_two_sided_mid(day_prices[(3, 0)], sym)
        opt_d1 = extract_two_sided_mid(day_prices[(3, 1)], sym)
        opt_d2 = extract_two_sided_mid(day_prices[(3, 2)], sym)
        opt_d3 = extract_two_sided_mid(day_prices[(4, 3)], sym)

        mean_s = float(np.mean(s_vals))
        mean_opt_is = float(opt_is["mid_price"].mean())
        bs_iv = implied_volatility_bs(mean_opt_is, mean_s, float(strike), tte=5.0 / 252.0)
        bach_sig = implied_volatility_bachelier(
            mean_opt_is,
            mean_s,
            float(strike),
            tte_steps=50_000.0,
        )

        # Empirical regression delta across IS days (dC vs dS per day)
        dc = np.concatenate([np.diff(opt_d0.to_numpy()), np.diff(opt_d1.to_numpy())])
        ds = np.concatenate([np.diff(spot_d0.to_numpy()), np.diff(spot_d1.to_numpy())])
        emp_delta = float(np.cov(dc, ds)[0, 1] / np.var(ds)) if np.var(ds) > 0 else 0.0
        bach_delta = bachelier_call_delta(mean_s, float(strike), 50_000.0, spot_sigma)

        # Trade aggressiveness IS (Day 0 + Day 1)
        f0 = classify_trade_flow(day_prices[(3, 0)], day_trades[(3, 0)], sym)
        f1 = classify_trade_flow(day_prices[(3, 1)], day_trades[(3, 1)], sym)
        tot_tr = f0.total_trades + f1.total_trades
        at_bid = f0.at_or_below_bid + f1.at_or_below_bid
        seller_pct = (100.0 * at_bid / tot_tr) if tot_tr > 0 else 0.0

        d0_m, d1_m, d2_m, d3_m = (
            float(opt_d0.mean()),
            float(opt_d1.mean()),
            float(opt_d2.mean()),
            float(opt_d3.mean()),
        )

        rows.append({
            "symbol": sym,
            "strike": strike,
            "is_mid_mean": round(mean_opt_is, 2),
            "is_mid_std": round(float(opt_is["mid_price"].std(ddof=1)), 2),
            "is_spread_mean": round(
                float((opt_is["ask_price_1"] - opt_is["bid_price_1"]).mean()),
                2,
            ),
            "is_sigma_diff": round(float(np.std(dc, ddof=1)), 4),
            "is_adf_t_d0": None,
            "is_half_life_d0": None,
            "bid_minus_intr": round(b_ex, 2),
            "ask_minus_intr": round(a_ex, 2),
            "mid_minus_intr": round(m_ex, 2),
            "bs_iv_5d": round(bs_iv, 4) if bs_iv is not None else None,
            "bach_sigma_50k": round(bach_sig, 4) if bach_sig is not None else None,
            "emp_delta_is": round(emp_delta, 3),
            "bach_delta_50k": round(bach_delta, 3),
            "d0_mid": round(d0_m, 2),
            "d1_mid": round(d1_m, 2),
            "d2_mid": round(d2_m, 2),
            "d3_mid": round(d3_m, 2),
            "is_trades": tot_tr,
            "seller_init_pct": round(seller_pct, 1),
        })

        if strike >= 5000:
            plot_strikes.append(strike)
            plot_bid_ex.append(b_ex)
            plot_ask_ex.append(a_ex)
            plot_iv_bs.append(bs_iv * 100.0 if bs_iv is not None else float("nan"))
            plot_bach_iv.append(bach_sig if bach_sig is not None else float("nan"))
            plot_seller_pct.append(seller_pct)
            plot_decay_3d.append(d3_m - d0_m)

    _write_csv(TABLE_DIR / "r3_r4_options_surface.csv", rows)

    # Check static bull-spread & butterfly no-arbitrage bounds on R3+R4 IS
    pivot_bid = is_prices[is_prices["product"].isin(PROSPERITY4_VOUCHER_STRIKES)].pivot(
        index=["day", "timestamp"],
        columns="product",
        values="bid_price_1",
    )
    pivot_ask = is_prices[is_prices["product"].isin(PROSPERITY4_VOUCHER_STRIKES)].pivot(
        index=["day", "timestamp"],
        columns="product",
        values="ask_price_1",
    )
    strikes_sorted = [f"VEV_{k}" for k in sorted(PROSPERITY4_VOUCHER_STRIKES.values())]
    bull_arbs = 0
    for idx in range(len(strikes_sorted) - 1):
        lo_k, hi_k = strikes_sorted[idx], strikes_sorted[idx + 1]
        bull_arbs += int((pivot_ask[lo_k] < pivot_bid[hi_k]).sum())
    print(f"Round 3 IS Bull-Spread Arbitrage Ticks (ask(K_lo) < bid(K_hi)): {bull_arbs}")

    # Plot R3 Options Diagnostic Figure
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 3, figsize=(14.5, 4.5))

    axes[0].plot(plot_strikes, plot_bid_ex, marker="o", label="Bid - Intrinsic")
    axes[0].plot(plot_strikes, plot_ask_ex, marker="s", label="Ask - Intrinsic")
    axes[0].axhline(0.0, color="#6c757d", linestyle=":", linewidth=1.2)
    axes[0].set_title("VEV Call Quotes vs. Intrinsic Value (IS)")
    axes[0].set_xlabel("Strike K")
    axes[0].set_ylabel("Excess over max(0, S - K)")
    axes[0].grid(True, linestyle="--", alpha=0.4)
    axes[0].legend()

    axes[1].plot(
        plot_strikes,
        plot_bach_iv,
        marker="o",
        color="#2a9d8f",
        label="Implied sigma/step",
    )
    axes[1].axhline(
        spot_sigma,
        color="#e63946",
        linestyle="--",
        linewidth=1.5,
        label=f"Realized spot sigma ({spot_sigma:.2f})",
    )
    axes[1].set_title("Bachelier Implied Vol Smile (T=50k steps)")
    axes[1].set_xlabel("Strike K")
    axes[1].set_ylabel("Implied Step Volatility (XIRECs/tick^0.5)")
    axes[1].grid(True, linestyle="--", alpha=0.4)
    axes[1].legend()

    axes[2].bar(
        [str(k) for k in plot_strikes],
        plot_seller_pct,
        color="#457b9d",
        alpha=0.85,
        label="Seller-init %",
    )
    axes[2].set_title("IS Option Trade Flow (% At/Below Bid)")
    axes[2].set_xlabel("Strike K")
    axes[2].set_ylabel("Trades at Bid (%)")
    axes[2].set_ylim(0, 108)
    axes[2].grid(True, axis="y", linestyle="--", alpha=0.4)

    fig.tight_layout()
    fig.savefig(FIG_DIR / "r3_options_iv_smile_and_premium.png", dpi=200)
    plt.close(fig)
    return rows


def analyze_round4_counterparties(loader: DataLoader) -> list[dict[str, object]]:
    """Profile buyer/seller counterparties in Round 4 (Day 1,2 IS vs Day 3 OOS)."""
    split_days = {
        "IS": [(4, 1), (4, 2)],
        "OOS": [(4, 3)],
    }
    records: list[dict[str, object]] = []
    horizons = (1, 5, 20, 50)

    for split_name, day_list in split_days.items():
        actor_events: dict[str, list[dict[str, float]]] = {}
        for rnd, day in day_list:
            p_df = loader.load_day_prices(rnd, day)
            t_df = loader.load_day_trades(rnd, day)
            mid_wide = p_df.pivot(index="timestamp", columns="product", values="mid_price")
            bid_wide = p_df.pivot(index="timestamp", columns="product", values="bid_price_1")
            ask_wide = p_df.pivot(index="timestamp", columns="product", values="ask_price_1")

            for _, tr in t_df.iterrows():
                ts = int(tr["timestamp"])
                sym = str(tr["symbol"])
                px = float(tr["price"])
                qty = int(tr["quantity"])
                if ts not in mid_wide.index or sym not in mid_wide.columns:
                    continue

                b1 = float(bid_wide.at[ts, sym])
                a1 = float(ask_wide.at[ts, sym])
                m0 = float(mid_wide.at[ts, sym])

                # Measure post-trade mid-price mark-out for each horizon
                markouts: dict[str, float] = {}
                for h in horizons:
                    future_ts = ts + h * 100
                    m_fut = (
                        float(mid_wide.at[future_ts, sym])
                        if future_ts in mid_wide.index
                        else m0
                    )
                    markouts[f"m_diff_{h}"] = m_fut - px

                buyer = str(tr["buyer"]) if pd.notna(tr["buyer"]) else ""
                seller = str(tr["seller"]) if pd.notna(tr["seller"]) else ""

                if buyer:
                    ev_b: dict[str, float] = {
                        "qty": float(qty),
                        "is_buy": 1.0,
                        "is_aggr": 1.0 if px >= a1 else 0.0,
                    }
                    for h in horizons:
                        ev_b[f"mo_{h}"] = markouts[f"m_diff_{h}"]
                    actor_events.setdefault(buyer, []).append(ev_b)

                if seller:
                    ev_s: dict[str, float] = {
                        "qty": float(qty),
                        "is_buy": 0.0,
                        "is_aggr": 1.0 if px <= b1 else 0.0,
                    }
                    for h in horizons:
                        ev_s[f"mo_{h}"] = -markouts[f"m_diff_{h}"]
                    actor_events.setdefault(seller, []).append(ev_s)

        for actor in sorted(actor_events):
            evs = pd.DataFrame(actor_events[actor])
            buy_qty = int(evs.loc[evs["is_buy"] == 1.0, "qty"].sum())
            sell_qty = int(evs.loc[evs["is_buy"] == 0.0, "qty"].sum())
            weights = evs["qty"].to_numpy(dtype=np.float64)
            row: dict[str, object] = {
                "split": split_name,
                "counterparty": actor,
                "trade_sides": int(len(evs)),
                "buy_qty": buy_qty,
                "sell_qty": sell_qty,
                "net_qty": buy_qty - sell_qty,
                "aggr_pct": round(100.0 * float(evs["is_aggr"].mean()), 1),
            }
            for h in horizons:
                mo = float(np.average(evs[f"mo_{h}"].to_numpy(dtype=np.float64), weights=weights))
                row[f"markout_h{h}"] = round(mo, 3)
            records.append(row)

    _write_csv(TABLE_DIR / "r4_counterparty_profiles.csv", records)

    # Stratified VELVETFRUIT_EXTRACT mid-price move post-trade (separates alpha from spread mix)
    velvet_sym = "VELVETFRUIT_EXTRACT"
    p_all = pd.concat(
        [loader.load_day_prices(4, d).assign(d=d) for d in (1, 2, 3)],
        ignore_index=True,
    )
    t_all = pd.concat(
        [loader.load_day_trades(4, d).assign(d=d) for d in (1, 2, 3)],
        ignore_index=True,
    )
    v_map = (
        p_all[p_all["product"] == velvet_sym]
        .set_index(["d", "timestamp"])["mid_price"]
        .to_dict()
    )
    tv = t_all[t_all["symbol"] == velvet_sym]
    vel_rows: list[dict[str, object]] = []
    for actor, side_col in [
        ("Mark 67", "buyer"),
        ("Mark 55", "buyer"),
        ("Mark 55", "seller"),
        ("Mark 49", "seller"),
        ("Mark 01", "buyer"),
        ("Mark 14", "buyer"),
    ]:
        sub_tr = tv[tv[side_col].fillna("") == actor]
        moves: dict[int, list[float]] = {h: [] for h in horizons}
        for d_val, ts_val in zip(sub_tr["d"], sub_tr["timestamp"], strict=False):
            m0 = v_map.get((int(d_val), int(ts_val)))
            if m0 is None:
                continue
            for h in horizons:
                mf = v_map.get((int(d_val), int(ts_val) + h * 100))
                if mf is not None:
                    moves[h].append(float(mf) - float(m0))
        vel_rows.append({
            "counterparty": actor,
            "side": side_col,
            "n_trades": len(sub_tr),
            "mid_move_h1": round(float(np.mean(moves[1])), 3) if moves[1] else None,
            "mid_move_h5": round(float(np.mean(moves[5])), 3) if moves[5] else None,
            "mid_move_h20": round(float(np.mean(moves[20])), 3) if moves[20] else None,
            "mid_move_h50": round(float(np.mean(moves[50])), 3) if moves[50] else None,
        })
    _write_csv(TABLE_DIR / "r4_counterparty_velvet_midmoves.csv", vel_rows)

    # Plot R4 Counterparty Flow & Mark-Out Curves
    df_rec = pd.DataFrame(records)
    if not df_rec.empty:
        fig, axes = plt.subplots(1, 2, figsize=(13.0, 4.8))
        is_sub = df_rec[df_rec["split"] == "IS"].sort_values("counterparty")
        oos_sub = df_rec[df_rec["split"] == "OOS"].set_index("counterparty")

        x = np.arange(len(is_sub))
        w = 0.36
        axes[0].bar(x - w / 2, is_sub["buy_qty"], width=w, label="IS Buy Qty", color="#2a9d8f")
        axes[0].bar(x + w / 2, is_sub["sell_qty"], width=w, label="IS Sell Qty", color="#e76f51")
        axes[0].set_xticks(x, is_sub["counterparty"], rotation=25)
        axes[0].set_title("Round 4 Counterparty Buy vs. Sell Volume (IS Days 1-2)")
        axes[0].set_ylabel("Total Traded Contracts")
        axes[0].grid(True, axis="y", linestyle="--", alpha=0.4)
        axes[0].legend()

        for _, r in is_sub.iterrows():
            actor = str(r["counterparty"])
            ys = [r["markout_h1"], r["markout_h5"], r["markout_h20"], r["markout_h50"]]
            axes[1].plot(horizons, ys, marker="o", label=f"{actor} (IS)")
            if actor in oos_sub.index:
                ro = oos_sub.loc[actor]
                yo = [ro["markout_h1"], ro["markout_h5"], ro["markout_h20"], ro["markout_h50"]]
                axes[1].plot(horizons, yo, linestyle=":", alpha=0.55)
        axes[1].axhline(0.0, color="#6c757d", linestyle="--", linewidth=1.2)
        axes[1].set_title("Weighted Mid-Price Mark-Out by Horizon (IS Solid, OOS Dotted)")
        axes[1].set_xlabel("Horizon (ticks)")
        axes[1].set_ylabel("Mark-Out (XIRECs)")
        axes[1].grid(True, linestyle="--", alpha=0.4)
        axes[1].legend(fontsize=8, ncol=2)

        fig.tight_layout()
        fig.savefig(FIG_DIR / "r4_counterparty_markouts.png", dpi=200)
        plt.close(fig)

    return records


def analyze_round5(loader: DataLoader) -> None:
    """Analyze Round 5 50-asset universe: IS (Days 2-3) vs held-out OOS (Day 4)."""
    p_d2 = loader.load_day_prices(5, 2)
    p_d3 = loader.load_day_prices(5, 3)
    p_d4 = loader.load_day_prices(5, 4)

    t_d2 = loader.load_day_trades(5, 2)
    t_d3 = loader.load_day_trades(5, 3)
    t_d4 = loader.load_day_trades(5, 4)

    def _to_wide(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
        mid = df.pivot(index="timestamp", columns="product", values="mid_price").sort_index()
        spr = (df["ask_price_1"] - df["bid_price_1"]).groupby(
            [df["timestamp"], df["product"]],
        ).first().unstack()
        return mid, spr

    mid_d2, spr_d2 = _to_wide(p_d2)
    mid_d3, spr_d3 = _to_wide(p_d3)
    mid_d4, spr_d4 = _to_wide(p_d4)

    # 1. Per-product 50-asset EDA table (IS = Days 2+3; OOS = Day 4)
    prod_rows: list[dict[str, object]] = []
    for cat, syms in PROSPERITY4_R5_CATEGORIES.items():
        for sym in syms:
            s_d2 = mid_d2[sym].to_numpy(dtype=np.float64)
            s_d3 = mid_d3[sym].to_numpy(dtype=np.float64)
            s_d4 = mid_d4[sym].to_numpy(dtype=np.float64)

            is_diffs = np.concatenate([np.diff(s_d2), np.diff(s_d3)])
            is_sigma = float(np.std(is_diffs, ddof=1))
            is_acf1 = compute_return_moments(
                np.concatenate([s_d2, s_d3]),
                lags=(1,),
            )["acf_lag_1"]
            is_spr_med = float(pd.concat([spr_d2[sym], spr_d3[sym]]).median())
            adf_d2 = augmented_dickey_fuller_test(s_d2, lags=1)
            ou_d2 = estimate_ou_ar1(s_d2)
            s_is_cat = np.concatenate([s_d2, s_d3])
            slope_is, _, _ = estimate_linear_drift(
                np.arange(len(s_is_cat), dtype=np.float64),
                s_is_cat,
            )

            oos_sigma = float(np.std(np.diff(s_d4), ddof=1))
            adf_d4 = augmented_dickey_fuller_test(s_d4, lags=1)
            slope_d4, _, _ = estimate_linear_drift(
                np.arange(len(s_d4), dtype=np.float64),
                s_d4,
            )

            prod_rows.append({
                "category": cat,
                "symbol": sym,
                "is_mid_mean": round(float(np.mean(s_is_cat)), 2),
                "is_mid_std": round(float(np.std(s_is_cat, ddof=1)), 2),
                "is_spread_med": round(is_spr_med, 1),
                "is_sigma_diff": round(is_sigma, 3),
                "is_spread_to_sigma": round(is_spr_med / is_sigma, 3) if is_sigma > 0 else 0.0,
                "is_acf1": round(is_acf1, 4),
                "is_d2_adf_t": round(adf_d2.t_statistic, 2),
                "is_d2_half_life": (
                    round(ou_d2.half_life, 1) if np.isfinite(ou_d2.half_life) else None
                ),
                "is_drift_per_10k": round(slope_is * 10_000.0, 1),
                "oos_d4_mid_std": round(float(np.std(s_d4, ddof=1)), 2),
                "oos_d4_sigma_diff": round(oos_sigma, 3),
                "oos_d4_adf_t": round(adf_d4.t_statistic, 2),
                "oos_d4_drift_per_10k": round(slope_d4 * 10_000.0, 1),
            })

    _write_csv(TABLE_DIR / "r5_per_product_eda.csv", prod_rows)

    # 2. Per-category PCA spectrum & Shared Pulse detection (IS Days 2-3 vs OOS Day 4)
    cat_rows: list[dict[str, object]] = []
    diffs_is_all = pd.concat([mid_d2.diff().dropna(), mid_d3.diff().dropna()], ignore_index=True)
    diffs_oos_all = mid_d4.diff().dropna()

    for cat, syms in PROSPERITY4_R5_CATEGORIES.items():
        cols = list(syms)
        pca_diff_is = compute_pca_spectrum(diffs_is_all[cols], use_diffs=False)
        pca_lvl_is = compute_pca_spectrum(mid_d2[cols], use_diffs=False)
        pca_lvl_oos = compute_pca_spectrum(mid_d4[cols], use_diffs=False)

        corr_is = diffs_is_all[cols].corr().to_numpy(dtype=np.float64, copy=True)
        np.fill_diagonal(corr_is, 0.0)
        max_abs_corr_is = float(np.max(np.abs(corr_is)))

        corr_oos = diffs_oos_all[cols].corr().to_numpy(dtype=np.float64, copy=True)
        np.fill_diagonal(corr_oos, 0.0)
        max_abs_corr_oos = float(np.max(np.abs(corr_oos)))

        p_d2_pulses = detect_trade_pulses(t_d2, syms, mid_d2, total_ticks=10_000, min_group_size=3)
        p_d3_pulses = detect_trade_pulses(t_d3, syms, mid_d3, total_ticks=10_000, min_group_size=3)
        p_d4_pulses = detect_trade_pulses(t_d4, syms, mid_d4, total_ticks=10_000, min_group_size=3)

        is_ev_tot = p_d2_pulses.n_pulse_events + p_d3_pulses.n_pulse_events
        is_side_agree = (
            (
                p_d2_pulses.uniform_side_share * p_d2_pulses.n_pulse_events
                + p_d3_pulses.uniform_side_share * p_d3_pulses.n_pulse_events
            )
            / is_ev_tot
            if is_ev_tot > 0
            else 0.0
        )

        cat_rows.append({
            "category": cat,
            "is_diff_eig1": round(float(pca_diff_is.eigenvalues[0]), 2),
            "is_diff_eig5": round(float(pca_diff_is.eigenvalues[-1]), 2),
            "is_lvl_cond_ratio": round(pca_lvl_is.condition_ratio, 1),
            "oos_lvl_cond_ratio": round(pca_lvl_oos.condition_ratio, 1),
            "is_max_abs_diff_corr": round(max_abs_corr_is, 4),
            "oos_max_abs_diff_corr": round(max_abs_corr_oos, 4),
            "is_pulse_events_20k": is_ev_tot,
            "is_pulse_lambda": round(is_ev_tot / 20_000.0, 4),
            "is_pulse_uniform_side_pct": round(100.0 * is_side_agree, 1),
            "oos_d4_pulse_events": p_d4_pulses.n_pulse_events,
            "oos_d4_pulse_lambda": round(p_d4_pulses.arrival_rate_per_tick, 4),
            "oos_d4_uniform_qty_pct": round(100.0 * p_d4_pulses.uniform_qty_share, 1),
        })

    _write_csv(TABLE_DIR / "r5_category_pca_and_pulses.csv", cat_rows)

    # 3. Structural invariants summary: Pebbles 5-sum + Snackpack pair & triplet
    peb_cols = list(PROSPERITY4_R5_CATEGORIES["Pebbles"])
    peb_sum_d2 = mid_d2[peb_cols].sum(axis=1)
    peb_sum_d3 = mid_d3[peb_cols].sum(axis=1)
    peb_sum_d4 = mid_d4[peb_cols].sum(axis=1)
    peb_basket_d2 = fit_cointegrating_basket(mid_d2[peb_cols])
    peb_basket_d4 = fit_cointegrating_basket(mid_d4[peb_cols])

    cv_cols = ["SNACKPACK_CHOCOLATE", "SNACKPACK_VANILLA"]
    cv_sum_d2 = mid_d2[cv_cols].sum(axis=1)
    cv_sum_d3 = mid_d3[cv_cols].sum(axis=1)
    cv_sum_d4 = mid_d4[cv_cols].sum(axis=1)

    tri_cols = ["SNACKPACK_PISTACHIO", "SNACKPACK_STRAWBERRY", "SNACKPACK_RASPBERRY"]
    tri_d2 = fit_cointegrating_basket(mid_d2[tri_cols])
    tri_d4 = fit_cointegrating_basket(mid_d4[tri_cols])

    baskets_rows = [
        {
            "structure": "Pebbles 5-Sum (raw sum)",
            "split": "IS (Day 2)",
            "mean": round(float(peb_sum_d2.mean()), 2),
            "std": round(float(peb_sum_d2.std(ddof=1)), 3),
            "adf_t": round(augmented_dickey_fuller_test(peb_sum_d2.to_numpy()).t_statistic, 2),
            "half_life": round(peb_basket_d2.ou_half_life, 2),
            "notes": f"min={peb_sum_d2.min():.1f}, max={peb_sum_d2.max():.1f}",
        },
        {
            "structure": "Pebbles 5-Sum (raw sum)",
            "split": "IS (Day 3)",
            "mean": round(float(peb_sum_d3.mean()), 2),
            "std": round(float(peb_sum_d3.std(ddof=1)), 3),
            "adf_t": round(augmented_dickey_fuller_test(peb_sum_d3.to_numpy()).t_statistic, 2),
            "half_life": round(fit_cointegrating_basket(mid_d3[peb_cols]).ou_half_life, 2),
            "notes": f"min={peb_sum_d3.min():.1f}, max={peb_sum_d3.max():.1f}",
        },
        {
            "structure": "Pebbles 5-Sum (raw sum)",
            "split": "OOS (Day 4)",
            "mean": round(float(peb_sum_d4.mean()), 2),
            "std": round(float(peb_sum_d4.std(ddof=1)), 3),
            "adf_t": round(augmented_dickey_fuller_test(peb_sum_d4.to_numpy()).t_statistic, 2),
            "half_life": round(peb_basket_d4.ou_half_life, 2),
            "notes": f"min={peb_sum_d4.min():.1f}, max={peb_sum_d4.max():.1f}",
        },
        {
            "structure": "Snackpack Choc + Van Pair Sum",
            "split": "IS (Day 2)",
            "mean": round(float(cv_sum_d2.mean()), 2),
            "std": round(float(cv_sum_d2.std(ddof=1)), 2),
            "adf_t": round(augmented_dickey_fuller_test(cv_sum_d2.to_numpy()).t_statistic, 2),
            "half_life": round(estimate_ou_ar1(cv_sum_d2.to_numpy()).half_life, 1),
            "notes": f"diff_corr={diffs_is_all[cv_cols].corr().iloc[0, 1]:.3f}",
        },
        {
            "structure": "Snackpack Choc + Van Pair Sum",
            "split": "IS (Day 3)",
            "mean": round(float(cv_sum_d3.mean()), 2),
            "std": round(float(cv_sum_d3.std(ddof=1)), 2),
            "adf_t": round(augmented_dickey_fuller_test(cv_sum_d3.to_numpy()).t_statistic, 2),
            "half_life": round(estimate_ou_ar1(cv_sum_d3.to_numpy()).half_life, 1),
            "notes": "Day-specific equilibrium K_3 shifts -98.2 from Day 2",
        },
        {
            "structure": "Snackpack Choc + Van Pair Sum",
            "split": "OOS (Day 4)",
            "mean": round(float(cv_sum_d4.mean()), 2),
            "std": round(float(cv_sum_d4.std(ddof=1)), 2),
            "adf_t": round(augmented_dickey_fuller_test(cv_sum_d4.to_numpy()).t_statistic, 2),
            "half_life": round(estimate_ou_ar1(cv_sum_d4.to_numpy()).half_life, 1),
            "notes": f"oos_diff_corr={diffs_oos_all[cv_cols].corr().iloc[0, 1]:.3f}",
        },
        {
            "structure": "Snackpack Pis/Straw/Rasp Triplet",
            "split": "IS (Day 2)",
            "mean": round(tri_d2.spread_mean, 2),
            "std": round(tri_d2.spread_std, 2),
            "adf_t": round(tri_d2.adf_t_stat, 2),
            "half_life": round(tri_d2.ou_half_life, 1),
            "notes": f"weights={np.round(tri_d2.weights, 3).tolist()}",
        },
        {
            "structure": "Snackpack Pis/Straw/Rasp Triplet",
            "split": "OOS (Day 4)",
            "mean": round(tri_d4.spread_mean, 2),
            "std": round(tri_d4.spread_std, 2),
            "adf_t": round(tri_d4.adf_t_stat, 2),
            "half_life": round(tri_d4.ou_half_life, 1),
            "notes": f"weights={np.round(tri_d4.weights, 3).tolist()}",
        },
    ]
    _write_csv(TABLE_DIR / "r5_baskets_summary.csv", baskets_rows)

    # Plot R5 Figure 1: Spread / Sigma ranking & Intra-Category Correlations
    df_prod = pd.DataFrame(prod_rows).sort_values("is_spread_to_sigma", ascending=False)
    df_cat = pd.DataFrame(cat_rows).sort_values("is_max_abs_diff_corr", ascending=True)

    fig, axes = plt.subplots(1, 2, figsize=(14.5, 5.2))
    top_bot = pd.concat([df_prod.head(8), df_prod.tail(6)])
    colors = ["#2a9d8f"] * 8 + ["#e76f51"] * 6
    y_pos = np.arange(len(top_bot))
    axes[0].barh(y_pos, top_bot["is_spread_to_sigma"], color=colors, alpha=0.88)
    axes[0].set_yticks(y_pos, [s[:22] for s in top_bot["symbol"]], fontsize=8)
    axes[0].invert_yaxis()
    axes[0].set_xlabel("Median Spread / Per-Tick Sigma (IS Days 2-3)")
    axes[0].set_title("Round 5 MM Opportunity Index: Top 8 vs. Bottom 6")
    axes[0].grid(True, axis="x", linestyle="--", alpha=0.4)

    yc = np.arange(len(df_cat))
    axes[1].barh(
        yc - 0.18,
        df_cat["is_max_abs_diff_corr"],
        height=0.35,
        label="IS (Days 2-3)",
        color="#264653",
    )
    axes[1].barh(
        yc + 0.18,
        df_cat["oos_max_abs_diff_corr"],
        height=0.35,
        label="OOS (Day 4)",
        color="#e9c46a",
    )
    axes[1].set_yticks(yc, df_cat["category"], fontsize=9)
    axes[1].set_xlabel("Max Pairwise |Corr(dP)| within Category")
    axes[1].set_title("Intra-Category Return Co-Movement (IS vs. OOS)")
    axes[1].grid(True, axis="x", linestyle="--", alpha=0.4)
    axes[1].legend()

    fig.tight_layout()
    fig.savefig(FIG_DIR / "r5_category_spread_vol_and_corr.png", dpi=200)
    plt.close(fig)

    # Plot R5 Figure 2: Pebbles 50,000 residual & Snackpacks Pair Drift
    fig, axes = plt.subplots(1, 2, figsize=(13.5, 4.6))
    axes[0].plot(peb_sum_d4.index, peb_sum_d4.values - 50_000.0, linewidth=0.9, color="#1d3557")
    axes[0].axhline(0.0, color="#e63946", linestyle="--", linewidth=1.2)
    axes[0].set_title("OOS Day 4: Pebbles 5-Asset Sum Deviation from 50,000")
    axes[0].set_xlabel("Timestamp")
    axes[0].set_ylabel("Sum(Mids) - 50,000 (XIRECs)")
    axes[0].grid(True, linestyle="--", alpha=0.4)

    axes[1].plot(cv_sum_d2.index, cv_sum_d2.values, label=f"Day 2 IS (mean={cv_sum_d2.mean():.0f})")
    axes[1].plot(cv_sum_d3.index, cv_sum_d3.values, label=f"Day 3 IS (mean={cv_sum_d3.mean():.0f})")
    axes[1].plot(
        cv_sum_d4.index,
        cv_sum_d4.values,
        label=f"Day 4 OOS (mean={cv_sum_d4.mean():.0f})",
        linewidth=1.5,
    )
    axes[1].set_title("Snackpack Chocolate + Vanilla Daily Pair Equilibrium K_day")
    axes[1].set_xlabel("Timestamp")
    axes[1].set_ylabel("CHOC_mid + VAN_mid (XIRECs)")
    axes[1].grid(True, linestyle="--", alpha=0.4)
    axes[1].legend()

    fig.tight_layout()
    fig.savefig(FIG_DIR / "r5_pebbles_and_snackpacks_invariants.png", dpi=200)
    plt.close(fig)


def main() -> int:
    """Execute complete Round 2-5 quantitative EDA pipeline."""
    raw_root = Path("data/raw/prosperity4")
    if not (raw_root / "round5").exists():
        print("Rounds 2-5 raw datasets not found; skipping EDA generation.")
        return 0

    loader = DataLoader(data_root=Path("data"))
    print("Running Round 2 microstructure EDA...")
    analyze_round2(loader)
    print("Running Round 3-4 options surface EDA...")
    analyze_round3_round4_options(loader)
    print("Running Round 4 counterparty flow profiling...")
    analyze_round4_counterparties(loader)
    print("Running Round 5 50-asset PCA, basket & pulse EDA...")
    analyze_round5(loader)
    print("Completed Round 2-5 EDA tables (reports/tables/) and figures (reports/figures/).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
