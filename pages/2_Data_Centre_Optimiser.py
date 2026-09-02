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
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

REPO_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_DIR))

import lca_helpers as H
from optimisation import baseline_grid, battery, gb_map, h2_prices, profiles, renewables, tech_costs
from optimisation import dc_architectures as A
from optimisation import dc_inputs, dc_job, dc_model, dc_pareto, dc_runner, sites
from optimisation import thresholds as TH

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
             gb_map, sites, profiles, dc_model, dc_inputs, dc_pareto, A, dc_runner,
             TH, dc_job):
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

# Capacities that have a matching annual-energy figure from dc_pareto.ENERGY_VARS.
# cap_batt_e and cap_tank are absent by design — see the note in that module.
ENERGY_CAPS = {"cap_grid", "cap_wind", "cap_solar", "cap_batt_p", "cap_ely", "cap_fc"}
NA = float("nan")

# Sentinel for the TNUoS band control: derive the band rather than pin one.
TDR_AUTO = "Auto — from the load"

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


# One colour per source, used by both charts so the battery's band and its
# state of charge are visibly the same asset.
SOURCE_COLOURS = {
    "Solar PV": "#e8b833", "Wind": "#4c9f70", "Offshore wind": "#2f6f8f",
    "Battery": "#8a63b8", "Fuel cell": "#4bacc6", "Grid import": "#9aa0a6",
    "Unserved": "#d62728",
}

# Above this many periods a chart stops being readable before it stops being
# drawable, so the window is averaged down to it. Mean power over a longer step
# is still the right height for an area chart — the energy under the curve is
# preserved — but a one-hour price spike is not.
MAX_PLOT_PERIODS = 1500

# The dispatch panels are a vconcat, which cannot autosize to its container.
PLOT_WIDTH = 780


@st.cache_data(show_spinner=False)
def _dispatch(path: str) -> pd.DataFrame:
    return pd.read_parquet(path)


def _for_display(win: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    """Thin a window down to something Vega can draw, and say so if it was."""
    if len(win) <= MAX_PLOT_PERIODS:
        return win, ""
    step = win.index[1] - win.index[0]
    factor = int(len(win) / MAX_PLOT_PERIODS) + 1
    coarse = win.resample(step * factor).mean(numeric_only=True)
    return coarse, (f" Averaged to {_pretty(step * factor)} steps to stay "
                    f"drawable — {len(win):,} periods would not.")


def _pretty(td: timedelta) -> str:
    h = td.total_seconds() / 3600.0
    return f"{h / 24:.0f} day" if h >= 24 else f"{h:.0f} h"


def _tail(path, lines: int = 40) -> str:
    """The last of a job's log — the only thing a crashed child leaves behind."""
    try:
        return "\n".join(Path(path).read_text().splitlines()[-lines:]) or "(empty)"
    except Exception as exc:
        return f"(no log: {exc})"


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
    pue = st.number_input("PUE", 1.0, 2.0, 1.50, step=0.05,
                          help="1.50 is the base case. IT load x PUE is the "
                               "only thing the model sees: it sets the flat "
                               "demand, and the foreground's embodied hardware "
                               "is scaled by it too, so cooling plant is "
                               "treated as proportional to the reference "
                               "facility rather than costed separately. Set "
                               "**1.00** to reproduce Zhang et al. exactly, "
                               "whose 7.31 MW is already facility-level.")
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
    "the period the optimiser sees. Any window the Carbon Intensity and Elexon "
    "APIs serve works — from 2018-05-11 to yesterday — and one that has not "
    "been built yet is built by the run rather than refused."
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


MAP_PARAM = "pick"


def _map_key() -> str:
    """The map's widget key, which moves with the coordinate.

    A fixed key would leave the last click sitting in the chart's state: after
    typing a coordinate by hand, clicking that same point again would produce
    no change of state, so no rerun, so a dead click. Keying the chart on the
    coordinate hands every rerun a chart whose selection is empty, and makes
    any click on it a change.
    """
    return (f"dc_map_{st.session_state['dc_lat']:.4f}"
            f"_{st.session_state['dc_lon']:.4f}")


def _map_click() -> tuple[float, float] | None:
    """The coordinate a click on the map landed on, if one just did."""
    sel = (st.session_state.get(_map_key()) or {}).get("selection") or {}
    pts = sel.get(MAP_PARAM) or []
    if not pts:
        return None
    return round(float(pts[0]["lat"]), 4), round(float(pts[0]["lon"]), 4)


def _apply_preset():
    key = st.session_state.get("dc_preset")
    if key and key in sites.PRESETS:
        lat, lon, _name = sites.PRESETS[key]
        st.session_state["dc_lat"], st.session_state["dc_lon"] = lat, lon


st.session_state.setdefault("dc_lat", sites.PRESETS[sites.DEFAULT_PRESET][0])
st.session_state.setdefault("dc_lon", sites.PRESETS[sites.DEFAULT_PRESET][1])

# A click on the map arrives as the chart's widget state on the rerun the click
# itself triggers, and Streamlit refuses to let a widget's key be written after
# that widget exists. So the click is spent here, above the number inputs it
# feeds, rather than next to the chart it came from.
_click = _map_click()
if _click:
    st.session_state["dc_lat"], st.session_state["dc_lon"] = _click
# Every click leaves a dead entry behind, because the key moves with it.
for _k in [k for k in st.session_state
           if k.startswith("dc_map_") and k != _map_key()]:
    del st.session_state[_k]

c1, c2, c3, c4, c5, c6 = st.columns([1.3, 0.9, 0.9, 1.0, 1.0, 1.1])
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
        help="**0 derives it** from the IT load and PUE below, at "
             f"{sites.CONNECTION_HEADROOM_ASSUMED:g}x the load — an assumed "
             "headroom, not a sourced figure, since there is no public register "
             "of available connection capacity by location. The derived ceiling "
             "is what the LP is held to *and* what the TNUoS band is read from, "
             "so the two cannot disagree. Enter a number when you have a real "
             "figure for a real site.")
