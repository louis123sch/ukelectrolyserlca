#!/usr/bin/env python
"""The supervisor's +/-50 % test of the grid connection's price (email of 4 Nov 2026): "if you vary
the connection cost by +/-50 % and the design doesn't change, there's no need to go further on it for
now."

    python -m optimisation.sensitivity connection <case>   # solve: sensitivity_connection_<case>.csv (~3.5 h a case)
    python scripts/connection_sensitivity.py               # judge: connection_sensitivity.md

Reads the sweep's three frontier points per knob and scale, applies the cut-off rule's own test
(optimisation_outputs/cutoff_rule3.md: the same technologies built and no built capacity moved by more
than 5 %) against the central row, and writes the tables. A file that is still being written is
judged on the variants it holds so far.
"""
import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "optimisation_outputs"
TOL = 0.05
BUILT_ABOVE = 1e-3          # MW, MWh or kg: below this a capacity is the solver's rounding, not a build
CAPS = {"cap_grid": "Grid MW", "cap_wind": "Wind MW", "cap_solar": "Solar MW", "cap_batt_p": "Battery MW",
        "cap_batt_e": "Battery MWh", "cap_ely": "Electrolyser MW", "cap_tank": "Tank kg", "cap_fc": "Fuel cell MW"}
SHORT = {"cap_grid": "grid", "cap_wind": "wind", "cap_solar": "solar", "cap_batt_p": "battery power",
         "cap_batt_e": "battery energy", "cap_ely": "electrolyser", "cap_tank": "tank", "cap_fc": "fuel cell"}
POINTS = ("min_cost", "knee", "min_gwp")
POINT_NAME = {"min_cost": "cheapest", "knee": "knee", "min_gwp": "lowest carbon"}
KNOBS = {"connection_build_scale": "One-off build cost", "network_charges_scale": "Yearly network charges"}
CASES = {
    "london_150_single": "London, 150 MW of computing, the fixed national-grid price list (T-Demand4)",
    "london_150_leicester_sq_cap": "London, 150 MW of computing, connected at LEICESTER SQ 11KV at 132 kV, "
                                   "size free up to 1.43x the load (room ignored)",
    "london_150_leicester_sq": "London, 150 MW of computing, connected at LEICESTER SQ 11KV at 132 kV, "
                               "capped at the room it publishes",
}


def built(row) -> set:
    return {c for c in CAPS if row[c] > BUILT_ABOVE}


def compare(central, row) -> dict:
    """The cut-off rule's test on one point: technologies built, and the largest move."""
    b0, b1 = built(central), built(row)
    moves = {c: row[c] / central[c] - 1.0 for c in b0 & b1}
    worst = max(moves, key=lambda c: abs(moves[c])) if moves else None
    return {"appears": sorted(b1 - b0), "disappears": sorted(b0 - b1), "moves": moves, "worst": worst,
            "worst_move": moves[worst] if worst else 0.0,
            "passed": b0 == b1 and all(abs(m) <= TOL for m in moves.values())}


def _fmt(v: float) -> str:
    return "0" if abs(v) <= BUILT_ABOVE else f"{v:,.1f}"


def _label(row, knob_of_row) -> tuple[str, str]:
    if knob_of_row is None:
        return "Central", "1.0x"
    return KNOBS[knob_of_row], f"{row[f'knob:{knob_of_row}']:g}x"


def _knob(row) -> str | None:
    for k in KNOBS:
        if f"knob:{k}" in row and pd.notna(row[f"knob:{k}"]):
            return k
    return None


def case_section(case: str, df: pd.DataFrame) -> tuple[list[str], list[dict]]:
    lines = [f"### {CASES.get(case, case)}", ""]
    central = df[df.variant == "central"].set_index("objective")
    if "grid_floor_mw" in df:
        c0 = df.iloc[0]
        lines += [f"The price list holds the connection between {c0.grid_floor_mw:,.1f} and {c0.grid_ceiling_mw:,.1f} MW.", ""]
    lines += ["| Knob | Scale | Point | " + " | ".join(CAPS.values()) + " | Cost £ m/yr | Carbon t/yr | Test |",
              "|---|---|---|" + "---|" * len(CAPS) + "---|---|---|"]
    judged = []
    for _, r in df.iterrows():
        knob = _knob(r)
        name, scale = _label(r, knob)
        base = central.loc[r.objective]
        if knob is None:
            test = "reference"
        else:
            c = compare(base, r)
            judged.append({"case": case, "knob": knob, "scale": r[f"knob:{knob}"], "point": r.objective, **c,
                           "cost": r.cost_m_GBP_per_year, "cost_base": base.cost_m_GBP_per_year,
                           "gwp": r.gwp_t_per_year, "gwp_base": base.gwp_t_per_year})
            test = "pass" if c["passed"] else "FAIL"
            if c["worst"]:
                test += f": {SHORT[c['worst']]} {c['worst_move']:+.1%}"
            for what, cs in (("appears", c["appears"]), ("disappears", c["disappears"])):
                if cs:
                    test += f"; {', '.join(SHORT[x] for x in cs)} {what}"
        lines.append(f"| {name} | {scale} | {POINT_NAME[r.objective]} | "
                     + " | ".join(_fmt(r[c]) for c in CAPS)
                     + f" | {r.cost_m_GBP_per_year:,.2f} | {r.gwp_t_per_year:,.0f} | {test} |")
    return lines + [""], judged


