"""The register's capacity layer (scripts/register_capacity.py, COST_PLAN §1.10
R2-R4) and the fetch script's source table (R1): helpers and the overlay on a
toy register, without the portals or the built files."""
import importlib.util
import pathlib
import sys

import numpy as np
import pandas as pd
import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from scripts import register_capacity as C  # noqa: E402


def _load(name):
    import importlib
    return importlib.import_module(f"scripts.{name}")


# --- R1: the source table -------------------------------------------------------
def test_every_source_has_a_unique_key_a_known_portal_and_a_plan_step():
    F = _load("fetch_register_sources")
    keys = [s.key for s in F.SOURCES]
    assert len(keys) == len(set(keys))
    for s in F.SOURCES:
        assert s.company in F.ODS or s.company in F.CKAN
        assert s.kind in ("ods", "ods_query", "ckan")
        assert (s.kind == "ckan") == (s.resource is not None)
        assert s.used_for
    assert {s.company for s in F.SOURCES} == {"UKPN", "NPG", "ENWL", "SPEN", "NGED", "SSEN"}


def test_keys_are_read_from_the_environment_never_written(monkeypatch):
    F = _load("fetch_register_sources")
    monkeypatch.setenv("UKPN_API_KEY", "test-only")
    assert F.load_keys()["UKPN_API_KEY"] == "test-only"
    src = (ROOT / "scripts" / "fetch_register_sources.py").read_text(encoding="utf-8")
    assert "Apikey test" not in src and "API_KEY=" not in src.replace("API_KEY=...", "")


# --- helpers ----------------------------------------------------------------------
def test_os_grid_reference_to_coordinates_lands_on_the_right_square():
    """SZ 04270 95141 is near Bournemouth (Alderney primary, SSEN's report)."""
    lat, lon = C.gridref_to_latlon("SZ 04270 95141")
    assert 50.70 < lat < 50.80 and -1.95 < lon < -1.85
    lat, lon = C.gridref_to_latlon("NH 33843 03575")            # Fort Augustus area
    assert 57.0 < lat < 57.2 and -4.8 < lon < -4.6
    assert all(v != v for v in C.gridref_to_latlon("not a reference"))


@pytest.mark.parametrize("a, b", [("Botley Wood GSP", "Botley Wood"), ("Indian Queens  S.G.P.", "INDIAN QUEENS"),
                                  ("Bramley (Ames-That)", "Bramley"), ("Sandford 132Kv Sgp", "Sandford Substation"),
                                  ("Templeborough 275/33kV", "Templeborough")])
def test_grid_supply_point_names_join_across_sources(a, b):
    assert C.gsp_key(a) == C.gsp_key(b)


@pytest.mark.parametrize("name, level", [("Ipswich Grid 33kV", "Grid Substation"), ("Ipswich Grid 11kV", "Grid Substation 132/11kV"),
                                         ("STOWMARKET GRID 33", "Grid Substation"), ("Coldharbour Farm 11kV", None),
                                         ("NEASDEN BSP", "Grid Substation")])
def test_ukpn_table_rows_take_a_level_from_their_names_only_when_the_name_says_grid(name, level):
    assert C.ukpn_level_from_name(name) == level


def test_opendatasoft_geo_points_parse_as_lat_lon():
    lat, lon = C.latlon(pd.Series(["51.754587, -0.337665", None, "junk"]))
    assert lat.iloc[0] == pytest.approx(51.754587) and lon.iloc[0] == pytest.approx(-0.337665)
    assert lat.isna().tolist() == [False, True, True]


# --- the overlay --------------------------------------------------------------------
def _sites():
    return pd.DataFrame({
        "region": [13, 13, 13, 13], "company": "UKPN",
        "name": ["ALPHA GRID 132/33kV", "ALPHA GRID 132/33kV", "BETA PRIMARY 11kV", "GAMMA 33KV"],
        "level": ["Grid Substation", "Primary Substation", "Primary Substation", "Grid Substation"],
        "voltage_kv": [132, 11, 11, 33], "lat": [51.50, 51.50, 51.60, 51.70], "lon": [-0.10, -0.10, -0.20, -0.30],
        "firm_mva": [np.nan, np.nan, 20.0, np.nan], "demand_headroom_mw": [np.nan, np.nan, 4.0, np.nan],
        "source": "site list", "site_id": ["F1", "F1", "H2", "D3"],
    })