with c5:
    headroom = st.number_input(
        "Connection headroom (x load)", 1.0, 4.0,
        float(sites.CONNECTION_HEADROOM_ASSUMED), step=0.1,
        help="How much more connection than load the site is assumed to "
             "contract for, when the cap above is left at 0. **Assumed, not "
             "sourced** — there is no public register of available connection "
             "capacity. 1.0 asks what a site sized purely for its load can "
             "achieve; the unbounded minimum-carbon build on the 300 MW "
             "Highland run wanted 2.41x, and used it for six hours a year. "
             "The ceiling is what the LP is held to *and* what the TNUoS band "
             "is read from.")

with c6:
    # "Auto" is the default and should stay it. This control used to offer only
    # the distribution bands and default to EHV2 — right for the study's 7.31 MW
    # reference data centre and 17x too cheap for a 300 MW one, with no way to
    # say so, because the transmission bands were not in the list at all. It
    # also silently overrode the derivation in build_series, so the load could
    # say 300 MW while the charge stayed at 7 MW's band.
    tdr = st.selectbox(
        "TNUoS band", [TDR_AUTO, "HV1", "HV2", "HV3", "HV4",
                       "EHV1", "EHV2", "EHV3", "EHV4",
                       "T-Demand1", "T-Demand2", "T-Demand3", "T-Demand4"],
        index=0,
        help="Set by what the site draws, not by where it is. **Auto** derives "
             "it from the IT load and PUE you set below — distribution bands "
             "(LV/HV/EHV) by agreed capacity, transmission bands (T-Demand) by "
             "gross consumption. Override only if you know the site's actual "
             "band; a band that disagrees with the load misprices the "
             "connection by millions a year.")

# --- the map ----------------------------------------------------------------
# Two ways in, one coordinate out. Clicking the map writes the number inputs
# above; typing in them moves the marker. Vega can only report a click as the
# *nearest data point*, so what is clickable is gb_map's grid of GB land
# coordinates rather than the continuous plane — see that module for why the
# grid is land-only and stops at the Irish Sea.
@st.cache_data(show_spinner=False)
def _click_grid() -> pd.DataFrame:
    return gb_map.land_grid()


def _geo(iso: str) -> alt.Data:
    fc = gb_map.outline()
    return alt.Data(
        values={"type": "FeatureCollection",
                "features": [f for f in fc["features"]
                             if f["properties"]["iso"] == iso]},
        format=alt.DataFormat(property="features", type="json"))


_pick = alt.selection_point(name=MAP_PARAM, fields=["lat", "lon"],
                            nearest=True, on="click", empty=False, clear=False)
_ie = alt.Chart(_geo("IRL")).mark_geoshape(
    fill="#ededed", stroke="#d0d0d0", strokeWidth=0.4)
_gb = alt.Chart(_geo("GBR")).mark_geoshape(
    fill="#dfe8dc", stroke="#78907a", strokeWidth=0.5)
_hit = alt.Chart(_click_grid()).mark_square(size=14, opacity=0).encode(
    longitude="lon:Q", latitude="lat:Q",
    tooltip=[alt.Tooltip("lat:Q", title="lat", format=".2f"),
             alt.Tooltip("lon:Q", title="lon", format=".2f")],
).add_params(_pick)
_pre = alt.Chart(pd.DataFrame(
    [{"lat": v[0], "lon": v[1], "name": f"{k} · {v[2]}"}
     for k, v in sites.PRESETS.items()])).mark_point(
    shape="diamond", size=45, filled=True, color="#4c78a8", opacity=0.85).encode(
    longitude="lon:Q", latitude="lat:Q", tooltip=["name:N"])
