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

Caveat: forced local, the 257 MW ceiling is above the DNO's top (240/250 MVA);
the model does not cap it, and the LP builds what it wants under 257. A real
offer would hold it at the DNO's top.

Run:  python scripts/run_both_tiers.py [--regions 3,7,9,11,13,14] [--size 150]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import lca_helpers as H  # noqa: E402
H.setup_brightway()
from optimisation import dc_inputs as I, dc_model as M, dc_pareto as P, sites, duos_areas as D  # noqa: E402
from scripts.check_connection_chain import COORDS, START, END, PUE  # noqa: E402

OUT = ROOT / "optimisation_outputs" / "both_tiers_150mw.csv"


def run(region: int, size: float, transmission: bool, points: int = 3) -> dict:
    lat, lon, city = COORDS[region]
    site = sites.get(f"{lat},{lon}", transmission_connected=transmission)
    series, meta = I.build_series(site, START, END, size, pue=PUE)
    series = I.resample(series, 1.0)
    tech = I.build_tech(site, meta, ely_tech="PEM operation", cost_case="central", size_mw_it=size, pue=PUE)
    assets = M.Assets(grid=True, wind=True, solar=True, battery=True, electrolyser=True, tank=True, fuel_cell=True)
    assets = M.Assets(**{**assets.__dict__, "grid_limit_mw": meta["connection_limit_mw"],
                         "grid_floor_mw": meta["connection_floor_mw"]})
    r = P.front(series, assets, tech, points=points)
    c, cp = meta["network_charges"], meta["connection_site"] or {}
    row = {"region": region, "city": city, "tier": "national grid" if transmission else "local network",
           "voltage": meta["connection_voltage"], "band": meta["tdr_band"],
           "ceiling_mw": meta["connection_limit_mw"], "floor_mw": meta["connection_floor_mw"],
           "substation": cp.get("substation"), "route_km": cp.get("route_km"), "headroom": cp.get("headroom_status"),
           "tdr_GBP_yr": c["tnuos_tdr_GBP_per_year"], "duos_cap_GBP_MW_yr": c["duos_capacity_GBP_per_MW_year"],
           "duos_fixed_GBP_yr": c["duos_fixed_GBP_per_year"], "duos_unit_GBP_MWh": c["duos_mean_GBP_per_MWh"],
           "tnuos_loc_GBP_MW_yr": c["tnuos_locational_GBP_per_MW_year"],
           "conn_per_mw_yr": tech.cost_grid_per_mw_year, "conn_fixed_yr": tech.cost_grid_fixed_per_year,
           "price_mean_GBP_MWh": float(series.grid_price_per_mwh.mean())}
    for name in ("min_cost", "min_gwp"):
        x = r[name]
        row[f"{name}_cap_grid"] = x["cap_grid"]
        row[f"{name}_cost_m_yr"] = x["cost_GBP_per_year"] / 1e6
        row[f"{name}_t_yr"] = x["gwp_kgco2e_per_year"] / 1e3
        row[f"{name}_import_GWh"] = x["import_MWh_per_year"] / 1e3
        for k in ("cap_wind", "cap_solar", "cap_batt_e"):
            row[f"{name}_{k}"] = x.get(k)
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--regions", default="3,7,9,11,13,14")
    ap.add_argument("--size", type=float, default=150.0)
    a = ap.parse_args()
    rows = []
    for region in (int(r) for r in a.regions.split(",")):
        for transmission in (True, False):
            row = run(region, a.size, transmission)
            rows.append(row)
            print(f"  r{region:<3}{row['city']:<12}{row['tier']:<14}{row['voltage']:<13}{row['band']:<10}"
                  f"cap {row['min_cost_cap_grid']:>6.1f} MW  cost £{row['min_cost_cost_m_yr']:>7.2f} m  "
                  f"{row['min_cost_t_yr']:>8,.0f} t | min-carbon £{row['min_gwp_cost_m_yr']:>7.2f} m {row['min_gwp_t_yr']:>8,.0f} t")
            pd.DataFrame(rows).to_csv(OUT, index=False)
    d = pd.DataFrame(rows)
    print(f"\nwritten to {OUT}\n")
    piv = d.pivot(index="city", columns="tier", values=["min_cost_cost_m_yr", "min_cost_t_yr", "min_gwp_cost_m_yr", "min_gwp_t_yr"])
    piv["cost gap local-national, £m/yr"] = piv[("min_cost_cost_m_yr", "local network")] - piv[("min_cost_cost_m_yr", "national grid")]
    piv["carbon gap local-national, t/yr"] = piv[("min_gwp_t_yr", "local network")] - piv[("min_gwp_t_yr", "national grid")]
    pd.set_option("display.width", 250)
    print(piv.round(2).to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
