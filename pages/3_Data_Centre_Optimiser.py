"""Data Centre Optimiser — pick a size, a site and a power option, get the mix.

You fix the demand side (data centre size, site, window, horizon) and which
power options to compare; the optimiser returns the installed mix that runs it
at minimum cost, at minimum emissions, and at the knee point between them.

The science lives in ``optimisation/dc_model.py``, ``dc_pareto.py`` and
``dc_runner.py``; the cost and carbon inputs come from ``baseline_grid.py``,
``h2_prices.py``, ``tech_costs.py``, ``renewables.py`` and ``battery.py`` and
are shown in the *Inputs* section below, so there is never a second
implementation of the science to keep in sync. Pressing *Run* first builds
whatever input data the run needs (hydrogen prices, Renewables.ninja profiles,
network charges), then launches the solves — one progress bar covers both.
"""

from __future__ import annotations

import importlib
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import ui_defaults as D
from optimisation import dc_architectures as A
from optimisation import dc_runner
from optimisation import network_charges as nc
from optimisation import sites
from ui_common import REPO_DIR, capture, download, show_console

for _mod in (A, dc_runner, sites, nc, D):
    importlib.reload(_mod)

st.set_page_config(page_title="Data Centre Optimiser", layout="wide")
st.title("Data Centre Optimiser")
st.caption(
    "Give it a size, a site, a time frame and a power option — it finds the "
    "installed mix that runs the data centre at minimum cost, minimum "
    "emissions, or the knee point between the two."
)

RUNS = REPO_DIR / "optimisation_outputs" / "dc_runs"
OUT_DIR = REPO_DIR / "optimisation_outputs"


@st.cache_data(show_spinner=False)
def _tnuos():
    return nc.tnuos_hh_demand()


CAPS = D.DC_CAP_COLUMNS


# =============================================================================
# 1. The data centre
# =============================================================================
st.header("1. What are you powering, where, and when?")

st.markdown(
    "**A GB coordinate is the input.** The Carbon Intensity region and the TNUoS "
    "demand zone are derived from it, so the weather, the grid mix and the "
    "network bill always move together — picking a location cannot change one "
    "without the others."
)


def _apply_preset():
    key = st.session_state.get("dc_preset")
    if key and key in sites.PRESETS:
        lat, lon, _name = sites.PRESETS[key]
        st.session_state["dc_lat"], st.session_state["dc_lon"] = lat, lon


st.session_state.setdefault("dc_lat", sites.PRESETS[sites.DEFAULT_PRESET][0])
st.session_state.setdefault("dc_lon", sites.PRESETS[sites.DEFAULT_PRESET][1])

c1, c2, c3 = st.columns([1.2, 1, 1])
with c1:
    st.selectbox("Jump to a preset", [""] + list(sites.PRESETS), key="dc_preset",
                 on_change=_apply_preset,
                 format_func=lambda k: "—" if k == "" else
                 f"{k} · {sites.PRESETS[k][2]}",
                 help="A shortcut that fills the coordinates. Any GB coordinate works.")
with c2:
    lat = st.number_input("Latitude", D.DC_LAT_MIN, D.DC_LAT_MAX, key="dc_lat",
                          format="%.4f", step=D.DC_COORD_STEP)
with c3:
    lon = st.number_input("Longitude", D.DC_LON_MIN, D.DC_LON_MAX, key="dc_lon",
                          format="%.4f", step=D.DC_COORD_STEP)

c1, c2, c3 = st.columns(3)
with c1:
    conn = st.number_input(
        "Grid connection cap (MW)", D.DC_CONNECTION_MW_MIN, D.DC_CONNECTION_MW_MAX,
        D.DC_CONNECTION_MW, step=D.DC_CONNECTION_MW_STEP,
        help="0 means unconstrained. There is no public register of available "
             "connection capacity, so any number here is yours, not sourced — "
             "and it is the most decision-relevant input in the study.")
with c2:
    override_tdr = st.checkbox(
        "Override TNUoS band", value=D.DC_TDR_OVERRIDE,
        help="By default the demand residual band is derived from the agreed "
             "capacity — the connection cap if you set one, otherwise peak "
             "facility demand. Tick only to force a band you know applies.")
    tdr = st.selectbox("TNUoS demand residual band", D.DC_TDR_BANDS,
                       index=D.DC_TDR_BAND_INDEX, disabled=not override_tdr,
                       help="Set by agreed capacity and connection voltage, "
                            "never by location.") if override_tdr else None
