"""The grid-build lock, and the file reads the build finishes on.

``ensure_grid_series`` builds a window nobody has built yet rather than refusing
it — that is the whole point of the autobuild path. Two things stopped it ever
running on Windows, both of them silent about the real cause:

  * ``_build_lock`` imported ``fcntl``, which does not exist there, so the run
    died with ModuleNotFoundError the moment it decided to build; and
  * the build reads its executed notebook back at the end, and doing that
    through the locale codec raises on the notebook's own box-drawing output —
    after nbconvert has already succeeded, throwing the whole build away.

No notebook is executed here. This is the plumbing around it.
"""
import pathlib
import subprocess
import sys
import time

import pytest

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from backend import runner
from optimisation import sites


# -----------------------------------------------------------------------------
# The lock
# -----------------------------------------------------------------------------
def test_the_lock_can_be_taken_and_released():
    with sites._build_lock():
        pass
    with sites._build_lock():           # released, so it can be taken again
        pass


def test_the_lock_is_exclusive_across_processes():
    """The reason it exists: run_lca patches the single tracked
    dashboard_config.py, so two builds at once each run the other's config."""
    holder = subprocess.Popen(
        [sys.executable, "-c",
         f"import sys, time; sys.path.insert(0, {str(REPO)!r});"
         "from optimisation import sites;"
         "ctx = sites._build_lock(); ctx.__enter__();"
         "print('held', flush=True); time.sleep(20)"],
        stdout=subprocess.PIPE, text=True)
    try:
        assert holder.stdout.readline().strip() == "held"
        waited = []
        with pytest.raises(TimeoutError):
            with sites._build_lock(wait_s=1.0, on_progress=waited.append):
                pytest.fail("a second holder took a lock the first still owns")
        assert waited == ["waiting for another grid build to finish"]
    finally:
        holder.kill()
        holder.wait()


def test_the_lock_comes_back_when_its_holder_dies():
    """flock and msvcrt.locking are held by the handle, so the OS releases them
    on exit. An O_EXCL lock file would strand every later run for six hours."""
    holder = subprocess.Popen(
        [sys.executable, "-c",
         f"import sys; sys.path.insert(0, {str(REPO)!r});"
         "from optimisation import sites;"
         "ctx = sites._build_lock(); ctx.__enter__(); print('held', flush=True)"],
        stdout=subprocess.PIPE, text=True)
    assert holder.stdout.readline().strip() == "held"
    holder.wait(timeout=30)             # exits still "holding" it
    deadline = time.time() + 15
    while True:
        try:
            with sites._build_lock(wait_s=0.0):
                return
        except TimeoutError:
            if time.time() > deadline:
                raise
            time.sleep(0.5)


# -----------------------------------------------------------------------------
# What the build reads back once nbconvert has succeeded
# -----------------------------------------------------------------------------
def test_the_executed_notebook_is_read_as_utf8_not_the_locale_codec():
    """The notebook the build runs carries 1400 bytes cp1252 cannot decode at
    all, so read_text() with no encoding raised *after* a successful run."""
    nb = REPO / runner.RUNNER_NOTEBOOK
    assert nb.exists(), f"{runner.RUNNER_NOTEBOOK} is the notebook run_lca executes"
    undecodable = {0x81, 0x8D, 0x8F, 0x90, 0x9D}
    assert undecodable & set(nb.read_bytes()), (
        "this notebook no longer contains bytes cp1252 rejects, so it no longer "
        "guards the regression — point the test at one that does")
    assert runner._extract_notebook_log(nb)          # the call that used to raise


def test_the_patched_config_survives_a_round_trip(tmp_path, monkeypatch):
    """run_lca rewrites the tracked dashboard_config.py in place. Reading it
    through cp1252 and writing it back happens to be byte-safe today only
    because it contains none of the five bytes cp1252 cannot decode."""
    cfg = tmp_path / "dashboard_config.py"
    original = 'CARBON_API_REGION_ID_OVERRIDE = None\nNOTE = "— ═ ₂ £"\n'
    cfg.write_text(original, encoding="utf-8")
    monkeypatch.setattr(runner, "CONFIG_PATH", cfg)
    monkeypatch.setattr(runner, "RUNS_DIR", tmp_path / "runs")
    text = runner.CONFIG_PATH.read_text(encoding="utf-8")
    runner.CONFIG_PATH.write_text(text, encoding="utf-8")
    assert cfg.read_text(encoding="utf-8") == original
