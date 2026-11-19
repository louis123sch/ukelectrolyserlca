#!/usr/bin/env python
"""Gurobi against HiGHS on the real cases, hourly (10 Nov 2026).

    set DC_SOLVER=gurobi                        # the default since 11 Nov 2026
    python scripts/solver_compare.py solve      # central rows, both anchors: sensitivity_solver_gurobi_<case>.csv
    python scripts/solver_compare.py judge      # optimisation_outputs/solver_compare.md

The HiGHS side is the central rows of the hourly cost cut-off run of 10 Nov
(sign-off step 4, same cases, same price-list handling: every list at the loose
gap), read from --highs-dir. Neither the model nor its inputs changed between
that run and this one: only the solver and the push knob, which the central rows
do not use. The question: the same design (the cut-off rule's test: the same
technologies and no size moved by more than 5 %, here expected to agree far more
closely), the same totals, and how much faster.
"""
from __future__ import annotations

import os
import sys
from dataclasses import replace
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
OUT = ROOT / "optimisation_outputs"
CASES = ("islanded_h2", "norfolk_grid")
CAPS = ["cap_wind", "cap_solar", "cap_batt_p", "cap_batt_e", "cap_ely", "cap_tank", "cap_fc", "cap_ge", "cap_grid"]
HIGHS_DIR = Path(next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--highs-dir=")),
                      r"C:\Users\ls1524\Desktop\ukdclca-signoff\optimisation_outputs\signoff\2026-11-10_0831\results"))


def solve():
    from optimisation import dc_model as M, sensitivity as S
    solver = M.current_solver()
    for c in CASES:
        case = replace(S.CASES[c], resample_hours=1.0)
        S.run(case, [{}], name=f"solver_{solver}_{c}", list_choice="fixed")


def judge():
    lines = ["# Gurobi against HiGHS, hourly, central rows", "",
             f"HiGHS: the hourly cost cut-off run of 10 Nov 2026 (`{HIGHS_DIR}`). "
             "Gurobi: `scripts/solver_compare.py`, the same cases and price-list handling. Minutes are per anchor "
             "(the lowest-cost or lowest-carbon design with its tie-breaks).", "",
             "| Case | Anchor | Minutes, HiGHS → Gurobi | Cost, £m/yr | Carbon, t/yr | Same technologies? | Largest size difference |",
             "|---|---|---|---|---|---|---|"]
    for c in CASES:
        g_path = OUT / f"sensitivity_solver_gurobi_{c}.csv"
        h_path = HIGHS_DIR / f"sensitivity_cost_cutoff_{c}.csv"
        if not (g_path.exists() and h_path.exists()):
            lines.append(f"| {c} | — | missing {'Gurobi' if not g_path.exists() else 'HiGHS'} file | | | | |")
            continue
        g, h = pd.read_csv(g_path), pd.read_csv(h_path)
        h = h[h.variant == "central"]
        for anchor in ("min_cost", "min_gwp"):
            gr, hr = g[g.objective == anchor].iloc[0], h[h.objective == anchor].iloc[0]
            bg = {k for k in CAPS if gr.get(k, 0.0) > 1e-6}         # cap_ge absent before 13 Nov 2026
            bh = {k for k in CAPS if hr.get(k, 0.0) > 1e-6}
            diffs = {k: gr[k] / hr[k] - 1 for k in bg & bh}
            worst = max(diffs.items(), key=lambda kv: abs(kv[1])) if diffs else ("", 0.0)
            lines.append(
                f"| {c} | {anchor} | {hr.solve_s / 60:.1f} → {gr.solve_s / 60:.1f} "
                f"(×{hr.solve_s / max(gr.solve_s, 1e-9):.1f}) | {hr.cost_m_GBP_per_year:.3f} → {gr.cost_m_GBP_per_year:.3f} | "
                f"{hr.gwp_t_per_year:,.0f} → {gr.gwp_t_per_year:,.0f} | "
                f"{'yes' if bg == bh else 'no: ' + ', '.join(sorted(k[4:] for k in bg ^ bh))} | "
                f"{worst[0][4:]} {worst[1]:+.2%} |")
    text = "\n".join(lines) + "\n"
    (OUT / "solver_compare.md").write_text(text, encoding="utf-8", newline="\n")
    print(text)


if __name__ == "__main__":
    what = next((a for a in sys.argv[1:] if not a.startswith("--")), "judge")
    {"solve": solve, "judge": judge}[what]()
