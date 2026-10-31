import math

import numpy as np
import pytest

from coase import durability as du
from coase import dynamic as dy
from coase import static as st


# --- Figures I and II -------------------------------------------------------

def test_figure_one_monopoly_price_above_competitive():
    pts = st.figure_one()
    assert pts["OM"] < pts["OQ"]
    assert pts["OA"] > pts["OB"]


def test_figure_two_mr_equals_mc_at_m():
    pts = st.figure_two(mc=3.0)
    assert st.marginal_revenue(pts["OM"]) == pytest.approx(3.0)
    assert st.demand(pts["OQ"]) == pytest.approx(3.0)


# --- Infinite-horizon Coase conjecture --------------------------------------

def test_impatient_seller_is_a_static_monopolist():
    eq = dy.solve(1e-9)
    assert eq.opening_price() == pytest.approx(0.5, abs=1e-6)
    assert eq.profit() == pytest.approx(dy.commitment_profit(), abs=1e-6)


@pytest.mark.parametrize("delta", [0.3, 0.6, 0.9, 0.99, 0.9999])
def test_matches_closed_form(delta):
    # Known solution for uniform valuations: lam = 1 / (1 + sqrt(1 - delta)).
    s = math.sqrt(1 - delta)
    eq = dy.solve(delta)
    assert eq.lam == pytest.approx(1 / (1 + s), rel=1e-9)
    assert eq.opening_price() == pytest.approx(s / (1 + s), rel=1e-9)
    assert eq.profit() == pytest.approx(s / (2 * (1 + s)), rel=1e-9)


def test_coase_conjecture_price_falls_to_cost():
    c = 0.2
    prices = [dy.solve(d).opening_price(c) for d in (0.9, 0.99, 0.999, 0.99999)]
    assert all(a > b for a, b in zip(prices, prices[1:]))
    assert prices[-1] - c < 0.01
    assert dy.solve(0.99999).profit(c) < 0.01 * dy.commitment_profit(c)


def test_equilibrium_is_sellers_best_response():
    eq = dy.solve(0.9)
    x, policy, _ = dy.best_response_on_grid(eq, n=1001)
    step = x[1] - x[0]
    assert np.max(np.abs(policy - eq.lam * x)) <= step


def test_buyers_are_indifferent_at_the_cutoff():
    eq = dy.solve(0.95)
    x = 1.0
    y = eq.lam * x
    assert y - eq.gamma * x == pytest.approx(eq.delta * (y - eq.gamma * y))


# --- Two-period selling, leasing and durability -----------------------------

def test_bulow_selling_vs_leasing_numbers():
    # Bulow (1982), linear demand, c = 0, delta = 1: selling 0.45, leasing 0.50.
    assert du.sell(1.0, 0.0, 1.0).profit == pytest.approx(0.45, abs=1e-6)
    assert du.lease(1.0, 0.0, 1.0).profit == pytest.approx(0.50, abs=1e-6)


def test_one_period_good_has_no_durability_problem():
    for c in (0.0, 0.2):
        assert du.sell(0.0, c, 0.9).profit == pytest.approx(du.lease(0.0, c, 0.9).profit, abs=1e-6)


@pytest.mark.parametrize("theta", [0.25, 0.5, 1.0])
@pytest.mark.parametrize("c", [0.0, 0.1, 0.3])
def test_leasing_beats_selling(theta, c):
    assert du.lease(theta, c).profit >= du.sell(theta, c).profit - 1e-9


def test_planned_obsolescence_when_cost_is_low():
    theta_sell, _ = du.best_durability(du.sell, c=0.1, n=201)
    theta_lease, _ = du.best_durability(du.lease, c=0.1, n=21)
    theta_plan, _ = du.best_durability(du.planner, c=0.1, n=21)
    assert theta_sell < 0.6
    assert theta_lease == pytest.approx(1.0)
    assert theta_plan == pytest.approx(1.0)