with c3:
    st.write("")

c1, c2, c3 = st.columns(3)
with c1:
    size_mw = st.number_input("IT load (MW)", D.DC_IT_LOAD_MW_MIN, D.DC_IT_LOAD_MW_MAX,
                              D.DC_IT_LOAD_MW, step=D.DC_IT_LOAD_MW_STEP,
                              help="7.31 MW is the Zhang et al. foreground's own "
                                   "continuous draw — the study's baseline case.")
    pue = st.number_input("PUE", D.DC_PUE_MIN, D.DC_PUE_MAX, D.DC_PUE, step=D.DC_PUE_STEP,
                          help="1.00 reproduces the foreground, whose figure is "
                               "already facility-level rather than IT-only.")
with c2:
    start = st.text_input("Window start", D.DC_WINDOW_START)
    end = st.text_input("Window end", D.DC_WINDOW_END)
    st.caption("The dispatch window. Real grid and price data exists for 2025 only.")
with c3:
    horizon = st.number_input("Horizon (years)", D.DC_HORIZON_YEARS_MIN, D.DC_HORIZON_YEARS_MAX,
                              D.DC_HORIZON_YEARS, step=D.DC_HORIZON_YEARS_STEP,
                              help="Amortisation only — a different thing from the "
                                   "dispatch window. Both are reported.")
    cost_case = st.radio("Cost case", D.COST_CASES, index=D.COST_CASE_INDEX,
                         horizontal=True)

try:
    site = sites.resolve(lat, lon, tdr_band=tdr,
                         connection_limit_mw=(conn or None),
                         agreed_capacity_mw=size_mw * pue)
except Exception as exc:
    st.error(f"Could not resolve that coordinate: {exc}")
    st.stop()

c1, c2 = st.columns(2)
with c1:
    resample = st.selectbox(
        "Resolution", D.DC_RESAMPLE_OPTIONS, index=D.DC_RESAMPLE_INDEX,
        format_func=lambda h: D.DC_RESAMPLE_LABELS[h],
        help="1 h is 3.5x faster than half-hourly for 0.14 % on cost and 0.32 % "
             "on carbon. 2 h costs 1.2 % on carbon — comparable to the "
             "differences between options, so use it only to explore.")
with c2:
    unserved = st.number_input("Unserved allowance", D.DC_UNSERVED_MIN, D.DC_UNSERVED_MAX,
                               D.DC_UNSERVED, step=D.DC_UNSERVED_STEP,
                               format="%.3f",
                               help="Fraction of annual demand permitted to go "
                                    "unserved. 0 is the data centre standard.")

# --- what the coordinate resolved to -----------------------------------------
try:
    _hh, _ = _tnuos()
    tariff = float(_hh.set_index("zone_no").tariff_GBP_per_kW.get(site.tnuos_zone,
                                                                 float("nan")))
except Exception:
    tariff = float("nan")

m1, m2, m3, m4 = st.columns(4)
m1.metric("Resolved to", site.name)
m2.metric("Carbon Intensity region", f"{site.carbon_api_region} · {site.region_name}")
m3.metric("TNUoS zone", f"{site.tnuos_zone}")
m4.metric("TNUoS demand tariff", f"£{tariff:.2f}/kW" if tariff == tariff else "—")

