#!/usr/bin/env python
"""At what bought green hydrogen price does the cheapest design use hydrogen? Site by site (13 Nov 2026).

For each UK study site (``scripts/uk_sites.py``) and grid level, with everything on the table
(``--set present``'s kit: wind, solar, battery, PEM electrolyser, tank, fuel cell, bought green
hydrogen, gas engines) and once more without the gas engines, ``optimisation/thresholds.find``
bisects the bought hydrogen price on the min-cost design until the fuel cell serves 1 % of supply
(``thresholds.ENTRY_SHARE``). Today's delivered green price is about £10.6/kg (2026 pounds).

    python scripts/breakeven_sites.py --rig                 # every site, 4-hour steps (testing: not quotable)
    python scripts/breakeven_sites.py --sites 2 15 18 23 --levels limited full     # hourly
    python scripts/breakeven_sites.py --summary [--rig]     # only rebuild the table

Status per search: ``found`` (the price is ``threshold_GBP_per_kg``); ``already_viable`` (hydrogen is
used at today's price already: the search only looks downward, so no price is reported);
``not_found`` (not used even at the bracket's floor, £0.05/kg). Each search writes its own folder
under ``optimisation_outputs/uk_sites_2025_breakeven/<rig|hourly>/``; a finished one is kept, so the
script resumes. The price swept is the price only: the hydrogen's carbon stays green's.
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
from optimisation import dc_architectures as A, thresholds as TH  # noqa: E402

OUT = ROOT / "optimisation_outputs" / "uk_sites_2025_breakeven"
GAS = (True, False)


def scenario(level: str, gas: bool) -> A.Scenario:
    flags = dict(grid=level != "offgrid", wind=True, offshore_wind=False, solar=True, battery=True,
                 electrolyser=True, tank=True, fuel_cell=True, buy_h2=True, buy_h2_2=False, gas_engine=gas)
    return A.Scenario(n=0, architecture="custom", label=f"break-even, {level}, {'gas' if gas else 'no gas'}",
                      assets=flags, ely_tech="PEM operation", h2_colour="green", strategy="free")


def folder(kind: str, level: str, n: int, gas: bool) -> Path:
    return OUT / kind / level / f"{n:02d}_{'gas' if gas else 'nogas'}"


def run(kind: str, level: str, row, gas: bool) -> dict:
    n, label, lat, lon, region, why, wind = row
    out = folder(kind, level, n, gas)
    done = out / "result.json"
    if done.exists():
        print(f"site {n} {level} {'gas' if gas else 'no gas'}: already done", flush=True)
        return json.loads(done.read_text(encoding="utf-8"))
    site = U.site_for(n, label, lat, lon, region, level)
    t0 = time.time()
    print(f"[{time.strftime('%a %H:%M')}] site {n} {label} {level} {'gas' if gas else 'no gas'} ({kind})", flush=True)
    r = TH.find(scenario(level, gas), "h2_price", site=site, start=U.START, end=U.END, size_mw_it=100.0,
                resample_hours=4.0 if kind == "rig" else 1.0,
                connection_mode=None if level == "offgrid" else "cap", out_root=out, refresh=False)
    rec = {"site": n, "place": label, "region": region, "why": why, "level": level, "gas_engines": gas,
           "status": r.get("status"), "threshold_GBP_per_kg": r.get("threshold"),
           "solves": r.get("solves"), "minutes": round((time.time() - t0) / 60.0, 1), "kind": kind}
    out.mkdir(parents=True, exist_ok=True)
    done.write_text(json.dumps(rec, indent=1, default=str), encoding="utf-8")
    print(f"   {rec['status']} {rec['threshold_GBP_per_kg']} in {rec['minutes']} min", flush=True)
    return rec


def summary(kind: str) -> pd.DataFrame:
    rows = [json.loads(p.read_text(encoding="utf-8")) for p in (OUT / kind).rglob("result.json")]
    df = pd.DataFrame(rows).sort_values(["site", "level", "gas_engines"]) if rows else pd.DataFrame()
    (OUT / kind).mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT / kind / "summary.csv", index=False)
    return df


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--rig", action="store_true", help="4-hour steps (testing, not quotable)")
    ap.add_argument("--levels", nargs="*", default=list(U.LEVELS), choices=U.LEVELS)
    ap.add_argument("--sites", nargs="*", type=int, default=None)
    ap.add_argument("--summary", action="store_true")
    # One site, level and engine choice per call lets the cluster run the searches side by side
    # (scripts/cluster/); --no-summary leaves summary.csv to one --summary call at the end.
    ap.add_argument("--gas", choices=("both", "with", "without"), default="both",
                    help="gas engines on offer: both runs (default), only with, or only without")
    ap.add_argument("--no-summary", action="store_true", help="run only; leave summary.csv alone")
    a = ap.parse_args(argv)
    kind = "rig" if a.rig else "hourly"
    gases = {"both": GAS, "with": (True,), "without": (False,)}[a.gas]
    if not a.summary:
        for level in a.levels:
            for row in U.SITES:
                if a.sites and row[0] not in a.sites:
                    continue
                for gas in gases:
                    try:
                        run(kind, level, row, gas)
                    except Exception as exc:  # noqa: BLE001 - one search's failure must not stop the night
                        print(f"   FAILED site {row[0]} {level} gas={gas}: {type(exc).__name__}: {exc}", flush=True)
    if a.no_summary:
        return
    s = summary(kind)
    print(f"summary: {len(s)} rows -> {OUT / kind / 'summary.csv'}", flush=True)


if __name__ == "__main__":
    main()
