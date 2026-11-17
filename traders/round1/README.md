# Round 1 Submission Trader (`traders/round1/submission.py`)

## Overview & Runtime Specification

- **Instruments**: `ASH_COATED_OSMIUM`, `INTARIAN_PEPPER_ROOT`
- **Configured Position Limits**: `20` units/product (*explicit assumption; official Prosperity 4 Round 1 limit remains **UNVERIFIED***)
- **Runtime Dependencies**: Strictly `datamodel` and Python standard library (`json`, `math`, `typing`); passes `scripts/validate_submission.py`.
- **State Persistence**: Stores online filter state (`fv`, `drift`, `ts`) per symbol in compact JSON via `state.traderData`.
- **Observed Latency**: `0.037–0.041 ms/tick` mean over `10,000` ticks (tested via `CompetitionStrategyAdapter`).

## Strategy Summary & Validation Links

- **Fair Value Estimation**: `_popular_wall_mid` selects the highest-volume resting level on each side of two-sided books, cutting step-to-step quote noise std by `31%–40%`.
- **Filters**: `0.25` EMA on stationary `ASH_COATED_OSMIUM`; alpha-beta drift tracker (`alpha=0.25, beta=0.01`) on linearly drifting `INTARIAN_PEPPER_ROOT`.
- **Execution**: Takes mispriced liquidity (`take_edge=1.0`), penny-improves wide bot spreads (`min_edge=1.5`), and applies reservation skew (`inventory_skew=0.80`) strictly constrained against starting tick inventory.
- **Validation**: See [round_1.md](../../docs/rounds/round_1.md), [EXP-R1-001](../../reports/experiments/EXP-R1-001_stage5_vs_stage6.md), and [EXP-R1-002](../../reports/experiments/EXP-R1-002_per_asset_attribution_and_bootstrap.md).
