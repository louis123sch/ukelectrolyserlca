#!/usr/bin/env python
"""Sign-off steps 4 and 5 (docs/TESTING.md) at East Grinstead, one case per cluster piece (20 Nov 2026).

    python scripts/cluster/signoff_site.py cost islanded_h2      # step 4: cost cut-off, rule 3
    python scripts/cluster/signoff_site.py cost norfolk_grid
    python scripts/cluster/signoff_site.py carbon islanded_h2    # step 5: carbon cut-off, rule 3
    python scripts/cluster/signoff_site.py carbon norfolk_grid_green

The same sweeps as ``python -m optimisation.sensitivity cost_cutoff|cutoff --hours=1``, moved from
North Norfolk to East Grinstead (site 23; user, 19 Nov 2026: test at the typical site), hourly.
Each case keeps its own settings (buying none since 20 Nov 2026), renamed eastgrinstead_*.
Writes optimisation_outputs/sensitivity_{cost_cutoff,cutoff}_eastgrinstead_*.csv. The judges
(scripts/cutoff_rule3.py and the cost check) read North Norfolk's names and need the new ones
passed in when these come home.
"""
from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fixcheck_site import site  # noqa: E402  (East Grinstead, region 14, 2 km route)

RULES = {"cost": ("cost_cutoff", {"cost_cutoff": "upper"}), "carbon": ("cutoff", {"cutoff": "upper"})}
CASES = {"cost": ("islanded_h2", "norfolk_grid"), "carbon": ("islanded_h2", "norfolk_grid_green")}


def main(rule: str, case_name: str) -> None:
    from optimisation import sensitivity as S
    if case_name not in CASES[rule]:
        raise SystemExit(f"{rule}: case must be one of {CASES[rule]}")
    prefix, variant = RULES[rule]
    name = "eastgrinstead_" + case_name.replace("norfolk_", "")
    case = replace(S.CASES[case_name], name=name, site=site(), resample_hours=1.0)
    S.run(case, [{}, variant], name=f"{prefix}_{name}", list_choice="fixed")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
