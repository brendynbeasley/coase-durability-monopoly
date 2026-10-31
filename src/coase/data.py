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
    "EC1700SIZECONCEN.zip": f"{CENSUS}/2017/sector00/EC1700SIZECONCEN.zip",
    "EC2200SIZECONCEN.zip": f"{CENSUS}/2022/sector00/EC2200SIZECONCEN.zip",
    "EC1731BASIC.zip": f"{CENSUS}/2017/sector31/EC1731BASIC.zip",
    "EC2231BASIC.zip": f"{CENSUS}/2022/sector31/EC2231BASIC.zip",
    "AllTablesIO.zip": "https://apps.bea.gov/industry/iTables%20Static%20Files/AllTablesIO.zip",
}
BEA_USE = "IOUse_Before_Redefinitions_PRO_2017_Detail.xlsx"

YEARS = {
    2017: {"conc": "EC1700SIZECONCEN", "basic": "EC1731BASIC", "naics": "NAICS2017"},
    2022: {"conc": "EC2200SIZECONCEN", "basic": "EC2231BASIC", "naics": "NAICS2022"},
}

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
            with urllib.request.urlopen(url, timeout=600) as r:
                path.write_bytes(r.read())
        hashes[name] = sha256(path)
    return hashes


# --------------------------------------------------------------------------
# Census
# --------------------------------------------------------------------------

def _read_census(stem: str) -> pd.DataFrame:
    with zipfile.ZipFile(RAW / f"{stem}.zip") as z:
        df = pd.read_csv(z.open(f"{stem}.dat"), sep="|", dtype=str)
    df.columns = [c.lstrip("#") for c in df.columns]
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

    conc = _read_census(spec["conc"])
    conc = conc[(conc.GEOTYPE == "01") & (conc.SECTOR == "31")
                & (conc.TYPOP == "00") & (conc[nc].str.len() == 6)]
    out = pd.DataFrame(index=pd.Index(sorted(conc[nc].unique()), name="naics"))
    for code, name in [("604", "cr4"), ("608", "cr8"), ("620", "cr20"), ("650", "cr50")]:
        rows = conc[conc.CONCENFI == code].set_index(nc)
        out[name] = _numeric(rows, "VAL_PCT") / 100.0
    rows = conc[conc.CONCENFI == "650"].set_index(nc)
    out["hhi"] = _numeric(rows, "HHI")
    rows = conc[conc.CONCENFI == "001"].set_index(nc)
    out["firms"] = _numeric(rows, "FIRM")

    basic = _read_census(spec["basic"])
    basic = basic[(basic.GEOTYPE == "01") & (basic[nc].str.len() == 6)].set_index(nc)
    for var in ["RCPTOT", "PAYANN", "BENEFIT", "CSTMTOT", "VALADD", "ASTEND", "EMP"]:
        out[var.lower()] = _numeric(basic, var)
    out["label"] = basic[nc + "_TTL"]
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


def attach_final_share(df: pd.DataFrame, fs: pd.DataFrame) -> pd.DataFrame:
    """Match each 6-digit NAICS to the BEA commodity with the longest prefix.

    A few 2022 NAICS codes were created by merging 2017 codes (for example
    336110 replaced 336111 and 336112). When no BEA prefix covers a code, we
    fall back to the BEA commodities whose NAICS lists start with the code's
    first five, then four, digits, and average their shares.
    """
    prefixes = fs.sort_values("prefix", key=lambda s: -s.str.len())
    lookup = list(zip(prefixes.prefix, prefixes.final_share, prefixes.private_share, prefixes.bea))
    rows = []
    for code in df.naics:
        hit = next(((f, p, b) for pre, f, p, b in lookup if code.startswith(pre)), None)
        if hit is None:
            for k in (5, 4):
                near = fs[fs.prefix.str.startswith(code[:k])].drop_duplicates("bea")
                if len(near):
                    hit = (near.final_share.mean(), near.private_share.mean(), "+".join(near.bea))
                    break
        rows.append(hit if hit else (np.nan, np.nan, None))
    f, p, b = zip(*rows)
    return df.assign(final_share=f, private_share=p, bea=b)


# --------------------------------------------------------------------------
# Panel
# --------------------------------------------------------------------------

def build_panel(final_cutoff: float = 0.5) -> pd.DataFrame:
    df = pd.concat([census_year(y) for y in YEARS], ignore_index=True)
    df = attach_final_share(df, bea_final_share())

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
    df["log_ship"] = np.log(df.rcptot)
    return df


def save_panel(df: pd.DataFrame) -> Path:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    path = PROCESSED / "industry_panel.csv"
    df.to_csv(path, index=False)
    return path


def load_panel() -> pd.DataFrame:
    return pd.read_csv(PROCESSED / "industry_panel.csv", dtype={"naics": str, "subsector": str})
