"""Notebook runner behind the optimiser's grid builds.

dashboard_config.py is the project's single source of truth for every
notebook — its own docstring says as much ("Edit this file once, save it,
restart the notebook kernel, then run"). ``optimisation.sites.build_grid_series``
follows that same contract instead of inventing a second one: it patches the
on-disk dashboard_config.py with the region and window it needs, then runs
1.build_grid.ipynb, which chains the foreground, grid and price notebooks.

This keeps 100% of the actual LCA science (Carbon Intensity API client, wind
dispatch logic, Brightway calls) in the tested notebooks/lca_helpers.py — this
module only edits config text, runs a subprocess, and collects results.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO_DIR / "dashboard_config.py"
RUNS_DIR = REPO_DIR / "_streamlit_runs"
PLOTS_DIR = RUNS_DIR / "plots"
RUNNER_NOTEBOOK = "1.build_grid.ipynb"

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

OUTPUT_DIRS = [
    "custom_grid_lca_outputs",
    "price_outputs",
]


def _literal(value) -> str:
    """Render a Python value as source text for a dashboard_config.py assignment."""
    return repr(value)


def apply_config_overrides(base_text: str, overrides: dict) -> str:
    """Return dashboard_config.py source text with the given top-level assignments replaced.

    Only touches the single `KEY = ...` line for each override key (matched at
    the start of a line so e.g. GRID_SINGLE_DATETIME never matches
    PRICE_SINGLE_DATETIME); everything else, including all derived-value and
    validation logic further down the file, is left untouched and recomputes
    naturally from the new values when the module is imported.
    """
    text = base_text
    for key, value in overrides.items():
        pattern = re.compile(rf"(?m)^{re.escape(key)}\s*=.*$")
        new_line = f"{key} = {_literal(value)}"
        text, count = pattern.subn(new_line, text, count=1)
        if count == 0:
            raise ValueError(
                f"Could not find a top-level '{key} = ...' assignment in dashboard_config.py "
                "to override. Check the key name."
            )
    return text


def _snapshot(dirs: list[Path]) -> dict[Path, float]:
    seen = {}
    for d in dirs:
        if not d.exists():
            continue
        for p in d.glob("*"):
            if p.is_file():
                seen[p] = p.stat().st_mtime
    return seen


def _new_or_changed(before: dict[Path, float], dirs: list[Path]) -> list[Path]:
    after = _snapshot(dirs)
    changed = [p for p, mtime in after.items() if before.get(p) != mtime]
    changed.sort(key=lambda p: after[p], reverse=True)
    return changed


@dataclass
class RunResult:
    success: bool
    log_text: str = ""
    error_text: str = ""
    new_files: list[Path] = field(default_factory=list)
    executed_notebook: Path | None = None
    config_backup: Path | None = None
    plots: list[tuple[str, Path]] = field(default_factory=list)
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


def _caption_from_stream_text(text: str) -> str:
    """Pick the title line out of accumulated stream text, skipping warnings/tracebacks.

    Notebook 2 prints a title before each plt.show(); matplotlib/pandas also
    write deprecation warnings (file-path-prefixed) to the same stream, so the
    literal last line before an image is often a warning, not the title.
    """
    candidates = [
        line.strip() for line in text.splitlines()
        if line.strip()
        and not line.startswith((" ", "\t"))  # warning tracebacks print the offending code indented
        and "Warning" not in line
        and ".py:" not in line
        and not set(line.strip()) <= {"=", "-"}
    ]
    return candidates[0] if candidates else ""


def _extract_notebook_images(nb_path: Path) -> list[tuple[str, bytes]]:
    """Pull every PNG figure notebook 2's plotting cells produced, with a caption."""
    import base64
    import json

    nb = json.loads(nb_path.read_text(encoding="utf-8"))
    images: list[tuple[str, bytes]] = []
    for cell in nb.get("cells", []):
        if cell.get("cell_type") != "code":
            continue
        pending_text = ""
        for out in cell.get("outputs", []):
            if out.get("output_type") == "stream":
                pending_text += "".join(out.get("text", []))
            elif out.get("output_type") == "display_data" and "image/png" in out.get("data", {}):
                caption = _caption_from_stream_text(pending_text) or f"Figure {len(images) + 1}"
                images.append((caption, base64.b64decode(out["data"]["image/png"])))
                pending_text = ""
    return images


