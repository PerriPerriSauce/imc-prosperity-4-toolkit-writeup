# Quantitative Research: Option Pricing, Volatility Surfaces & Stationary Traps

Quantitative option valuation in IMC Prosperity 4 centers on ten European call vouchers (`VEV_4000` through `VEV_6500`, `Q_max = 300`) written on `VELVETFRUIT_EXTRACT` (`Q_max = 200`) across Rounds 3 and 4, alongside the exotic derivatives book in the Round 4 manual challenge (`AETHER_CRYSTAL`). The unifying insight across both environments is that textbook continuous-time diffusion formulas fail whenever you blindly hardcode clock assumptions or ignore stationarity and discrete monitoring.

## 1. Analytic Pricing Kernels (`VEV_4000`–`VEV_6500`)

Depending on whether underlying spot noise scales multiplicatively or additively over remaining horizon $\tau$, [`options.py`](file:///c:/Users/pierr/Desktop/imc-prosperity-4-toolkit-writeup/src/prosperity_toolkit/analysis/options.py) implements both zero-rate pricing kernels together with bounded-bisection implied volatility solvers (`implied_volatility_bs`, `implied_volatility_bachelier`).

Under **Geometric Black-Scholes** ($r = 0$):
$$C_{\text{BS}}(S, K, \tau, \sigma_{\text{BS}}) = S\,\Phi(d_1) - K\,\Phi(d_2), \qquad d_1 = \frac{\ln(S/K) + \frac{1}{2} v^2}{v}, \quad d_2 = d_1 - v, \quad v = \sigma_{\text{BS}}\sqrt{\tau}$$
with delta $\Delta_{\text{BS}} = \Phi(d_1)$ and vega $\mathcal{V}_{\text{BS}} = S \sqrt{\tau}\,\phi(d_1)$. Under **Arithmetic Bachelier** dynamics ($dS_t = \sigma_{\text{tick}}\,dW_t$) over $T$ remaining ticks:
$$C_{\text{Bach}}(S, K, T, \sigma_{\text{tick}}) = (S - K)\,\Phi(d) + \sigma_{\text{tick}}\sqrt{T}\,\phi(d), \qquad d = \frac{S - K}{\sigma_{\text{tick}}\sqrt{T}}, \qquad \Delta_{\text{Bach}} = \Phi(d)$$

Crucially, notice that $C_{\text{BS}}$ depends on $\sigma_{\text{BS}}$ and $\tau$ **only through the total-variance scalar $v = \sigma_{\text{BS}}\sqrt{\tau}$** when $r = 0$. Inverting an observed bot mid directly for $v_K$ rather than assuming a calendar day count ($\tau = 5 - d$) eliminates systematic mispricing whenever the exchange scheduler runs on a longer clock (empirically closer to $\tau_{\text{eff}} \approx 8$ days across Rounds 3 and 4).

## 2. Empirical Volatility Smile & Multi-Day Decay (`r3_r4_options_surface.csv`)

Auditing the full strike chain across In-Sample Days 0–1 (Round 3 IS) and held-out Days 2–3 reveals both how liquidity bots quote the strip and where structural edge concentrates:

| Instrument | Strike | IS Mean Mid | IS Spread | $\hat{\sigma}_{\text{BS, 5d}}$ | Bach $\hat{\sigma}_{50k}$ | Empirical $\hat{\Delta}_{\text{IS}}$ | Bach $\Delta_{50k}$ | Day `0 -> 3` Mid Trajectory | Seller-Init Flow |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `VEV_4000` | `4,000` | `1,247.47` | `20.77` | `0.5388` | `1.5595` | `0.751` | `1.000` | `1246.52 -> 1248.41 -> 1255.40 -> 1239.16` | `51.8%` (`336`t) |
| `VEV_4500` | `4,500` | `747.46` | `15.80` | `0.3115` | `0.9543` | `0.663` | `0.998` | `746.52 -> 748.41 -> 755.40 -> 739.16` | `0.0%` (`1`t) |
| `VEV_5000` | `5,000` | `253.26` | `6.00` | `0.2386` | `0.7699` | `0.651` | `0.837` | `253.26 -> 253.26 -> 258.54 -> 241.63` | `0.0%` (`1`t) |
| `VEV_5100` | `5,100` | `166.55` | `4.29` | `0.2381` | `0.7761` | `0.568` | `0.721` | `168.11 -> 164.98 -> 167.33 -> 150.28` | `0.0%` (`1`t) |
| `VEV_5200` | `5,200` | `96.30` | `2.90` | `0.2386` | `0.7850` | `0.431` | `0.575` | `97.47 -> 95.13 -> 94.05 -> 77.81` | `90.0%` (`10`t) |
| `VEV_5300` | `5,300` | `47.90` | `2.13` | `0.2400` | `0.7971` | `0.272` | `0.417` | `48.89 -> 46.91 -> 44.48 -> 32.14` | `98.7%` (`76`t) |
| `VEV_5400` | `5,400` | `17.06` | `1.41` | `0.2262` | `0.7587` | `0.132` | `0.273` | `18.47 -> 15.65 -> 13.73 -> 8.50` | `100.0%` (`145`t) |
| `VEV_5500` | `5,500` | `7.31` | `1.17` | `0.2444` | `0.8272` | `0.059` | `0.158` | `8.06 -> 6.57 -> 5.29 -> 2.26` | `100.0%` (`173`t) |
| `VEV_6000` | `6,000` | `0.50` | `1.00` | `0.3727` | `1.3181` | `0.000` | `0.001` | `0.50 -> 0.50 -> 0.50 -> 0.50` | `100.0%` (`189`t) |
| `VEV_6500` | `6,500` | `0.50` | `1.00` | `0.5639` | `2.0782` | `0.000` | `0.000` | `0.50 -> 0.50 -> 0.50 -> 0.50` | `100.0%` (`189`t) |

Three microstructural mechanisms jump out of [`r3_r4_options_surface.csv`](file:///c:/Users/pierr/Desktop/imc-prosperity-4-toolkit-writeup/reports/tables/r3_r4_options_surface.csv):

1. **Flat Core Smile vs. Wing Artifacts**: Across `VEV_5000..5500`, quoting bots maintain an almost flat `22.6%–24.4%` annualized BS smile (`0.759–0.827` Bachelier tick vol) whose prices step down deterministically day-by-day. Meanwhile `VEV_6000` and `VEV_6500` sit pinned at the `[0, 1]` integer floor (`mid = 0.50`), inflating wing BS IVs to `37%–56%` purely from tick discreteness, while taker bots repeatedly dump size into `0`-price bids (`189` prints/strike in IS, `90%–100%` seller-initiated across `5200..6500`).
2. **Stationary Underlying Option Trap**: On `VELVETFRUIT_EXTRACT`, single-step differences have $\sigma_{\Delta S} = 1.1277$. A naive unit-root random-walk projection over `50,000` ticks expects $\sigma_{50k} = 1.1277\sqrt{50{,}000} \approx 252.2$, which would falsely make `0.76–0.83` implied tick vol look *cheap*. In fact, `VELVETFRUIT_EXTRACT` rejects the unit root (`ADF t = -3.53`, half-life `206.1` ticks), confining stationary spot standard deviation to `14.18` XIRECs (`~5,198..5,300` range). Against true stationary terminal dispersion, near-ATM/OTM calls carry `~47` XIRECs (`VEV_5200`/`5300`) of excess premium paired with heavy taker selling pressure.
3. **Errors-in-Variables Delta Attenuation**: Notice why empirical tick-regression $\hat{\Delta}_{\text{IS}}$ (`0.751` on `VEV_4000`, `0.272` on `VEV_5300`) sits systematically below theoretical Bachelier/BS $\Delta$ (`1.000` on `VEV_4000`, `0.417` on `VEV_5300`). Deep-ITM `VEV_4000` quotes a `20.77`-tick spread with independent bot jitter ($\sigma_{\Delta O} = 1.4186 > \sigma_{\Delta S} = 1.1277$), whereas `VELVETFRUIT_EXTRACT` itself jitters inside a `5`-tick spread. Regressing noisy tick differences $\Delta O_t$ on noisy $\Delta S_t$ attenuates the OLS slope toward zero—a classic measurement-error bias that disappears once delta is computed off smoothed wall-mid prices (`_popular_wall_mid`).

## 3. Production Implications & Exotic Monitoring Connections

- **Why Fixed-TTE Parametric BS Lost Money (`PM-004`)**: Hardcoding $\tau = 5 - d$ forced `OptionsVolatilityContract` to cross `VEV_5100..5500` aggressively against wrong time-to-expiry assumptions (`-7,604.00` OOS `Day 2`). Switching to rolling EWMA total-volatility $v_K = \sigma_K \sqrt{\tau}$ alignment (`VEV_5200..5500`) plus deep-ITM parity arbitrage (`VEV_4000`, `VEV_4500`) and bounded underlying delta hedging (`HEDGE_BAND = 10` inside `Q_max = 200`) completely stabilized options attribution ([`round_3.md`](file:///c:/Users/pierr/Desktop/imc-prosperity-4-toolkit-writeup/docs/rounds/round_3.md)).
- **Discrete Barrier Monitoring (`R4 Manual: Aether Crystal`)**: In Round 4's manual challenge ($\sigma_{\text{ann}} = 251\%$, `15d` expiry, `6h` discrete resets $\Delta t = 1/60$), discrete barrier survival follows the Broadie–Glasserman–Kou continuity correction $B_{\text{eff}} = B \exp(-\beta \sigma \sqrt{\Delta t})$ with $\beta \approx 0.5826$ (`B = 35` shifts effectively to `33.42`). Under discrete monitoring, `AC_45_KO` trades undervalued at `0.175` vs fair `0.2108` (`+0.0358` BUY edge), whereas `24`-step/day monitoring compresses fair value down to `0.1570`—proving how discrete reset geometry flips trade direction at the barrier boundary ([`MANUAL_CHALLENGES.md`](file:///c:/Users/pierr/Desktop/imc-prosperity-4-toolkit-writeup/docs/manual/MANUAL_CHALLENGES.md)).