# The band is the single largest free parameter on this page, so state what it
# resolved to and what it costs rather than leaving it implicit.
try:
    _tdr_tbl, _ = nc.tnuos_tdr()
    _row = _tdr_tbl[_tdr_tbl.band == site.tdr_band]
    _per_year = float(_row.iloc[0].GBP_per_site_year) if not _row.empty else float("nan")
    _agreed = conn or (size_mw * pue)
    _per_mwh = _per_year / (size_mw * pue * 8760)
    b1, b2, b3 = st.columns(3)
    b1.metric("Agreed capacity", f"{_agreed:,.2f} MW",
              help="The connection cap where you set one, otherwise peak facility demand.")
    b2.metric("TNUoS demand residual band", site.tdr_band,
              help="Overridden." if override_tdr else "Derived from the agreed capacity.")
    b3.metric("Demand residual", f"£{_per_year:,.0f}/yr",
              delta=f"£{_per_mwh:.2f}/MWh", delta_color="off")
    if nc.TDR_BANDS_ARE_ASSUMED and not override_tdr:
        st.warning(
            "The demand residual **tariffs** are NESO-sourced, but the **capacity "
            "boundaries** that pick the band are assumed — under the TCR each DNO "
            "sets its own in DCUSA, and they are not in the NESO feed. Band choice "
            "spans £0.12–£22.13/MWh, so replace "
            "`network_charges.TDR_BAND_MAX_MVA` with your DNO's published table "
            "before quoting an absolute cost.",
            icon="⚠️",
        )
except Exception as exc:
    st.caption(f"Could not price the TDR band: {exc}")

have = sites.available_grid_regions()
grid_ready = site.carbon_api_region in have
if grid_ready:
    st.success(
        f"Grid data cached for region {site.carbon_api_region} "
        f"({site.region_name}). "
        + ("Offshore wind available." if site.offshore_wind else "No offshore option.")
    )
else:
    cached = ", ".join(f"{r} ({sites.CARBON_API_REGIONS[r]})" for r in sorted(have)) or "none"
    st.error(
        f"**No cached grid series for region {site.carbon_api_region} "
        f"({site.region_name}).** Cached: {cached}.\n\n"
        "Using another region's half-hourly intensities here would produce a "
        "confident wrong answer about whether renewables beat the grid, so the "
        "optimiser refuses. This series scores the GB fuel mix against ecoinvent "
        "for every half-hour, so building it takes tens of minutes."
    )
    if st.button(f"Build the grid series for region {site.carbon_api_region} now"):
        with st.status(
                f"Building grid series for region {site.carbon_api_region} — "
                "this runs the Carbon Intensity notebook and can take 30+ "
                "minutes. Leave this page open.", expanded=True) as s:
            try:
                sites.build_grid_series(site.carbon_api_region)
                s.update(label="Grid series built.", state="complete")
                st.rerun()
            except Exception as exc:
                # The message carries the tail of the notebook log, which is
                # the only place the real cause shows up — so it goes in the
                # body, not squeezed into the one-line status label.
                s.update(label="Build failed.", state="error")
                st.code(str(exc), language="text")
    st.stop()

# =============================================================================
# 2. Which options to compare
# =============================================================================
st.header("2. Which power options?")
matrix = A.core_matrix()
table = A.table()

choice = st.radio("Selection", D.DC_SELECTION_MODES, horizontal=True)
if choice == D.DC_SELECTION_CORE:
    chosen = matrix
else:
    labels = {s.n: f"{s.n:>2}  {s.label} · {s.strategy}" for s in matrix}
    picked = st.multiselect("Configurations", list(labels), default=D.DC_CONFIGS,
                            format_func=lambda n: labels[n])
    chosen = [s for s in matrix if s.n in picked]

points = st.slider("Pareto sweep points", D.DC_PARETO_POINTS_MIN, D.DC_PARETO_POINTS_MAX,
                   D.DC_PARETO_POINTS,
                   help="Each point is one LP solve. min cost, min GWP and the "
                        "knee all come out of a single sweep.")

with st.expander("What each configuration may build"):
    show = table.copy()
    for col in ("grid", "wind_solar", "battery", "electrolyser", "tank",
                "fuel_cell", "bought_h2"):
        show[col] = show[col].map({True: "✓", False: "·"})
    st.dataframe(show[["n", "label", "strategy", "grid", "wind_solar", "battery",
                       "electrolyser", "tank", "fuel_cell", "bought_h2", "note"]],
                 width="stretch", hide_index=True)

n_solves = len(chosen) * (points + 1)
st.write(f"**{len(chosen)} configuration(s) × {points + 1} solves = {n_solves} LPs.**")
if n_solves > D.DC_SOLVE_WARN_THRESHOLD:
    _lo = n_solves * D.DC_SECONDS_PER_SOLVE_LOW / 60 / D.DC_CORES
    _hi = n_solves * D.DC_SECONDS_PER_SOLVE_HIGH / 60 / D.DC_CORES
    st.caption(f"At roughly {D.DC_SECONDS_PER_SOLVE_LOW}–{D.DC_SECONDS_PER_SOLVE_HIGH} s "
               f"each on {resample:g} h steps, expect {_lo:.0f}–{_hi:.0f} min "
               f"across {D.DC_CORES} cores. Results are cached by config hash, so "
               "re-running an unchanged scenario is free.")

