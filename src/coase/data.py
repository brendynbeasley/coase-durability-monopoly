"""Download and assemble the industry dataset used in the empirical test.

Sources (all public, no API key needed):

* U.S. Census Bureau, Economic Census 2017 and 2022
  - Concentration of the largest firms (CR4, CR8, CR20, CR50, HHI)
  - Manufacturing summary statistics (shipments, payroll, value added, assets)
* Bureau of Economic Analysis, 2017 detailed Use table (before redefinitions,
  producers' prices), used to measure how much of each product goes to final
  owners (households and equipment investment) rather than to other industries.

Unit of observation: a 6-digit NAICS manufacturing industry in a census year.
"""

from __future__ import annotations

import hashlib
import io
import urllib.request
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"

CENSUS = "https://www2.census.gov/programs-surveys/economic-census/data"
RAW_FILES = {
    "EC0231SR12.zip": f"{CENSUS}/2002/sector31/EC0231SR12.zip",
    "ec0231i3.zip": f"{CENSUS}/2002/sector31/ec0231i3.zip",
    "EC0731SR12.zip": f"{CENSUS}/2007/sector31/EC0731SR12.zip",
    "EC0731SG2.zip": f"{CENSUS}/2007/sector31/EC0731SG2.zip",
    "EC1231SR2.zip": f"{CENSUS}/2012/sector31/EC1231SR2.zip",
    "EC1231SG1.zip": f"{CENSUS}/2012/sector31/EC1231SG1.zip",
    "EC1700SIZECONCEN.zip": f"{CENSUS}/2017/sector00/EC1700SIZECONCEN.zip",
    "EC2200SIZECONCEN.zip": f"{CENSUS}/2022/sector00/EC2200SIZECONCEN.zip",
    "EC1731BASIC.zip": f"{CENSUS}/2017/sector31/EC1731BASIC.zip",
    "EC2231BASIC.zip": f"{CENSUS}/2022/sector31/EC2231BASIC.zip",
    "AllTablesIO.zip": "https://apps.bea.gov/industry/iTables%20Static%20Files/AllTablesIO.zip",
    "PEQBridge_2017_DET.xlsx": "https://apps.bea.gov/industry/xls/io-annual/PEQBridge_2017_DET.xlsx",
    "PCEBridge_2017_DET.xlsx": "https://apps.bea.gov/industry/xls/io-annual/PCEBridge_2017_DET.xlsx",
    "detailnonres_dep1.xlsx": "https://apps.bea.gov/national/FA2004/Details/xls/detailnonres_dep1.xlsx",
    "detailnonres_stk1.xlsx": "https://apps.bea.gov/national/FA2004/Details/xls/detailnonres_stk1.xlsx",
    "DetailCDG.xlsx": "https://apps.bea.gov/national/FA2004/Details/xls/DetailCDG.xlsx",
    "nsf20311-tab017.xlsx": "https://ncses.nsf.gov/pubs/nsf20311/assets/data-tables/tables/nsf20311-tab017.xlsx",
    "nsf24335-tab017.xlsx": "https://ncses.nsf.gov/pubs/nsf24335/assets/data-tables/tables/nsf24335-tab017.xlsx",
}
# NSF Business Enterprise R&D Survey, table 17: domestic R&D as a percent of
# domestic sales of companies that perform or fund R&D, by industry, for
# 2017 (nsf20311) and 2022 (nsf24335).
RD_TABLES = ["nsf20311-tab017.xlsx", "nsf24335-tab017.xlsx"]

# Census related-party trade files: domestic exports and imports for
# consumption by 6-digit NAICS and country, 2005 onward. Census publishes no
# comparable keyless file for 2002, so import penetration is missing in 2002.
TRADE = "https://www.census.gov/foreign-trade/Press-Release/related_party"
TRADE_FILES = {2007: "rp_naics6_2005.csv", 2012: "rp_naics6_2011.csv",
               2017: "rp_naics6_2016.csv", 2022: "rp_naics6_2021_to_2025.csv"}
