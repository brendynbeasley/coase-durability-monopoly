"""Run the empirical test and write results/empirics/ and figures/.

Usage:  python scripts/run_empirics.py      (after scripts/build_data.py)
"""

from __future__ import annotations

import json
import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from coase import data, empirics as em

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "empirics"
FIG = ROOT / "figures"
OUT.mkdir(parents=True, exist_ok=True)

COLORS = {"nondurable": "#2e7d32", "durable_intermediate": "#888888", "durable_final": "#b03a2e"}
plt.rcParams.update({"axes.spines.top": False, "axes.spines.right": False})


def stars(p):
    return "***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.10 else ""


def fmt(c, s):
    return f"{c:.3f} ({s:.3f})"


def main_table(specs) -> str:
    lines = ["| Specification | N | Nondurable | Durable intermediate | Durable final | Final minus nondurable | Durable minus nondurable |",
             "|---|---|---|---|---|---|---|"]
    rows = []
    for r in specs:
        sl = r.slopes
        df_, dd = r.diff_final, r.diff_durable
        lines.append(
            f"| {r.name} | {r.n} | {fmt(*sl['nondurable'])} | {fmt(*sl['durable_intermediate'])} | "
            f"{fmt(*sl['durable_final'])} | {df_[0]:.3f}{stars(df_[2])} (p={df_[2]:.3f}) | "
            f"{dd[0]:.3f}{stars(dd[2])} (p={dd[2]:.3f}) |")
        rows.append({"spec": r.name, "n": r.n,
                     **{f"slope_{g}": sl[g][0] for g in em.GROUPS},
                     **{f"se_{g}": sl[g][1] for g in em.GROUPS},
                     "diff_final": df_[0], "diff_final_se": df_[1], "diff_final_p": df_[2],
                     "diff_durable": dd[0], "diff_durable_se": dd[1], "diff_durable_p": dd[2]})
    pd.DataFrame(rows).to_csv(OUT / "main_results.csv", index=False)
    return "\n".join(lines)


def fig_binscatter(df):
    s = em.sample(df)
    fig, ax = plt.subplots(figsize=(7.5, 4.8))
    for g in em.GROUPS:
        sub = s[s.group == g]
        bins = pd.qcut(sub.cr4, 8, duplicates="drop")
        means = sub.groupby(bins, observed=True)[["cr4", "pcm"]].mean()
        ax.scatter(means.cr4, means.pcm, color=COLORS[g], s=40, zorder=3)
        b, a = np.polyfit(sub.cr4, sub.pcm, 1)
        xs = np.linspace(sub.cr4.min(), sub.cr4.max(), 50)
        ax.plot(xs, a + b * xs, color=COLORS[g], lw=2,
                label=f"{em.GROUP_LABELS[g]} (slope {b:+.2f}, n={len(sub)})")
    ax.set_xlabel("Share of industry sales held by the 4 largest firms (CR4)")
    ax.set_ylabel("Price-cost margin")
    ax.set_title("Concentration and margins, U.S. manufacturing 2017 and 2022\n(binned means of raw data)")
    ax.legend(frameon=False, fontsize=9)
    fig.tight_layout()
    fig.savefig(FIG / "fig5_concentration_margins.png", dpi=200)
    plt.close(fig)


def fig_slopes(specs):
    fig, ax = plt.subplots(figsize=(8.5, 0.42 * len(specs) + 1.8))
    names = [r.name for r in specs]
    y = np.arange(len(specs))[::-1]
    for k, g in enumerate(em.GROUPS):
        c = np.array([r.slopes[g][0] for r in specs])
        se = np.array([r.slopes[g][1] for r in specs])
        ax.errorbar(c, y + (1 - k) * 0.22, xerr=1.96 * se, fmt="o", color=COLORS[g],
                    capsize=2, ms=5, label=em.GROUP_LABELS[g])
    ax.axvline(0, color="black", lw=0.8)
    ax.set_yticks(y)
    ax.set_yticklabels(names)
    ax.set_xlabel("Effect of CR4 (or HHI, CR8) on the price-cost margin, with 95% CI")
    ax.set_title("Concentration slope by product type and specification")
    ax.legend(frameon=False, fontsize=9, loc="upper center", bbox_to_anchor=(0.45, -0.08), ncol=3)
    fig.tight_layout()
    fig.savefig(FIG / "fig6_slopes_by_specification.png", dpi=200)
    plt.close(fig)