_here = alt.Chart(pd.DataFrame([{"lat": lat, "lon": lon}])).mark_point(
    shape="circle", size=200, filled=False, color="#d62728",
    strokeWidth=2.5).encode(
    longitude="lon:Q", latitude="lat:Q",
    tooltip=[alt.Tooltip("lat:Q", format=".4f"),
             alt.Tooltip("lon:Q", format=".4f")])
_dot = _here.mark_point(shape="circle", size=18, filled=True, color="#d62728")

mc, mi = st.columns([1, 2])
with mc:
    st.altair_chart(
        alt.layer(_ie, _gb, _hit, _pre, _here, _dot)
        .project(type="mercator")
        .properties(width=330, height=430)
        .configure_view(strokeWidth=0),
        key=_map_key(), on_select="rerun")
with mi:
    _snap = gb_map.nearest_land(lat, lon)
    _off_km = ((_snap[0] - lat) ** 2
               + ((_snap[1] - lon) * 0.6) ** 2) ** 0.5 * 111.0
    st.markdown(
        "**Click anywhere on Great Britain** to place the data centre there; "
        "the latitude and longitude above fill in, and everything below "
        "re-resolves from them. Typing the coordinates instead moves the red "
        "marker — the two controls are the same input.\n\n"
        "The blue diamonds are the presets. A click snaps to the nearest point "
        f"of a {gb_map.DEFAULT_STEP_LAT:g}° × {gb_map.DEFAULT_STEP_LON:g}° "
        "grid of GB land, so it lands within about 5 km of the cursor — finer "
        "than a Carbon Intensity region, but not exact. **Type the coordinate "
        "when the site is real**, especially near a region boundary.\n\n"
        "Ireland is drawn for orientation only, and Northern Ireland is not "
        "clickable: the Carbon Intensity API's regional series, which is the "
        "grid mix this page runs on, covers GB only."
    )
    if _off_km > 8.0:
        st.caption(
            f"The marker is {_off_km:,.0f} km from the nearest clickable land "
            "point — a coordinate this far offshore has no postcode, so the "
            "reverse geocode below will fail or land somewhere unintended.")

try:
    site = sites.resolve(lat, lon, tdr_band=(None if tdr == TDR_AUTO else tdr),
                         connection_limit_mw=(conn or None))
except Exception as exc:
    st.error(f"Could not resolve that coordinate: {exc}")
    st.stop()

# What the settings above actually resolve to. The chain is load -> connection
# ceiling -> band -> tariff, and each link used to be settable independently of
# the others, so the page could show a 300 MW site being charged a 7 MW band.
_load_preview = size_mw * pue          # both set in section 1, above
if _load_preview > 0:
    from optimisation import network_charges as _nc
    _cmw, _cnote = ((float(conn), "") if conn else
                    sites.max_connection_mw(_load_preview, headroom))
    _trans, _ = _nc.is_transmission_connected(_cmw)
    _band = tdr if tdr != TDR_AUTO else _nc.tdr_band_for(
        _cmw, _load_preview * 8760.0, transmission_connected=_trans)[0]
    _mismatch = tdr != TDR_AUTO and (_trans != _band.startswith("T-Demand"))
    st.caption(
        f"**Resolves to:** {_load_preview:,.1f} MW load → "
        f"{_cmw:,.1f} MW connection ceiling "
        f"({f'derived at {headroom:g}x' if not conn else 'as entered'}) → "
        f"{'transmission' if _trans else 'distribution'}-connected → "
        f"band **{_band}**"
        + (f"  ·  _{_cnote}_" if _cnote else ""))
    if _mismatch:
        st.warning(
            f"**The band you picked does not match the connection.** "
            f"{_band} is a "
            f"{'transmission' if _band.startswith('T-Demand') else 'distribution'}"
            f" band, but a {_cmw:,.0f} MW connection is "
            f"{'transmission' if _trans else 'distribution'}-connected. Set the "
            f"band to Auto unless you know the site's actual agreed band.")

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

# Readiness is about *this window*, not about the region having some file
# somewhere. A region whose only cached series is one week of June is not ready
# for a January window, and saying "cached" on the strength of the file
# existing is how that mismatch got discovered by a run failing minutes later
# with an error about representative-day sampling that had nothing to do with it.
#
# Nothing here gates the Optimise button any more: a missing window is built by
# the run itself (dc_inputs.build_series -> sites.ensure_grid_series). This box
# only says whether this run will pay for a build first.
try:
    _status = profiles.window_status(start, end,
                                     carbon_api_region=site.carbon_api_region)
except Exception as _exc:                      # unparseable dates, mostly
    _status = {"ok": False, "grid_ok": False, "price_ok": False,
               "grid_index": {}, "detail": str(_exc)}

if _status["ok"]:
    st.success(
        f"Grid and price data cover {start} to {end} for region "
        f"{site.carbon_api_region} ({site.region_name}) — "
        f"`{_status['grid_file']}`. The run starts solving immediately.")
