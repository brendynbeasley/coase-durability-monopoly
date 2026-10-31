"""Run every experiment and write figures/ and results/.

Usage:  python scripts/run_experiments.py
"""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from coase import durability as du
from coase import dynamic as dy
from coase import static as st

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "figures"
RES = ROOT / "results"
FIG.mkdir(exist_ok=True)
RES.mkdir(exist_ok=True)

BLUE, RED, GREY, GREEN = "#1f4e79", "#b03a2e", "#666666", "#2e7d32"
RATE = 0.10  # annual interest rate used to turn period length into delta
plt.rcParams.update({"axes.spines.top": False, "axes.spines.right": False})


def write_csv(path, header, rows):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def experiment_1_figures():
    st.plot_figures(FIG / "fig1_coase_figures.png")


def experiment_2_coase_conjecture():
    """Opening price and profit as the seller becomes more patient."""
    one_minus = np.logspace(0, -6, 121)
    deltas = 1 - one_minus
    eqs = [dy.solve(min(d, 1 - 1e-12)) for d in deltas]
    rows = [(d, e.lam, e.opening_price(), e.profit()) for d, e in zip(deltas, eqs)]
    write_csv(RES / "coase_conjecture.csv",
              ["delta", "lambda", "opening_price", "profit"], rows)

    periods = {"1 year": 1, "1 quarter": 1 / 4, "1 month": 1 / 12, "1 week": 1 / 52,
               "1 day": 1 / 365, "1 hour": 1 / 8760}
    prow = []
    for name, years in periods.items():
        e = dy.solve(dy.delta_from_period(years, RATE))
        prow.append((name, years, e.delta, e.opening_price(), e.profit(),
                     e.profit() / dy.commitment_profit()))
    write_csv(RES / "period_length.csv",
              ["period", "years", "delta", "opening_price", "profit", "profit_vs_commitment"],
              prow)

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.3))
    ax = axes[0]
    x = one_minus
    ax.semilogx(x, [r[2] for r in rows], color=BLUE, lw=2.2, label="Opening price, selling")
    ax.semilogx(x, [r[3] for r in rows], color=RED, lw=2.2, label="Profit, selling")
    ax.axhline(dy.commitment_price(), color=BLUE, ls=":", lw=1.4,
               label="Monopoly price OA (commit or lease)")
    ax.axhline(dy.commitment_profit(), color=RED, ls=":", lw=1.4,
               label="Monopoly profit (commit or lease)")
    ax.invert_xaxis()
    ax.set_xlabel(r"$1-\delta$  (more patient seller →)")
    ax.set_ylabel("Price / profit (cost = 0, top valuation = 1)")
    ax.set_title("A. Price collapses to cost as $\\delta \\to 1$")
    ax.legend(frameon=False, fontsize=8.5, loc="center right")

    ax = axes[1]
    names = [r[0] for r in prow]
    shares = [100 * r[5] for r in prow]
    bars = ax.bar(names, shares, color=BLUE)
    ax.bar_label(bars, fmt="%.1f%%", fontsize=9)
    ax.set_ylabel("Profit as % of monopoly profit")
    ax.set_title(f"B. Shorter periods between price cuts (r = {RATE:.0%}/yr)")
    ax.set_ylim(0, 105)
    ax.tick_params(axis="x", rotation=20)
    fig.tight_layout()
    fig.savefig(FIG / "fig2_coase_conjecture.png", dpi=200)
    plt.close(fig)
    return prow


def experiment_3_price_paths():
    """Price over calendar time for different lengths of a period."""
    horizon = 3.0
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.3))
    for (name, years), color in zip(
        {"1 year": 1, "1 quarter": 1 / 4, "1 month": 1 / 12, "1 week": 1 / 52}.items(),
        [GREY, GREEN, RED, BLUE],
    ):
        e = dy.solve(dy.delta_from_period(years, RATE))
        n = int(horizon / years) + 1
        t = np.arange(n) * years
        axes[0].step(t, e.price_path(n), where="post", color=color, lw=2, label=name)
        axes[1].step(t, 100 * e.share_served(n), where="post", color=color, lw=2, label=name)
    axes[0].axhline(0.5, color="black", ls=":", lw=1.2, label="Monopoly price OA")
    axes[0].set_title("A. Price path: skimming down the demand curve")
    axes[0].set_ylabel("Price")
    axes[1].set_title("B. Share of eventual buyers served")
    axes[1].set_ylabel("%")
    axes[0].legend(frameon=False, fontsize=9, title="Period length", loc="upper right",
                   bbox_to_anchor=(1.0, 0.93))
    axes[1].legend(frameon=False, fontsize=9, title="Period length", loc="lower right")
    for ax in axes:
        ax.set_xlabel("Years")
    fig.tight_layout()
    fig.savefig(FIG / "fig3_price_paths.png", dpi=200)
    plt.close(fig)


