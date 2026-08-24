#!/usr/bin/env python
"""Run the data centre scenario matrix headless.

    python scripts/run_dc_scenarios.py --site london --dc-size 7.31 --workers 8

Defaults reproduce the study's own baseline case: London, the 2025 window the
cached grid and price data covers, hourly resampling (3.5x faster than
half-hourly for 0.14 % on cost and 0.32 % on carbon — see dc_inputs.resample),
and a 12-point Pareto sweep per configuration.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from optimisation import dc_architectures as A
from optimisation import dc_runner


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--site", default="london", help="site key from optimisation/sites.py")
    ap.add_argument("--dc-size", type=float, default=7.31, help="IT load, MW")
    ap.add_argument("--pue", type=float, default=1.0,
                    help="1.0 reproduces the Zhang foreground, whose figure is already facility-level")
    ap.add_argument("--start", default="2025-01-01")
    ap.add_argument("--end", default="2025-12-29")
    ap.add_argument("--horizon-years", type=float, default=25.0,
                    help="amortisation horizon; separate from the dispatch window")
    ap.add_argument("--resample", type=float, default=1.0,
                    help="hours per step; 0.5 for native half-hourly, 0 to disable")
    ap.add_argument("--points", type=int, default=12, help="Pareto sweep points")
    ap.add_argument("--cost-case", default="central", choices=("low", "central", "high"))
    ap.add_argument("--unserved", type=float, default=0.0,
                    help="permitted unserved fraction of annual demand")
    ap.add_argument("--only", nargs="*", type=int,
                    help="scenario numbers to run, e.g. --only 1 2 3")
    ap.add_argument("--workers", type=int, default=None,
                    help="parallel processes; 1 to run serially")
    ap.add_argument("--out", default=None)
    ap.add_argument("--refresh", action="store_true", help="ignore cached results")
    args = ap.parse_args(argv)

    scenarios = A.core_matrix()
    if args.only:
        wanted = set(args.only)
        scenarios = [s for s in scenarios if s.n in wanted]
        if not scenarios:
            ap.error(f"No scenarios match {sorted(wanted)}; matrix is 1..{len(A.core_matrix())}")

    print(f"{len(scenarios)} configuration(s) x {args.points + 1} solves = "
          f"{len(scenarios) * (args.points + 1)} LPs")
    print(f"site={args.site} size={args.dc_size} MW window={args.start}..{args.end} "
          f"step={args.resample or 0.5} h case={args.cost_case}\n")

    df = dc_runner.run_matrix(
        scenarios, site=args.site, start=args.start, end=args.end,
        size_mw_it=args.dc_size, pue=args.pue,
        resample_hours=(args.resample or None), points=args.points,
        cost_case=args.cost_case, horizon_years=args.horizon_years,
        unserved_fraction=args.unserved,
        out_root=Path(args.out) if args.out else None,
        workers=args.workers, refresh=args.refresh)

    if len(df):
        knee = df[df.point == "knee"].sort_values("gwp_t_per_year")
        print("\nKnee point, cleanest first")
        print(knee[["n", "label", "cost_m_GBP_per_year", "gwp_t_per_year",
                    "gwp_g_per_kWh"]].round(2).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
