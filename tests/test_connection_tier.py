"""The connection tier: GB's voltage rule and the band floor (fast), and the
chain tier -> band -> DUoS -> frontier on both sides of the tier (slow).

The slow test solves several LPs and needs Brightway and a Renewables.ninja
token, so the fast suite skips it. Run it directly, or with RUN_SLOW=1.
"""
import os
import pathlib
import sys, numpy as np

import pytest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from optimisation import network_charges as nc

LONDON, HIGHLAND, NORTH_WEST, YORKSHIRE, WEST_MIDLANDS, SOUTH_SCOTLAND = 13, 1, 3, 5, 8, 2


# --- fast: the tier rule and the band floor, no solve ------------------------
@pytest.mark.parametrize("region, mw, want", [
    (LONDON, 225.0, False),       # 157 MW load x 1.43: distribution, under 240 MVA
    (LONDON, 241.0, True),
    (HIGHLAND, 119.0, False),
    (HIGHLAND, 121.0, True),      # Scotland's DNO stops at 33 kV
])
def test_tier_follows_the_voltage_rule(region, mw, want):
    assert nc.is_transmission_connected(mw, region)[0] is want


@pytest.mark.parametrize("region", [LONDON, HIGHLAND])
def test_an_explicit_tier_beats_the_rule(region):
    assert nc.is_transmission_connected(500.0, region, False) == (False, "")
    assert nc.is_transmission_connected(1.0, region, True) == (True, "")


def test_the_rule_needs_a_region():
    with pytest.raises(ValueError):
        nc.is_transmission_connected(50.0, None)


@pytest.mark.parametrize("band, floor", [("HV1", 0.0), ("HV2", 0.5), ("HV3", 1.1),
                                         ("HV4", 2.0),
                                         # an EHV site is over the area's 11 kV
                                         # limit (15 MVA in the North West), so
                                         # its floor is never below it
                                         ("EHV1", 15.0), ("EHV2", 15.0),
                                         ("EHV3", 15.0), ("EHV4", 20.0)])
def test_distribution_band_floors(band, floor):
    assert nc.band_floor_mw(False, band, NORTH_WEST) == floor


def test_every_region_has_a_rule_that_is_in_order():
    for region in range(1, 15):
        r = nc.area_rule(region)
        assert 0 < r.max_11kv < r.max_33kv <= r.dno_max
        assert r.uncertain_from < r.dno_max
        assert r.sources


@pytest.mark.parametrize("region, mw, voltage, band", [
    (LONDON, 1.5, "11 kV", "HV3"),
    (LONDON, 7.9, "11 kV", "HV4"),
    (LONDON, 8.0, "33 kV", "EHV2"),          # UKPN: 8 MVA and above to 33 kV
    (NORTH_WEST, 13.16, "11 kV", "HV4"),     # ES216: 11 kV up to 15 MVA
    (NORTH_WEST, 15.0, "11 kV", "HV4"),
    (NORTH_WEST, 16.0, "33 kV", "EHV3"),
    (YORKSHIRE, 12.0, "11 kV", "HV4"),       # Northern Powergrid: 12 MVA at 11 kV
    (YORKSHIRE, 13.0, "33 kV", "EHV3"),
    (NORTH_WEST, 120.0, "33 kV", "EHV4"),    # 33 kV at a bulk supply point
    (NORTH_WEST, 121.0, "132 kV", "EHV4"),
    (HIGHLAND, 119.0, "33 kV", "EHV4"),      # Scotland's DNO stops at 33 kV
])
def test_voltage_decides_the_band_family(region, mw, voltage, band):
    """HV is 1 kV to under 22 kV, EHV 22 kV and above (LC14 glossary)."""
    assert nc.connection_voltage(mw, region, False) == voltage
    assert nc.tdr_band_for(mw, mw * 8760, region=region,
                           transmission_connected=False)[0] == band


@pytest.mark.parametrize("region, mw, want", [
    (WEST_MIDLANDS, 245.0, False),   # NGED: 250 MW and over not seen on distribution
    (WEST_MIDLANDS, 251.0, True),
    (NORTH_WEST, 245.0, True),       # ENWL: 240 MVA
])
def test_the_top_of_the_local_network_follows_the_area(region, mw, want):
    assert nc.is_transmission_connected(mw, region)[0] is want


@pytest.mark.parametrize("region, mw, want", [
    (LONDON, 100.0, False),          # 33 kV is enough: the rule is clear
    (LONDON, 150.0, True),           # 132 kV local or a 132 kV bay on the national grid
    (LONDON, 241.0, False),          # above the top: national grid, no doubt
    (WEST_MIDLANDS, 249.0, True),
    (SOUTH_SCOTLAND, 40.0, False),   # one 33 kV cable carries it
    (SOUTH_SCOTLAND, 60.0, True),    # above one cable, up to the 120 MVA proxy
    (SOUTH_SCOTLAND, 121.0, False),
])
def test_which_sizes_are_uncertain(region, mw, want):
    assert nc.tier_is_uncertain(mw, region) is want


