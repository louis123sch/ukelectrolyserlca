"""The site's connection point (substations.py), its cable route in
connection_cost, and the site-specific EHV charges (ehv_charges.py) —
COST_PLAN §1.9 parts B, C and D, wired in on 29 Oct 2026."""
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from optimisation import connection_cost as cc, duos_areas as D, ehv_charges as E, network_charges as nc, substations as S  # noqa: E402

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


# --- the voltage from the area's own substation capacities (29 Oct 2026) ------
MANCHESTER, READING, NORWICH, HIGHLAND = (53.48, -2.24), (51.45, -0.97), (52.63, 1.30), (57.48, -4.22)


def test_a_33kv_site_with_no_room_in_reach_connects_at_132kv():
    """103 MW (60 MW IT x 1.2 x 1.43) in Manchester: ENWL's rule says 33 kV, but
    the largest bulk-supply-point headroom in reach is 75 MW (58 of 59 publish)."""
    v, why = S.voltage_with_room(*MANCHESTER, "33 kV", 102.9, region=3)
    assert v == "132 kV" and "stepped up from 33 kV" in why
    assert nc.connection_voltage(102.9, 3, False) == "33 kV"                  # the rule alone
    assert nc.connection_voltage(102.9, 3, False, site=MANCHESTER) == "132 kV"
    assert S.voltage_with_room(*READING, "33 kV", 102.9, region=12)[0] == "132 kV"


def test_a_site_with_room_keeps_the_rules_voltage():
    v, why = S.voltage_with_room(*MANCHESTER, "33 kV", 51.4, region=3)
    assert v == "33 kV" and "have room for 51 MW" in why


def test_the_rule_is_the_floor_not_overruled_by_a_primary_with_room():
    assert S.voltage_with_room(*MANCHESTER, "33 kV", 5.0, region=3)[0] == "33 kV"


def test_the_half_published_threshold_and_what_the_capacity_layer_changed():
    """Until 30 Oct 2026 London (2 of 117 bulk supply points publishing) and
    Norwich (3 of 31) kept the rule for want of data. With the companies'
    standard heatmaps in, London's bulk points publish and three have room for
    103 MW, so it keeps 33 kV *with room*; Norwich's all publish and none has
    room, so it steps up to 132 kV. The threshold itself is checked wherever an
    area is still under it."""
    v, why = S.voltage_with_room(*LONDON, "33 kV", 102.9, region=13)
    assert v == "33 kV" and "have room for 103 MW" in why
    v, why = S.voltage_with_room(*NORWICH, "33 kV", 102.9, region=10)
    assert v == "132 kV" and "stepped up from 33 kV" in why
    for lat, lon, region in ((50.72, -3.53, 11), (51.4816, -3.1791, 7), (52.489, -1.898, 8)):
        c = S.candidates(lat, lon, "33 kV", region)
        share = c.demand_headroom_mw.notna().mean()
        v, why = S.voltage_with_room(lat, lon, "33 kV", 102.9, region)
        if share < S.MIN_PUBLISHED_SHARE:
            assert v == "33 kV" and "under the 50%" in why
        else:
            assert "under the 50%" not in why


def test_scotland_tops_out_at_33kv_and_reaches_the_grid_supply_point():
    v, why = S.voltage_with_room(*HIGHLAND, "33 kV", 102.9, region=1)
    assert v == "33 kV"
    p = S.connection_point(*HIGHLAND, "33 kV", 102.9, region=1)
    assert p["found"] and p["level"] == "gsp"
    # since 30 Oct 2026 SSEN's grid supply points carry a derived N-1 figure (Headroom Dashboard)
    assert p["headroom_status"] in ("room", "shortfall") and "N-1 nameplate" in p["headroom_basis"]
    assert S.levels_for("33 kV", 1) == ("bulk", "gsp") and S.levels_for("33 kV", 3) == ("bulk",)


def test_the_band_family_follows_the_site_voltage():
    """11 kV rule, but no primary in reach has room -> 33 kV, so EHV not HV bands."""
    import pandas as pd
    c = S.candidates(*MANCHESTER, "11 kV", region=3)
    known = c.dropna(subset=["demand_headroom_mw"])
    mw = float(known.demand_headroom_mw.max()) + 0.5          # just over the largest primary's room
    if mw > 15.0 or len(known) / len(c) < S.MIN_PUBLISHED_SHARE:
        pytest.skip("register changed: no 11 kV size between the largest primary's room and ES216's 15 MVA")
    assert nc.connection_voltage(mw, 3, False) == "11 kV"
    band, note = nc.tdr_band_for(mw, mw * 8760, region=3, transmission_connected=False, site=MANCHESTER)
    assert band.startswith("EHV") and "stepped up from 11 kV" in note
    assert nc.tdr_band_for(mw, mw * 8760, region=3, transmission_connected=False)[0] == "HV4"


