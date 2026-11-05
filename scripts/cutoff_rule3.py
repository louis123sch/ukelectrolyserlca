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
CAPS = ["cap_wind", "cap_offshore", "cap_solar", "cap_batt_p", "cap_batt_e", "cap_ely", "cap_tank", "cap_fc", "cap_grid"]
TOL = 0.05


def built(row):
    return {c for c in CAPS if c in row and row[c] > 1e-6}


lines = ["### Rule 3 — the design-change test", "",
         "The two reference cases re-solved at both anchors with every still-excluded flow added at its",
         "upper estimate (`dc_inputs.build_tech(cutoff=\"upper\")`, sensitivity knob `cutoff`), against the",
         "central model. Q4's test: the same technologies are built and no built capacity moves by more than",
         "5 %. Solved 23 Oct 2026; `optimisation_outputs/sensitivity_cutoff_*.csv`.", "",
         "| Case | Anchor | Technologies built | Same with upper? | Largest capacity move | GWP t/yr, central → upper | Verdict |",
         "|---|---|---|---|---|---|---|"]
verdicts = []
for case in ("london_grid", "islanded_h2"):
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
        worst = max(moves.items(), key=lambda kv: abs(kv[1]))
        ok = b0 == b1 and all(abs(m) <= TOL for m in moves.values())
        verdicts.append(ok)
        lines.append(f"| {case} | {anchor} | {', '.join(sorted(c[4:] for c in b0))} | "
                     f"{'yes' if b0 == b1 else 'no: ' + ', '.join(sorted(c[4:] for c in b0 ^ b1))} | "
                     f"{worst[0][4:]} {worst[1]:+.1%} | {base.gwp_t_per_year:,.0f} → {up.gwp_t_per_year:,.0f} | "
                     f"{'pass' if ok else 'FAIL'} |")
summary = ("**Rule 3 passes**: at both anchors of both cases the upper-estimate run builds the same technologies "
           "and moves no capacity by more than 5 %." if verdicts and all(verdicts) else
           "**Rule 3 fails** on at least one case; the flows that drive the change are to be included (step 5).")
lines += ["", summary, "",
          "The London case was solved with the grid connection at 282.0 kg CO2e per MW per year; the switchyard's",
          "share of Leng's construction machinery (+4.85, carried since 22 Oct 2026) was added while it ran. At the",
          "145 MW connection the minimum-cost design builds that is 0.7 t CO2e a year, under a millionth of the",
          "system, so it cannot move a design. The islanded case has no grid connection.", ""]
text = "\n".join(lines)
print(text)

(OUT / "cutoff_rule3.md").write_text(text, encoding="utf-8", newline="\n")
sys.path.insert(0, str(ROOT))
from optimisation import cutoff, dc_inputs as I  # noqa: E402
tech = I.build_tech("london", {"capacity_GBP_per_MW_year": 0.0, "fixed_GBP_per_year": 0.0}, h2_colour="green")
cutoff.write_assumptions(tech)
print("optimisation_outputs/cutoff_rule3.md written and ASSUMPTIONS section 8 regenerated")
