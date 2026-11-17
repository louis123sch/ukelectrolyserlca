#!/usr/bin/env python
"""Under what conditions is hydrogen used? The 26-site UK run (12 Nov 2026).

Each site is designed from scratch on 2025 weather and prices at three grid levels,
every point from lowest cost to lowest carbon, with everything else held the same:

  off-grid   no connection; bought hydrogen still on offer (trucked in)
  limited    a connection of at most 25 MW (about a sixth of peak; North Norfolk's room)
  full       a connection up to the 1.43x ceiling on the load

At both grid levels the optimiser chooses among every price list the site could be on
(cap mode), on a cable route fixed at 2 km (``Site.connection_route_km``), so sites differ
only in what a developer cannot change: wind, sun, grid carbon and grid prices.

Sites: the windiest and least windy point in each Carbon Intensity region (one each for
the West and East Midlands, where wind barely varies), and the sunniest and least sunny,
picked from the 2025 Renewables.ninja map of 76 wind and 19 solar points (gb_layers,
11 Nov 2026). London is left out (user). Gross wind, nearest solar point.

    python scripts/uk_sites.py                      # every site, every level
    python scripts/uk_sites.py --levels offgrid limited --sites 23
    python scripts/uk_sites.py --summary            # only rebuild the summary table
    python scripts/uk_sites.py --set present        # 13 Nov: everything on the table, green only
    python scripts/uk_sites.py --set blue           # 13 Nov: the same with blue on offer too (a what-if)

Sets (13 Nov 2026). ``base`` is the 12 Nov study as run (no gas engines, green, 5 even points).
``present`` puts everything on the table that can be bought today: the gas engines added,
bought hydrogen green only (no UK blue plant is running and no CO2 store is open; grey is
beaten by the engines on cost and carbon; turquoise is not for sale). ``blue`` is the what-if
"blue hydrogen becomes available" (from about 2028 on current plans), priced at the
government's modelled cost, as a second contract beside green. Both take their frontier
points packed at the low-carbon end (``EPS_FRACS``), where hydrogen hands over to other kit.
(User, 17 Nov 2026: back to the 12 packed points after a day on 6 even. The "five times slower"
was against the 12 Nov run without gas engines; with today's options 12 packed took about
16 min an off-grid site on the laptop against about 21 for 6 even. The 6-even results of
16-17 Nov are kept in ``uk_sites_2025_present_even6``.)
Each set writes its own folder, so the 12 Nov results are left as they are.
``--no-summary`` skips rewriting summary.csv, for pieces run side by side on the cluster
(scripts/cluster/); run ``--summary`` once when they are all in.

Writes optimisation_outputs/uk_sites_2025/<level>/<site>/... (one dc_runner folder per
run, dispatch saved) and optimisation_outputs/uk_sites_2025/summary.csv. A run whose
folder already holds a front is skipped, so the script resumes.
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
from optimisation import dc_architectures as A, dc_runner, sites  # noqa: E402

SETS = {
    "base":    {"gas": False, "blue": False, "out": "uk_sites_2025"},
    "present": {"gas": True,  "blue": False, "out": "uk_sites_2025_present"},
    "blue":    {"gas": True,  "blue": True,  "out": "uk_sites_2025_blue"},
}
OUT = ROOT / "optimisation_outputs" / SETS["base"]["out"]
SET = "base"
# Fractions of the carbon span above the lowest-carbon point (dc_pareto.front eps_fracs): a dozen
# points, most of them in the first fifth, where the North Norfolk rig showed hydrogen giving way
# to gas between 35 and ~52 g/kWh on a 35-169 g span.
EPS_FRACS = (0.01, 0.02, 0.04, 0.06, 0.09, 0.13, 0.18, 0.25, 0.35, 0.5, 0.7, 0.85)
ENTRY_SHARE = 0.01          # hydrogen "used" when the fuel cell serves 1 % of supply (thresholds.py's)
ROUTE_KM = 2.0
LIMITED_MW = 25.0
START, END = "2025-01-01", "2025-12-29"

# (number, label, lat, lon, region from the map, why it is in, map wind gross)
SITES = [
    (1, "Perthshire Highlands", 56.7, -4.0, 1, "North Scotland, least windy", 0.344),
    (2, "Isle of Lewis", 58.2, -6.4, 1, "North Scotland, windiest", 0.545),
    (3, "Moffat", 55.2, -3.2, 2, "South Scotland, least windy", 0.383),
    (4, "Ayrshire coast", 55.7, -4.8, 2, "South Scotland, windiest", 0.491),
    (5, "Blackburn", 53.7, -2.4, 3, "North West England, least windy", 0.358),
    (6, "Cumbrian coast", 54.2, -3.2, 3, "North West England, windiest", 0.501),
    (7, "Thirsk", 54.2, -1.6, 4, "North East England, least windy", 0.365),
    (8, "Northumberland coast", 55.2, -1.6, 4, "North East England, windiest", 0.518),
    (9, "Wakefield", 53.7, -1.6, 5, "Yorkshire, least windy", 0.349),
    (10, "Holderness coast", 53.7, 0.0, 5, "Yorkshire, windiest", 0.416),
    (11, "Welshpool", 52.7, -3.2, 6, "North Wales, least windy", 0.333),
    (12, "Bangor", 53.2, -4.0, 6, "North Wales, windiest", 0.414),
    (13, "Builth Wells", 52.2, -3.2, 7, "South Wales, least windy", 0.341),
    (14, "Pembrokeshire", 51.7, -4.8, 7, "South Wales, windiest", 0.538),
    (15, "Lichfield", 52.7, -1.6, 8, "West Midlands, one site", 0.335),
    (16, "Northampton", 52.2, -0.8, 9, "East Midlands, one site", 0.342),
    (17, "Chilterns", 51.7, -0.8, 10, "East England, least windy", 0.347),
    (18, "Essex coast", 51.7, 0.8, 10, "East England, windiest", 0.477),
    (19, "Stroud", 51.7, -2.4, 11, "South West England, least windy", 0.340),
    (20, "East Devon coast", 50.7, -3.2, 11, "South West England, windiest", 0.508),
    (21, "Witney", 51.7, -1.6, 12, "South England, least windy", 0.344),
    (22, "Dorset coast", 50.7, -2.4, 12, "South England, windiest", 0.520),
    (23, "East Grinstead", 51.2, 0.0, 14, "South East England, least windy; typical core", 0.389),
    (24, "Ashford", 51.2, 0.8, 14, "South East England, windiest", 0.427),
    (25, "West Highlands", 56.7, -5.8, 1, "least sunny", None),
    (26, "Isle of Wight", 50.7, -1.3, 12, "sunniest", None),
]
LEVELS = ("offgrid", "limited", "full")


def scenario(level: str) -> A.Scenario:
    cfg = SETS[SET]
    flags = dict(grid=level != "offgrid", wind=True, offshore_wind=False, solar=True, battery=True,
                 electrolyser=True, tank=True, fuel_cell=True, buy_h2=True, buy_h2_2=cfg["blue"])
    if cfg["gas"]:
        flags["gas_engine"] = True
    return A.Scenario(n=0, architecture="custom", label=f"UK site study, {level}, {SET}",
                      assets=flags, ely_tech="PEM operation", h2_colour="green",
                      h2_colour_2="blue" if cfg["blue"] else None, strategy="free")


def site_for(n, label, lat, lon, region, level):
    kw = dict(name=label, connection_route_km=ROUTE_KM)
    if level == "limited":
        kw["connection_limit_mw"] = LIMITED_MW
    try:
        return sites.resolve(lat, lon, **kw)
    except Exception as exc:  # noqa: BLE001 - a point the postcode lookup cannot place
        print(f"   site {n}: lookup failed ({exc}); using the map's region {region}", flush=True)
        return sites.resolve(lat, lon, carbon_api_region=region, **kw)


def folder(level, n):
    return OUT / level / f"{n:02d}"


def done(level, n) -> bool:
    return any(folder(level, n).rglob("pareto.parquet"))


def run(level, row):
    n, label, lat, lon, region, why, wind = row
    site = site_for(n, label, lat, lon, region, level)
    t0 = time.time()
    print(f"[{time.strftime('%H:%M')}] site {n} {label} ({site.carbon_api_region}) {level}", flush=True)
    dc_runner.run_one(
        scenario(level), site=site, start=START, end=END,
        connection_mode=None if level == "offgrid" else "cap", connection_solve="loose",
        size_mw_it=100.0, pue=None, resample_hours=1.0, points=5, cost_case="central",
        horizon_years=25.0, unserved_fraction=0.0, out_root=folder(level, n),
        save_dispatch=True, refresh=False, progress=lambda t: print("   ", t, flush=True),
        eps_fracs=None if SET == "base" else EPS_FRACS)
    print(f"   done in {(time.time() - t0) / 60:.1f} min", flush=True)


def summary() -> pd.DataFrame:
    rows = []
    for n, label, lat, lon, region, why, wind in SITES:
        for level in LEVELS:
            for p in folder(level, n).rglob("pareto.parquet"):
                df = pd.read_parquet(p)
                cfg = json.loads((p.parent / "config.json").read_text(encoding="utf-8"))
                for _, r in df.iterrows():
                    served = r.get("served_MWh_per_year") or float("nan")
                    rows.append({
                        "site": n, "place": label, "why": why, "lat": lat, "lon": lon,
                        "region": cfg["site"]["carbon_api_region"], "map_wind_gross": wind, "level": level,
                        "point": r["point"], "cost_GBP_per_MWh": r["cost_GBP_per_MWh"],
                        "gwp_g_per_kWh": r["gwp_g_per_kWh"], "gwp_supply_g_per_kWh": r.get("gwp_supply_g_per_kWh"),
                        **{c: r[c] for c in ("cap_wind", "cap_solar", "cap_batt_p", "cap_batt_e", "cap_ely",
                                             "cap_tank", "cap_fc", "cap_grid")},
                        "cap_ge": r.get("cap_ge", 0.0),
                        "gas_engine_share_of_supply": r.get("cap_ge_MWh_per_year", 0.0) / served,
                        "h2_bought_t_per_year": r.get("h2_bought_kg_per_year", 0.0) / 1000.0,
                        "h2_bought_blue_t_per_year": r.get("h2_bought_2_kg_per_year", 0.0) / 1000.0,
                        # made on site = burned less bought (storage is cyclic; leaks are tiny)
                        "h2_made_t_per_year": max(0.0, r.get("h2_to_fuel_cell_kg_per_year", 0.0)
                                                  - r.get("h2_bought_kg_per_year", 0.0)
                                                  - r.get("h2_bought_2_kg_per_year", 0.0)) / 1000.0,
                        "fuel_cell_share_of_supply": r.get("cap_fc_MWh_per_year", 0.0) / served,
                        "import_share_of_supply": r.get("import_MWh_per_year", 0.0) / served,
                        "hydrogen_used": bool(r["cap_fc"] > 1e-3),
                        "makes_own_hydrogen": bool(r["cap_ely"] > 1e-3),
                        "connection": r.get("connection_option"),
                    })
    out = pd.DataFrame(rows)
    OUT.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT / "summary.csv", index=False)
    if len(out):
        hydrogen_limits(out).to_csv(OUT / "hydrogen_limits.csv", index=False)
    return out


def hydrogen_limits(out: pd.DataFrame) -> pd.DataFrame:
    """One row per site and grid level: where hydrogen stops being used along the frontier.

    ``h2_up_to_g_per_kWh`` is the highest-carbon frontier point at which the fuel cell still serves
    ENTRY_SHARE of supply: below it the cheapest designs use hydrogen, above it they do not. Exact
    only to the frontier's own points (EPS_FRACS)."""
    rows = []
    for (n, level), g in out.groupby(["site", "level"]):
        g = g.sort_values("gwp_g_per_kWh")
        used = g[g.fuel_cell_share_of_supply >= ENTRY_SHARE]
        lo, hi = g.iloc[0], g.iloc[-1]
        rows.append({
            "site": n, "place": g.place.iloc[0], "level": level, "region": g.region.iloc[0],
            "min_gwp_g_per_kWh": lo.gwp_g_per_kWh, "min_gwp_cost_GBP_per_MWh": lo.cost_GBP_per_MWh,
            "min_cost_g_per_kWh": hi.gwp_g_per_kWh, "min_cost_GBP_per_MWh": hi.cost_GBP_per_MWh,
            "h2_up_to_g_per_kWh": used.gwp_g_per_kWh.max() if len(used) else float("nan"),
            "h2_points": len(used), "points": len(g),
            "h2_share_at_min_gwp": lo.fuel_cell_share_of_supply,
            "gas_share_at_min_cost": hi.gas_engine_share_of_supply,
            "blue_t_at_min_cost": hi.h2_bought_blue_t_per_year,
        })
    return pd.DataFrame(rows)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--levels", nargs="*", default=list(LEVELS), choices=LEVELS)
    ap.add_argument("--sites", nargs="*", type=int, default=None)
    ap.add_argument("--summary", action="store_true")
    ap.add_argument("--no-summary", action="store_true", help="run only; leave summary.csv alone")
    ap.add_argument("--set", default="base", choices=list(SETS))
    a = ap.parse_args(argv)
    global OUT, SET
    SET, OUT = a.set, ROOT / "optimisation_outputs" / SETS[a.set]["out"]
    if not a.summary:
        for level in a.levels:
            for row in SITES:
                if a.sites and row[0] not in a.sites:
                    continue
                if done(level, row[0]):
                    print(f"site {row[0]} {level}: already done", flush=True)
                    continue
                try:
                    run(level, row)
                except Exception as exc:  # noqa: BLE001 - one site's failure must not stop the night
                    print(f"   FAILED site {row[0]} {level}: {type(exc).__name__}: {exc}", flush=True)
    if a.no_summary:
        return
    s = summary()
    print(f"summary: {len(s)} rows -> {OUT / 'summary.csv'}", flush=True)


if __name__ == "__main__":
    main()
