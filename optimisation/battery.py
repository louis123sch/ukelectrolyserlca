"""
Lithium-ion battery storage — cost and embodied carbon.
=============================================================================

Costs since 9 Nov 2026 come from **NESO's FES 2025 Economics Inputs Data
Workbook**, sheet E.03: capital and fixed running cost of a battery built in
2026, by duration (1, 2, 4, 6 and 9 hours), in 2025 pounds — the system
operator's figure, stated for the build year (its capital is Modo's data, its
running cost BEIS 2022's, inflated). The straight line through it carries the
price beyond 9 hours (``PNNL_LFP_10MW_2030_USD_PER_KW``). Until 9 Nov the
central case was BEIS 2022 (2030 capital, real 2019), kept below as
``BEIS_CAPEX_GBP_PER_KW`` for the record. Modo Energy sets the low case. Everything
is in **real 2025 GBP** (dc_inputs takes it to 2026).

Embodied carbon comes from ecoinvent 3.9.1. Cost and carbon are deliberately
kept on the same two-part structure — a **power** term (£/kW, kg CO2e/kW) and
an **energy** term (£/kWh, kg CO2e/kWh) — so the optimiser can size power and
duration independently instead of being locked to a 4-hour product.

Sources
-------
cost              NESO, FES 2025 Economics Inputs Data Workbook v2 (Aug 2026),
                  sheet E.03, rows 14-18 (CapEx) and 59-63 (Fixed OpEx), 2026
                  column; sheet E.02 rows 13-17: 15-year life, 1-year build.
                  2025 prices. Was BEIS, Benefits of Long Duration Electricity
                  Storage (2022), Exhibit 3.11 (real 2019, 2030 capital).

cost low case,    Modo Energy, "BESS Cost and Technical Assumptions",
technical         docs.modoenergy.com/pages/jan-2026/uk-europe/model-assumptions/
                  (July 2026). ~£400/kW for a 1-hour system today falling to
                  ~£200/kW by 2040. 15-year asset life, ~67 % capacity
                  remaining after 10,000 cycles (~12-15 years), 1-2 cycles per
                  day. Real 2025 GBP. Each further hour: Ember, "How cheap is
                  battery storage?" (Dec 2025), about $125/kWh all-in.

cost high case    US Annual Technology Baseline 2025, utility-scale battery,
                  moderate, 2026, 2 to 10 hours, 2023 US $.

discount rate     CEPA for DESNZ, hurdle rates (2025), Table E.1: lithium
                  batteries 8.90 % pre-tax real.

cost spread       Modo Energy BESS CapEx Survey 2024 (30 market participants,
                  2.8 GW at 1.9 h average): average £580k/MW, two-hour median
                  £650k/MW, 68 % of projects between £400k/MW and £700k/MW.

round-trip eff.   88 %, Modo's standard assumption. Not stated on the model
                  assumptions page itself, so it is the least firmly sourced
                  number here.

embodied carbon   energy term: the ``battery foreground`` built by
                  ``optimiser_lca/bess.py`` — Jasper et al. (2026) Energy
                  Advances 5:550, liquid-cooled LFP container, around the Voß
                  et al. (2025) Energy Environ. Sci. 18:8104 LFP cell, on
                  ecoinvent 3.9.1 apos. Power term: ecoinvent 3.9.1 apos
                  500 kW inverter. IPCC 2021 GWP100.

Every number in this module is listed in ``SOURCES.md`` alongside its
source and provenance grade (transcribed / derived / assumed).

Run:  python optimisation/battery.py
"""
import math
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
OUT_DIR = ROOT / "optimisation_outputs"

import numpy as np  # noqa: E402

from optimisation import price_base as P  # noqa: E402
from optimisation import trace as T  # noqa: E402

CASES = ("low", "central", "high")

# =============================================================================
# Cost — BEIS 2022, with Modo Energy as the low case; real 2025 GBP
# =============================================================================
# Central since 4 Nov 2026 (UK government sources first, COST_GOV_FIGURES_PLAN.md):
# BEIS, Benefits of Long Duration Electricity Storage (2022), Exhibit 3.11, p. 30,
# real 2019 pounds. It covers 1 to 9 hours; a 2022 forecast of 2030 capital, so its
# age is stated rather than corrected.
BEIS_PRICE_YEAR = 2019
BEIS_CAPEX_GBP_PER_KW = {1: 331.0, 2: 449.0, 4: 696.0, 6: 930.0, 9: 1328.0}       # the record; not used
BEIS_OPEX_GBP_PER_KW_YEAR = {1: 5.0, 2: 7.0, 4: 10.0, 6: 11.0, 9: 13.0}

# Central since 9 Nov 2026 (government or system operator decides): NESO FES 2025
# Economics Inputs Data Workbook v2, sheet E.03, build year 2026, 2025 prices.
NESO_PRICE_YEAR = 2025
NESO_CAPEX_2026_GBP_PER_KW = {1: 298.35, 2: 547.26, 4: 920.18, 6: 1264.71, 9: 1812.719849}
NESO_OPEX_GBP_PER_KW_YEAR = {1: 6.203703703703703, 2: 8.685185185185185, 4: 12.407407407407407,
                             6: 13.648148148148147, 9: 16.12962962962963}
