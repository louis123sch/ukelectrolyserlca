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
