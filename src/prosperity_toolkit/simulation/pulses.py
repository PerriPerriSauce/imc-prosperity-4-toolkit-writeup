"""Vectorized counterparty trade arrival and correlated shock generators."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray


@dataclass(frozen=True, slots=True)
class TradeArrivalConfig:
    """Parameters governing synthetic counterparty market-order arrivals."""

    arrival_prob: float = 0.25
    buy_prob: float = 0.5
    min_size: int = 1
    max_size: int = 5

    def __post_init__(self) -> None:
        if not 0.0 <= self.arrival_prob <= 1.0:
            msg = f"arrival_prob must be in [0, 1], got {self.arrival_prob}"
            raise ValueError(msg)
        if not 0.0 <= self.buy_prob <= 1.0:
            msg = f"buy_prob must be in [0, 1], got {self.buy_prob}"
            raise ValueError(msg)
        if self.min_size <= 0 or self.max_size < self.min_size:
            msg = f"Invalid size bounds: min={self.min_size}, max={self.max_size}"
            raise ValueError(msg)


def simulate_trade_arrivals(
    config: TradeArrivalConfig,
    n_sessions: int,
    n_steps: int,
    rng: np.random.Generator,
) -> NDArray[np.int64]:
    """Generate signed counterparty trade quantities of shape (n_sessions, n_steps).

    Positive entries denote buyer-initiated market orders (lifting asks);
    negative entries denote seller-initiated market orders (hitting bids);
    zero denotes no counterparty market order on that tick.
    """
    arrivals = rng.random((n_sessions, n_steps)) < config.arrival_prob
    is_buy = rng.random((n_sessions, n_steps)) < config.buy_prob
    sizes = rng.integers(
        config.min_size,
        config.max_size + 1,
        size=(n_sessions, n_steps),
        dtype=np.int64,
    )
    signs = np.where(is_buy, 1, -1)
    result: NDArray[np.int64] = np.where(arrivals, signs * sizes, 0).astype(np.int64)
    return result


def generate_correlated_pulses(
    n_assets: int,
    n_sessions: int,
    n_steps: int,
    pulse_prob: float,
    pulse_sigma: float,
    rng: np.random.Generator,
) -> NDArray[np.float64]:
    """Generate shared cross-asset jump/pulse shocks of shape (n_assets, n_sessions, n_steps)."""
    if n_assets <= 0:
        msg = "n_assets must be strictly positive"
        raise ValueError(msg)
    shared_trigger = rng.random((n_sessions, n_steps)) < pulse_prob
    shared_shock = rng.normal(0.0, pulse_sigma, size=(n_sessions, n_steps))
    masked_shock = np.where(shared_trigger, shared_shock, 0.0)
    return np.broadcast_to(masked_shock, (n_assets, n_sessions, n_steps)).copy()
