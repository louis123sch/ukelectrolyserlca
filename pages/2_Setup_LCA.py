"""Setup LCA — pick a foreground process, configure the background scenario, run it.

Foreground processes come from any non-ecoinvent/biosphere database in the
Brightway project: the built-in six electrolysis/H2 techs in "hydrogen
foreground", plus anything the Add Foreground page (page 1) has written.
Running this page patches dashboard_config.py with the chosen settings and
executes 2.dashboard_lca_adaptive.ipynb — the same pipeline the notebooks use.
"""

from __future__ import annotations

import datetime as dt
import os
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import dashboard_config as cfg
import lca_helpers as H
from backend.runner import REPO_DIR, run_lca

st.set_page_config(page_title="Setup LCA", layout="wide")
st.title("Setup LCA")
st.caption("Select a foreground process, configure the background scenario, then run it.")


@st.cache_resource(show_spinner="Connecting to Brightway…")
def _connect():
    H.setup_brightway()
    return True


try:
    _connect()
except Exception as exc:
    st.error(f"Could not open Brightway project {cfg.PROJECT_NAME!r}: {exc}")
    st.stop()

# =============================================================================
# 1. Foreground selection
# =============================================================================
st.header("1. Foreground process")

fg_databases = H.list_foreground_databases()
if not fg_databases:
    st.error("No foreground databases found in this Brightway project.")
    st.stop()

default_db_index = fg_databases.index(cfg.FOREGROUND_DB) if cfg.FOREGROUND_DB in fg_databases else 0
db_col, proc_col = st.columns([1, 2])
with db_col:
    selected_db = st.selectbox(
        "Foreground database",
        fg_databases,
        index=default_db_index,
        help="The built-in 'hydrogen foreground' plus any database written by the Add Foreground page.",
    )

processes = H.list_process_activities(selected_db)
if not processes:
    st.warning(f"No process activities found in {selected_db!r}.")
    st.stop()

# H2_CODES maps a human tech label ("PEM operation") to a Brightway activity
# *code* — it has no relation to the activity's own `name` field, so match on
# code to find which row (if any) is one of the 6 built-in techs.
code_to_known_label = {code: label for label, code in H.H2_CODES.items()}


def _tech_label(row):
    """The label used for TECH_SELECTED/ELECTROLYSER_TECHS/TECH_SOURCE_OVERRIDES."""
    return code_to_known_label.get(row["code"], row["name"])


def _display(row):
    known_label = code_to_known_label.get(row["code"])
    tag = f" · built-in tech ({known_label})" if known_label else ""
    elec = "" if row["has_electricity_input"] else "  ⚠ no direct electricity input"
    return f"{row['name']} ({row['unit']}){tag}{elec}"


with proc_col:
    processes_sorted = sorted(processes, key=lambda r: (r["code"] not in code_to_known_label, r["name"]))
    proc_options = {_display(r): r for r in processes_sorted}
    default_known_code = H.H2_CODES.get(cfg.TECH_SELECTED[0])
    default_proc_label = next(
        (lbl for lbl, r in proc_options.items() if r["code"] == default_known_code),
        next(iter(proc_options)),
    )
    selected_label = st.selectbox(
        "Foreground process to run through the LCA",
        list(proc_options.keys()),
        index=list(proc_options.keys()).index(default_proc_label),
    )
    selected_proc = proc_options[selected_label]

if not selected_proc["has_electricity_input"]:
    st.warning(
        "This process has no direct technosphere electricity exchange, so the grid/wind pipelines "
        "have nothing to swap out — the run will fail. Pick a process with a direct kWh electricity input."
    )

tech_label = _tech_label(selected_proc)
tech_overrides = {tech_label: (selected_proc["database"], selected_proc["code"])}

# =============================================================================
# 2. Background setup
# =============================================================================
st.header("2. Background setup")

strategy = st.radio(
    "Running strategy",
    ["Grid only", "Wind + grid (blended)", "Wind + grid (switching)", "Wind + grid (both)"],
    horizontal=True,
    help=(
        "Grid only runs the selected process against the live UK grid mix. "
        "Wind + grid dispatches a wind farm alongside the grid, in blended (fractional) "
        "or switching (all-or-nothing) mode."
    ),
)
run_grid_only = strategy == "Grid only"
wind_mode = {"Wind + grid (blended)": "blended", "Wind + grid (switching)": "switching",
             "Wind + grid (both)": "both"}.get(strategy)