RAW_FILES.update({name: f"{TRADE}/{name}" for name in TRADE_FILES.values()})
BEA_USE = "IOUse_Before_Redefinitions_PRO_2017_Detail.xlsx"

# Service lives. BEA's fixed-asset accounts give depreciation and net stock by
# asset type; with geometric depreciation at rate d, the mean service life of
# an asset is 1/d. The PEQ and PCE bridge tables say which equipment and
# consumer-durable categories each commodity is sold into. These two maps line
# the bridge categories (by NIPA line) up with the fixed-asset codes.
PEQ_TO_ASSET = {
    4: ["EP1A", "EP1B", "EP1D", "EP1E", "EP1G", "EP1H"], 5: ["EP20"], 6: ["EP34", "EP35"],
    7: ["EP36"], 8: ["EP31"], 9: ["EP12"], 11: ["EI12"], 12: ["EI21", "EI22"], 13: ["EI30"],
    14: ["EI40"], 15: ["EI50"], 16: ["EI60"], 19: ["ET11"], 20: ["ET12"], 21: ["ET20"],
    22: ["ET30"], 23: ["ET40"], 24: ["ET50"], 26: ["EO11", "EO12"], 27: ["EO21", "EO30"],
    28: ["EO22", "EO40"], 29: ["EO50"], 30: ["EO60"], 31: ["EO71", "EO72"], 32: ["EO80"],
    34: ["EO71"],  # residential equipment, mostly appliances
}
PCE_TO_CDG = {
    7: "mv10", 8: "mv10", 13: "mv10", 9: "mv20", 17: "mv20", 21: "mv30", 22: "mv30",
    25: "fh11", 26: "fh12", 27: "fh13", 28: "fh14", 30: "fh20", 31: "fh20", 33: "fh30",
    34: "fh30", 36: "fh40", 37: "fh40", 41: "rg11", 42: "rg11", 43: "rg11", 45: "rg11",
    46: "rg11", 47: "rg12", 49: "rgpc", 50: "rgcs", 51: "rgca", 52: "rg20", 54: "rg31",
    55: "rg32", 57: "rgpb", 58: "rgpa", 59: "rgrv", 60: "rg40", 61: "rg50", 64: "od10",
    65: "od10", 67: "od20", 68: "od20", 69: "od30", 70: "od40", 71: "od50",
}
LIFE_YEAR = 2017

# The 2002-2012 concentration tables use one layout and the 2017-2022 tables
# another. "old" files code the largest-firm groups 856/857/858/859 and report
# the share in CCORCPPCT and the HHI in VSHERFI.
OLD_CONC = {"codes": {"856": "cr4", "857": "cr8", "858": "cr20", "859": "cr50"},
            "all": "004", "share": "CCORCPPCT", "hhi": "VSHERFI", "firms": "COMPANY"}
NEW_CONC = {"codes": {"604": "cr4", "608": "cr8", "620": "cr20", "650": "cr50"},
            "all": "001", "share": "VAL_PCT", "hhi": "HHI", "firms": "FIRM"}

YEARS = {
    2002: {"conc": "EC0231SR12", "basic": "ec0231i3", "naics": "NAICS2002", "layout": OLD_CONC,
           "label": "NAICS2002_MEANING", "rename": {"PAYANT": "PAYANN", "BENTOT": "BENEFIT"}},
    2007: {"conc": "EC0731SR12", "basic": "EC0731SG2", "naics": "NAICS2007", "layout": OLD_CONC,
           "label": "NAICS2007_MEANING", "rename": {}},
    2012: {"conc": "EC1231SR2", "basic": "EC1231SG1", "naics": "NAICS2012", "layout": OLD_CONC,
           "label": "NAICS2012_TTL", "rename": {}},
    2017: {"conc": "EC1700SIZECONCEN", "basic": "EC1731BASIC", "naics": "NAICS2017", "layout": NEW_CONC,
           "label": "NAICS2017_TTL", "rename": {}},
    2022: {"conc": "EC2200SIZECONCEN", "basic": "EC2231BASIC", "naics": "NAICS2022", "layout": NEW_CONC,
           "label": "NAICS2022_TTL", "rename": {}},
}
BASIC_VARS = ["RCPTOT", "PAYANN", "BENEFIT", "CSTMTOT", "VALADD", "ASTEND", "EMP", "PCHADVT"]