# The line is fitted through 2-9 hours, the durations the optimiser builds: there it
# is within 1 % of every row. NESO's 1-hour system is a cheaper, power-led product
# the line overprices by about a quarter; nothing the model builds is that short.
NESO_FIT_HOURS = (2, 4, 6, 9)
# North Norfolk's least-cost design builds 18 hours. No UK figure read goes past 12.
# The one source read that does, PNNL's 2022 assessment, Figure 4.3 (LFP, 10 MW, 2030,
# total installed), says the line holds: fitted through 2 to 10 hours it lands within
# 1 % at 18 and 1.3 % at 24. A check on the shape only, never charged: its level is
# older and higher. The longest lithium projects found are 8 to 11.5 hours, so
# sensitivity.ASSUMPTION_KNOBS also runs the design capped at 9.
PNNL_LFP_10MW_2030_USD_PER_KW = {2: 707.0, 4: 1244.0, 10: 2828.0, 24: 6456.0}


def _finance_factor(rate: float, years: int) -> float:
    """Capital at the end of the build per £1 spent evenly over it (tech_costs's)."""
    from optimisation.tech_costs import building_finance_factor
    return building_finance_factor(rate, years)


def _fit_power_energy(rows: dict[int, float]) -> tuple[float, float]:
    """(per kW, per kWh) of the straight line through a figure by duration: a
    1-hour system is 1 kWh per kW, so the slope is per kWh. The capital fit is
    within 2 % of every row."""
    slope, intercept = np.polyfit(list(rows), list(rows.values()), 1)
    return float(intercept), float(slope)


# Low case: Modo Energy's GB model, ~400 GBP/kW at 1 hour, real 2025, for the
# 1-hour system, and Ember's all-in $125/kWh (October 2025, projects of 4 hours
# and more outside China and the United States) for each further hour. Until
# 4 Nov 2026 the further hour was £100/kW, a figure not on Modo's page.
MODO_1H_GBP_PER_KW = 400.0
EMBER_ALL_IN_USD_PER_KWH = 125.0
EMBER_PRICE_YEAR = 2025

# High case: the US Annual Technology Baseline 2025 (moderate, 2026), all-in and
# carrying US sales tax, 2023 dollars, 2 to 10 hours, fitted the same way as
# BEIS and inflated in dollars.
ATB_PRICE_YEAR = 2023
ATB_2026_USD_PER_KW = {2: 907.617750, 4: 1344.455703, 6: 1781.293657, 8: 2218.131610, 10: 2654.969563}

# CEPA for DESNZ (2025), Table E.1: lithium batteries 8.90 %, pre-tax real.
# Was Modo's 5.0 % real until 4 Nov 2026 (evening).
WACC_REAL = 0.089
BUILD_YEARS = 1              # NESO FES 2025 E.02 (and BEIS 2022): build time 1 year at every duration
ASSET_LIFE_YEARS = 15        # Modo: BESS asset lifetime

# =============================================================================
# Technical — Modo
# =============================================================================
WARRANTED_CYCLES = 10_000          # to the repowering threshold
CAPACITY_AT_END_OF_LIFE = 0.67     # ~67 % remaining after those cycles
# Standing loss per hour of storage held: self-discharge only, on the energy stored.
#
# Mott MacDonald for BEIS, "Storage cost and technical assumptions" (8 Aug 2018),
# Table 5, p. 44, and all its lithium tables: 1,560 hours before capacity falls below
# 80 % by self-discharge. The model's stock falls by this fraction each hour, so the
# rate is the one that reaches 80 % in that time: 0.0143 % an hour, 0.34 % a day. It
# was zero and assumed until 5 Nov 2026. Modo's 88 % is a round-trip number: if it
# holds any loss over the hours between charge and discharge, the overlap is about
# 0.06 % of a four-hour hold.
#
# The auxiliary load that keeps a containerised system alive, BMS and above all the
# HVAC, is a different thing: it runs on installed size and has no term of its own,
# and no source here gives a lithium figure. Modo's definition may put part of it in
# the 88 %, spread per cycle (docs/OBJECTIVE_AUDIT.md). See DATA_GAPS.md.
SELF_DISCHARGE_HOURS_TO_80_PCT = 1560.0
STANDING_LOSS_PER_HOUR = -math.log(0.8) / SELF_DISCHARGE_HOURS_TO_80_PCT
STANDING_LOSS_IS_ASSUMED = False

ROUND_TRIP_EFFICIENCY = 0.88       # Modo standard; least firmly sourced here
CYCLES_PER_DAY = (1.0, 2.0)        # configurable, warranty-aligned

# =============================================================================
# Embodied carbon — IPCC 2021 GWP100
# =============================================================================
# Two bases for the ENERGY term. The power term is the same in both.
#
# "jasper_voss_2026"  (default) a grid battery: Jasper et al.'s liquid-cooled
#     LFP container — cells, modules, racks, container, liquid cooling, fire
#     suppression — around Voß et al.'s LFP cell, made in China, built on
#     ecoinvent 3.9.1 by optimiser_lca/bess.py. Per kWh of NAMEPLATE cells.
# "ecoinvent_ev_pack" the basis before 14 Oct 2026, kept only to reproduce old
#     runs: ecoinvent's EV traction pack (Dai et al. / GREET, 116 Wh/kg) with
#     no container, racking, HVAC or fire suppression, charged per kWh of
#     cap_batt_e with no usable-fraction correction. It ran low on two counts
#     that partly hid each other behind a cell figure that ran high per kg.
EMBODIED_BASES = ("jasper_voss_2026", "ecoinvent_ev_pack")
EMBODIED_BASIS = "jasper_voss_2026"
if EMBODIED_BASIS not in EMBODIED_BASES:
    raise ValueError(f"EMBODIED_BASIS must be one of {EMBODIED_BASES}")

