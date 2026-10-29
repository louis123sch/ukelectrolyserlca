"""The site's connection point (substations.py), its cable route in
connection_cost, and the site-specific EHV charges (ehv_charges.py) —
COST_PLAN §1.9 parts B, C and D, wired in on 29 Oct 2026."""
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from optimisation import connection_cost as cc, duos_areas as D, ehv_charges as E, substations as S  # noqa: E402

LONDON = (51.505, -0.02)
MAXWELL_HOUSE = (52.002384, -0.737258)      # NGED East Midlands, a listed data centre


def test_levels_are_normalised_across_companies():
    assert S.level_of("PRY") == S.level_of("Primary Substation") == S.level_of("PRIMARY SITE") == "primary"
    assert S.level_of("Bulk Supply Point") == S.level_of("Grid Substation") == "bulk"
    assert S.level_of("Super Grid Substation") == "gsp" and S.level_of("EHV PM SITE") is None


def test_each_voltage_reaches_the_right_substations():
    for v in ("11 kV", "33 kV", "132 kV", "transmission"):
        c = S.candidates(*LONDON, v, region=13 if v != "transmission" else None)
        assert len(c) and set(c.level_std) <= set(S.VOLTAGE_LEVELS[v])
        assert c.straight_km.is_monotonic_increasing


def test_connection_point_prices_the_real_route_not_two_km():
    p = S.connection_point(*LONDON, "132 kV", 225.0, region=13)
    assert p["found"] and p["route_km"] == pytest.approx(p["straight_km"] * S.ROUTE_FACTOR_ASSUMED)
    assert p["straight_km"] < 2.0
    with_route = cc.connection_costs(13, False, connection_voltage="132 kV", route_km=p["route_km"])
    default = cc.connection_costs(13, False, connection_voltage="132 kV")
    assert with_route["fixed_per_year_GBP"] < default["fixed_per_year_GBP"]
    assert with_route["per_MW_year_GBP"] == default["per_MW_year_GBP"]       # the substation does not move


def test_a_shortfall_is_flagged_and_both_routes_reported():
    """Manchester, 225 MW at 33 kV: no ENWL bulk supply point has that headroom."""
    p = S.connection_point(53.48, -2.24, "33 kV", 225.0, region=3)
    assert p["headroom_status"] == "shortfall" and "Access SCR" in p["note"]
    assert p["substation"] == p["nearest"]                                   # default: upgrade at the nearest
    assert p["next_with_room"] is None                                       # nothing in reach takes 225 MW
    small = S.connection_point(53.48, -2.24, "33 kV", 1.0, region=3)         # the nearest has 0 MW headroom
    assert small["headroom_status"] == "shortfall" and small["next_with_room"] is not None
    assert small["next_with_room_straight_km"] > small["nearest_straight_km"]


def test_shortfall_route_next_moves_to_the_substation_with_room():
    p = S.connection_point(53.48, -2.24, "33 kV", 1.0, region=3, shortfall_route="next")
    assert p["substation"] == p["next_with_room"] and p["route_km"] > p["nearest_straight_km"]


def test_site_specific_charge_is_node_price_plus_area_addon():
    s = E.site_charges(*MAXWELL_HOUSE, 9, "33 kV", "EHV4")
    assert s["how"] == "site-specific" and s["node"]["local_GBP_per_kVA"] == 0.0
    a, b, _ = E.addon(9, 33.0, "central")
    assert s["capacity_p_per_kva_day"] == pytest.approx(a)                   # local 0 -> the add-on alone
    assert s["super_red_p_per_kwh"] == pytest.approx(b)
    # published 1.33 p/kVA/day (NGED East Midlands Annex 2) within the area's range
    lo = E.site_charges(*MAXWELL_HOUSE, 9, "33 kV", "EHV4", "low")["capacity_p_per_kva_day"]
    hi = E.site_charges(*MAXWELL_HOUSE, 9, "33 kV", "EHV4", "high")["capacity_p_per_kva_day"]
    assert lo <= 1.33 <= hi


def test_ssen_areas_keep_the_listed_site_median():
    s = E.site_charges(57.48, -4.22, 1, "33 kV", "EHV4")
    assert s["how"] == "area median" and "outside the EDCM" in s["note"]
    assert s["capacity_GBP_per_MW_year"] == pytest.approx(D.EHV_BANDS[1][4].capacity_p_per_kva_day[1] / 100 * 365 * 1000)


def test_duos_charges_switch_to_site_specific_when_a_site_is_given():
    import pandas as pd
    idx = pd.date_range("2027-01-04", periods=48, freq="30min")
    area = D.charges(idx, 9, "EHV4")
    site = D.charges(idx, 9, "EHV4", site=MAXWELL_HOUSE, connection_voltage="33 kV")
    assert "site-specific" in site["tariff"] and "site-specific" not in area["tariff"]
    assert site["fixed_GBP_per_year"] == area["fixed_GBP_per_year"]          # the fixed charge keeps the band quartiles
