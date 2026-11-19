#!/usr/bin/env python
"""The screened inputs at their ranges (TESTING.md step 6): pick what goes hourly, then judge it.

    python -m optimisation.sensitivity shaky                     # the rig: sensitivity_shaky_<case>_4h.csv
    python scripts/shaky_judge.py pick                           # writes optimisation_outputs/shaky_hourly.txt
    python -m optimisation.sensitivity shaky norfolk_grid_green --hours=1 --only=optimisation_outputs/shaky_hourly.txt
    python scripts/shaky_judge.py judge                          # writes optimisation_outputs/shaky_inputs.md

The test is the cut-off rule's (CUTOFF_RULE_PLAN.md Q4): at each anchor, the same
technologies are built and no built size moves by more than 5 %. A rig result
cannot pass it (TESTING.md): it compares rig with rig, and only decides what is
solved hourly. Hourly, on North Norfolk (the reference site; user, 10 Nov 2026):
every variant that moves a size by more than 3 % on the rig or changes what is
built, and battery carbon and fuel cell capital and running-hours life whatever
the rig says, because a 4-hour step smooths the daily cycling those depend on.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "optimisation_outputs"
CAPS = ["cap_wind", "cap_solar", "cap_batt_p", "cap_batt_e", "cap_ely", "cap_tank", "cap_fc", "cap_ge", "cap_grid"]
RIG_FLAG = 0.03
TOL = 0.05
HOURLY_CASE = "norfolk_grid_green"
CASES = ("islanded_h2", "norfolk_grid_green")
LIST = OUT / "shaky_hourly.txt"
# Confirmed hourly whatever the rig says: battery carbon (named by the supervisor)
# and the fuel cell's capital and running-hours life, which turn on the daily
# cycling a 4-hour step smooths. Six variants: about 12 answers, a night.
ALWAYS = ("push=battery.energy_per_usable_kWh*", "push=cost.fuel_cell.capex_per_kW*", "fc_stack_duty_hours=")


def built(row) -> set:
    return {c for c in CAPS if c in row and row[c] > 1e-6}


def compare(df: pd.DataFrame) -> pd.DataFrame:
    """Each variant against its central row at the same anchor."""
    rows = []
    for _, r in df[df.variant != "central"].iterrows():
        base = df[(df.variant == "central") & (df.objective == r.objective)]
        if base.empty:
            continue
        b = base.iloc[0]
        b0, b1 = built(b), built(r)
        moves = {c: r[c] / b[c] - 1 for c in b0 & b1}
        worst = max(moves.items(), key=lambda kv: abs(kv[1])) if moves else ("", 0.0)
        rows.append(dict(variant=r.variant, objective=r.objective, same_built=b0 == b1,
                         appear=", ".join(sorted(c[4:] for c in b1 - b0)),
                         go=", ".join(sorted(c[4:] for c in b0 - b1)),
                         worst=worst[0][4:], worst_move=worst[1],
                         d_cost_pct=r.get("d_cost_m_GBP_per_year_pct"), d_gwp_pct=r.get("d_gwp_t_per_year_pct")))
    return pd.DataFrame(rows)


def pick() -> list[str]:
    path = OUT / f"sensitivity_shaky_{HOURLY_CASE}_4h.csv"
    if not path.exists():
        sys.exit(f"no rig file {path.name}; run: python -m optimisation.sensitivity shaky")
    seen = []
    for case in CASES:
        p = OUT / f"sensitivity_shaky_{case}_4h.csv"
        if not p.exists():
            continue
        c = compare(pd.read_csv(p))
        flagged = c[(~c.same_built) | (c.worst_move.abs() > RIG_FLAG)].variant
        seen += [v for v in flagged if v not in seen]
    hourly_variants = set(pd.read_csv(path).variant) - {"central"}
    always = [v for v in sorted(hourly_variants) if v.startswith(ALWAYS)]
    chosen = [v for v in seen if v in hourly_variants] + [v for v in always if v not in seen]
    LIST.write_text("\n".join(chosen) + "\n", encoding="utf-8")
    print(f"{len(chosen)} variants for the hourly run on {HOURLY_CASE} -> {LIST.relative_to(ROOT)}")
    for v in chosen:
        print("  ", v, "(rig flag)" if v in seen else "(battery / fuel cell)")
    return chosen


def table(c: pd.DataFrame, tol: float) -> list[str]:
    out = ["| Variant | Anchor | Same technologies? | Largest size move | Cost | Carbon | |",
           "|---|---|---|---|---|---|---|"]
    for _, r in c.iterrows():
        same = "yes" if r.same_built else "no: " + "; ".join(x for x in (
            f"+{r.appear}" if r.appear else "", f"-{r.go}" if r.go else "") if x)
        ok = r.same_built and abs(r.worst_move) <= tol
        out.append(f"| {r.variant} | {r.objective} | {same} | {r.worst} {r.worst_move:+.1%} | "
                   f"{r.d_cost_pct:+.2f} % | {r.d_gwp_pct:+.2f} % | {'holds' if ok else '**moves**'} |")
    return out


def judge():
    lines = ["# The screened inputs at their ranges", "",
             "The inputs `scripts/screen_inputs.py` picked (`input_screen.md`), one at a time at their ranges "
             "(`sensitivity.SHAKY_KNOBS`). The test: the same technologies built and no built size moved by more "
             "than 5 % at the same anchor. Rig rows compare rig with rig and only chose what was solved hourly; "
             "the verdicts are the hourly ones.", ""]
    hourly = OUT / f"sensitivity_shaky_{HOURLY_CASE}.csv"
    if hourly.exists():
        c = compare(pd.read_csv(hourly))
        lines += [f"## Hourly, {HOURLY_CASE}", ""] + table(c, TOL) + [""]
        moved = sorted(set(c[(~c.same_built) | (c.worst_move.abs() > TOL)].variant))
        lines += [("**Every hourly variant holds the design.**" if not moved else
                   "**These move the design and are reported with the result:** " + ", ".join(moved)), ""]
    else:
        lines += ["No hourly run yet.", ""]
    for case in CASES:
        p = OUT / f"sensitivity_shaky_{case}_4h.csv"
        if p.exists():
            lines += [f"## Rig (4-hour steps), {case}", "", "Flag at 3 % on the rig.", ""] + table(compare(pd.read_csv(p)), RIG_FLAG) + [""]
    text = "\n".join(lines)
    (OUT / "shaky_inputs.md").write_text(text, encoding="utf-8", newline="\n")
    print(text)


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "judge"
    {"pick": pick, "judge": judge}[what]()
