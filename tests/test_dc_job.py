"""The job protocol: what the page believes about a solve it cannot see.

Pure file and process-liveness logic — no LP, no Brightway, no network. The
solving itself is dc_runner's, and is tested by running it.
"""
import json
import os
import sys

import pytest

sys.path.insert(0, "/Users/louis/lca-ai-project/ukelectrolyserlca")
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