def _cap():
    return pd.DataFrame({
        "company": "UKPN", "region": 13,
        "site_id": [None, "F1", None, None],
        "name": ["Alpha Grid 33kV", "Alpha Grid", "Beta Primary 11kV", "Delta Primary 11kV"],
        "level": ["Grid Substation", "Grid Substation", "Primary", "Primary"],
        "lat": [np.nan, np.nan, 51.6001, 51.90], "lon": [np.nan, np.nan, -0.2001, -0.50],
        "firm_mva": [90.0, 95.0, 23.0, 30.0], "max_demand_mw": [50.0, 60.0, 16.0, 10.0],
        "demand_headroom_mw": [40.0, 35.0, 7.0, 20.0], "demand_contracted_mw": [np.nan, 5.0, np.nan, np.nan],
        "headroom_net_of_contracted_mw": np.nan, "constraint": ["Green", "Amber", "Green", "Green"],
        "headroom_basis": ["table 3a", "grid areas", "heatmap", "heatmap"],
        "headroom_as_of": ["2026-06-01", "2025-03-31", "2026-10-19", "2026-10-19"],
        "source_dataset": ["t3a", "areas", "heat", "heat"], "priority": [2, 3, 1, 1],
    })


def test_overlay_joins_by_id_then_name_then_distance_and_appends_the_rest():
    out, tally = C.overlay(_sites(), _cap())
    alpha = out[(out.name == "ALPHA GRID 132/33kV") & (out.level == "Grid Substation")].iloc[0]
    assert alpha.demand_headroom_mw == 40.0 and alpha.headroom_basis == "table 3a"      # the name match, priority 2
    assert alpha.demand_contracted_mw == 5.0 and alpha.overlay == "name"               # priority 3 only fills the gap
    beta = out[out.name == "BETA PRIMARY 11kV"].iloc[0]
    assert beta.demand_headroom_mw == 7.0 and beta.overlay == "name"
    delta = out[out.name == "Delta Primary 11kV"]
    assert len(delta) == 1 and delta.iloc[0].overlay == "appended" and delta.iloc[0].demand_headroom_mw == 20.0
    gamma = out[out.name == "GAMMA 33KV"].iloc[0]
    assert gamma.demand_headroom_mw != gamma.demand_headroom_mw                         # nothing matched: left blank
    assert tally["appended"] == 1 and tally["name"] >= 2


def test_overlay_matches_within_300_m_at_the_same_level_only():
    sites = _sites().iloc[[2]].assign(name="SOMETHING ELSE", site_id=None)              # Beta, renamed
    cap = _cap().iloc[[2]]                                                                 # 15 m away, a primary
    out, tally = C.overlay(sites, cap)
    assert out.iloc[0].demand_headroom_mw == 7.0 and out.iloc[0].overlay == "near"
    cap_far = cap.assign(lat=51.61)                                                        # 1.1 km away
    out, _ = C.overlay(sites, cap_far)
    assert len(out) == 2 and out.iloc[0].demand_headroom_mw != out.iloc[0].demand_headroom_mw
    cap_bulk = cap.assign(level="BSP")                                                     # same place, other level
    out, _ = C.overlay(sites, cap_bulk)
    assert out.iloc[0].overlay != "near"


def test_apply_is_idempotent_and_keeps_the_builders_figures_as_fallback(monkeypatch):
    sites = _sites()
    monkeypatch.setitem(C.READERS, "UKPN", lambda src: _cap())
    once, tally = C.apply(sites, pathlib.Path("."))
    twice, _ = C.apply(once, pathlib.Path("."))
    pd.testing.assert_frame_equal(once.reset_index(drop=True), twice.reset_index(drop=True))
    gamma = once[once.name == "GAMMA 33KV"].iloc[0]
    assert gamma.demand_headroom_mw != gamma.demand_headroom_mw and gamma.builder_headroom_mw != gamma.builder_headroom_mw
    beta = once[once.name == "BETA PRIMARY 11kV"].iloc[0]
    assert beta.builder_headroom_mw == 4.0 and beta.demand_headroom_mw == 7.0           # the builder's 4 kept aside
    assert int(tally.iloc[0]["with_headroom"]) == 4


def test_transmission_rows_take_the_nearest_grid_supply_point_record_within_3_km():
    tx = pd.DataFrame({"name": ["Big Substation", "Lonely Substation"], "lat": [52.0, 55.0], "lon": [-1.0, -3.0],
                       "level": "transmission"})
    gsps = pd.DataFrame({"company": ["SSEN"], "name": ["Big"], "lat": [52.01], "lon": [-1.0], "firm_mva": [300.0],
                         "max_demand_mw": [120.0], "demand_headroom_mw": [180.0], "accepted_mw": [np.nan],
                         "headroom_basis": ["limit minus peak"], "headroom_as_of": ["2026-04-02"], "source_dataset": ["technicallimits"]})
    out = C.transmission_capacity(tx, gsps)
    assert out.iloc[0].demand_headroom_mw == 180.0 and out.iloc[0].gsp_record == "SSEN: Big"
    assert out.iloc[1].demand_headroom_mw != out.iloc[1].demand_headroom_mw