# --- register corrections from the both-ways run (29 Oct 2026) ------------------
def test_transmission_layer_holds_no_generator_or_interconnector_sites():
    t = S.substations().query("level_std == 'transmission'")
    assert not t.name.str.contains("Wind Farm|Converter|Solar|Power Station|BESS", case=False, na=False).any()
    assert t.name.str.contains("Washway Farm", na=False).any()       # a real 275 kV substation named after a farm
    p = S.connection_point(50.82, -0.137, "transmission", 257.0, region=14)
    assert p["substation"] == "Bolney Substation"                     # not Rampion's onshore substation


def test_ukpn_132_11kv_grid_sites_are_not_33kv_points():
    u = S.substations().query("company == 'UKPN'")
    g = u[u.level == "Grid Substation 132/11kV"]
    assert len(g) and (g.level_std == "gsp").all()
    assert (u[u.level == "132kV Switching Station"].level_std == "gsp").all()
    assert (u[u.level == "Grid Substation"].level_std == "bulk").all()
    # every 132/11 kV grid site's 11 kV board is also a primary (a handful of
    # boards are merged with a primary of the same name by the capacity layer)
    boards = u[(u.level_std == "primary") & u.source.str.contains("132/11", na=False)]
    assert len(set(boards.name) & set(g.name)) >= 0.95 * len(g)
    for v in ("33 kV",):
        c = S.candidates(51.5074, -0.1278, v, region=13)
        assert not c.name.str.contains(r"\b11KV$", na=False).any()


def test_the_connection_ceiling_is_one_over_the_fes_load_factor():
    from optimisation import sites
    assert sites.CONNECTION_HEADROOM_ASSUMED == pytest.approx(1 / 0.70)
    mw, note = sites.max_connection_mw(100.0)
    assert mw == pytest.approx(142.857, abs=1e-3) and "FES 70 %" in note
    assert "set by the caller" in sites.max_connection_mw(100.0, 1.5)[1]


def _named_node(region=9, vkv=33.0):
    """A 33 kV price node matched by name to its substation, in the East Midlands."""
    n = S.price_nodes()
    n = n[(n.kind == "network") & n.how.isin(["name", "group"]) & (n.voltage_kv == vkv) & (n.region == region)]
    for r in n.itertuples():
        if S.price_node_at(r.lat, r.lon, region, vkv) is not None:
            return r
    pytest.skip("no named node in the register")


def test_site_specific_charge_is_node_price_plus_area_addon():
    """Since 30 Oct 2026 a site takes a node's price only where the schedule's
    node was matched by name to the substation it connects to; Maxwell House's
    nearest bulk supply point has no such node, so it takes the area figure."""
    m = E.site_charges(*MAXWELL_HOUSE, 9, "33 kV", "EHV4")
    assert m["how"] == "area median" and "30 Oct 2026" in m["note"]
    r = _named_node()
    s = E.site_charges(r.lat, r.lon, 9, "33 kV", "EHV4")
    assert s["how"] == "site-specific" and s["node"]["node_id"] == r.node_id
    assert s["node"]["local_GBP_per_kVA"] == pytest.approx(r.local_GBP_per_kVA)
    a, b, _ = E.addon(9, 33.0, "central")
    assert s["capacity_p_per_kva_day"] == pytest.approx(max(0.0, r.local_GBP_per_kVA * 100 / 365 + a))
    assert s["super_red_p_per_kwh"] == pytest.approx(max(0.0, r.remote_GBP_per_kVA / s["super_red_hours"] * 100 + b))
    # the central figure sits inside the area's quartile range
    lo = E.site_charges(r.lat, r.lon, 9, "33 kV", "EHV4", "low")["capacity_p_per_kva_day"]
    hi = E.site_charges(r.lat, r.lon, 9, "33 kV", "EHV4", "high")["capacity_p_per_kva_day"]
    assert lo <= s["capacity_p_per_kva_day"] <= hi


def test_ssen_areas_keep_the_listed_site_median():
    s = E.site_charges(57.48, -4.22, 1, "33 kV", "EHV4")
    assert s["how"] == "area median" and "outside the EDCM" in s["note"]
    assert s["capacity_GBP_per_MW_year"] == pytest.approx(D.EHV_BANDS[1][4].capacity_p_per_kva_day[1] / 100 * 365 * 1000)


def test_duos_charges_switch_to_site_specific_when_a_site_is_given():
    import pandas as pd
    idx = pd.date_range("2027-01-04", periods=48, freq="30min")
    r = _named_node()
    area = D.charges(idx, 9, "EHV4")
    site = D.charges(idx, 9, "EHV4", site=(r.lat, r.lon), connection_voltage="33 kV")
    assert "site-specific" in site["tariff"] and "site-specific" not in area["tariff"]
    assert site["fixed_GBP_per_year"] == area["fixed_GBP_per_year"]          # the fixed charge keeps the band quartiles