else:
    _missing = " and ".join(
        k for k in ("grid", "price") if not _status[f"{k}_ok"]) or "data"
    st.info(
        f"**No {_missing} series covers {start} to {end}"
        + (f" for region {site.carbon_api_region} ({site.region_name})"
           if not _status["grid_ok"] else "")
        + " yet — the run will build it first.**\n\n"
        "Substituting another region's half-hourly intensities, or another "
        "month's, would give a confident wrong answer about whether renewables "
        "beat the grid here, so the window is built rather than borrowed. "
        "Building scores the GB fuel mix against ecoinvent for every half-hour: "
        "a week takes a couple of minutes, a full year considerably longer. It "
        "happens inside the same detached process as the solve, so you can "
        "close the tab while it runs.")
    if _status["grid_index"]:
        with st.expander("What is on disk for this region"):
            st.code(profiles.describe_files(_status["grid_index"]))


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

# Two anchors plus points-1 epsilon solves, and a target if one is asked for.
# Each anchor can also need up to two tie-break solves — see dc_pareto._tie_break
# — which is why the count is a range rather than a number.
n_solves = int(points) + 1 + (1 if gwp_target is not None else 0)
st.caption(f"**{n_solves}–{n_solves + 4} LP solves** at {resample:g} h steps — the "
           "spread is the anchor tie-breaks, which only run when an objective "
           "leaves its own answer undetermined. Results are cached on a hash of "
           "every input above plus the model source, so re-running an unchanged "
           "scenario is free.")

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

# Is something already solving? The answer lives in a file, not in this
# session, so it is the same answer for every tab and every reload.
job = dc_job.active()
job_running = bool(job and job["state"] in ("starting", "running"))

c1, c2, _ = st.columns([1, 1, 3])
with c1:
    launch = st.button("Optimise", type="primary",
                       disabled=bool(problems) or job_running,
                       help="A run is already in progress — stop it, or wait."
                       if job_running else None)
with c2:
    refresh = st.checkbox("Ignore cache", value=False, disabled=job_running)

if launch:
    dc_job.start(
        scenario=scenario, site=site, out_root=out_root, label=label,
        total=n_solves + 4,
        start=start, end=end, size_mw_it=size_mw, pue=pue,
        resample_hours=(resample or None), points=int(points),
        cost_case=cost_case, horizon_years=horizon,
        unserved_fraction=unserved, gwp_target_kg_per_year=gwp_target,
        connection_headroom=headroom, refresh=refresh,
        # Always: it is a few MB, and a run whose dispatch was not kept cannot
        # be asked about later without solving it again.
        save_dispatch=True)
    st.rerun()

