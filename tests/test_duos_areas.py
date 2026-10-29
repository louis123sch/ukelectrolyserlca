"""Local network charges and loss factors by licence area (``duos_areas``),
pinned to each area's 2026/27 schedule of charges. ``scripts/check_duos_areas.py``
compares every figure with the workbooks; the last test runs it when the
OneDrive sources folder is present (RUN_SLOW=1)."""
import os
import pathlib
import subprocess
import sys

import numpy as np
import pandas as pd
import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from optimisation import duos_areas as D, levies as lv, network_charges as nc, sites  # noqa: E402

YEAR = pd.date_range("2026-04-01", "2027-03-31 23:30", freq="30min")


def test_every_region_has_every_table():
    for r in range(1, 15):
        assert set(D.HV_ROWS[r]) == {1, 2, 3, 4}
        assert set(D.EHV_BANDS[r]) == {1, 2, 3, 4}
        assert r in D.HV_TIME_BANDS and r in D.SUPER_RED
        assert r in D.LLF or r in D.LLF_ASSUMED_REGIONS


def test_each_zone_names_its_own_area():
    for r, z in sites.CI_REGION_TO_TNUOS_ZONE.items():
        assert nc.region_for_zone(z) == r
        ch = nc.import_charges(YEAR[:48], zone_no=z, tdr_band="EHV4")
        assert ch["components"]["duos_area"] == D.AREA_NAMES[r]


def test_a_132kv_site_pays_ehv_charges_not_the_hv_row():
    """London Annex 2, band 4: median of 16 sites, 2.225 p/kVA/day and 63,517.91 p/day."""
    c = D.charges(YEAR, 13, "EHV4")
    assert c["capacity_GBP_per_MW_year"] == pytest.approx(2.225 / 100 * 365 * 1000)
    assert c["fixed_GBP_per_year"] == pytest.approx(63_517.91 / 100 * 365)
    assert "Designated EHV" in c["tariff"]


def test_an_11kv_site_pays_its_areas_hv_row_in_its_areas_red_band():
    """NGED South West Annex 1: HV Site Specific Band 4 red 7.242 p/kWh, 17:00-19:00."""
    idx = pd.DatetimeIndex(["2026-11-04 17:30", "2026-11-04 16:30", "2026-11-07 17:30"])
    c = D.charges(idx, 11, "HV4")                     # Wednesday red, Wednesday amber, Saturday amber
    assert list(c["duos_GBP_per_MWh"]) == pytest.approx([72.42, 3.02, 3.02])
    assert c["fixed_GBP_per_year"] == pytest.approx(1908.16 / 100 * 365)


def test_super_red_follows_each_area_and_its_christmas_exclusion():
    jan = pd.DatetimeIndex(["2027-01-06 16:30", "2027-01-06 17:30", "2027-01-06 19:15"])
    assert list(D.super_red_window(jan, 3)) == [True, True, False]      # North West 16-19
    assert list(D.super_red_window(jan, 7)) == [False, True, True]      # South Wales 17-19:30
    xmas = pd.DatetimeIndex(["2026-12-23 17:30", "2027-01-05 17:30"])
    assert list(D.super_red_window(xmas, 7)) == [False, True]
    assert list(D.super_red_window(xmas, 3)) == [True, True]
    summer = pd.DatetimeIndex(["2026-07-01 11:30"])                    # 12:30 BST
    assert D.super_red_window(summer, 13)[0] and not D.super_red_window(summer, 10)[0]


@pytest.mark.parametrize("region, when, period", [
    (2, "2027-01-06 17:00", 4), (2, "2027-01-06 21:00", 2), (2, "2027-01-06 03:00", 1),
    (1, "2027-01-06 17:00", 1), (1, "2027-01-06 21:00", 3), (1, "2027-01-06 03:00", 4),
    (4, "2026-11-04 17:00", 2), (4, "2026-12-02 17:00", 1), (4, "2026-12-02 18:45", 2),
    (5, "2027-01-06 19:30", 2), (3, "2027-01-06 21:00", 2), (3, "2026-07-01 12:00", 4),
    (13, "2026-07-01 12:00", 2), (13, "2027-03-03 12:00", 3),
])
def test_llf_periods_follow_each_areas_annex_5(region, when, period):
    assert D.llf_period(pd.DatetimeIndex([when]), region)[0] == period


def test_llfs_are_the_areas_own():
    s = lv.loss_series(pd.DatetimeIndex(["2027-01-06 17:00"]), "33 kV", 6)
    assert s.iloc[0] == pytest.approx(1.02 * (1 + 0.0021 + 0.011))    # Manweb 33kV period 4; zone 4 winter TLF
    s = lv.loss_series(pd.DatetimeIndex(["2027-01-06 17:00"]), "11 kV", 3)
    assert s.iloc[0] == pytest.approx(1.038 * (1 - 0.0032 + 0.011))   # ENWL 11kV period 1; zone 7 winter TLF


@pytest.mark.parametrize("region, when, voltage, llf", [
    (7, "2027-01-06 17:00", "33 kV", 1.037),      # South Wales "EHV connected", peak
    (8, "2027-01-06 19:30", "11 kV", 1.06),       # West Midlands HV network, winter
    (9, "2026-07-01 03:00", "132 kV", 1.006),     # East Midlands 132kV, night
    (11, "2026-07-01 22:45", "33 kV", 1.011),     # South West, night from 23:30 BST
])
def test_nged_llfs_are_their_own_published_workbooks(region, when, voltage, llf):
    s = lv.loss_series(pd.DatetimeIndex([when]), voltage, region)
    assert s.iloc[0] == pytest.approx(llf * lv.tlm_series(pd.DatetimeIndex([when]), region).iloc[0])
    assert not D.LLF_ASSUMED_REGIONS


@pytest.mark.skipif(not os.environ.get("RUN_SLOW"), reason="reads 14 workbooks; set RUN_SLOW=1")
def test_every_figure_matches_its_workbook():
    base = pathlib.Path.home() / "OneDrive - Imperial College London" / "DC optimiser" / "connection sources"
    if not base.exists():
        pytest.skip("sources folder not on this machine")
    r = subprocess.run([sys.executable, "-I", str(ROOT / "scripts" / "check_duos_areas.py"), str(base)],
                       capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stdout[-3000:]
