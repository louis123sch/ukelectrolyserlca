#!/usr/bin/env python
"""The 19 Nov 2026 before/after run (docs/CODE_CHECK_FIX_PLAN.md step 5) at East Grinstead.

    python scripts/cluster/fixcheck_site.py refcases        # the two reference cases, hourly
    python scripts/cluster/fixcheck_site.py scenario 7      # one configuration of the scenario list

The same work the laptop run did (scripts/solver_compare.py solve, then
scripts/run_dc_scenarios.py with its defaults), moved from North Norfolk to East
Grinstead, the 26-site study's typical site (site 23; user, 19 Nov 2026: test at the most
representative site from now on). The cable route is fixed at 2 km and the region at 14,
as in scripts/uk_sites.py, so no lookup needs the internet. Uses only what both the code
before the fixes (c9cc1dc) and after has, so fixcheck_setup.sh copies it into both.
"""
from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from optimisation import dc_architectures as A, dc_runner, sites  # noqa: E402

LAT, LON, REGION, ROUTE_KM = 51.2, 0.0, 14, 2.0      # uk_sites.SITES row 23


def site():
    return sites.resolve(LAT, LON, name="East Grinstead", carbon_api_region=REGION,
                         connection_route_km=ROUTE_KM)


def refcases():
    from optimisation import sensitivity as S
    s = site()
    for c in ("islanded_h2", "norfolk_grid"):
        name = c.replace("norfolk_", "eastgrinstead_")
        case = replace(S.CASES[c], name=name, site=s, resample_hours=1.0)
        S.run(case, [{}], name=f"fixcheck_{name}", list_choice="fixed")


def scenario(n: int):
    chosen = [s for s in A.core_matrix() if s.n == n]
    if not chosen:
        print(f"configuration {n} is not in this code's scenario list")
        return
    dc_runner.run_matrix(chosen, site=site(), workers=1,
                         out_root=ROOT / "optimisation_outputs" / "dc_runs" / "fixcheck_east_grinstead")


if __name__ == "__main__":
    if sys.argv[1] == "refcases":
        refcases()
    else:
        scenario(int(sys.argv[2]))