# =============================================================================
# 3. Inputs — the coefficients the optimiser will use
# =============================================================================
st.header("3. Inputs")
st.caption(
    "Every table below is produced by a module in `optimisation/` — this page "
    "only calls them and displays what they return. The same modules feed the "
    "run button, so what you see is what the optimiser uses. The cost case is "
    f"the one chosen above (**{cost_case}**)."
)

tab_base, tab_h2p, tab_gen, tab_batt, tab_src = st.tabs(
    ["Baseline — GB grid", "Hydrogen", "Generation", "Battery", "Sources"])

with tab_base:
    st.subheader("Baseline 1 — data centre on the GB grid")
    st.caption(
        "The data centre's US-SERC electricity exchanges are swapped for the "
        "half-hourly GB grid mix. Flat 100 % load — which is the foreground's "
        "own figure, not an added assumption. Needs Brightway, so it is "
        "computed on demand."
    )

    @st.cache_data(show_spinner="Running the grid baseline (Brightway)…")
    def _baseline():
        import lca_helpers as H
        H.setup_brightway()
        import bw2data as bd
        from dashboard_config import DC_FOREGROUND_DB
        if DC_FOREGROUND_DB not in bd.databases:
            raise RuntimeError(
                f"The Brightway project has no {DC_FOREGROUND_DB!r} database — "
                "the data centre foreground has not been built on this machine. "
                "Run 2.tech_lca_foreground.ipynb once (in the brightway "
                "environment) to create it, then come back."
            )
        from optimisation import baseline_grid
        return capture(baseline_grid.run)

    if st.button("Compute the grid baseline") or "dc_baseline_done" in st.session_state:
        try:
            summary, console = _baseline()
            st.session_state["dc_baseline_done"] = True
            r = summary.iloc[0]
            c = st.columns(4)
            c[0].metric("Total emissions", f"{r.total_tco2e_yr:,.0f} t CO₂e/y")
            c[1].metric("Carbon intensity", f"{r.gco2e_per_kwh:,.0f} g/kWh")
            c[2].metric("Electricity cost", f"£{r.electricity_cost_MGBP_yr:,.2f} M/y")
            c[3].metric("Demand", f"{r.dc_electricity_GWh_yr:,.1f} GWh/y")

            c2 = st.columns(3)
            c2[0].metric("Operational", f"{r.operational_tco2e_yr:,.0f} t/y")
            c2[1].metric("Embodied (amortised)", f"{r.embodied_tco2e_yr:,.0f} t/y",
                         help="A fixed floor every other option also carries.")
            c2[2].metric("vs as-authored US-SERC",
                         f"{100*(r.total_tco2e_yr/r.reference_us_serc_tco2e_yr-1):,.0f} %")

            st.dataframe(summary.T.rename(columns={0: "value"}), width="stretch")
            download(summary, "baseline1_summary.csv")
            show_console(console)
        except Exception as exc:
            st.error(f"Baseline failed: {exc or type(exc).__name__}")

with tab_h2p:
    st.subheader("Hydrogen purchase price by colour")
    st.caption(
        "Hydrogen is bought, not self-produced. Production is co-located with use, "
        "so these are plant-gate prices with no delivery leg. "
        "`h2_prices_recommended.csv` is a hard input of the bought-hydrogen "
        "configurations — the run button rebuilds it if it is missing."
    )

    @st.cache_data(show_spinner="Fetching NESO hydrogen costs…")
    def _h2():
        from optimisation import h2_prices
        return capture(h2_prices.run)

    try:
        from optimisation import h2_prices
        _detail, console = _h2()
        rec = h2_prices.recommended_table()
        st.dataframe(
            rec[["colour", "variant", "low", "central", "high",
                 "central_source", "corroboration"]],
            width="stretch", hide_index=True,
            column_config={c: st.column_config.NumberColumn(f"{c} £/kg", format="%.2f")
                           for c in ("low", "central", "high")},
        )
        st.info(
            "**Green splits in two, and the gap is UK network charges.** A behind-the-"
            "meter electrolyser on on-site wind pays £4.93/kg; one importing from the "
            "grid pays £8.33/kg, of which €2.77/kg is grid fees and taxes — 29 % of the "
            "total. Which one applies depends on how the option is wired."
        )
        st.warning(
            "**Turquoise is constructed, not sourced.** It is an 86 % grey / 14 % green "
            "blend weighted by the MP-E inventory's own gas:electricity energy split, "
            "and carries no first-of-a-kind premium in the central case — so it is a "
            "floor, not a forecast."
        )
        download(rec, "h2_prices_recommended.csv")
        show_console(console)
    except Exception as exc:
        st.error(f"Hydrogen prices failed: {exc}")

