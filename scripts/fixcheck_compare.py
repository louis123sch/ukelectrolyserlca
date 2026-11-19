#!/usr/bin/env python
"""Before/after table for the East Grinstead cluster checks, from the unpacked results.

    python scripts/fixcheck_compare.py <folder> [--before after] [--after fc] [--fc-check] [--out table.md]

<folder> is where fixcheck_results.tgz was unpacked (scripts/cluster/fixcheck_pack.sh). It holds
fix-<name>/optimisation_outputs/{dc_runs/fixcheck_east_grinstead/*/summary.json,
sensitivity_fixcheck_*.csv} for each code copy. --before and --after name two of them
(default: before, after — the code-check of docs/CODE_CHECK_FIX_PLAN.md step 5).

--fc-check (the fuel-cell stack interest fix, docs/FUEL_CELL_STACK_AND_EQUATIONS_PLAN.md step 6,
run as --before after --after fc): a design with no fuel cell must come out identical, and where a
design keeps its sizes the bill must rise by exactly cap_fc × the stack's new capacity term (2026
pounds), because the fix adds a term on capacity and nothing else. Prints which designs pass,
which moved, and the ones that need a look.

Prints markdown. No solving; reads saved results only.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
CAPS = ["cap_wind", "cap_solar", "cap_batt_p", "cap_batt_e", "cap_ely", "cap_tank", "cap_fc", "cap_ge", "cap_grid"]
POINTS = ["min_cost", "knee", "min_gwp"]
REL = 1e-6          # "identical": cost and carbon within one part in a million
FC_REL = 1e-4       # the fuel-cell check: bill change within 0.01 % of cap_fc × the stack term


def load(folder: Path, name: str) -> dict:
    out = {}
    runs = folder / f"fix-{name}" / "optimisation_outputs" / "dc_runs" / "fixcheck_east_grinstead"
    for p in sorted(runs.glob("*/summary.json")):
        s = json.loads(p.read_text(encoding="utf-8"))
        out[s["n"]] = s
    return out


def rel(a: float, b: float) -> float:
    return (b - a) / abs(a) if abs(a) > 1e-9 else (0.0 if abs(b) < 1e-9 else float("inf"))


def cap_moves(pa: dict, pb: dict) -> str:
    moves = []
    for k in CAPS:
        a, b = float(pa.get(k, 0.0) or 0.0), float(pb.get(k, 0.0) or 0.0)
        if abs(b - a) > max(1e-3, 1e-4 * max(abs(a), abs(b))):
            moves.append(f"{k[4:]} {a:,.2f} → {b:,.2f}")
    return "; ".join(moves) or "none"


def stack_term_2026() -> float:
    """The fix's new capacity term, £ per MW of fuel cell a year in 2026 pounds (central case)."""
    sys.path.insert(0, str(ROOT))
    from optimisation import h2_capex as hc
    from optimisation import price_base as P
    row = hc.fuel_cell_costs().set_index("case").loc["central"]
    return float(row.stack_annual_GBP_per_MW_year) * P.to_2026()


