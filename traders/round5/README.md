# Round 5 Submission Trader (`traders/round5/submission.py`)

- **Instruments**: All `50` Round 5 spot assets across `10` categories
- **Configured Position Limits**: Uniform `±10` per symbol (`max_gross = 500`)
- **Runtime Dependencies**: Strictly `datamodel` and Python stdlib (`json`, `math`, `typing`); passes `scripts/validate_submission.py`.
- **State Persistence**: Compact rolling state in `state.traderData` (`k` for `SNACKPACK_CHOCOLATE + VANILLA` daily equilibrium $K_{\text{day}}$, `m` last wall mids, `v` EWMA step volatilities for dynamic `Robots`/`Microchips` spread-to-vol gating).
- **Observed Latency**: `0.6920 ms/tick` mean across all `50` simultaneous books (`Day 4` OOS `queue_aware`).

## Strategy Summary & Validation Links

- **Model**: Lag-free `_popular_wall_mid` valuation (`EDGE_FRAC = 0.18, INVENTORY_SKEW = 1.25`), full `QUOTE_CLIP = 10` capacity utilization, defensive step-volatility guarding on `Robots`/`Microchips` (`LOW_RATIO_EDGE_FRAC = 0.35`, `VOL_GUARD_MULT = 0.50`), decoupled atomic 5-leg `PEBBLES` constant-sum (`50,000`) IOC cross-taking, and slow online `SNACKPACK` $K_{\text{day}}$ tracking (`PAIR_EMA_ALPHA = 0.005`).
- **Overfitting Gates (`Day 2, 3` IS)**: `CSCV PBO = 0.1000`, `DSR = 1.0000`, `N_eff = 1.30`.
- **Held-Out OOS (`Day 4`, `queue_aware`)**: **`+123,173.00`** (`88.3%` of single-day public-tape spread ceiling, `Sharpe_252 = 0.8109`, `MaxDD = 6,205.50`, `7,477` fills, all `10` categories positive; `-78.7%` drawdown vs `EmaSymmetricMM_All50`).
- **Documentation**: [round_5.md](../../docs/rounds/round_5.md) and [EXP-R5-001](../../reports/experiments/EXP-R5-001_round5_portfolio_optimization.md).
