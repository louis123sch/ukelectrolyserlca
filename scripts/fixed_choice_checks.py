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

``--supply`` (20 Nov 2026) sets how hydrogen may be bought: ``none``, the model's central case and
the default here since 20 Nov; ``jit`` (pipeline stand-in) or ``steady`` (truck contract). Each
writes ``uk_sites_2025_checks_<supply>``: the steady checks of 18 Nov (East Grinstead) are in
``uk_sites_2025_checks_steady``; the just-in-time checks of 13 Nov stay in ``uk_sites_2025_checks``.
With ``none`` the two variants that only act on bought hydrogen (its price, the seller's grid
share) are skipped. Since 20 Nov the pushes also cover the electrolyser stack's price share, the
fuel cell's maintenance and the off-grid spare-power shares (load, wind), as sensitivity.SHAKY_KNOBS
does; the spare-power ones only act off grid. The bundles are as on 18 Nov.
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

SUPPLY = "none"      # set by --supply
OUT = ROOT / "optimisation_outputs" / f"uk_sites_2025_checks_{SUPPLY}"
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
    # 24 Nov 2026: the whole import price +25 %, about the gap to DESNZ's survey of what
    # suppliers charge users over 150 GWh a year (validation write-up, "Grid bill").
    # Grid-connected levels only: an islanded site buys no grid power.
    "grid_price_x1.25": ({}, {"grid_price_scale": 1.25}),
}

# --- the screened inputs, one at a time (user, 18 Nov 2026: robustness at four sites) ----------
# Everything sensitivity.SHAKY_KNOBS pushes (the 10 Nov screen's shortlist, run at North Norfolk
# until now) plus the tank's installed cost, which carries a tank about five times bigger under a
# steady contract (one supplier's quote, Element Energy 2018). Wider than a fresh screen would
# pick, so nothing it would add is missed. x0.5 / x1.5 on our own figure; published ranges where
# they exist (percentage tests only, user 11 Nov 2026). Run keyword arguments go to run_one:
# "tech" to build_tech, "pushes" through trace.pushed.
PUSHED = {            # short name -> recorded step key
    "fc_capex":     "cost.fuel_cell.capex_per_kW",
    "batt_carbon":  "battery.energy_per_usable_kWh",
    "ely_cost":     "coefficient.cost_ely",
    "h2_price":     "cost.bought_h2.green.delivered",
    "tank_carbon":  "coefficient.gwp_tank",
    "tank_cost":    "cost.h2_tank.capex_per_kg",
    "wind_parts":   "onshore_wind.parts_fraction",
    "stack_carbon": "coefficient.gwp_fc_stack_per_mw",
    "batt_fade":    "battery.capacity_fade_at_end_of_life",
    "ge_carbon":    "coefficient.gwp_ge_per_mw",
    # since 20 Nov 2026 (sensitivity.SHAKY_KNOBS): comparison fixes and REopt fixes
    "stack_share":  "cost.electrolyser.stack_cost_fraction",
    "fc_maint":     "cost.fuel_cell.maintenance_per_kW_year",
    "reserve_load": "reserve.load_fraction",          # off grid only
    "reserve_wind": "reserve.wind_fraction",          # off grid only
}
# Variants that act only on bought hydrogen: skipped when none is bought.
BUYING_ONLY = {"h2_price_x0.5", "h2_price_x1.5",
               "green_h2_grid_share_against_h2", "green_h2_grid_share_for_h2"}
# Variants that act only with no grid: the piece lists run them off grid only.
OFF_GRID_ONLY = {f"{n}_x{f:g}" for n in ("reserve_load", "reserve_wind") for f in (0.5, 1.5)}
for _name, _key in PUSHED.items():
    for _f in (0.5, 1.5):
        VARIANTS[f"{_name}_x{_f:g}"] = ({}, {"pushes": [(_key, _f)]})


def _centrals() -> dict:
    """Central values of the inputs swept on a range, as build_tech takes them."""
    from optimisation import battery, fuel_cell, h2_prices, h2_storage
    return {"fc_stack_calendar_years": fuel_cell.STACK_CALENDAR_LIFETIME_YEARS,
            "fc_stack_duty_hours": float(fuel_cell.decompose()["stack_lifetime_hours"]),
            "tank_leakage_per_hour": h2_storage.LEAKAGE_FRAC_PER_HOUR,
            "green_h2_grid_share": h2_prices.GREEN_H2_GRID_SHARE,
            "batt_standing_loss_per_hour": battery.STANDING_LOSS_PER_HOUR}


# Range ends, as sensitivity.SHAKY_KNOBS has them: (end that hurts hydrogen, end that helps it).
RANGES = {
    "fc_stack_calendar_years": (5.0, 15.0),
    "fc_stack_duty_hours": (20_000.0, 40_000.0),
    "tank_leakage_per_hour": (0.01 / 100, 0.0),
    "green_h2_grid_share": (1.0, 0.0),          # the seller on the grid: more carbon per kg bought
    "batt_standing_loss_per_hour": (0.0, None),  # None: twice the central (filled below)
}
RUN_ARGS = ("tank_leakage_per_hour", "green_h2_grid_share", "batt_standing_loss_per_hour")
for _name, (_lo, _hi) in RANGES.items():
    for _end, _v in (("against", _lo), ("for", _hi)):
        VARIANTS[f"{_name}_{_end}_h2"] = ({}, {"range": (_name, _end)})