# The foreground activity is optimiser_lca/bess.py's ``registry.BESS_DC_BLOCK_KWH``;
# everything about what the battery is made of lives there, and this module
# only scores and amortises it.
#
# Scored once and pinned so this module runs without Brightway;
# check_against_ecoinvent() re-scores it and fails if it has moved.
BESS_KGCO2E_PER_KWH_NAMEPLATE = 103.515   # 26 Oct 2026: HFC credit dropped; cell factory gas on Voß's Chinese dataset; FePO4 per kg (was 101.237)

# Share of nameplate cell capacity the battery is allowed to swing. ASSUMED.
# Both sources report per kWh of cells; the LP's cap_batt_e is the energy
# between the state-of-charge limits (soc runs 0..cap_batt_e in dc_model), and
# Modo's costs are per usable kWh too, so carbon is grossed up to the cells a
# usable kWh needs. 0.90 is commercial operating practice; Jasper assume 80 %
# depth of discharge in their use phase, which would add a further 12.5 %.
USABLE_FRACTION = 0.90

# The cell is the soft spot of the energy term (~81 % of it). Pinned per kWh
# of cells, so a sensitivity swaps the cell and keeps everything around it:
#   voss_cn          Voß 2025 cell, made in China — the default, inside
#                    BESS_KGCO2E_PER_KWH_NAMEPLATE
#   voss_de          the same cell from Voß's own German gigafactory
#   jasper_fig4_311  Jasper 2026 Fig 4 "cells" for the liquid-cooled LFP
#                    system, re-scored on ecoinvent 3.11 cut-off at EF 3.1
#                    with transport: a cross-version comparison, not a
#                    like-for-like inventory
# Scored 22 Oct 2026 on ecoinvent 3.9.1 apos (optimiser_lca/bess.py), after
# upstream transport was put back (Jasper's material legs; Voß's in-China leg
# on every cell material, the natural graphite included) and Jasper's concrete
# block restored.
CELL_KGCO2E_PER_KWH = {"voss_cn": 82.920, "voss_de": 74.933, "jasper_fig4_311": 95.44}   # 26 Oct 2026 (was 80.711 / 73.677): see SOURCES.md
CELL_BASIS = "voss_cn"

# --- the legacy EV-pack basis -------------------------------------------------
# ecoinvent's LFP dataset documents a 203 kg pack holding 23.5 kWh gross, and
# its own price comment independently cites 0.115 kWh/kg. The cell figure
# (0.159 kWh/kg x 0.727 kg cell per kg pack = 0.1156) agrees to 0.2 %.
PACK_KWH_PER_KG = 23.5 / 203.0
BATTERY_ACTIVITY = ("market for battery, Li-ion, LFP, rechargeable, prismatic", "GLO")
PACK_KGCO2E_PER_KG = 11.368
# No stationary enclosure in that dataset. 0.0 reproduces the old runs, which
# is all this basis is now for; the default basis carries the enclosure itself.
CONTAINER_UPLIFT_FRACTION = 0.0

# --- the power term, both bases -------------------------------------------------
PCS_ACTIVITY = ("market for inverter, 500kW", "GLO")
PCS_RATED_KW = 500.0
PCS_KGCO2E_PER_UNIT = 15_930.86

LCA_CAVEATS = {
    "jasper_voss_2026": ("Jasper 2026 liquid-cooled LFP container + Voß 2025 cell, made in "
                         "China, on ecoinvent 3.9.1; excludes the PCS (power term) and the container "
                         "transformer (transformers.py, since 15 Oct), delivery to site and end-of-life; "
                         "Jasper's concrete block is in since 21 Oct"),
    "ecoinvent_ev_pack": ("ecoinvent LFP pack is an EV traction pack (Dai et al./GREET), "
                          "reused for stationary storage; no container/HVAC/racking"),
}
LCA_CAVEAT = LCA_CAVEATS[EMBODIED_BASIS]


def capital_recovery_factor(rate, lifetime_years):
    rate, lifetime_years = float(rate), float(lifetime_years)
    if lifetime_years <= 0:
        raise ValueError("lifetime_years must be positive")
    if rate == 0:
        return 1.0 / lifetime_years
    return rate * (1.0 + rate) ** lifetime_years / ((1.0 + rate) ** lifetime_years - 1.0)


