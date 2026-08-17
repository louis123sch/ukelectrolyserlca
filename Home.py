"""Home — project status and latest results.

Entry point for the multipage app:
  1. Add Foreground  — paper/document → reviewed Brightway foreground database.
  2. Setup LCA       — pick a foreground process, configure the grid/wind background, run it.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

import dashboard_config as cfg
import lca_helpers as H

st.set_page_config(page_title="UK Electrolyser LCA", layout="wide")
st.title("UK Electrolyser LCA")
st.caption("Hydrogen electrolyser life-cycle assessment against the live UK grid and wind data.")

st.markdown(
    """
Use the sidebar to navigate:

- **1 Add Foreground** — turn a paper, datasheet or spec into a reviewed Brightway foreground process.
- **2 Setup LCA** — pick any foreground process (built-in or newly added), configure the background
  scenario (grid region, wind farm, running strategy, time period), and run the LCA.
"""
)


@st.cache_resource(show_spinner="Connecting to Brightway…")
def _connect():
    H.setup_brightway()
    return True


st.header("Project status")
try:
    _connect()
    st.success(f"Connected to Brightway project **{cfg.PROJECT_NAME}**.")

    cols = st.columns(4)
    cols[0].metric("Ecoinvent", H.find_database_name(["ecoinvent", cfg.SYSTEM_MODEL]))
    cols[1].metric("Biosphere activities", len(H.bio) if H.bio is not None else "—")

    fg_dbs = H.list_foreground_databases()
    cols[2].metric("Foreground databases", len(fg_dbs))
    total_processes = sum(len(H.list_process_activities(db)) for db in fg_dbs)
    cols[3].metric("Foreground processes", total_processes)

    with st.expander("Foreground databases and processes", expanded=True):
        for db in fg_dbs:
            rows = H.list_process_activities(db)
            tag = " (built-in)" if db == cfg.FOREGROUND_DB else " (from Add Foreground)"
            st.markdown(f"**{db}**{tag} — {len(rows)} process(es)")
            if rows:
                st.dataframe(
                    pd.DataFrame(rows)[["name", "reference_product", "unit", "has_electricity_input"]],
                    width="stretch", hide_index=True,
                )
except Exception as exc:
    st.error(f"Could not connect to Brightway project {cfg.PROJECT_NAME!r}: {exc}")

st.header("Latest results")


def _latest_csv(folder: str, pattern: str = "*.csv"):
    p = Path(folder)
    if not p.exists():
        return None
    files = sorted(p.glob(pattern), key=lambda f: f.stat().st_mtime, reverse=True)
    return files[0] if files else None


result_cols = st.columns(3)
result_specs = [
    ("Grid (Carbon Intensity API)", cfg.GRID_OUTPUT_DIR, "custom_grid_lca_carbon_api_*.csv"),
    ("Wind + grid — blended", cfg.WIND_OUTPUT_DIR_BLENDED, "*.csv"),
    ("Wind + grid — switching", cfg.WIND_OUTPUT_DIR_SWITCHING, "*.csv"),
]
for col, (label, folder, pattern) in zip(result_cols, result_specs):
    with col:
        st.subheader(label)
        latest = _latest_csv(folder, pattern)
        if latest is None:
            st.caption("No results yet — run one from **2 Setup LCA**.")
            continue
        st.caption(latest.name)
        try:
            df = pd.read_csv(latest)
            st.dataframe(df.head(5), width="stretch", hide_index=True)
        except Exception as exc:
            st.warning(f"Could not read {latest.name}: {exc}")
