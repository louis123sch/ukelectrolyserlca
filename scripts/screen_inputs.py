#!/usr/bin/env python
"""Which inputs could matter? A screen that needs no optimiser run.

Every number the model records with ``T.step`` / ``T.cost`` is an input or a
step made from inputs. This script takes each recorded *leaf* (a step that uses
no other recorded step: a figure read from a source, an assumption, a proxy),
pushes it to half and to one and a half times its value through the real code
(``build_tech``, and ``build_series`` with ``--series``), and re-scores a saved
run's three points (lowest cost, knee, lowest carbon) with the design held
fixed. It reports, per input:

- its grade (transcribed / assumed / proxy / derived) - how unsure it is;
- how far each total (cost, carbon) moves at each point - how much it could
  matter to the answer that was built;
- the largest move in any one coefficient, and whether that coefficient belongs
  to a technology a point does not build - such an input scores zero on the
  totals but could still get that technology built, so it is flagged.

What it cannot say is whether the design changes: that needs a solve. It ranks
the candidates for the +/-30-50 % runs (sensitivity.py); it decides nothing.

    python scripts/screen_inputs.py                 # build_tech side, a few minutes
    python scripts/screen_inputs.py --series        # also the series side (about a minute an input)
    python scripts/screen_inputs.py --run <folder>  # a saved run other than the newest

Writes optimisation_outputs/input_screen.csv (one row per recorded step or sweep
argument) and input_screen_shares.csv (each term's share of each total). The
written reading of a run is optimisation_outputs/input_screen.md.

Limits, stated in the output: a step the code only records (it goes on with a
figure made from it, or the value is a table) cannot be pushed and is marked;
inputs that act through how the plant runs (fuel cell calendar life, storage
losses, transformer loadings) move nothing with the dispatch held fixed and need
a solve; the grid's prices and carbon are series, judged by their share instead.
"""
from __future__ import annotations

import argparse
import dataclasses
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]

PUSH = (0.5, 1.5)
OUT_CSV = ROOT / "optimisation_outputs" / "input_screen.csv"
OUT_MD = ROOT / "optimisation_outputs" / "input_screen.md"
POINTS = ("min_cost", "knee", "min_gwp")
COST_GROUPS = ("cost_capital", "cost_operational", "cost_constant")
GWP_GROUPS = ("gwp_embodied", "gwp_operational", "gwp_facility")
# A coefficient's technology, for the "not built" flag: the capacity it multiplies.
CAP_OF = {"wind": "cap_wind", "offshore": "cap_offshore", "solar": "cap_solar", "batt": "cap_batt_e",
          "battery": "cap_batt_e", "ely": "cap_ely", "electrolyser": "cap_ely", "tank": "cap_tank",
          "fc": "cap_fc", "grid": "cap_grid"}


def totals(tech, series, pts, assets):
    from build_workbooks import evaluate_terms
    out = {}
    for pt in POINTS:
        p = pts[pt]
        terms, _ = evaluate_terms(tech, series, p["sc"], p["hr"], pt, None, assets)
        out[pt] = (sum(v.val for g in COST_GROUPS for v in terms[g].values()),
                   sum(v.val for g in GWP_GROUPS for v in terms[g].values()))
    return out


def coefficients(tech) -> dict:
    from optimisation import dc_model as M
    out = {}
    for f in dataclasses.fields(tech):
        v = getattr(tech, f.name)
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            out[f.name] = float(v)
    for i, o in enumerate(M.connection_options_of(tech) or ()):
        for f in ("cost_per_mw_year", "cost_fixed_per_year", "gwp_per_mw_year", "gwp_fixed_per_year"):
            v = getattr(o, f)
            if v is not None:
                out[f"option{i + 1}.{f}"] = float(v)
    return out


def cap_of(field: str):
    body = field.split("_", 1)[1] if "_" in field else field
    for stem, cap in CAP_OF.items():
        if body == stem or body.startswith(stem + "_") or body.startswith(stem):
            return cap
    return None


