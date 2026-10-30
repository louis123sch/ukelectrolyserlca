"""The register read the other way round (optimisation/availability.py, COST_PLAN
§1.10 R5), the strict price-node rule and the new register columns
(substations.py, 30 Oct 2026). Needs the built register."""
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from optimisation import availability as A, network_charges as nc, substations as S  # noqa: E402

REG = S.REGISTER
pytestmark = pytest.mark.skipif(not (REG / "substations.csv").exists(), reason="register not built")


def test_every_capacity_row_says_what_it_is_and_how_old():
    s = S.substations()
    has = s[s.demand_headroom_mw.notna() & (s.level_std != "transmission")]
    assert has.headroom_basis.notna().all() and has.headroom_as_of.notna().all() and has.source_dataset.notna().all()
    assert has.headroom_as_of.astype(str).str.match(r"20\d\d-\d\d").all()
    # the standard heatmaps are in: every company publishes on more than one basis/dataset now
    assert s[s.company == "UKPN"].source_dataset.dropna().str.contains("ukpn-capacity-heatmap").any()
    assert s[s.company == "NGED"].source_dataset.dropna().str.contains("network-opportunity-map").any()
    assert s[s.company == "SPEN"].source_dataset.dropna().str.contains("distribution-capacity-heatmaps").any()


def test_london_grid_sites_now_publish_capacity_and_primaries_everywhere_mostly_do():
    import pandas as pd
    cov = pd.read_csv(REG / "capacity_coverage.csv")
    prim = cov[cov.level_std == "primary"].set_index("region").share
    assert (prim >= 0.7).all(), prim.to_dict()
    london = cov[(cov.region == 13)].set_index("level_std").share
    assert london["gsp"] > 0.3 and london["bulk"] > 0.3           # 1 % on 29 Oct 2026


def test_contracted_demand_and_net_headroom_where_published():
    s = S.substations()
    for co in ("NGED", "Northern Powergrid", "SSEN"):
        c = s[s.company == co]
        assert c.demand_contracted_mw.notna().sum() > 50, co
        assert c.headroom_net_of_contracted_mw.notna().sum() > 50, co


def test_transmission_layer_carries_grid_supply_point_capacity():
    t = S.substations().query("level_std == 'transmission'")
    assert t.demand_headroom_mw.notna().sum() >= 50
    g = S.grid_supply_points()
    assert len(g) > 300 and g.lat.notna().mean() > 0.9
    assert (g[g.company == "SSEN"].import_limit_winter_mw.dropna() > 0).all()


def test_headroom_by_year_and_queue_tables_are_there():
    h = S.headroom_by_year()
    assert set(h.company) >= {"UKPN", "Northern Powergrid", "ENWL", "SSEN"}
    assert h.year.min() <= 2026 and h.year.max() >= 2050 and h.central.any()
    q = S.connection_queue()
    assert set(q.company) >= {"NGED", "UKPN", "Northern Powergrid", "SSEN"} and (q.demand_mw > 0).all()
    y = S.with_year_headroom(2030)
    assert y.headroom_year_mw.notna().sum() > 1000


def test_price_node_only_where_a_node_was_matched_by_name_to_the_connection_substation():
    n = S.price_nodes()
    named = n[(n.kind == "network") & n.how.isin(["name", "group"]) & (n.voltage_kv == 33.0) & (n.region == 9)].iloc[0]
    hit = S.price_node_at(named.lat, named.lon, 9, 33.0)
    assert hit is not None and hit["how"] in ("name", "group") and hit["node_id"] == named.node_id
    placed = n[(n.kind == "network") & (n.how == "place") & (n.voltage_kv == 33.0)]
    if len(placed):
        r = placed.iloc[0]
        got = S.price_node_at(r.lat, r.lon, int(r.region), 33.0)
        assert got is None or got["how"] in ("name", "group")       # never a place- or code-placed node


def test_connection_point_reports_the_basis_and_date_of_the_figure():
    p = S.connection_point(51.5074, -0.1278, "33 kV", 50.0, region=13)
    assert p["found"] and "headroom_basis" in p and "headroom_as_of" in p
    if p["headroom_status"] != "unknown":
        assert p["headroom_basis"] and p["headroom_as_of"]


def test_candidates_have_room_and_follow_the_areas_rules():
    c = A.candidates(60, 1.2)
    conn = c.attrs["connection_mw"]
    assert conn == pytest.approx(60 * 1.2 / 0.70, rel=1e-3)
    assert len(c) > 20 and (c.room_mw >= conn).all()
    for r in c.region.unique():
        rule = nc.connection_voltage(conn, int(r), False)
        assert (c[c.region == r].voltage.map({"11 kV": 0, "33 kV": 1, "132 kV": 2}) >= {"11 kV": 0, "33 kV": 1, "132 kV": 2}[rule]).all()
    big = A.candidates(150, 1.2)                                     # transmission tier in England and Wales
    assert (big.voltage == "transmission").any()
    yr = A.candidates(5, 1.2, year=2030)
    assert len(yr) > 100 and yr.room_basis.str.contains("2030").all()
    net = A.candidates(60, 1.2, net_of_contracted=True)
    assert len(net) <= len(c) + 5


def test_pricing_runs_the_same_chain_and_ranks():
    av = A.availability(60, 1.2, regions=[9, 13], top=5)
    assert len(av) and av.cost_m_per_year.is_monotonic_increasing
    r = av.iloc[0]
    assert 100 < r.cost_GBP_per_MWh < 260 and r.band.startswith(("EHV", "HV", "T-Demand"))
    assert r.capacity_GBP_per_MW_year > 0 and r.carbon_kg_per_kwh_delivered > 0
    assert set(av.columns) >= {"room_basis", "headroom_as_of", "duos_how", "carbon_window"}
    s = A.summary(av)
    assert len(s) == av.region.nunique()
