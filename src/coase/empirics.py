"""Empirical test of Coase (1972) on U.S. manufacturing industries.

Hypotheses
----------
H1 (Bain 1951). In nondurable industries, more concentrated industries have
    higher price-cost margins.
H2 (Coase 1972). The concentration-margin slope is flatter in durable-goods
    industries, because a durable-goods seller also competes with the stock
    it has already sold and with its own future price cuts.
H3. The flattening is strongest for long-lived goods bought by final owners
    (households and equipment investors), the case Coase actually describes,
    and weaker for durable intermediate inputs that are used up inside other
    products.

Main specification (pooled Economic Censuses 2002, 2007, 2012, 2017 and 2022,
standard errors clustered by 6-digit industry):

    PCM_it = a_g + b_g * CR4_it + c * K/S_it + d * log(shipments)_it + year_t + e_it

where g indexes the three groups (nondurable, durable intermediate, durable
final). H2 and H3 are tests of b_durable_final < b_nondurable.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

GROUPS = ["nondurable", "durable_intermediate", "durable_final"]
GROUP_LABELS = {
    "nondurable": "Nondurable",
    "durable_intermediate": "Durable intermediate",
    "durable_final": "Durable final (long-lived)",
}
CONTROLS = "ks + log_ship + C(year)"


def sample(df: pd.DataFrame, conc: str = "cr4", outcome: str = "pcm") -> pd.DataFrame:
    cols = [outcome, conc, "ks", "log_ship", "group", "naics", "year", "rcptot"]
    s = df.dropna(subset=cols).copy()
    s = s[np.isfinite(s[outcome])]
    s["group"] = pd.Categorical(s.group, categories=GROUPS)
    return s


def _fit(formula: str, s: pd.DataFrame, weights=None):
    model = smf.wls(formula, s, weights=weights) if weights is not None else smf.ols(formula, s)
    return model.fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(s.naics)[0]})


@dataclass
class SlopeResult:
    name: str
    n: int
    slopes: dict  # group -> (coef, se)
    diff_final: tuple  # (coef, se, p) for durable_final - nondurable
    diff_durable: tuple | None  # (coef, se, p) for pooled durable - nondurable


def group_slopes(s: pd.DataFrame, conc: str = "cr4", outcome: str = "pcm",
                 extra: str = "", weights=None, name: str = "") -> SlopeResult:
    """Separate concentration slope for each group, plus the H3 contrast."""
    f = f"{outcome} ~ 0 + C(group) + {conc}:C(group) + {CONTROLS}{extra}"
    m = _fit(f, s, weights)
    slopes = {}
    for g in GROUPS:
        term = f"{conc}:C(group)[{g}]"
        slopes[g] = (m.params[term], m.bse[term])
    t = m.t_test(f"{conc}:C(group)[durable_final] - {conc}:C(group)[nondurable] = 0")
    diff_final = (float(np.squeeze(t.effect)), float(np.squeeze(t.sd)), float(np.squeeze(t.pvalue)))

    # H2 with the official Census durable/nondurable split.
    f2 = f"{outcome} ~ {conc} * durable + {CONTROLS}{extra}"
    m2 = _fit(f2, s, weights)
    term = f"{conc}:durable"
    diff_durable = (m2.params[term], m2.bse[term], m2.pvalues[term])
    return SlopeResult(name, int(m.nobs), slopes, diff_final, diff_durable)


def _with(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    return sample(df.dropna(subset=cols))


# Additional industry controls, added one at a time and then together.
EXTRA_CONTROLS = {
    "adv": "Advertising intensity",
    "imp_pen": "Import penetration",
    "rd": "R&D intensity",
}


def specifications(df: pd.DataFrame) -> list[SlopeResult]:
    out = []
    s = sample(df)
    out.append(group_slopes(s, name="Baseline (CR4)"))
    out.append(group_slopes(s, extra=" + C(naics)", name="Industry fixed effects"))
    available = [c for c in EXTRA_CONTROLS if c in df and df[c].notna().any()]
    for c in available:
        out.append(group_slopes(_with(df, [c]), extra=f" + {c}", name=f"+ {EXTRA_CONTROLS[c]}"))
    if len(available) > 1:
        out.append(group_slopes(_with(df, available), extra=" + " + " + ".join(available),
                                name="+ All industry controls"))
    out.append(group_slopes(s, extra=" + C(subsector)", name="Subsector fixed effects"))
    out.append(group_slopes(s, weights=s.rcptot, name="Weighted by shipments"))
    s_b = sample(df, outcome="pcm_benefits")
    out.append(group_slopes(s_b, outcome="pcm_benefits", name="Margin net of benefits"))
    s_h = sample(df, conc="hhi").assign(hhi=lambda d: d.hhi / 10_000)
    out.append(group_slopes(s_h, conc="hhi", name="HHI instead of CR4"))
    s_8 = sample(df, conc="cr8")
    out.append(group_slopes(s_8, conc="cr8", name="CR8 instead of CR4"))
    lo, hi = s.pcm.quantile([0.01, 0.99])
    out.append(group_slopes(s.assign(pcm=s.pcm.clip(lo, hi)), name="Margin winsorized 1%"))
    s_p = sample(df.assign(group=df.group_private))
    out.append(group_slopes(s_p, name="Private buyers only (no government)"))
    out.append(group_slopes(s[s.year > 2002], name="Excluding 2002 (imputed capital)"))
    for y in sorted(s.year.unique()):
        out.append(group_slopes(s[s.year == y], name=f"{y} only"))
    return out


def service_life_test(df: pd.DataFrame) -> dict | None:
    """Continuous version of H3: among durable industries, does the
    concentration slope fall as the product's service life rises?"""
    if "life" not in df or df.life.isna().all():
        return None
    s = _with(df[df.durable == 1], ["life"])
    m = _fit(f"pcm ~ cr4 * life + {CONTROLS}", s)
    term = "cr4:life"
    return {"n": int(m.nobs), "coef": m.params[term], "se": m.bse[term], "p": m.pvalues[term],
            "cr4_at_0": m.params["cr4"], "life_mean": s.life.mean(), "life_sd": s.life.std()}