def matrix(folder: Path, before: str, after: str, fc_check: bool) -> list[str]:
    bef, aft = load(folder, before), load(folder, after)
    lines = [f"Scenario list: {len(bef)} solved in fix-{before}, {len(aft)} in fix-{after}.", ""]
    term = stack_term_2026() if fc_check else None
    if fc_check:
        lines += [f"Fuel-cell check: an unchanged design's bill should rise by cap_fc × £{term:,.0f} a year.", ""]
    head = "| n | Configuration | Result | Point | Cost £m/yr (change %) | Carbon t/yr (change %) | Sizes that moved |"
    if fc_check:
        head += " Expected rise £m | Check |"
    lines += [head, "|" + "---|" * (head.count("|") - 1)]
    tally = {"identical": 0, "fc ok": 0, "fc moved": 0, "look": 0}
    for n in range(1, 26):
        b, a = bef.get(n), aft.get(n)
        if b is None and a is None:
            continue
        if a is None or b is None:
            s = b or a
            lines.append(f"| {n} | {s['label']} | no result in fix-{after if a is None else before} | | | | |"
                         + (" | |" if fc_check else ""))
            tally["look"] += 1
            continue
        lab = a["label"] + (f" ({b['strategy']} → {a['strategy']})" if b["strategy"] != a["strategy"]
                            else f" ({a['strategy']})")
        rows, identical, has_fc = [], True, False
        for pt in POINTS:
            pb, pa = b[pt], a[pt]
            dc = rel(pb["cost_GBP_per_year"], pa["cost_GBP_per_year"])
            dg = rel(pb["gwp_kgco2e_per_year"], pa["gwp_kgco2e_per_year"])
            mv = cap_moves(pb, pa)
            has_fc = has_fc or float(pb.get("cap_fc", 0) or 0) > 1e-6 or float(pa.get("cap_fc", 0) or 0) > 1e-6
            if abs(dc) > REL or abs(dg) > REL or mv != "none":
                identical = False
            rows.append((pt, pb, pa, dc, dg, mv))
        if identical and not (fc_check and has_fc):
            tally["identical"] += 1
            lines.append(f"| {n} | {lab} | identical | all three | {a['knee']['cost_GBP_per_year'] / 1e6:,.3f} "
                         f"| {a['knee']['gwp_kgco2e_per_year'] / 1e3:,.0f} | none |" + (" | ok |" if fc_check else ""))
            continue
        for pt, pb, pa, dc, dg, mv in rows:
            line = (f"| {n} | {lab} | changed | {pt} | {pb['cost_GBP_per_year'] / 1e6:,.3f} → "
                    f"{pa['cost_GBP_per_year'] / 1e6:,.3f} ({dc * 100:+.3f}) | {pb['gwp_kgco2e_per_year'] / 1e3:,.0f} → "
                    f"{pa['gwp_kgco2e_per_year'] / 1e3:,.0f} ({dg * 100:+.3f}) | {mv} |")
            if fc_check:
                cap = float(pb.get("cap_fc", 0) or 0)
                expect = cap * term
                rise = pa["cost_GBP_per_year"] - pb["cost_GBP_per_year"]
                if not has_fc:
                    verdict = "LOOK: no fuel cell, yet it changed"
                    tally["look"] += 1
                elif mv == "none" and abs(rise - expect) <= FC_REL * max(abs(pb["cost_GBP_per_year"]), 1.0) \
                        and abs(dg) <= REL:
                    verdict = "ok: rise = cap_fc × term"
                    tally["fc ok"] += 1
                elif mv != "none":
                    verdict = "design moved"
                    tally["fc moved"] += 1
                else:
                    verdict = f"LOOK: rise {rise / 1e6:,.3f}"
                    tally["look"] += 1
                line += f" {expect / 1e6:,.3f} | {verdict} |"
            lines.append(line)
    lines.append("")
    if fc_check:
        lines.append(f"{tally['identical']} configurations with no fuel cell identical; {tally['fc ok']} fuel-cell points "
                     f"rose by exactly cap_fc × the term; {tally['fc moved']} fuel-cell points changed design; "
                     f"{tally['look']} need a look.")
    else:
        lines.append(f"{tally['identical']} configurations identical (cost and carbon within one part in a million, "
                     f"no size moved).")
    return lines


def refcases(folder: Path, before: str, after: str) -> list[str]:
    lines = ["", "| Reference case | Point | Cost £m/yr (change %) | Carbon t/yr (change %) | Sizes that moved |",
             "|---|---|---|---|---|"]
    for c in ("islanded_h2", "eastgrinstead_grid"):
        fb = folder / f"fix-{before}" / "optimisation_outputs" / f"sensitivity_fixcheck_{c}.csv"
        fa = folder / f"fix-{after}" / "optimisation_outputs" / f"sensitivity_fixcheck_{c}.csv"
        if not (fb.exists() and fa.exists()):
            lines.append(f"| {c} | missing in fix-{before if not fb.exists() else after} | | | |")
            continue
        b, a = pd.read_csv(fb), pd.read_csv(fa)
        cc, gc = "cost_m_GBP_per_year", "gwp_t_per_year"          # already £m and tonnes
        for anchor in sorted(set(b.objective)):
            rb, ra = b[b.objective == anchor].iloc[0], a[a.objective == anchor].iloc[0]
            dc, dg = rel(rb[cc], ra[cc]), rel(rb[gc], ra[gc])
            lines.append(f"| {c} | {anchor} | {rb[cc]:,.3f} → {ra[cc]:,.3f} ({dc * 100:+.3f}) | {rb[gc]:,.0f} → "
                         f"{ra[gc]:,.0f} ({dg * 100:+.3f}) | {cap_moves(rb.to_dict(), ra.to_dict())} |")
    return lines


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("folder", type=Path)
    ap.add_argument("--before", default="before")
    ap.add_argument("--after", default="after")
    ap.add_argument("--fc-check", action="store_true")
    ap.add_argument("--out", type=Path)
    a = ap.parse_args(argv)
    text = "\n".join(matrix(a.folder, a.before, a.after, a.fc_check) + refcases(a.folder, a.before, a.after))
    if a.out:
        a.out.write_text(text + "\n", encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