with tab_gen:
    st.subheader("Wind, offshore and solar — cost and embodied carbon")

    @st.cache_data(show_spinner="Loading generation costs…")
    def _gen_costs():
        from optimisation import tech_costs
        return capture(tech_costs.run)

    @st.cache_data(show_spinner="Decomposing embodied carbon from ecoinvent…")
    def _gen_decompose():
        from optimisation import renewables
        return capture(renewables.decompose_all)

    try:
        from optimisation import renewables
        (long_df, ann_df), cost_console = _gen_costs()
        st.markdown("**Costs** — DESNZ/Arup 2024, real 2023 prices")
        view = ann_df[ann_df.case == cost_case][[
            "asset", "capex_GBP_per_MW", "opex_GBP_per_MW_year", "net_load_factor",
            "lifetime_years", "discount_rate", "lcoe_GBP_per_MWh",
            "reported_lcoe_GBP_per_MWh", "lcoe_delta_pct"]]
        st.dataframe(view, width="stretch", hide_index=True)
        download(ann_df, "generation_costs_annualised.csv")
        show_console(cost_console, "tech_costs.py output")

        rows, carbon_console = _gen_decompose()
        emb = renewables.apply_case(rows, cost_case)
        st.markdown("**Embodied carbon** — per MW installed, decomposed out of ecoinvent")
        st.dataframe(
            emb[["technology", "capital_kgco2e_per_MW", "study_load_factor",
                 "study_lifetime_years", "restated_kgco2e_per_kWh",
                 "ecoinvent_per_kWh", "ratio_to_ecoinvent"]],
            width="stretch", hide_index=True,
        )
        download(emb.drop(columns=["_parts"]), "renewables_embodied.csv")
        show_console(carbon_console, "renewables.py output")
    except Exception as exc:
        st.error(f"Generation inputs failed: {exc}")

with tab_batt:
    st.subheader("Battery storage — Li-ion LFP")
    durations = st.multiselect(
        "Durations to tabulate (hours)", [1, 2, 4, 8, 12], default=[1, 2, 4, 8],
        help="Power and energy are costed and scored separately, so the "
             "optimiser can choose duration rather than being locked to a "
             "4-hour product.",
    ) or [1, 2, 4, 8]

    @st.cache_data(show_spinner="Loading battery inputs…")
    def _batt(durs: tuple):
        from optimisation import battery
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            battery.run()
        return battery.cost_table(durs), battery.carbon_table(durs), buf.getvalue()

    try:
        from optimisation import battery
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
        st.warning(
            f"**The battery outlives nothing.** A {battery.ASSET_LIFE_YEARS}-year life "
            f"against the data centre's 25 means "
            f"**{battery.builds_over_horizon(25):.2f} builds** over the horizon, which "
            "both cost and carbon must carry. Fixed OPEX is a flagged proxy — Modo do "
            "not publish it — and the embodied figure excludes container, racking and "
            "HVAC, for which ecoinvent 3.9.1 has no dataset."
        )
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
# 4. Run — build the data, then solve
# =============================================================================
st.header("4. Run")

out_root = RUNS / f"{site.key}_{size_mw:g}MW_{start[:4]}"

c1, c2, c3 = st.columns([1, 1, 4])
with c1:
    launch = st.button("Build the data and run", type="primary", disabled=not chosen)
with c2:
    refresh = st.checkbox("Ignore cache", value=D.DC_IGNORE_CACHE)

