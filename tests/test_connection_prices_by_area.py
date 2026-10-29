"""Connection build prices by DNO area (connection_cost.py, COST_PLAN §1.9 E,
29 Oct 2026): each area on its own company's statement, POA rows on the
publishers' median, NGED's low substation rows kept and flagged."""
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from optimisation import connection_cost as cc  # noqa: E402


def test_every_area_has_a_price_list_and_every_row_is_filled():
    for region in range(1, 15):
        p = cc.prices(region)
        assert p["list"] in cc.PRICE_LISTS
        for v in ("132 kV", "33 kV"):
            assert p["substation"][v]["low"] <= p["substation"][v]["central"] <= p["substation"][v]["high"]
        for v in cc.VOLTAGES:
            assert p["cable_first"][v]["low"] > 0 and p["cable_per_m"][v]["low"] > 0


@pytest.mark.parametrize("region, voltage, lo, hi", [
    (12, "132 kV", 11_495_717, 13_043_778),      # SSEN SEPD v1.47 p.152, outdoor double
    (12, "33 kV", 2_616_172, 2_833_817),
    (1, "33 kV", 1_939_300, 2_852_850),          # SHEPD v1.46 p.150, indoor double
    (10, "132 kV", 8_000_000, 9_000_000),        # UKPN Aug 2026 p.167, EPN column
    (14, "132 kV", 8_100_000, 9_200_000),        # SPN column
    (10, "33 kV", 5_200_000, 5_700_000),
    (3, "132 kV", 6_961_000, 11_270_000),        # ENWL v5.9 p.161, outdoor double
    (3, "33 kV", 4_039_000, 4_767_000),
    (7, "132 kV", 1_700_792, 2_790_945),         # NGED June 2026 p.168 (kept, flagged)
])
def test_substation_rows_are_the_companys_own(region, voltage, lo, hi):
    p = cc.prices(region)
    assert p["substation"][voltage] == {"low": lo, "central": (lo + hi) / 2, "high": hi}
    assert f"substation {voltage}" not in p["stand_in"]


@pytest.mark.parametrize("region, voltage, first_lo, first_hi, m_lo, m_hi", [
    (12, "132 kV", 57_334, 194_474, 1_405, 32_316),   # SEPD p.150
    (12, "33 kV", 13_096, 47_697, 437, 1_054),
    (1, "33 kV", 3_613, 9_544, 141, 439),             # SHEPD p.147
    (13, "132 kV", 22_000, 50_000, 600, 900),         # UKPN LPN p.163
    (10, "132 kV", 20_000, 50_000, 500, 900),         # EPN
    (14, "11 kV", 3_100, 14_900, 300, 800),           # SPN p.161
    (3, "132 kV", 100_000, 135_000, 2_300, 3_500),    # ENWL p.157
    (3, "33 kV", 74_400, 91_400, 2_300, 3_200),
    (2, "33 kV", 10_912, 24_119, 557, 722),           # SPEN p.151
    (6, "11 kV", 5_440, 15_337, 145, 475),
    (4, "11 kV", 7_299, 14_098, 146, 292),            # Northern Powergrid Northeast
    (5, "11 kV", 7_099, 12_721, 141, 262),            # Yorkshire
])
def test_cable_rows_are_the_companys_own(region, voltage, first_lo, first_hi, m_lo, m_hi):
    p = cc.prices(region)
    assert (p["cable_first"][voltage]["low"], p["cable_first"][voltage]["high"]) == (first_lo, first_hi)
    assert (p["cable_per_m"][voltage]["low"], p["cable_per_m"][voltage]["high"]) == (m_lo, m_hi)


def test_poa_rows_take_the_publishers_median_and_say_so():
    # 132 kV substation: NGED 1.70, ENWL 6.96, EPN 8.0, SPN 8.1, SEPD 11.50 -> 8.0 m low; 9.2 m high
    assert cc.median_row("substation", "132 kV") == (8_000_000, 9_200_000)
    for region in (2, 4, 5, 6, 13):                     # SPEN x2, Northern Powergrid x2, London
        p = cc.prices(region)
        assert p["substation"]["132 kV"]["low"] == 8_000_000 and "substation 132 kV" in p["stand_in"]
    assert "substation 132 kV" in cc.prices(1)["stand_in"]        # SHEPD: 132 kV is N/A
    assert cc.prices(4)["stand_in"] == ["substation 132 kV", "substation 33 kV", "cable_first 132 kV",
                                        "cable_per_m 132 kV", "cable_first 33 kV", "cable_per_m 33 kV"]
    assert cc.prices(3)["stand_in"] == [] and cc.prices(12)["stand_in"] == []


def test_ngeds_areas_keep_their_own_rows_and_are_flagged():
    for region in (7, 8, 9, 11):
        p = cc.prices(region)
        assert p["list"] == "NGED" and cc.NGED_SUBSTATION_FLAG in p["flags"]
        assert p["substation"]["33 kV"]["low"] == 1_359_279
    assert cc.NGED_SUBSTATION_FLAG not in cc.prices(3)["flags"]


def test_capital_is_priced_on_the_areas_list():
    enwl = cc.capital("33 kV", "central", route_km=2.0, region=3)
    assert enwl["per_MW_GBP"] == pytest.approx((4_039_000 + 4_767_000) / 2 / 29.0)
    assert enwl["fixed_GBP"] == pytest.approx(2 * ((74_400 + 91_400) / 2 + 1_970 * (2_300 + 3_200) / 2))
    assert enwl["price_list"] == "ENWL" and enwl["stand_in"] == []
    london = cc.capital("132 kV", "low", route_km=2.0, region=13)
    assert london["per_MW_GBP"] == pytest.approx(8_000_000 / 60.0)        # the median stand-in
    assert london["fixed_GBP"] == pytest.approx(2 * (22_000 + 1_960 * 600))   # London's own cable
    assert london["stand_in"] == ["substation 132 kV"]
    eleven = cc.capital("11 kV", "high", route_km=2.0, region=5)
    assert eleven["fixed_GBP"] == pytest.approx(2 * (12_721 + 1_980 * 262) + 76_873)


def test_connection_costs_carries_the_list_and_the_stand_ins():
    k = cc.connection_costs(4, False, connection_voltage="33 kV", route_km=3.0)
    assert k["price_list"] == "NPG-NE" and "substation 33 kV" in k["stand_in"]
    lo, hi = cc.median_row("substation", "33 kV")        # six lists: 3.33-3.81 m
    assert (lo, hi) == (3_327_586.0, 3_809_925.0)
    assert k["per_MW_year_GBP"] == pytest.approx((lo + hi) / 2 / 29.0 * k["annual_factor"])


def test_the_default_region_is_still_nged_south_wales():
    assert cc.capital("132 kV", "central")["price_list"] == "NGED"
