"""Infinite-horizon durable-goods monopoly (the "Coase conjecture").

Model
-----
A unit mass of buyers has valuations v ~ U[0, 1], where v is the present
value of the services of one unit of a perfectly durable good. Each buyer
wants at most one unit. A monopolist with constant marginal cost c sells
over periods t = 0, 1, 2, ... and cannot commit to future prices. Both sides
discount by delta per period.

Because buyers with high valuations buy first, the state is the highest
remaining valuation x. We look for the stationary linear equilibrium
(Stokey 1981; Gul, Sonnenschein & Wilson 1986):

    next cutoff   y = lambda * x
    price         p = gamma  * x       (measured net of cost)
    seller value  W(x) = w * x**2

The marginal buyer y must be indifferent between buying now and waiting
one period:  y - p = delta * (y - gamma * y)  =>  p = k * y,
with k = 1 - delta + delta * gamma.

This is exactly Coase's argument written as a game: the seller who has just
sold to everyone above x faces a new, smaller market and wants to sell
again, and buyers anticipate it.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import brentq


@dataclass(frozen=True)
class Equilibrium:
    delta: float
    lam: float  # share of remaining market NOT served each period (y = lam * x)
    gamma: float  # price / state, net of cost
    k: float  # price / next cutoff, net of cost
    w: float  # seller value / state**2

    def opening_price(self, c: float = 0.0) -> float:
        """Price in period 0 when valuations span [0, 1] and cost is c."""
        return c + self.gamma * (1.0 - c)

    def profit(self, c: float = 0.0) -> float:
        """Present value of the seller's profit from period 0."""
        return self.w * (1.0 - c) ** 2

    def price_path(self, periods: int, c: float = 0.0) -> np.ndarray:
        t = np.arange(periods)
        return c + self.gamma * (1.0 - c) * self.lam**t

    def share_served(self, periods: int) -> np.ndarray:
        """Fraction of eventual buyers served by the end of each period."""
        t = np.arange(1, periods + 1)
        return 1.0 - self.lam**t


def _k(lam: float, delta: float) -> float:
    # From gamma = k * lam and k = 1 - delta + delta * gamma.
    return (1.0 - delta) / (1.0 - delta * lam)


def _w(lam: float, delta: float) -> float:
    # W(x) = (x - y) k y + delta W(y) with y = lam x.
    k = _k(lam, delta)
    return lam * (1.0 - lam) * k / (1.0 - delta * lam**2)


def _residual(lam: float, delta: float) -> float:
    # Seller's first-order condition: y = k x / (2 (k - delta w)).
    k = _k(lam, delta)
    w = _w(lam, delta)
    return lam - k / (2.0 * (k - delta * w))


def solve(delta: float) -> Equilibrium:
    """Solve the stationary linear equilibrium for discount factor delta."""
    if not 0.0 <= delta < 1.0:
        raise ValueError("delta must be in [0, 1)")
    if delta == 0.0:
        return Equilibrium(delta, 0.5, 0.5, 1.0, 0.25)
    lam = brentq(_residual, 1e-12, 1.0 - 1e-15, args=(delta,), xtol=1e-15)
    k = _k(lam, delta)
    return Equilibrium(delta, lam, k * lam, k, _w(lam, delta))


def commitment_profit(c: float = 0.0) -> float:
    """Profit if the seller can commit (Coase's price OA, quantity OM).

    Leasing, a binding promise not to sell more, or a buy-back guarantee
    all give this same profit in the model.
    """
    return (1.0 - c) ** 2 / 4.0


def commitment_price(c: float = 0.0) -> float:
    return (1.0 + c) / 2.0


def delta_from_period(period_years: float, rate: float = 0.10) -> float:
    """Per-period discount factor for a period of the given length."""
    return float(np.exp(-rate * period_years))


def best_response_on_grid(eq: Equilibrium, n: int = 4001, iters: int = 3000):
    """Check the equilibrium by brute force.

    Holding buyers' behaviour fixed (price p = k * y for any cutoff y the
    seller chooses), solve the seller's dynamic programme on a grid by value
    iteration and return (grid, optimal next cutoff). In equilibrium the
    optimal cutoff should be lam * x.
    """
    x = np.linspace(0.0, 1.0, n)
    # Choosing y <= x only: mask the upper triangle.
    revenue = (x[:, None] - x[None, :]) * eq.k * x[None, :]
    feasible = x[None, :] <= x[:, None]
    revenue = np.where(feasible, revenue, -np.inf)
    v = np.zeros(n)
    for _ in range(iters):
        v_new = np.max(revenue + eq.delta * v[None, :], axis=1)
        if np.max(np.abs(v_new - v)) < 1e-13:
            v = v_new
            break
        v = v_new
    policy = x[np.argmax(revenue + eq.delta * v[None, :], axis=1)]
    return x, policy, v
