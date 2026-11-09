#!/usr/bin/env python
"""Run the sign-off in docs/TESTING.md unattended, one step at a time, and say how it went.

    python scripts/signoff.py                       # every step, in order
    python scripts/signoff.py --run-to PATH         # also the North Norfolk optimiser run, saved under PATH
    python scripts/signoff.py --only 1 2 8 3 4 5   # just those steps, in that order

Meant to run from a clean, committed tree (a separate worktree is safest, so nothing edited
meanwhile in the working checkout can reach it). Each step's output goes to
``optimisation_outputs/signoff/<date>/step_<n>.log``; a step that fails is recorded and the
next one still runs, as the steps are independent. ``SIGNOFF_RUNNING`` in the tree's root says
the sign-off is still going (other overnight jobs wait for it to go); ``SUMMARY.md`` beside the
logs is the morning read. Nothing here commits, pushes or deletes anything but the one file
TESTING.md says to delete (step 3's resumable sweep).

Steps (TESTING.md): 1 clean tree; 2 every test; R the North Norfolk run (optional, for the maps
and workbooks: dc_runner, the page's path, dispatch saved); 3 connection's price at +/-50 %;
4 cost cut-off; 5 carbon cut-off; 6 assumptions at their ranges; 7 carbon inputs at their ranges;
8 both maps and their tests.
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable
LOCK = ROOT / "SIGNOFF_RUNNING"

RUN_SNIPPET = r"""
import sys, json
from pathlib import Path
sys.path.insert(0, r"{root}")
from optimisation import dc_runner, sites
from optimisation import dc_architectures as A
flags = dict(grid=True, wind=True, offshore_wind=False, solar=True, battery=True,
             electrolyser=True, tank=True, fuel_cell=True, buy_h2=True, buy_h2_2=False)
scen = A.Scenario(n=0, architecture="custom", label="every asset (North Norfolk reference)",
                  assets=flags, ely_tech="PEM operation", h2_colour="green", strategy="free")
site = sites.get("north_norfolk")
out = Path(r"{out}") / f"{{site.key}}_100MW_2025_custom"
s = dc_runner.run_one(scen, site=site, start="2025-01-01", end="2025-12-29", connection_mode="room",
                      connection_solve="loose", size_mw_it=100.0, pue=None, resample_hours=1.0, points=5,
                      cost_case="central", horizon_years=25.0, unserved_fraction=0.0, out_root=out,
                      save_dispatch=True, refresh=True, progress=lambda t: print("  ", t, flush=True))
print("RUN FOLDER", out / scen.key, flush=True)
print(json.dumps({{k: s.get(k) for k in ("min_cost", "knee", "min_gwp")}}, default=str)[:4000])
"""


def steps(run_to: str | None):
    hours = ["--hours=1"]
    out = [
        ("1", "Clean tree", [["git", "status", "--porcelain"], ["git", "rev-parse", "HEAD"]]),
        ("2", "Every test", [[PY, "-m", "pytest", "tests", "-q", "-p", "no:cacheprovider"]]),
    ]
    if run_to:
        out.append(("R", "North Norfolk run for the maps and workbooks",
                    [[PY, "-c", RUN_SNIPPET.format(root=ROOT, out=run_to)]]))
    out += [
        ("3", "Connection's price, +/-50 %",
         ["DELETE optimisation_outputs/sensitivity_connection_norfolk_150_room.csv",
          [PY, "-m", "optimisation.sensitivity", "connection", "norfolk_150_room", *hours],
          [PY, "scripts/connection_sensitivity.py"]]),
        ("4", "Cost cut-off, rule 3", [[PY, "-m", "optimisation.sensitivity", "cost_cutoff", *hours]]),
        ("5", "Carbon cut-off, rule 3", [[PY, "-m", "optimisation.sensitivity", "cutoff", *hours],
                                         [PY, "scripts/cutoff_rule3.py"]]),
        ("6", "Assumptions at their ranges", [[PY, "-m", "optimisation.sensitivity", "assumptions", *hours]]),
        ("7", "Carbon inputs at their ranges", [[PY, "-m", "optimisation.sensitivity", "carbon", *hours]]),
        ("8", "Both maps", [[PY, "scripts/build_lca_map.py"], [PY, "scripts/build_cost_map.py"],
                            [PY, "-m", "pytest", "tests/test_cost_map.py", "tests/test_lca_map.py", "-q",
                             "-p", "no:cacheprovider"]]),
    ]
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-to", default=None, help="save the North Norfolk run under this dc_runs folder")
    ap.add_argument("--only", nargs="*", default=None)
    a = ap.parse_args(argv)
    os.environ.setdefault("MKL_THREADING_LAYER", "TBB")
    stamp = dt.datetime.now().strftime("%Y-%m-%d_%H%M")
    logdir = ROOT / "optimisation_outputs" / "signoff" / stamp
    logdir.mkdir(parents=True, exist_ok=True)
    LOCK.write_text(f"started {stamp}, logs in {logdir}\n", encoding="utf-8")
    head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    rows = []
    plan = steps(a.run_to)
    if a.only:                      # the steps asked for, in the order asked
        by = {n: (n, name, cmds) for n, name, cmds in plan}
        plan = [by[n] for n in a.only if n in by]
    try:
        for n, name, cmds in plan:
            log = logdir / f"step_{n}.log"
            t0, ok, note = time.time(), True, ""
            with log.open("w", encoding="utf-8", errors="replace") as f:
                f.write(f"# step {n}: {name}\n# commit {head}\n")
                for c in cmds:
                    if isinstance(c, str) and c.startswith("DELETE "):
                        p = ROOT / c.split(" ", 1)[1]
                        p.unlink(missing_ok=True)
                        f.write(f"$ deleted {p}\n")
                        continue
                    f.write(f"\n$ {' '.join(map(str, c))}\n")
                    f.flush()
                    r = subprocess.run(c, cwd=ROOT, stdout=f, stderr=subprocess.STDOUT, text=True)
                    if r.returncode != 0:
                        ok, note = False, f"exit {r.returncode} from {' '.join(map(str, c[:4]))}"
                        break
                if n == "1":
                    dirty = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"], cwd=ROOT,
                                           capture_output=True, text=True).stdout.strip()
                    if dirty:
                        ok, note = False, "tracked files changed: not a committed tree"
            mins = (time.time() - t0) / 60.0
            tail = log.read_text(encoding="utf-8", errors="replace").strip().splitlines()[-3:]
            rows.append((n, name, "done" if ok else "FAILED", f"{mins:,.0f} min", note or " / ".join(tail)[:300]))
            _summary(logdir, head, rows, running=True)
    finally:
        _summary(logdir, head, rows, running=False)
        LOCK.unlink(missing_ok=True)
    return 0 if all(r[2] == "done" for r in rows) else 1


def _summary(logdir: Path, head: str, rows, running: bool):
    lines = [f"# Sign-off, commit {head}", "",
             "Still running." if running else f"Finished {dt.datetime.now():%Y-%m-%d %H:%M}.", "",
             "Each step's own judge (TESTING.md) decides pass or fail; \"done\" means the commands ran. "
             "Read each step's log for its verdict.", "",
             "| Step | Check | Ran | Time | Last lines / note |", "|---|---|---|---|---|"]
    lines += [f"| {n} | {name} | {st} | {t} | {note.replace('|', '/')} |" for n, name, st, t, note in rows]
    (logdir / "SUMMARY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
