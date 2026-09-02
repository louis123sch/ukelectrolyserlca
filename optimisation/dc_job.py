"""
Jobs — an optimiser run that outlives the browser tab that asked for it.
=============================================================================

``dc_runner.run_one`` solves a Pareto front in the process that calls it. From
a notebook that is exactly right. From Streamlit it is not: the script run
belongs to the browser session, so switching to another page, refreshing, or
closing the tab takes the solve with it — and because ``run_one`` only writes
``summary.json`` at the end, a run killed at LP 11 of 13 leaves nothing behind.
Twenty minutes of work disappears for a mis-click.

This module puts the solve in a **detached child process** instead, and gives
the page a file to look at rather than a variable to hold:

    page                          child (its own process group)
    ----                          -----------------------------
    write request.json   ---->    read request.json
    launch, then forget           run_one(..., progress=tick)
    poll status.json     <----    write status.json each LP
    read summary.json    <----    run_one writes it at the end

Nothing is held in session state, so *any* browser session — a refresh, a
second tab, a laptop reopened an hour later — can pick the run up again by
reading the same files. The child survives the page being closed, the session
ending, and Streamlit itself being restarted; only killing the process or the
machine stops it.

What is deliberately NOT here
-----------------------------
A queue. One page, one run at a time: ``active()`` reports the single job the
pointer file names, and the page refuses to launch a second while one is alive.
Parallelism across configurations already exists in ``dc_runner.run_matrix``,
which is the right tool for a sweep and a poor one for a single answer.

Liveness is checked, not assumed. A child that segfaults or is killed leaves a
``running`` status behind forever, so ``read`` cross-examines the status with
``os.kill(pid, 0)`` and reports ``lost`` rather than a progress bar that never
moves.

Run:  python -m optimisation.dc_job run <folder>      (what the page launches)
      python optimisation/dc_job.py                   (self-test, no solving)
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import traceback
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

RUNS = ROOT / "optimisation_outputs" / "dc_runs"

# Two kinds of job, and two pointers. A threshold sweep runs *after* a front and
# reports against it, so if they shared one pointer the sweep would erase the
# page's memory of the answer it is annotating. Separate pointers let both be
# alive, or finished, or lost, independently.
POINTER = RUNS / "_active_job.json"                     # kind "front"
THRESHOLD_POINTER = RUNS / "_active_threshold_job.json"  # kind "thresholds"
KINDS = ("front", "thresholds")


def pointer_for(kind: str) -> Path:
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {KINDS}, got {kind!r}")
    return POINTER if kind == "front" else THRESHOLD_POINTER

REQUEST = "request.json"
STATUS = "status.json"
LOG = "job.log"
SUMMARY = "summary.json"

# A child that has not written a status line for this long, but whose pid is
# still alive, is not dead — it is inside the one step that reports nothing:
# build_series, which can spend minutes fetching and scoring a year of grid
# data before the first LP. Only the pid decides life; this is for the wording.
QUIET_SECONDS = 600.0


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _write_json(path: Path, payload: dict):
    """Atomically, so a poll can never read half a status."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=2, default=str))
    tmp.replace(path)


def _read_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def _alive(pid: int | None) -> bool:
    if not pid:
        return False
    try:
        os.kill(int(pid), 0)
    except (OSError, ValueError):
        return False
    return True


# -----------------------------------------------------------------------------
# The page's side
# -----------------------------------------------------------------------------
def folder_for(out_root, scenario_key: str, kind: str = "front") -> Path:
    """Where a job of this kind keeps its request, status, log and result.

    A threshold sweep lives under ``_thresholds/`` beside the scenario folders
    rather than inside one, so its own knob files sit with it and neither job
    can overwrite the other's ``status.json``. The underscore keeps it out of
    ``dc_runner.load_results``, which globs ``*/summary.json``.
    """
    root = Path(out_root)
    return (root / scenario_key if kind == "front"
            else root / "_thresholds" / scenario_key)