# Census M3 survey definition of durable-goods manufacturing (3-digit NAICS).
DURABLE_SUBSECTORS = {"321", "327", "331", "332", "333", "334", "335", "336", "337", "339"}

# BEA final-use columns. "Final owner" uses are purchases by households and
# equipment investment by businesses and governments: the buyers who hold a
# durable good as a stock. Exports, imports and inventory change are excluded
# from the denominator because they say nothing about who holds the good in
# the U.S.
FINAL_OWNER_COLS = ["F01000", "F02E00", "F06E00", "F07E00", "F10E00"]
# Robustness: private owners only (households and business equipment), which
# drops military and other government purchases.
PRIVATE_OWNER_COLS = ["F01000", "F02E00"]
EXCLUDED_COLS = ["F03000", "F04000", "F05000"]


# --------------------------------------------------------------------------
# Download
# --------------------------------------------------------------------------

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download(force: bool = False) -> dict[str, str]:
    """Fetch every raw file into data/raw and return their SHA-256 hashes."""
    RAW.mkdir(parents=True, exist_ok=True)
    hashes = {}
    for name, url in RAW_FILES.items():
        path = RAW / name
        if force or not path.exists():
            print(f"downloading {name}")
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (compatible; coase-durability-monopoly data download)"})
            with urllib.request.urlopen(req, timeout=600) as r:
                path.write_bytes(r.read())
        hashes[name] = sha256(path)
    return hashes


# --------------------------------------------------------------------------
# Census
# --------------------------------------------------------------------------

def _read_census(stem: str) -> pd.DataFrame:
    with zipfile.ZipFile(RAW / f"{stem}.zip") as z:
        dat = next(n for n in z.namelist() if n.lower().endswith(".dat"))
        df = pd.read_csv(z.open(dat), sep="|", dtype=str, encoding="latin-1")
    df.columns = [c.strip().lstrip("#") for c in df.columns]
    return df


def _numeric(df: pd.DataFrame, var: str) -> pd.Series:
    """Census value with suppressed or flagged cells set to missing."""
    x = pd.to_numeric(df[var], errors="coerce")
    flag = var + "_F"
    if flag in df:
        x[df[flag].notna()] = np.nan
    return x


def census_year(year: int) -> pd.DataFrame:
    spec = YEARS[year]
    nc = spec["naics"]

    lay = spec["layout"]

    conc = _read_census(spec["conc"])
    keep = (conc.GEOTYPE == "01") & (conc.SECTOR == "31") & (conc[nc].str.len() == 6)
    if "TYPOP" in conc:
        keep &= conc.TYPOP == "00"
    conc = conc[keep]
    out = pd.DataFrame(index=pd.Index(sorted(conc[nc].unique()), name="naics"))
    for code, name in lay["codes"].items():
        rows = conc[conc.CONCENFI == code].set_index(nc)
        out[name] = _numeric(rows, lay["share"]) / 100.0
    # The HHI is reported on one of the rows (which one varies by year), with
    # the others flagged; take the reported value.
    hhi = conc.assign(h=_numeric(conc, lay["hhi"])).query("h > 0").groupby(nc).h.max()
    out["hhi"] = hhi
    rows = conc[conc.CONCENFI == lay["all"]].set_index(nc)
    out["firms"] = _numeric(rows, lay["firms"])
    # Some files report CR20 or CR50 as 0 when the industry has fewer than 20
    # or 50 firms; the true share is then 100 percent.
    for k, name in ((8, "cr8"), (20, "cr20"), (50, "cr50")):
        out.loc[(out[name] == 0) & (out.firms <= k), name] = 1.0
        out.loc[out[name] == 0, name] = np.nan

    basic = _read_census(spec["basic"])
    for old, new in spec["rename"].items():
        basic = basic.rename(columns={old: new, old + "_F": new + "_F"})
    basic = basic[(basic.GEOTYPE == "01") & (basic[nc].str.len() == 6)].set_index(nc)
    for var in BASIC_VARS:
        out[var.lower()] = _numeric(basic, var) if var in basic else np.nan
    out["label"] = basic[spec["label"]].str.strip()
    out["year"] = year
    return out.reset_index()


