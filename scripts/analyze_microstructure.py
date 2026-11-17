"""Reproducible market microstructure and calibration analysis for Round 0 and Round 1."""

from __future__ import annotations

from pathlib import Path

from prosperity_toolkit.analysis.microstructure import (
    augmented_dickey_fuller_test,
    compute_return_moments,
    estimate_linear_drift,
    estimate_ou_ar1,
    evaluate_obi_signal,
    extract_two_sided_mid,
    summarize_order_book,
)
from prosperity_toolkit.data.loader import DataLoader


def analyze_round(round_num: int, days: list[int]) -> None:
    """Run descriptive, stationarity, OU/drift, and OBI analysis for a round."""
    loader = DataLoader()
    print(f"\n==================== ROUND {round_num} ====================")

    for day in days:
        prices_df = loader.load_day_prices(round_num, day)
        trades_df = loader.load_day_trades(round_num, day)
        print(f"\n--- Round {round_num}, Day {day} (trade_prints={len(trades_df)}) ---")

        for product in sorted(prices_df["product"].unique()):
            book_rep = summarize_order_book(prices_df, product)
            mid_series = extract_two_sided_mid(prices_df, product)
            moments = compute_return_moments(mid_series, lags=(1, 2, 5, 10))
            adf = augmented_dickey_fuller_test(mid_series.to_numpy(), lags=2)
            ou = estimate_ou_ar1(mid_series.to_numpy(), dt=1.0)
            slope, intercept, r2 = estimate_linear_drift(
                mid_series.index.to_numpy(dtype=float),
                mid_series.to_numpy(dtype=float),
            )
            obi_res = evaluate_obi_signal(prices_df, product, horizons=(1, 5, 10))

            prod_trades = trades_df[trades_df["symbol"] == product]
            print(f"\nProduct: {product}")
            print(
                f"  Ticks: total={book_rep.total_ticks}, two_sided={book_rep.two_sided_ticks}, "
                f"one_sided={book_rep.one_sided_ticks}, empty={book_rep.empty_ticks}",
            )
            print(
                f"  Two-Sided Mid: mean={book_rep.mid_mean:.2f}, std={book_rep.mid_std:.2f}, "
                f"min={book_rep.mid_min:.1f}, max={book_rep.mid_max:.1f}",
            )
            print(
                f"  Spread: mean={book_rep.spread_mean:.2f}, median={book_rep.spread_median:.1f}, "
                f"min={book_rep.spread_min:.1f}, max={book_rep.spread_max:.1f} | "
                f"L1 Depth: bid={book_rep.avg_bid_depth_l1:.2f}, "
                f"ask={book_rep.avg_ask_depth_l1:.2f}",
            )
            print(
                f"  dMid Moments: std={moments['std']:.4f}, skew={moments['skewness']:.3f}, "
                f"kurt={moments['excess_kurtosis']:.2f}, "
                f"acf1={moments['acf_lag_1']:.4f}, acf2={moments['acf_lag_2']:.4f}, "
                f"acf5={moments['acf_lag_5']:.4f}",
            )
            print(
                f"  ADF(lags=2): t={adf.t_statistic:.3f}, "
                f"reject_unit_root_5pct={adf.reject_unit_root_5pct}",
            )
            print(
                f"  OU(AR1): b={ou.ar1_slope:.5f} (se={ou.ar1_slope_se:.5f}), "
                f"mu={ou.mu:.2f}, theta={ou.theta:.5f}, sigma={ou.sigma:.4f}, "
                f"half_life={ou.half_life:.2f} ticks",
            )
            print(
                f"  Linear Drift vs Timestamp: slope={slope:.6f}/tick_unit "
                f"({slope * 100:.5f}/step), intercept={intercept:.2f}, R2={r2:.4f}",
            )
            for item in obi_res:
                print(
                    f"  OBI->dMid(h={item.horizon}): r={item.correlation:.4f}, "
                    f"slope={item.ols_slope:.4f}, t={item.t_stat:.2f}, p={item.p_value:.2e}",
                )
            if not prod_trades.empty:
                print(
                    f"  Trades: count={len(prod_trades)}, "
                    f"mean_qty={prod_trades['quantity'].mean():.2f}, "
                    f"total_vol={int(prod_trades['quantity'].sum())}",
                )


def main() -> int:
    """Run Round 0 and Round 1 empirical analysis."""
    if not Path("data/raw/prosperity4").exists():
        print("Raw data directory not found.")
        return 1
    analyze_round(0, [-2, -1])
    analyze_round(1, [-2, -1, 0])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
