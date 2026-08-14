"""Streamlit "Run LCA" backend.

dashboard_config.py is the project's single source of truth for every
notebook — its own docstring says as much ("Edit this file once, save it,
restart the notebook kernel, then run"). The Setup-LCA Streamlit page follows
that same contract instead of inventing a second one: it patches the on-disk
dashboard_config.py with the values chosen in the form, then runs the same
2.dashboard_lca_adaptive.ipynb notebook every manual workflow already uses.

This keeps 100% of the actual LCA science (Carbon Intensity API client, wind
dispatch logic, Brightway calls) in the tested notebooks/lca_helpers.py — this
module only edits config text, runs a subprocess, and collects results.
"""

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO_DIR / "dashboard_config.py"
RUNS_DIR = REPO_DIR / "_streamlit_runs"
RUNNER_NOTEBOOK = "2.dashboard_lca_adaptive.ipynb"

OUTPUT_DIRS = [
    "custom_grid_lca_outputs",
    "blended_wind_grid_lca_outputs",
    "hybrid_wind_grid_lca_outputs",
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


def _extract_notebook_log(nb_path: Path, max_chars: int = 20000) -> str:
    import json

    nb = json.loads(nb_path.read_text())
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


def run_lca(overrides: dict, timeout_s: int = 1800) -> RunResult:
    """Apply ``overrides`` to dashboard_config.py and execute the adaptive dashboard notebook.

    ``overrides`` maps dashboard_config.py variable names to their new values,
    e.g. {"GRID_TIME_MODE": "single", "TECH_SELECTED": ["PEM operation"]}.
    """
    RUNS_DIR.mkdir(exist_ok=True)

    base_text = CONFIG_PATH.read_text()
    backup_path = RUNS_DIR / "dashboard_config.before_last_run.py"
    backup_path.write_text(base_text)

    new_text = apply_config_overrides(base_text, overrides)
    CONFIG_PATH.write_text(new_text)

    output_dirs = [REPO_DIR / d for d in OUTPUT_DIRS]
    before = _snapshot(output_dirs)

    python_exe = Path(sys.executable)
    nbconvert_exe = python_exe.with_name("jupyter-nbconvert")
    if not nbconvert_exe.exists():
        nbconvert_exe = "jupyter-nbconvert"  # fall back to PATH lookup

    executed_path = RUNS_DIR / "last_run_executed.ipynb"
    cmd = [
        str(nbconvert_exe),
        "--to", "notebook",
        "--execute",
        f"--ExecutePreprocessor.timeout={timeout_s}",
        "--ExecutePreprocessor.kernel_name=python3",
        "--output", str(executed_path),
        str(REPO_DIR / RUNNER_NOTEBOOK),
    ]

    try:
        proc = subprocess.run(
            cmd,
            cwd=REPO_DIR,
            capture_output=True,
            text=True,
            timeout=timeout_s + 60,
        )
    except subprocess.TimeoutExpired as exc:
        return RunResult(
            success=False,
            error_text=f"Run timed out after {timeout_s}s.\n{exc.stdout or ''}\n{exc.stderr or ''}",
            config_backup=backup_path,
        )

    new_files = _new_or_changed(before, output_dirs)

    if proc.returncode != 0 or not executed_path.exists():
        return RunResult(
            success=False,
            error_text=(proc.stderr or proc.stdout or "nbconvert failed with no output")[-8000:],
            new_files=new_files,
            config_backup=backup_path,
        )

    log_text = _extract_notebook_log(executed_path)
    return RunResult(
        success=True,
        log_text=log_text,
        new_files=new_files,
        executed_notebook=executed_path,
        config_backup=backup_path,
    )
