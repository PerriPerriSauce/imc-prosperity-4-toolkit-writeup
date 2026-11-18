# Manual Challenges Research (Rounds 1–5)

Each round of IMC Prosperity 4 pairs the algorithmic exchange with a one-shot manual decision game. Because manual submissions are irreversible and interact with thousands of competing teams, the core discipline across all five rounds is separating **deterministic payoff structure** from **unknown crowd beliefs**, selecting submissions backed by sensitivity sweeps rather than fragile point forecasts.

## Summary & Final Submitted Inputs Across Rounds

| Round | Challenge | Core Mathematical Structure | Decision Rule & Sensitivity Basis | Final Submitted Portal Inputs | Code |
| :---: | :--- | :--- | :--- | :--- | :--- |
| **1** | *An Intarian Welcome* | Sealed uniform clearing auction + back-of-queue time priority | Step 1 tick above static clear (`29/66`), then defend fill probability under $\mathcal{N}(45, 22^2)$ demand shocks | `DRYLAND_FLAX`: **`px=30, qty=65`**; `EMBER_MUSHROOM`: **`px=20, qty=10`** | [manual_challenges.py](file:///c:/Users/pierr/Desktop/imc-prosperity-4-toolkit-writeup/src/prosperity_toolkit/analysis/manual_challenges.py#L44) |
| **2** | *Invest & Expand* | Concave-linear budget simplex + Speed rank multiplier | Level-k Cognitive Hierarchy (`29.5% -> 37.5% -> 42.0%`) balanced against CH mixture upper bound (`44.0%`) | **`Research = 15%` (`14.71%`), `Scale = 43%` (`43.29%`), `Speed = 42%`** | [manual_challenges.py](file:///c:/Users/pierr/Desktop/imc-prosperity-4-toolkit-writeup/src/prosperity_toolkit/analysis/manual_challenges.py#L199) |
| **3** | *Celestial Gardeners' Guild* | Two-stage sealed reserve screening (`{670..920}`) + cubic shrinkage | Quadratic integration across $\bar{b}_2 \sim \mathcal{N}(875, 15^2)$ (`76.00` EV/unit vs `63.73` single bid) | **`Bid 1 = 775, Bid 2 = 880`** | [manual_challenges.py](file:///c:/Users/pierr/Desktop/imc-prosperity-4-toolkit-writeup/src/prosperity_toolkit/analysis/manual_challenges.py#L289) |
| **4** | *Vanilla Just Isn't Exotic Enough* | `AETHER_CRYSTAL` discrete `4/day` GBM ($\sigma_{\text{ann}}=251\%$, `15d`) | Sell rich `AC_50_CO`/`AC_40_BP`, buy BGK discrete `AC_45_KO` (`0.211` vs `0.175`), straddle-hedge variance (`-90.3%` std) | **`AC_50_CO: -15`, `AC_40_BP: -50`, `AC_45_KO: +198`, `AC_50_C15: +5`, `AC_50_P15: +21`** | [manual_challenges.py](file:///c:/Users/pierr/Desktop/imc-prosperity-4-toolkit-writeup/src/prosperity_toolkit/analysis/manual_challenges.py#L407) |
| **5** | *Extra! Extra!* | Ignith portfolio across 9 news catalysts with quadratic fee `(q/100)^2 * 1M` | Variance-adjusted KKT thresholding ($\kappa = 3.0$) concentrates in `5/9` clear catalysts and zeroes out noisy stories | **`Thermalite +35%, Sulfur +29%, Ashes -23%, Pyroflex -10%, Scoria +3%, Rest 0%`** | [manual_challenges.py](file:///c:/Users/pierr/Desktop/imc-prosperity-4-toolkit-writeup/src/prosperity_toolkit/analysis/manual_challenges.py#L516) |

Reproducing every table row and figure in this section:

```bash
uv run python scripts/evaluate_manual_challenges.py
uv run pytest tests/unit/test_manual_challenges.py -v
```

See [MANUAL_CHALLENGES.md](file:///c:/Users/pierr/Desktop/imc-prosperity-4-toolkit-writeup/docs/manual/MANUAL_CHALLENGES.md) for full mathematical derivations, comparative statics, and exact vs rounded portal inputs, and [manual_challenges_summary.csv](file:///c:/Users/pierr/Desktop/imc-prosperity-4-toolkit-writeup/reports/tables/manual_challenges_summary.csv) for machine-readable outputs.
