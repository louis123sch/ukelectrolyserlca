"""Execute a project notebook headless, in this interpreter's environment.

Only one notebook still needs this: ``2.tech_lca_foreground.ipynb``, which
builds the foreground databases from ecoinvent and has no API behind it, so it
runs once per machine (``optimisation.sites.build_grid_series`` starts it when
the data centre foreground is missing). Grid and price series are built in
Python by ``optimisation/grid_build.py`` and do not come through here.

Nothing is patched: the notebook reads ``dc_config.py`` as it stands.
"""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent
RUNS_DIR = REPO_DIR / "_streamlit_runs"
FOREGROUND_NOTEBOOK = "2.tech_lca_foreground.ipynb"

# A console window for the notebook child, and what it costs to let one open.
#
# The Streamlit page runs a solve through optimisation/dc_job.py, which spawns
# it DETACHED_PROCESS — deliberately, so nothing aimed at the server's console
# can reach it. A detached process has no console of its own, so when it starts
# a console-subsystem child like nbconvert, Windows allocates that child a
# *brand new console window*: a blank black one titled with this environment's
# python.exe path, sitting on the desktop for the length of the build.
#
# It is not merely untidy. Everything attached to that console receives
# CTRL_CLOSE_EVENT when its window is closed, so closing what looks like a
# stray terminal kills nbconvert instantly — non-zero exit, no traceback, and
# no "[NbConvertApp] ERROR", because the notebook never failed. That is exactly
# how a region 14 build died mid-fetch after 65 seconds and took the whole
# optimiser run above it down with an error that named nothing.
#
# Nothing needs the console: stdout and stderr are already pipes.
_NO_WINDOW = ({"creationflags": subprocess.CREATE_NO_WINDOW}
              if sys.platform == "win32" else {})


@dataclass
class RunResult:
    success: bool
    log_text: str = ""
    error_text: str = ""
    executed_notebook: Path | None = None
    returncode: int | None = None
    # True when nbconvert exited non-zero without reporting a reason of its
    # own — the process died rather than the notebook failing. A cell that
    # raises always leaves "[NbConvertApp] ERROR" and a traceback behind, so
    # its absence is the distinguishing evidence. Callers use it to decide
    # whether retrying could possibly help: a notebook that raised will raise
    # again, a process that was killed may well not.
    crashed: bool = False


def _extract_notebook_log(nb_path: Path, max_chars: int = 20000) -> str:
    import json

    nb = json.loads(nb_path.read_text(encoding="utf-8"))
    chunks = []
    for cell in nb.get("cells", []):
        if cell.get("cell_type") != "code":
            continue
        for out in cell.get("outputs", []):
            if out.get("output_type") == "stream":
                chunks.append("".join(out.get("text", [])))
            elif out.get("output_type") == "error":
                chunks.append(
                    f"ERROR: {out.get('ename')}: {out.get('evalue')}\n"
                    + "\n".join(out.get("traceback", []))
                )
    text = "\n".join(chunks)
    if len(text) > max_chars:
        text = text[-max_chars:]
    return text


def run_notebook(notebook: str = FOREGROUND_NOTEBOOK, timeout_s: int = 5400) -> RunResult:
    """Execute ``notebook`` (relative to the repo) with nbconvert and report how it went.

    The executed copy is written to ``_streamlit_runs/<name>.executed.ipynb``
    (gitignored), so the repo's own notebook is never rewritten by a run.
    """
    RUNS_DIR.mkdir(exist_ok=True)
    executed_path = RUNS_DIR / f"{Path(notebook).stem}.executed.ipynb"
    # ``-m nbconvert`` rather than the console script beside the interpreter.
    # That sibling only exists on POSIX, where bin/ holds python and
    # jupyter-nbconvert together; Windows keeps python.exe at the env root and
    # the scripts in Scripts\, so the old lookup always missed and fell back to
    # a bare PATH search — which found base conda's nbconvert, not this env's.
    cmd = [
        sys.executable, "-m", "nbconvert",
        "--to", "notebook",
        "--execute",
        f"--ExecutePreprocessor.timeout={timeout_s}",
        "--ExecutePreprocessor.kernel_name=python3",
        "--output", str(executed_path),
        str(REPO_DIR / notebook),
    ]

    env = dict(os.environ)
    # Running the right nbconvert is only half of it: the python3 kernelspec's
    # argv starts with a bare "python", resolved from PATH when the kernel is
    # launched. Put this interpreter's own directory first so the notebook runs
    # in the environment that asked for it — otherwise it lands in whatever
    # python PATH happens to name, and reports the whole science stack missing.
    _here = Path(sys.executable).parent
    env["PATH"] = os.pathsep.join(
        [str(_here)]
        + ([str(_here / "Scripts")] if (_here / "Scripts").is_dir() else [])
        + [env.get("PATH", "")])
    # A headless run has no use for interactive figures.
    env["MPLBACKEND"] = "Agg"
    # Decoding this pipe as UTF-8 below is only half the bargain: nbconvert
    # writes to it through *its* locale codec, and stdout is a pipe rather than
    # a terminal, so on Windows that is cp1252. Relaying a notebook line
    # containing a "═" separator then kills nbconvert itself with
    # UnicodeEncodeError. Both ends have to agree.
    env["PYTHONIOENCODING"] = "utf-8"

    try:
        proc = subprocess.run(
            cmd,
            cwd=REPO_DIR,
            capture_output=True,
            text=True,
            # text=True alone decodes through the locale codec — cp1252 on
            # Windows — and nbconvert relays the notebook's own output, which
            # carries characters cp1252 cannot represent. Losing a whole run's
            # log to a decode error is worse than a replacement character.
            encoding="utf-8",
            errors="replace",
            timeout=timeout_s + 60,
            env=env,
            **_NO_WINDOW,
        )
    except subprocess.TimeoutExpired as exc:
        return RunResult(
            success=False,
            error_text=f"Run timed out after {timeout_s}s.\n{exc.stdout or ''}\n{exc.stderr or ''}",
        )

    if proc.returncode != 0 or not executed_path.exists():
        # Both streams, always, and the exit code with them. Reporting only
        # stderr's tail is how a failed region-14 build arrived as nothing but
        # nbconvert's banner and an unrelated zmq warning: the notebook's own
        # traceback, when there is one, and the exit code that says whether
        # there could have been one, were both thrown away before anyone saw
        # them.
        crashed = "[NbConvertApp] ERROR" not in (proc.stderr or "")
        parts = [f"nbconvert exited {proc.returncode}"
                 + ("" if executed_path.exists() else
                    f", and wrote no {executed_path.name}")
                 + ("." if not crashed else
                    " without reporting an error of its own, which means the "
                    "process died rather than the notebook failing.")]
        for name, text in (("stderr", proc.stderr), ("stdout", proc.stdout)):
            if (text or "").strip():
                parts.append(f"--- {name} ---\n{text[-6000:]}")
        return RunResult(
            success=False,
            error_text="\n".join(parts),
            returncode=proc.returncode,
            crashed=crashed,
        )

    return RunResult(
        success=True,
        log_text=_extract_notebook_log(executed_path),
        executed_notebook=executed_path,
    )
