#!/usr/bin/env python
"""Do the study's fixed choices change what gets built? Four sites, one change at a time (13 Nov 2026).

The ``present`` set of ``scripts/uk_sites.py`` (everything on the table that can be bought today)
fixes some choices: a PEM electrolyser, central costs, the central gas price, the bulk 28 bar tank.
This changes each one alone, at four sites and two grid levels, and solves the frontier:

    ely_ae             alkaline electrolyser
    ely_soec_gas       solid-oxide electrolyser, heat from a gas boiler
    ely_soec_elec      solid-oxide electrolyser, heat from an electric boiler
    cost_low/high      the low / high cost case (every asset's published range)
    gas_low/high       DESNZ's low / high gas price for 2026
    tank_200bar        the 200 bar steel cylinder in place of the bulk 28 bar vessel
    central            nothing changed, on the same frontier points, for the comparison

    python scripts/fixed_choice_checks.py
    python scripts/fixed_choice_checks.py --summary

Since 18 Nov 2026 (user) bought hydrogen comes on a steady contract, the model's new default
(``dc_architectures.Scenario.h2_supply``), and the checks run off-grid too; they write
``uk_sites_2025_checks_steady``. The just-in-time checks of 13 Nov stay in ``uk_sites_2025_checks``.
Bundles (``BUNDLES``) push several screened inputs at once, all against hydrogen or all for it, at
30 % and 50 % (the user's option B): pushes through ``trace.pushed``, the same as a sweep's.

Sites: Isle of Lewis (windiest, North Scotland), Lichfield (least windy, West Midlands), Essex coast
(windy, East England) and East Grinstead (typical South East); 25 MW and full grid. Frontier points:
``CHECK_FRACS``, fewer than the 26-site sets, so compare a variant with this script's own central.
Writes ``optimisation_outputs/uk_sites_2025_checks/<variant>/<level>/<site>/``; resumes.
"""
from __future__ import annotations

import argparse
import contextlib
import json
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import uk_sites as U  # noqa: E402
from optimisation import dc_architectures as A, dc_runner, trace as T  # noqa: E402

OUT = ROOT / "optimisation_outputs" / "uk_sites_2025_checks_steady"
SITES = (2, 15, 18, 23)
LEVELS = ("offgrid", "limited", "full")
CHECK_FRACS = (0.02, 0.06, 0.13, 0.25, 0.5)
VARIANTS = {          # name -> (Scenario fields, run_one keyword arguments)
    "central":       ({}, {}),
    "ely_ae":        ({"ely_tech": "AE operation"}, {}),
    "ely_soec_gas":  ({"ely_tech": "SOEC operation", "soec_heat": "gas_boiler"}, {}),
    "ely_soec_elec": ({"ely_tech": "SOEC operation", "soec_heat": "electric_boiler"}, {}),
    "cost_low":      ({}, {"cost_case": "low"}),
    "cost_high":     ({}, {"cost_case": "high"}),
    "gas_low":       ({}, {"gas_price_case": "low"}),
    "gas_high":      ({}, {"gas_price_case": "high"}),
    "tank_200bar":   ({"tank_design": "type1_200bar"}, {}),
}
# name -> (pushes as (recorded step key, factor), run_one keyword arguments). Filled from the
# screen of the steady-contract North Norfolk run (18 Nov 2026); each is also a variant.
BUNDLES: dict[str, tuple[list[tuple[str, float]], dict]] = {}
VARIANTS.update({k: ({}, kw) for k, (_, kw) in BUNDLES.items()})


def scenario(level: str, fields: dict) -> A.Scenario:
    flags = dict(grid=level != "offgrid", wind=True, offshore_wind=False, solar=True, battery=True,
                 electrolyser=True, tank=True, fuel_cell=True, buy_h2=True, buy_h2_2=False, gas_engine=True)
    base = dict(ely_tech="PEM operation", h2_colour="green", strategy="free")
    return A.Scenario(n=0, architecture="custom", label=f"fixed-choice check, {level}", assets=flags,
                      **{**base, **fields})


