# Round 2 Submission Trader (`traders/round2/submission.py`)

- **Instruments**: `ASH_COATED_OSMIUM`, `INTARIAN_PEPPER_ROOT`
- **Configured Position Limits**: `±80` units per symbol
- **Runtime Dependencies**: Strictly `datamodel` and Python stdlib (`json`, `math`, `typing`); passes `scripts/validate_submission.py`.
- **State Persistence**: Compact JSON scalar/filter dictionary (`fv`, `drift`, `ts`) per symbol in `state.traderData`.
- **Observed Latency**: `0.0406 ms/tick` mean over `10,000` ticks (`Day 1` OOS `queue_aware`).

## Strategy Summary & Validation Links

- **Model**: Bot-wall midpoint filter (`_popular_wall_mid`), causal alpha-beta trend tracker (`alpha=0.25, beta=0.01`) on `INTARIAN_PEPPER_ROOT`, penny-improving market maker (`MIN_EDGE = 3.5`, `INVENTORY_SKEW = 0.75`, `QUOTE_CLIP = 30`).
- **Overfitting Gates (`Day -1, 0` IS)**: `CSCV PBO = 0.0000`, `DSR = 1.0000`, `N_eff = 1.22`.
- **Held-Out OOS (`Day 1`, `queue_aware`)**: **`+27,463.00`** (`Sharpe_252 = 1.3972`, `MaxDD = 419.50`, `1,022` fills; `ASH_COATED_OSMIUM +15,312.00`, `INTARIAN_PEPPER_ROOT +12,151.00`).
- **Documentation**: [round_2.md](../../docs/rounds/round_2.md) and [EXP-R2-001](../../reports/experiments/EXP-R2-001_round2_scale_and_maf.md).