# --------------------------------------------------------------------------
# BEA: share of each product bought by final owners
# --------------------------------------------------------------------------

def _code(x) -> str:
    """Excel stores numeric-looking codes as floats; normalise to text."""
    return str(int(x)) if isinstance(x, (int, float)) else str(x).strip()


def _bea_naics_map(xlsx: Path) -> pd.DataFrame:
    """BEA detail code -> list of NAICS prefixes, from the 'NAICS Codes' sheet."""
    n = pd.read_excel(xlsx, "NAICS Codes", header=None)
    n = n[n[3].notna() & n[6].notna()]
    rows = []
    for _, r in n.iterrows():
        code = _code(r[3])
        for part in _code(r[6]).replace(";", ",").split(","):
            part = part.strip()
            if "-" in part:
                # Shorthand ranges: "32192-9" is 32192..32199,
                # "332111-2" is 332111..332112.
                lo, hi = (p.strip() for p in part.split("-"))
                hi = lo[: len(lo) - len(hi)] + hi
                for v in range(int(lo), int(hi) + 1):
                    rows.append((code, str(v)))
            elif part.isdigit():
                rows.append((code, part))
    return pd.DataFrame(rows, columns=["bea", "prefix"])


def bea_final_share() -> pd.DataFrame:
    """Final-owner share of domestic use for each BEA detail commodity."""
    xlsx = RAW / "bea" / BEA_USE
    if not xlsx.exists():
        xlsx.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(RAW / "AllTablesIO.zip") as z:
            xlsx.write_bytes(z.read(BEA_USE))
    u = pd.read_excel(xlsx, "2017", header=None)
    header = [str(c) for c in u.iloc[5]]
    body = u.iloc[6:].copy()
    body.columns = header
    body = body[body["Code"].notna()]
    body.index = [_code(c) for c in body["Code"]]
    body = body.drop(columns=["Code", "Commodity Description"])
    body = body.apply(pd.to_numeric, errors="coerce").fillna(0.0)
    final_cols = [c for c in header
                  if c.startswith("F") and len(c) == 6 and c not in EXCLUDED_COLS]
    domestic = body["T001"] + body[final_cols].sum(axis=1)
    out = pd.DataFrame({
        "final_share": (body[FINAL_OWNER_COLS].sum(axis=1) / domestic).where(domestic > 0),
        "private_share": (body[PRIVATE_OWNER_COLS].sum(axis=1) / domestic).where(domestic > 0),
    })
    out.index.name = "bea"
    return out.reset_index().merge(_bea_naics_map(xlsx), on="bea")