def experiment_4_leasing_and_durability():
    """Two-period model: selling vs leasing, and the choice of durability."""
    thetas = np.linspace(0, 1, 101)
    costs = [0.0, 0.05, 0.1, 0.15, 0.2]
    rows = []
    for c in costs:
        for th in thetas:
            s, l = du.sell(th, c), du.lease(th, c)
            rows.append((c, th, s.profit, l.profit, s.surplus, l.surplus))
    write_csv(RES / "durability_profit.csv",
              ["cost", "theta", "profit_sell", "profit_lease", "surplus_sell", "surplus_lease"],
              rows)

    cgrid = np.round(np.arange(0.0, 0.401, 0.01), 3)
    choice = []
    for c in cgrid:
        ts, ps = du.best_durability(du.sell, c, n=501)
        tl, pl = du.best_durability(du.lease, c, n=51)
        tp, sp = du.best_durability(du.planner, c, n=51)
        choice.append((c, ts, tl, tp, ps, pl, du.sell(ts, c).surplus, sp))
    write_csv(RES / "durability_choice.csv",
              ["cost", "theta_sell", "theta_lease", "theta_planner",
               "profit_sell", "profit_lease", "surplus_sell", "surplus_planner"], choice)

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.3))
    ax = axes[0]
    cmap = plt.get_cmap("viridis")
    for j, c in enumerate(costs):
        sub = [r for r in rows if r[0] == c]
        col = cmap(j / (len(costs) - 1) * 0.85)
        ax.plot([r[1] for r in sub], [r[2] for r in sub], color=col, lw=2, label=f"sell, c={c}")
        ax.plot([r[1] for r in sub], [r[3] for r in sub], color=col, lw=1.2, ls="--")
        best = max(sub, key=lambda r: r[2])
        ax.plot(best[1], best[2], "o", color=col)
    ax.set_xlabel(r"Durability $\theta$ (0 = lasts one period, 1 = lasts forever)")
    ax.set_ylabel("Monopoly profit")
    ax.set_title("A. Profit vs durability (solid sell, dashed lease)")
    ax.legend(frameon=False, fontsize=8, ncol=2)

    ax = axes[1]
    ax.plot(cgrid, [r[1] for r in choice], color=RED, lw=2.4, label="Selling monopolist")
    ax.plot(cgrid, [r[2] for r in choice], color=BLUE, lw=2, ls="--", label="Leasing monopolist")
    ax.plot(cgrid, [r[3] for r in choice], color=GREEN, lw=1.5, ls=":", label="Social planner")
    ax.set_xlabel("Unit production cost c")
    ax.set_ylabel(r"Chosen durability $\theta^*$")
    ax.set_title("B. Planned obsolescence when production is cheap")
    ax.set_ylim(-0.05, 1.08)
    ax.legend(frameon=False, fontsize=9)
    fig.tight_layout()
    fig.savefig(FIG / "fig4_leasing_and_durability.png", dpi=200)
    plt.close(fig)
    return choice


def main():
    experiment_1_figures()
    prow = experiment_2_coase_conjecture()
    experiment_3_price_paths()
    choice = experiment_4_leasing_and_durability()

    bulow_sell, bulow_lease = du.sell(1.0).profit, du.lease(1.0).profit
    lines = ["# Results summary", "",
             "## Coase conjecture (infinite horizon, uniform valuations, r = 10%/yr)", "",
             "| Period length | delta | Opening price | Profit | % of monopoly profit |",
             "|---|---|---|---|---|"]
    for name, _, d, p, pi, share in prow:
        lines.append(f"| {name} | {d:.6f} | {p:.4f} | {pi:.4f} | {100 * share:.1f}% |")
    lines += ["", "Monopoly (commitment or leasing): price 0.5000, profit 0.2500.", "",
              "## Two-period model, fully durable good, c = 0, delta = 1", "",
              f"Selling profit {bulow_sell:.4f} vs leasing profit {bulow_lease:.4f}.", "",
              "## Chosen durability by unit cost (delta = 1)", "",
              "| c | theta (sell) | theta (lease) | theta (planner) |", "|---|---|---|---|"]
    for r in choice:
        if round(r[0] * 100) % 5 == 0:
            lines.append(f"| {r[0]:.2f} | {r[1]:.3f} | {r[2]:.2f} | {r[3]:.2f} |")
    (RES / "summary.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
