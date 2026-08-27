"""Data Centre Optimiser — one page: size it, site it, pick the kit, get the sizing.

You fix the demand side (data centre size, site, window, horizon), tick the
infrastructure you want to investigate, say which answer you want, and the
optimiser returns the installed capacity of each ticked asset that delivers it.

Nothing ticked is ever *required*: every asset is an upper bound, so an option
the optimiser sizes to zero is a result — "this would not earn its place" —
rather than a failure.

The coefficients the optimiser runs on are at the bottom of the page rather than
on a separate one, because they are the assumptions behind the answer above them
and reading the two apart is how a wrong number survives.

The science lives in ``optimisation/``: ``dc_model.py`` (the LP), ``dc_pareto.py``
(the cost/carbon frontier), ``dc_runner.py`` (caching), and the coefficient
modules. This page collects settings, calls them and displays what comes back —
there is never a second implementation to keep in sync.
"""

from __future__ import annotations

import contextlib
import importlib
import io
import sys
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

REPO_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_DIR))

import lca_helpers as H
from optimisation import baseline_grid, battery, h2_prices, profiles, renewables, tech_costs
from optimisation import dc_architectures as A
from optimisation import dc_inputs, dc_model, dc_pareto, dc_runner, sites

# Streamlit keeps imported modules in sys.modules across reruns, so edits to
# optimisation/*.py would otherwise need a full app restart to show up. These
# modules are small, pure and free of import-time side effects.
#
# The list must cover the whole dependency closure of anything this page calls,
# leaves first: reloading dc_runner alone leaves it bound to a stale dc_pareto,
# which surfaces as a TypeError about an argument that plainly does exist.
# profiles is a leaf dc_inputs imports lazily inside build_series — easy to
# forget precisely because it never appears at this page's own call sites.
for _mod in (tech_costs, renewables, h2_prices, battery, baseline_grid,
             sites, profiles, dc_model, dc_inputs, dc_pareto, A, dc_runner):
    importlib.reload(_mod)

st.set_page_config(page_title="Data Centre Optimiser", layout="wide")
st.title("Data Centre Optimiser")
st.caption(
    "Size the data centre, place it, tick the infrastructure worth investigating — "
    "and get the installed capacity of each piece that delivers the answer you asked for."
)

RUNS = REPO_DIR / "optimisation_outputs" / "dc_runs"

# label, unit, and how to format the number
CAPS = [("cap_grid", "Grid connection", "MW"),
        ("cap_wind", "Wind", "MW"),
        ("cap_solar", "Solar PV", "MWp"),
        ("cap_batt_p", "Battery power", "MW"),
        ("cap_batt_e", "Battery energy", "MWh"),
        ("cap_ely", "Electrolyser", "MW"),
        ("cap_tank", "Hydrogen storage", "kg"),
        ("cap_fc", "Fuel cell", "MW")]

# which capacity variable each tick-box can switch on
FLAG_CAPS = {"grid": ["cap_grid"], "wind": ["cap_wind"], "solar": ["cap_solar"],
             "battery": ["cap_batt_p", "cap_batt_e"],
             "electrolyser": ["cap_ely"], "tank": ["cap_tank"],
             "fuel_cell": ["cap_fc"], "buy_h2": []}


@st.cache_resource(show_spinner="Connecting to Brightway…")
def _connect():
    H.setup_brightway()
    return True


@st.cache_data(show_spinner=False)
def _tnuos():
    from optimisation import network_charges as nc
    return nc.tnuos_hh_demand()