def cost_components():
    """Capex, power (GBP/kW) and energy (GBP/kWh), and fixed running cost per each
    (GBP per year), by case, in 2025 pounds. Running cost is NESO's in every case."""
    inflate = P.factor(NESO_PRICE_YEAR)
    fit = lambda d: _fit_power_energy({h: d[h] for h in NESO_FIT_HOURS})   # noqa: E731
    power, energy = (v * inflate for v in fit(NESO_CAPEX_2026_GBP_PER_KW))
    run_power, run_energy = (v * inflate for v in fit(NESO_OPEX_GBP_PER_KW_YEAR))
    ember = P.usd_to_gbp_2025(EMBER_ALL_IN_USD_PER_KWH, EMBER_PRICE_YEAR)
    atb_power, atb_energy = (P.usd_to_gbp_2025(v, ATB_PRICE_YEAR) for v in _fit_power_energy(ATB_2026_USD_PER_KW))
    capex = {"low": (MODO_1H_GBP_PER_KW - ember, ember),
             "central": (power, energy),
             "high": (atb_power, atb_energy)}
    return {c: {"power_GBP_per_kW": capex[c][0], "energy_GBP_per_kWh": capex[c][1],
                "fixed_opex_GBP_per_kW_year": run_power, "fixed_opex_GBP_per_kWh_year": run_energy}
            for c in CASES}


# Insurance (12 Nov 2026): NESO's running cost (BEIS 2022) does not say it carries
# it, so it is added at the ratio DESNZ/Arup give onshore wind (£3.6k/MW/yr on
# £1,588/kW), as the fuel cell does (h2_capex). Estimate: cost_exclusions.py.
INSURANCE_FRAC_OF_CAPITAL = 3.6 / 1_588.0


def annual_costs(case: str) -> dict:
    """The battery's two LP cost coefficients in one case, £/MW/y (power) and
    £/MWh/y (energy): capital times the CRF at Modo's WACC over the life, plus
    the fixed running cost. Each number recorded for the cost map (``trace.cost``)."""
    sheet = [("neso_fes2025_economics_inputs", "sheet E.03, battery storage 1-9 hr, build year 2026")]
    modo = [("modo_bess_assumptions", "GB model assumptions, capital cost")]
    T.cost("cost.battery.neso_capex_by_duration", NESO_CAPEX_2026_GBP_PER_KW[6], "GBP per kW",
           "Capital of a 6-hour system built in 2026 (2025 prices); the line runs through 2-9 hours",
           grade="transcribed",
           cites=sheet, inputs={f"{h} h": v for h, v in NESO_CAPEX_2026_GBP_PER_KW.items()})
    T.cost("cost.battery.neso_opex_by_duration", NESO_OPEX_GBP_PER_KW_YEAR[6], "GBP per kW per year",
           "Running cost of a 6-hour system (2025 prices)", grade="transcribed", cites=sheet,
           inputs={f"{h} h": v for h, v in NESO_OPEX_GBP_PER_KW_YEAR.items()},
           note="NESO's own source for running cost is BEIS 2022, inflated")
    capex_uses = ["cost.battery.neso_capex_by_duration"]
    if case == "low":
        T.cost("cost.battery.modo_1h_per_kW", MODO_1H_GBP_PER_KW, "GBP per kW", "A 1-hour system's capital",
               grade="transcribed", cites=modo)
        T.cost("cost.battery.ember_all_in_USD_per_kWh", EMBER_ALL_IN_USD_PER_KWH, "US $ per kWh",
               "All-in capital of a 4-hour-plus project outside China and the US, October 2025", grade="transcribed",
               cites=[("ember_bess_2025", "about $125/kWh: $75 equipment, $50 install and connect")],
               note="Each further hour of duration in the low case; assumes cheap land")
        P.record_fx()
        capex_uses = ["cost.battery.modo_1h_per_kW", "cost.battery.ember_all_in_USD_per_kWh",
                      P.record_foreign("usd", EMBER_PRICE_YEAR), "fx.usd_per_gbp_2025"]
    elif case == "high":
        T.cost("cost.battery.atb_capex_by_duration", ATB_2026_USD_PER_KW[4], "US $ per kW",
               "A 4-hour system's all-in capital, 2026 moderate, 2023 dollars", grade="transcribed",
               cites=[("nrel_atb_2025", "utility-scale battery, moderate, 2026, total capital")],
               inputs={f"{h} h": v for h, v in ATB_2026_USD_PER_KW.items()})
        P.record_fx()
        capex_uses = ["cost.battery.atb_capex_by_duration", P.record_foreign("usd", ATB_PRICE_YEAR),
                      "fx.usd_per_gbp_2025"]
    c = cost_components()[case]
    power = T.cost("cost.battery.power_per_kW", c["power_GBP_per_kW"], "GBP per kW",
                   "Power conversion capital: the fit's intercept against duration", uses=capex_uses)
    energy = T.cost("cost.battery.energy_per_kWh", c["energy_GBP_per_kWh"], "GBP per kWh",
                    "Energy capital: the fit's slope against duration", uses=capex_uses,
                    cites=[("pnnl_esgc_2022", "Figure 4.3, LFP at 2, 4, 10 and 24 hours: the line holds past the fit's range"),
                           ("lcp_delta_long_bess_2025", "p. 30: each added two hours costs the same")],
                    note="Beyond the source's range at long durations: an extension, checked for shape, not a quote")
    run_uses = ["cost.battery.neso_opex_by_duration"]
    run_power = T.cost("cost.battery.fixed_opex_per_kW_year", c["fixed_opex_GBP_per_kW_year"], "GBP per kW per year",
                       "Fixed running cost, power: the fit's intercept against duration", uses=run_uses)
    run_energy = T.cost("cost.battery.fixed_opex_per_kWh_year", c["fixed_opex_GBP_per_kWh_year"], "GBP per kWh per year",
                        "Fixed running cost, energy: the fit's slope against duration", uses=run_uses)
    wacc = T.cost("cost.battery.wacc", WACC_REAL, "fraction per year", "CEPA's hurdle rate for lithium batteries",
                  grade="transcribed", cites=[("cepa_hurdle_rates_2025", "Table E.1, lithium batteries, 8.90 %")])
    build = T.cost("cost.battery.construction_years", BUILD_YEARS, "years", "Build time", grade="transcribed",
                   cites=[("neso_fes2025_economics_inputs", "sheet E.02, battery 1-9 hr, build time 1 year")])
    finance = T.cost("cost.battery.building_finance_factor", _finance_factor(wacc, build), "multiplier",
                     "Capital carried at the rate over the build", uses=["cost.battery.wacc",
                                                                         "cost.battery.construction_years"])
    life = T.cost("cost.battery.life_years", ASSET_LIFE_YEARS, "years", "Battery financial life",
                  grade="transcribed", cites=[("neso_fes2025_economics_inputs", "sheet E.02, battery 1-9 hr, "
                                                                                "15-year life"),
                                              ("beis_ldes_2022", "Exhibit 3.11, financial lifetime 15 years")],
                  note="Modo's October 2026 assumptions say 20 years; the system operator and BEIS say 15")
    crf = T.cost("cost.battery.crf", capital_recovery_factor(wacc, life), "per year",
                 "Capital recovery factor at the WACC over the life",
                 uses=["cost.battery.wacc", "cost.battery.life_years"])
    ins = T.cost("cost.battery.insurance_frac", INSURANCE_FRAC_OF_CAPITAL, "fraction of capital per year",
                 "Insurance, at onshore wind's ratio to capital: an estimate that fails the 1 % test if left out",
                 grade="proxy", cites=[("desnz_arup_2024_onshore_solar", "Table 3, insurance over total capex, central")])
    return {"power_GBP_per_MW_year": (power * finance * crf + run_power + power * ins) * 1000.0,
            "energy_GBP_per_MWh_year": (energy * finance * crf + run_energy + energy * ins) * 1000.0,
            "power_GBP_per_kW": power, "energy_GBP_per_kWh": energy, "crf": crf, "finance": finance}