if launch:
    bar = st.progress(0.0, text="Starting…")

    # --- Stage 1: build the underlying data (0 → 15 %) -----------------------
    try:
        needs_h2 = any(s.h2_colour is not None for s in chosen)
        h2_csv = OUT_DIR / "h2_prices_recommended.csv"
        if needs_h2 and not h2_csv.exists():
            bar.progress(0.02, text="Building hydrogen prices from NESO…")
            from optimisation import h2_prices
            capture(h2_prices.run)

        bar.progress(0.05, text="Network charges — TNUoS/BSUoS caches…")
        _tnuos()

        bar.progress(0.08, text="Wind profile — checking the Renewables.ninja cache…")
        from optimisation import profiles
        _, wind_cached = profiles.fetch_wind_cf(site.lat, site.lon, start, end)
        bar.progress(0.12, text="Wind profile "
                     + ("was cached." if wind_cached else "fetched.")
                     + " Solar profile…")
        profiles.fetch_solar_cf(site.lat, site.lon, start, end)
    except Exception as exc:
        bar.empty()
        st.error(f"Data build failed: {exc}")
        st.stop()

    # --- Stage 2: launch the solves (15 → 100 %) -----------------------------
    # -u because stdout is a file, not a tty: without it Python block-buffers
    # and the [n/total] progress lines only land when the run is already over.
    cmd = [sys.executable, "-u",
           str(REPO_DIR / "scripts" / "run_dc_scenarios.py"),
           "--lat", str(site.lat), "--lon", str(site.lon),
           "--tdr-band", site.tdr_band,
           "--dc-size", str(size_mw), "--pue", str(pue),
           "--start", start, "--end", end, "--horizon-years", str(horizon),
           "--resample", str(resample), "--points", str(points),
           "--cost-case", cost_case, "--unserved", str(unserved),
           "--out", str(out_root)]
    if site.connection_limit_mw:
        cmd += ["--connection-limit", str(site.connection_limit_mw)]
    if choice != D.DC_SELECTION_CORE:
        cmd += ["--only", *[str(s.n) for s in chosen]]
    if refresh:
        cmd.append("--refresh")
    log = out_root / "run.log"
    out_root.mkdir(parents=True, exist_ok=True)
    # Launched as a detached process so a long matrix survives page reruns —
    # the loop below watches the log for progress, and results are read back
    # off disk as they land even if you navigate away.
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    if os.name == "nt":
        # See lca_helpers: MKL 2025 OpenMP layer is broken on Windows.
        env.setdefault("MKL_THREADING_LAYER", "TBB")
    with log.open("w", encoding="utf-8") as fh:
        proc = subprocess.Popen(cmd, stdout=fh, stderr=subprocess.STDOUT,
                                cwd=str(REPO_DIR), env=env)
    st.session_state["dc_running"] = str(out_root)

    bar.progress(0.15, text=f"Launched {n_solves} solves across "
                            f"{len(chosen)} configuration(s)…")
    tail = st.empty()
    n_total = len(chosen)
    done_re = re.compile(r"^\[(\d+)/(\d+)\]")
    while True:
        finished = proc.poll() is not None
        text = ""
        if log.exists():
            text = log.read_text(encoding="utf-8", errors="replace")
        done = 0
        for line in text.splitlines():
            m = done_re.match(line.strip())
            if m:
                done = max(done, int(m.group(1)))
        frac = 0.15 + 0.85 * min(1.0, done / max(1, n_total))
        bar.progress(min(0.99 if not finished else 1.0, frac),
                     text=f"Solving… {done}/{n_total} configuration(s) done")
        tail.code(text[-1500:] or "Waiting for the first solve…", language="text")
        if finished:
            break
        time.sleep(2)
    bar.progress(1.0, text="Run complete.")
    time.sleep(0.5)
    bar.empty()
    tail.empty()
    if proc.returncode != 0:
        st.error(f"The run exited with code {proc.returncode} — see the log below.")
        st.code((log.read_text(encoding="utf-8", errors="replace"))[-3000:],
                language="text")
    else:
        st.success("All solves finished. Results below.")

# =============================================================================
# 5. Results
# =============================================================================
st.header("5. Results")