VARIANTS["batt_tx_x_eff_1"] = ({}, {"tech": {"batt_tx_x_eff": 1.0}})
VARIANTS["fc_tx_x_eff_0.5"] = ({}, {"tech": {"fc_tx_x_eff": 0.5}})

# --- bundles: every one of them at once, all against hydrogen or all for it (option B) ----------
# The pushed inputs move by the bundle's share (30 % or 50 %) in the direction that hurts (or
# helps) hydrogen against its rivals; the ranged ones go that share of the way to the range's end
# over its x0.5 distance (so the 50 % bundle reaches the ends). Hurts hydrogen: dearer fuel cell,
# electrolyser, tank and bought hydrogen, more carbon in the tank and stacks; and its rivals helped:
# less battery carbon and fade, less gas engine carbon. Wind parts are left out: wind serves both.
AGAINST_UP = ("fc_capex", "ely_cost", "h2_price", "tank_carbon", "tank_cost", "stack_carbon")
AGAINST_DOWN = ("batt_carbon", "batt_fade", "ge_carbon")
for _share in (0.3, 0.5):
    for _end, _sign in (("against", 1.0), ("for", -1.0)):
        pushes = ([(PUSHED[n], 1.0 + _sign * _share) for n in AGAINST_UP]
                  + [(PUSHED[n], 1.0 - _sign * _share) for n in AGAINST_DOWN])
        VARIANTS[f"bundle_{_end}_h2_{round(_share * 100)}"] = ({}, {"pushes": pushes, "bundle": (_end, _share)})


def run_args(kwargs: dict) -> tuple[dict, dict, list]:
    """A variant's (run_one arguments, build_tech overrides, pushes), ranges resolved."""
    run, tech, pushes = {}, dict(kwargs.get("tech", {})), list(kwargs.get("pushes", []))
    for k in ("cost_case", "gas_price_case", "grid_price_scale"):
        if k in kwargs:
            run[k] = kwargs[k]
    picks = []
    if "range" in kwargs:
        picks = [(kwargs["range"][0], kwargs["range"][1], 1.0)]
    elif "bundle" in kwargs:
        end, share = kwargs["bundle"]
        picks = [(name, end, share / 0.5) for name in RANGES]
    if picks:
        c = _centrals()
        for name, end, frac in picks:
            lo, hi = RANGES[name]
            if hi is None:
                hi = 2.0 * c[name]
            target = lo if end == "against" else hi
            value = c[name] + frac * (target - c[name])
            (run if name in RUN_ARGS else tech)[name] = value
    return run, tech, pushes


def scenario(level: str, fields: dict) -> A.Scenario:
    flags = dict(grid=level != "offgrid", wind=True, solar=True, battery=True,
                 electrolyser=True, tank=True, fuel_cell=True, buy_h2=True, buy_h2_2=False, gas_engine=True)
    base = dict(ely_tech="PEM operation", h2_colour="green", strategy="free", h2_supply=SUPPLY)
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
    run_kw, tech, pushes = run_args(kwargs)
    site = U.site_for(n, label, lat, lon, region, level)
    t0 = time.time()
    print(f"[{time.strftime('%a %H:%M')}] {variant} site {n} {label} {level}", flush=True)
    with contextlib.ExitStack() as stack:
        hits = [(key, stack.enter_context(T.pushed(key, f))) for key, f in pushes]
        dc_runner.run_one(
            scenario(level, fields), site=site, start=U.START, end=U.END,
            connection_mode=None if level == "offgrid" else "cap", connection_solve="loose", size_mw_it=100.0,
            pue=None, resample_hours=1.0, points=5, cost_case=run_kw.get("cost_case", "central"),
            horizon_years=25.0, unserved_fraction=0.0, gas_price_case=run_kw.get("gas_price_case"),
            tank_leakage_per_hour=run_kw.get("tank_leakage_per_hour"),
            green_h2_grid_share=run_kw.get("green_h2_grid_share"),
            batt_standing_loss_per_hour=run_kw.get("batt_standing_loss_per_hour"),
            tech_overrides=tech or None, grid_price_scale=run_kw.get("grid_price_scale"),
            out_root=folder(variant, level, n),
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
    ap.add_argument("--supply", default="none", choices=A.H2_SUPPLIES,
                    help="how hydrogen may be bought (default none, the model's central case)")
    a = ap.parse_args(argv)
    global SUPPLY, OUT
    SUPPLY = a.supply
    OUT = ROOT / "optimisation_outputs" / f"uk_sites_2025_checks_{SUPPLY}"
    if not a.summary:
        rows = [r for r in U.SITES if r[0] in a.sites]
        for variant in a.variants:
            if SUPPLY == "none" and variant in BUYING_ONLY:
                print(f"{variant}: skipped, no hydrogen is bought", flush=True)
                continue
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
