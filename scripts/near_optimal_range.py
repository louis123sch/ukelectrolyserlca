#!/usr/bin/env python
"""The range of battery and hydrogen sizes within 1 % of the lowest carbon (supervisor, 23 Nov 2026).

At each site and grid level, on the robustness checks' central setting (scripts/fixed_choice_checks.py:
everything on the table, PEM, green hydrogen priced but none bought, gas engines allowed), this finds
the lowest-carbon design and then, holding carbon within ``--slack`` of it, the smallest and largest
battery (energy and power), electrolyser, tank and fuel cell (optimisation/near_optimal.py).

    python scripts/near_optimal_range.py --sites 23 --levels offgrid limited full
    python scripts/near_optimal_range.py --sites 23 --levels full --vars cap_tank
    python scripts/near_optimal_range.py --summary

``--vars`` limits a piece to some sizes (the cluster runs one size a piece, for short jobs that start
sooner; each piece re-solves the lowest-carbon design first, so pieces are independent).

Writes optimisation_outputs/near_optimal_2025/<level>/<site>/range.json; resumes (a finished piece
is skipped). The run settings are the robustness checks' (hourly, 2025, 100 MW of IT, the "cap"
connection mode at the loose switch gap), so its lowest-carbon design is theirs.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import uk_sites as U  # noqa: E402
import fixed_choice_checks as F  # noqa: E402
from optimisation import dc_model as M, dc_runner, near_optimal as NO  # noqa: E402

OUT = ROOT / "optimisation_outputs" / "near_optimal_2025"


def piece(n: int, level: str, slack: float, variables=None) -> Path:
    name = "range.json" if not variables else f"range_{'_'.join(variables)}.json"
    path = OUT / level / f"{n:02d}" / name
    if path.exists():
        print(f"site {n} {level} {name}: already done", flush=True)
        return path
    row = next(r for r in U.SITES if r[0] == n)
    _, label, lat, lon, region, _why, _wind = row
    site = U.site_for(n, label, lat, lon, region, level)
    t0 = time.time()
    print(f"[{time.strftime('%a %H:%M')}] site {n} {label} {level}, slack {slack:.1%}", flush=True)
    series, meta, tech, assets = dc_runner.build_inputs(
        F.scenario(level, {}), site=site, start=U.START, end=U.END, size_mw_it=100.0, pue=None,
        resample_hours=1.0, connection_mode=None if level == "offgrid" else "cap",
        cost_case="central", horizon_years=25.0)
    res = NO.ranges(series, assets, tech, slack=slack, mip_rel_gap=M.LOOSE_MIP_REL_GAP,
                    variables=tuple(variables) if variables else NO.DEFAULT_VARS,
                    progress=lambda t: print(f"   {t}", flush=True))
    res.update({"site": n, "label": label, "level": level, "minutes": (time.time() - t0) / 60})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(res, indent=2, default=float), encoding="utf-8")
    print(f"   done in {res['minutes']:.1f} min", flush=True)
    return path


def summary() -> pd.DataFrame:
    rows = []
    for p in sorted(OUT.rglob("range*.json")):
        r = json.loads(p.read_text(encoding="utf-8"))
        for var, d in r["ranges"].items():
            rows.append({"site": r["site"], "level": r["level"], "size": var, **d})
    df = pd.DataFrame(rows)
    if not df.empty:
        print(df.to_string(index=False, float_format=lambda x: f"{x:,.2f}"))
    return df


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--sites", nargs="*", type=int, default=[23])
    ap.add_argument("--levels", nargs="*", default=list(U.LEVELS), choices=U.LEVELS)
    ap.add_argument("--slack", type=float, default=0.01)
    ap.add_argument("--vars", nargs="*", choices=NO.ALL_SIZES, default=None)
    ap.add_argument("--summary", action="store_true")
    a = ap.parse_args()
    if a.summary:
        summary()
        return
    for n in a.sites:
        for level in a.levels:
            piece(n, level, a.slack, a.vars)


if __name__ == "__main__":
    main()
