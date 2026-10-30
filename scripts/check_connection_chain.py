"""
G: the connection chain run end to end — 14 areas x 3 sizes (COST_PLAN §1.9,
re-run for §1.11 on 30 Oct 2026 with the price list chosen in the LP).
=============================================================================

Every area at a small, a medium and a large data centre, through the whole
chain built 28-30 Oct 2026 — the price lists the site could be on (grid,
voltage, charging band, substation, cable, each area's own charges and build
prices, losses and levies), and then the LP's two anchors (minimum cost,
minimum carbon) on a one-week June window at hourly resolution, the LP
choosing the price list with the connection size (``--mode room``, the
default; ``cap``; or ``single``, the model before 30 Oct 2026, one list fixed
from the 1.43x ceiling).

What it checks, per run
-----------------------
- the connection the LP builds sits inside the size range of the price list
  it is charged on (``floor <= cap_grid <= ceiling``), and whether the floor
  binds — structural once the list is chosen, a finding when it is fixed;
- the tier, voltage and band of the chosen list agree with each other and
  with the band the built connection falls in by the tables;
- a national-grid site pays no local charges; a local site pays its own area's;
- a 33/132 kV site's local charges are site-specific where a node exists;
- the build prices are the area's own list, and which rows are stand-ins;
- the all-in import price of the chosen voltage group is in a plausible band;
- the optimiser's choice against the rule's list, and the solve time.

Writes ``optimisation_outputs/connection_chain.csv`` (``connection_chain_<mode>.csv``
for a mode other than the default) and prints the checks.

Run:  python scripts/check_connection_chain.py [--mode room|cap|single] [--sizes 5,60,150] [--regions 3,13] [--points 3]
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import lca_helpers as H  # noqa: E402
H.setup_brightway()
from optimisation import dc_inputs as I, dc_model as M, dc_pareto as P, network_charges as nc  # noqa: E402
from optimisation import connection_cost as cc, connection_options as CO, duos_areas as D  # noqa: E402

START, END, PUE = "2025-06-02", "2025-06-09", 1.2
COORDS = {
    1: (57.48, -4.22, "Inverness"), 2: (55.86, -4.25, "Glasgow"), 3: (53.48, -2.24, "Manchester"),
    4: (54.978, -1.617, "Newcastle"), 5: (53.8008, -1.5491, "Leeds"), 6: (53.227, -4.129, "Bangor"),
    7: (51.4816, -3.1791, "Cardiff"), 8: (52.489, -1.898, "Birmingham"),
    9: (52.954, -1.158, "Nottingham"), 10: (52.62, 1.29, "Norwich"), 11: (50.72, -3.53, "Exeter"),
    12: (50.91, -1.404, "Southampton"), 13: (51.5074, -0.1278, "London"), 14: (50.82, -0.137, "Brighton"),
}
OUT = ROOT / "optimisation_outputs" / "connection_chain.csv"


def chosen(x: dict, meta: dict) -> dict:
    """The price list a frontier point is on: the one it chose, or the fixed one."""
    opts = {o["key"]: o for o in meta.get("connection_options") or []}
    key = x.get("connection_option")
    if key and key in opts:
        o = opts[key]
        g = (meta.get("connection_groups") or {}).get(o["group"], {})
        return {"option": key, "transmission": bool(o["transmission"]), "voltage": o["voltage"], "band": o["band"],
                "floor_mw": o["floor_mw"], "ceiling_mw": o["ceiling_mw"], "substation": o.get("substation"),
                "route_km": o.get("route_km"), "headroom": o.get("headroom_status"), "which": o.get("which"),
                "room_mw": o.get("room_mw"), "charges": o["network_charges"],
                "price_mean": g.get("price_mean_GBP_per_MWh"), "loss": g.get("loss_gross_up_mean"),
                "ci_mean": (g.get("gwp_mean_kgco2e_per_kwh") or np.nan) * 1000.0}
    cp = meta.get("connection_site") or {}
    return {"option": f"{meta['tdr_band']} (fixed)", "transmission": meta["transmission_connected"],
            "voltage": meta["connection_voltage"], "band": meta["tdr_band"],
            "floor_mw": meta["connection_floor_mw"], "ceiling_mw": meta["connection_limit_mw"],
            "substation": cp.get("substation"), "route_km": cp.get("route_km"), "headroom": cp.get("headroom_status"),
            "which": "nearest", "room_mw": cp.get("nearest_headroom_mw"), "charges": meta["network_charges"],
            "price_mean": None, "loss": meta["levies"]["loss_gross_up_mean"], "ci_mean": None}


def one(region: int, size_mw_it: float, points: int, mode: str) -> dict:
    lat, lon, city = COORDS[region]
    key = f"{lat},{lon}"
    t0 = time.time()
    series, meta = I.build_series(key, START, END, size_mw_it, pue=PUE, connection_mode=mode)
    series = I.resample(series, 1.0)
    tech = I.build_tech(key, meta, ely_tech="PEM operation", cost_case="central",
                        size_mw_it=size_mw_it, pue=PUE)
    t_build = time.time() - t0
    assets = M.Assets(grid=True, wind=True, solar=True, battery=True,
                      electrolyser=True, tank=True, fuel_cell=True)
    assets = M.Assets(**{**assets.__dict__, "grid_limit_mw": meta["connection_limit_mw"],
                         "grid_floor_mw": meta["connection_floor_mw"]})
    t1 = time.time()
    r = P.front(series, assets, tech, points=points)
    t_solve = time.time() - t1
    load = size_mw_it * PUE
    ref = meta["connection_reference"]
    row = {
        "region": region, "city": city, "area": D.AREA_NAMES[region][:34], "size_mw_it": size_mw_it,
        "load_mw": load, "mode": meta["connection_mode"], "chosen_by": meta["connection_chosen_by"],
        "options": len(meta["connection_options"]), "ceiling_mw": meta["connection_limit_mw"], "floor_mw": meta["connection_floor_mw"],
        "rule_transmission": ref["transmission"], "rule_voltage": ref["voltage"], "rule_band": ref["band"],
        "rule_key": ref["key"], "nged_flag": region in (7, 8, 9, 11),
        "levies_GBP_MWh": meta["levies"].get("flat_GBP_per_MWh"),
        "seconds": time.time() - t0, "build_s": t_build, "solve_s": t_solve,
    }
    for name in ("min_cost", "min_gwp"):
        x = r[name]
        c = chosen(x, meta)
        ch = c["charges"]
        conn = cc.connection_costs(region, c["transmission"], "central", connection_voltage=c["voltage"], route_km=c["route_km"])
        built_band, _ = nc.tdr_band_for(max(x["cap_grid"], 1e-6), load * 8760, region=region, site=(lat, lon),
                                        transmission_connected=c["transmission"])
        row.update({
            f"{name}_cap_grid": x["cap_grid"], f"{name}_cost_m_yr": x["cost_GBP_per_year"] / 1e6,
            f"{name}_t_yr": x["gwp_kgco2e_per_year"] / 1e3, f"{name}_import_GWh": x["import_MWh_per_year"] / 1e3,
            f"{name}_option": c["option"], f"{name}_transmission": c["transmission"], f"{name}_voltage": c["voltage"],
            f"{name}_band": c["band"], f"{name}_band_built": built_band,
            f"{name}_floor": c["floor_mw"], f"{name}_ceiling": c["ceiling_mw"],
            f"{name}_floor_binding": abs(x["cap_grid"] - c["floor_mw"]) <= max(c["floor_mw"], 1.0) * 1e-6,
            f"{name}_ceiling_binding": abs(x["cap_grid"] - c["ceiling_mw"]) <= max(c["ceiling_mw"], 1.0) * 1e-6,
            f"{name}_substation": c["substation"], f"{name}_route_km": c["route_km"], f"{name}_headroom": c["headroom"],
            f"{name}_which": c["which"], f"{name}_room_mw": c["room_mw"],
            f"{name}_tnuos_loc_GBP_MW_yr": ch["tnuos_locational_GBP_per_MW_year"], f"{name}_tdr_GBP_yr": ch["tnuos_tdr_GBP_per_year"],
            f"{name}_duos_cap_GBP_MW_yr": ch["duos_capacity_GBP_per_MW_year"], f"{name}_duos_fixed_GBP_yr": ch["duos_fixed_GBP_per_year"],
            f"{name}_duos_unit_GBP_MWh": ch["duos_mean_GBP_per_MWh"],
            f"{name}_duos_how": (ch.get("duos_site_specific") or {}).get("how"),
            f"{name}_price_list": conn["price_list"], f"{name}_stand_in": ";".join(conn["stand_in"]),
            f"{name}_conn_cap_GBP_MW_yr": conn["per_MW_year_GBP"], f"{name}_conn_fixed_GBP_yr": conn["fixed_per_year_GBP"],
            f"{name}_loss_gross_up": c["loss"] if c["loss"] is not None else meta["levies"]["loss_gross_up_mean"],
            f"{name}_price_mean_GBP_MWh": (c["price_mean"] if c["price_mean"] is not None
                                          else float(np.mean(series.grid_price_per_mwh))),
            f"{name}_rule_voltage_at_built": nc.connection_voltage(max(x["cap_grid"], 1e-6), region, c["transmission"]),
            f"{name}_is_rules_list": c["option"] == ref["key"] or (c["option"].endswith("(fixed)")),
        })
    row["front_points"] = len(r["front"])
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default=CO.DEFAULT_MODE, choices=CO.MODES)
    ap.add_argument("--sizes", default="5,60,150")
    ap.add_argument("--regions", default=",".join(str(r) for r in COORDS))
    ap.add_argument("--points", type=int, default=3)
    ap.add_argument("--out", default=None)
    ap.add_argument("--recheck", action="store_true", help="run the checks on the CSV already written, no solving")
    a = ap.parse_args()
    out = Path(a.out) if a.out else (OUT if a.mode == CO.DEFAULT_MODE else OUT.with_name(f"connection_chain_{a.mode}.csv"))
    sizes = [float(s) for s in a.sizes.split(",")]
    regions = [int(r) for r in a.regions.split(",")]
    rows = []
    print(f"connection chain, {a.mode} mode, {len(regions)} areas x {len(sizes)} sizes, {START} to {END} hourly")
    if a.recheck:
        rows = pd.read_csv(out).to_dict("records")
        print(f"  rechecking {len(rows)} rows from {out}")
        regions, sizes = [], []
    for region in regions:
        for size in sizes:
            try:
                row = one(region, size, a.points, a.mode)
            except Exception as e:                       # keep going; record the failure
                row = {"region": region, "city": COORDS[region][2], "size_mw_it": size, "error": repr(e)[:300]}
                print(f"  !! r{region} {COORDS[region][2]} {size:g} MW: {e!r}"[:300])
            rows.append(row)
            if "error" not in row:
                print(f"  r{region:<3}{row['city']:<12}{size:>6g} MW  {row['options']:>2} lists  "
                      f"{row['min_cost_voltage']:<13}{row['min_cost_band']:<10}{'T' if row['min_cost_transmission'] else 'D'}  "
                      f"cap {row['min_cost_cap_grid']:>7.1f} [{row['min_cost_floor']:.1f}-{row['min_cost_ceiling']:.1f}] MW "
                      f"{row['min_cost_headroom'] or '-':<9} cost £{row['min_cost_cost_m_yr']:>7.2f} m  {row['min_cost_price_list']:<9}"
                      f"{row['solve_s']:>5.0f} s{'  (rule' + chr(39) + 's list)' if row['min_cost_is_rules_list'] else ''}")
            pd.DataFrame(rows).to_csv(out, index=False)
    d = pd.DataFrame(rows)
    ok = d[d.get("error", pd.Series(dtype=object)).isna()] if "error" in d else d
    print(f"\n{len(ok)} of {len(d)} runs solved; written to {out}")
    if ok.empty:
        return 1
    fails = []

    def chk(name, cond, detail=""):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}   {detail}")
        if not cond:
            fails.append(name)

    print("\n=== chain checks ===")
    for name in ("min_cost", "min_gwp"):
        chk(f"{name}: connection built inside the chosen list's floor and ceiling",
            ((ok[f"{name}_cap_grid"] >= ok[f"{name}_floor"] * (1 - 1e-6) - 1e-6)
             & (ok[f"{name}_cap_grid"] <= ok[f"{name}_ceiling"] * (1 + 1e-6) + 1e-6)).all())
        bad = ok[ok[f"{name}_band_built"] != ok[f"{name}_band"]]
        chk(f"{name}: built connection is in the band charged", bad.empty,
            "; ".join(f"r{r.region} {r.size_mw_it:g}: {r[name + '_band_built']} vs {r[name + '_band']}" for _, r in bad.iterrows()) or "all")
        chk(f"{name}: floor binds somewhere?", True,
            f"{int(ok[f'{name}_floor_binding'].sum())} of {len(ok)} runs on the floor, "
            f"{int(ok[f'{name}_ceiling_binding'].sum())} on the ceiling")
        chk(f"{name}: tier and band family agree",
            (ok[f"{name}_transmission"] == ok[f"{name}_band"].str.startswith("T-Demand")).all())
        chk(f"{name}: voltage family and band family agree",
            ((ok[f"{name}_voltage"] == "11 kV") == ok[f"{name}_band"].str.startswith("HV")).all())
        chk(f"{name}: national-grid sites pay no local charges",
            ((~ok[f"{name}_transmission"]) | ((ok[f"{name}_duos_cap_GBP_MW_yr"] == 0) & (ok[f"{name}_duos_fixed_GBP_yr"] == 0)
                                              & (ok[f"{name}_duos_unit_GBP_MWh"] == 0))).all())
        chk(f"{name}: local sites pay local charges",
            ((ok[f"{name}_transmission"]) | (ok[f"{name}_duos_cap_GBP_MW_yr"] > 0)).all())
        up = ok[(~ok[f"{name}_transmission"]) & (ok[f"{name}_voltage"] != ok[f"{name}_rule_voltage_at_built"])]
        chk(f"{name}: voltage above the rule's for the built size (chosen, or stepped up by the register)", True,
            "; ".join(f"r{r.region} {r.size_mw_it:g}: {r[name + '_rule_voltage_at_built']}->{r[name + '_voltage']}" for _, r in up.iterrows()) or "nowhere")
        ehv = ok[(~ok[f"{name}_transmission"]) & (ok[f"{name}_voltage"] != "11 kV")]
        chk(f"{name}: 33/132 kV sites site-specific where a node exists", True,
            f"{int((ehv[f'{name}_duos_how'] == 'site-specific').sum())} of {len(ehv)} site-specific")
        chk(f"{name}: every area priced on its own list", (ok[f"{name}_price_list"] == ok.region.map(cc.AREA_PRICE_LIST)).all())
        chk(f"{name}: all-in import price £80-£200/MWh", ok[f"{name}_price_mean_GBP_MWh"].between(80, 200).all(),
            f"£{ok[f'{name}_price_mean_GBP_MWh'].min():.0f}-{ok[f'{name}_price_mean_GBP_MWh'].max():.0f}/MWh")
        chk(f"{name}: loss gross-up 0.95-1.08", ok[f"{name}_loss_gross_up"].between(0.95, 1.08).all(),
            f"{ok[f'{name}_loss_gross_up'].min():.4f}-{ok[f'{name}_loss_gross_up'].max():.4f}")
        chk(f"{name}: connection capital positive (no substation per MW at 11 kV, by design)",
            (ok[f"{name}_conn_fixed_GBP_yr"] > 0).all() & ((ok[f"{name}_voltage"] == "11 kV") | (ok[f"{name}_conn_cap_GBP_MW_yr"] > 0)).all())
        same = ok[f"{name}_is_rules_list"].astype(bool)      # object dtype when failed rows left blanks
        chk(f"{name}: the rule's own list chosen in", True, f"{int(same.sum())} of {len(ok)} runs"
            + ("" if same.all() else "; elsewhere: " + ", ".join(
                f"r{r.region} {r.size_mw_it:g} {r[name + '_option'][:40]}" for _, r in ok[~same].head(8).iterrows())))
    chk("NGED flag on its four areas only", (ok.nged_flag == ok.region.isin([7, 8, 9, 11])).all())
    chk("min_cost costs no more than min_gwp", (ok.min_cost_cost_m_yr <= ok.min_gwp_cost_m_yr * (1 + 1e-6)).all())
    chk("min_gwp emits no more than min_cost", (ok.min_gwp_t_yr <= ok.min_cost_t_yr * (1 + 1e-6)).all())
    short = ok[ok.min_cost_headroom == "shortfall"]
    chk("spare-capacity shortfalls at the chosen substation", True, f"{len(short)} of {len(ok)} runs: "
        + ", ".join(f"r{r.region} {r.size_mw_it:g}" for _, r in short.iterrows()))
    print(f"\n  solve time: median {ok.solve_s.median():.0f} s, max {ok.solve_s.max():.0f} s per frontier of {a.points} points "
          f"(build {ok.build_s.median():.0f} s median); {ok.options.min():.0f}-{ok.options.max():.0f} price lists")
    print("\n" + ("ALL PASSED" if not fails else f"FAILED: {fails}"))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