loc_col, wind_col, elec_col = st.columns(3)
with loc_col:
    st.subheader("Location")
    lat = st.number_input("Latitude", value=float(cfg.WIND_LAT), format="%.4f")
    lon = st.number_input("Longitude", value=float(cfg.WIND_LON), format="%.4f")
    st.caption("Used to auto-pick the nearest GB Carbon Intensity API region and to site the wind farm.")
    method_mode = st.selectbox("Grid LCA method", ["cheap", "exact"], index=0,
                                help="'cheap' decomposes each tech once then reuses it per timeslice — much faster.")

with wind_col:
    st.subheader("Wind farm")
    wind_capacity_kw = st.number_input("Installed capacity (kW)", min_value=0.0,
                                        value=float(cfg.WIND_INSTALLED_CAPACITY_KW), step=100.0,
                                        disabled=run_grid_only)
    turbine_options = ["Vestas V90 2000", "Vestas V80 2000", "Siemens SWT 2300", "Enercon E70 2300", "Other…"]
    turbine_default = cfg.NINJA_TURBINE if cfg.NINJA_TURBINE in turbine_options else "Other…"
    turbine_choice = st.selectbox("Turbine model", turbine_options,
                                   index=turbine_options.index(turbine_default), disabled=run_grid_only)
    if turbine_choice == "Other…":
        turbine = st.text_input("Turbine model (renewables.ninja identifier)", value=cfg.NINJA_TURBINE,
                                 disabled=run_grid_only)
    else:
        turbine = turbine_choice
    hub_height = st.number_input("Hub height (m)", min_value=0.0, value=float(cfg.NINJA_HUB_HEIGHT_M),
                                  disabled=run_grid_only)

with elec_col:
    st.subheader("Electrolyser")
    st.caption(f"Selected process: **{tech_label}**")
    electrolyser_capacity_kw = st.number_input("Capacity (kW)", min_value=0.0,
                                                value=float(cfg.ELECTROLYSER_CAPACITY_KW), step=100.0,
                                                disabled=run_grid_only)
    min_load_frac = st.slider("Minimum load fraction", 0.0, 1.0, float(cfg.MIN_LOAD_FRACTION),
                               disabled=run_grid_only)
    wind_method_mode = st.selectbox("Wind LCA method", ["cheap", "exact"], index=0, disabled=run_grid_only)

st.subheader("Renewables.ninja API token")
ninja_token = st.text_input(
    "Token (leave blank to use a RENEWABLES_NINJA_TOKEN already set in your environment)",
    type="password",
    disabled=run_grid_only,
    help="Passed to the run as an environment variable only — never written to dashboard_config.py.",
)
if not run_grid_only and not (ninja_token or os.getenv("RENEWABLES_NINJA_TOKEN")):
    st.warning(
        "No Renewables.ninja token found (form, or RENEWABLES_NINJA_TOKEN env var). "
        "The wind fetch will fail without one."
    )

st.subheader("Time period")
time_mode = st.radio("Mode", ["single", "range", "year_average"], horizontal=True,
                      index=["single", "range", "year_average"].index(cfg.GRID_TIME_MODE))

if time_mode == "single":
    default_dt = dt.datetime.fromisoformat(cfg.GRID_SINGLE_DATETIME)
    d = st.date_input("Date", value=default_dt.date())
    t = st.time_input("Time", value=default_dt.time())
    single_datetime = f"{d.isoformat()} {t.strftime('%H:%M:%S')}"
    range_start = cfg.GRID_RANGE_START
    range_end = cfg.GRID_RANGE_END
    year = cfg.GRID_YEAR
elif time_mode == "range":
    default_start = dt.datetime.fromisoformat(cfg.GRID_RANGE_START).date()
    default_end = dt.datetime.fromisoformat(cfg.GRID_RANGE_END).date()
    c1, c2 = st.columns(2)
    start_date = c1.date_input("Start date", value=default_start)
    end_date = c2.date_input("End date", value=default_end)
    range_start = f"{start_date.isoformat()} 00:00:00"
    range_end = f"{end_date.isoformat()} 00:00:00"
    single_datetime = cfg.GRID_SINGLE_DATETIME
    year = cfg.GRID_YEAR
    st.caption("A multi-day/multi-month range fetches many half-hourly points — this can take a while.")