if not out_root.exists():
    st.info(f"No results yet for {site.name} at {size_mw:g} MW. Run the matrix above.")
    st.stop()

summaries = dc_runner.load_results(out_root)
if not summaries:
    st.info("Run launched but nothing has finished yet. Rerun the page shortly.")
    log = out_root / "run.log"
    if log.exists():
        st.code(log.read_text(encoding="utf-8", errors="replace")[-2000:],
                language="text")
    st.stop()

df = dc_runner.comparison_table(summaries)
st.caption(f"{len(summaries)} configuration(s) from `{out_root.relative_to(REPO_DIR)}`")

baseline = df[(df.architecture == "grid_only") & (df.point == "min_cost")]
base_cost = float(baseline.cost_m_GBP_per_year.iloc[0]) if len(baseline) else None
base_gwp = float(baseline.gwp_t_per_year.iloc[0]) if len(baseline) else None

tab_cmp, tab_one, tab_h2 = st.tabs(
    ["Compare all", "One configuration", "What does hydrogen buy you?"])

# --- compare ---------------------------------------------------------------
with tab_cmp:
    point = st.radio("Answer", D.ANSWER_POINTS, horizontal=True,
                     help="All three come from one Pareto sweep. The knee is the "
                          "point closest to the utopia corner on the normalised "
                          "front — no carbon price assumed.")
    sub = df[df.point == point].sort_values("gwp_t_per_year")

    chart = alt.Chart(sub).mark_circle(size=140).encode(
        x=alt.X("gwp_t_per_year:Q", title="t CO₂e per year"),
        y=alt.Y("cost_m_GBP_per_year:Q", title="£m per year"),
        color=alt.Color("architecture:N", title="Architecture"),
        tooltip=["n", "label", "strategy", "cost_m_GBP_per_year",
                 "gwp_t_per_year", "gwp_g_per_kWh"],
    ).interactive()
    if base_cost is not None:
        rule_x = alt.Chart(pd.DataFrame({"x": [base_gwp]})).mark_rule(
            strokeDash=[4, 4], color="grey").encode(x="x:Q")
        rule_y = alt.Chart(pd.DataFrame({"y": [base_cost]})).mark_rule(
            strokeDash=[4, 4], color="grey").encode(y="y:Q")
        chart = chart + rule_x + rule_y
    st.altair_chart(chart, width="stretch")
    if base_cost is not None:
        st.caption("Dashed lines are the grid-only baseline. Down and left is better "
                   "on both axes.")

    cols = ["n", "label", "strategy", "cost_m_GBP_per_year", "gwp_t_per_year",
            "gwp_g_per_kWh", "degenerate"] + [c for c, _ in CAPS]
    st.dataframe(sub[cols].round(2), width="stretch", hide_index=True)
    st.download_button("Download comparison.csv",
                       df.to_csv(index=False).encode(),
                       file_name="comparison.csv", mime="text/csv")

