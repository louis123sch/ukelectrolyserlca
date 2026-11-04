"""The two knobs behind the +/-50 % test of the grid connection's price (4 Nov 2026): each moves what
it says and nothing else, on one price list and on several, and the sweep reports all three frontier
points with terms that add up. One June week, so it needs the caches but no full-year solve."""
import pathlib
import sys
from dataclasses import replace

import numpy as np
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from optimisation import connection_cost, dc_inputs as I, sensitivity as S, sites  # noqa: E402

LONDON = "51.5074,-0.1278"
WEEK = ("2025-06-02", "2025-06-09")
SIZE, PUE = 150.0, 1.2


def _series(site=LONDON, mode="single", **kw):
    return I.build_series(site, *WEEK, SIZE, pue=PUE, connection_mode=mode, **kw)


def _tech(meta, site=LONDON, **kw):
    return I.build_tech(site, meta, size_mw_it=SIZE, pue=PUE, **kw)


@pytest.fixture(scope="module")
def local():
    """A local-network site: the only kind that pays per-MWh and local capacity charges."""
    return replace(sites.get(LONDON), connection_substation="LEICESTER SQ 11KV",
                   connection_substation_voltage="132 kV")


@pytest.fixture(scope="module")
def base(local):
    series, meta = _series(local, mode="room")
    return series, meta, _tech(meta, local)


def _build(meta, site):
    return connection_cost.connection_costs(site.carbon_api_region, bool(meta["transmission_connected"]), "central",
                                            connection_voltage=meta["connection_voltage"],
                                            route_km=(meta["connection_site"] or {}).get("route_km"))


def test_the_knobs_at_one_are_the_published_model(local, base):
    series, meta, tech = base
    s1, m1 = _series(local, mode="room", network_charges_scale=1.0)
    t1 = _tech(m1, local, connection_build_scale=1.0)
    assert np.array_equal(s1.grid_price_per_mwh, series.grid_price_per_mwh)
    for f in ("cost_grid_per_mw_year", "cost_grid_triad_per_mw_year", "cost_grid_fixed_per_year"):
        assert getattr(t1, f) == getattr(tech, f)
    assert tech.labels["connection_build_scale"] == 1.0 and tech.labels["network_charges_scale"] == 1.0


@pytest.mark.parametrize("scale", [0.5, 1.5])
def test_the_build_knob_moves_only_the_build_cost(local, base, scale):
    series, meta, tech = base
    t = _tech(meta, local, connection_build_scale=scale)
    b = _build(meta, local)
    assert t.cost_grid_per_mw_year - tech.cost_grid_per_mw_year == pytest.approx((scale - 1) * b["per_MW_year_GBP"])
    assert t.cost_grid_fixed_per_year - tech.cost_grid_fixed_per_year == pytest.approx((scale - 1) * b["fixed_per_year_GBP"])
    assert t.cost_grid_triad_per_mw_year == tech.cost_grid_triad_per_mw_year
    assert t.gwp_grid_per_mw == tech.gwp_grid_per_mw and t.gwp_grid_fixed_per_year == tech.gwp_grid_fixed_per_year
    assert t.labels["connection_build_scale"] == scale


@pytest.mark.parametrize("scale", [0.5, 1.5])
def test_the_network_knob_moves_every_network_charge_and_not_the_build_cost(local, base, scale):
    series, meta, tech = base
    s, m = _series(local, mode="room", network_charges_scale=scale)
    t = _tech(m, local)
    b = _build(meta, local)
    assert m["capacity_GBP_per_MW_year"] == pytest.approx(scale * meta["capacity_GBP_per_MW_year"])
    assert m["fixed_GBP_per_year"] == pytest.approx(scale * meta["fixed_GBP_per_year"])
    assert t.cost_grid_triad_per_mw_year == pytest.approx(scale * tech.cost_grid_triad_per_mw_year)
    assert t.cost_grid_per_mw_year - b["per_MW_year_GBP"] == pytest.approx(scale * (tech.cost_grid_per_mw_year - b["per_MW_year_GBP"]))
    assert t.cost_grid_fixed_per_year - b["fixed_per_year_GBP"] == pytest.approx(scale * (tech.cost_grid_fixed_per_year - b["fixed_per_year_GBP"]))
    assert t.labels["network_charges_scale"] == scale and t.labels["connection_build_scale"] == 1.0
    # Only the local unit rates inside the import price move, and they do move.
    moved = np.asarray(s.grid_price_per_mwh) - np.asarray(series.grid_price_per_mwh)
    duos = meta["network_charges"]["duos_mean_GBP_per_MWh"]
    assert duos > 0 and moved.mean() == pytest.approx((scale - 1) * duos, rel=1e-6)
    assert np.array_equal(s.grid_gwp_per_mwh, series.grid_gwp_per_mwh)
    assert m["network_charges"]["bsuos_mean_GBP_per_MWh"] == meta["network_charges"]["bsuos_mean_GBP_per_MWh"]