def start(*, scenario, site, out_root, label: str, total: int,
          kind: str = "front", **kw) -> dict:
    """Launch a detached solve and return its first status.

    ``kw`` is passed straight to ``dc_runner.run_one`` (kind "front") or to
    ``thresholds.sweep`` (kind "thresholds"), so this stays a thin wrapper
    rather than a second copy of either signature. Everything in it must be
    JSON-safe — the ``Site`` is rebuilt by the child from coordinates.
    """
    folder = folder_for(out_root, scenario.key, kind)
    folder.mkdir(parents=True, exist_ok=True)
    _write_json(folder / REQUEST, {
        "scenario": asdict(scenario),
        # Enough to rebuild the Site without touching postcodes.io again: with
        # carbon_api_region given, sites.resolve does no network at all.
        "site": {"lat": site.lat, "lon": site.lon,
                 "carbon_api_region": site.carbon_api_region,
                 "name": site.name, "tdr_band": site.tdr_band,
                 "connection_limit_mw": site.connection_limit_mw,
                 "transmission_connected": site.transmission_connected},
        "out_root": str(out_root),
        "kind": kind,
        "kw": kw,
    })
    status = {"state": "starting", "label": label, "site_name": site.name,
              "folder": str(folder), "kind": kind, "done": 0, "total": int(total),
              "tag": "starting up", "started": _now(), "heartbeat": _now(),
              "pid": None}
    _write_json(folder / STATUS, status)

    log = open(folder / LOG, "w")
    proc = subprocess.Popen(
        [sys.executable, "-m", "optimisation.dc_job", "run", str(folder)],
        cwd=str(ROOT), stdout=log, stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        # Its own process group, so it is not killed with the shell, the
        # Streamlit server, or whatever else Ctrl-C reaches.
        start_new_session=True)
    status["pid"] = proc.pid
    status["state"] = "running"
    _write_json(folder / STATUS, status)
    _write_json(pointer_for(kind),
                {"folder": str(folder), "kind": kind, "started": status["started"]})
    return status


def read(folder) -> dict | None:
    """The status of the job in ``folder``, with its liveness checked."""
    folder = Path(folder)
    s = _read_json(folder / STATUS)
    if s is None:
        return None
    s["folder"] = str(folder)
    s["log"] = str(folder / LOG)
    if s.get("state") in ("done", "failed"):
        return s
    if not _alive(s.get("pid")):
        # Finished-but-unrecorded is a real case: the child can be killed
        # between writing summary.json and its final status line.
        if (folder / SUMMARY).exists():
            summ = _read_json(folder / SUMMARY) or {}
            if summ.get("config_hash") and s.get("config_hash") in (None, summ["config_hash"]):
                s.update(state="done", tag="finished", config_hash=summ["config_hash"])
                return s
        s["state"] = "lost"
        s["tag"] = "the solver process is gone"
        return s
    age = time.time() - _mtime(folder / STATUS)
    s["quiet_seconds"] = age
    s["quiet"] = age > QUIET_SECONDS
    return s


def _mtime(p: Path) -> float:
    try:
        return p.stat().st_mtime
    except OSError:
        return time.time()


def active(kind: str = "front") -> dict | None:
    """The job of this kind the pointer names, whatever session started it."""
    ptr = _read_json(pointer_for(kind))
    if not ptr:
        return None
    s = read(ptr["folder"])
    if s is not None:
        s.setdefault("kind", kind)
    return s


def clear_pointer(kind: str = "front"):
    pointer_for(kind).unlink(missing_ok=True)


def cancel(folder) -> bool:
    """Stop a running job. Returns whether a process was actually signalled."""
    s = read(folder)
    if not s or not _alive(s.get("pid")):
        return False
    try:
        os.killpg(os.getpgid(int(s["pid"])), 9)
    except OSError:
        try:
            os.kill(int(s["pid"]), 9)
        except OSError:
            return False
    s.update(state="failed", tag="cancelled", error="Cancelled from the page.",
             heartbeat=_now())
    _write_json(Path(folder) / STATUS, s)
    return True