def system_capex_gbp_per_kw(duration_h, case="central"):
    """Total capex of a system of a given duration, GBP per kW of power."""
    c = cost_components()[case]
    return c["power_GBP_per_kW"] + c["energy_GBP_per_kWh"] * float(duration_h)


def lifetime_throughput_mwh_per_mwh():
    """MWh discharged over life, per MWh of installed capacity.

    Capacity fades linearly from 100 % to CAPACITY_AT_END_OF_LIFE across the
    warranted cycles, so the mean capacity over life is the average of the two.
    Modo quote capacity as AC useable at the point of connection, so depth of
    discharge is already inside the rating and is not applied again.
    """
    mean_capacity = (1.0 + CAPACITY_AT_END_OF_LIFE) / 2.0
    return WARRANTED_CYCLES * mean_capacity


# =============================================================================
# Ageing: sized to end of life (12 Nov 2026, user)
# =============================================================================
# The LP's cap_batt_e is the energy the plant needs in every hour of every year,
# so the battery is bought big enough to still hold it in year 15. That is BEIS's
# own convention: Mott MacDonald for BEIS (2018, summary table p. 7) give
# lithium-ion 15 years, "dependent on the energy capacity installed at the start
# of the project (overplanting at project start to account for degradation can
# extend life)". They give no fade rate.
#
# Fade over life = time + use. Modo's warranted line (67 % after 10,000 cycles,
# ~12-15 years at 1-2 cycles a day) holds both; the calendar part is taken out of
# it over Modo's own span so it is not counted twice, and the rest is spread per
# cycle. The calendar rate is ASSUMED: no UK government figure; published LFP
# measurements and fleet data run about 1-2 % a year at moderate temperature
# (DATA_GAPS.md). Tested at x0.5 / x1.5 on the whole fade (SHAKY_KNOBS).
CALENDAR_FADE_PER_YEAR = 0.01            # ASSUMED, fraction of rated capacity lost per year
MODO_WARRANTY_SPAN_YEARS = 13.5          # Modo: "~12-15 years" for the 10,000 cycles
# Full cycles a year the saved North Norfolk run gives the battery (11 Nov 2026,
# re-solve of the pre-tank reference run): 161 at lowest cost, 205 at lowest
# carbon. Fixed here, not solved for; check it against each new run.
CYCLES_PER_YEAR_IN_USE = 180.0


