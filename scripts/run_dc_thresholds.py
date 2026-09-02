#!/usr/bin/env python
"""Find the input prices at which hydrogen enters the build.

    python scripts/run_dc_thresholds.py --from-run optimisation_outputs/dc_runs/<site>/<scenario>
    python scripts/run_dc_thresholds.py --only 21
    python scripts/run_dc_thresholds.py --only 16 19 --knobs h2_price
    python scripts/run_dc_thresholds.py --only 21 --knobs batt_capex --gwp-limit 6.0e6

--from-run is the form to prefer. A threshold only means something against a
particular answer, and inheriting that answer's own site, window, size and cost
case is what stops a 7 MW London threshold being quoted against a 100 MW
Highland front.

Every grid-connected configuration in the study builds no hydrogen at all, at
both ends of its Pareto front. This asks the follow-on question: how far would
one input have to move before it did? One knob at a time, by bisection on a
re-solve — see optimisation/thresholds.py for why the solver's own reduced costs
cannot answer it.

Defaults follow run_dc_scenarios.py, so a threshold and a front are always
computed against the same site, window and resolution.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from optimisation import dc_architectures as A
from optimisation import sites, thresholds as T


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lat", type=float, help="site latitude (GB)")
    ap.add_argument("--lon", type=float, help="site longitude (GB)")
    ap.add_argument("--site", default=None,
                    help=f"preset shortcut instead of --lat/--lon: "
                         f"{', '.join(sites.PRESETS)}")
    ap.add_argument("--connection-limit", type=float, default=None)
    ap.add_argument("--dc-size", type=float, default=7.31, help="IT load, MW")
    ap.add_argument("--pue", type=float, default=1.0)
    ap.add_argument("--start", default="2025-01-01")
    ap.add_argument("--end", default="2025-12-29")
    ap.add_argument("--horizon-years", type=float, default=25.0)
    ap.add_argument("--resample", type=float, default=1.0,
                    help="hours per step; 0 to disable, 2 for a fast look")
    ap.add_argument("--cost-case", default="central", choices=("low", "central", "high"))
    ap.add_argument("--unserved", type=float, default=0.0)
    ap.add_argument("--from-run", default=None, metavar="FOLDER",
                    help="a solved scenario folder under optimisation_outputs/"
                         "dc_runs/; takes its scenario, site, window, size and "
                         "cost case from that run's config.json. Overrides --only "
                         "and the site/size/window flags.")
    ap.add_argument("--only", nargs="*", type=int,
                    help="scenario numbers from the core matrix, e.g. --only 21")
    ap.add_argument("--knobs", nargs="*", default=None,
                    choices=sorted(T.KNOBS),
                    help="inputs to find a threshold in; with --from-run the "
                         "default is every knob that configuration can answer")
    ap.add_argument("--h2-colour", default=None,
                    help="price a colour so an architecture that MAY buy hydrogen "
                         "does; supplies the carbon intensity while --knobs "
                         "h2_price sweeps the price")
    ap.add_argument("--gwp-limit", type=float, default=None,
                    help="cap annual kg CO2e, so the question becomes 'at this "
                         "carbon target, when does hydrogen enter'")
    ap.add_argument("--entry-share", type=float, default=T.ENTRY_SHARE,
                    help="share of annual load the fuel cell must carry to count "
                         "as hydrogen entering")
    ap.add_argument("--rel-tol", type=float, default=T.REL_TOL)
    ap.add_argument("--out", default=None)
    ap.add_argument("--refresh", action="store_true", help="ignore cached thresholds")
    ap.add_argument("--stale-ok", action="store_true",
                    help="run even though the coefficients or the model have "
                         "moved since --from-run's front was solved")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)
    if not args.from_run and not args.only:
        ap.error("give --from-run FOLDER, or --only with scenario numbers")

    shared = dict(gwp_limit_kg_per_year=args.gwp_limit,
                  target_share=args.entry_share, rel_tol=args.rel_tol,
                  out_root=(Path(args.out) if args.out else None),
                  refresh=args.refresh)
    log = (lambda s: None) if args.quiet else (lambda s: print("   ", s, flush=True))

    if args.from_run:
        inherited = T.from_run(args.from_run)
        if inherited["stale"] and not args.stale_ok:
            ap.error(
                "that front was solved before "
                + ", ".join(inherited["stale_keys"])
                + " changed. A threshold computed now would annotate a result "
                  "that no longer exists — re-run the front, or pass --stale-ok.")
        if inherited["stale"]:
            print("  ! stale: " + ", ".join(inherited["stale_keys"])
                  + " changed since this front was solved.\n", flush=True)
        jobs = [(inherited["scenario"], {**inherited["kwargs"], **shared})]
    else:
        site = (sites.get(args.site) if args.site
                else sites.get((args.lat, args.lon)) if args.lat is not None
                else sites.get(sites.DEFAULT_PRESET))
        if args.connection_limit is not None:
            from dataclasses import replace
            site = replace(site, connection_limit_mw=args.connection_limit)
        chosen = [s for s in A.core_matrix() if s.n in set(args.only)]
        if not chosen:
            ap.error(f"no scenario matches --only {args.only}")
        kw = dict(site=site, start=args.start, end=args.end,
                  size_mw_it=args.dc_size, pue=args.pue,
                  resample_hours=(args.resample or None), cost_case=args.cost_case,
                  horizon_years=args.horizon_years, unserved_fraction=args.unserved,
                  h2_colour=args.h2_colour, **shared)
        jobs = [(scen, kw) for scen in chosen]

    results = []
    for scen, kw in jobs:
        knobs = tuple(args.knobs) if args.knobs else tuple(T.applicable_knobs(scen))
        head = f"{scen.n:02d}  {scen.label}" if scen.n else scen.label
        print(f"\n{'=' * 78}\n{head}\n{'=' * 78}", flush=True)
        rs = T.sweep(scen, knobs, progress=log, notice=log, **kw)
        for r in rs:
            print("  ", T.describe(r), flush=True)
        results += rs

    print(f"\n{'=' * 78}\nTHRESHOLDS\n{'=' * 78}")
    print(T.table(results).to_string(index=False))
    print(f"\nWritten to {T.OUT_ROOT}")
    return results


if __name__ == "__main__":
    main()
