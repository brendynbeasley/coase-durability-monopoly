"""Recreate Coase's Figures I and II with linear demand P = a - b Q."""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np

A, B = 10.0, 1.0  # demand intercept and slope


def demand(q):
    return A - B * q


def marginal_revenue(q):
    return A - 2 * B * q


def figure_one(stock: float = 7.0):
    """Fixed stock of land OQ, zero cost of selling."""
    m = A / (2 * B)  # MR = 0
    return {"OQ": stock, "OB": demand(stock), "OM": m, "OA": demand(m)}


def figure_two(mc: float = 3.0):
    """Produced durable good with constant marginal cost."""
    q = (A - mc) / B  # P = MC
    m = (A - mc) / (2 * B)  # MR = MC
    return {"OQ": q, "OB": mc, "OM": m, "OA": demand(m)}


def _draw(ax, pts, title, mc=None):
    q = np.linspace(0, A / B, 200)
    ax.plot(q, demand(q), color="#1f4e79", lw=2.2, label="D (demand)")
    qm = q[marginal_revenue(q) >= -2]
    ax.plot(qm, marginal_revenue(qm), "--", color="#b03a2e", lw=1.8, label="MR")
    if mc is not None:
        ax.axhline(mc, color="#555", lw=1.6, label="MC")
    for qv, pv, name in [(pts["OM"], pts["OA"], "A"), (pts["OQ"], pts["OB"], "B")]:
        ax.plot([0, qv], [pv, pv], color="#888", lw=0.9)
        ax.plot([qv, qv], [0, pv], color="#888", lw=0.9)
        ax.annotate(name, (0, pv), xytext=(-14, -4), textcoords="offset points", fontsize=12)
    ax.annotate("M", (pts["OM"], 0), xytext=(-4, -16), textcoords="offset points", fontsize=12)
    ax.annotate("Q", (pts["OQ"], 0), xytext=(-4, -16), textcoords="offset points", fontsize=12)
    ax.annotate("O", (0, 0), xytext=(-12, -14), textcoords="offset points", fontsize=12)
    ax.set_xlim(0, A / B)
    ax.set_ylim(0, A * 1.05)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_xlabel("Quantity", labelpad=24)
    ax.set_ylabel("Price per unit", labelpad=18)
    ax.set_title(title)
    ax.legend(frameon=False, loc="upper right")
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)


def plot_figures(path):
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8))
    _draw(axes[0], figure_one(), "Figure I: monopoly landowner (fixed stock OQ)")
    _draw(axes[1], figure_two(), "Figure II: monopoly producer (constant MC)", mc=3.0)
    fig.text(0.5, -0.02,
             "Textbook monopoly: sell OM at price OA.  Coase: without commitment, "
             "all of OQ is sold and the price falls to OB.",
             ha="center", fontsize=10, style="italic")
    fig.tight_layout()
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)
