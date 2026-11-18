# Round 4 Submission Trader (`traders/round4/submission.py`)

- **Instruments**: `HYDROGEL_PACK` (`±200`), `VELVETFRUIT_EXTRACT` (`±200`), and `VEV_4000`–`VEV_6500` (`±300` each) with live `market_trades` counterparty IDs (`Mark 01..67`)
- **Runtime Dependencies**: Strictly `datamodel` and Python stdlib (`json`, `math`, `statistics.NormalDist`, `typing`); passes `scripts/validate_submission.py`.
- **State Persistence**: EWMA total-vol anchors $v_K$ and exponentially decaying `Mark 67` flow impulse (`m67` signal) in `state.traderData`.
- **Observed Latency**: `0.1871 ms/tick` mean over `10,000` ticks (`Day 3` OOS `queue_aware`).

## Strategy Summary & Validation Links

- **Model**: Extends Round 3's options surface + `HEDGE_BAND = 10` spot delta engine with `Mark 67` counterparty flow conditioning aligned strictly to its IS plateau (`M67_BUMP = 0.5`, decay `0.80x`, `MM_EDGE = 5.5`, `MM_SKEW = 0.08`).
- **Overfitting Gates (`Day 1, 2` IS)**: `CSCV PBO = 0.0571`, `DSR = 0.9975`, `N_eff = 1.08` (while rejecting aggressive `s_alpha = 0.85` spot-chasing variants with `PBO = 0.9714`).
- **Held-Out OOS (`Day 3`, `queue_aware`)**: **`+11,741.00`** (`Sharpe_252 = 0.3613` vs `Round3Ungated 0.3488`, `MaxDD = 2,901.00` `-10.8%` reduction, `VELVETFRUIT_EXTRACT +1,027.00`, `touch = +13,259.50`).
- **Documentation**: [round_4.md](../../docs/rounds/round_4.md) and [EXP-R4-001](../../reports/experiments/EXP-R4-001_round4_counterparty_flow.md).
