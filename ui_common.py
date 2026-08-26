"""Shared plumbing for the Streamlit pages.

Helpers that were previously copy-pasted into each page live here. Widget
*values* live in ``ui_defaults.py``; modelling science lives in
``optimisation/``. This file should stay boring — display and I/O only.
"""

from __future__ import annotations

import contextlib
import io
from pathlib import Path

import pandas as pd
import streamlit as st

REPO_DIR = Path(__file__).resolve().parent


@st.cache_resource(show_spinner="Connecting to Brightway…")
def connect_brightway() -> bool:
    # Imported lazily so merely importing this module does not pull in Brightway.
    import lca_helpers as H

    H.setup_brightway()
    return True


def capture(fn, *args, **kwargs):
    """Run a module function, returning (result, its printed output)."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        result = fn(*args, **kwargs)
    return result, buf.getvalue()


def show_console(text: str, label: str = "Module output — cross-checks and caveats") -> None:
    """Show a module's stdout in a collapsed expander, if it wrote anything.

    Named `show_console` rather than `console` because pages bind captured
    output to a local called `console`, which would shadow the function.
    """
    if text.strip():
        with st.expander(label):
            st.code(text, language="text")


def download(df: pd.DataFrame, name: str, label: str | None = None) -> None:
    st.download_button(
        label or f"Download {name}",
        df.to_csv(index=False).encode("utf-8"),
        file_name=name,
        mime="text/csv",
        key=f"dl_{name}",
    )


def latest_csv(folder, pattern: str = "*.csv") -> Path | None:
    """Newest CSV in `folder`, anchored at the repo so the launch cwd cannot matter."""
    p = Path(folder)
    if not p.is_absolute():
        p = REPO_DIR / p
    if not p.exists():
        return None
    files = sorted(p.glob(pattern), key=lambda f: f.stat().st_mtime, reverse=True)
    return files[0] if files else None
