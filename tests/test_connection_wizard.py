"""The connection wizard's model side (4 Nov 2026): the substation list the
page shows, and a substation picked by the user as the one option — capped
at its published room, or at the size the user set, folded to one band so
the run is the single-price-list model. Needs the register, not Brightway."""
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from optimisation import connection_options as CO, sites, substations as S  # noqa: E402

LAT, LON = 51.5074, -0.1278
LOAD = 180.0


def _london(**kw):
    return sites.resolve(LAT, LON, name="London", carbon_api_region=13, tdr_band=None, **kw)


@pytest.fixture(scope="module")
def subs():
    return S.substation_list(LAT, LON, 13)


def test_the_list_holds_every_voltage_within_its_reach(subs):
    assert set(subs.voltage) <= set(S.VOLTAGE_LEVELS) and len(subs) > 50
    for v, g in subs.groupby("voltage"):
        assert (g.straight_km <= S.REACH_KM[v] + 1e-9).all() and g.straight_km.is_monotonic_increasing
    assert (subs.has_room <= subs.has_figure).all()                      # room implies a figure
    assert subs.loc[~subs.has_figure, "room_mw"].isna().all()
    assert (subs.route_km > subs.straight_km).all()


def test_a_picked_substation_with_room_is_the_one_option_capped_at_its_room(subs):
    pick = subs[(subs.voltage == "132 kV") & subs.has_room].iloc[0]
    site = _london(connection_substation=pick.substation, connection_substation_voltage="132 kV")
    opts, dropped = CO.option_table(site, LOAD, LOAD * 8760, mode="room")
    assert len(opts) == 1
    o = opts[0]
    assert o["voltage"] == "132 kV" and o["point"]["substation"] == pick.substation
    assert o["ceiling_mw"] == pytest.approx(min(pick.room_mw, o["ceiling_mw"])) and o["ceiling_mw"] <= pick.room_mw + 1e-9
    assert o["point"]["which"] == "picked by the user" and o["key"].endswith("| picked")
    assert all(d["why"].startswith("folded") for d in dropped)          # the other bands folded away, nothing lost


def test_a_size_of_the_users_own_ignores_the_room_and_says_so(subs):
    pick = subs[(subs.voltage == "132 kV") & subs.has_room].iloc[0]
    size = float(pick.room_mw) + 50.0
    site = _london(connection_substation=pick.substation, connection_substation_voltage="132 kV",
                   connection_limit_mw=size)
    opts, _ = CO.option_table(site, LOAD, LOAD * 8760, mode="cap", cap_mw=size)
    assert len(opts) == 1 and opts[0]["ceiling_mw"] == pytest.approx(size)
    assert "above its published room" in opts[0]["cap_basis"]
    assert opts[0]["point"]["headroom_status"] == "shortfall"


def test_a_full_or_unpublished_substation_gives_no_option_and_asks_for_a_size(subs):
    full = subs[~subs.has_room]
    if full.empty:
        pytest.skip("every substation in reach of London has room now")
    f = full.iloc[0]
    site = _london(connection_substation=f.substation, connection_substation_voltage=str(f.voltage))
    opts, dropped = CO.option_table(site, LOAD, LOAD * 8760, mode="room")
    assert not opts and dropped and all(d["why"].startswith("no room") for d in dropped)
    msg = CO.no_room_message(site, LOAD, dropped, "room")
    assert f.substation in msg and "Set your own connection size" in msg and "islanded" in msg


def test_an_unknown_name_is_an_explicit_answer():
    site = _london(connection_substation="NO SUCH SUBSTATION", connection_substation_voltage="33 kV")
    opts, dropped = CO.option_table(site, LOAD, LOAD * 8760, mode="room")
    assert not opts and all("no 33 kV substation named" in d["why"] for d in dropped)
    with pytest.raises(ValueError):
        CO.option_table(_london(connection_substation="X", connection_substation_voltage="400 kV"),
                        LOAD, LOAD * 8760, mode="room")


def test_the_site_carries_the_pin_through_resolve_and_the_job_request():
    site = _london(connection_substation="A", connection_substation_voltage="11 kV")
    assert site.connection_substation == "A" and site.connection_substation_voltage == "11 kV"
    assert _london().connection_substation is None


# --- the band choice at a picked substation (4 Nov 2026, afternoon) --------------
def test_band_optimised_keeps_every_band_at_the_picked_voltage(subs):
    pick = subs[(subs.voltage == "132 kV") & subs.has_room].iloc[0]
    folded = _london(connection_substation=pick.substation, connection_substation_voltage="132 kV")
    opts_f, _ = CO.option_table(folded, LOAD, LOAD * 8760, mode="room")
    open_ = _london(connection_substation=pick.substation, connection_substation_voltage="132 kV",
                    connection_band_optimised=True)
    opts_o, dropped = CO.option_table(open_, LOAD, LOAD * 8760, mode="room")
    assert len(opts_f) == 1 and len(opts_o) > 1 and not any(d["why"].startswith("folded") for d in dropped)
    assert {o["point"]["substation"] for o in opts_o} == {pick.substation} and {o["voltage"] for o in opts_o} == {"132 kV"}
    assert opts_f[0]["band"] in {o["band"] for o in opts_o}                 # the folded band is one of them
    tops = sorted(o["ceiling_mw"] for o in opts_o)
    assert tops[-1] <= pick.room_mw + 1e-9 and all(o["floor_mw"] < o["ceiling_mw"] for o in opts_o)
    assert _london().connection_band_optimised is False and open_.connection_band_optimised is True