else:
    year = st.number_input("Year", min_value=2015, max_value=dt.date.today().year, value=int(cfg.GRID_YEAR))
    single_datetime = cfg.GRID_SINGLE_DATETIME
    range_start = cfg.GRID_RANGE_START
    range_end = cfg.GRID_RANGE_END
    st.caption("Runs 12 wind-based representative days for the year (average/top-10%/bottom-10% wind per season).")

# =============================================================================
# 3. Run
# =============================================================================
st.header("3. Run")

overrides = {
    "RUN_FOREGROUND_NOTEBOOK_FROM_DASHBOARD": False,
    "RUN_PRICE_NOTEBOOK_FROM_DASHBOARD": False,
    # The grid notebook always has to run when GRID_DATA_SOURCE="carbon_api":
    # the wind notebook gets its Carbon-Intensity-API rows from
    # DASHBOARD_GRID_RUN_ROWS, which 4.1 only sets once RUN_GRID_SCENARIO_LCA
    # lets it run to completion — so "Wind + grid" still needs this step even
    # though its own grid-only CSV output isn't what the user asked for.
    "RUN_GRID_NOTEBOOK_FROM_DASHBOARD": True,
    "RUN_GRID_SCENARIO_LCA": True,
    "RUN_WIND_NOTEBOOK_FROM_DASHBOARD": not run_grid_only,
    "RUN_WIND_GRID_LCA": not run_grid_only,
    "WIND_LCA_MODE": wind_mode or cfg.WIND_LCA_MODE,
    "METHOD_MODE": method_mode,
    "WIND_METHOD_MODE": wind_method_mode,
    "VALIDATE_CHEAP_METHOD": False,
    "TECH_SELECTED": [tech_label],
    "ELECTROLYSER_TECHS": [tech_label],
    "TECH_SOURCE_OVERRIDES": tech_overrides,
    "WIND_LAT": float(lat),
    "WIND_LON": float(lon),
    "CARBON_API_REGION_ID_OVERRIDE": None,
    "WIND_INSTALLED_CAPACITY_KW": float(wind_capacity_kw),
    "NINJA_TURBINE": turbine,
    "NINJA_HUB_HEIGHT_M": float(hub_height),
    "ELECTROLYSER_CAPACITY_KW": float(electrolyser_capacity_kw),
    "MIN_LOAD_FRACTION": float(min_load_frac),
    "GRID_TIME_MODE": time_mode,
    "GRID_SINGLE_DATETIME": single_datetime,
    "GRID_RANGE_START": range_start,
    "GRID_RANGE_END": range_end,
    "GRID_YEAR": int(year),
    "USE_GETPASS": False,
}
# Never written to dashboard_config.py — passed to the subprocess as an env var instead.
secrets = {"RENEWABLES_NINJA_TOKEN": ninja_token} if ninja_token else {}

with st.expander("Show dashboard_config.py overrides this run will apply"):
    st.json(overrides)

if st.button("Run LCA", type="primary"):
    with st.spinner("Patching dashboard_config.py and running the pipeline — this can take a while…"):
        result = run_lca(overrides, secrets=secrets)

    if not result.success:
        st.error("Run failed.")
        with st.expander("Error details", expanded=True):
            st.code(result.error_text or "(no output captured)")
        if result.config_backup:
            st.caption(f"dashboard_config.py before this run was backed up to {result.config_backup}")
    else:
        st.success("Run completed.")
        with st.expander("Run log"):
            st.code(result.log_text[-8000:])

        if not result.new_files:
            st.info("Run finished but no new/updated result files were detected.")
        for f in result.new_files:
            st.subheader(f.name)
            try:
                df = pd.read_csv(f)
            except Exception as exc:
                st.warning(f"Could not read {f.name}: {exc}")
                continue
            st.dataframe(df.head(20), width="stretch")

            gwp_col = tech_label if tech_label in df.columns else next(
                (c for c in df.columns if "gwp100_kgco2e_per_kg_h2" in c), None
            )
            dt_col = next((c for c in ["datetime", "DATETIME"] if c in df.columns), None)
            if gwp_col and dt_col and len(df) > 1:
                chart_df = df[[dt_col, gwp_col]].copy()
                chart_df[dt_col] = pd.to_datetime(chart_df[dt_col], errors="coerce")
                st.line_chart(chart_df.set_index(dt_col)[gwp_col])
            elif gwp_col and len(df) >= 1:
                st.metric(f"{gwp_col} (kg CO2eq/kg H2)", f"{df[gwp_col].iloc[0]:.4f}")

        st.caption(f"Executed notebook saved to {result.executed_notebook}")
