"""Size Optimiser — pick the demand, let the programme size the supply.

You fix the demand side (technology, rating, running strategy), the site and
the date range, and an emissions threshold. This searches for the cheapest
wind / solar / battery build that still meets the threshold.

The science lives in ``optimisation/sizing.py`` and ``optimisation/profiles.py``;
this page only collects settings, calls them, and displays the result.
"""

from __future__ import annotations

import datetime as dt
import importlib
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

REPO_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_DIR))

import dashboard_config as cfg
import lca_helpers as H
from optimisation import profiles, renewables, sizing

for _mod in (renewables, profiles, sizing):
    importlib.reload(_mod)

st.set_page_config(page_title="Size Optimiser", layout="wide")
st.title("Size Optimiser")
st.caption(
    "Fix the demand, and find the cheapest wind, solar and battery build that "
    "still meets an emissions threshold."
)


@st.cache_resource(show_spinner="Connecting to Brightway…")
def _connect():
    H.setup_brightway()
    return True


try:
    _connect()
except Exception as exc:
    st.error(f"Could not open the Brightway project: {exc}")
    st.stop()

# =============================================================================
# 1. What is being powered
# =============================================================================
st.header("1. What are you powering?")
demand_type = st.radio(
    "Demand", ["Electrolyser", "Data centre"], horizontal=True,
    help="The data centre case is a fixed 7.31 MW flat load — the Zhang et al. "
         "foreground's own figure. It is not wired into the optimiser yet.",
)

if demand_type == "Data centre":
    st.info(
        "**Not wired up yet.** The data centre is a fixed 7.31 MW flat load, so it "
        "fits this optimiser's shape exactly — the only differences are that the "
        "output is MWh served rather than kg of hydrogen, and the emissions "
        "threshold would be gCO₂e/kWh rather than the hydrogen standard. Its grid "
        "baseline is on the **Optimisation Inputs** page. Pick *Electrolyser* to "
        "run the optimiser."
    )
    st.stop()

# =============================================================================
# 2. The electrolyser
# =============================================================================
st.header("2. The electrolyser")
c1, c2, c3 = st.columns(3)
with c1:
    tech = st.selectbox("Technology", list(H.ELECTROLYSER_CODES),
                        index=list(H.ELECTROLYSER_CODES).index("PEM operation"))
    capacity_mw = st.number_input("Rating (MW)", 0.1, 1000.0, 10.0, step=1.0)
with c2:
    strategy = st.selectbox("Running strategy", list(sizing.STRATEGIES))
    st.caption(sizing.STRATEGIES[strategy])
with c3:
    min_load = st.slider("Minimum load (fraction of rating)", 0.0, 0.5, 0.10, 0.05,
                         help="Below this the stack shuts down rather than "
                              "turning down further.")
    clean_thresh = st.number_input(
        "Clean-grid threshold (kg CO₂e/kWh)", 0.0, 0.5, 0.05, 0.01,
        disabled=(strategy != "grid_when_clean"),
        help="Only used by the grid_when_clean strategy: import is allowed only "
             "when grid intensity is at or below this.")


@st.cache_data(show_spinner="Reading electrolyser coefficients from Brightway…")
def _ely_coeffs(tech_: str):
    e = sizing.load_electrolyser(tech_)
    return e.kwh_per_kg, e.fixed_kgco2e_per_kg


kwh_per_kg, fixed_kg = _ely_coeffs(tech)
st.caption(
    f"From the Brightway foreground: **{kwh_per_kg:.1f} kWh/kg H₂**, plus a "
    f"non-electricity (stack and balance-of-plant) burden of "
    f"**{fixed_kg:.4f} kg CO₂e/kg H₂**."
)

# =============================================================================
# 3. Site and period
# =============================================================================
st.header("3. Site and period")
c1, c2, c3 = st.columns(3)
with c1:
    lat = st.number_input("Latitude", -90.0, 90.0, float(cfg.WIND_LAT), format="%.4f")
    lon = st.number_input("Longitude", -180.0, 180.0, float(cfg.WIND_LON), format="%.4f")
with c2:
    start = st.date_input("Start", dt.date(2025, 1, 1))
    end = st.date_input("End", dt.date(2025, 3, 31))
with c3:
    turbine = st.text_input("Turbine", cfg.NINJA_TURBINE)
    tilt = st.number_input("PV tilt (degrees)", 0.0, 90.0, 35.0, step=5.0)

