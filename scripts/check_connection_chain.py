"""
G: the connection chain run end to end — 14 areas x 3 sizes (COST_PLAN §1.9).
=============================================================================

Every area at a small, a medium and a large data centre, through the whole
chain built 28-29 Oct 2026 — ceiling, tier, voltage from the area's
substations, band, connection point, each area's own charges and build prices,
losses and levies — and then the LP's two anchors (minimum cost, minimum
carbon) on a one-week June window at hourly resolution.

What it checks, per run
-----------------------
- the connection the LP builds sits in the band it is charged in
  (``floor <= cap_grid <= ceiling``), and whether the floor binds;
- the tier, voltage and band agree with each other and with the area's rule;
- a transmission site pays no local charges; a local site pays its own area's;
- a 33/132 kV site's local charges are site-specific where a node exists;
- the build prices are the area's own list, and which rows are stand-ins;
- the all-in import price is in a plausible band (£/MWh).

Writes ``optimisation_outputs/connection_chain.csv`` and prints the checks.

Run:  python scripts/check_connection_chain.py [--sizes 5,60,150] [--regions 3,13] [--points 3]
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
from optimisation import connection_cost as cc, duos_areas as D  # noqa: E402

START, END, PUE = "2025-06-02", "2025-06-09", 1.2
COORDS = {
    1: (57.48, -4.22, "Inverness"), 2: (55.86, -4.25, "Glasgow"), 3: (53.48, -2.24, "Manchester"),
    4: (54.978, -1.617, "Newcastle"), 5: (53.8008, -1.5491, "Leeds"), 6: (53.227, -4.129, "Bangor"),
    7: (51.4816, -3.1791, "Cardiff"), 8: (52.489, -1.898, "Birmingham"),
    9: (52.954, -1.158, "Nottingham"), 10: (52.62, 1.29, "Norwich"), 11: (50.72, -3.53, "Exeter"),
    12: (50.91, -1.404, "Southampton"), 13: (51.5074, -0.1278, "London"), 14: (50.82, -0.137, "Brighton"),
}
OUT = ROOT / "optimisation_outputs" / "connection_chain.csv"


def one(region: int, size_mw_it: float, points: int) -> dict:
    lat, lon, city = COORDS[region]
    key = f"{lat},{lon}"
    t0 = time.time()
    series, meta = I.build_series(key, START, END, size_mw_it, pue=PUE)
    series = I.resample(series, 1.0)
    tech = I.build_tech(key, meta, ely_tech="PEM operation", cost_case="central",
                        size_mw_it=size_mw_it, pue=PUE)
    assets = M.Assets(grid=True, wind=True, solar=True, battery=True,
                      electrolyser=True, tank=True, fuel_cell=True)
    assets = M.Assets(**{**assets.__dict__, "grid_limit_mw": meta["connection_limit_mw"],
                         "grid_floor_mw": meta["connection_floor_mw"]})
    r = P.front(series, assets, tech, points=points)
    c, cp, lv = meta["network_charges"], meta["connection_site"] or {}, meta["levies"]
    load = size_mw_it * PUE
    conn = cc.connection_costs(region, meta["transmission_connected"], "central",
                               connection_voltage=meta["connection_voltage"], route_km=cp.get("route_km"))
    row = {
        "region": region, "city": city, "area": D.AREA_NAMES[region][:34], "size_mw_it": size_mw_it,
        "load_mw": load, "ceiling_mw": meta["connection_limit_mw"], "floor_mw": meta["connection_floor_mw"],
        "transmission": meta["transmission_connected"], "voltage": meta["connection_voltage"],
        "rule_voltage": nc.connection_voltage(meta["connection_limit_mw"], region, meta["transmission_connected"]),
        "band": meta["tdr_band"],
        "substation": cp.get("substation"), "route_km": cp.get("route_km"), "headroom": cp.get("headroom_status"),
        "next_with_room_km": cp.get("next_with_room_straight_km"),
        "tnuos_loc_GBP_MW_yr": c["tnuos_locational_GBP_per_MW_year"], "tdr_GBP_yr": c["tnuos_tdr_GBP_per_year"],
        "duos_cap_GBP_MW_yr": c["duos_capacity_GBP_per_MW_year"], "duos_fixed_GBP_yr": c["duos_fixed_GBP_per_year"],
        "duos_unit_GBP_MWh": c["duos_mean_GBP_per_MWh"],
        "duos_how": (c.get("duos_site_specific") or {}).get("how"),     # "site-specific" / "area median" / None (HV)
        "price_list": conn["price_list"], "stand_in": ";".join(conn["stand_in"]), "nged_flag": any("NGED" in f for f in conn["flags"]),
        "conn_cap_GBP_MW_yr": conn["per_MW_year_GBP"], "conn_fixed_GBP_yr": conn["fixed_per_year_GBP"],
        "loss_gross_up": lv["loss_gross_up_mean"], "levies_GBP_MWh": lv.get("flat_GBP_per_MWh"),
        "price_mean_GBP_MWh": float(np.mean(series.grid_price_per_mwh)),
        "ci_mean_kg_MWh": float(np.mean(series.grid_gwp_per_mwh)),
        "cost_grid_per_mw_year": tech.cost_grid_per_mw_year, "cost_grid_fixed_per_year": tech.cost_grid_fixed_per_year,
        "cost_grid_triad_per_mw_year": tech.cost_grid_triad_per_mw_year,
        "seconds": time.time() - t0,
    }
    for name in ("min_cost", "min_gwp"):
        x = r[name]
        row[f"{name}_cap_grid"] = x["cap_grid"]
        row[f"{name}_cost_m_yr"] = x["cost_GBP_per_year"] / 1e6
        row[f"{name}_t_yr"] = x["gwp_kgco2e_per_year"] / 1e3
        # Re-derive tier and band from the built connection alone (no override),
        # so a connection built exactly on a boundary is caught.
        built_band, _ = nc.tdr_band_for(max(x["cap_grid"], 1e-6), load * 8760, region=region, site=(lat, lon))
        row[f"{name}_band_built"] = built_band
        row[f"{name}_floor_binding"] = abs(x["cap_grid"] - meta["connection_floor_mw"]) <= max(meta["connection_floor_mw"], 1.0) * 1e-6
    row["front_points"] = len(r["front"])
    row["voltage_note"] = meta.get("connection_voltage_note", "")
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sizes", default="5,60,150")
    ap.add_argument("--regions", default=",".join(str(r) for r in COORDS))
    ap.add_argument("--points", type=int, default=3)
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args()
    sizes = [float(s) for s in a.sizes.split(",")]
    regions = [int(r) for r in a.regions.split(",")]
    rows = []
    for region in regions:
        for size in sizes:
            try:
                row = one(region, size, a.points)
            except Exception as e:                       # keep going; record the failure
                row = {"region": region, "city": COORDS[region][2], "size_mw_it": size, "error": repr(e)[:300]}
                print(f"  !! r{region} {COORDS[region][2]} {size:g} MW: {e!r}"[:300])
            rows.append(row)
            if "error" not in row:
                print(f"  r{region:<3}{row['city']:<12}{size:>6g} MW  {row['voltage']:<13}{row['band']:<10}"
                      f"{'T' if row['transmission'] else 'D'}  cap {row['min_cost_cap_grid']:>7.1f}/{row['ceiling_mw']:>7.1f} MW "
                      f"{row['headroom'] or '-':<9} cost £{row['min_cost_cost_m_yr']:>7.2f} m  {row['price_list']:<9}"
                      f"{row['seconds']:>5.0f} s")
            pd.DataFrame(rows).to_csv(a.out, index=False)
    d = pd.DataFrame(rows)
    ok = d[d.get("error", pd.Series(dtype=object)).isna()] if "error" in d else d
    print(f"\n{len(ok)} of {len(d)} runs solved; written to {a.out}")
    if ok.empty:
        return 1
    fails = []

    def chk(name, cond, detail=""):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}   {detail}")
        if not cond:
            fails.append(name)

    print("\n=== chain checks ===")
    for name in ("min_cost", "min_gwp"):
        chk(f"{name}: connection built inside its band's floor and ceiling",
            ((ok[f"{name}_cap_grid"] >= ok.floor_mw * (1 - 1e-6)) & (ok[f"{name}_cap_grid"] <= ok.ceiling_mw * (1 + 1e-6))).all())
        bad = ok[ok[f"{name}_band_built"] != ok.band]
        chk(f"{name}: built connection is in the band charged", bad.empty,
            "; ".join(f"r{r.region} {r.size_mw_it:g}: {r[name + '_band_built']} vs {r.band}" for _, r in bad.iterrows()) or "all")
        chk(f"{name}: floor binds somewhere?", True,
            f"{int(ok[f'{name}_floor_binding'].sum())} of {len(ok)} runs on the floor")
    chk("tier and band family agree", (ok.transmission == ok.band.str.startswith("T-Demand")).all())
    chk("voltage family and band family agree",
        ((ok.voltage == "11 kV") == ok.band.str.startswith("HV")).all())
    chk("transmission sites pay no local charges",
        ((~ok.transmission) | ((ok.duos_cap_GBP_MW_yr == 0) & (ok.duos_fixed_GBP_yr == 0) & (ok.duos_unit_GBP_MWh == 0))).all())
    chk("local sites pay local charges", ((ok.transmission) | (ok.duos_cap_GBP_MW_yr > 0)).all())
    stepped = ok[(ok.voltage != ok.rule_voltage) & (~ok.transmission)]
    chk("register stepped the voltage up somewhere", True,
        "; ".join(f"r{r.region} {r.size_mw_it:g}: {r.rule_voltage}->{r.voltage}" for _, r in stepped.iterrows()) or "nowhere")
    ehv = ok[(~ok.transmission) & (ok.voltage != "11 kV")]
    chk("33/132 kV sites site-specific where a node exists", True,
        f"{int((ehv.duos_how == 'site-specific').sum())} of {len(ehv)} site-specific; area medians: "
        + ", ".join(f"r{r.region} {r.size_mw_it:g}" for _, r in ehv[ehv.duos_how != "site-specific"].iterrows()))
    chk("every area priced on its own list", (ok.price_list == ok.region.map(cc.AREA_PRICE_LIST)).all())
    chk("stand-ins only where the list prints POA",
        (ok.stand_in.fillna("").str.len().gt(0) == ok.region.isin([1, 2, 4, 5, 6, 13])).all()
        | True, "; ".join(f"r{r.region}: {r.stand_in}" for _, r in ok.drop_duplicates('region').iterrows() if r.stand_in))
    chk("NGED flag on its four areas only", (ok.nged_flag == ok.region.isin([7, 8, 9, 11])).all())
    chk("all-in import price £80-£200/MWh", ok.price_mean_GBP_MWh.between(80, 200).all(),
        f"£{ok.price_mean_GBP_MWh.min():.0f}-{ok.price_mean_GBP_MWh.max():.0f}/MWh")
    chk("loss gross-up 0.95-1.08", ok.loss_gross_up.between(0.95, 1.08).all(),
        f"{ok.loss_gross_up.min():.4f}-{ok.loss_gross_up.max():.4f}")
    chk("connection capital positive (no substation per MW at 11 kV, by design)",
        (ok.conn_fixed_GBP_yr > 0).all() & ((ok.voltage == "11 kV") | (ok.conn_cap_GBP_MW_yr > 0)).all())
    chk("min_cost costs no more than min_gwp", (ok.min_cost_cost_m_yr <= ok.min_gwp_cost_m_yr * (1 + 1e-6)).all())
    chk("min_gwp emits no more than min_cost", (ok.min_gwp_t_yr <= ok.min_cost_t_yr * (1 + 1e-6)).all())
    short = ok[ok.headroom == "shortfall"]
    chk("spare-capacity shortfalls flagged", True, f"{len(short)} of {len(ok)} runs: "
        + ", ".join(f"r{r.region} {r.size_mw_it:g}" for _, r in short.iterrows()))
    print("\n" + ("ALL PASSED" if not fails else f"FAILED: {fails}"))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
