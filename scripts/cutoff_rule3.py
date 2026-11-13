#!/usr/bin/env python
"""Rule 3 of the cut-off rule: did adding every still-excluded flow at its upper estimate change the
best design? (CUTOFF_RULE_PLAN.md step 4.)

    python -m optimisation.sensitivity cutoff --hours=1   # solve: sensitivity_cutoff_<case>.csv (~1 h)
    python scripts/cutoff_rule3.py                        # judge: cutoff_rule3.md and ASSUMPTIONS.md section 8

Reads sensitivity_cutoff_<case>.csv (central and cutoff=upper at both anchors), applies Q4's test
(the same technologies built; every built capacity within 5 %), writes
optimisation_outputs/cutoff_rule3.md and regenerates ASSUMPTIONS.md section 8, which carries it.
"""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "optimisation_outputs"
CAPS = ["cap_wind", "cap_offshore", "cap_solar", "cap_batt_p", "cap_batt_e", "cap_ely", "cap_tank", "cap_fc", "cap_ge", "cap_grid"]
TOL = 0.05
# Size floor (user, 12 Nov 2026): a capacity counts in the test only where the asset is
# material in that design, at least 1 % of its supply carbon (the building's constant left
# out) or of its cost, in the central or the upper run. Below that, a size is not a stable
# result: the 12 Nov sign-off's lowest-carbon battery (11-21 MWh beside ~480 MW of wind)
# moved 10-80 % when unrelated groups were added back one at a time
# (sensitivity_cutoff_groups_1112_*), and 30-200 % on many screened inputs, while total
# carbon moved under 1 %. Moves of such assets are still printed, marked "below floor".
FLOOR = 0.01
GWP_PARTS = {
    "cap_wind": ["wind", "wind step-up transformers"],
    "cap_offshore": ["offshore wind"],
    "cap_solar": ["solar", "solar step-up transformers"],
    "cap_batt_e": ["battery cells and container"],
    "cap_batt_p": ["battery power conversion", "battery step-up transformers"],
    "cap_ely": ["electrolyser", "electrolyser stack replacements"],
    "cap_tank": ["H2 tank"],
    "cap_fc": ["fuel cell stack replacements", "fuel cell BoP replacements", "fuel cell step-up transformers"],
    "cap_ge": ["gas engines"],
    "cap_grid": ["grid connection", "grid connection cable"],
}
COST_PARTS = {  # the battery's cost is one line for both of its capacities
    "cap_wind": ["wind"], "cap_offshore": ["offshore wind"], "cap_solar": ["solar"],
    "cap_batt_e": ["battery"], "cap_batt_p": ["battery"], "cap_ely": ["electrolyser"],
    "cap_tank": ["H2 tank"], "cap_fc": ["fuel cell"], "cap_ge": ["gas engines"], "cap_grid": ["grid connection", "fixed charges and cable"],
}


def built(row):
    return {c for c in CAPS if c in row and row[c] > 1e-6}


def share(row, cap):
    """The asset's larger share of the design's supply carbon or of its cost."""
    supply = row.gwp_t_per_year - row.get("gwp_t:constant", 0.0)
    g = sum(row.get(f"gwp_t:{p}", 0.0) for p in GWP_PARTS[cap])
    c = sum(row.get(f"cost_m:{p}", 0.0) for p in COST_PARTS[cap])
    return max(g / supply if supply > 0 else 0.0, c / row.cost_m_GBP_per_year if row.cost_m_GBP_per_year > 0 else 0.0)


def material(base, up, cap):
    return max(share(base, cap), share(up, cap)) >= FLOOR


lines = ["### Rule 3 — the design-change test", "",
         "The two reference cases re-solved at both anchors with every still-excluded flow added at its",
         "upper estimate (`dc_inputs.build_tech(cutoff=\"upper\")`, sensitivity knob `cutoff`), against the",
         "central model. Q4's test: the same technologies are built and no built capacity moves by more than",
         "5 %, counting only assets that are at least 1 % of the design's supply carbon or cost (the size",
         "floor, 12 Nov 2026: a smaller asset's size is not a stable result). Solved "+ ", ".join(sorted({__import__("datetime").date.fromtimestamp(p.stat().st_mtime).isoformat()
                                            for p in OUT.glob("sensitivity_cutoff_*.csv")
                                            if p.stem.split("cutoff_", 1)[1] in ("norfolk_grid_green", "islanded_h2")}))
         + "; `optimisation_outputs/sensitivity_cutoff_*.csv`.", "",
         "| Case | Anchor | Technologies built | Same with upper? | Largest capacity move | GWP t/yr, central → upper | Verdict |",
         "|---|---|---|---|---|---|---|"]
verdicts = []
for case in ("norfolk_grid_green", "islanded_h2"):
    path = OUT / f"sensitivity_cutoff_{case}.csv"
    if not path.exists():
        lines.append(f"| {case} | — | — | — | — | — | not run |")
        verdicts.append(False)
        continue
    df = pd.read_csv(path)
    for anchor in ("min_cost", "min_gwp"):
        base = df[(df.objective == anchor) & (df.variant == "central")].iloc[0]
        up = df[(df.objective == anchor) & (df.variant == "cutoff=upper")].iloc[0]
        b0, b1 = built(base), built(up)
        moves = {c: up[c] / base[c] - 1 for c in b0 & b1}
        mat = {c for c in b0 | b1 if material(base, up, c)}
        counted = {c: m for c, m in moves.items() if c in mat}
        worst = max((counted or moves).items(), key=lambda kv: abs(kv[1]))
        small = [f"{c[4:]} {m:+.1%}" for c, m in moves.items() if c not in mat and abs(m) > TOL]
        same = (b0 & mat) == (b1 & mat)
        ok = same and all(abs(m) <= TOL for m in counted.values())
        verdicts.append(ok)
        lines.append(f"| {case} | {anchor} | {', '.join(sorted(c[4:] for c in b0))} | "
                     f"{'yes' if same else 'no: ' + ', '.join(sorted(c[4:] for c in (b0 ^ b1) & mat))} | "
                     f"{worst[0][4:]} {worst[1]:+.1%}"
                     + (f" (below floor: {', '.join(small)})" if small else "")
                     + f" | {base.gwp_t_per_year:,.0f} → {up.gwp_t_per_year:,.0f} | {'pass' if ok else 'FAIL'} |")
summary = ("**Rule 3 passes**: at both anchors of both cases the upper-estimate run builds the same technologies "
           "and moves no material capacity by more than 5 %." if verdicts and all(verdicts) else
           "**Rule 3 fails** on at least one case; the flows that drive the change are to be included (step 5).")
lines += ["", summary, "", "The islanded case has no grid connection.", ""]
text = "\n".join(lines)
print(text)

(OUT / "cutoff_rule3.md").write_text(text, encoding="utf-8", newline="\n")
sys.path.insert(0, str(ROOT))
from optimisation import cutoff, dc_inputs as I  # noqa: E402
tech = I.build_tech("north_norfolk", {"capacity_GBP_per_MW_year": 0.0, "fixed_GBP_per_year": 0.0}, h2_colour="green")
cutoff.write_assumptions(tech)
print("optimisation_outputs/cutoff_rule3.md written and ASSUMPTIONS section 8 regenerated")
