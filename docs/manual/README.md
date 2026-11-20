# Manual Challenges Research (Rounds 1–5)

Each round of IMC Prosperity 4 pairs the algorithmic exchange with a one-shot manual decision challenge. Because manual outcomes depend on opponent population behavior and deterministic payoff geometry that are unobserved locally, every model below is evaluated **strictly as an ex-ante offline mathematical policy** parameterized by explicit assumptions—never as actual live portal scores.

## Summary of Ex-Ante Offline Model Policies (`manual_challenges_summary.csv`)

| Round | Challenge | Core Mathematical Structure | Ex-Ante Decision Rule & Basis | Model Policy Output | Code |
| :---: | :--- | :--- | :--- | :--- | :--- |
| **1** | *An Intarian Welcome* | Sealed uniform clearing auction + back-of-queue arrival priority | Jump static clear, then defend fill rate under $\mathcal{N}(45, 22^2)$ human shocks (`68.12` / `9.81` EV) | `DRYLAND_FLAX: (px=30, qty=65)`; `EMBER_MUSHROOM: (px=20, qty=10)` | [manual_challenges.py](../../src/prosperity_toolkit/analysis/manual_challenges.py) |
| **2** | *Invest & Expand* | Concave-linear budget simplex + Speed rank multiplier | Level-k Cognitive Hierarchy (`tau = 1.5`: `L1 29.5% -> L2 37.5% -> L3 42.0%`), `225,094.01` EV | `Research = 15% (14.71%), Scale = 43% (43.29%), Speed = 42%` | [manual_challenges.py](../../src/prosperity_toolkit/analysis/manual_challenges.py) |
| **3** | *Celestial Gardeners' Guild* | Two-stage sealed reserve screening (`{670..920}`) + cubic shrinkage | Quadratic integration across $\bar{b}_2 \sim \mathcal{N}(875, 15^2)$ (`76.00` EV/unit vs `63.73` single bid) | `Bid 1 = 775, Bid 2 = 880` | [manual_challenges.py](../../src/prosperity_toolkit/analysis/manual_challenges.py) |
| **4** | *Aether Crystal Exotics* | Exact BS/Rubinstein + `4/day` discrete GBM KO ($\sigma_{\text{ann}}=251\%$, `15d`) | Sell rich `AC_50_CO` (`21.8977` vs `22.20`) / `AC_40_BP` (`4.7679` vs `5.00`), buy discrete `AC_45_KO` (`0.2113` vs `0.175`), Day-15 MV hedge (`-70.1%` std cut) | `AC_50_CO: -50, AC_40_BP: -50, AC_45_KO: +183, AC_50_C15: +53, AC_50_P15: +74` | [manual_challenges.py](../../src/prosperity_toolkit/analysis/manual_challenges.py) |
| **5** | *Extra! Extra!* | 9 Ignith news catalysts with quadratic fee `(q/100)^2 * 1M` & `-92%` Phoenix bound | Exact KKT (`857,400.00` EV) & risk-adjusted (`kappa = 3.0`, `855,944.53` EV vs `524,444` equal `1/9`); `5/9` active | `Thermalite +36.3%, Sulfur +30.3%, Ashes -17.3%, Pyroflex -11.1%, Scoria +5.1%`, others `0%` | [manual_challenges.py](../../src/prosperity_toolkit/analysis/manual_challenges.py) |

Reproducing every table row and figure in this section:

```bash
uv run python scripts/evaluate_manual_challenges.py
uv run pytest tests/unit/test_manual_challenges.py -v
```

See [MANUAL_CHALLENGES.md](MANUAL_CHALLENGES.md) for full mathematical derivations and sensitivity sweeps, and [manual_challenges_summary.csv](../../reports/tables/manual_challenges_summary.csv) for machine-readable outputs.