st.caption(
    "Wind and solar profiles come from Renewables.ninja at these coordinates and "
    "are cached on disk. Grid intensity and price are read from the CSVs the "
    "existing pipeline writes — the period must already be covered by a "
    "**continuous** run of notebooks 3.1 and 5."
)

# =============================================================================
# 4. Target and search space
# =============================================================================
st.header("4. Emissions target")
c1, c2 = st.columns([1, 2])
with c1:
    use_lchs = st.checkbox("UK Low Carbon Hydrogen Standard", value=True)
    threshold = st.number_input(
        "Threshold (g CO₂e/MJ LHV)", 0.1, 200.0,
        float(sizing.LCHS_GCO2E_PER_MJ), step=1.0, disabled=use_lchs)
    if use_lchs:
        threshold = sizing.LCHS_GCO2E_PER_MJ
    cost_case = st.radio("Cost case", ["low", "central", "high"], index=1,
                         horizontal=True)
with c2:
    limit_kg = sizing.lchs_kgco2e_per_kg(threshold)
    budget = (limit_kg - fixed_kg) / kwh_per_kg * 1000.0
    st.metric("Equivalent limit", f"{limit_kg:.2f} kg CO₂e / kg H₂")
    if budget <= 0:
        st.error(
            f"The stack's own {fixed_kg:.3f} kg CO₂e/kg already exceeds this "
            "threshold. No amount of clean electricity can comply."
        )
    else:
        st.metric("Leaves for electricity", f"{budget:.1f} g CO₂e / kWh")
        st.caption(
            f"After the stack's {fixed_kg:.3f} kg CO₂e/kg "
            f"({100*fixed_kg/limit_kg:.0f}% of the budget). For reference: onshore "
            f"wind ≈ 5.6, solar PV ≈ 56.7, GB grid mean ≈ 237 g CO₂e/kWh."
        )

with st.expander("Search space (multiples of the electrolyser's rating)"):
    b1, b2, b3, b4 = st.columns(4)
    wind_max = b1.number_input("Max wind", 0.5, 50.0, 5.0, step=1.0)
    solar_max = b2.number_input("Max solar", 0.0, 50.0, 5.0, step=1.0)
    bmw_max = b3.number_input("Max battery power", 0.0, 20.0, 2.0, step=0.5)
    bh_max = b4.number_input("Max battery hours", 0.0, 48.0, 8.0, step=1.0)
    e1, e2 = st.columns(2)
    maxiter = e1.slider("Solver iterations", 10, 120, 40, 10)
    popsize = e2.slider("Population size", 5, 30, 12, 1)

# =============================================================================
# 5. Run
# =============================================================================
st.header("5. Run")
if st.button("Find the optimal build", type="primary"):
    try:
        with st.spinner("Loading wind, solar, grid and price profiles…"):
            prof, meta = profiles.build(
                lat, lon, str(start), str(end), turbine=turbine, tilt=tilt)
    except Exception as exc:
        st.error(str(exc))
        st.stop()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Slices", f"{meta['slices']:,}")
    m2.metric("Mean wind CF", f"{meta['mean_wind_cf']:.1%}")
    m3.metric("Mean solar CF", f"{meta['mean_solar_cf']:.1%}")
    m4.metric("Mean grid", f"{meta['mean_grid_kgco2e_per_kwh']*1000:.0f} g/kWh")
    if meta["missing_slices"]:
        st.caption(
            f"{meta['missing_slices']} slices missing from the grid series "
            f"(largest gap {meta['largest_gap_hours']:.1f} h) — API dropouts, "
            "carried over by the dispatch."
        )

    ely = sizing.load_electrolyser(
        tech, capacity_mw=capacity_mw, strategy=strategy,
        min_load_fraction=min_load,
        clean_grid_threshold_kgco2e_per_kwh=clean_thresh)
    bounds = sizing.Bounds(
        wind_mw=(0.0, wind_max), solar_mwp=(0.0, solar_max),
        battery_mw=(0.0, bmw_max), battery_hours=(0.0, bh_max))

    bar = st.progress(0.0, text="Searching…")
    budget_evals = max(1, maxiter * popsize * 4)

    def _tick(n):
        bar.progress(min(0.99, n / budget_evals), text=f"Searching… {n} dispatches")

    with st.spinner("Optimising…"):
        r = sizing.optimise(prof, ely, threshold_g_per_mj=threshold,
                            cost_case=cost_case, bounds=bounds,
                            maxiter=maxiter, popsize=popsize, progress=_tick)
    bar.empty()
    st.session_state["sizing_result"] = r
    st.session_state["sizing_meta"] = meta

