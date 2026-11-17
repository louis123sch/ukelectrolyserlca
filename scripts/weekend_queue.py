#!/usr/bin/env python
"""The weekend of 14-16 Nov 2026, one job at a time, after the sign-off (user, 13 Nov 2026).

    python scripts/weekend_queue.py                          # waits for SIGNOFF_RUNNING to go, then runs
    python scripts/weekend_queue.py --stop-at 2026-11-17T08:00
    pythonw scripts/weekend_queue.py --stop-at ...          # windowless; how it should be started

Order (user, revised 13 Nov 2026 evening): what gets built today at every site, then the
fixed-choice checks, then the hydrogen break-even prices hourly (the four representative sites
first, then every site and level; the second step reuses the first's results). No rig pass:
hourly everywhere instead. The blue what-if is dropped for this weekend (``scripts/uk_sites.py
--set blue`` later). The break-even goes last because it is the longest (estimated 20-50 h) and
resumes where it stopped; note a step already running carries on past ``--stop-at``.
Each step resumes where it stopped, so the queue can be run
again after an interruption. A step that fails is logged and the next one still runs; nothing
new starts after ``--stop-at``. Logs: ``optimisation_outputs/weekend_2026-11-14/``. Nothing here
commits, pushes or deletes anything. Remove ``WEEKEND_RUNNING`` in the tree's root only if the
queue died without doing so.
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
PY = str(Path(sys.executable).with_name("python.exe"))  # steps run on python.exe even when the queue is on pythonw.exe
# 16 Nov 2026: the first start (13 Nov) ran on main's Brightway project ("hydrogen-smr"), which
# has no gas engine database and none of this branch's new inventories. Every step now gets
# the branch's project and the settings the runs need, whatever shell started the queue.
BRANCH_PROJECT = "hydrogen-smr-sources"
ENV = dict(os.environ, DC_BW_PROJECT=BRANCH_PROJECT, MKL_THREADING_LAYER="TBB", PYTHONIOENCODING="utf-8")
# 16 Nov 2026: the queue died twice (Fri 18:36, Mon 14:11) from a stray Ctrl+C reaching the console
# window it ran in. Start it windowless (pythonw.exe) and give each step its own hidden console, so
# nothing else shares a window with the runs.
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
SIGNOFF_LOCK = ROOT / "SIGNOFF_RUNNING"
LOCK = ROOT / "WEEKEND_RUNNING"
LOGDIR = ROOT / "optimisation_outputs" / "weekend_2026-11-14"
REP = ["2", "15", "18", "23"]

STEPS = [
    ("1_present", "26 sites, everything on the table, green only", ["scripts/uk_sites.py", "--set", "present"]),
    ("2_checks", "Fixed choices one at a time, 4 sites, 25 MW and full grid", ["scripts/fixed_choice_checks.py"]),
    ("3_breakeven_hourly_rep", "Break-even green price, 4 sites, 25 MW and full grid (hourly)",
     ["scripts/breakeven_sites.py", "--sites", *REP, "--levels", "limited", "full"]),
    ("4_breakeven_hourly_all", "Break-even green price, every site and level, with and without engines (hourly)",
     ["scripts/breakeven_sites.py"]),
]


def log(msg: str):
    line = f"[{dt.datetime.now():%a %H:%M}] {msg}"
    if sys.stdout is not None:  # None when started windowless with pythonw.exe
        print(line, flush=True)
    with open(LOGDIR / "queue.log", "a", encoding="utf-8") as f:
        f.write(line + "\n")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--stop-at", default="2026-11-17T08:00")
    ap.add_argument("--only", nargs="*", default=None)
    a = ap.parse_args(argv)
    stop_at = dt.datetime.fromisoformat(a.stop_at)
    LOGDIR.mkdir(parents=True, exist_ok=True)
    if LOCK.exists():
        sys.exit("WEEKEND_RUNNING exists: the queue is already going (or died; remove the file to restart)")
    LOCK.write_text(f"started {dt.datetime.now():%Y-%m-%d %H:%M}\n", encoding="utf-8")
    try:
        while SIGNOFF_LOCK.exists():
            if dt.datetime.now() >= stop_at:
                log("stop time reached while waiting for the sign-off; nothing run")
                return 1
            time.sleep(120)
        log(f"sign-off finished; starting the queue (Brightway project {BRANCH_PROJECT}, stop at {stop_at:%a %d %b %H:%M})")
        for key, title, cmd in STEPS:
            if a.only and key not in a.only:
                continue
            if dt.datetime.now() >= stop_at:
                log(f"{key}: not started, past {stop_at:%a %H:%M}")
                continue
            log(f"{key}: {title}")
            t0 = time.time()
            with open(LOGDIR / f"{key}.log", "a", encoding="utf-8") as out:
                rc = subprocess.run([PY, *cmd], cwd=ROOT, env=ENV, stdout=out, stderr=subprocess.STDOUT,
                                    creationflags=NO_WINDOW).returncode
            log(f"{key}: exit {rc} after {(time.time() - t0) / 3600:.1f} h")
        log("queue finished")
    finally:
        LOCK.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