def test_an_11kv_site_takes_grid_electricity_at_medium_voltage():
    assert nc.delivery_voltage(False, "HV4") == "medium"
    assert nc.delivery_voltage(False, "EHV3") == "high"
    assert nc.delivery_voltage(True, "T-Demand4") == "high"


@pytest.mark.parametrize("mwh, band", [(20_000, "T-Demand1"), (25_131, "T-Demand1"),
                                       (60_000, "T-Demand2"), (100_000, "T-Demand3"),
                                       (163_881, "T-Demand4"), (876_000, "T-Demand4")])
def test_transmission_band_follows_annual_consumption(mwh, band):
    """NESO Table TB (2026/27): T-Demand bands are set on MWh a year, not MVA."""
    assert nc.tdr_band_for(500.0, mwh, region=LONDON)[0] == band


def test_the_tariff_year_is_2026_27():
    """The residual for each band, read live for the tariff year (NESO FY2027)."""
    tdr, _ = nc.tnuos_tdr()
    per_day = dict(zip(tdr.band, tdr.GBP_per_site_day))
    assert nc.TARIFF_FY == 2027
    assert per_day["EHV4"] == pytest.approx(5_698.386405)
    assert per_day["T-Demand4"] == pytest.approx(20_829.236682)


def test_transmission_floor_is_the_tier_boundary():
    assert nc.band_floor_mw(True, "T-Demand4", LONDON) == nc.E_AND_W_DNO_MAX_MVA
    assert nc.band_floor_mw(True, "T-Demand4", HIGHLAND) == nc.SCOTLAND_DNO_MAX_MVA


@pytest.mark.parametrize("region, ceiling", [(LONDON, 225.0), (LONDON, 300.0),
                                             (HIGHLAND, 450.0), (LONDON, 8.0),
                                             (LONDON, 16.0), (LONDON, 1.0)])
def test_the_floor_sits_in_the_ceilings_band(region, ceiling):
    """The ceiling is in its own band, so its floor can never be above it."""
    trans, _ = nc.is_transmission_connected(ceiling, region)
    band, _ = nc.tdr_band_for(ceiling, ceiling * 8760, region=region,
                              transmission_connected=trans)
    assert nc.band_floor_mw(trans, band, region) <= ceiling



