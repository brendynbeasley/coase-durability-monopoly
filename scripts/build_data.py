"""Download the raw Census and BEA files and build data/processed/industry_panel.csv.

Usage:  python scripts/build_data.py [--force]
"""

from __future__ import annotations

import json
import sys

from coase import data

COLUMNS = [
    "naics", "label", "year", "subsector", "durable", "group", "group_private",
    "final_share", "private_share", "bea",
    "cr4", "cr8", "cr20", "cr50", "hhi", "firms",
    "rcptot", "payann", "benefit", "cstmtot", "valadd", "astend", "emp",
    "pchadvt", "imports", "exports",
    "pcm", "pcm_benefits", "ks", "ks_imputed", "log_ship",
    "adv", "rd", "imp_pen", "exp_share", "life",
]


def main():
    hashes = data.download(force="--force" in sys.argv)
    panel = data.build_panel()[COLUMNS]
    path = data.save_panel(panel)

    manifest = {
        "sources": data.RAW_FILES,
        "sha256": hashes,
        "rows": len(panel),
        "industries_by_year": panel.groupby("year").size().to_dict(),
    }
    (data.PROCESSED / "manifest.json").write_text(json.dumps(manifest, indent=2, default=str) + "\n")
    print(f"wrote {path} ({len(panel)} rows)")


if __name__ == "__main__":
    main()