def attach_bea(df: pd.DataFrame, table: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """Match each 6-digit NAICS to the BEA commodity with the longest prefix
    and copy its values in `cols`.

    Some NAICS codes in other vintages were created by merging 2017 codes (for
    example 336110 replaced 336111 and 336112). When no BEA prefix covers a
    code, we fall back to the BEA commodities whose NAICS lists start with the
    code's first five, then four, digits, and average their values.
    """
    prefixes = table.sort_values("prefix", key=lambda s: -s.str.len())
    lookup = list(zip(prefixes.prefix, prefixes[cols].itertuples(index=False), prefixes.bea))
    vals, codes = [], []
    for code in df.naics:
        hit = next(((v, b) for pre, v, b in lookup if code.startswith(pre)), None)
        if hit is None:
            for k in (5, 4):
                near = table[table.prefix.str.startswith(code[:k])].drop_duplicates("bea")
                if len(near):
                    hit = (tuple(near[cols].mean()), "+".join(near.bea))
                    break
        vals.append(tuple(hit[0]) if hit else (np.nan,) * len(cols))
        codes.append(hit[1] if hit else None)
    out = df.copy()
    out[cols] = pd.DataFrame(vals, columns=cols, index=df.index)
    out["bea"] = codes
    return out


def attach_final_share(df: pd.DataFrame, fs: pd.DataFrame) -> pd.DataFrame:
    return attach_bea(df, fs, ["final_share", "private_share"])


# --------------------------------------------------------------------------
# BEA: service life of each commodity
# --------------------------------------------------------------------------

def _fixed_asset_sheet(path: Path, header_row: int, first_data_row: int, code_pattern=None):
    """Read a BEA fixed-asset 'Details' workbook into (code, year) values,
    summing across sheets (the nonresidential files split industries over
    several sheets)."""
    x = pd.ExcelFile(path)
    total = None
    for s in x.sheet_names:
        if s.lower() in ("readme", "datasets"):
            continue
        d = pd.read_excel(x, s, header=None)
        years = pd.to_numeric(d.iloc[header_row, 2:], errors="coerce")
        body = d.iloc[first_data_row:, :].copy()
        body = body[body[0].notna()]
        body[0] = body[0].astype(str).str.strip()
        if code_pattern:
            body = body[body[0].str.match(code_pattern)]
        vals = body.iloc[:, 2:2 + len(years)].apply(pd.to_numeric, errors="coerce")
        vals.columns = years.astype("Int64").tolist()
        vals.index = body[0].values
        vals = vals.groupby(level=0).sum()
        total = vals if total is None else total.add(vals, fill_value=0)
    return total


def asset_service_lives(year: int = LIFE_YEAR) -> dict[str, float]:
    """Mean service life 1/d by fixed-asset code, d = depreciation / average net stock."""
    dep = _fixed_asset_sheet(RAW / "detailnonres_dep1.xlsx", 5, 7, r"^E[A-Z0-9]{3}$")
    stk = _fixed_asset_sheet(RAW / "detailnonres_stk1.xlsx", 5, 7, r"^E[A-Z0-9]{3}$")
    lives = {}
    for code in dep.index:
        avg = (stk.loc[code, year] + stk.loc[code, year - 1]) / 2
        if avg > 0 and dep.loc[code, year] > 0:
            lives[code] = avg / dep.loc[code, year]

    x = pd.ExcelFile(RAW / "DetailCDG.xlsx")
    dsheet = next(s for s in x.sheet_names if s.strip().startswith("Depreciation"))
    ssheet = next(s for s in x.sheet_names if s.strip().startswith("Net Stock"))
    for sheet, key in ((dsheet, "dep"), (ssheet, "stk")):
        d = pd.read_excel(x, sheet, header=None)
        years = pd.to_numeric(d.iloc[5, 2:], errors="coerce").astype("Int64").tolist()
        body = d.iloc[8:, :]
        body = body[body[0].notna()]
        vals = body.iloc[:, 2:2 + len(years)].apply(pd.to_numeric, errors="coerce")
        vals.columns = years
        vals.index = body[0].astype(str).str.strip().str[-4:].values
        if key == "dep":
            cdg_dep = vals
        else:
            cdg_stk = vals
    for code in cdg_dep.index:
        avg = (cdg_stk.loc[code, year] + cdg_stk.loc[code, year - 1]) / 2
        if avg > 0 and cdg_dep.loc[code, year] > 0:
            lives[code] = avg / cdg_dep.loc[code, year]
    return lives


def _bridge(path: Path) -> pd.DataFrame:
    d = pd.read_excel(path, "2017", header=None, skiprows=5).iloc[:, :5]
    d.columns = ["line", "category", "bea", "description", "producer_value"]
    d["line"] = pd.to_numeric(d.line, errors="coerce")
    d["producer_value"] = pd.to_numeric(d.producer_value, errors="coerce")
    d["bea"] = [_code(c) for c in d.bea]
    return d.dropna(subset=["line", "producer_value"])


def commodity_service_life() -> pd.DataFrame:
    """Flow-weighted mean service life of the equipment and consumer-durable
    categories each commodity is sold into (producers' value weights)."""
    lives = asset_service_lives()
    rows = []
    for path, mapping in ((RAW / "PEQBridge_2017_DET.xlsx", PEQ_TO_ASSET),
                          (RAW / "PCEBridge_2017_DET.xlsx", PCE_TO_CDG)):
        b = _bridge(path)
        b = b[b.line.isin(mapping) & (b.producer_value > 0)]
        for _, r in b.iterrows():
            codes = mapping[int(r.line)]
            codes = codes if isinstance(codes, list) else [codes]
            ls = [lives[c] for c in codes if c in lives]
            if ls:
                rows.append((r.bea, r.producer_value, float(np.mean(ls))))
    t = pd.DataFrame(rows, columns=["bea", "w", "life"])
    out = t.groupby("bea").apply(lambda g: np.average(g.life, weights=g.w), include_groups=False)
    out = out.rename("life").to_frame()
    out["durable_flow"] = t.groupby("bea").w.sum()
    return out.reset_index()


# --------------------------------------------------------------------------
# NSF: R&D intensity
# --------------------------------------------------------------------------

def _rd_prefixes(cell: str) -> list[str]:
    """Turn a BERD NAICS cell such as '313–16', '336411–13', '3255, 3259' or
    'other 333' into a list of NAICS prefixes."""
    out = []
    for part in str(cell).replace("–", "-").replace("other", "").split(","):
        part = part.strip()
        if "-" in part:
            lo, hi = (s.strip() for s in part.split("-"))
            hi = lo[: len(lo) - len(hi)] + hi
            out += [str(v) for v in range(int(lo), int(hi) + 1)]
        elif part.isdigit():
            out.append(part)
    return out


def rd_intensity() -> pd.DataFrame:
    """R&D intensity by BERD manufacturing industry, averaged over 2017 and 2022."""
    frames = []
    for name in RD_TABLES:
        d = pd.read_excel(RAW / name, header=None)
        start = d.index[d[1].astype(str).str.strip().isin(["31–33", "31-33"])][0] + 1
        stop = d.index[d[0].astype(str).str.startswith("Nonmanufacturing")][0]
        body = d.loc[start:stop - 1, [1, 4]]
        for cell, val in body.itertuples(index=False):
            v = pd.to_numeric(val, errors="coerce")
            for prefix in _rd_prefixes(cell):
                frames.append((name, prefix, v / 100.0))
    t = pd.DataFrame(frames, columns=["table", "prefix", "rd"])
    return t.groupby("prefix", as_index=False).rd.mean()


def attach_rd(df: pd.DataFrame) -> pd.DataFrame:
    """Longest-prefix match of each 6-digit NAICS to a BERD industry. R&D
    intensity is treated as a fixed industry characteristic in every year."""
    t = rd_intensity().dropna()
    lookup = sorted(zip(t.prefix, t.rd), key=lambda x: -len(x[0]))
    rd = [next((v for p, v in lookup if code.startswith(p)), np.nan) for code in df.naics]
    return df.assign(rd=rd)


# --------------------------------------------------------------------------
# Census: imports and exports
# --------------------------------------------------------------------------

def trade(year: int) -> pd.DataFrame:
    """Exports and imports (dollars) by 6-digit NAICS for one year, summed
    over countries."""
    d = pd.read_csv(RAW / TRADE_FILES[year], skiprows=3, usecols=[0, 2, 3, 7], dtype={0: str})
    d.columns = ["naics", "year", "exports", "imports"]
    d = d[d.year == year]
    d["naics"] = d.naics.str[:6]
    return d.groupby("naics", as_index=False)[["exports", "imports"]].sum()


def attach_trade(df: pd.DataFrame) -> pd.DataFrame:
    """Import penetration = imports / (shipments + imports - exports).

    Trade statistics sometimes bundle several 6-digit industries under a code
    ending in X (for example 33641X for aircraft and parts). For those, trade
    and shipments are pooled over every census industry sharing the first five
    digits and the pooled ratio is given to each member. Values above 1, which
    arise where trade and production classifications disagree, are capped at 1.
    """
    out = []
    for year, g in df.groupby("year"):
        g = g.copy()
        if year not in TRADE_FILES:
            g[["exports", "imports", "imp_pen", "exp_share"]] = np.nan
            out.append(g)
            continue
        t = trade(year)
        bundled = {c[:5] for c in t.naics if c.endswith("X")}
        t["key"] = np.where(t.naics.str.endswith("X"), t.naics.str[:5], t.naics)
        t.loc[t.naics.str[:5].isin(bundled), "key"] = t.naics.str[:5]
        g["key"] = np.where(g.naics.str[:5].isin(bundled), g.naics.str[:5], g.naics)
        tk = t.groupby("key")[["exports", "imports"]].sum()
        ship = (g.rcptot * 1000).groupby(g.key).sum()
        absorption = ship + tk.imports.reindex(ship.index) - tk.exports.reindex(ship.index)
        pen = (tk.imports.reindex(ship.index) / absorption).where(absorption > 0).clip(upper=1.0)
        exp = tk.exports.reindex(ship.index) / ship
        g["imp_pen"] = g.key.map(pen)
        g["exp_share"] = g.key.map(exp)
        g["exports"] = g.key.map(tk.exports)
        g["imports"] = g.key.map(tk.imports)
        out.append(g.drop(columns="key"))
    return pd.concat(out, ignore_index=True)


# --------------------------------------------------------------------------
# Panel
# --------------------------------------------------------------------------

def build_panel(final_cutoff: float = 0.5) -> pd.DataFrame:
    df = pd.concat([census_year(y) for y in YEARS], ignore_index=True)
    fs = bea_final_share().merge(commodity_service_life(), on="bea", how="left")
    df = attach_bea(df, fs, ["final_share", "private_share", "life"])
    df = attach_rd(df)
    df = attach_trade(df)

    df["subsector"] = df.naics.str[:3]
    df["durable"] = df.subsector.isin(DURABLE_SUBSECTORS).astype(int)
    df["durable_final"] = ((df.durable == 1) & (df.final_share >= final_cutoff)).astype(int)
    df["group"] = np.select(
        [df.durable == 0, df.durable_final == 1],
        ["nondurable", "durable_final"],
        default="durable_intermediate",
    )
    df["group_private"] = np.select(
        [df.durable == 0, df.private_share >= final_cutoff],
        ["nondurable", "durable_final"],
        default="durable_intermediate",
    )

    # Collins-Preston price-cost margin and controls.
    df["pcm"] = (df.valadd - df.payann) / df.rcptot
    df["pcm_benefits"] = (df.valadd - df.payann - df.benefit) / df.rcptot
    df["ks"] = df.astend / df.rcptot
    # The 2002 census did not publish gross depreciable assets. Carry back each
    # industry's 2007 capital-to-shipments ratio (same NAICS code) and flag it.
    ks07 = df[df.year == 2007].set_index("naics").ks
    fill = (df.year == 2002) & df.ks.isna()
    df["ks_imputed"] = (fill & df.naics.map(ks07).notna()).astype(int)
    df.loc[fill, "ks"] = df.loc[fill, "naics"].map(ks07)
    df["log_ship"] = np.log(df.rcptot)
    df["adv"] = df.pchadvt / df.rcptot
    return df


def save_panel(df: pd.DataFrame) -> Path:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    path = PROCESSED / "industry_panel.csv"
    df.to_csv(path, index=False)
    return path


def load_panel() -> pd.DataFrame:
    return pd.read_csv(PROCESSED / "industry_panel.csv", dtype={"naics": str, "subsector": str})