def durables_continuous(df: pd.DataFrame, share: str = "final_share") -> dict:
    """Within durable industries: does the CR4 slope fall as the final-owner share rises?"""
    s = sample(df)
    s = s[s.durable == 1]
    m = _fit(f"pcm ~ cr4 * {share} + {CONTROLS}", s)
    term = f"cr4:{share}"
    return {"n": int(m.nobs), "coef": m.params[term], "se": m.bse[term], "p": m.pvalues[term],
            "cr4_at_0": m.params["cr4"]}


def permutation_test(df: pd.DataFrame, draws: int = 2000, seed: int = 1972) -> dict:
    """Randomly reassign group labels across industries (same group sizes,
    same label in both years) and recompute the durable-final minus
    nondurable slope gap. The p-value is the share of placebo gaps at least
    as negative as the observed one."""
    s = sample(df)
    labels = s.drop_duplicates("naics").set_index("naics").group.astype(str)

    def gap(group_of_naics: pd.Series) -> float:
        g = pd.Categorical(s.naics.map(group_of_naics), categories=GROUPS)
        m = smf.ols(f"pcm ~ 0 + C(g) + cr4:C(g) + {CONTROLS}", s.assign(g=g)).fit()
        return m.params["cr4:C(g)[durable_final]"] - m.params["cr4:C(g)[nondurable]"]

    observed = gap(labels)
    rng = np.random.default_rng(seed)
    placebo = np.array([
        gap(pd.Series(rng.permutation(labels.values), index=labels.index))
        for _ in range(draws)
    ])
    return {"observed": observed, "p": float(np.mean(placebo <= observed)),
            "draws": draws, "placebo": placebo}


