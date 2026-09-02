"""The job protocol: what the page believes about a solve it cannot see.

Pure file and process-liveness logic — no LP, no Brightway, no network. The
solving itself is dc_runner's, and is tested by running it.
"""
import json
import os
import pathlib
import sys
import time

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from optimisation import dc_job


def _status(folder, **kw):
    s = {"state": "running", "label": "test", "site_name": "nowhere",
         "done": 1, "total": 4, "started": dc_job._now(), "pid": os.getpid()}
    s.update(kw)
    dc_job._write_json(folder / dc_job.STATUS, s)
    return s


def test_live_job_reads_back_as_running(tmp_path):
    _status(tmp_path)                       # this test's own pid: certainly alive
    s = dc_job.read(tmp_path)
    assert s["state"] == "running" and s["done"] == 1
    assert not s["quiet"]


def test_dead_process_with_no_result_is_lost(tmp_path):
    _status(tmp_path, pid=999_999)          # a pid that cannot be running
    assert dc_job.read(tmp_path)["state"] == "lost"


def test_dead_process_that_wrote_a_summary_is_done(tmp_path):
    """The child can be killed between writing its result and its last status."""
    _status(tmp_path, pid=999_999)
    (tmp_path / dc_job.SUMMARY).write_text(json.dumps({"config_hash": "abc123"}))
    s = dc_job.read(tmp_path)
    assert s["state"] == "done" and s["config_hash"] == "abc123"


def test_quiet_but_alive_is_flagged_not_killed(tmp_path, monkeypatch):
    monkeypatch.setattr(dc_job, "QUIET_SECONDS", -1.0)
    _status(tmp_path)
    s = dc_job.read(tmp_path)
    assert s["state"] == "running" and s["quiet"]


def test_pointer_finds_the_job_from_any_session(tmp_path, monkeypatch):
    monkeypatch.setattr(dc_job, "POINTER", tmp_path / "_active_job.json")
    assert dc_job.active() is None          # nothing started
    folder = tmp_path / "job"
    folder.mkdir()
    _status(folder, label="grid + wind")
    dc_job._write_json(dc_job.POINTER, {"folder": str(folder),
                                        "started": dc_job._now()})
    a = dc_job.active()
    assert a["label"] == "grid + wind" and a["state"] == "running"
    dc_job.clear_pointer()
    assert dc_job.active() is None


def test_missing_status_is_no_job(tmp_path):
    assert dc_job.read(tmp_path) is None


def test_half_written_status_never_reaches_the_page(tmp_path):
    """_write_json goes through a temp file, so a poll sees old or new, not half."""
    _status(tmp_path)
    assert not list(tmp_path.glob("*.tmp"))
    assert json.loads((tmp_path / dc_job.STATUS).read_text())["label"] == "test"


# -----------------------------------------------------------------------------
# Two kinds of job, two pointers
# -----------------------------------------------------------------------------
def test_each_kind_has_its_own_pointer():
    assert dc_job.pointer_for("front") != dc_job.pointer_for("thresholds")


def test_an_unknown_kind_is_refused_rather_than_silently_shared():
    with pytest.raises(ValueError):
        dc_job.pointer_for("everything")


def test_a_threshold_sweep_lives_beside_the_scenarios_not_inside_one(tmp_path):
    """Inside would clobber the front's status.json; the underscore keeps it
    out of dc_runner.load_results, which globs */summary.json."""
    front = dc_job.folder_for(tmp_path, "00_custom_getf", "front")
    thr = dc_job.folder_for(tmp_path, "00_custom_getf", "thresholds")
    assert front == tmp_path / "00_custom_getf"
    assert thr == tmp_path / "_thresholds" / "00_custom_getf"
    assert thr not in tmp_path.glob("*/summary.json")


def test_folder_for_defaults_to_the_front(tmp_path):
    assert dc_job.folder_for(tmp_path, "k") == dc_job.folder_for(tmp_path, "k", "front")


def test_a_sweep_does_not_erase_the_answer_it_annotates(tmp_path, monkeypatch):
    """The page reads the front's result out of its pointer. If a threshold
    sweep took that pointer, launching one would blank section 5."""
    monkeypatch.setattr(dc_job, "POINTER", tmp_path / "front.json")
    monkeypatch.setattr(dc_job, "THRESHOLD_POINTER", tmp_path / "thr.json")
    fdir, tdir = tmp_path / "f", tmp_path / "t"
    _status(fdir, label="the front")
    _status(tdir, label="the sweep")
    dc_job._write_json(dc_job.POINTER, {"folder": str(fdir), "kind": "front"})
    dc_job._write_json(dc_job.THRESHOLD_POINTER, {"folder": str(tdir),
                                                  "kind": "thresholds"})
    assert dc_job.active("front")["label"] == "the front"
    assert dc_job.active("thresholds")["label"] == "the sweep"


def test_dismissing_one_kind_leaves_the_other_alone(tmp_path, monkeypatch):
    monkeypatch.setattr(dc_job, "POINTER", tmp_path / "front.json")
    monkeypatch.setattr(dc_job, "THRESHOLD_POINTER", tmp_path / "thr.json")
    fdir = tmp_path / "f"
    _status(fdir)
    dc_job._write_json(dc_job.POINTER, {"folder": str(fdir), "kind": "front"})
    dc_job._write_json(dc_job.THRESHOLD_POINTER, {"folder": str(fdir),
                                                  "kind": "thresholds"})
    dc_job.clear_pointer("thresholds")
    assert dc_job.active("thresholds") is None
    assert dc_job.active("front") is not None