def capacity_fade_at_end_of_life(calendar_fade_per_year: float | None = None,
                                 cycles_per_year: float | None = None) -> float:
    """Share of rated energy lost by the end of ``ASSET_LIFE_YEARS``: the calendar
    rate over the life, plus Modo's per-cycle fade net of its own calendar part
    times the cycles the battery does. Recorded as a traced step so a sweep can
    push it (``battery.capacity_fade_at_end_of_life``)."""
    cal = CALENDAR_FADE_PER_YEAR if calendar_fade_per_year is None else float(calendar_fade_per_year)
    cyc_yr = CYCLES_PER_YEAR_IN_USE if cycles_per_year is None else float(cycles_per_year)
    warranted_fade = 1.0 - CAPACITY_AT_END_OF_LIFE
    per_cycle = (warranted_fade - cal * MODO_WARRANTY_SPAN_YEARS) / WARRANTED_CYCLES
    if per_cycle < 0:
        raise ValueError(f"calendar fade {cal:.3%}/yr exceeds Modo's whole warranted fade over "
                         f"{MODO_WARRANTY_SPAN_YEARS} years")
    fade = cal * ASSET_LIFE_YEARS + per_cycle * cyc_yr * ASSET_LIFE_YEARS
    fade = T.step("battery.capacity_fade_at_end_of_life", fade, "fraction of rated energy",
                  "Battery energy lost by the end of its 15-year life: time plus use",
                  grade="assumed",
                  inputs={"calendar_fade_per_year": cal, "asset_life_years": ASSET_LIFE_YEARS,
                          "cycles_per_year": cyc_yr, "warranted_cycles": WARRANTED_CYCLES,
                          "capacity_at_end_of_warranty": CAPACITY_AT_END_OF_LIFE,
                          "warranty_span_years": MODO_WARRANTY_SPAN_YEARS},
                  cites=[("modo_bess_assumptions", "~67 % after 10,000 cycles, ~12-15 years"),
                         ("mott_macdonald_storage_2018", "summary table p. 7: 15 years with overplanting")],
                  note="Calendar rate assumed (about 1-2 %/yr in LFP measurements); cycles from the saved run")
    if not 0.0 <= fade < 0.9:
        raise ValueError(f"battery fade at end of life {fade!r} is outside [0, 0.9)")
    return fade


def end_of_life_oversize(calendar_fade_per_year: float | None = None,
                         cycles_per_year: float | None = None) -> float:
    """Rated energy bought per MWh the plant needs in year 15: 1 / (1 - fade).
    Multiplies the battery's energy cost and carbon, not its power."""
    fade = capacity_fade_at_end_of_life(calendar_fade_per_year, cycles_per_year)
    return T.step("battery.end_of_life_oversize", 1.0 / (1.0 - fade), "MWh rated per MWh needed",
                  "Battery energy bought so it still holds what is needed at end of life",
                  uses=["battery.capacity_fade_at_end_of_life"])


def embodied_components(basis: str | None = None, usable_fraction: float | None = None,
                        cell_basis: str | None = None):
    """Embodied carbon split the same way as cost: per kW and per usable kWh.

    ``usable_fraction`` overrides ``USABLE_FRACTION`` (ASSUMED) for a sweep; it
    applies to the default basis only, whose inventory is per nameplate kWh.
    """
    basis = basis or EMBODIED_BASIS
    usable = USABLE_FRACTION if usable_fraction is None else float(usable_fraction)
    if not 0.5 <= usable <= 1.0:
        raise ValueError(f"usable_fraction must be in [0.5, 1.0], got {usable!r}")
    cell = cell_basis or CELL_BASIS
    if cell not in CELL_KGCO2E_PER_KWH:
        raise ValueError(f"cell_basis must be one of {list(CELL_KGCO2E_PER_KWH)}, got {cell!r}")
    if basis == "jasper_voss_2026":
        from optimiser_lca.registry import BESS_DB, BESS_DC_BLOCK_KWH
        block = T.activity(BESS_DB, BESS_DC_BLOCK_KWH)
        T.step("battery.dc_block_per_kWh", BESS_KGCO2E_PER_KWH_NAMEPLATE, "kg CO2e per kWh of cells",
               "The DC block built: Jasper 2026's liquid-cooled LFP container around Voß 2025's "
               "cell, per nameplate kWh", uses=[block], scores=block, grade="derived",
               source=LCA_CAVEATS["jasper_voss_2026"],
               note="Pinned so this module runs without Brightway; check_against_ecoinvent() "
                    "rescores it and fails if it has moved.")
        nameplate = T.step("battery.nameplate_per_kWh",
                           (BESS_KGCO2E_PER_KWH_NAMEPLATE - CELL_KGCO2E_PER_KWH[CELL_BASIS]
                            + CELL_KGCO2E_PER_KWH[cell]),
                           "kg CO2e per kWh of cells",
                           f"The block with its cell on the {cell!r} basis",
                           uses=["battery.dc_block_per_kWh"],
                           inputs={"cell_basis": cell,
                                   "pinned_cell": CELL_KGCO2E_PER_KWH[CELL_BASIS],
                                   "this_cell": CELL_KGCO2E_PER_KWH[cell]},
                           grade="derived")
        energy = T.step("battery.energy_per_usable_kWh", nameplate / usable,
                        "kg CO2e per usable kWh",
                        "Grossed up to the cells one usable kWh needs",
                        uses=["battery.nameplate_per_kWh"], inputs={"usable_fraction": usable},
                        grade="assumed",
                        note="cap_batt_e is the energy between the state-of-charge limits; "
                             "0.90 is commercial operating practice (ASSUMED).")
    elif basis == "ecoinvent_ev_pack":
        kg_per_kwh = 1.0 / PACK_KWH_PER_KG
        energy = T.step("battery.energy_per_usable_kWh",
                        kg_per_kwh * PACK_KGCO2E_PER_KG * (1.0 + CONTAINER_UPLIFT_FRACTION),
                        "kg CO2e per kWh", "ecoinvent's EV traction pack, per kWh (legacy basis)",
                        uses=[T.ecoinvent(*BATTERY_ACTIVITY)], grade="transcribed",
                        inputs={"pack_kWh_per_kg": PACK_KWH_PER_KG})
    else:
        raise ValueError(f"basis must be one of {EMBODIED_BASES}, got {basis!r}")
    pcs = T.ecoinvent(*PCS_ACTIVITY)
    T.step("battery.pcs_per_unit", PCS_KGCO2E_PER_UNIT, "kg CO2e per 500 kW inverter",
           "Power conversion: ecoinvent's 500 kW inverter", uses=[pcs], scores=pcs,
           grade="transcribed")
    power = T.step("battery.pcs_per_kW", PCS_KGCO2E_PER_UNIT / PCS_RATED_KW, "kg CO2e per kW",
                   "The inverter per kW of its rating", uses=["battery.pcs_per_unit"],
                   inputs={"rated_kW": PCS_RATED_KW}, grade="derived")
    return {"energy_kgco2e_per_kWh": energy, "power_kgco2e_per_kW": power}


