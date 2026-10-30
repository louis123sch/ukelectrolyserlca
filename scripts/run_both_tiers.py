"""
A 150 MW IT data centre solved both ways: on the local network and on the
national grid (COST_PLAN §1.9 G follow-up, 29 Oct 2026).
=============================================================================

The chain check found every England-and-Wales 150 MW run sitting on the
transmission tier boundary — the optimiser would build a smaller connection
than the 1.43x ceiling (257 MW) puts it in. This runs the same site with the
tier forced each way (``Site.transmission_connected``), same window, same
resolution, and reports both anchors of the frontier with the charges behind
them.

Since 30 Oct 2026 (COST_PLAN §1.11 S4) this is also the check on the switched
model: the forced local run is capped at the company's largest connection
(240/250 MVA), and two switched runs follow — one restricted to the two forced
price lists, which must return the cheaper forced answer to solver tolerance,
and one with every price list, which must be no dearer.

Run:  python scripts/run_both_tiers.py [--regions 3,7,9,11,13,14] [--size 150] [--no-switched]
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import lca_helpers as H  # noqa: E402
H.setup_brightway()
from optimisation import dc_inputs as I, dc_model as M, dc_pareto as P, sites, network_charges as nc  # noqa: E402
from scripts.check_connection_chain import COORDS, START, END, PUE  # noqa: E402

OUT = ROOT / "optimisation_outputs" / "both_tiers_150mw.csv"


def _site(region: int, size: float, transmission: bool | None, mode: str):
    """The site for one run. A forced local run is capped at the company's
    largest connection (the caveat of 29 Oct 2026: the 257 MW ceiling is
    above the 240/250 MVA top), so the two forced lists are exactly the two
    the switched model has at those sizes."""
    lat, lon, _city = COORDS[region]
    limit = None
    if mode == "single" and transmission is False:
        limit = min(sites.max_connection_mw(size * PUE)[0], nc.dno_max_mva(region))
    return sites.get(f"{lat},{lon}", transmission_connected=transmission, connection_limit_mw=limit)


def run(region: int, size: float, transmission: bool | None, points: int = 3, mode: str = "single",
        restrict: bool = False) -> dict:
    """One solve. ``mode`` "single" forces the tier (today's model); "cap" lets
    the model choose among every price list capped at the 1.43x ceiling;
    ``restrict`` keeps only the two lists the forced runs are on (the local
    network at the reference voltage's top band, and the national grid), so
    the switched answer must equal the cheaper forced one."""
    lat, lon, city = COORDS[region]
    site = _site(region, size, transmission, mode)
    series, meta = I.build_series(site, START, END, size, pue=PUE, connection_mode=mode)
    series = I.resample(series, 1.0)
    kept = None
    if restrict and len(meta["connection_options"]) > 1:
        ref = meta["connection_reference"]
        top_local = max((o for o in meta["connection_options"] if not o["transmission"]),
                        key=lambda o: o["ceiling_mw"], default=None)
        keep = {o["key"] for o in meta["connection_options"] if o["transmission"]}
        if top_local is not None:
            keep |= {o["key"] for o in meta["connection_options"]
                     if not o["transmission"] and o["voltage"] == top_local["voltage"] and o["band"] == top_local["band"]
                     and o["which"] == top_local["which"]}
        meta = {**meta, "connection_options": [o for o in meta["connection_options"] if o["key"] in keep]}
        kept = [o["key"] for o in meta["connection_options"]]
    tech = I.build_tech(site, meta, ely_tech="PEM operation", cost_case="central", size_mw_it=size, pue=PUE)
    assets = M.Assets(grid=True, wind=True, solar=True, battery=True, electrolyser=True, tank=True, fuel_cell=True)
    assets = M.Assets(**{**assets.__dict__, "grid_limit_mw": meta["connection_limit_mw"],
                         "grid_floor_mw": meta["connection_floor_mw"]})
    t0 = time.time()
    r = P.front(series, assets, tech, points=points)
    c, cp = meta["network_charges"], meta["connection_site"] or {}
    label = ({True: "national grid (forced)", False: "local network (forced)"}[transmission] if mode == "single"
             else ("switched, the two forced lists" if restrict else "switched, every list"))
    row = {"region": region, "city": city, "tier": label, "mode": mode,
           "voltage": meta["connection_voltage"], "band": meta["tdr_band"],
           "ceiling_mw": meta["connection_limit_mw"], "floor_mw": meta["connection_floor_mw"],
           "options": len(meta["connection_options"]), "kept": ";".join(kept or []),
           "substation": cp.get("substation"), "route_km": cp.get("route_km"), "headroom": cp.get("headroom_status"),
           "tdr_GBP_yr": c["tnuos_tdr_GBP_per_year"], "duos_cap_GBP_MW_yr": c["duos_capacity_GBP_per_MW_year"],
           "duos_fixed_GBP_yr": c["duos_fixed_GBP_per_year"], "duos_unit_GBP_MWh": c["duos_mean_GBP_per_MWh"],
           "tnuos_loc_GBP_MW_yr": c["tnuos_locational_GBP_per_MW_year"],
           "conn_per_mw_yr": tech.cost_grid_per_mw_year, "conn_fixed_yr": tech.cost_grid_fixed_per_year,
           "price_mean_GBP_MWh": float(series.grid_price_per_mwh.mean()), "solve_s": time.time() - t0}
    for name in ("min_cost", "min_gwp"):
        x = r[name]
        row[f"{name}_cap_grid"] = x["cap_grid"]
        row[f"{name}_cost_m_yr"] = x["cost_GBP_per_year"] / 1e6
        row[f"{name}_t_yr"] = x["gwp_kgco2e_per_year"] / 1e3
        row[f"{name}_import_GWh"] = x["import_MWh_per_year"] / 1e3
        row[f"{name}_option"] = x.get("connection_option", f"{meta['tdr_band']} (fixed)")
        for k in ("cap_wind", "cap_solar", "cap_batt_e"):
            row[f"{name}_{k}"] = x.get(k)
    return row


TOL = 1e-5      # relative: the switched answer against the cheaper forced run


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--regions", default="3,7,9,11,13,14")
    ap.add_argument("--size", type=float, default=150.0)
    ap.add_argument("--no-switched", action="store_true", help="the two forced runs only, as on 29 Oct 2026")
    a = ap.parse_args()
    rows, fails = [], []
    for region in (int(r) for r in a.regions.split(",")):
        runs = [("single", True, False), ("single", False, False)]
        if not a.no_switched:
            runs += [("cap", None, True), ("cap", None, False)]
        got = {}
        for mode, transmission, restrict in runs:
            row = run(region, a.size, transmission, mode=mode, restrict=restrict)
            rows.append(row)
            got[row["tier"]] = row
            print(f"  r{region:<3}{row['city']:<12}{row['tier']:<30}{row['voltage']:<13}{row['band']:<10}"
                  f"cap {row['min_cost_cap_grid']:>6.1f} MW  cost £{row['min_cost_cost_m_yr']:>7.2f} m  "
                  f"{row['min_cost_t_yr']:>8,.0f} t | min-carbon £{row['min_gwp_cost_m_yr']:>7.2f} m {row['min_gwp_t_yr']:>8,.0f} t"
                  f"  {row['solve_s']:>4.0f} s  {row['min_cost_option'] if mode != 'single' else ''}")
            pd.DataFrame(rows).to_csv(OUT, index=False)
        if not a.no_switched:
            # S4 check (COST_PLAN §1.11): on the two forced lists the switched
            # answer is the cheaper forced run; with every list it is no dearer.
            forced = min(got["national grid (forced)"]["min_cost_cost_m_yr"], got["local network (forced)"]["min_cost_cost_m_yr"])
            two = got["switched, the two forced lists"]["min_cost_cost_m_yr"]
            every = got["switched, every list"]["min_cost_cost_m_yr"]
            ok_two = abs(two - forced) <= TOL * forced
            ok_all = every <= forced * (1 + TOL)
            print(f"      check: switched on the two lists £{two:.4f} m vs cheaper forced £{forced:.4f} m "
                  f"[{'PASS' if ok_two else 'FAIL'}]; every list £{every:.4f} m [{'PASS' if ok_all else 'FAIL'}]")
            if not (ok_two and ok_all):
                fails.append(region)
    d = pd.DataFrame(rows)
    print(f"\nwritten to {OUT}\n")
    piv = d.pivot(index="city", columns="tier", values=["min_cost_cost_m_yr", "min_cost_t_yr", "min_gwp_cost_m_yr", "min_gwp_t_yr"])
    piv["cost gap local-national, £m/yr"] = piv[("min_cost_cost_m_yr", "local network (forced)")] - piv[("min_cost_cost_m_yr", "national grid (forced)")]
    pd.set_option("display.width", 250)
    print(piv.round(2).to_string())
    if not a.no_switched:
        print("\n" + ("ALL PASSED: the switched answer is the cheaper forced run on the two lists, and no dearer with every list"
                       if not fails else f"FAILED in regions {fails}"))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
