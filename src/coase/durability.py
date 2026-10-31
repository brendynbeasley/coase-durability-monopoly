"""Two-period model of selling, leasing and durability (after Bulow 1982, 1986).

Coase argues that a monopolist can escape the durability problem by leasing
or by making the good less durable. This module tests both claims in the
simplest setting where they can be computed exactly.

Setup
-----
* Two periods, discount factor delta.
* Each period, demand for the *services* of the good is P = 1 - S, where S
  is the stock of services in use.
* A unit built in period 1 gives 1 unit of service in period 1 and theta
  units in period 2. theta = 1 is fully durable, theta = 0 lasts one period.
* Every new unit costs c to build, whatever its durability.

Selling: in period 2 the seller has no reason to protect period-1 buyers and
sells new units against the old stock theta * q1. Period-1 buyers foresee
this, so a unit sells for (1 - q1) + delta * theta * p2.

Leasing: the seller keeps ownership, so any price cut in period 2 lowers
its own rental income. It therefore chooses the whole service path.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import minimize, minimize_scalar


@dataclass(frozen=True)
class Outcome:
    q1: float
    q2: float
    p1: float  # price of a unit (selling) or rent (leasing) in period 1
    p2: float  # service price in period 2
    profit: float
    surplus: float  # buyers' plus seller's surplus


def _period2_sale(q1, theta: float, c: float):
    # Works on floats and numpy arrays of q1.
    q2 = np.maximum(0.0, (1.0 - theta * q1 - c) / 2.0)
    p2 = 1.0 - theta * q1 - q2
    return q2, p2


def _total_surplus(q1: float, q2: float, theta: float, c: float, delta: float) -> float:
    s1, s2 = q1, theta * q1 + q2
    return (s1 - s1**2 / 2) - c * q1 + delta * ((s2 - s2**2 / 2) - c * q2)


def _sell_profit(q1, theta: float, c: float, delta: float):
    q2, p2 = _period2_sale(q1, theta, c)
    p1 = (1.0 - q1) + delta * theta * p2
    return (p1 - c) * q1 + delta * (p2 - c) * q2


def sell(theta: float, c: float = 0.0, delta: float = 1.0) -> Outcome:
    """Equilibrium when the monopolist sells and cannot commit."""
    grid = np.linspace(0.0, 1.0, 20001)
    profits = _sell_profit(grid, theta, c, delta)
    i = int(np.argmax(profits))
    lo, hi = grid[max(i - 1, 0)], grid[min(i + 1, len(grid) - 1)]
    res = minimize_scalar(
        lambda q: -_sell_profit(q, theta, c, delta),
        bounds=(lo, hi),
        method="bounded",
        options={"xatol": 1e-12},
    )
    q1 = float(res.x) if -res.fun >= profits[i] else float(grid[i])
    q2, p2 = (float(v) for v in _period2_sale(q1, theta, c))
    p1 = (1.0 - q1) + delta * theta * p2
    return Outcome(
        q1, q2, p1, p2, float(_sell_profit(q1, theta, c, delta)),
        _total_surplus(q1, q2, theta, c, delta),
    )


def _maximize_over_stock(objective) -> tuple[float, float]:
    best = None
    for start in [(0.5, 0.0), (0.5, 0.5), (0.3, 0.2), (0.8, 0.1)]:
        res = minimize(lambda z: -objective(*z), start, bounds=[(0, 1), (0, 1)],
                       method="L-BFGS-B", options={"ftol": 1e-15, "gtol": 1e-12})
        if best is None or res.fun < best.fun:
            best = res
    return float(best.x[0]), float(best.x[1])


def lease(theta: float, c: float = 0.0, delta: float = 1.0) -> Outcome:
    """Monopolist that rents out the good and keeps ownership."""
    def profit(q1, q2):
        s1, s2 = q1, theta * q1 + q2
        return (1 - s1) * s1 - c * q1 + delta * ((1 - s2) * s2 - c * q2)

    q1, q2 = _maximize_over_stock(profit)
    s2 = theta * q1 + q2
    return Outcome(q1, q2, 1 - q1, 1 - s2, profit(q1, q2),
                   _total_surplus(q1, q2, theta, c, delta))


def planner(theta: float, c: float = 0.0, delta: float = 1.0) -> Outcome:
    """Efficient benchmark: maximise total surplus."""
    q1, q2 = _maximize_over_stock(lambda a, b: _total_surplus(a, b, theta, c, delta))
    s2 = theta * q1 + q2
    return Outcome(q1, q2, 1 - q1, 1 - s2, float("nan"),
                   _total_surplus(q1, q2, theta, c, delta))


def best_durability(model, c: float, delta: float = 1.0, n: int = 1001) -> tuple[float, float]:
    """Durability theta in [0, 1] that maximises profit (or surplus for the planner).

    Ties (e.g. leasing with c = 0, where durability is irrelevant) are broken
    towards the more durable good.
    """
    thetas = np.linspace(0.0, 1.0, n)
    key = "surplus" if model is planner else "profit"
    values = np.array([getattr(model(t, c, delta), key) for t in thetas])
    i = int(np.flatnonzero(values >= values.max() - 1e-9)[-1])
    return float(thetas[i]), float(values[i])