def list_comparison(frames: dict) -> list[str]:
    """The price list itself is part of the design, and the fixed-list cases cannot change it. What
    can be read off them: which of the two lists is cheaper at each scale of each knob."""
    a, b = frames.get("london_150_single"), frames.get("london_150_leicester_sq_cap")
    if a is None or b is None:
        return []
    lines = ["### Which price list is cheaper at each scale", "",
             "The cheapest point on each of the two lists, £ m a year. The fixed-list runs cannot switch list "
             "themselves, so this is the check on whether the choice would flip.", "",
             "| Knob | Scale | National-grid list | 132 kV list | Gap (national less 132 kV) |", "|---|---|---|---|---|"]
    for variant in a.variant.unique():
        x = a[(a.variant == variant) & (a.objective == "min_cost")]
        y = b[(b.variant == variant) & (b.objective == "min_cost")]
        if x.empty or y.empty:
            continue
        name, scale = _label(x.iloc[0], _knob(x.iloc[0]))
        cx, cy = x.iloc[0].cost_m_GBP_per_year, y.iloc[0].cost_m_GBP_per_year
        lines.append(f"| {name} | {scale} | {cx:,.2f} | {cy:,.2f} | {cx - cy:+,.2f} |")
    return lines + [""]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=str(OUT), help="where the sweep files are")
    ap.add_argument("--no-write", action="store_true", help="print only")
    a = ap.parse_args()
    frames = {}
    for case in CASES:
        path = Path(a.dir) / f"sensitivity_connection_{case}.csv"
        if path.exists():
            frames[case] = pd.read_csv(path)
    if not frames:
        raise SystemExit(f"no sensitivity_connection_*.csv in {a.dir}")
    lines = ["# The grid connection's price, +/-50 %", "",
             "The supervisor's test (email of 4 Nov 2026). Full year 2025, hourly, three-point frontier per "
             "variant (`optimisation/sensitivity.py`, `connection`). Each row is judged against its case's central "
             "row at the same point with the cut-off rule's test: the same technologies built and no built "
             f"capacity moved by more than {TOL:.0%}.", "",
             "*One-off build cost* is the yearly annuity on the substation, cable and switchgear "
             "(`connection_cost.py`). *Yearly network charges* are the national locational charge on winter-peak "
             "demand, the local capacity charge, the national residual and local fixed charges, and the local "
             "per-MWh unit rates. The balancing charge, losses and levies are not scaled. No carbon coefficient "
             "changes in either knob.", ""]
    judged = []
    for case, df in frames.items():
        section, j = case_section(case, df)
        lines += section
        judged += j
    lines += list_comparison(frames)
    fails = [j for j in judged if not j["passed"]]
    lines += ["### Summary", "", f"{len(judged) - len(fails)} of {len(judged)} points pass the test."]
    for j in fails:
        lines.append(f"- {j['case']}, {KNOBS[j['knob']].lower()} at {j['scale']:g}x, {POINT_NAME[j['point']]}: "
                     f"{SHORT[j['worst']] if j['worst'] else 'nothing in common'} {j['worst_move']:+.1%}"
                     + "".join(f"; {', '.join(SHORT[x] for x in j[w])} {w}" for w in ("appears", "disappears") if j[w]))
    lines.append("")
    verdict = OUT / "connection_sensitivity_verdict.md"
    if verdict.exists():
        lines = lines[:2] + verdict.read_text(encoding="utf-8").rstrip().split("\n") + [""] + lines[2:]
    text = "\n".join(lines)
    print(text)
    if not a.no_write:
        (OUT / "connection_sensitivity.md").write_text(text, encoding="utf-8", newline="\n")
        print("\nwritten to optimisation_outputs/connection_sensitivity.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
