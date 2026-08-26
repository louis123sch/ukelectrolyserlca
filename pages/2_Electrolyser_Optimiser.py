"""Electrolyser Optimiser — pick the demand, let the programme size the supply.

You fix the demand side (technology, rating, running strategy), the site and
the date range, and an emissions threshold. This searches for the cheapest
wind / solar / battery build that still meets the threshold.

The science lives in ``optimisation/sizing.py`` and ``optimisation/profiles.py``;
the cost and carbon inputs come from ``optimisation/tech_costs.py``,
``optimisation/renewables.py`` and ``optimisation/battery.py`` and are shown in
the *Inputs* section below, so there is never a second implementation of the
science to keep in sync. Pressing *Run* first builds whatever input data the
run needs (grid/price series, Renewables.ninja profiles, the embodied-carbon
decomposition), then runs the search — one progress bar covers both.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import dashboard_config as cfg
import lca_helpers as H
import ui_defaults as D
from optimisation import battery, profiles, renewables, sites, sizing, tech_costs
from ui_common import REPO_DIR, capture, connect_brightway, download, show_console

# ui_defaults is reloaded too so edits to it land on a rerun. ui_common is NOT:
# reloading it would rebuild its @st.cache_resource function and reconnect to
# Brightway on every interaction.
for _mod in (tech_costs, renewables, battery, profiles, sites, sizing, D):
    importlib.reload(_mod)

st.set_page_config(page_title="Electrolyser Optimiser", layout="wide")
st.title("Electrolyser Optimiser")
st.caption(
    "Fix the demand, and find the cheapest wind, solar and battery build that "
    "still meets an emissions threshold."
)


try:
    connect_brightway()
except Exception as exc:
    st.error(f"Could not open the Brightway project: {exc}")
    st.stop()

st.info(
    "Powering a **data centre** instead? That optimiser — with its grid "
    "baseline, hydrogen storage and the full architecture matrix — has its own "
    "page.",
    icon="🏢",
)
st.page_link("pages/3_Data_Centre_Optimiser.py", label="Go to the Data Centre Optimiser →")

# =============================================================================
# 1. The electrolyser
# =============================================================================
st.header("1. The electrolyser")
c1, c2, c3 = st.columns(3)
with c1:
    tech = st.selectbox("Technology", list(H.ELECTROLYSER_CODES),
                        index=list(H.ELECTROLYSER_CODES).index(D.ELY_TECH))
    capacity_mw = st.number_input("Rating (MW)", D.ELY_RATING_MW_MIN, D.ELY_RATING_MW_MAX,
                                  D.ELY_RATING_MW, step=D.ELY_RATING_MW_STEP)
with c2:
    strategy = st.selectbox("Running strategy", list(sizing.STRATEGIES))
    st.caption(sizing.STRATEGIES[strategy])
with c3:
    min_load = st.slider("Minimum load (fraction of rating)", D.ELY_MIN_LOAD_MIN,
                         D.ELY_MIN_LOAD_MAX, D.ELY_MIN_LOAD, D.ELY_MIN_LOAD_STEP,
                         help="Below this the stack shuts down rather than "
                              "turning down further.")
    clean_thresh = st.number_input(
        "Clean-grid threshold (kg CO₂e/kWh)", D.ELY_CLEAN_THRESHOLD_MIN,
        D.ELY_CLEAN_THRESHOLD_MAX, D.ELY_CLEAN_THRESHOLD, D.ELY_CLEAN_THRESHOLD_STEP,
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
# 2. Site and period
# =============================================================================
st.header("2. Site and period")
c1, c2, c3 = st.columns(3)
with c1:
    lat = st.number_input("Latitude", D.ELY_LAT_MIN, D.ELY_LAT_MAX, float(cfg.WIND_LAT), format="%.4f")
    lon = st.number_input("Longitude", D.ELY_LON_MIN, D.ELY_LON_MAX, float(cfg.WIND_LON), format="%.4f")
with c2:
    start = st.date_input("Start", D.ELY_START_DATE)
    end = st.date_input("End", D.ELY_END_DATE)
with c3:
    turbine = st.text_input("Turbine", cfg.NINJA_TURBINE)
    tilt = st.number_input("PV tilt (degrees)", D.ELY_PV_TILT_MIN, D.ELY_PV_TILT_MAX,
                           D.ELY_PV_TILT, step=D.ELY_PV_TILT_STEP)

st.caption(
    "The coordinate drives everything that varies by location: the "
    "Renewables.ninja wind and solar profiles, and the Carbon Intensity region "
    "whose half-hourly grid mix is used. Both are cached on disk."
)


@st.cache_data(show_spinner="Resolving the coordinate…")
def _resolve(lat_: float, lon_: float):
    s = sites.resolve(lat_, lon_)
    return s.name, s.carbon_api_region, s.region_name


try:
    site_name, ely_region, ely_region_name = _resolve(lat, lon)
except Exception as exc:
    st.error(f"Could not resolve that coordinate: {exc}")
    st.stop()

r1, r2 = st.columns(2)
r1.metric("Resolved to", site_name)
r2.metric("Carbon Intensity region", f"{ely_region} · {ely_region_name}")

_have = sites.available_grid_regions()
if ely_region in _have:
    st.success(
        f"Grid series cached for region {ely_region} ({ely_region_name}). "
        "Price data is national, so it applies everywhere."
    )
else:
    _cached = ", ".join(f"{r} ({sites.CARBON_API_REGIONS[r]})"
                        for r in sorted(_have)) or "none"
    st.error(
        f"**No cached grid series for region {ely_region} "
        f"({ely_region_name}).** Cached: {_cached}.\n\n"
        "Scoring this site against another region's half-hourly intensities "
        "would produce a confident wrong answer about whether renewables beat "
        "the grid here, so the run is blocked. The series is shared between "
        "both optimisers, so building it once serves either."
    )
    if st.button(f"Build the grid series for region {ely_region} now"):
        with st.status(
                f"Building grid series for region {ely_region} "
                f"({ely_region_name}) — this runs the Carbon Intensity "
                "notebook and can take 30+ minutes. Leave this page open.",
                expanded=True) as _s:
            try:
                sites.build_grid_series(ely_region)
                _s.update(label="Grid series built.", state="complete")
                st.rerun()
            except Exception as exc:
                _s.update(label="Build failed.", state="error")
                st.code(str(exc), language="text")
    st.stop()

# =============================================================================
# 3. Target and search space
# =============================================================================
st.header("3. Emissions target")
c1, c2 = st.columns([1, 2])
with c1:
    use_lchs = st.checkbox("UK Low Carbon Hydrogen Standard", value=D.ELY_USE_LCHS)
    threshold = st.number_input(
        "Threshold (g CO₂e/MJ LHV)", D.ELY_THRESHOLD_MIN, D.ELY_THRESHOLD_MAX,
        float(sizing.LCHS_GCO2E_PER_MJ), step=D.ELY_THRESHOLD_STEP, disabled=use_lchs)
    if use_lchs:
        threshold = sizing.LCHS_GCO2E_PER_MJ
    cost_case = st.radio("Cost case", D.COST_CASES, index=D.COST_CASE_INDEX,
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
    wind_max = b1.number_input("Max wind", D.ELY_WIND_MAX_MIN, D.ELY_WIND_MAX_MAX,
                               D.ELY_WIND_MAX, step=D.ELY_WIND_MAX_STEP)
    solar_max = b2.number_input("Max solar", D.ELY_SOLAR_MAX_MIN, D.ELY_SOLAR_MAX_MAX,
                                D.ELY_SOLAR_MAX, step=D.ELY_SOLAR_MAX_STEP)
    bmw_max = b3.number_input("Max battery power", D.ELY_BATT_MW_MIN, D.ELY_BATT_MW_MAX,
                              D.ELY_BATT_MW, step=D.ELY_BATT_MW_STEP)
    bh_max = b4.number_input("Max battery hours", D.ELY_BATT_H_MIN, D.ELY_BATT_H_MAX,
                             D.ELY_BATT_H, step=D.ELY_BATT_H_STEP)
    e1, e2 = st.columns(2)
    maxiter = e1.slider("Solver iterations", D.ELY_MAXITER_MIN, D.ELY_MAXITER_MAX,
                        D.ELY_MAXITER, D.ELY_MAXITER_STEP)
    popsize = e2.slider("Population size", D.ELY_POPSIZE_MIN, D.ELY_POPSIZE_MAX,
                        D.ELY_POPSIZE, D.ELY_POPSIZE_STEP)

# =============================================================================
# 4. Inputs — the coefficients the optimiser will use
# =============================================================================
st.header("4. Inputs")
st.caption(
    "Every number below is produced by a module in `optimisation/` — this page "
    "only calls them and displays what they return. The same tables feed the "
    "run button, so what you see is what the optimiser uses. The cost case is "
    f"the one chosen above (**{cost_case}**)."
)

tab_gen, tab_batt, tab_src = st.tabs(["Generation", "Battery", "Sources"])

with tab_gen:
    st.subheader("Wind and solar — cost and embodied carbon")

    @st.cache_data(show_spinner="Loading generation costs…")
    def _gen_costs():
        return capture(tech_costs.run)

    # The ecoinvent decomposition is case-independent, so it is cached once and
    # the (cheap) restatement is applied per scenario. Caching the whole thing
    # on `case` instead made every scenario switch re-solve the LCI — ~30 s.
    @st.cache_data(show_spinner="Decomposing embodied carbon from ecoinvent…")
    def _gen_decompose():
        return capture(renewables.decompose_all)

    try:
        (long_df, ann_df), cost_console = _gen_costs()
        st.markdown("**Costs** — DESNZ/Arup 2024, real 2023 prices")
        view = ann_df[ann_df.case == cost_case][[
            "asset", "capex_GBP_per_MW", "opex_GBP_per_MW_year", "net_load_factor",
            "lifetime_years", "discount_rate", "lcoe_GBP_per_MWh",
            "reported_lcoe_GBP_per_MWh", "lcoe_delta_pct"]]
        st.dataframe(view, width="stretch", hide_index=True)
        st.caption(
            "`lcoe_delta_pct` compares this module's plain CRF annuity against each "
            "report's own published LCOE. The residual is methodological — the DESNZ "
            "calculator also discounts construction-period spend."
        )
        download(ann_df, "generation_costs_annualised.csv")
        show_console(cost_console, "tech_costs.py output")

        st.divider()
        rows, carbon_console = _gen_decompose()
        emb = renewables.apply_case(rows, cost_case)
        st.markdown("**Embodied carbon** — per MW installed, decomposed out of ecoinvent")
        st.dataframe(
            emb[["technology", "capital_kgco2e_per_MW", "ecoinvent_implied_load_factor",
                 "study_load_factor", "study_lifetime_years",
                 "restated_kgco2e_per_kWh", "ecoinvent_per_kWh", "ratio_to_ecoinvent"]],
            width="stretch", hide_index=True,
        )
        w = emb[emb.technology == "onshore_wind"].iloc[0]
        st.warning(
            f"**ecoinvent's implied yield is not this study's yield.** Its GB onshore "
            f"wind assumes {w.ecoinvent_lifetime_kWh_per_kW:,.0f} kWh/kW over life "
            f"({w.ecoinvent_implied_load_factor:.1%} for "
            f"{w.ecoinvent_lifetime_years:.0f} y); on the **{cost_case}** cost case "
            f"DESNZ/Arup give {w.study_lifetime_kWh_per_kW:,.0f} kWh/kW "
            f"({w.study_load_factor:.1%} for {w.study_lifetime_years:.0f} y) — "
            f"{w.study_lifetime_kWh_per_kW / w.ecoinvent_lifetime_kWh_per_kW:.1f}× more. "
            f"This optimiser therefore uses the per-MW figures."
        )
        pv = emb[emb.technology == "solar_pv"].iloc[0]
        st.info(
            f"**PV is a conservative upper bound.** ecoinvent 3.9.1's GB open-ground PV "
            f"is a 2012 multi-Si plant, so it restates to "
            f"~{pv.restated_kgco2e_per_kWh*1000:.0f} g CO₂e/kWh against ~20–40 g/kWh in "
            f"current literature. Wind, being mostly steel and concrete, is far less "
            f"affected."
        )
        download(emb.drop(columns=["_parts"]), "renewables_embodied.csv")
        show_console(carbon_console, "renewables.py output")
    except Exception as exc:
        st.error(f"Generation inputs failed: {exc}")

with tab_batt:
    st.subheader("Battery storage — Li-ion LFP")
    durations = st.multiselect(
        "Durations to tabulate (hours)", D.ELY_DURATION_OPTIONS, default=D.ELY_DURATIONS,
        help="Power and energy are costed separately, so any duration is valid — "
             "the optimiser searches duration continuously either way.",
    ) or D.ELY_DURATIONS

    @st.cache_data(show_spinner="Loading battery inputs…")
    def _batt(durs: tuple):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            battery.run()
        return battery.cost_table(durs), battery.carbon_table(durs), buf.getvalue()

    try:
        ct, kt, console = _batt(tuple(sorted(durations)))
        comp = battery.cost_components()[cost_case]
        c = st.columns(4)
        c[0].metric("Capex, power", f"£{comp['power_GBP_per_kW']:,.0f}/kW")
        c[1].metric("Capex, energy", f"£{comp['energy_GBP_per_kWh']:,.0f}/kWh")
        c[2].metric("Embodied, energy",
                    f"{battery.embodied_components()['energy_kgco2e_per_kWh']:,.0f} kg/kWh")
        c[3].metric("Throughput",
                    f"{battery.lifetime_throughput_mwh_per_mwh():,.0f} MWh/MWh")

        merged = (ct[ct.case == cost_case]
                  .merge(kt, on="duration_h")
                  [["duration_h", "capex_GBP_per_MW", "capex_GBP_per_kWh",
                    "total_annual_GBP_per_kW_year", "embodied_tco2e_per_MW",
                    "embodied_kgco2e_per_MWh_throughput"]])
        st.dataframe(merged, width="stretch", hide_index=True)
        download(ct, "battery_costs.csv")
        download(kt, "battery_carbon.csv")
        show_console(console)
    except Exception as exc:
        st.error(f"Battery inputs failed: {exc}")

with tab_src:
    st.subheader("Provenance")
    st.caption(
        "Three grades are used throughout: **transcribed** (from a named table or a "
        "public API), **derived** (computed from transcribed values plus this "
        "project's own inventories), **assumed** (a scenario choice with no source — "
        "every one is flagged in its module and printed in its output)."
    )
    for fname, label in [
        ("SOURCES.md", "Source register"),
        ("ASSUMPTIONS.md", "Scope assumptions"),
        ("DATA_GAPS.md", "Data gap register"),
    ]:
        path = REPO_DIR / "optimisation" / fname
        with st.expander(label, expanded=(fname == "SOURCES.md")):
            if path.exists():
                st.markdown(path.read_text(encoding="utf-8"))
            else:
                st.warning(f"{fname} not found.")

# =============================================================================
# 5. Run — build the data, then search
# =============================================================================
st.header("5. Run")
if st.button("Build the data and find the optimal build", type="primary"):
    bar = st.progress(0.0, text="Starting…")

    def _stage(frac: float, text: str):
        bar.progress(frac, text=text)

    # --- Stage A: build the underlying data (0 → 35 %) ----------------------
    try:
        _stage(0.02, "Loading grid intensity and wholesale price series…")
        profiles.load_grid_and_price(str(start), str(end), ely_region)

        _stage(0.10, "Wind profile — checking the Renewables.ninja cache…")
        _, wind_cached = profiles.fetch_wind_cf(lat, lon, str(start), str(end),
                                                turbine=turbine)
        _stage(0.18, "Wind profile "
               + ("was cached." if wind_cached else "fetched from Renewables.ninja.")
               + " Solar profile…")
        _, solar_cached = profiles.fetch_solar_cf(lat, lon, str(start), str(end),
                                                  tilt=tilt)

        _stage(0.24, "Merging wind, solar, grid and price onto one index…")
        # Both fetches are now disk-cached, so this repeats no network work.
        prof, meta = profiles.build(
            lat, lon, str(start), str(end), turbine=turbine, tilt=tilt,
            carbon_api_region=ely_region)

        _stage(0.28, "Embodied carbon — decomposing wind/solar out of ecoinvent…")
        embodied = renewables.apply_case(renewables.decompose_all(), cost_case)

        _stage(0.33, "Reading the electrolyser from Brightway…")
        ely = sizing.load_electrolyser(
            tech, capacity_mw=capacity_mw, strategy=strategy,
            min_load_fraction=min_load,
            clean_grid_threshold_kgco2e_per_kwh=clean_thresh)
    except Exception as exc:
        bar.empty()
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

    # --- Stage B: the search itself (35 → 100 %) ----------------------------
    bounds = sizing.Bounds(
        wind_mw=(0.0, wind_max), solar_mwp=(0.0, solar_max),
        battery_mw=(0.0, bmw_max), battery_hours=(0.0, bh_max))

    budget_evals = max(1, maxiter * popsize * 4)

    def _tick(n):
        frac = 0.35 + 0.64 * min(1.0, n / budget_evals)
        bar.progress(min(0.99, frac), text=f"Searching… {n:,} dispatch evaluations")

    try:
        r = sizing.optimise(prof, ely, threshold_g_per_mj=threshold,
                            cost_case=cost_case, bounds=bounds,
                            maxiter=maxiter, popsize=popsize, progress=_tick,
                            embodied=embodied)
    except Exception as exc:
        bar.empty()
        st.error(f"Optimiser failed: {exc}")
        st.stop()
    bar.progress(1.0, text="Done.")
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
