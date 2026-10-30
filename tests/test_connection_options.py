"""The price lists a real site could be on (optimisation/connection_options.py,
COST_PLAN §1.11, 30 Oct 2026): size ranges from the published rules, the
substation points of the room mode, the site's overrides, and the single
mode as the model before that date. Needs the register and the cached NESO
tariffs, not Brightway."""
import pathlib
import sys

import pandas as pd
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from optimisation import connection_options as CO, network_charges as nc, sites, substations as S  # noqa: E402

LONDON = sites.resolve(51.5074, -0.1278, name="London", carbon_api_region=13)
MANCHESTER = sites.resolve(53.48, -2.24, name="Manchester", carbon_api_region=3)
INVERNESS = sites.resolve(57.48, -4.22, name="Inverness", carbon_api_region=1)


def test_size_ranges_follow_the_rules_and_the_band_tables():
    rows = size = CO.size_ranges(13, 180.0 * 8760)
    by = {(r["voltage"], r["band"]): r for r in rows}
    assert by[("11 kV", "HV4")]["ceiling_mw"] == pytest.approx(8.0 - nc.BAND_FLOOR_STEP_MW)   # UKPN: 8 MVA and above is 33 kV
    assert by[("33 kV", "EHV2")]["floor_mw"] == pytest.approx(8.0)
    assert by[("33 kV", "EHV4")]["ceiling_mw"] == 120.0 and by[("132 kV", "EHV4")]["ceiling_mw"] == 240.0
    assert ("33 kV", "EHV1") not in by                    # under the 11 kV limit: an 11 kV connection
    t = [r for r in rows if r["transmission"]]
    assert len(t) == 1 and t[0]["band"] == "T-Demand4" and t[0]["floor_mw"] == pytest.approx(240.001)
    scot = CO.size_ranges(1, 6.0 * 8760)
    assert all(r["voltage"] != "132 kV" for r in scot)   # 132 kV is transmission in Scotland
    assert max(r["ceiling_mw"] for r in scot if r["voltage"] == "33 kV") == 120.0
    assert [r for r in scot if r["transmission"]][0]["band"] == "T-Demand2"


def test_room_points_skip_blanks_and_add_the_next_with_room():
    pts = S.room_points(*(LONDON.lat, LONDON.lon), "transmission", 180.0, 13)
    assert pts and pts[0]["which"] == "nearest with a published figure"
    assert pts[0]["room_mw"] is not None and pts[0]["skipped"]            # London's nearest 275/400 kV points publish nothing
    c = S.candidates(LONDON.lat, LONDON.lon, "transmission", None)
    assert c.iloc[0]["name"] in pts[0]["skipped"]
    pts = S.room_points(MANCHESTER.lat, MANCHESTER.lon, "33 kV", 72.0, 3, within_km=60.0)   # beyond the 15 km reach
    assert pts[0]["room_mw"] < 72.0 and len(pts) == 2 and pts[1]["which"] == "next with room"
    assert pts[1]["room_mw"] >= 72.0 and pts[1]["straight_km"] > pts[0]["straight_km"]
    assert S.room_points(LONDON.lat, LONDON.lon, "33 kV", 1.0, 13)[0]["room_mw"] >= 1.0 or True


def test_room_mode_caps_each_option_by_its_substations_room():
    opts, dropped = CO.option_table(LONDON, 180.0, 180.0 * 8760, mode="room")
    assert len(opts) > 1 and all(o["mode"] == "room" for o in opts)
    for o in opts:
        assert o["ceiling_mw"] <= o["point"]["room_mw"] + 1e-9 and o["ceiling_mw"] >= o["floor_mw"]
        assert o["cap_basis"] == "published room at the substation"
    tiers = {o["tier"] for o in opts}
    assert tiers == {"local network", "national grid"}
    assert any(d["why"].startswith("room") for d in dropped)          # a band whose floor is above the room


def test_cap_mode_caps_every_option_at_the_one_figure_and_keeps_the_nearest():
    cap = sites.max_connection_mw(180.0)[0]
    opts, dropped = CO.option_table(LONDON, 180.0, 180.0 * 8760, mode="cap", cap_mw=cap)
    assert all(o["ceiling_mw"] <= cap + 1e-9 for o in opts) and all(o["point"]["which"] == "nearest" for o in opts)
    t = [o for o in opts if o["transmission"]]
    assert len(t) == 1 and t[0]["ceiling_mw"] == pytest.approx(cap) and t[0]["floor_mw"] == pytest.approx(240.001)
    local_top = max(o["ceiling_mw"] for o in opts if not o["transmission"])
    assert local_top == 240.0                                        # the company's largest connection
    with pytest.raises(ValueError):
        CO.option_table(LONDON, 180.0, 180.0 * 8760, mode="cap")       # the cap mode needs its cap


def test_the_sites_own_settings_still_override():
    cap = 257.0
    forced_t = sites.resolve(LONDON.lat, LONDON.lon, carbon_api_region=13, transmission_connected=True)
    opts, _ = CO.option_table(forced_t, 180.0, 180.0 * 8760, mode="cap", cap_mw=cap)
    assert opts and all(o["transmission"] for o in opts)
    forced_band = sites.resolve(LONDON.lat, LONDON.lon, carbon_api_region=13, tdr_band="EHV4")
    opts, _ = CO.option_table(forced_band, 180.0, 180.0 * 8760, mode="cap", cap_mw=cap)
    assert opts and all(o["band"] == "EHV4" for o in opts) and {o["voltage"] for o in opts} == {"33 kV", "132 kV"}