def fig_bain(bain):
    b = bain[bain.group != "All manufacturing"]
    fig, ax = plt.subplots(figsize=(7, 4.2))
    cols = [COLORS[g] for g in em.GROUPS]
    x = np.arange(len(b))
    ax.bar(x, 100 * b.gap, yerr=196 * b.gap_se, color=cols, capsize=4)
    for xi, v in zip(x, b.gap):
        ax.text(xi + 0.12, 100 * v / 2, f"{100 * v:+.1f}", va="center", fontsize=11, color="white",
                fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(b.group)
    ax.axhline(0, color="black", lw=0.8)
    ax.set_ylabel("Margin gap, percentage points")
    ax.set_title("Bain's test by product type: margin of industries with CR8 ≥ 70%\nminus margin of industries with CR8 < 70%")
    fig.tight_layout()
    fig.savefig(FIG / "fig7_bain_split.png", dpi=200)
    plt.close(fig)


def fig_permutation(perm):
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.hist(perm["placebo"], bins=50, color="#bbbbbb")
    ax.axvline(perm["observed"], color=COLORS["durable_final"], lw=2.5,
               label=f"Observed gap {perm['observed']:.3f}  (p = {perm['p']:.3f})")
    ax.set_xlabel("Durable-final slope minus nondurable slope")
    ax.set_ylabel("Random relabelings")
    ax.set_title(f"Permutation test: {perm['draws']:,} random assignments of product types")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(FIG / "fig8_permutation_test.png", dpi=200)
    plt.close(fig)


def fig_between_within(specs, fd_periods):
    """Cross-industry gap in each census year next to the within-industry gap
    in each period between censuses."""
    yearly = [r for r in specs if r.name.endswith(" only")]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), sharey=True)
    ax = axes[0]
    x = np.arange(len(yearly))
    c = np.array([r.diff_final[0] for r in yearly])
    se = np.array([r.diff_final[1] for r in yearly])
    ax.bar(x, c, yerr=1.96 * se, color=COLORS["durable_final"], capsize=4)
    ax.set_xticks(x)
    ax.set_xticklabels([r.name.split()[0] for r in yearly])
    ax.set_title("A. Across industries, each census year")
    ax.set_ylabel("Durable-final slope minus nondurable slope")
    ax = axes[1]
    x = np.arange(len(fd_periods))
    ax.bar(x, fd_periods.gap, yerr=1.96 * fd_periods.gap_se, color="#888888", capsize=4)
    ax.set_xticks(x)
    ax.set_xticklabels(fd_periods.period)
    ax.set_title("B. Within industries, change between censuses")
    for a in axes:
        a.axhline(0, color="black", lw=0.8)
    fig.suptitle("Coase's prediction is a negative gap. It holds across industries, not within them over time.",
                 fontsize=11)
    fig.tight_layout()
    fig.savefig(FIG / "fig9_between_within.png", dpi=200)
    plt.close(fig)


