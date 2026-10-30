"""
S5 of COST_PLAN §1.11: solve time and answer, the price list chosen in the LP
against one fixed before it, on a full year (30 Oct 2026).
=============================================================================

The chain check (``check_connection_chain.py --mode ...``) times the 14 x 3
one-week runs; this is the one full-year run the plan asks for: one site, the
2025 window at hourly resolution, a three-point frontier in each mode, with
the time of every solve and the answer beside it.

Run:  python scripts/time_connection_modes.py [--region 13] [--size 150] [--modes single,room,cap]
      [--window 2025-01-01 2025-12-29] [--points 3]
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
from optimisation import dc_inputs as I, dc_model as M, dc_pareto as P, sites  # noqa: E402
from scripts.check_connection_chain import COORDS, PUE  # noqa: E402

OUT = ROOT / "optimisation_outputs" / "connection_mode_timing.csv"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--region", type=int, default=13)
    ap.add_argument("--size", type=float, default=150.0)
    ap.add_argument("--modes", default="single,room,cap")
    ap.add_argument("--window", nargs=2, default=["2025-01-01", "2025-12-29"])
    ap.add_argument("--points", type=int, default=3)
    ap.add_argument("--out", default=None, help="another CSV (default connection_mode_timing.csv), so modes can run in parallel")
    a = ap.parse_args()
    out = Path(a.out) if a.out else OUT
    lat, lon, city = COORDS[a.region]
    rows = []
    for mode in a.modes.split(","):
        t0 = time.time()
        site = sites.get(f"{lat},{lon}")
        series, meta = I.build_series(site, a.window[0], a.window[1], a.size, pue=PUE, connection_mode=mode)
        series = I.resample(series, 1.0)
        tech = I.build_tech(site, meta, ely_tech="PEM operation", cost_case="central", size_mw_it=a.size, pue=PUE)
        assets = M.Assets(grid=True, wind=True, solar=True, battery=True, electrolyser=True, tank=True, fuel_cell=True,
                          grid_limit_mw=meta["connection_limit_mw"], grid_floor_mw=meta["connection_floor_mw"])
        t_build = time.time() - t0
        solves = []

        def progress(tag):
            solves.append((tag, time.time()))

        t1 = time.time()
        r = P.front(series, assets, tech, points=a.points, progress=progress)
        t_front = time.time() - t1
        per = [b - a_ for (_, a_), (_, b) in zip(solves, solves[1:] + [("end", time.time())])]
        row = {"city": city, "size_mw_it": a.size, "mode": mode, "steps": series.n, "options": len(meta["connection_options"]),
               "build_s": t_build, "front_s": t_front, "solves": len(solves),
               "solve_s_mean": sum(per) / len(per), "solve_s_max": max(per)}
        for name in ("min_cost", "min_gwp", "knee"):
            x = r[name]
            row.update({f"{name}_cost_m_yr": x["cost_GBP_per_year"] / 1e6, f"{name}_t_yr": x["gwp_kgco2e_per_year"] / 1e3,
                        f"{name}_cap_grid": x["cap_grid"], f"{name}_option": x.get("connection_option", meta["tdr_band"] + " (fixed)")})
        rows.append(row)
        print(f"{city} {a.size:g} MW IT, {mode:<7} {series.n:,} steps, {row['options']:>2} lists: build {t_build:5.0f} s, "
              f"frontier {t_front:6.0f} s over {len(solves)} solves (mean {row['solve_s_mean']:.0f} s, max {row['solve_s_max']:.0f} s); "
              f"min cost £{row['min_cost_cost_m_yr']:.2f} m at {row['min_cost_cap_grid']:.1f} MW on {row['min_cost_option']}")
        pd.DataFrame(rows).to_csv(out, index=False)
    print(f"written to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
