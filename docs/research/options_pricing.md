# Quantitative Research: Option Pricing, Volatility Surfaces & Stationary Traps

Quantitative option valuation in IMC Prosperity 4 centers on ten European call vouchers (`VEV_4000` through `VEV_6500`, `Q_max = ±300`) written on `VELVETFRUIT_EXTRACT` (`Q_max = ±200`) across Rounds 3 and 4, alongside exotic options in the Round 4 manual challenge (`AETHER_CRYSTAL`).

## 1. Analytic Pricing Kernels (`VEV_4000`–`VEV_6500`)

[`options.py`](../../src/prosperity_toolkit/analysis/options.py) implements zero-rate Black-Scholes and arithmetic Bachelier kernels with bounded-bisection IV solvers (`implied_volatility_bs`, `implied_volatility_bachelier`). Under zero rates, $C_{\text{BS}}$ depends on $\sigma_{\text{BS}}$ and horizon $\tau$ solely through **total implied volatility** $v = \sigma_{\text{BS}}\sqrt{\tau}$:
$$C_{\text{BS}}(S, K, v) = S\,\Phi(d_1) - K\,\Phi(d_2), \qquad d_1 = \frac{\ln(S/K) + \frac{1}{2} v^2}{v}, \quad d_2 = d_1 - v$$
Inverting observed bot mid-quotes directly for rolling EWMA $v_K$ removes fatal calendar-horizon misspecification across days (`OptionsVolatilityContract` lost `-1,051.00` OOS Day 2 using fixed calendar $\tau$).

## 2. Empirical Volatility Smile & Multi-Day Decay (`r3_r4_options_surface.csv`)

Across `VEV_5000..5500`, quoting bots maintain a nearly flat `22.6%–24.4%` BS smile (`0.759–0.827` Bachelier tick vol) whose time value decays deterministically across `Day 0 -> Day 3`, while deep-OTM `VEV_6000` and `VEV_6500` stay pinned at `bid = 0, ask = 1` (`189` seller-initiated zero-price prints/strike IS) and are pruned completely from `traders/round3` and `traders/round4`.

1. **Stationary Underlying Trap**: `VELVETFRUIT_EXTRACT` rejects the unit root (`ADF t = -3.53`, half-life `206` ticks), keeping spot tightly bounded (`~5,200–5,300`, `std ~ 14.2`). Against stationary variance, near-ATM/OTM vouchers systematically bleed time value (`VEV_5000..5300` contribute strongly short-biased OOS attribution: `+13.8k/+12.8k/+10.1k/+7.9k` R3; `+39.0k/+36.8k/+28.6k/+16.9k` R4).
2. **Negative Result — Spot Delta-Hedging Drag (`R3`)**: Attempting to delta-hedge option inventory mechanically through `VELVETFRUIT_EXTRACT` crosses wide `~5`-tick spot spreads repeatedly on temporary OU noise, eroding spread profits. Leaving `Round3Submission` **delta-unhedged** inside the `±300` voucher / `±200` spot limits delivers **`+95,093.00` OOS** (`R3 Day 2`) and **`+260,540.00` OOS** (`R4 Day 3` with causal counterparty flow).

## 3. Exotic Discrete Monitoring Connection (`R4 Manual: Aether Crystal`)

In Round 4's manual challenge ($\sigma_{\text{ann}} = 251\%$, `15d` expiry, `6h` discrete resets `4/day`), vanillas (`AC_50_C15 = AC_50_P15 = 12.0269`), the binary put (`AC_40_BP = 4.7679`), and the chooser (`AC_50_CO = 21.8977`) are priced by **exact closed-form Black-Scholes / Rubinstein formulas**, while `100,000`-path antithetic GBM prices the path-dependent `4/day` down-and-out put (`AC_45_KO = 0.2113` fair vs `0.175` ask, compared to `0.1562` under fine `24/day` monitoring), matching the Broadie–Glasserman–Kou discrete survival premium ([`MANUAL_CHALLENGES.md`](../manual/MANUAL_CHALLENGES.md)).
