# Round 3 Submission Trader (`traders/round3/submission.py`)

- **Instruments**: `HYDROGEL_PACK` (`±200`), `VELVETFRUIT_EXTRACT` (`±200`), and `VEV_4000`–`VEV_6500` (`±300` each)
- **Runtime Dependencies**: Strictly `datamodel` and Python stdlib (`json`, `math`, `statistics.NormalDist`, `typing`); passes `scripts/validate_submission.py`.
- **State Persistence**: EWMA composite total implied volatilities $v_K = \sigma_K \sqrt{\tau}$ (`VEV_5200..5500`) in `state.traderData`.
- **Observed Latency**: `0.1872 ms/tick` mean over `10,000` ticks (`Day 2` OOS `queue_aware`).

## Strategy Summary & Validation Links

- **Model**: Wide-spread bot-wall MM on `HYDROGEL_PACK` (`MM_EDGE = 4.5, MM_SKEW = 0.10`), deep-ITM parity arbitrage on `VEV_4000/4500`, day-invariant BS total-vol bisection on `VEV_5200..5500`, and `HEDGE_BAND = 10` spot delta neutralization on `VELVETFRUIT_EXTRACT`.
- **Overfitting Gates (`Day 0, 1` IS)**: `CSCV PBO = 0.0000`, `DSR = 0.9921`, `N_eff = 1.12`.
- **Held-Out OOS (`Day 2`, `queue_aware`)**: **`+7,525.50`** (`Sharpe_252 = 0.2276`, `MaxDD = 1,936.00`, `726` fills).
- **Documentation**: [round_3.md](../../docs/rounds/round_3.md) and [EXP-R3-001](../../reports/experiments/EXP-R3-001_round3_options_and_spot.md).
