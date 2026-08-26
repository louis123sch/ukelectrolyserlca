"""Data Centre Optimiser — pick a size, a site and a power option, get the mix.

You fix the demand side (data centre size, site, window, horizon) and which
power options to compare; the optimiser returns the installed mix that runs it
at minimum cost, at minimum emissions, and at the knee point between them.

The science lives in ``optimisation/dc_model.py``, ``dc_pareto.py`` and
``dc_runner.py``. This page collects settings, launches the runner and displays
what comes back — the same relationship the Optimisation Inputs page has with
its modules, so there is never a second implementation to keep in sync.
"""

from __future__ import annotations

import importlib
import json
import subprocess
import sys
import time
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

REPO_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_DIR))

from optimisation import dc_architectures as A
from optimisation import dc_runner, sites

for _mod in (A, dc_runner, sites):
    importlib.reload(_mod)

st.set_page_config(page_title="Data Centre Optimiser", layout="wide")
st.title("Data Centre Optimiser")
st.caption(
    "Give it a size, a site, a time frame and a power option — it finds the "
    "installed mix that runs the data centre at minimum cost, minimum "
    "emissions, or the knee point between the two."
)

RUNS = REPO_DIR / "optimisation_outputs" / "dc_runs"


@st.cache_data(show_spinner=False)
def _tnuos():
    from optimisation import network_charges as nc
    return nc.tnuos_hh_demand()


CAPS = [("cap_wind", "Wind MW"), ("cap_offshore", "Offshore MW"),
        ("cap_solar", "Solar MWp"), ("cap_batt_p", "Battery MW"),
        ("cap_batt_e", "Battery MWh"), ("cap_ely", "Electrolyser MW"),
        ("cap_tank", "H₂ tank kg"), ("cap_fc", "Fuel cell MW"),
        ("cap_grid", "Grid MW")]


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
    lat = st.number_input("Latitude", 49.0, 61.0, key="dc_lat", format="%.4f", step=0.01)
with c3:
    lon = st.number_input("Longitude", -9.0, 2.0, key="dc_lon", format="%.4f", step=0.01)

c1, c2, c3 = st.columns(3)
with c1:
    conn = st.number_input(
        "Grid connection cap (MW)", 0.0, 10_000.0, 0.0, step=1.0,
        help="0 means unconstrained. There is no public register of available "
             "connection capacity, so any number here is yours, not sourced — "
             "and it is the most decision-relevant input in the study.")
with c2:
    tdr = st.selectbox("TNUoS demand residual band",
                       ["HV1", "HV2", "HV3", "HV4", "EHV1", "EHV2", "EHV3", "EHV4"],
                       index=5, help="Set by agreed capacity, not by location.")
with c3:
    st.write("")

try:
    site = sites.resolve(lat, lon, tdr_band=tdr,
                         connection_limit_mw=(conn or None))
except Exception as exc:
    st.error(f"Could not resolve that coordinate: {exc}")
    st.stop()

c1, c2, c3 = st.columns(3)
with c1:
    size_mw = st.number_input("IT load (MW)", 0.1, 1000.0, 7.31, step=1.0,
                              help="7.31 MW is the Zhang et al. foreground's own "
                                   "continuous draw — the study's baseline case.")
    pue = st.number_input("PUE", 1.0, 2.0, 1.00, step=0.05,
                          help="1.00 reproduces the foreground, whose figure is "
                               "already facility-level rather than IT-only.")
with c2:
    start = st.text_input("Window start", "2025-01-01")
    end = st.text_input("Window end", "2025-12-29")
    st.caption("The dispatch window. Real grid and price data exists for 2025 only.")
with c3:
    horizon = st.number_input("Horizon (years)", 1.0, 50.0, 25.0, step=1.0,
                              help="Amortisation only — a different thing from the "
                                   "dispatch window. Both are reported.")
    cost_case = st.radio("Cost case", ["low", "central", "high"], index=1,
                         horizontal=True)