def test_the_network_knob_leaves_the_national_grid_unit_price_alone():
    """A national-grid site pays no local unit rates, so its import price does not move."""
    s0, m0 = _series()
    s1, m1 = _series(network_charges_scale=0.5)
    assert np.array_equal(s0.grid_price_per_mwh, s1.grid_price_per_mwh)
    assert m1["fixed_GBP_per_year"] == pytest.approx(0.5 * m0["fixed_GBP_per_year"])


def test_the_knobs_reach_every_price_list():
    series, meta = _series(mode="cap")
    tech = _tech(meta)
    assert len(tech.connection_options) > 1
    s1, m1 = _series(mode="cap", network_charges_scale=0.5)
    t1 = _tech(m1, connection_build_scale=1.5)
    tnuos = meta["network_charges"]["tnuos_locational_GBP_per_MW_year"]
    assert t1.cost_grid_triad_per_mw_year == pytest.approx(0.5 * tnuos)
    for o0, o1, rec in zip(tech.connection_options, t1.connection_options, meta["connection_options"]):
        assert o1.key == o0.key
        i = o0.info
        assert o1.cost_per_mw_year == pytest.approx(0.5 * (rec["capacity_GBP_per_MW_year"] - tnuos)
                                                    + 1.5 * i["build_per_MW_year_GBP"])
        assert o1.cost_fixed_per_year == pytest.approx(0.5 * rec["fixed_GBP_per_year"] + 1.5 * i["build_fixed_per_year_GBP"])
    for g in series.grid_groups:
        duos = meta["connection_groups"][g]["duos_mean_GBP_per_MWh"]
        moved = np.asarray(s1.grid_groups[g]["price_per_mwh"]) - np.asarray(series.grid_groups[g]["price_per_mwh"])
        assert moved.mean() == pytest.approx(-0.5 * duos, abs=1e-9)


@pytest.mark.parametrize("kw", [{"connection_build_scale": -1.0}, {"connection_build_scale": float("nan")}])
def test_a_bad_build_scale_fails_at_once(kw):
    with pytest.raises(ValueError, match="connection_build_scale"):
        I.build_tech("london", {}, **kw)


def test_a_bad_network_scale_fails_at_once():
    with pytest.raises(ValueError, match="network_charges_scale"):
        _series(network_charges_scale=-0.5)


def test_the_sweep_is_the_central_case_and_each_knob_either_way():
    assert S.one_at_a_time(S.CONNECTION_KNOBS) == [
        {}, {"connection_build_scale": 0.5}, {"connection_build_scale": 1.5},
        {"network_charges_scale": 0.5}, {"network_charges_scale": 1.5}]
    assert "network_charges_scale" in S.SERIES_KNOBS and "connection_build_scale" not in S.SERIES_KNOBS
    assert set(S.CONNECTION_CASES) <= set(S.CASES)


def test_a_frontier_sweep_reports_three_points_with_terms_that_add_up(tmp_path, monkeypatch):
    monkeypatch.setattr(S, "OUT_DIR", tmp_path)
    case = replace(S.CASES["london_150_leicester_sq"], start="2025-06-02", end="2025-06-04")
    variants = [{}, {"connection_build_scale": 1.5}]
    df = S.run(case, variants, name="t", points=2, progress=None)
    assert list(df.objective[:3]) == ["min_cost", "knee", "min_gwp"] and len(df) == 6
    assert (tmp_path / "sensitivity_t.csv").exists()
    cost = df[[c for c in df if c.startswith("cost_m:")]].sum(axis=1)
    gwp = df[[c for c in df if c.startswith("gwp_t:")]].sum(axis=1)
    assert np.allclose(cost, df.cost_m_GBP_per_year) and np.allclose(gwp, df.gwp_t_per_year)
    assert (df[df.variant == "central"].d_cost_m_GBP_per_year_pct == 0).all()
    # A second run with resume solves nothing it already has.
    called = []
    monkeypatch.setattr(S, "_frontier_rows", lambda *a, **k: called.append(a) or [])
    again = S.run(case, variants, name="t", points=2, progress=None, resume=True)
    assert not called and len(again) == 6