def leaves(rec) -> list[str]:
    keys = set(rec.steps)
    return [k for k, s in rec.steps.items()
            if not any(isinstance(u, str) and u in keys for u in s.uses)]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default=None)
    ap.add_argument("--series", action="store_true", help="also push the inputs build_series records")
    a = ap.parse_args(argv)

    from build_workbooks import choose_run, record_run, run_points
    from optimisation import dc_inputs as I, dc_runner as R, trace as T

    folder = choose_run(a.run)
    if folder is None:
        sys.exit("no finished run in optimisation_outputs/dc_runs; pass --run <folder>")
    t0 = time.time()
    rec, L = record_run(folder)
    problems = []
    pts = run_points(folder, L, problems)
    if problems:
        sys.exit("the saved run does not rebuild cleanly: " + "; ".join(problems))
    with T.recording() as rtech:
        I.build_tech(L.site, L.meta, **L.tech_kw)
    base = totals(L.tech, L.series, pts, L.assets)
    base_coef = coefficients(L.tech)
    built = {pt: pts[pt]["build"] for pt in POINTS}
    print(f"run {folder.name}: rebuilt in {time.time() - t0:.0f} s; "
          + ", ".join(f"{pt} £{base[pt][0] / 1e6:.1f} m, {base[pt][1] / 1e6:.2f} kt" for pt in POINTS))

    # the screen holds itself to the run: pushing by 1 changes nothing
    with T.pushed("__none__", 1.0):
        again = totals(I.build_tech(L.site, L.meta, **L.tech_kw), L.series, pts, L.assets)
    for pt in POINTS:
        for i in (0, 1):
            if not np.isclose(again[pt][i], base[pt][i], rtol=1e-9):
                sys.exit(f"a rebuilt build_tech does not reproduce the run at {pt}")

    # Every step build_tech records, not only the leaves: some sources are
    # recorded as read but the code goes on with a figure derived from them
    # (the battery's capital is a fit through NESO's table), so the first step
    # that moves the answer can be a derived one. A step that moves nothing is
    # kept, marked "recorded only".
    tech_keys = list(rtech.steps)
    series_keys = [k for k in leaves(rec) if k not in rtech.steps] if a.series else []
    rows = []
    jobs = [(k, "tech") for k in tech_keys] + [(k, "series") for k in series_keys]
    for n, (key, side) in enumerate(jobs, 1):
        s = rec.steps.get(key) or rtech.steps[key]
        row = dict(key=key, title=s.title, grade=s.grade, side="cost" if s.side == "cost" else "carbon",
                   built_in=side, value=s.value, unit=s.unit, where=s.where)
        pushable = True
        for f in PUSH:
            hits = []
            try:
                with T.pushed(key, f) as hits:
                    if side == "tech":
                        tech, series = I.build_tech(L.site, L.meta, **L.tech_kw), L.series
                    else:
                        with T.quiet():
                            L2 = R.load_inputs(folder)
                        tech, series = L2.tech, L2.series
                tt = totals(tech, series, pts, L.assets)
            except Exception as e:                       # noqa: BLE001 - a count pushed to a fraction, say
                row["note"] = f"x{f} breaks the code: {type(e).__name__}: {e}"[:160]
                pushable = False
                break
            if not hits or not any(hits):
                row["note"] = "not a number the code reads back (a flag, a label or a table)"
                pushable = False
                break
            tag = "low" if f < 1 else "high"
            for pt in POINTS:
                row[f"cost_{pt}_{tag}_pct"] = 100 * (tt[pt][0] / base[pt][0] - 1)
                row[f"gwp_{pt}_{tag}_pct"] = 100 * (tt[pt][1] / base[pt][1] - 1)
            c = coefficients(tech)
            moves = {k: abs(c[k] / v - 1) for k, v in base_coef.items() if k in c and v}
            moves.update({k: float("inf") for k, v in base_coef.items() if k in c and not v and c[k]})
            if moves:
                kmax = max(moves, key=moves.get)
                if moves[kmax] * 100 > row.get("coef_move_pct", -1):
                    row["coef_move_pct"], row["coef_field"] = 100 * moves[kmax], kmax
        row["pushable"] = pushable
        if pushable:
            row["total_move_pct"] = max(abs(row[c]) for c in row if c.endswith("_pct") and c.startswith(("cost_", "gwp_")))
            if row["total_move_pct"] < 1e-9 and row.get("coef_move_pct", 0) < 1e-9:
                row["note"] = "recorded only: the code goes on with a figure made from it"
            cap = cap_of(row.get("coef_field") or "")
            row["unbuilt_at"] = ", ".join(pt for pt in POINTS if cap and built[pt].get(cap, 1.0) <= 1e-6) or ""
        rows.append(row)
        if n % 20 == 0:
            print(f"  {n} of {len(jobs)} ({time.time() - t0:.0f} s)")

    # The carbon coefficients come from cached Brightway scores: their T.step
    # records explain them but the code does not read the recorded value back,
    # so pushing a step moves nothing. The carbon side's assumptions are reached
    # instead through build_tech's own sweep arguments, at the ranges the sweeps
    # use (sensitivity.CARBON_KNOBS / ASSUMPTION_KNOBS), design held fixed.
    from optimisation import sensitivity as S
    skip = set(S.SERIES_KNOBS) | {"cutoff", "batt_max_duration_hours", "cost_case"}
    knobs = {**S.ASSUMPTION_KNOBS, **S.CARBON_KNOBS}
    for knob, values in knobs.items():
        if knob in skip:
            continue
        row = dict(key=f"knob:{knob}", title=f"sweep argument {knob}", grade="assumed", side="both",
                   built_in="knob", value=None, unit="", where="optimisation/sensitivity.py")
        moves = []
        for v in values:
            try:
                tech = I.build_tech(L.site, L.meta, **{**L.tech_kw, knob: v})
                tt = totals(tech, L.series, pts, L.assets)
            except Exception as e:                          # noqa: BLE001
                row["note"] = f"{knob}={v!r} fails: {type(e).__name__}: {e}"[:160]
                continue
            for pt in POINTS:
                row[f"cost_{pt}_{v}_pct"] = 100 * (tt[pt][0] / base[pt][0] - 1)
                row[f"gwp_{pt}_{v}_pct"] = 100 * (tt[pt][1] / base[pt][1] - 1)
                moves += [abs(row[f"cost_{pt}_{v}_pct"]), abs(row[f"gwp_{pt}_{v}_pct"])]
            c = coefficients(tech)
            cm = {k: abs(c[k] / b - 1) for k, b in base_coef.items() if k in c and b}
            if cm:
                kmax = max(cm, key=cm.get)
                if cm[kmax] * 100 > row.get("coef_move_pct", -1):
                    row["coef_move_pct"], row["coef_field"] = 100 * cm[kmax], kmax
        row["values"] = ", ".join(map(str, values))
        row["pushable"] = bool(moves)
        if moves:
            row["total_move_pct"] = max(moves)
            cap = cap_of(row.get("coef_field") or "")
            row["unbuilt_at"] = ", ".join(pt for pt in POINTS if cap and built[pt].get(cap, 1.0) <= 1e-6) or ""
        rows.append(row)

    # Each technology's share of each total: the most any input inside it could
    # move that total is half its share, at +/-50 %.
    from build_workbooks import evaluate_terms
    shares = []
    for pt in POINTS:
        terms, _ = evaluate_terms(L.tech, L.series, pts[pt]["sc"], pts[pt]["hr"], pt, None, L.assets)
        for side, groups, tot in (("cost", COST_GROUPS, base[pt][0]), ("carbon", GWP_GROUPS, base[pt][1])):
            for g in groups:
                for name, v in terms[g].items():
                    shares.append(dict(point=pt, side=side, term=name, value=v.val, share_pct=100 * v.val / tot))
    pd.DataFrame(shares).to_csv(OUT_CSV.with_name("input_screen_shares.csv"), index=False)

    df = pd.DataFrame(rows)
    df = df.sort_values(["pushable", "total_move_pct"], ascending=[False, False], na_position="last")
    df.to_csv(OUT_CSV, index=False)
    print(f"wrote {OUT_CSV.relative_to(ROOT)}: {len(df)} inputs, {int(df.pushable.sum())} pushed")
    return df, base, built, folder


if __name__ == "__main__":
    main()