def folder(variant: str, level: str, n: int) -> Path:
    return OUT / variant / level / f"{n:02d}"


def run(variant: str, level: str, row):
    n, label, lat, lon, region, why, wind = row
    if any(folder(variant, level, n).rglob("pareto.parquet")):
        print(f"{variant} site {n} {level}: already done", flush=True)
        return
    fields, kwargs = VARIANTS[variant]
    pushes = BUNDLES[variant][0] if variant in BUNDLES else []
    site = U.site_for(n, label, lat, lon, region, level)
    t0 = time.time()
    print(f"[{time.strftime('%a %H:%M')}] {variant} site {n} {label} {level}", flush=True)
    with contextlib.ExitStack() as stack:
        hits = [(key, stack.enter_context(T.pushed(key, f))) for key, f in pushes]
        dc_runner.run_one(
            scenario(level, fields), site=site, start=U.START, end=U.END,
            connection_mode=None if level == "offgrid" else "cap", connection_solve="loose", size_mw_it=100.0,
            pue=None, resample_hours=1.0, points=5, cost_case=kwargs.get("cost_case", "central"),
            horizon_years=25.0, unserved_fraction=0.0, gas_price_case=kwargs.get("gas_price_case"),
            tank_leakage_per_hour=kwargs.get("tank_leakage_per_hour"), out_root=folder(variant, level, n),
            save_dispatch=False, refresh=False, progress=lambda t: None, eps_fracs=CHECK_FRACS)
    missed = [key for key, h in hits if not any(h)]
    if missed:
        raise ValueError(f"{variant}: no recorded step {missed} ran while building the coefficients")
    print(f"   done in {(time.time() - t0) / 60:.1f} min", flush=True)


def summary() -> pd.DataFrame:
    rows = []
    for p in OUT.rglob("pareto.parquet"):
        variant, level, site = p.parts[-5], p.parts[-4], int(p.parts[-3])
        for _, r in pd.read_parquet(p).iterrows():
            served = r.get("served_MWh_per_year") or float("nan")
            rows.append({"variant": variant, "level": level, "site": site, "point": r["point"],
                         "cost_GBP_per_MWh": r["cost_GBP_per_MWh"], "gwp_g_per_kWh": r["gwp_g_per_kWh"],
                         **{c: r.get(c, 0.0) for c in ("cap_wind", "cap_solar", "cap_batt_e", "cap_ely", "cap_tank",
                                                        "cap_fc", "cap_ge", "cap_grid")},
                         "fuel_cell_share_of_supply": r.get("cap_fc_MWh_per_year", 0.0) / served,
                         "gas_engine_share_of_supply": r.get("cap_ge_MWh_per_year", 0.0) / served})
    df = pd.DataFrame(rows)
    OUT.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT / "summary.csv", index=False)
    return df


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--variants", nargs="*", default=list(VARIANTS), choices=list(VARIANTS))
    ap.add_argument("--summary", action="store_true")
    # One variant, site and level per call lets the cluster run the 64 pieces side by side
    # (scripts/cluster/); --no-summary leaves summary.csv to one --summary call at the end.
    ap.add_argument("--sites", nargs="*", type=int, default=list(SITES), choices=list(SITES))
    ap.add_argument("--levels", nargs="*", default=list(LEVELS), choices=list(LEVELS))
    ap.add_argument("--no-summary", action="store_true", help="run only; leave summary.csv alone")
    a = ap.parse_args(argv)
    if not a.summary:
        rows = [r for r in U.SITES if r[0] in a.sites]
        for variant in a.variants:
            for level in a.levels:
                for row in rows:
                    try:
                        run(variant, level, row)
                    except Exception as exc:  # noqa: BLE001 - one run's failure must not stop the night
                        print(f"   FAILED {variant} site {row[0]} {level}: {type(exc).__name__}: {exc}", flush=True)
    if a.no_summary:
        return
    s = summary()
    print(f"summary: {len(s)} rows -> {OUT / 'summary.csv'}", flush=True)


if __name__ == "__main__":
    main()
