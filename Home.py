"""Home — project status for the Data Centre Optimiser.

Entry point for the multipage app. The work happens on one page:
  Data Centre Optimiser — size it, site it, tick the kit, get the optimal capacities.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

import dc_config as cfg
import lca_helpers as H
from optimisation import sites

st.set_page_config(page_title="UK Data Centre Optimiser", layout="wide")
st.title("UK Data Centre Optimiser")
st.caption("Cost and carbon of powering a UK data centre from grid, renewables, "
           "batteries and hydrogen, against half-hourly regional grid data.")

st.page_link("pages/2_Data_Centre_Optimiser.py", label="Open the Data Centre Optimiser",
             icon=":material/arrow_forward:")


@st.cache_resource(show_spinner="Connecting to Brightway…")
def _connect():
    H.setup_brightway()
    return True


st.header("Project status")
try:
    _connect()
    st.success(f"Connected to Brightway project **{cfg.PROJECT_NAME}**.")
    cols = st.columns(2)
    cols[0].metric("Ecoinvent", H.find_database_name(["ecoinvent", cfg.SYSTEM_MODEL]))
    cols[1].metric("Biosphere activities", len(H.bio) if H.bio is not None else "—")
except Exception as exc:
    st.error(f"Could not connect to Brightway project {cfg.PROJECT_NAME!r}: {exc}")

st.header("Grid series on disk")
st.caption("Half-hourly regional grid carbon the optimiser can use without a build. "
           "A site in any other region (or window) triggers a build (`optimisation/grid_build.py`).")
have = sites.available_grid_regions()
st.dataframe(
    pd.DataFrame(
        [{"region": r, "name": sites.CARBON_API_REGIONS.get(r, "?"), "files": len(have.get(r, [])),
          "windows": ", ".join(n.split("_cheap_", 1)[-1].removesuffix(".csv") for n in have.get(r, []))}
         for r in sorted(sites.CARBON_API_REGIONS)]
    ),
    width="stretch", hide_index=True,
)