# --- whatever is running, wherever it was started ---------------------------
# The solve is a detached process writing to disk, not a call inside this
# script (see optimisation/dc_job.py). So this panel is the same whether the
# run was just launched, or launched twenty minutes ago by a browser tab that
# has since been closed: it reads the job's status file either way.
if job:
    _el = ""
    with contextlib.suppress(Exception):
        _t0 = datetime.fromisoformat(job["started"])
        _el = f" · {(datetime.now(timezone.utc) - _t0).total_seconds() / 60:.0f} min elapsed"

    if job_running:
        box = st.container(border=True)
        box.markdown(f"**Solving — {job['label']}** at {job['site_name']}{_el}")
        # Never let the bar sit at 100 % while the solve is still going: the
        # exact number of LPs is not known ahead of time (tie-breaks), so the
        # denominator is an estimate and the bar is kept honest about it.
        _n = int(job.get("done") or 0)
        _tot = max(int(job.get("total") or 1), _n + 1)
        box.progress(_n / _tot, text=f"LP {_n} of ~{_tot} — {job.get('tag', '')}")
        box.caption(
            "This is running in its own process. **Leave the page, close the "
            "tab, come back tomorrow** — it keeps going, and this panel finds "
            "it again. Only Stop, or killing the machine, ends it."
        )
        if job.get("quiet"):
            _building = "building grid data" in str(job.get("tag", ""))
            box.caption(
                f"No progress line for {job['quiet_seconds'] / 60:.0f} minutes. "
                + ("That is the grid build above: it scores the GB fuel mix "
                   "against ecoinvent for every half-hour of the window, and "
                   "reports nothing until it finishes."
                   if _building else
                   "That is normal before the first LP — building the "
                   "half-hourly series can fetch and score a full year of grid "
                   "data — and abnormal after it."))
        b1, b2, _ = box.columns([1, 1, 3])
        if b1.button("Stop"):
            dc_job.cancel(job["folder"])
            st.rerun()
        b2.button("Refresh")

    elif job["state"] == "done":
        _summary = dc_job.summary(job["folder"])
        if _summary:
            st.session_state["dc_summary"] = _summary
            st.session_state["dc_out_root"] = str(Path(job["folder"]).parent)
            _how = ("read from cache" if job.get("cached") else
                    f"{job.get('solve_seconds') or 0:.0f} s")
            st.success(f"**Solved — {job['label']}** ({_how}). "
                       "The answer is below, and stays here across refreshes.")
        else:
            st.warning("The job finished but wrote no summary — see its log.")

    else:
        st.error(
            f"**The run {'was cancelled' if job.get('tag') == 'cancelled' else job['state']}"
            f" — {job['label']}.**\n\n"
            + (f"`{job['error']}`" if job.get("error") else
               "The solver process is no longer alive and left no result. "
               "Its log has the last thing it printed."))
        with st.expander("Job log"):
            st.code(_tail(job.get("log")), language="text")
        if st.button("Dismiss"):
            dc_job.clear_pointer()
            st.rerun()


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
    # Asset x build x (capacity, energy) is three dimensions in a two-
    # dimensional table. Interleaving capacity and MWh columns fits, but at
    # eight columns nobody can read across it. Two tables of the same shape,
    # stacked, keep every column narrow and put each MWh directly under the
    # capacity it belongs to.
    caps, energy = [], []
    for key, name, unit in CAPS:
        allowed = any(key in FLAG_CAPS[f] for f in ran_kit)
        vals = {colname: float(p.get(key, 0.0)) for colname, p in cols.items()}
        if not allowed and all(v <= 1e-6 for v in vals.values()):
            continue
        caps.append({"Asset": name, "Unit": unit, **vals})

        # Absent, not zero, for an asset with no MWh of its own, and for a
        # result cached before this column existed — both must read blank
        # rather than as a genuine zero.
        mwh = {colname: (float(point[f"{key}_MWh_per_year"])
                         if key in ENERGY_CAPS and f"{key}_MWh_per_year" in point
                         else NA)
               for colname, point in cols.items()}
        energy.append({"Asset": name, **mwh})

    num = {name: st.column_config.NumberColumn(format="%.2f") for name in cols}
    st.markdown("**What to build**")
    st.dataframe(pd.DataFrame(caps), width="stretch", hide_index=True,
                 column_config=num)

    st.markdown("**Energy through it, MWh per year**")
    st.dataframe(pd.DataFrame(energy), width="stretch", hide_index=True,
                 column_config={name: st.column_config.NumberColumn(
                     format="localized") for name in cols})
    st.caption(
        "Same rows, same order, so each figure sits under the capacity built to "
        "carry it. **Battery energy and hydrogen storage are blank on purpose:** "
        "the battery's energy rating shares the power rating's flow, and the "
        "tank is sized in kg of stock rather than MWh of throughput, so neither "
        "has an MWh of its own."
    )

    st.caption(
        "**A small MWh against a large capacity means the asset was sized by "
        "peak, not by energy** — which is normal for a battery and worth "
        "looking at for the grid connection. On the 300 MW Highland run the "
        "lowest-emissions connection is 868 MW carrying 246,749 MWh, a 3.2 % "
        "load factor against 37.7 % at lowest cost, with six hours of the year "
        "above 99 % of it. That is genuine: re-solving for least cost at the "
        "same carbon shrinks it by 3.3 MW. Decarbonising the last stretch buys "
        "a connection sized for a handful of hours, and at Highland's DUoS "
        "capacity rate those 868 MW are £29 m/yr of the build's cost."
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

    # --- the dispatch, period by period ---------------------------------------
    # Capacities say what is built; only the dispatch says how it is used. The
    # bands are an attribution, not an LP output — dc_model.serve_stack owns
    # that convention, and explains it, so this page does not restate it.
    _disp_path = Path(st.session_state["dc_out_root"]) / summary["key"] / "dispatch.parquet"
    if _disp_path.exists():
        st.subheader("How each build actually runs")

        _have = [(k, name) for k, name in POINTS_SHOWN
                 if k in set(_dispatch(str(_disp_path)).point.unique())]
        d1, d2 = st.columns([1.4, 2])
        with d1:
            _pick_pt = st.radio("Which build", [k for k, _ in _have],
                                format_func=dict(_have).get, key="dsp_point")
        _frame = (_dispatch(str(_disp_path)).query("point == @_pick_pt")
                  .set_index("t").sort_index())
        _t0 = _frame.index.min().to_pydatetime()
        _t1 = _frame.index.max().to_pydatetime()
        _span = _t1 - _t0
        with d2:
            if _span > timedelta(days=8):
                _default = (_t0, _t0 + timedelta(days=7))
                _lo, _hi = st.slider(
                    "Time range", _t0, _t1, _default, format="D MMM",
                    key="dsp_range",
                    help="A week shows the daily cycle; a month shows the "
                         "weather. The whole window is averaged down to stay "
                         "drawable — the shape survives, single hours do not.")
            else:
                _lo, _hi = _t0, _t1
                st.caption(f"The whole window: {_t0:%d %b} to {_t1:%d %b}.")

        _win = _frame.loc[_lo:_hi]
        _win, _note = _for_display(_win)
        _stack = dc_model.serve_stack(_win)

        _order = [x for x in dc_model.SERVE_SOURCES
                  if _stack.loc[_stack.source == x, "mw"].abs().sum() > 1e-9]
        _area = alt.Chart(_stack[_stack.source.isin(_order)]).mark_area(
            interpolate="step-after").encode(
            x=alt.X("t:T", title=None, axis=alt.Axis(format="%-d %b %H:%M")),
            y=alt.Y("mw:Q", title="MW serving the load", stack=True),
            color=alt.Color("source:N", title=None,
                            sort=list(dc_model.SERVE_SOURCES),
                            scale=alt.Scale(domain=list(dc_model.SERVE_SOURCES),
                                            range=list(SOURCE_COLOURS.values())),
                            legend=alt.Legend(orient="bottom", columns=4)),
            order=alt.Order("rank:Q", sort="ascending"),
            tooltip=[alt.Tooltip("t:T", title="when"), "source:N",
                     alt.Tooltip("mw:Q", format=".2f", title="MW")],
        # Vega-Lite only honours a container width on single and layered
        # views, never inside a vconcat — so both panels are pinned to the same
        # explicit width instead, which is also what keeps their x axes lined up.
        ).properties(height=260, width=PLOT_WIDTH)

        _cap_e = float((summary.get(_pick_pt) or {}).get("cap_batt_e") or 0.0)
        if _cap_e > 1e-6:
            _soc = alt.Chart(_win.reset_index()).mark_line(
                color=SOURCE_COLOURS["Battery"], strokeWidth=1.5).encode(
                x=alt.X("t:T", title=None, axis=alt.Axis(format="%-d %b %H:%M")),
                y=alt.Y("soc:Q", title="Battery charge, MWh",
                        scale=alt.Scale(domain=[0, _cap_e * 1.05])),
                tooltip=[alt.Tooltip("t:T", title="when"),
                         alt.Tooltip("soc:Q", format=".2f", title="MWh")],
            ).properties(height=130, width=PLOT_WIDTH)
            _full = alt.Chart(pd.DataFrame({"y": [_cap_e]})).mark_rule(
                strokeDash=[4, 4], color="grey").encode(y="y:Q")
            st.altair_chart(alt.vconcat(_area, _soc + _full)
                            .resolve_scale(x="shared"), width="stretch")
            st.caption(
                f"The dashed line is this build's {_cap_e:,.1f} MWh of battery "
                f"energy — where the charge line touches it, the battery is "
                "full and further surplus is curtailed or exported."
                + _note)
        else:
            st.altair_chart(_area, width="stretch")
            st.caption("This build has no battery, so there is no state of "
                       "charge to plot." + _note)

        st.caption(
            "**Bands are demand served, not generation.** They sum to demand in "
            "every period, so renewable output that charged the battery, ran "
            "the electrolyser, was exported or was curtailed is not in them. "
            "Which source served the load when several were flowing is a "
            "reading convention — renewables first, then battery, then fuel "
            "cell, with the grid as the residual — set out in full in "
            "`dc_model.serve_stack`."
        )
        _download(_win.reset_index(), f"dispatch_{_pick_pt}.csv",
                  "Download this window, every column")

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
            show = f[["point", "cost_m", "gwp_t", "gwp_g_per_kWh"]
                     + [c for k, _, _ in CAPS
                        for c in ((k, f"{k}_MWh_per_year") if k in ENERGY_CAPS
                                  else (k,))
                        if c in f.columns]]
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
         **{f"{k}_MWh_per_year": p.get(f"{k}_MWh_per_year", NA)
            for k, _, _ in CAPS if k in ENERGY_CAPS},
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
# 6. How far from hydrogen
# =============================================================================
st.header("6. How far from hydrogen?")
st.markdown(
    "An asset sized to zero says *not at these prices*. This asks the follow-on "
    "question — **how far would a price have to move before it was worth "
    "building?** — by moving one input at a time and re-solving until hydrogen "
    "first carries a stated share of the load.\n\n"
    "It is a separate run because it costs roughly nine solves **per input**, "
    "against one sweep for the answer above. It inherits every setting from the "
    "result on screen rather than reading the boxes above, so a threshold can "
    "never quote itself against a configuration you have since changed."
)

_thr_run_folder = None
if summary and st.session_state.get("dc_out_root"):
    _thr_run_folder = Path(st.session_state["dc_out_root"]) / summary["key"]

if not summary:
    st.info("Solve something first — a threshold is measured against a result.")
elif _thr_run_folder is None or not (_thr_run_folder / "config.json").exists():
    st.info(
        "This answer came from a cache written before the page recorded its own "
        "settings. Press **Optimise** with *Ignore cache* ticked to make it "
        "re-runnable, and this section will open."
    )
else:
    _inherited = None
    try:
        _inherited = TH.from_run(_thr_run_folder)
    except Exception as _exc:
        st.warning(f"Could not read that run's settings back: `{_exc}`")

    if _inherited is not None:
        _scen = _inherited["scenario"]
        _knobs_all = TH.applicable_knobs(_scen)
        _h2_knobs = [k for k in _knobs_all
                     if k in ("h2_price", "ely_capex", "fc_capex", "tank_capex",
                              "h2_chain")]

        # Does hydrogen even appear in what was solved? Without a fuel cell
        # there is nothing to measure a share through, and every knob would
        # come back not_applicable at the cost of a solve each.
        if not _h2_knobs:
            st.info(
                "The run above has no hydrogen in it — nothing to find a "
                "threshold for. Tick an electrolyser, a store and a fuel cell "
                "in section 3, or bring in a priced colour, and re-solve."
            )
        else:
            _c = _inherited["config"]
            st.caption(
                f"Inheriting from **{summary['label']}** at {summary['site_name']} · "
                f"{_c['size_mw_it']:g} MW IT · PUE {_c['pue']:g} · "
                f"{_c['start']} to {_c['end']} · {_c['cost_case']} costs · "
                f"{_c.get('resample_hours') or 0.5:g} h steps."
            )

            _stale_ok = True
            if _inherited["stale"]:
                st.warning(
                    "**"
                    + ", ".join(f"`{k}`" for k in _inherited["stale_keys"])
                    + "** changed since that front was solved, so a threshold "
                      "found now would be annotating a result that no longer "
                      "exists. Re-solve section 4 first, or tick below to "
                      "proceed anyway."
                )
                _stale_ok = st.checkbox(
                    "Run against the stale result anyway", value=False)

            k1, k2 = st.columns([3, 2])
            with k1:
                _pick = st.multiselect(
                    "Inputs to find a threshold in", _knobs_all,
                    default=_h2_knobs,
                    format_func=lambda k: TH.KNOBS[k].label,
                    help="Only the inputs this configuration can actually "
                         "answer are listed. `h2_chain` moves the electrolyser, "
                         "store and fuel cell together — usually the only one "
                         "that reaches a threshold, because no single link "
                         "carries the chain alone.")
            with k2:
                _entry = st.slider(
                    "Counts as hydrogen at this share of load (%)", 0.5, 10.0,
                    TH.ENTRY_SHARE * 100, step=0.5, format="%.1f",
                    help="The first MW enters at zero volume, so a bare "
                         "'capacity above zero' test lands in a band where the "
                         "optimiser is indifferent. A share bisects cleanly.")
                _coarse = st.checkbox(
                    "Coarser steps (2 h)",
                    value=bool((_c.get("resample_hours") or 0.5) < 2),
                    help="Roughly 4x faster. The study's own measurement puts "
                         "2 h steps at about 1.2 % on carbon against 30 min — "
                         "fine for locating a threshold, too coarse to quote "
                         "the build at it.")

            if _pick:
                st.caption(
                    f"**~{TH.estimate_solves(_pick)} LP solves** "
                    f"({len(_pick)} input{'s' if len(_pick) > 1 else ''} "
                    f"x ~9 each, measured). Cached per input, so a re-run that "
                    "changes nothing is free."
                )

            _tjob = dc_job.active("thresholds")
            _trunning = bool(_tjob and _tjob["state"] in ("starting", "running"))
            t1, t2, _ = st.columns([1, 1, 3])
            with t1:
                _tlaunch = st.button(
                    "Find thresholds", type="primary",
                    disabled=(not _pick) or _trunning or not _stale_ok,
                    help="A threshold sweep is already running — stop it, or wait."
                    if _trunning else None)
            with t2:
                _trefresh = st.checkbox("Ignore cache", value=False,
                                        key="thr_refresh", disabled=_trunning)

            if _tlaunch:
                _kw = dict(_inherited["kwargs"])
                _site = _kw.pop("site")
                if _coarse:
                    _kw["resample_hours"] = 2.0
                dc_job.start(
                    kind="thresholds", scenario=_scen, site=_site,
                    out_root=Path(st.session_state["dc_out_root"]),
                    label=f"thresholds — {summary['label']}",
                    total=TH.estimate_solves(_pick) + len(_pick),
                    knobs=list(_pick), target_share=_entry / 100.0,
                    refresh=_trefresh, **_kw)
                st.rerun()

            # --- the sweep's own status panel, same protocol as section 4 ----
            if _tjob:
                if _trunning:
                    _box = st.container(border=True)
                    _box.markdown(f"**Searching — {_tjob['label']}**")
                    _n = int(_tjob.get("done") or 0)
                    _tot = max(int(_tjob.get("total") or 1), _n + 1)
                    _box.progress(_n / _tot,
                                  text=f"solve {_n} of ~{_tot} — {_tjob.get('tag', '')}")
                    _box.caption(
                        "Detached, like the optimiser itself — leave the page "
                        "and come back. Each input's result is written the "
                        "moment it is found, so a sweep stopped halfway keeps "
                        "what it already answered."
                    )
                    _b1, _b2, _ = _box.columns([1, 1, 3])
                    if _b1.button("Stop", key="thr_stop"):
                        dc_job.cancel(_tjob["folder"])
                        st.rerun()
                    _b2.button("Refresh", key="thr_refresh_btn")
                elif _tjob["state"] not in ("done",):
                    st.error(
                        f"**The threshold sweep "
                        f"{'was cancelled' if _tjob.get('tag') == 'cancelled' else _tjob['state']}.**\n\n"
                        + (f"`{_tjob['error']}`" if _tjob.get("error") else
                           "Its process is gone. Anything it had already found "
                           "is still shown below."))
                    if st.button("Dismiss", key="thr_dismiss"):
                        dc_job.clear_pointer("thresholds")
                        st.rerun()

            # --- results, read from disk so they outlive the session ---------
            _found = TH.load_run(
                Path(st.session_state["dc_out_root"]) / "_thresholds", _scen.key)
            if _found:
                st.subheader("What would have to change")
                for _r in sorted(_found, key=lambda r: (r["status"] != "found",
                                                        r["knob"])):
                    (st.success if _r["status"] == "found" else st.info)(
                        TH.describe(_r))

                _tdf = pd.DataFrame(TH.records(_found))
                _show = _tdf[["knob_label", "unit", "today", "threshold",
                              "needs", "status", "solves"]].rename(columns={
                    "knob_label": "Input", "unit": "Unit", "today": "Today",
                    "threshold": "Threshold", "needs": "Move required",
                    "status": "Result", "solves": "Solves"})
                st.dataframe(_show, width="stretch", hide_index=True)
                _download(_tdf, "hydrogen_thresholds.csv",
                          "Download these thresholds as CSV")

                with st.expander("Every re-solve behind them"):
                    st.caption(
                        "The path to a threshold is worth as much as the "
                        "threshold: it says whether hydrogen arrives gradually "
                        "or all at once. In this study it has always been a "
                        "cliff."
                    )
                    _pickc = st.selectbox(
                        "Input", [r["knob"] for r in _found],
                        format_func=lambda k: TH.KNOBS[k].label, key="thr_curve")
                    _cr = next(r for r in _found if r["knob"] == _pickc)
                    _cf = TH.curve_frame(_cr)
                    if not _cf.empty:
                        _cf = _cf.assign(
                            share_pct=_cf["h2_share_of_load"].clip(lower=0) * 100)
                        _chart = alt.Chart(_cf).mark_line(point=True).encode(
                            x=alt.X("value:Q", title=f"{TH.KNOBS[_pickc].label} "
                                                     f"({TH.KNOBS[_pickc].unit})"),
                            y=alt.Y("share_pct:Q", title="H₂ share of load (%)"),
                            tooltip=[alt.Tooltip("value:Q", format=".4g"),
                                     alt.Tooltip("share_pct:Q", format=".2f",
                                                 title="% of load"),
                                     alt.Tooltip("cost_GBP_per_MWh:Q", format=".2f"),
                                     alt.Tooltip("gwp_g_per_kWh:Q", format=".1f"),
                                     alt.Tooltip("cap_ely:Q", format=".3f"),
                                     alt.Tooltip("cap_fc:Q", format=".3f")],
                        ).properties(height=260)
                        st.altair_chart(_chart, width="stretch")
                        st.dataframe(
                            _cf[["value", "share_pct", "cap_ely", "cap_tank",
                                 "cap_fc", "cap_batt_e", "cost_GBP_per_MWh",
                                 "gwp_g_per_kWh"]],
                            width="stretch", hide_index=True)
                    if _cr.get("knob_note"):
                        st.caption(_cr["knob_note"])
                    if not _cr.get("monotone", True):
                        st.warning(
                            "Hydrogen's share did not move consistently with "
                            "this input, so the value above is one step among "
                            "several rather than *the* tipping point. Read the "
                            "curve."
                        )
                st.caption(
                    "Perfect foresight applies here too, and doubly: these say "
                    "what would have to be true for hydrogen to be worth "
                    "**building**, not what an operator without a year's "
                    "forecast would achieve."
                )


# =============================================================================
# 7. The numbers behind the answer
# =============================================================================
st.header("7. The numbers behind the answer")
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


# =============================================================================
# Poll, last of all
# =============================================================================
# Deliberately at the bottom: a rerun redraws the page from the top, so waiting
# here means everything above is already on screen while the solve continues.
# The sleep costs this session nothing that matters — the work is in another
# process, and closing the tab stops the polling, not the run.
if job_running:
    time.sleep(2.0)
    st.rerun()