def builds_over_horizon(horizon_years):
    """How many battery builds a longer-lived host asset needs.

    The data centre runs 25 years; the battery lasts 15. Ignoring this would
    silently give the battery a 25-year life it does not have.
    """
    return float(horizon_years) / float(ASSET_LIFE_YEARS)


def cost_table(durations=(1, 2, 4, 8)):
    rows = []
    crf = capital_recovery_factor(WACC_REAL, ASSET_LIFE_YEARS) * _finance_factor(WACC_REAL, BUILD_YEARS)
    for case in CASES:
        comp = cost_components()[case]
        for d in durations:
            capex_kw = system_capex_gbp_per_kw(d, case)
            opex_kw = comp["fixed_opex_GBP_per_kW_year"] + comp["fixed_opex_GBP_per_kWh_year"] * d
            rows.append({
                "case": case, "duration_h": d,
                "capex_GBP_per_kW": round(capex_kw, 1),
                "capex_GBP_per_kWh": round(capex_kw / d, 1),
                "capex_GBP_per_MW": round(capex_kw * 1000, 0),
                "power_component_GBP_per_kW": round(comp["power_GBP_per_kW"], 1),
                "energy_component_GBP_per_kWh": round(comp["energy_GBP_per_kWh"], 1),
                "fixed_opex_GBP_per_kW_year": round(opex_kw, 2),
                "crf": round(crf, 5),
                "annualised_capex_GBP_per_kW_year": round(capex_kw * crf, 2),
                "total_annual_GBP_per_kW_year": round(capex_kw * crf + opex_kw, 2),
            })
    return pd.DataFrame(rows)


def carbon_table(durations=(1, 2, 4, 8)):
    emb = embodied_components()
    thr = lifetime_throughput_mwh_per_mwh()
    rows = []
    for d in durations:
        per_kw = emb["power_kgco2e_per_kW"] + emb["energy_kgco2e_per_kWh"] * d
        per_kwh = per_kw / d
        rows.append({
            "duration_h": d,
            "embodied_kgco2e_per_kW": round(per_kw, 1),
            "embodied_kgco2e_per_kWh": round(per_kwh, 1),
            "embodied_tco2e_per_MW": round(per_kw, 1),
            "lifetime_throughput_MWh_per_MWh": round(thr, 0),
            "embodied_kgco2e_per_MWh_throughput": round(per_kwh * 1000 / thr, 2),
        })
    return pd.DataFrame(rows)


def check_against_ecoinvent():
    """Re-score the pinned ecoinvent factors and fail if they have drifted."""
    try:
        import sys
        sys.path.insert(0, str(ROOT))
        import bw2data as bd
        import lca_helpers as H
        from optimiser_lca.registry import BESS_DB, BESS_DC_BLOCK_KWH
        ei, _bio, _fg, _m = H.setup_brightway()
        method = next(m for m in bd.methods if m[1] == "IPCC 2021"
                      and m[2] == "climate change" and "GWP100" in str(m)
                      and "no LT" not in str(m))
    except Exception as e:
        return f"skipped — Brightway unavailable ({type(e).__name__})"

    problems = []
    for (name, loc), pinned, label in (
            (BATTERY_ACTIVITY, PACK_KGCO2E_PER_KG, "LFP pack (legacy basis)"),
            (PCS_ACTIVITY, PCS_KGCO2E_PER_UNIT, "inverter 500kW")):
        hits = [a for a in ei if a["name"] == name and a["location"] == loc]
        if not hits:
            problems.append(f"{label}: activity not found")
            continue
        got = H.run_lca_score(hits[0], method)
        if abs(got - pinned) / pinned > 0.001:
            problems.append(f"{label}: ecoinvent={got:.3f} pinned={pinned:.3f}")
    try:
        act = bd.get_activity((BESS_DB, BESS_DC_BLOCK_KWH))
    except Exception:
        problems.append(f"{BESS_DB!r}/{BESS_DC_BLOCK_KWH!r} is not built — run "
                        "`python -m optimiser_lca.build bess`")
    else:
        got = H.run_lca_score(act, method)
        if abs(got - BESS_KGCO2E_PER_KWH_NAMEPLATE) / BESS_KGCO2E_PER_KWH_NAMEPLATE > 0.001:
            problems.append(f"battery foreground: scored={got:.3f} "
                            f"pinned={BESS_KGCO2E_PER_KWH_NAMEPLATE:.3f}")
    if problems:
        raise AssertionError("battery factors are stale:\n  " + "\n  ".join(problems))
    return "OK — the battery foreground and 2 ecoinvent factors match their pinned values"


