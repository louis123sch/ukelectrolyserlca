#!/usr/bin/env python
"""The weekend of 14-16 Nov 2026, one job at a time, after the sign-off (user, 13 Nov 2026).

    python scripts/weekend_queue.py                          # waits for SIGNOFF_RUNNING to go, then runs
    python scripts/weekend_queue.py --stop-at 2026-11-17T08:00

Order (user's priority): what gets built today at every site, then the hydrogen break-even
prices (every site on the rig, then hourly at four), then the fixed-choice checks, then the
blue what-if if there is time. Each step resumes where it stopped, so the queue can be run
again after an interruption. A step that fails is logged and the next one still runs; nothing
new starts after ``--stop-at``. Logs: ``optimisation_outputs/weekend_2026-11-14/``. Nothing here
commits, pushes or deletes anything. Remove ``WEEKEND_RUNNING`` in the tree's root only if the
queue died without doing so.
"""
from __future__ import annotations

import argparse
import datetime as dt
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable
SIGNOFF_LOCK = ROOT / "SIGNOFF_RUNNING"
LOCK = ROOT / "WEEKEND_RUNNING"
LOGDIR = ROOT / "optimisation_outputs" / "weekend_2026-11-14"
REP = ["2", "15", "18", "23"]

STEPS = [
    ("1_present", "26 sites, everything on the table, green only", ["scripts/uk_sites.py", "--set", "present"]),
    ("2_breakeven_rig", "Break-even green price, every site and level, with and without engines (rig)",
     ["scripts/breakeven_sites.py", "--rig"]),
    ("3_breakeven_hourly", "Break-even green price, 4 sites, 25 MW and full grid (hourly)",
     ["scripts/breakeven_sites.py", "--sites", *REP, "--levels", "limited", "full"]),
    ("4_checks", "Fixed choices one at a time, 4 sites, 25 MW and full grid", ["scripts/fixed_choice_checks.py"]),
    ("5_blue", "26 sites, the blue what-if (green and blue)", ["scripts/uk_sites.py", "--set", "blue"]),
]


def log(msg: str):
    line = f"[{dt.datetime.now():%a %H:%M}] {msg}"
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
        log("sign-off finished; starting the queue")
        for key, title, cmd in STEPS:
            if a.only and key not in a.only:
                continue
            if dt.datetime.now() >= stop_at:
                log(f"{key}: not started, past {stop_at:%a %H:%M}")
                continue
            log(f"{key}: {title}")
            t0 = time.time()
            with open(LOGDIR / f"{key}.log", "a", encoding="utf-8") as out:
                rc = subprocess.run([PY, *cmd], cwd=ROOT, stdout=out, stderr=subprocess.STDOUT).returncode
            log(f"{key}: exit {rc} after {(time.time() - t0) / 3600:.1f} h")
        log("queue finished")
    finally:
        LOCK.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
