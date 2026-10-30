"""
Where can a data centre of this size connect? (COST_PLAN §1.10 R5)
=============================================================================

Lists every substation in the register with room for the connection a site
of this size needs, prices each through the connection chain without solving
(``optimisation.availability``), ranks by cost and carbon, and optionally
solves the optimiser at the top few (the site placed at the substation).

    python scripts/availability_map.py --size 60 [--pue 1.2] [--headroom 1.43]
          [--year 2030] [--net-of-contracted] [--regions 3,13] [--by cost|carbon]
          [--top 25] [--solve 3] [--window 2025-06-02 2025-06-09]

Writes optimisation_outputs/availability/<size>mw[_<year>][_net].csv and
prints the top rows and a per-area summary.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")
OUT = ROOT / "optimisation_outputs" / "availability"


def solve_top(av: pd.DataFrame, size: float, pue: float, n: int, start: str, end: str, points: int = 3) -> pd.DataFrame:
    """The optimiser's two anchors at the top ``n`` candidates, site at the substation."""
    import lca_helpers as H
    H.setup_brightway()
    from optimisation import dc_inputs as I, dc_model as M, dc_pareto as P, sites
    rows = []
    for r in av.head(n).itertuples(index=False):
        t0 = time.time()
        try:
            site = sites.resolve(r.lat, r.lon, name=f"{r.name} ({r.company})", carbon_api_region=int(r.region))
            series, meta = I.build_series(site, start, end, size, pue=pue)
            series = I.resample(series, 1.0)
            tech = I.build_tech(site, meta, ely_tech="PEM operation", cost_case="central", size_mw_it=size, pue=pue)
            assets = M.Assets(grid=True, wind=True, solar=True, battery=True, electrolyser=True, tank=True, fuel_cell=True)
            assets = M.Assets(**{**assets.__dict__, "grid_limit_mw": meta["connection_limit_mw"],
                                 "grid_floor_mw": meta["connection_floor_mw"]})
            f = P.front(series, assets, tech, points=points)
            cp = meta["connection_site"] or {}
            rows.append({"rank": r.rank, "name": r.name, "company": r.company, "voltage_run": meta["connection_voltage"],
                         "band_run": meta["tdr_band"], "substation_run": cp.get("substation"), "route_km": cp.get("route_km"),
                         "headroom_run": cp.get("headroom_status"),
                         "min_cost_m_yr": f["min_cost"]["cost_GBP_per_year"] / 1e6, "min_cost_t_yr": f["min_cost"]["gwp_kgco2e_per_year"] / 1e3,
                         "min_cost_cap_grid": f["min_cost"]["cap_grid"],
                         "min_gwp_m_yr": f["min_gwp"]["cost_GBP_per_year"] / 1e6, "min_gwp_t_yr": f["min_gwp"]["gwp_kgco2e_per_year"] / 1e3,
                         "seconds": time.time() - t0})
            print(f"  solved #{r.rank} {r.name} ({r.company}): min cost £{rows[-1]['min_cost_m_yr']:.2f} m/yr, "
                  f"min carbon {rows[-1]['min_gwp_t_yr']:,.0f} t/yr  ({rows[-1]['seconds']:.0f} s)")
        except Exception as e:                    # keep going
            rows.append({"rank": r.rank, "name": r.name, "company": r.company, "error": repr(e)[:200]})
            print(f"  !! #{r.rank} {r.name}: {e!r}"[:200])
    return pd.DataFrame(rows)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--size", type=float, required=True, help="IT load, MW")
    ap.add_argument("--pue", type=float, default=1.2)
    ap.add_argument("--headroom", type=float, default=None, help="connection / load; default 1 / 0.70")
    ap.add_argument("--year", type=int, default=None, help="read the companies' scenario headroom for this year")
    ap.add_argument("--net-of-contracted", action="store_true")
    ap.add_argument("--regions", default=None, help="comma-separated CI regions, default all 14")
    ap.add_argument("--by", choices=["cost", "carbon"], default="cost")
    ap.add_argument("--top", type=int, default=25)
    ap.add_argument("--solve", type=int, default=0, help="solve the optimiser at the top N")
    ap.add_argument("--window", nargs=2, default=["2025-06-02", "2025-06-09"])
    ap.add_argument("--points", type=int, default=3)
    a = ap.parse_args()
    from optimisation import availability as A
    regions = [int(x) for x in a.regions.split(",")] if a.regions else None
    t0 = time.time()
    av = A.availability(a.size, a.pue, a.headroom, year=a.year, net_of_contracted=a.net_of_contracted,
                        regions=regions, by=a.by)
    z = av.attrs
    print(f"{a.size:g} MW IT x PUE {a.pue:g} = {z.get('load_mw', 0):.1f} MW load, {z.get('connection_mw', 0):.1f} MW connection"
          f"{'' if a.year is None else f', room in {a.year}'}{' net of contracted' if a.net_of_contracted else ''}: "
          f"{len(av):,} substations with room ({time.time() - t0:.0f} s)")
    if av.empty:
        return 1
    OUT.mkdir(parents=True, exist_ok=True)
    stem = f"{a.size:g}mw" + (f"_{a.year}" if a.year else "") + ("_net" if a.net_of_contracted else "")
    av.to_csv(OUT / f"{stem}.csv", index=False)
    show = ["rank", "area", "name", "level", "voltage", "band", "room_mw", "cost_m_per_year", "cost_GBP_per_MWh",
            "carbon_kg_per_kwh_delivered", "duos_how", "headroom_as_of"]
    pd.set_option("display.width", 200)
    print(av[show].head(a.top).to_string(index=False, float_format=lambda x: f"{x:,.2f}"))
    print("\nper area:")
    print(A.summary(av).to_string(index=False, float_format=lambda x: f"{x:,.2f}"))
    print(f"\nwholesale £{z.get('wholesale_GBP_per_MWh', 0):.2f}/MWh ({z.get('price_file')}); levies £{z.get('levies_GBP_per_MWh', 0):.2f}/MWh; "
          f"build prices at the 2 km default route; written to {OUT / (stem + '.csv')}")
    if a.solve:
        print(f"\nsolving the optimiser at the top {a.solve} ({a.window[0]} to {a.window[1]}, hourly):")
        s = solve_top(av, a.size, a.pue, a.solve, a.window[0], a.window[1], a.points)
        s.to_csv(OUT / f"{stem}_solved.csv", index=False)
        print(s.to_string(index=False, float_format=lambda x: f"{x:,.2f}"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
