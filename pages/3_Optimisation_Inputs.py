"""Optimisation Inputs — the cost and carbon coefficients the optimiser will use.

Every table on this page is produced by the modules in ``optimisation/``, not
recomputed here. This page only selects a scenario, calls them, and displays
what they return — the same relationship the Setup LCA page has with the
notebooks, so there is never a second implementation of the science to keep
in sync.

Each tab also shows the module's own console output, which carries its
cross-checks and caveats. Those are worth reading: several of them exist
because they caught real errors.
"""

from __future__ import annotations

import contextlib
import importlib
import io
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

REPO_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_DIR))

import lca_helpers as H
from optimisation import baseline_grid, battery, h2_prices, renewables, tech_costs

# Streamlit reruns this script on every interaction but keeps imported modules
# in sys.modules, so edits to optimisation/*.py would otherwise need a full app
# restart to show up. These modules are small, pure and free of import-time side
# effects, and they only import each other inside function bodies, so reloading
# them here is safe and keeps the page honest about what the code currently says.
for _mod in (tech_costs, renewables, h2_prices, battery, baseline_grid):
    importlib.reload(_mod)

st.set_page_config(page_title="Optimisation Inputs", layout="wide")
st.title("Optimisation Inputs")
st.caption(
    "Cost and carbon coefficients for the data-centre powering study — "
    "generation, hydrogen by colour, battery storage, and the grid baseline."
)

OUT_DIR = REPO_DIR / "optimisation_outputs"


@st.cache_resource(show_spinner="Connecting to Brightway…")
def _connect():
    H.setup_brightway()
    return True


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
    st.download_button(
        label or f"Download {name}",
        df.to_csv(index=False).encode("utf-8"),
        file_name=name, mime="text/csv", key=f"dl_{name}",
    )


# =============================================================================
# Scenario
# =============================================================================
with st.sidebar:
    st.header("Scenario")
    case = st.radio(
        "Cost case", ["low", "central", "high"], index=1,
        help="DESNZ/Arup scenario labels. Low and high pair costs inversely with "
             "load factor and lifetime, following the reports' own method.",
    )
    durations = st.multiselect(
        "Battery durations (hours)", [1, 2, 4, 8, 12], default=[1, 2, 4, 8],
        help="Power and energy are costed separately, so any duration is valid.",
    ) or [1, 2, 4, 8]
    st.divider()
    st.caption(
        "Provenance for every number is in the **Sources** tab. "
        "Deferred gaps are listed there too."
    )

try:
    _connect()
except Exception as exc:
    st.error(f"Could not open the Brightway project: {exc}")
    st.stop()

tab_base, tab_gen, tab_h2, tab_batt, tab_src = st.tabs(
    ["Baseline — GB grid", "Generation", "Hydrogen", "Battery", "Sources"]
)

# =============================================================================
# Baseline
# =============================================================================
with tab_base:
    st.subheader("Baseline 1 — data centre on the GB grid")
    st.caption(
        "The data centre's US-SERC electricity exchanges are swapped for the "
        "half-hourly GB grid mix. Flat 100 % load — which is the foreground's "
        "own figure, not an added assumption."
    )

    @st.cache_data(show_spinner="Running the grid baseline…")
    def _baseline():
        return _capture(baseline_grid.run)

    try:
        summary, console = _baseline()
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
        _download(summary, "baseline1_summary.csv")
        _console(console)
    except Exception as exc:
        st.error(f"Baseline failed: {exc}")

# =============================================================================
# Generation
# =============================================================================
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
        view = ann_df[ann_df.case == case][[
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
        rows, carbon_console = _gen_decompose()
        emb = renewables.apply_case(rows, case)
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
            f"{w.ecoinvent_lifetime_years:.0f} y); on the **{case}** cost case "
            f"DESNZ/Arup give {w.study_lifetime_kWh_per_kW:,.0f} kWh/kW "
            f"({w.study_load_factor:.1%} for {w.study_lifetime_years:.0f} y) — "
            f"{w.study_lifetime_kWh_per_kW / w.ecoinvent_lifetime_kWh_per_kW:.1f}× more. "
            f"Charging embodied carbon per kWh at ecoinvent's rate overstates it by that "
            f"factor: {w.ecoinvent_per_kWh*1000:.1f} vs "
            f"{w.restated_kgco2e_per_kWh*1000:.1f} g CO₂e/kWh. Notebooks 4.1 and 4.3 do "
            f"exactly that — fine for a fixed plant, wrong once capacity is a decision "
            f"variable. Use the per-MW figures here."
        )
        pv = emb[emb.technology == "solar_pv"].iloc[0]
        st.info(
            f"**PV is a conservative upper bound.** ecoinvent 3.9.1's GB open-ground PV "
            f"is a 2012 multi-Si plant, so it restates to "
            f"~{pv.restated_kgco2e_per_kWh*1000:.0f} g CO₂e/kWh against ~20–40 g/kWh in "
            f"current literature. Wind, being mostly steel and concrete, is far less "
            f"affected."
        )
        _download(emb.drop(columns=["_parts"]), "renewables_embodied.csv")
        st.caption(
            "Ratios below 1 mean ecoinvent's per-kWh figure overstates the burden "
            "for this study's yield. Run `python optimisation/renewables.py` for the "
            "module's full commentary."
        )
    except Exception as exc:
        st.error(f"Generation inputs failed: {exc}")

# =============================================================================
# Hydrogen
# =============================================================================
with tab_h2:
    st.subheader("Hydrogen purchase price by colour")
    st.caption(
        "Hydrogen is bought, not self-produced. Production is co-located with use, "
        "so these are plant-gate prices with no delivery leg."
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

# =============================================================================
# Battery
# =============================================================================
with tab_batt:
    st.subheader("Battery storage — Li-ion LFP")
    st.caption(
        "Power and energy are costed and scored separately, so the optimiser can "
        "choose duration rather than being locked to a 4-hour product."
    )

    @st.cache_data(show_spinner="Loading battery inputs…")
    def _batt(durs: tuple):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            battery.run()
        return battery.cost_table(durs), battery.carbon_table(durs), buf.getvalue()

    try:
        ct, kt, console = _batt(tuple(sorted(durations)))
        comp = battery.cost_components()[case]
        c = st.columns(4)
        c[0].metric("Capex, power", f"£{comp['power_GBP_per_kW']:,.0f}/kW")
        c[1].metric("Capex, energy", f"£{comp['energy_GBP_per_kWh']:,.0f}/kWh")
        c[2].metric("Embodied, energy",
                    f"{battery.embodied_components()['energy_kgco2e_per_kWh']:,.0f} kg/kWh")
        c[3].metric("Throughput",
                    f"{battery.lifetime_throughput_mwh_per_mwh():,.0f} MWh/MWh")

        merged = (ct[ct.case == case]
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
            f"against the data centre's 25 means "
            f"**{battery.builds_over_horizon(25):.2f} builds** over the horizon, which "
            "both cost and carbon must carry. Fixed OPEX is a flagged proxy — Modo do "
            "not publish it — and the embodied figure excludes container, racking and "
            "HVAC, for which ecoinvent 3.9.1 has no dataset."
        )
        _download(ct, "battery_costs.csv")
        _download(kt, "battery_carbon.csv")
        _console(console)
    except Exception as exc:
        st.error(f"Battery inputs failed: {exc}")

# =============================================================================
# Sources
# =============================================================================
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
                st.markdown(path.read_text())
            else:
                st.warning(f"{fname} not found.")
