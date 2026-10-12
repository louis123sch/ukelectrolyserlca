"""The grid-build lock, and the file reads the build finishes on.

``ensure_grid_series`` builds a window nobody has built yet rather than refusing
it — that is the whole point of the autobuild path. Two things stopped it ever
running on Windows, both of them silent about the real cause:

  * ``_build_lock`` imported ``fcntl``, which does not exist there, so the run
    died with ModuleNotFoundError the moment it decided to build; and
  * reading an executed notebook back through the locale codec raises on
    box-drawing output — after nbconvert has already succeeded. Only notebook 2
    (the one-off foreground build) still goes through nbconvert, but it prints
    the same separators.

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
    """The reason it exists: dc_runner.run_matrix's workers can find the same
    window missing at once, and each would fetch it and overwrite the other."""
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
def test_the_foreground_notebook_exists():
    assert (REPO / runner.FOREGROUND_NOTEBOOK).exists(), (
        f"{runner.FOREGROUND_NOTEBOOK} is the notebook a first build runs")


def test_the_executed_notebook_is_read_as_utf8_not_the_locale_codec(tmp_path):
    """An executed notebook carries box-drawing output,
    which includes bytes cp1252 cannot decode at all, so read_text() with no
    encoding raised *after* a successful run. A fixture rather than the real
    notebook, so the guard does not depend on what that notebook prints."""
    import json
    nb = tmp_path / "executed.ipynb"
    nb.write_text(json.dumps({"cells": [{"cell_type": "code", "outputs": [
        {"output_type": "stream", "name": "stdout", "text": ["═" * 70 + "\n"]}]}]},
        ensure_ascii=False), encoding="utf-8")
    undecodable = {0x81, 0x8D, 0x8F, 0x90, 0x9D}
    assert undecodable & set(nb.read_bytes())
    assert "═" in runner._extract_notebook_log(nb)   # the call that used to raise