def run():
    print("=" * 92)
    print("BATTERY STORAGE — Li-ion LFP, real 2025 GBP and IPCC 2021 GWP100")
    print("=" * 92)
    print(check_against_ecoinvent())

    comp = cost_components()
    emb = embodied_components()
    print()
    print("Two-part structure (power and energy sized independently)")
    print("-" * 92)
    print(f"{'':<22}{'low':>14}{'central':>14}{'high':>14}")
    print(f"{'capex, power':<22}" + "".join(
        f"{comp[c]['power_GBP_per_kW']:>13.0f} " for c in CASES) + " GBP/kW")
    print(f"{'capex, energy':<22}" + "".join(
        f"{comp[c]['energy_GBP_per_kWh']:>13.0f} " for c in CASES) + " GBP/kWh")
    print(f"{'embodied, power':<22}{emb['power_kgco2e_per_kW']:>13.1f} "
          f"{'(no case spread)':>28}  kg CO2e/kW")
    print(f"{'embodied, energy':<22}{emb['energy_kgco2e_per_kWh']:>13.1f} "
          f"{'':>28}  kg CO2e/kWh")

    print()
    print(f"WACC {WACC_REAL:.1%} real | life {ASSET_LIFE_YEARS} y | "
          f"CRF {capital_recovery_factor(WACC_REAL, ASSET_LIFE_YEARS):.4f} | "
          f"RTE {ROUND_TRIP_EFFICIENCY:.0%}")
    print(f"{WARRANTED_CYCLES:,} cycles to {CAPACITY_AT_END_OF_LIFE:.0%} capacity "
          f"-> {lifetime_throughput_mwh_per_mwh():,.0f} MWh out per MWh installed")

    ct, kt = cost_table(), carbon_table()
    print()
    print("By duration")
    print("-" * 92)
    print(f"{'dur':>5}{'capex k/MW':>13}{'£/kWh':>9}{'ann. £/kW/y':>14}"
          f"{'embodied t/MW':>16}{'kg/MWh cycled':>16}")
    for d in (1, 2, 4, 8):
        c = ct[(ct.case == "central") & (ct.duration_h == d)].iloc[0]
        k = kt[kt.duration_h == d].iloc[0]
        print(f"{d:>4}h{c.capex_GBP_per_MW/1000:>13,.0f}{c.capex_GBP_per_kWh:>9.0f}"
              f"{c.total_annual_GBP_per_kW_year:>14,.0f}"
              f"{k.embodied_tco2e_per_MW:>16,.0f}"
              f"{k.embodied_kgco2e_per_MWh_throughput:>16.1f}")

    print()
    print("Cross-checks and caveats")
    print("-" * 92)
    survey_19h = system_capex_gbp_per_kw(1.9, "central")
    print(f"  BEIS 2022 fit at 1.9 h: {survey_19h:,.0f} GBP/kW vs Modo's 2024")
    print(f"  survey average of 580 GBP/kW at the same duration.")
    print(f"  Two-hour: model {system_capex_gbp_per_kw(2,'central'):,.0f} vs survey median 650 GBP/kW.")
    print(f"  Central is a 2022 forecast of 2030 capital; the low case is Modo's 1-hour figure "
          f"+ Ember's ${EMBER_ALL_IN_USD_PER_KWH:,.0f}/kWh an hour; the high the US technology baseline.")
    print(f"  Battery life {ASSET_LIFE_YEARS} y vs data centre 25 y -> "
          f"{builds_over_horizon(25):.2f} builds over the DC's life,")
    print(f"  which both cost and carbon must carry.")
    print(f"  LCA ({EMBODIED_BASIS}): {LCA_CAVEAT}.")
    if EMBODIED_BASIS == "jasper_voss_2026":
        legacy = embodied_components("ecoinvent_ev_pack")["energy_kgco2e_per_kWh"]
        print(f"  Energy term {BESS_KGCO2E_PER_KWH_NAMEPLATE:.1f} kg CO2e per nameplate kWh / "
              f"{USABLE_FRACTION:.2f} usable = {emb['energy_kgco2e_per_kWh']:.1f} per usable kWh,")
        print(f"  against {legacy:.1f} on the legacy EV-pack basis.")

    OUT_DIR.mkdir(exist_ok=True)
    ct.to_csv(OUT_DIR / "battery_costs.csv", index=False)
    kt.to_csv(OUT_DIR / "battery_carbon.csv", index=False)
    print()
    print("Wrote: optimisation_outputs/battery_costs.csv, battery_carbon.csv")
    return ct, kt


if __name__ == "__main__":
    run()