def main():
    df = data.load_panel()

    desc = em.descriptives(df)
    desc.to_csv(OUT / "descriptives.csv", index=False)
    specs = em.specifications(df)
    table = main_table(specs)
    fd = em.first_differences(df)
    fd_periods = em.first_differences_by_period(df)
    fd_periods.to_csv(OUT / "first_differences_by_period.csv", index=False)
    cont = em.durables_continuous(df)
    life = em.service_life_test(df)
    bain = em.bain_table(df)
    bain.to_csv(OUT / "bain_split.csv", index=False)
    perm = em.permutation_test(df)
    top = em.most_concentrated(df)
    top.to_csv(OUT / "most_concentrated_durable_final_2022.csv", index=False)

    fig_binscatter(df)
    fig_slopes(specs)
    fig_bain(bain)
    fig_permutation(perm)
    fig_between_within(specs, fd_periods)

    md = ["# Empirical results", "",
          "Generated by `scripts/run_empirics.py`. Unit: 6-digit NAICS manufacturing industry. "
          "Outcome: price-cost margin (value added minus payroll, over shipments). "
          "Controls: capital-to-shipments ratio, log shipments, census year. "
          "Standard errors clustered by industry. * p<0.10, ** p<0.05, *** p<0.01.", "",
          "## Sample", "",
          "| Year | Group | Industries | Shipments ($bn) | Mean CR4 | Mean margin | Mean final-owner share |",
          "|---|---|---|---|---|---|---|"]
    for _, r in desc.iterrows():
        md.append(f"| {r.year} | {em.GROUP_LABELS[r.group]} | {r.industries} | {r.shipments_bn:,.0f} | "
                  f"{r.mean_cr4:.3f} | {r.mean_pcm:.3f} | {r.mean_final_share:.3f} |")
    md += ["", "## Concentration slope by product type", "", table, "",
           "## Within-industry changes between consecutive censuses", "",
           f"Stacked differences for codes present in both years of each pair, with period effects; N = {fd['n']}.", "",
           "| Group | Slope of change in margin on change in CR4 |", "|---|---|"]
    for g in em.GROUPS:
        md.append(f"| {em.GROUP_LABELS[g]} | {fmt(*fd['slopes'][g])} |")
    md += ["", f"Durable final minus nondurable: {fd['diff_final'][0]:.3f} (SE {fd['diff_final'][1]:.3f}, p = {fd['diff_final'][2]:.3f}).", "",
           "| Period | N | Nondurable | Durable intermediate | Durable final | Gap (p) |", "|---|---|---|---|---|---|"]
    for _, r in fd_periods.iterrows():
        md.append(f"| {r.period} | {r.n} | {r.slope_nondurable:.3f} | {r.slope_durable_intermediate:.3f} | "
                  f"{r.slope_durable_final:.3f} | {r.gap:+.3f} ({r.p:.3f}) |")
    if life:
        md += ["", "## Durable industries only, continuous service life", "",
               f"Interaction CR4 × service life (years): {life['coef']:.4f} (SE {life['se']:.4f}, p = {life['p']:.3f}, N = {life['n']}). "
               f"Mean service life {life['life_mean']:.1f} years, SD {life['life_sd']:.1f}."]
    md += ["",
           "## Durable industries only, continuous final-owner share", "",
           f"Interaction CR4 × final-owner share: {cont['coef']:.3f} (SE {cont['se']:.3f}, p = {cont['p']:.3f}, N = {cont['n']}).", "",
           "## Permutation test", "",
           f"Observed durable-final minus nondurable gap {perm['observed']:.3f}; "
           f"share of {perm['draws']:,} random relabelings at least as negative: p = {perm['p']:.3f}.", "",
           "## Bain's 70 percent split (CR8)", "",
           "| Group | Industries CR8 ≥ 70% | Margin | Industries CR8 < 70% | Margin | Gap (SE) |",
           "|---|---|---|---|---|---|"]
    for _, r in bain.iterrows():
        md.append(f"| {r.group} | {r.n_high} | {r.pcm_high:.3f} | {r.n_low} | {r.pcm_low:.3f} | {r.gap:+.3f} ({r.gap_se:.3f}) |")
    md += ["", "## Most concentrated long-lived durable industries, 2022", "",
           "| NAICS | Industry | CR4 | HHI | Firms | Shipments ($bn) | Margin |", "|---|---|---|---|---|---|---|"]
    for _, r in top.iterrows():
        hhi = "suppressed" if pd.isna(r.hhi) else f"{r.hhi:,.0f}"
        md.append(f"| {r.naics} | {r.label} | {r.cr4:.3f} | {hhi} | {r.firms:,.0f} | {r.rcptot / 1e6:,.1f} | {r.pcm:.3f} |")
    (OUT / "summary.md").write_text("\n".join(md) + "\n")
    (OUT / "headline.json").write_text(json.dumps({
        "baseline": {"slopes": {g: specs[0].slopes[g] for g in em.GROUPS},
                     "diff_final": specs[0].diff_final, "diff_durable": specs[0].diff_durable,
                     "n": specs[0].n},
        "permutation_p": perm["p"], "first_difference": fd["diff_final"],
        "service_life": life,
    }, indent=2, default=float) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
