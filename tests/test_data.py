"""Checks on the processed industry panel and the empirical pipeline.

These run on data/processed/industry_panel.csv, which is committed, so no
download is needed.
"""

import numpy as np
import pandas as pd
import pytest

from coase import data, empirics


@pytest.fixture(scope="module")
def panel():
    return data.load_panel()


def test_panel_size(panel):
    assert panel.groupby("year").size().to_dict() == {
        2002: 473, 2007: 471, 2012: 364, 2017: 360, 2022: 346}
    assert not panel.duplicated(["naics", "year"]).any()


def test_concentration_ratios_are_ordered(panel):
    s = panel.dropna(subset=["cr4", "cr8", "cr20", "cr50"])
    assert (s.cr4 <= s.cr8 + 1e-9).all()
    assert (s.cr8 <= s.cr20 + 1e-9).all()
    assert (s.cr20 <= s.cr50 + 1e-9).all()
    assert s.cr4.between(0, 1).all()


def test_every_industry_has_a_final_owner_share(panel):
    assert panel.final_share.notna().all()
    assert panel.final_share.between(0, 1).all()
    assert (panel.private_share <= panel.final_share + 1e-9).all()


def test_durable_classification(panel):
    durable = panel.subsector.isin(data.DURABLE_SUBSECTORS)
    assert (panel.durable == durable.astype(int)).all()
    assert (panel.loc[~durable, "group"] == "nondurable").all()
    g = panel[panel.year == 2017].set_index("naics").group
    assert g["336411"] == "durable_final"          # aircraft
    assert g["337121"] == "durable_final"          # upholstered household furniture
    assert g["334413"] == "durable_intermediate"   # semiconductors
    assert g["312120"] == "nondurable"             # breweries


def test_margins_are_sensible(panel):
    s = panel.dropna(subset=["pcm"])
    assert s.pcm.between(-0.5, 1).all()
    assert 0.25 < s.pcm.median() < 0.45


def test_final_share_fallback_for_merged_2022_codes():
    fs = pd.DataFrame({"bea": ["A", "B"], "final_share": [0.2, 0.6],
                       "private_share": [0.1, 0.5], "prefix": ["336111", "336112"]})
    out = data.attach_final_share(pd.DataFrame({"naics": ["336110", "336111"]}), fs)
    assert out.final_share.tolist() == pytest.approx([0.4, 0.2])


def test_headline_result_reproduces(panel):
    base = empirics.group_slopes(empirics.sample(panel))
    assert base.n == 1982
    assert base.slopes["nondurable"][0] == pytest.approx(0.121, abs=1e-3)
    assert base.slopes["durable_final"][0] == pytest.approx(0.012, abs=1e-3)
    assert base.diff_final[0] == pytest.approx(-0.109, abs=1e-3)


def test_original_two_census_result_still_reproduces(panel):
    base = empirics.group_slopes(empirics.sample(panel[panel.year >= 2017]))
    assert base.n == 699
    assert base.diff_final[0] == pytest.approx(-0.148, abs=1e-3)


def test_2002_capital_is_carried_back_from_2007(panel):
    p02 = panel[panel.year == 2002]
    assert p02.ks_imputed.sum() > 450
    k07 = panel[panel.year == 2007].set_index("naics").ks
    row = p02[p02.ks_imputed == 1].iloc[0]
    assert row.ks == pytest.approx(k07[row.naics])


def test_rd_and_service_life_ranges(panel):
    assert panel.rd.notna().all()
    assert panel.rd.between(0, 0.4).all()
    s = panel[panel.year == 2017].set_index("naics")
    assert s.loc["325412", "rd"] > 0.10       # pharmaceuticals are R&D intensive
    assert s.loc["311111", "rd"] < 0.02       # pet food is not
    assert s.loc["336411", "life"] > s.loc["336111", "life"]   # aircraft outlast cars
    assert panel.life.dropna().between(1, 25).all()


def test_rd_prefix_parser():
    assert data._rd_prefixes("313–16") == ["313", "314", "315", "316"]
    assert data._rd_prefixes("336411–13") == ["336411", "336412", "336413"]
    assert data._rd_prefixes("3255, 3259") == ["3255", "3259"]
    assert data._rd_prefixes("other 333") == ["333"]


def test_bain_split_signs(panel):
    b = empirics.bain_table(panel).set_index("group")
    assert b.loc["Nondurable", "gap"] > 0
    assert b.loc["Durable final (long-lived)", "gap"] < 0
    assert np.isfinite(b.gap_se).all()
