"""
Recalculate the cost and carbon workbooks in Excel and hold every cell to the model.
=============================================================================

``scripts/build_workbooks.py`` writes each workbook with a sidecar,
``<name>.expected.json``: every named cell's value as the model computed it.
This opens each workbook in Excel itself (through COM; Excel must be
installed), forces a full recalculation, and compares every named cell with
that value. A formula that links the wrong cell, an Excel function that differs
from the Python one, or a name Excel cannot resolve fails here.

It also holds each point's total - the parts added in Excel - to the run's own
total, so the workbook's breakdown is the run's result and not a near miss.

    python scripts/check_workbooks.py            # both workbooks
    python scripts/check_workbooks.py --rel 1e-9 # tolerance, relative (default)

Exit code 0 when every cell matches, 1 when any does not, 2 when Excel cannot
be started.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "optimisation_outputs"
BOOKS = ("cost_workbook.xlsx", "carbon_workbook.xlsx")
# The carbon workbook adds each inventory activity up from its inputs' scores.
# Brightway scores every activity in one sparse solve, good to about one part
# in ten million, so a sum of its scores and its own score for the total agree
# to that and no closer. Held to one part in a million.
REL_BY_BOOK = {"carbon_workbook.xlsx": 1e-6}


def excel():
    try:
        import win32com.client as w
        app = w.DispatchEx("Excel.Application")
        app.Visible = False
        app.DisplayAlerts = False
        return app
    except Exception as e:                                   # noqa: BLE001
        print(f"cannot start Excel: {e}")
        sys.exit(2)


def check(path: Path, app, rel: float, rel_total: float) -> list[str]:
    expected = json.loads(path.with_suffix(".expected.json").read_text(encoding="utf-8"))
    wb = app.Workbooks.Open(str(path), UpdateLinks=0, ReadOnly=True)
    fails = []
    try:
        app.CalculateFull()
        for name, want in expected.items():
            try:
                got = wb.Names(name).RefersToRange.Value
            except Exception as e:                           # noqa: BLE001
                fails.append(f"{name}: Excel cannot read it ({e.__class__.__name__})")
                continue
            if not isinstance(got, (int, float)):
                fails.append(f"{name}: Excel gives {got!r}, the model {want:.9g}")
                continue
            tol = rel_total if name.endswith(".total") else rel
            if abs(got - want) > tol * max(1.0, abs(want), abs(got)):
                fails.append(f"{name}: Excel gives {got:.12g}, the model {want:.12g}")
        print(f"{path.name}: {len(expected)} cells recalculated in Excel, {len(fails)} off")
    finally:
        wb.Close(SaveChanges=False)
    return fails


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--rel", type=float, default=1e-9, help="relative tolerance per cell")
    ap.add_argument("--dir", help="the folder holding the workbooks (default: optimisation_outputs)")
    ap.add_argument("--rel-total", type=float, default=1e-6,
                    help="relative tolerance for a point's total against the run's own")
    a = ap.parse_args()
    app = excel()
    fails = []
    try:
        for b in BOOKS:
            p = (Path(a.dir) if a.dir else OUT) / b
            if not p.exists():
                fails.append(f"{b}: not built (scripts/build_workbooks.py)")
                continue
            fails += [f"{b}: {f}" for f in check(p, app, max(a.rel, REL_BY_BOOK.get(b, 0.0)), a.rel_total)]
    finally:
        app.Quit()
    for f in fails:
        print("FAIL", f)
    print("OK: every cell recalculates to the model's value" if not fails else f"{len(fails)} failures")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
