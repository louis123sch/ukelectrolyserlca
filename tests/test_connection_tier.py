"""Integration test: tier -> band -> DUoS -> frontier, both sides of the tier.

Slow — it solves several LPs and needs Brightway and a Renewables.ninja token,
so the fast suite skips it. Run it directly, or with RUN_SLOW=1 under pytest.
"""
import os
import sys, numpy as np

import pytest
sys.path.insert(0, "/Users/louis/lca-ai-project/ukelectrolyserlca")
import lca_helpers as H; H.setup_brightway()
from optimisation import dc_inputs as I, dc_model as M, dc_pareto as P



def _run():
    fails = []
    W = ("2025-01-01", "2025-02-01")
    def check(name, ok, detail=""):
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}   {detail}")
        if not ok: fails.append(name)

    # EHV3, not EHV2, and deliberately: at PUE 1.2 the 7.31 MW reference draws
    # 8.77 MW, whose 1.5x connection ceiling is 13.16 MVA — over EHV2's 12 MVA
    # boundary. At the reference's own PUE of 1.00 the ceiling is 10.96 MVA and
    # the band is EHV2, unchanged from before the chain existed. The band
    # following the connection rather than the load is the point of the chain,
    # so this asserts the derived answer, not the historical one.
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
        r = P.front(series, assets, tech, points=3)
        d = r["front"]
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