# -----------------------------------------------------------------------------
# Liveness on Windows, which is where the POSIX idiom is worse than useless
# -----------------------------------------------------------------------------
def test_a_process_that_has_exited_reads_as_dead():
    """``os.kill(pid, 0)`` returns cleanly for an exited pid on Windows, so a
    finished-or-crashed solve read as "running" forever and the Optimise button
    never came back. Spawn a real child and let it exit rather than trust a
    made-up pid, which the OS can reject for the wrong reason."""
    import subprocess as sp
    child = sp.Popen([sys.executable, "-c", "pass"])
    child.wait()
    assert dc_job._alive(child.pid) is False
    assert dc_job._alive(os.getpid()) is True


def test_checking_liveness_sends_no_signal_to_the_child():
    """The bug this replaced: signal 0 *is* CTRL_C_EVENT on Windows, so polling
    a job's status sent a real Ctrl-C to the console and took the Streamlit
    server — and the child it had just launched — down with it."""
    import subprocess as sp
    child = sp.Popen([sys.executable, "-c", "import time; time.sleep(30)"],
                     stdin=sp.DEVNULL, **dc_job._SPAWN_KW)
    try:
        for _ in range(5):
            assert dc_job._alive(child.pid) is True
        assert child.poll() is None          # still running, not interrupted
    finally:
        # The Stop button's path. os.killpg/os.getpgid do not exist on Windows,
        # and AttributeError is not OSError, so the old handler did not catch it.
        assert dc_job._terminate(child.pid) is True
    child.wait(timeout=10)
    assert dc_job._alive(child.pid) is False


def test_the_child_is_launched_detached_from_this_console():
    """``start_new_session`` is silently ignored on Windows, which left the
    solver in the server's own process group."""
    if sys.platform == "win32":
        import subprocess as sp
        flags = dc_job._SPAWN_KW["creationflags"]
        assert flags & sp.CREATE_NEW_PROCESS_GROUP
        assert flags & sp.DETACHED_PROCESS
        assert "start_new_session" not in dc_job._SPAWN_KW
    else:
        assert dc_job._SPAWN_KW == {"start_new_session": True}


def test_a_status_write_survives_the_page_reading_it(tmp_path, monkeypatch):
    """os.replace is refused on Windows while any other handle is open on the
    destination. The child writes a status line after every LP and the page
    opens that file on every rerun, so an unretried replace killed the solve."""
    monkeypatch.setattr(dc_job, "_REPLACE_PAUSE", 0.0)
    target = tmp_path / dc_job.STATUS
    dc_job._write_json(target, {"state": "running", "done": 0})
    with open(target, "r", encoding="utf-8") as reader_holding_it_open:
        reader_holding_it_open.read(1)
        # One try is all a single blocked attempt gets; the retry is the fix.
        monkeypatch.setattr(dc_job, "_REPLACE_TRIES", 1)
        if sys.platform == "win32":
            with pytest.raises(PermissionError):
                dc_job._write_json(target, {"state": "running", "done": 1})
    monkeypatch.setattr(dc_job, "_REPLACE_TRIES", 12)
    dc_job._write_json(target, {"state": "running", "done": 2})
    assert json.loads(target.read_text(encoding="utf-8"))["done"] == 2


def test_a_lost_run_does_not_claim_the_previous_runs_answer(tmp_path):
    """summary.json is also the scenario's cache, so an earlier run of the same
    scenario leaves one in this very folder. A run that dies before recording
    its own config_hash used to adopt it and show the old answer as the new."""
    stale = {"config_hash": "from_the_run_before"}
    summary = tmp_path / dc_job.SUMMARY
    summary.write_text(json.dumps(stale), encoding="utf-8")
    an_hour_ago = time.time() - 3600
    os.utime(summary, (an_hour_ago, an_hour_ago))          # a real cached answer
    _status(tmp_path, pid=999_999, started=dc_job._now())  # this run began just now
    s = dc_job.read(tmp_path)
    assert s["state"] == "lost", "a summary older than the run is not its result"
    assert s.get("config_hash") != "from_the_run_before"


def test_a_summary_written_by_this_run_is_still_recognised(tmp_path):
    """The case the branch exists for: killed between writing the result and
    the final status line."""
    _status(tmp_path, pid=999_999, started=dc_job._now())
    (tmp_path / dc_job.SUMMARY).write_text(json.dumps({"config_hash": "mine"}),
                                           encoding="utf-8")
    s = dc_job.read(tmp_path)
    assert s["state"] == "done" and s["config_hash"] == "mine"


def test_stop_refuses_a_pid_older_than_the_job(tmp_path, monkeypatch):
    """Windows reuses pids briskly and _terminate kills a whole tree, so the
    pid in the status file is not on its own enough evidence to kill anything."""
    killed = []
    monkeypatch.setattr(dc_job, "_terminate", lambda pid: killed.append(pid) or True)
    # This interpreter is certainly older than a job "started" a moment ago.
    _status(tmp_path, pid=os.getpid(), started=dc_job._now())
    if dc_job._started_at(os.getpid()) is None:
        pytest.skip("no process creation time on this platform")
    assert dc_job.cancel(tmp_path) is False
    assert killed == [], "cancel killed a process that predates the job"