def _save_plots(nb_path: Path, plots_dir: Path) -> list[tuple[str, Path]]:
    """Save every figure from the executed notebook to plots_dir, replacing any previous run's."""
    import json
    import shutil

    if plots_dir.exists():
        shutil.rmtree(plots_dir)
    plots_dir.mkdir(parents=True)

    saved = []
    captions = {}
    for i, (caption, png_bytes) in enumerate(_extract_notebook_images(nb_path)):
        filename = f"{i:02d}.png"
        (plots_dir / filename).write_bytes(png_bytes)
        captions[filename] = caption
        saved.append((caption, plots_dir / filename))
    (plots_dir / "captions.json").write_text(json.dumps(captions, indent=2),
                                             encoding="utf-8")
    return saved


def run_lca(overrides: dict, secrets: dict | None = None, timeout_s: int = 1800) -> RunResult:
    """Apply ``overrides`` to dashboard_config.py and execute the adaptive dashboard notebook.

    ``overrides`` maps dashboard_config.py variable names to their new values,
    e.g. {"GRID_TIME_MODE": "single", "TECH_SELECTED": ["PEM operation"]}.

    ``secrets`` (e.g. {"RENEWABLES_NINJA_TOKEN": token}) are passed as
    subprocess environment variables instead — dashboard_config.py is a
    tracked file, so a token must never be written into it on disk.
    """
    RUNS_DIR.mkdir(exist_ok=True)

    base_text = CONFIG_PATH.read_text(encoding="utf-8")
    backup_path = RUNS_DIR / "dashboard_config.before_last_run.py"
    backup_path.write_text(base_text, encoding="utf-8")

    new_text = apply_config_overrides(base_text, overrides)
    CONFIG_PATH.write_text(new_text, encoding="utf-8")

    output_dirs = [REPO_DIR / d for d in OUTPUT_DIRS]
    before = _snapshot(output_dirs)

    executed_path = RUNS_DIR / "last_run_executed.ipynb"
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
        str(REPO_DIR / RUNNER_NOTEBOOK),
    ]

    env = {**os.environ, **(secrets or {})}
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
    # Force the inline backend so figures are always captured as PNG outputs
    # regardless of what MPLBACKEND (if any) this process inherited — e.g.
    # a plain "Agg" backend renders plt.show() a no-op and silently produces
    # zero images, which is otherwise very easy to hit by accident.
    env["MPLBACKEND"] = "module://matplotlib_inline.backend_inline"
    # Decoding this pipe as UTF-8 below is only half the bargain: nbconvert
    # writes to it through *its* locale codec, and stdout is a pipe rather than
    # a terminal, so on Windows that is cp1252. Relaying a notebook line
    # containing the pipeline's own "═" separator then kills nbconvert itself
    # with UnicodeEncodeError. Both ends have to agree.
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
            config_backup=backup_path,
        )

    new_files = _new_or_changed(before, output_dirs)

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
                 + ("."if not crashed else
                    " without reporting an error of its own, which means the "
                    "process died rather than the notebook failing.")]
        for name, text in (("stderr", proc.stderr), ("stdout", proc.stdout)):
            if (text or "").strip():
                parts.append(f"--- {name} ---\n{text[-6000:]}")
        return RunResult(
            success=False,
            error_text="\n".join(parts),
            new_files=new_files,
            config_backup=backup_path,
            returncode=proc.returncode,
            crashed=crashed,
        )

    log_text = _extract_notebook_log(executed_path)
    plots = _save_plots(executed_path, PLOTS_DIR)
    return RunResult(
        success=True,
        log_text=log_text,
        new_files=new_files,
        executed_notebook=executed_path,
        config_backup=backup_path,
        plots=plots,
    )


def latest_plots() -> list[tuple[str, Path]]:
    """Plots saved by the most recent successful run_lca() call, without running anything.

    Home.py uses this for an at-a-glance view of the last run.
    """
    import json

    if not PLOTS_DIR.exists():
        return []
    captions_path = PLOTS_DIR / "captions.json"
    captions = (json.loads(captions_path.read_text(encoding="utf-8"))
                if captions_path.exists() else {})
    return [
        (captions.get(p.name, f"Figure {p.stem}"), p)
        for p in sorted(PLOTS_DIR.glob("*.png"))
    ]
