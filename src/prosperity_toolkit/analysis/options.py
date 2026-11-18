"""Option pricing and implied volatility utilities for Prosperity derivatives analysis."""

from __future__ import annotations

import math
from statistics import NormalDist

_STD_NORM = NormalDist(0.0, 1.0)


def black_scholes_call(
    spot: float,
    strike: float,
    tte: float,
    vol: float,
    rate: float = 0.0,
) -> float:
    """Price a European call option under Black-Scholes (continuous compounding)."""
    if spot <= 0 or strike <= 0:
        msg = f"Spot and strike must be positive, got spot={spot}, strike={strike}"
        raise ValueError(msg)
    if tte <= 0 or vol <= 0:
        return max(0.0, spot - strike * math.exp(-rate * max(tte, 0.0)))

    sqrt_t = math.sqrt(tte)
    d1 = (math.log(spot / strike) + (rate + 0.5 * vol * vol) * tte) / (vol * sqrt_t)
    d2 = d1 - vol * sqrt_t
    return float(
        spot * _STD_NORM.cdf(d1) - strike * math.exp(-rate * tte) * _STD_NORM.cdf(d2),
    )


def black_scholes_call_delta(
    spot: float,
    strike: float,
    tte: float,
    vol: float,
    rate: float = 0.0,
) -> float:
    """Compute Black-Scholes European call delta Phi(d1)."""
    if tte <= 0 or vol <= 0 or spot <= 0 or strike <= 0:
        return 1.0 if spot > strike else 0.0
    sqrt_t = math.sqrt(tte)
    d1 = (math.log(spot / strike) + (rate + 0.5 * vol * vol) * tte) / (vol * sqrt_t)
    return float(_STD_NORM.cdf(d1))


def bachelier_call(
    spot: float,
    strike: float,
    tte_steps: float,
    sigma_per_step: float,
) -> float:
    """Price a European call option under arithmetic Brownian motion (Bachelier)."""
    if tte_steps <= 0 or sigma_per_step <= 0:
        return max(0.0, spot - strike)

    denom = sigma_per_step * math.sqrt(tte_steps)
    d = (spot - strike) / denom
    return float((spot - strike) * _STD_NORM.cdf(d) + denom * _STD_NORM.pdf(d))


def bachelier_call_delta(
    spot: float,
    strike: float,
    tte_steps: float,
    sigma_per_step: float,
) -> float:
    """Compute Bachelier call delta Phi((S - K) / (sigma * sqrt(T)))."""
    if tte_steps <= 0 or sigma_per_step <= 0:
        return 1.0 if spot > strike else 0.0
    d = (spot - strike) / (sigma_per_step * math.sqrt(tte_steps))
    return float(_STD_NORM.cdf(d))


def implied_volatility_bs(
    price: float,
    spot: float,
    strike: float,
    tte: float,
    rate: float = 0.0,
    lo: float = 1e-4,
    hi: float = 10.0,
    tol: float = 1e-7,
    max_iter: int = 80,
) -> float | None:
    """Invert Black-Scholes European call price for annualized implied volatility."""
    intrinsic = max(0.0, spot - strike * math.exp(-rate * max(tte, 0.0)))
    if tte <= 0 or spot <= 0 or strike <= 0 or price <= intrinsic or price >= spot:
        return None

    low_val = black_scholes_call(spot, strike, tte, lo, rate)
    high_val = black_scholes_call(spot, strike, tte, hi, rate)
    if price < low_val or price > high_val:
        return None

    left, right = lo, hi
    for _ in range(max_iter):
        mid = 0.5 * (left + right)
        est = black_scholes_call(spot, strike, tte, mid, rate)
        if abs(est - price) < tol:
            return mid
        if est < price:
            left = mid
        else:
            right = mid
    return 0.5 * (left + right)


def implied_volatility_bachelier(
    price: float,
    spot: float,
    strike: float,
    tte_steps: float,
    lo: float = 1e-4,
    hi: float = 500.0,
    tol: float = 1e-6,
    max_iter: int = 80,
) -> float | None:
    """Invert Bachelier European call price for per-step absolute volatility."""
    intrinsic = max(0.0, spot - strike)
    if tte_steps <= 0 or price <= intrinsic:
        return None

    low_val = bachelier_call(spot, strike, tte_steps, lo)
    high_val = bachelier_call(spot, strike, tte_steps, hi)
    if price < low_val or price > high_val:
        return None

    left, right = lo, hi
    for _ in range(max_iter):
        mid = 0.5 * (left + right)
        est = bachelier_call(spot, strike, tte_steps, mid)
        if abs(est - price) < tol:
            return mid
        if est < price:
            left = mid
        else:
            right = mid
    return 0.5 * (left + right)