r = st.session_state.get("sizing_result")
if r:
    meta = st.session_state.get("sizing_meta", {})
    st.divider()
    if r["meets_threshold"]:
        st.success(
            f"**Meets the threshold** — {r['gco2e_per_mj']:.2f} g CO₂e/MJ against a "
            f"limit of {r['threshold_g_per_mj']:g}. Found in {r['evaluations']:,} "
            "dispatch evaluations."
        )
    else:
        st.error(r.get("infeasible_reason", "Threshold not met."))

    st.subheader("Optimal build")
    b1, b2, b3, b4 = st.columns(4)
    b1.metric("Wind", f"{r['wind_mw']:,.1f} MW")
    b2.metric("Solar", f"{r['solar_mwp']:,.1f} MWp")
    b3.metric("Battery power", f"{r['battery_mw']:,.2f} MW")
    b4.metric("Battery energy", f"{r['battery_mwh']:,.1f} MWh",
              help=f"{r['battery_hours']:.1f} hours at rated power. Starts full.")

    st.subheader("Result")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("LCOH", f"£{r['lcoh_gbp_per_kg']:,.2f}/kg")
    k2.metric("Emissions", f"{r['gco2e_per_mj']:.2f} g/MJ",
              help=f"{r['kgco2e_per_kg']:.3f} kg CO₂e per kg H₂")
    k3.metric("Hydrogen", f"{r['h2_kg_yr']/1000:,.0f} t/y")
    k4.metric("Electrolyser CF", f"{r['capacity_factor']:.1%}")

    k1, k2, k3 = st.columns(3)
    k1.metric("Renewable fraction", f"{r['renewable_fraction']:.1%}")
    k2.metric("Grid import", f"{r['grid_kwh_yr']/1e6:,.1f} GWh/y")
    k3.metric("Curtailed", f"{r['curtailed_kwh_yr']/1e6:,.1f} GWh/y")

    cost = pd.DataFrame({
        "component": ["wind", "solar", "battery", "electrolyser", "grid"],
        "GBP_per_year": [r["cost_wind"], r["cost_solar"], r["cost_battery"],
                         r["cost_electrolyser"], r["cost_grid"]],
    })
    cost["share"] = cost.GBP_per_year / cost.GBP_per_year.sum()
    cost["GBP_per_kg_H2"] = cost.GBP_per_year / r["h2_kg_yr"]

    emis = pd.DataFrame({
        "component": ["wind", "solar", "battery", "grid", "stack"],
        "kgCO2e_per_year": [r["em_wind"], r["em_solar"], r["em_battery"],
                            r["em_grid"], r["em_stack"]],
    })
    emis["share"] = emis.kgCO2e_per_year / emis.kgCO2e_per_year.sum()
    emis["gCO2e_per_MJ"] = (emis.kgCO2e_per_year / r["h2_kg_yr"]
                            * 1000.0 / sizing.H2_LHV_MJ_PER_KG)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Cost**")
        st.dataframe(cost, hide_index=True, width="stretch")
    with c2:
        st.markdown("**Emissions**")
        st.dataframe(emis, hide_index=True, width="stretch")

    if r["binding_bounds"]:
        st.warning(
            "Against the search limit on **" + "**, **".join(r["binding_bounds"])
            + "** — the answer is shaped by the search space, not by cost or "
              "physics. Widen those bounds and re-run."
        )
    if r["solar_mwp"] < 0.05 * capacity_mw and r["wind_mw"] > 0:
        st.info(
            "**Solar was sized to roughly zero.** With ecoinvent 3.9.1's GB PV "
            "dataset at ~57 g CO₂e/kWh — a 2012 multi-Si plant — solar is too "
            "carbon-intensive to help against a hydrogen standard, even though it "
            "is cheap. Modern PV would be ~20–40 g/kWh and could change this "
            "result, so read it as a dataset-vintage artefact rather than a "
            "finding about solar."
        )

    out = pd.DataFrame([{k: v for k, v in r.items()
                         if not isinstance(v, (list, dict))}])
    st.download_button("Download result as CSV",
                       out.to_csv(index=False).encode("utf-8"),
                       "sizing_result.csv", "text/csv")
