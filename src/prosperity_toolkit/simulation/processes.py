"""Vectorized stochastic fair-value path generators using NumPy."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray


@dataclass(frozen=True, slots=True)
class OrnsteinUhlenbeckParams:
    """Parameters for an Ornstein-Uhlenbeck mean-reverting process.

    Continuous SDE:
        dS_t = theta * (mu - S_t) * dt + sigma * dW_t
    """

    mu: float
    theta: float
    sigma: float
    initial_price: float | None = None
    dt: float = 1.0

    def __post_init__(self) -> None:
        if self.theta < 0:
            msg = f"Mean-reversion speed theta must be non-negative, got {self.theta}"
            raise ValueError(msg)
        if self.sigma < 0:
            msg = f"Volatility sigma must be non-negative, got {self.sigma}"
            raise ValueError(msg)
        if self.dt <= 0:
            msg = f"Time step dt must be strictly positive, got {self.dt}"
            raise ValueError(msg)

    @property
    def stationary_std(self) -> float:
        """Theoretical stationary standard deviation sqrt(sigma^2 / (2 * theta))."""
        if self.theta == 0.0:
            return float("inf")
        return self.sigma / math.sqrt(2.0 * self.theta)


@dataclass(frozen=True, slots=True)
class RandomWalkParams:
    """Parameters for an arithmetic Brownian motion with drift.

    Continuous SDE:
        dS_t = mu_drift * dt + sigma * dW_t
    """

    initial_price: float
    mu_drift: float = 0.0
    sigma: float = 1.0
    dt: float = 1.0

    def __post_init__(self) -> None:
        if self.sigma < 0:
            msg = f"Volatility sigma must be non-negative, got {self.sigma}"
            raise ValueError(msg)
        if self.dt <= 0:
            msg = f"Time step dt must be strictly positive, got {self.dt}"
            raise ValueError(msg)


def simulate_ou_paths(
    params: OrnsteinUhlenbeckParams,
    n_sessions: int,
    n_steps: int,
    rng: np.random.Generator,
) -> NDArray[np.float64]:
    """Generate exact-discretization OU paths of shape (n_sessions, n_steps)."""
    if n_sessions <= 0 or n_steps <= 0:
        msg = "n_sessions and n_steps must be strictly positive"
        raise ValueError(msg)

    s0 = params.initial_price if params.initial_price is not None else params.mu
    paths = np.empty((n_sessions, n_steps), dtype=np.float64)
    paths[:, 0] = s0

    if n_steps == 1:
        return paths

    shocks = rng.standard_normal((n_sessions, n_steps - 1))

    if params.theta == 0.0:
        step_std = params.sigma * math.sqrt(params.dt)
        increments = step_std * shocks
        paths[:, 1:] = s0 + np.cumsum(increments, axis=1)
        return paths

    decay = math.exp(-params.theta * params.dt)
    exact_var = (params.sigma**2) * (1.0 - math.exp(-2.0 * params.theta * params.dt)) / (
        2.0 * params.theta
    )
    exact_std = math.sqrt(exact_var)

    for t in range(1, n_steps):
        paths[:, t] = (
            params.mu
            + (paths[:, t - 1] - params.mu) * decay
            + exact_std * shocks[:, t - 1]
        )

    return paths


def simulate_random_walk_paths(
    params: RandomWalkParams,
    n_sessions: int,
    n_steps: int,
    rng: np.random.Generator,
) -> NDArray[np.float64]:
    """Generate vectorized arithmetic random walk paths of shape (n_sessions, n_steps)."""
    if n_sessions <= 0 or n_steps <= 0:
        msg = "n_sessions and n_steps must be strictly positive"
        raise ValueError(msg)

    paths = np.empty((n_sessions, n_steps), dtype=np.float64)
    paths[:, 0] = params.initial_price

    if n_steps == 1:
        return paths

    shocks = rng.standard_normal((n_sessions, n_steps - 1))
    increments = params.mu_drift * params.dt + params.sigma * math.sqrt(params.dt) * shocks
    paths[:, 1:] = params.initial_price + np.cumsum(increments, axis=1)
    return paths