def summary(folder) -> dict | None:
    return _read_json(Path(folder) / SUMMARY)


# -----------------------------------------------------------------------------
# The child's side
# -----------------------------------------------------------------------------
def _run(folder: Path):
    import lca_helpers as H
    from optimisation import dc_architectures as A
    from optimisation import sites

    req = _read_json(folder / REQUEST) or {}
    status = _read_json(folder / STATUS) or {}

    def tick(tag: str, **extra):
        status["done"] = status.get("done", 0) + 1
        status["tag"] = tag
        status["heartbeat"] = _now()
        status.update(extra)
        _write_json(folder / STATUS, status)

    def stage(tag: str):
        status["tag"] = tag
        status["heartbeat"] = _now()
        _write_json(folder / STATUS, status)

    try:
        stage("connecting to Brightway")
        H.setup_brightway()
        scenario = A.Scenario(**req["scenario"])
        site = sites.resolve(**req["site"])
        stage("building the half-hourly series")
        if req.get("kind", "front") == "thresholds":
            result = _run_thresholds(folder, scenario, site, req, tick, stage)
        else:
            from optimisation import dc_runner
            result = dc_runner.run_one(scenario, site=site,
                                       out_root=Path(req["out_root"]),
                                       progress=tick, notice=stage, **req["kw"])
    except BaseException as exc:              # SystemExit and KeyboardInterrupt too
        status.update(state="failed", tag="failed", heartbeat=_now(),
                      error=f"{type(exc).__name__}: {exc}",
                      traceback=traceback.format_exc())
        _write_json(folder / STATUS, status)
        raise
    status.update(state="done", tag="finished", heartbeat=_now(),
                  config_hash=result.get("config_hash"),
                  cached=bool(result.get("cached")),
                  solve_seconds=result.get("solve_seconds"))
    _write_json(folder / STATUS, status)


def _run_thresholds(folder: Path, scenario, site, req, tick, stage) -> dict:
    """One threshold sweep, written where the page will look for it.

    ``run_one`` writes its own ``summary.json``; ``thresholds.sweep`` writes one
    file per knob instead, so this assembles the summary the job protocol needs.
    Its ``config_hash`` is the hash of the searches it contains, which is what
    lets ``read`` recognise a child that died between the last knob and its
    final status line.
    """
    import hashlib
    from optimisation import thresholds as T

    kw = dict(req["kw"])
    knobs = tuple(kw.pop("knobs"))
    results = T.sweep(scenario, knobs, site=site,
                      out_root=Path(req["out_root"]) / "_thresholds",
                      progress=tick, notice=stage, **kw)
    summary = {
        "kind": "thresholds",
        "scenario": scenario.key, "label": scenario.label,
        "site": site.key, "site_name": site.name,
        "knobs": list(knobs),
        "results": results,
        "table": T.records(results),
        "solve_seconds": sum(r.get("solve_seconds", 0.0) for r in results),
        "cached": all(r.get("cached") for r in results),
        "config_hash": hashlib.sha256(
            "|".join(r.get("config_hash", "") for r in results).encode()
        ).hexdigest()[:16],
    }
    _write_json(folder / SUMMARY, summary)
    return summary


def run():
    """Self-test. Exercises the plumbing — the file protocol, not the LP."""
    for kind in KINDS:
        print(f"{kind:11} pointer: {pointer_for(kind)}")
        a = active(kind)
        if a is None:
            print(f"{'':11} no job started, or its folder is gone.")
        else:
            print(f"{'':11} {a['state']} — {a.get('label')} at {a.get('site_name')}, "
                  f"{a.get('done')}/{a.get('total')} ({a.get('tag')})")
    print("\nStatuses on disk:")
    for st_path in sorted(RUNS.glob(f"**/{STATUS}")):
        s = read(st_path.parent) or {}
        print(f"  {s.get('state','?'):8} {s.get('done')}/{s.get('total')}  "
              f"{st_path.parent.relative_to(RUNS)}")


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "run":
        _run(Path(sys.argv[2]))
    else:
        run()