def first_differences(df: pd.DataFrame) -> dict:
    """Within-industry changes between consecutive censuses (2002-07, 2007-12,
    2012-17, 2017-22), stacked, for codes present in both years of a pair."""
    years = sorted(df.year.unique())
    parts = []
    for y0, y1 in zip(years[:-1], years[1:]):
        a = df[df.year == y0].set_index("naics")
        b = df[df.year == y1].set_index("naics")
        common = a.index.intersection(b.index)
        parts.append(pd.DataFrame({
            "d_pcm": b.loc[common, "pcm"] - a.loc[common, "pcm"],
            "d_cr4": b.loc[common, "cr4"] - a.loc[common, "cr4"],
            "d_ks": b.loc[common, "ks"] - a.loc[common, "ks"],
            "group": a.loc[common, "group"],
            "period": f"{y0}-{y1}",
            "naics": common,
        }))
    d = pd.concat(parts, ignore_index=True).dropna()
    d["group"] = pd.Categorical(d.group, categories=GROUPS)
    m = smf.ols("d_pcm ~ 0 + C(group) + d_cr4:C(group) + d_ks + C(period)", d).fit(
        cov_type="cluster", cov_kwds={"groups": pd.factorize(d.naics)[0]})
    t = m.t_test("d_cr4:C(group)[durable_final] - d_cr4:C(group)[nondurable] = 0")
    return {
        "n": int(m.nobs),
        "periods": d.period.value_counts().sort_index().to_dict(),
        "slopes": {g: (m.params[f"d_cr4:C(group)[{g}]"], m.bse[f"d_cr4:C(group)[{g}]"]) for g in GROUPS},
        "diff_final": (float(np.squeeze(t.effect)), float(np.squeeze(t.sd)), float(np.squeeze(t.pvalue))),
    }


def first_differences_by_period(df: pd.DataFrame) -> pd.DataFrame:
    """The within-industry regression run separately for each census pair."""
    years = sorted(df.year.unique())
    rows = []
    for y0, y1 in zip(years[:-1], years[1:]):
        r = first_differences(df[df.year.isin([y0, y1])])
        rows.append({"period": f"{y0}-{y1}", "n": r["n"],
                     **{f"slope_{g}": r["slopes"][g][0] for g in GROUPS},
                     "gap": r["diff_final"][0], "gap_se": r["diff_final"][1], "p": r["diff_final"][2]})
    return pd.DataFrame(rows)


def bain_table(df: pd.DataFrame, cutoff: float = 0.70) -> pd.DataFrame:
    """Bain's (1951) comparison: mean margin above vs below CR8 = 70%."""
    s = df.dropna(subset=["pcm", "cr8"])
    rows = []
    for g in GROUPS + ["all"]:
        sub = s if g == "all" else s[s.group == g]
        hi, lo = sub[sub.cr8 >= cutoff].pcm, sub[sub.cr8 < cutoff].pcm
        se = np.sqrt(hi.var() / len(hi) + lo.var() / len(lo)) if len(hi) > 1 else np.nan
        rows.append({
            "group": GROUP_LABELS.get(g, "All manufacturing"),
            "n_high": len(hi), "pcm_high": hi.mean(),
            "n_low": len(lo), "pcm_low": lo.mean(),
            "gap": hi.mean() - lo.mean(), "gap_se": se,
        })
    return pd.DataFrame(rows)


def descriptives(df: pd.DataFrame) -> pd.DataFrame:
    s = df.dropna(subset=["pcm", "cr4"])
    return (s.groupby(["year", "group"])
            .agg(industries=("naics", "size"), shipments_bn=("rcptot", lambda x: x.sum() / 1e6),
                 mean_cr4=("cr4", "mean"), mean_hhi=("hhi", "mean"), mean_pcm=("pcm", "mean"),
                 mean_final_share=("final_share", "mean"))
            .reset_index())


def most_concentrated(df: pd.DataFrame, year: int = 2022, group: str = "durable_final",
                      n: int = 15) -> pd.DataFrame:
    """Uses the private-buyer definition so that goods bought mainly by the
    military (missiles, ammunition) do not crowd the list."""
    s = df[(df.year == year) & (df.group_private == group)].dropna(subset=["cr4"])
    s = s.sort_values("cr4", ascending=False).head(n)
    return s[["naics", "label", "cr4", "hhi", "firms", "rcptot", "pcm", "final_share"]]