# --- one configuration ------------------------------------------------------
with tab_one:
    keys = {s["key"]: f"{s['n']:>2}  {s['label']} · {s['strategy']}" for s in summaries}
    key = st.selectbox("Configuration", list(keys), format_func=lambda k: keys[k])
    s = next(x for x in summaries if x["key"] == key)

    if s["degenerate"]:
        st.warning(
            "**The front collapses to a single point** — minimum cost and minimum "
            "emissions pick the same system. That is a result, not a failure: "
            "nothing on offer trades cost against carbon here. For grid + hydrogen "
            "it means the optimiser declined to build a hydrogen chain at all."
        )

    m1, m2, m3, m4 = st.columns(4)
    knee = s["knee"]
    m1.metric("Knee cost", f"£{knee['cost_GBP_per_year'] / 1e6:.2f} m/yr",
              None if base_cost is None else
              f"{knee['cost_GBP_per_year'] / 1e6 - base_cost:+.2f} vs grid only")
    m2.metric("Knee carbon", f"{knee['gwp_kgco2e_per_year'] / 1000:,.0f} t/yr",
              None if base_gwp is None else
              f"{knee['gwp_kgco2e_per_year'] / 1000 - base_gwp:+,.0f} vs grid only",
              delta_color="inverse")
    m3.metric("Intensity", f"{knee['gwp_g_per_kWh']:.1f} g/kWh")
    m4.metric("Solve time", f"{s['solve_seconds']:.0f} s")

    front = pd.read_parquet(out_root / key / "pareto.parquet")
    if not s["degenerate"]:
        marks = pd.DataFrame([
            {"which": w, "cost_m": s[w]["cost_GBP_per_year"] / 1e6,
             "gwp_t": s[w]["gwp_kgco2e_per_year"] / 1000}
            for w in ("min_cost", "min_gwp", "knee", "carbon_price")])
        line = alt.Chart(front.assign(
            cost_m=front.cost_GBP_per_year / 1e6,
            gwp_t=front.gwp_kgco2e_per_year / 1000)).mark_line(point=True).encode(
            x=alt.X("gwp_t:Q", title="t CO₂e per year"),
            y=alt.Y("cost_m:Q", title="£m per year", scale=alt.Scale(zero=False)),
            tooltip=["point", "cost_m", "gwp_t"])
        pts = alt.Chart(marks).mark_point(size=220, filled=True).encode(
            x="gwp_t:Q", y="cost_m:Q", color=alt.Color("which:N", title=""),
            tooltip=["which", "cost_m", "gwp_t"])
        st.altair_chart(line + pts, width="stretch")
        st.caption(
            f"Carbon-price point uses the FES 2025 GB figure, "
            f"£{s.get('carbon_price_GBP_per_tCO2', float('nan')):.2f}/tCO₂ — "
            "the study's own number, not an invented λ.")

    st.subheader("Installed mix")
    mix = pd.DataFrame([
        {"asset": label, "min cost": s["min_cost"][k], "knee": s["knee"][k],
         "min GWP": s["min_gwp"][k]}
        for k, label in CAPS])
    mix = mix[(mix[["min cost", "knee", "min GWP"]].abs() > 1e-6).any(axis=1)]
    st.dataframe(mix.round(2), width="stretch", hide_index=True)
    if s["note"]:
        st.caption(f"Note: {s['note']}")

# --- what does hydrogen buy you --------------------------------------------
with tab_h2:
    st.markdown(
        "Δ against the two references: **grid only** (the 16,006 t/yr baseline) "
        "and **grid + battery**, which does the same job as hydrogen — shifting "
        "grid electricity from clean half-hours to dirty ones — at 88 % "
        "round-trip instead of 29 %."
    )
    ref_batt = df[(df.architecture == "grid_battery") & (df.point == "knee")]
    h2 = df[(df.point == "knee")
            & (df.architecture.str.contains("h2"))].sort_values("gwp_t_per_year")
    if h2.empty or base_cost is None:
        st.info("Run the hydrogen configurations and grid_only to populate this.")
    else:
        out = h2[["n", "label", "strategy", "cost_m_GBP_per_year", "gwp_t_per_year"]].copy()
        out["Δcost vs grid only"] = out.cost_m_GBP_per_year - base_cost
        out["Δcarbon vs grid only"] = out.gwp_t_per_year - base_gwp
        if len(ref_batt):
            out["Δcost vs battery"] = out.cost_m_GBP_per_year - float(
                ref_batt.cost_m_GBP_per_year.iloc[0])
            out["Δcarbon vs battery"] = out.gwp_t_per_year - float(
                ref_batt.gwp_t_per_year.iloc[0])
        st.dataframe(out.round(2), width="stretch", hide_index=True)

    st.caption(
        "A hydrogen row that matches grid-only exactly means the optimiser "
        "declined to build the chain. Round-tripping grid electricity through "
        "hydrogen costs 3.41 kWh in per kWh out, and GB's p90/p10 carbon spread "
        "is only 3.12 — so grid-charged hydrogen arbitrage loses carbon on "
        "average. Hydrogen's case rests on duration and on islanded operation, "
        "not on day-to-day shifting."
    )

st.divider()
st.caption(
    "Every result assumes **perfect foresight** — the LP sees the whole window at "
    "once. That is a legitimate way to answer *what should I build?* and an "
    "illegitimate way to answer *what will I achieve?*. Fuel cell and hydrogen "
    "vessel costs are **assumed** with no UK source; the carbon side of the same "
    "architectures is fully sourced. See `optimisation/DATA_GAPS.md`."
)