c1, c2 = st.columns(2)
with c1:
    resample = st.selectbox(
        "Resolution", [1.0, 0.5, 2.0], index=0,
        format_func=lambda h: {0.5: "30 min (native)", 1.0: "1 h (recommended)",
                               2.0: "2 h (exploration)"}[h],
        help="1 h is 3.5x faster than half-hourly for 0.14 % on cost and 0.32 % "
             "on carbon. 2 h costs 1.2 % on carbon — comparable to the "
             "differences between options, so use it only to explore.")
with c2:
    unserved = st.number_input("Unserved allowance", 0.0, 0.10, 0.0, step=0.001,
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

have = sites.available_grid_regions()
if site.carbon_api_region in have:
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
        "optimiser refuses. Generate this one first — it scores the GB fuel mix "
        "against ecoinvent for every half-hour, so it takes a while:\n\n"
        f"```bash\npython -c \"from optimisation import sites; "
        f"sites.build_grid_series({site.carbon_api_region})\"\n```"
    )

# =============================================================================
# 2. Which options to compare
# =============================================================================
st.header("2. Which power options?")
matrix = A.core_matrix()
table = A.table()

choice = st.radio("Selection", ["Core matrix (all 21)", "Pick configurations"],
                  horizontal=True)
if choice.startswith("Core"):
    chosen = matrix
else:
    labels = {s.n: f"{s.n:>2}  {s.label} · {s.strategy}" for s in matrix}
    picked = st.multiselect("Configurations", list(labels), default=[1, 2, 3],
                            format_func=lambda n: labels[n])
    chosen = [s for s in matrix if s.n in picked]

points = st.slider("Pareto sweep points", 2, 20, 12,
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
if n_solves > 60:
    st.caption(f"At roughly 10–30 s each on {resample:g} h steps, expect "
               f"{n_solves * 20 / 60 / 8:.0f}–{n_solves * 30 / 60 / 8:.0f} min "
               "across 8 cores. Results are cached by config hash, so re-running "
               "an unchanged scenario is free.")

out_root = RUNS / f"{site.key}_{size_mw:g}MW_{start[:4]}"

c1, c2, c3 = st.columns([1, 1, 4])
with c1:
    launch = st.button("Run", type="primary", disabled=not chosen)
with c2:
    refresh = st.checkbox("Ignore cache", value=False)

if launch:
    cmd = [sys.executable, str(REPO_DIR / "scripts" / "run_dc_scenarios.py"),
           "--lat", str(site.lat), "--lon", str(site.lon),
           "--tdr-band", site.tdr_band,
           "--dc-size", str(size_mw), "--pue", str(pue),
           "--start", start, "--end", end, "--horizon-years", str(horizon),
           "--resample", str(resample), "--points", str(points),
           "--cost-case", cost_case, "--unserved", str(unserved),
           "--out", str(out_root)]
    if site.connection_limit_mw:
        cmd += ["--connection-limit", str(site.connection_limit_mw)]
    if not choice.startswith("Core"):
        cmd += ["--only", *[str(s.n) for s in chosen]]
    if refresh:
        cmd.append("--refresh")
    log = out_root / "run.log"
    out_root.mkdir(parents=True, exist_ok=True)
    # Launched as a detached process so a long matrix never blocks the UI —
    # results are read back off disk below as they land.
    with log.open("w") as fh:
        subprocess.Popen(cmd, stdout=fh, stderr=subprocess.STDOUT, cwd=str(REPO_DIR))
    st.session_state["dc_running"] = str(out_root)
    st.success(f"Launched {n_solves} solves. Results appear below as they land — "
               "rerun the page to refresh.")

# =============================================================================
# 3. Results
# =============================================================================
st.header("3. Results")

if not out_root.exists():
    st.info(f"No results yet for {site.name} at {size_mw:g} MW. Run the matrix above.")
    st.stop()

summaries = dc_runner.load_results(out_root)
if not summaries:
    st.info("Run launched but nothing has finished yet. Rerun the page shortly.")
    log = out_root / "run.log"
    if log.exists():
        st.code(log.read_text()[-2000:], language="text")
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
    point = st.radio("Answer", ["knee", "min_cost", "min_gwp"], horizontal=True,
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