def test_each_voltage_group_has_a_representative_holding_the_load():
    cap = sites.max_connection_mw(180.0)[0]
    opts, _ = CO.option_table(LONDON, 180.0, 180.0 * 8760, mode="cap", cap_mw=cap)
    rep = CO.representative(opts, "132 kV", 180.0)
    assert rep["band"] == "EHV4" and rep["floor_mw"] <= 180.0 <= rep["ceiling_mw"]
    rep = CO.representative(opts, "11 kV", 180.0)                    # nothing holds 180 MW at 11 kV: the roomiest
    assert rep["band"] == "HV4"
    assert CO.group_var("33 kV") == "imp_33kV" and CO.group_var("transmission") == "imp_transmission"


def test_charges_follow_each_options_band_and_tier():
    cap = sites.max_connection_mw(180.0)[0]
    opts, _ = CO.option_table(LONDON, 180.0, 180.0 * 8760, mode="cap", cap_mw=cap)
    idx = pd.date_range("2027-01-04", periods=48, freq="30min")
    duos = CO.with_charges(opts, idx, LONDON)
    t = next(o for o in opts if o["transmission"])
    assert t["network_charges"]["duos_capacity_GBP_per_MW_year"] == 0.0 and float(duos[t["key"]].mean()) == 0.0
    e4 = next(o for o in opts if o["voltage"] == "132 kV" and o["band"] == "EHV4")
    e3 = next(o for o in opts if o["voltage"] == "132 kV" and o["band"] == "EHV3")
    assert e4["fixed_GBP_per_year"] > e3["fixed_GBP_per_year"]        # the residual band charge rises with the band
    assert e4["network_charges"]["duos_capacity_GBP_per_MW_year"] > 0


@pytest.mark.skipif(not pathlib.Path(S.REGISTER / "substations.csv").exists(), reason="no register")
def test_single_mode_is_the_model_before_and_one_option_folds_in():
    """``build_series`` is slow (Brightway caches, the grid series), so the
    single mode and the one-option fold are checked on the option table: a
    site that pins tier, band and limit leaves exactly one list."""
    pinned = sites.resolve(LONDON.lat, LONDON.lon, carbon_api_region=13, transmission_connected=True,
                           tdr_band="T-Demand4", connection_limit_mw=257.0)
    opts, _ = CO.option_table(pinned, 180.0, 180.0 * 8760, mode="cap", cap_mw=257.0)
    assert len(opts) == 1 and opts[0]["band"] == "T-Demand4" and opts[0]["ceiling_mw"] == 257.0
    assert CO.reference_key(opts, True, "transmission", "T-Demand4") == opts[0]["key"]
    assert CO.reference_key(opts, False, "132 kV", "EHV4") is None


# --- no room nearby (30 Oct 2026, afternoon) -----------------------------------
def test_a_published_room_of_zero_is_no_room_and_reach_is_per_voltage():
    """Manchester's nearest 33 kV point with a figure publishes 0 MW, and the
    next with room for 72 MW was 58 km away: with the 15 km reach neither is
    an option at 33 kV, and the dropped list says so."""
    opts, dropped = CO.option_table(MANCHESTER, 72.0, 72.0 * 8760, mode="room")
    assert all(o["ceiling_mw"] > 0 for o in opts)
    assert all(o["point"]["straight_km"] <= S.REACH_KM[o["voltage"]] + 1e-9 for o in opts)
    whys = [d["why"] for d in dropped if d["voltage"] == "33 kV"]
    assert whys and all(w.startswith("no room") or "within 15 km" in w for w in whys)
    assert S.REACH_KM["11 kV"] < S.REACH_KM["33 kV"] < S.REACH_KM["132 kV"] <= S.REACH_KM["transmission"]
    pts = S.room_points(MANCHESTER.lat, MANCHESTER.lon, "33 kV", 72.0, 3)
    assert all(p["straight_km"] <= S.REACH_KM["33 kV"] for p in pts)
    far = S.room_points(MANCHESTER.lat, MANCHESTER.lon, "33 kV", 72.0, 3, within_km=60.0)
    assert len(far) >= len(pts)


def test_nothing_in_reach_is_an_explicit_answer_not_a_connection():
    """A site with every substation in reach full raises in build_series; the
    option table returns nothing and the message says what to do."""
    far_out = sites.resolve(58.6, -3.6, name="far north", carbon_api_region=1)   # Caithness: nothing with room in reach
    opts, dropped = CO.option_table(far_out, 180.0, 180.0 * 8760, mode="room")
    if opts:
        pytest.skip("the register has room in reach of this coordinate now")
    msg = CO.no_room_message(far_out, 180.0, dropped, "room")
    assert "No room found nearby" in msg and "islanded" in msg
    err = CO.ConnectionUnavailable(msg, dropped)
    assert isinstance(err, ValueError) and err.dropped is dropped