def _capture(fn, *args, **kwargs):
    """Run a module function, returning (result, its printed output)."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        result = fn(*args, **kwargs)
    return result, buf.getvalue()


def _console(text: str, label: str = "Module output — cross-checks and caveats"):
    if text.strip():
        with st.expander(label):
            st.code(text, language="text")


def _download(df: pd.DataFrame, name: str, label: str | None = None):
    st.download_button(label or f"Download {name}",
                       df.to_csv(index=False).encode("utf-8"),
                       file_name=name, mime="text/csv", key=f"dl_{name}")


try:
    _connect()
except Exception as exc:
    st.error(f"Could not open the Brightway project: {exc}")
    st.stop()


# =============================================================================
# 1. The data centre
# =============================================================================
st.header("1. The data centre")

c1, c2, c3, c4 = st.columns(4)
with c1:
    size_mw = st.number_input("IT load (MW)", 0.1, 1000.0, 7.31, step=1.0,
                              help="7.31 MW is the Zhang et al. foreground's own "
                                   "continuous draw — the study's baseline case.")
with c2:
    pue = st.number_input("PUE", 1.0, 2.0, 1.00, step=0.05,
                          help="1.00 reproduces the foreground, whose figure is "
                               "already facility-level rather than IT-only.")
with c3:
    horizon = st.number_input("Horizon (years)", 1.0, 50.0, 25.0, step=1.0,
                              help="Amortisation only — a different thing from the "
                                   "dispatch window. Both are reported.")
with c4:
    unserved = st.number_input("Unserved allowance", 0.0, 0.10, 0.0, step=0.001,
                               format="%.3f",
                               help="Fraction of annual demand permitted to go "
                                    "unserved. 0 is the data centre standard.")

c1, c2, c3, c4 = st.columns(4)
with c1:
    start = st.text_input("Window start", "2025-01-01")
with c2:
    end = st.text_input("Window end", "2025-12-29")
with c3:
    cost_case = st.radio("Cost case", ["low", "central", "high"], index=1,
                         horizontal=True,
                         help="DESNZ/Arup scenario labels. Drives every cost "
                              "table on this page, including the ones at the bottom.")
with c4:
    resample = st.selectbox(
        "Resolution", [1.0, 0.5, 2.0], index=0,
        format_func=lambda h: {0.5: "30 min (native)", 1.0: "1 h (recommended)",
                               2.0: "2 h (exploration)"}[h],
        help="1 h is 3.5x faster than half-hourly for 0.14 % on cost and 0.32 % "
             "on carbon. 2 h costs 1.2 % on carbon — comparable to the "
             "differences between options, so use it only to explore.")

st.caption(
    f"**{size_mw * pue:,.2f} MW facility draw**, flat. The dispatch window is "
    "the period the optimiser sees; real GB grid and price data exists for 2025 only."
)


# =============================================================================
# 2. Where
# =============================================================================
st.header("2. Where")

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

c1, c2, c3, c4, c5 = st.columns([1.4, 1, 1, 1.1, 1])
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
with c4:
    conn = st.number_input(
        "Connection cap (MW)", 0.0, 10_000.0, 0.0, step=1.0,
        help="0 means unconstrained. There is no public register of available "
             "connection capacity, so any number here is yours, not sourced — "
             "and it is the most decision-relevant input in the study.")
with c5:
    tdr = st.selectbox("TNUoS band",
                       ["HV1", "HV2", "HV3", "HV4", "EHV1", "EHV2", "EHV3", "EHV4"],
                       index=5, help="Set by agreed capacity, not by location.")

try:
    site = sites.resolve(lat, lon, tdr_band=tdr, connection_limit_mw=(conn or None))
except Exception as exc:
    st.error(f"Could not resolve that coordinate: {exc}")
    st.stop()

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
grid_ready = site.carbon_api_region in have
if grid_ready:
    st.success(
        f"Grid data cached for region {site.carbon_api_region} ({site.region_name})."
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
# 3. The infrastructure
# =============================================================================
st.header("3. The infrastructure to investigate")
st.markdown(
    "Tick what the optimiser is **allowed** to build. The grid connection is "
    "always available as a backstop — a data centre cannot go offline — so it "
    "is not a tickbox here. Two dependencies are **enforced**, not left as "
    "warnings: wind or solar requires a battery, and any hydrogen source "
    "requires storage and a fuel cell. Beyond that, nothing is required — an "
    "asset the optimiser sizes to zero is telling you that piece does not earn "
    "its place in this combination, at this site, for this answer."
)

st.session_state.setdefault("kit_strategy", "free")
for _k, _default in (("wind", True), ("solar", True), ("battery", True),
                     ("fuel_cell", False), ("tank", False)):
    st.session_state.setdefault(f"kit_{_k}", _default)

ELY_MAP = {"SOEC": "SOEC operation", "Alk": "AE operation", "PEM": "PEM operation"}
COLOUR_MAP = {"Blue H": "blue", "Green H": "green"}

c1, c2, c3 = st.columns(3)
with c1:
    st.markdown("**Generation**")
    f_wind = st.checkbox("Wind (onshore)", key="kit_wind")
    f_solar = st.checkbox("Solar PV", key="kit_solar")
    any_renewable = f_wind or f_solar
with c2:
    st.markdown("**Storage**")
    if any_renewable:
        st.session_state["kit_battery"] = True
    f_batt = st.checkbox(
        "Battery (Li-ion LFP)", key="kit_battery", disabled=any_renewable,
        help="Required automatically whenever wind or solar is ticked."
        if any_renewable else None)
with c3:
    st.markdown("**Hydrogen**")
    ely_choice = st.pills(
        "Electrolyser technology", list(ELY_MAP), key="kit_ely_choice",
        help="One at a time — the LP prices a single electrolyser technology "
             "per solve. Click a selected pill again to deselect it.")
    buy_choice = st.pills(
        "Buy hydrogen instead", list(COLOUR_MAP), key="kit_buy_choice",
        help="Plant-gate price and burden from the Hydrogen table at the "
             "bottom of this page. One colour at a time, same reason as above.")
    any_hydrogen = bool(ely_choice) or bool(buy_choice)
    if any_hydrogen:
        st.session_state["kit_fuel_cell"] = True
        st.session_state["kit_tank"] = True
    f_fc = st.checkbox(
        "Fuel cell", key="kit_fuel_cell", disabled=any_hydrogen,
        help="Required automatically whenever an electrolyser technology or a "
             "bought colour is ticked." if any_hydrogen else None)
    f_tank = st.checkbox(
        "Hydrogen storage", key="kit_tank", disabled=any_hydrogen,
        help="Required automatically whenever an electrolyser technology or a "
             "bought colour is ticked." if any_hydrogen else None)
    strategy = st.radio(
        "Electrolyser running strategy", list(A.STRATEGIES), key="kit_strategy",
        horizontal=True, disabled=not bool(ely_choice),
        help="baseload holds a capacity-factor floor; flexible runs on surplus "
             "only; free lets the LP decide.")

f_ely, f_buy = bool(ely_choice), bool(buy_choice)
ely_tech, colour = ELY_MAP.get(ely_choice), COLOUR_MAP.get(buy_choice)

flags = {"grid": True, "wind": f_wind, "offshore_wind": False, "solar": f_solar,
         "battery": f_batt, "electrolyser": f_ely, "tank": f_tank,
         "fuel_cell": f_fc, "buy_h2": f_buy}

# --- what this combination can and cannot do --------------------------------
problems, warnings = [], []
if (f_tank or f_fc) and not any_hydrogen:
    warnings.append(
        "**Hydrogen storage and/or fuel cell ticked with no hydrogen source.** "
        "Tick an electrolyser technology or a bought colour, or the optimiser "
        "will size both to zero."
    )

for p in problems:
    st.error(p)
for w in warnings:
    st.warning(w)


# =============================================================================
# 4. Run the optimiser
# =============================================================================
st.header("4. Run the optimiser")
st.markdown(
    "One exact epsilon-constraint sweep gives every answer at once — cheapest, "
    "cleanest and the knee between them — because both cost and carbon are "
    "linear in the same decision variables. Section 5 shows all three side by "
    "side, so there is no objective to pick here."
)

c1, c2 = st.columns([1, 2])
with c1:
    want_target = st.checkbox(
        "Also solve a carbon target",
        help="One extra LP: the cheapest build that hits a stated annual "
             "footprint, shown as a fourth column below.")
    gwp_target = None
    if want_target:
        target_t = st.number_input(
            "Carbon target (t CO₂e per year)", 0.0, 1_000_000.0, 8_000.0, step=100.0,
            help="Total annual footprint — operational plus amortised embodied — "
                 "not an intensity. The grid-only reference for the study's own "
                 "7.31 MW baseline is 16,006 t/yr.")
        gwp_target = float(target_t) * 1000.0
with c2:
    points = st.slider(
        "Frontier points", 3, 20, 12,
        help="Each point is one LP solve. The knee needs a genuine sweep, not "
             "just the two anchors, to be a real knee rather than a coin flip.")

n_solves = int(points) + 1 + (1 if gwp_target is not None else 0)
st.caption(f"**{n_solves} LP solve(s)** at {resample:g} h steps. Results are cached "
           "on a hash of every input above plus the model source, so re-running "
           "an unchanged scenario is free.")

kit_on = [k for k in A.ASSET_FLAGS if flags[k]]
LABELS = {"grid": "grid", "wind": "wind", "solar": "solar", "battery": "battery",
          "electrolyser": f"{ely_choice} electrolyser" if ely_choice else "electrolyser",
          "tank": "H₂ storage", "fuel_cell": "fuel cell",
          "buy_h2": f"bought {colour} H₂"}
label = " + ".join(LABELS[k] for k in kit_on) or "nothing"

scenario = A.Scenario(
    n=0, architecture="custom", label=label, assets=flags,
    ely_tech=ely_tech if f_ely else None,
    h2_colour=colour if f_buy else None,
    strategy=strategy if f_ely else "free",
)

out_root = RUNS / f"{site.key}_{size_mw:g}MW_{start[:4]}_custom"

c1, c2, _ = st.columns([1, 1, 3])
with c1:
    launch = st.button("Optimise", type="primary",
                       disabled=bool(problems) or not grid_ready)
with c2:
    refresh = st.checkbox("Ignore cache", value=False)

if launch:
    status = st.status(f"Solving — {label}", expanded=True)
    log = status.empty()
    done = {"n": 0}

    def _tick(tag):
        done["n"] += 1
        log.write(f"LP {done['n']}/{n_solves} — {tag}")

    try:
        summary = dc_runner.run_one(
            scenario, site=site, start=start, end=end,
            size_mw_it=size_mw, pue=pue,
            resample_hours=(resample or None), points=int(points),
            cost_case=cost_case, horizon_years=horizon,
            unserved_fraction=unserved,
            gwp_target_kg_per_year=gwp_target,
            out_root=out_root, refresh=refresh, progress=_tick)
    except Exception as exc:
        status.update(label=f"Failed: {type(exc).__name__}", state="error")
        st.exception(exc)
        st.stop()

    tag = "read from cache" if summary.get("cached") else f"{summary['solve_seconds']:.0f} s"
    status.update(label=f"Solved — {label} ({tag})", state="complete", expanded=False)
    st.session_state["dc_summary"] = summary
    st.session_state["dc_out_root"] = str(out_root)


# =============================================================================
# 5. The optimum sizing
# =============================================================================
st.header("5. The optimum sizing")
st.markdown(
    "Installed capacity, side by side, for the three points every sweep "
    "produces: the **cheapest** build, the **cleanest** build, and the "
    "**knee** — the point closest to the utopia corner on the normalised "
    "cost/carbon front, which needs no carbon-price assumption."
)

summary = st.session_state.get("dc_summary")
POINTS_SHOWN = [("min_cost", "Lowest cost"), ("min_gwp", "Lowest emissions"),
                ("knee", "Knee — best balance")]

# The result describes the run that produced it, not the current tick-boxes:
# changing a box without pressing Optimise must not relabel an old answer.
ran_on = (summary or {}).get("assets") or {}
ran_kit = [k for k in A.ASSET_FLAGS if ran_on.get(k)]

if not summary:
    st.info("Set the three sections above and press **Optimise**.")
else:
    if summary.get("target_note"):
        (st.error if not summary.get("target") else st.info)(
            f"**Carbon target — {summary['target_note']}.**")
    if summary.get("target"):
        POINTS_SHOWN = POINTS_SHOWN + [("target", "Carbon target")]
    cols = {name: summary[key] for key, name in POINTS_SHOWN if summary.get(key)}

    st.caption(
        f"**{summary['label']}** at {summary['site_name']}, "
        f"{summary['size_mw_it']:g} MW IT · PUE {summary['pue']:g} · "
        f"{summary['start']} to {summary['end']} · {summary['cost_case']} costs."
    )

    @st.cache_data(show_spinner="Running the grid baseline for comparison…")
    def _baseline():
        return _capture(baseline_grid.run)

    try:
        base_summary, base_console = _baseline()
        b = base_summary.iloc[0]
        base_gwp_t = float(b.total_tco2e_yr)
        base_gco2 = float(b.gco2e_per_kwh)
    except Exception:
        base_gwp_t = base_gco2 = None
        base_console = ""

    if summary["degenerate"]:
        st.info(
            "**The cost/carbon frontier collapses to a single point** — the "
            "cheapest build and the cleanest build are the same build, and the "
            "knee coincides with both. Nothing on offer here trades cost "
            "against carbon, which is itself a result."
        )

    # --- the sizing itself, side by side -------------------------------------
    rows = []
    for key, name, unit in CAPS:
        allowed = any(key in FLAG_CAPS[f] for f in ran_kit)
        vals = {colname: float(p.get(key, 0.0)) for colname, p in cols.items()}
        if not allowed and all(v <= 1e-6 for v in vals.values()):
            continue
        rows.append({"Asset": name, "Unit": unit, **vals})
    mix = pd.DataFrame(rows)
    st.dataframe(
        mix, width="stretch", hide_index=True,
        column_config={name: st.column_config.NumberColumn(format="%.2f")
                       for name in cols})

    if summary.get("h2_colour"):
        st.caption(f"Hydrogen is bought as **{summary['h2_colour']}** at the "
                   "plant-gate price in the Hydrogen table below, so there is "
                   "no electrolyser to size.")
    zero_notes = []
    for colname in cols:
        zeroed = [r["Asset"] for r in rows if r.get(colname, 0.0) <= 1e-6]
        if zeroed:
            zero_notes.append(f"**{colname}** — " + ", ".join(zeroed))
    if zero_notes:
        st.info(
            "**Sized to zero:** that is an answer, not a gap — for this site, "
            "this load and that point on the frontier, the optimiser would "
            "rather not build them at all.\n\n" + "  \n".join(zero_notes)
        )

    # --- what each build delivers ---------------------------------------------
    st.subheader("What each build delivers")
    metric_defs = [
        ("Annual cost", "cost_GBP_per_year", lambda v: f"£{v / 1e6:,.2f} m/yr"),
        ("Annual carbon", "gwp_kgco2e_per_year", lambda v: f"{v / 1000:,.0f} t CO₂e/yr"),
        ("Carbon intensity", "gwp_g_per_kWh", lambda v: f"{v:.1f} g/kWh"),
        ("Cost of energy", "cost_GBP_per_MWh", lambda v: f"£{v:,.1f}/MWh"),
        ("Grid import", "import_MWh_per_year", lambda v: f"{v:,.0f} MWh/yr"),
        ("Unserved", "unserved_MWh_per_year", lambda v: f"{v:,.1f} MWh/yr"),
    ]
    metric_rows = [
        {"Metric": mname, **{colname: fmt(p.get(key, 0.0)) for colname, p in cols.items()}}
        for mname, key, fmt in metric_defs
    ]
    st.dataframe(pd.DataFrame(metric_rows), width="stretch", hide_index=True)

    if any(p.get("unserved_MWh_per_year", 0.0) > 1e-3 for p in cols.values()):
        st.warning(
            "**At least one of these builds leaves demand unserved.** That is "
            "within the allowance you set, but it means that combination "
            "cannot actually keep the data centre up on its own kit. Unserved "
            "energy is priced at a deliberately punitive value so infeasible "
            "reliability targets surface as expensive answers rather than "
            "solver failures."
        )
    if base_gwp_t is not None:
        st.caption(
            f"**Demand served:** {summary['demand_MWh_per_year']:,.0f} MWh/yr · "
            f"**solve time:** {summary['solve_seconds']:.0f} s. Grid-only "
            f"reference for this data centre: **{base_gwp_t:,.0f} t CO₂e/yr** at "
            f"{base_gco2:,.0f} g/kWh — every carbon figure above can be read "
            "against it."
        )
        window_days = (pd.Timestamp(summary["end"]) - pd.Timestamp(summary["start"])).days
        if window_days < 350:
            st.warning(
                f"**The window is {window_days} days, and the figures above are "
                "that window scaled to a year.** The grid-only reference is a "
                "full 2025, so the two are not like for like — a winter-only "
                "window annualises a dirtier, windier grid than the year "
                "actually is, and a summer-only window a cleaner one. Use a "
                "partial window to iterate quickly; run the full year before "
                "quoting a delta."
            )
        _console(base_console, "Grid baseline — module output")

    # --- the trade-off curve, with every shown point marked -------------------
    out_root_p = Path(st.session_state["dc_out_root"])
    front_path = out_root_p / summary["key"] / "pareto.parquet"
    if not summary["degenerate"] and front_path.exists():
        front = pd.read_parquet(front_path)
        if len(front) > 2:
            st.subheader("The trade-off these are chosen from")
            f = front.assign(cost_m=front.cost_GBP_per_year / 1e6,
                             gwp_t=front.gwp_kgco2e_per_year / 1000)
            line = alt.Chart(f).mark_line(point=True, color="grey").encode(
                x=alt.X("gwp_t:Q", title="t CO₂e per year"),
                y=alt.Y("cost_m:Q", title="£m per year", scale=alt.Scale(zero=False)),
                tooltip=["point", "cost_m", "gwp_t"])
            markers = pd.DataFrame([
                {"cost_m": p["cost_GBP_per_year"] / 1e6,
                 "gwp_t": p["gwp_kgco2e_per_year"] / 1000, "which": colname}
                for colname, p in cols.items()])
            here = alt.Chart(markers).mark_point(size=220, filled=True).encode(
                x="gwp_t:Q", y="cost_m:Q", color=alt.Color("which:N", title=None),
                tooltip=["which", "cost_m", "gwp_t"])
            st.altair_chart(line + here, width="stretch")
            st.caption(
                "Every point on the grey line is a genuine optimum, not a "
                "sampled guess: both objectives are linear in the same "
                "variables, so the frontier is exact. The coloured markers are "
                "the builds in the tables above."
            )
            show = f[["point", "cost_m", "gwp_t", "gwp_g_per_kWh"] +
                     [k for k, _, _ in CAPS]]
            with st.expander("Every point on the frontier, with its sizing"):
                st.dataframe(show.round(2), width="stretch", hide_index=True)
            _download(front, "frontier.csv")

    if summary.get("carbon_price_GBP_per_tCO2"):
        cp = summary["carbon_price"]
        st.caption(
            f"For reference, at the FES 2025 GB carbon price of "
            f"£{summary['carbon_price_GBP_per_tCO2']:.2f}/tCO₂ — the study's own "
            f"number, not an invented λ — the optimum would be "
            f"£{cp['cost_GBP_per_year'] / 1e6:.2f} m/yr at "
            f"{cp['gwp_kgco2e_per_year'] / 1000:,.0f} t/yr."
        )

    export_rows = [
        {**{k: p.get(k, 0.0) for k, _, _ in CAPS},
         "cost_GBP_per_year": p["cost_GBP_per_year"],
         "gwp_kgco2e_per_year": p["gwp_kgco2e_per_year"],
         "gwp_g_per_kWh": p["gwp_g_per_kWh"],
         "point": colname, "label": summary["label"],
         "site": summary["site_name"], "size_mw_it": summary["size_mw_it"],
         "cost_case": summary["cost_case"]}
        for colname, p in cols.items()
    ]
    _download(pd.DataFrame(export_rows), "optimum_sizing.csv",
              "Download this sizing as CSV")

st.divider()
st.caption(
    "Every result assumes **perfect foresight** — the LP sees the whole window at "
    "once. That is a legitimate way to answer *what should I build?* and an "
    "illegitimate way to answer *what will I achieve?*. Fuel cell and hydrogen "
    "vessel costs are **assumed** with no UK source; the carbon side of the same "
    "architectures is fully sourced. See `optimisation/DATA_GAPS.md`."
)


# =============================================================================
# 6. The numbers behind the answer
# =============================================================================
st.header("6. The numbers behind the answer")
st.caption(
    "Every coefficient the optimiser above just used, on the **"
    f"{cost_case}** cost case you chose in section 1. These are produced by the "
    "modules in `optimisation/`, not recomputed here, so the page never holds a "
    "second copy of the science. Each tab also shows the module's own console "
    "output, which carries its cross-checks and caveats — several of them exist "
    "because they caught real errors."
)

tab_base, tab_gen, tab_h2, tab_batt, tab_src = st.tabs(
    ["Baseline — GB grid", "Generation", "Hydrogen", "Battery", "Sources"])

# --- baseline ---------------------------------------------------------------
with tab_base:
    st.subheader("Baseline 1 — data centre on the GB grid")
    st.caption(
        "The data centre's US-SERC electricity exchanges are swapped for the "
        "half-hourly GB grid mix. Flat 100 % load — which is the foreground's "
        "own figure, not an added assumption."
    )

    @st.cache_data(show_spinner="Running the grid baseline…")
    def _baseline_tab():
        return _capture(baseline_grid.run)

    try:
        bsummary, console = _baseline_tab()
        r = bsummary.iloc[0]
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

        st.dataframe(bsummary.T.rename(columns={0: "value"}), width="stretch")
        _download(bsummary, "baseline1_summary.csv")
        _console(console)
    except Exception as exc:
        st.error(f"Baseline failed: {exc}")

# --- generation -------------------------------------------------------------
with tab_gen:
    st.subheader("Wind and solar — cost and embodied carbon")

    @st.cache_data(show_spinner="Loading generation costs…")
    def _gen_costs():
        return _capture(tech_costs.run)

    # The ecoinvent decomposition is case-independent, so it is cached once and
    # the (cheap) restatement is applied per scenario. Caching the whole thing
    # on `case` instead made every scenario switch re-solve the LCI — ~30 s.
    @st.cache_data(show_spinner="Decomposing embodied carbon from ecoinvent…")
    def _gen_decompose():
        return _capture(renewables.decompose_all)

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
        _download(ann_df, "generation_costs_annualised.csv")
        _console(cost_console, "tech_costs.py output")

        st.divider()
        rows_, carbon_console = _gen_decompose()
        emb = renewables.apply_case(rows_, cost_case)
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
            f"Charging embodied carbon per kWh at ecoinvent's rate overstates it by that "
            f"factor: {w.ecoinvent_per_kWh*1000:.1f} vs "
            f"{w.restated_kgco2e_per_kWh*1000:.1f} g CO₂e/kWh. Notebooks 4.1 and 4.3 do "
            f"exactly that — fine for a fixed plant, wrong once capacity is a decision "
            f"variable. The optimiser above uses the per-MW figures here."
        )
        pv = emb[emb.technology == "solar_pv"].iloc[0]
        st.info(
            f"**PV is a conservative upper bound.** ecoinvent 3.9.1's GB open-ground PV "
            f"is a 2012 multi-Si plant, so it restates to "
            f"~{pv.restated_kgco2e_per_kWh*1000:.0f} g CO₂e/kWh against ~20–40 g/kWh in "
            f"current literature. If the optimiser above sized solar to zero, read that "
            f"as a dataset-vintage artefact before reading it as a finding about solar. "
            f"Wind, being mostly steel and concrete, is far less affected."
        )
        _download(emb.drop(columns=["_parts"]), "renewables_embodied.csv")
    except Exception as exc:
        st.error(f"Generation inputs failed: {exc}")

# --- hydrogen ---------------------------------------------------------------
with tab_h2:
    st.subheader("Hydrogen purchase price by colour")
    st.caption(
        "Bought hydrogen is priced here. Production is co-located with use, so "
        "these are plant-gate prices with no delivery leg."
    )

    @st.cache_data(show_spinner="Fetching NESO hydrogen costs…")
    def _h2():
        return _capture(h2_prices.run)

    try:
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
        _download(rec, "h2_prices_recommended.csv")
        _console(console)
    except Exception as exc:
        st.error(f"Hydrogen prices failed: {exc}")

# --- battery ----------------------------------------------------------------
with tab_batt:
    st.subheader("Battery storage — Li-ion LFP")
    st.caption(
        "Power and energy are costed and scored separately, which is why the "
        "optimiser above sizes MW and MWh independently rather than being locked "
        "to a 4-hour product."
    )
    durations = st.multiselect(
        "Durations to tabulate (hours)", [1, 2, 4, 8, 12], default=[1, 2, 4, 8],
        help="Display only — the optimiser is not restricted to these.") or [1, 2, 4, 8]

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
        st.success(
            f"**~{kt[kt.duration_h == 4].embodied_kgco2e_per_MWh_throughput.iloc[0]:.0f} kg CO₂e "
            "per MWh cycled** for a 4-hour system, against a GB grid mean of 237. A "
            "battery repays its embodied carbon in a small fraction of one cycle's "
            "displaced grid power — so on carbon it is hard to beat, and the real "
            "question is whether the capex earns its place."
        )
        st.warning(
            f"**The battery outlives nothing.** A {battery.ASSET_LIFE_YEARS}-year life "
            f"against the data centre's {horizon:g} means "
            f"**{battery.builds_over_horizon(horizon):.2f} builds** over the horizon, "
            "which both cost and carbon must carry. Fixed OPEX is a flagged proxy — "
            "Modo do not publish it — and the embodied figure excludes container, "
            "racking and HVAC, for which ecoinvent 3.9.1 has no dataset."
        )
        _download(ct, "battery_costs.csv")
        _download(kt, "battery_carbon.csv")
        _console(console)
    except Exception as exc:
        st.error(f"Battery inputs failed: {exc}")

# --- sources ----------------------------------------------------------------
with tab_src:
    st.subheader("Provenance")
    st.caption(
        "Three grades are used throughout: **transcribed** (from a named table or a "
        "public API), **derived** (computed from transcribed values plus this "
        "project's own inventories), **assumed** (a scenario choice with no source — "
        "every one is flagged in its module and printed in its output)."
    )
    for fname, flabel in [
        ("SOURCES.md", "Source register"),
        ("ASSUMPTIONS.md", "Scope assumptions"),
        ("DATA_GAPS.md", "Data gap register"),
    ]:
        path = REPO_DIR / "optimisation" / fname
        with st.expander(flabel, expanded=(fname == "SOURCES.md")):
            if path.exists():
                st.markdown(path.read_text())
            else:
                st.warning(f"{fname} not found.")