def _run():
    import lca_helpers as H; H.setup_brightway()
    from optimisation import dc_inputs as I, dc_model as M, dc_pareto as P
    fails = []
    W = ("2025-01-01", "2025-02-01")
    def check(name, ok, detail=""):
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}   {detail}")
        if not ok: fails.append(name)

    # HV4: at PUE 1.2 the 7.31 MW reference draws 8.77 MW, whose 1.43x connection
    # ceiling is 13.16 MVA — under ES216's 15 MVA for 11 kV, so an HV site, in the
    # top HV band (over 2,000 kVA). It was EHV3 until 28 Oct 2026, when every
    # distribution site took an EHV band.
    # The Highland site (North Scotland) uses the national 12 MVA 11 kV limit, so
    # a 13.16 MVA ceiling is a 33 kV, EHV3 connection there.
    for label, mw, want_trans, want_band in (("distribution 7.31 MW", 7.31, False, "EHV3"),
                                             ("transmission 300 MW", 300.0, True, "T-Demand4")):
        print(f"\n=== {label} ===")
        series, meta = I.build_series("57.48,-4.22", *W, mw, pue=1.2)
        series = I.resample(series, 1.0)
        c = meta["network_charges"]
        check("tier", meta["transmission_connected"] is want_trans,
              f"transmission={meta['transmission_connected']}")
        check("band", meta["tdr_band"] == want_band, meta["tdr_band"])
        duos_cap = c["duos_capacity_GBP_per_MW_year"]
        check("DUoS capacity consistent with tier",
              (duos_cap == 0.0) if want_trans else (duos_cap > 0),
              f"£{duos_cap:,.2f}/MW/yr")
        check("DUoS volumetric consistent with tier",
              (c["duos_mean_GBP_per_MWh"] == 0.0) if want_trans else (c["duos_mean_GBP_per_MWh"] > 0),
              f"£{c['duos_mean_GBP_per_MWh']:.2f}/MWh")
        if not want_trans:
            check("distribution capacity charge unregressed",
                  abs(c["duos_capacity_GBP_per_MW_year"] - 33543.50) < 0.01,
                  f"£{duos_cap:,.2f} (was £33,543.50)")

        tech = I.build_tech("57.48,-4.22", meta, ely_tech="SOEC operation",
                            cost_case="central", size_mw_it=mw, pue=1.2)
        assets = M.Assets(grid=True, wind=True, solar=True, battery=True,
                          electrolyser=True, tank=True, fuel_cell=True)
        assets = M.Assets(**{**assets.__dict__,
                             "grid_limit_mw": meta["connection_limit_mw"],
                             "grid_floor_mw": meta["connection_floor_mw"]})
        r = P.front(series, assets, tech, points=3)
        d = r["front"]
        # The fix the tier plan exists for: what is built is in the band charged.
        for name in ("min_cost", "min_gwp"):
            built = r[name]["cap_grid"]
            band, _ = nc.tdr_band_for(built, meta["load_mw"] * 8760 if "load_mw" in meta else None,
                                      region=1, transmission_connected=meta["transmission_connected"])
            check(f"{name} built in the band charged", band == meta["tdr_band"],
                  f"{built:,.1f} MW -> {band} vs {meta['tdr_band']}")
        check("frontier solved", len(d) >= 2, f"{len(d)} points")
        check("carbon ordering monotone", d.gwp_kgco2e_per_year.is_monotonic_increasing)
        check("cost falls as carbon rises", d.cost_GBP_per_year.is_monotonic_decreasing,
              f"£{d.cost_GBP_per_year.min()/1e6:.2f}-{d.cost_GBP_per_year.max()/1e6:.2f} m")
        check("min_gwp is the cleanest point",
              r["min_gwp"]["gwp_kgco2e_per_year"] <= d.gwp_kgco2e_per_year.min() * (1 + 1e-9))
        check("min_cost is the cheapest point",
              r["min_cost"]["cost_GBP_per_year"] <= d.cost_GBP_per_year.min() * (1 + 1e-9))

        # Walk the three stages by hand: each must hold carbon, and each must only
        # tighten what the stage before it left free. Comparing stage 3 against the
        # raw carbon-only solve would be meaningless — stage 2 moves to a cheaper
        # system, and a cheaper system can legitimately need a bigger connection.
        def stage(objective, **kw):
            m, V, o = M.build_model(series, assets, tech, objective=objective, **kw)
            M.solve(m)
            return _x(V, o), M.dispatch_frame(V, series)
        _x = lambda V, o: P._extract(V, o, series, "s")
        s1, _ = stage("gwp")
        g = s1["gwp_kgco2e_per_year"]
        s2, _ = stage("cost", gwp_limit=g * (1 + P.LEX_TOL))
        s3, d3 = stage("connection", gwp_limit=g * (1 + P.LEX_TOL),
                       cost_limit=s2["cost_GBP_per_year"] * (1 + P.LEX_TOL))
        check("stage 2 does not worsen cost",
              s2["cost_GBP_per_year"] <= s1["cost_GBP_per_year"] * (1 + 1e-9),
              f"£{s1['cost_GBP_per_year']/1e6:.3f} -> £{s2['cost_GBP_per_year']/1e6:.3f} m")
        check("stage 3 does not grow the connection",
              s3["cap_grid"] <= s2["cap_grid"] * (1 + 1e-9),
              f"{s2['cap_grid']:.4f} -> {s3['cap_grid']:.4f} MW")
        slack = s3["cap_grid"] - float(d3.imp.max())
        check("stage 3 leaves no slack on the connection",
              slack <= max(s3["cap_grid"], 1.0) * 1e-6,
              f"slack {slack:.6f} MW over a {float(d3.imp.max()):.4f} MW peak")
        check("carbon held across all three stages",
              all(abs(x["gwp_kgco2e_per_year"] - g) <= abs(g) * 1e-5 for x in (s2, s3)),
              f"{s1['gwp_kgco2e_per_year']/1000:,.1f} / {s2['gwp_kgco2e_per_year']/1000:,.1f}"
              f" / {s3['gwp_kgco2e_per_year']/1000:,.1f} t")
        check("front's anchor matches the three-stage result",
              abs(r["min_gwp"]["cap_grid"] - s3["cap_grid"]) <= max(s3["cap_grid"], 1.0) * 1e-6,
              f"{r['min_gwp']['cap_grid']:.4f} vs {s3['cap_grid']:.4f} MW")
        check("MWh columns present", "cap_grid_MWh_per_year" in d.columns)

    return fails


@pytest.mark.skipif(not os.environ.get("RUN_SLOW"),
                    reason="solves several LPs; set RUN_SLOW=1 to run")
def test_connection_tier_and_frontier():
    assert _run() == []


if __name__ == "__main__":
    f = _run()
    print("\n" + ("ALL PASSED" if not f else f"FAILED: {f}"))
    sys.exit(1 if f else 0)
