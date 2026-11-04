"""
Hydrogen-chain asset costs.
=============================================================================

What a stationary fuel cell costs per kW, what a hydrogen vessel costs per kg of
capacity, and what an SOEC electrolyser costs, from UK government documents
since 4 Nov 2026 (COST_GOV_FIGURES_PLAN.md). Each is thin evidence, stated below.

Read the caveats before quoting any hydrogen cost result
--------------------------------------------------------

**Fuel cell.** Baringa for DESNZ (Dec 2025) calls its own evidence limited: a
floor for a grid-scale system, and one real plant, each with about £485/kW of
purification for pipeline hydrogen. This study's hydrogen is made on site or
delivered as pure trailer gas, so the purification comes off in low and central
and stays in high. Neither figure carries a stack share or a life:
``FC_STACK_COST_FRACTION`` is read off Element Energy's chart (45 %), the top of
the non-government range.

**Hydrogen vessel.** Element Energy for BEIS (2018) rests on one supplier's quote
for a 95 m³ vessel at 50-80 bar, taken as 2017 pounds, installed; a vessel at
this study's 28 bar holds less but has a thinner wall. It is not the vessel the
carbon side inventories (Gandiglio's small stainless buffer, 313 kg of steel per
kg of hydrogen): a stated mismatch. There is no UK range, so the low and high
cases are not government figures.

**SOEC.** BEIS's 2021 annex assumes a mature plant. Its level is dated (its PEM
is a third of NESO's 2025 figure), so the central case is its ratio to PEM on
NESO's PEM, which lands above every non-government range read; the low case is
its level as printed. Treat cost-optimal SOEC with care: the bracket is 3x.

Run the cost case as a sensitivity, not as a scenario label — if a conclusion
flips between low and high, it is not a conclusion.

Currency
--------
Real 2025 GBP: ``price_base`` for pounds of another year, the FES 2025 cross-rate
for the two figures in euros.

Sources
-------
fuel cell     Baringa Partners for DESNZ, *Hydrogen to Power Costs and Barriers*
              (9 Dec 2025), §4.4 and §5, capital. Element Energy for BEIS,
              *Hydrogen supply chain evidence base* (Nov 2018), p. 94,
              maintenance at 1.4 MWe.
H2 vessel     Element Energy, p. 109, central. Rozzi et al. 2024 dataset
              (30 bar, 50 t), low; the older literature's EUR 1,040/kg, high.
              Element Energy p. 112, running cost; p. 110, footprint.
SOEC          BEIS, *Hydrogen Production Costs 2021*, annex, sheet "Technical
              and cost assumptions", commissioning 2025, on NESO's PEM capex in
              `price_outputs/electrolyser_costs_clean.csv`.

Run:  python optimisation/h2_capex.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from optimisation import price_base as P  # noqa: E402
from optimisation import tech_costs as tc  # noqa: E402
from optimisation import trace as T  # noqa: E402

PRICE_DIR = ROOT / "price_outputs"
OUT_DIR = ROOT / "optimisation_outputs"

CASES = ("low", "central", "high")

# FES 2025 Data Workbook cross-rate, as h2_prices.py uses (price_base holds it).
EUR_PER_GBP_2025 = P.EUR_PER_GBP_2025

# Hydrogen's higher heating value, to turn NESO's per-kWh-HHV variable opex into
# per kg. 39.4 kWh/kg is the standard figure (141.8 MJ/kg).
H2_HHV_KWH_PER_KG = 39.4

# Element Energy's report: "the majority of the assumptions were collated in 2017".
ELEMENT_ENERGY_PRICE_YEAR = 2017

# -----------------------------------------------------------------------------
# Fuel cell
# -----------------------------------------------------------------------------
# Baringa for DESNZ, 2025 pounds, installed. The report's "exceed £2,500/kW" is a
# floor for a pipeline-fed grid-scale system; the 80 MW Korean plant is its one
# real project; purification is what pipeline hydrogen needs and this site's does not.
FC_KOREAN_PLANT_GBP_PER_KW = 2_700.0
FC_PURIFICATION_GBP_PER_KW = 485.0
# The low case (4 Nov 2026) is the US national laboratory's modelled 100 MW
# plant, NLR/TP-5400-91146 Table 18, 2022 dollars, less the US sales tax and
# transmission interconnection it carries; Baringa's floor was the same document
# as its central, so no real range. Inflated in dollars, then the FES cross-rate.
NLR_TOTAL_OVERNIGHT_USD_PER_KW = 1_352.08
NLR_SALES_TAX_USD_PER_KW = 143.17
NLR_TRANSMISSION_USD_PER_KW = 100.0
NLR_PRICE_YEAR = 2022
FC_GBP_PER_KW = {
    "low": P.usd_to_gbp_2025(NLR_TOTAL_OVERNIGHT_USD_PER_KW - NLR_SALES_TAX_USD_PER_KW - NLR_TRANSMISSION_USD_PER_KW,
                             NLR_PRICE_YEAR),
    "central": FC_KOREAN_PLANT_GBP_PER_KW - FC_PURIFICATION_GBP_PER_KW,
    "high": FC_KOREAN_PLANT_GBP_PER_KW,
}
# Element Energy p. 94, 1.4 MWe, annual maintenance: 500 and 1 units per manufacturer.
FC_MAINTENANCE_GBP_PER_KW_YEAR = {"low": 42.0, "central": 48.0, "high": 48.0}
# CEPA for DESNZ (2025), Table E.1: hydrogen to power (emerging) and novel
# long-duration storage, 10.10 %; there is no fuel cell or hydrogen store row.
FC_DISCOUNT_RATE = 0.101
# Capital carried at the rate over the build (tech_costs.building_finance_factor):
# NLR Table 12 gives 3 years for the plant; Mott MacDonald for BEIS (2018) Table 53
# gives 1 year for a hydrogen storage system.
FC_BUILD_YEARS = 3
TANK_BUILD_YEARS = 1
# Insurance, which the maintenance figure does not carry, at the ratio DESNZ's
# onshore wind gives (£3.6k/MW/yr on £1,588/kW). Estimate: cost_exclusions.py.
FC_INSURANCE_FRAC_OF_CAPITAL = 3.6 / 1_588.0
# Stack's share of fuel-cell capital, since 4 Nov 2026 (evening): the Clean
# Hydrogen Partnership's state-of-the-art KPIs for 51-500 kWe PEM stationary
# units, Table 21: stack production cost €400/kWe on a €1,900/kW system. The UK
# figure (Element Energy's £1,200 replacement over £2,642 installed, 45 %) was
# read off a chart and sat above every other share read (Battelle 22-41 % with
# the fuel processor out; Roland Berger 34 %; NLR's module 17 %), so it is the
# high case of a sweep, not the central. 17.2 % until 4 Nov, frozen from a
# carbon split.
CH_STACK_EUR_PER_KWE = 400.0
CH_SYSTEM_EUR_PER_KW = 1_900.0
FC_STACK_COST_FRACTION = CH_STACK_EUR_PER_KWE / CH_SYSTEM_EUR_PER_KW
FC_STACK_COST_FRACTION_UK_HIGH = 1_200.0 / 2_642.0

# -----------------------------------------------------------------------------
# Hydrogen vessel
# -----------------------------------------------------------------------------
# Element Energy p. 109: installed price per vessel, with its 1.3 installation
# factor (the US DoE's H2A), and the hydrogen one holds.
TANK_VESSEL_INSTALLED_GBP = 182_000.0
TANK_VESSEL_KG = 405.0
# No UK range exists (4 Nov 2026, evening). Low: the Clean Hydrogen Partnership's
# KPI for above-ground storage at 20 t, €600/kg, a 2030 target that includes
# compression to 120 bar and purification, so a floor for a bare vessel; price
# year not stated, taken as is. High: the Danish Energy Agency's 200 bar rack of
# Type I tanks, Table 6: €600/kg for the tanks plus about €150,000 of piping,
# power electronics and manhours per 500 kg system, 2020 euros.
TANK_LOW_EUR_PER_KG = 600.0
DEA_TANK_EUR_PER_KG = 600.0
DEA_TANK_PIPING_EUR_PER_SYSTEM = 150_000.0
DEA_TANK_SYSTEM_KG = 500.0
DEA_TANK_PRICE_YEAR = 2020
TANK_HIGH_EUR_PER_KG = DEA_TANK_EUR_PER_KG + DEA_TANK_PIPING_EUR_PER_SYSTEM / DEA_TANK_SYSTEM_KG
# Element Energy p. 112, medium pressure: £0.34 fixed on £11.45 capital per kWh stored
TANK_FIXED_OPEX_FRAC = 0.34 / 11.45
# Land, an estimate: Element Energy p. 110's footprint for its high-pressure tubes
# (the only one it gives; a 28 bar vessel takes more), at DESNZ's rural solar rent,
# 2023 pounds. COST_GOV_FIGURES_PLAN.md H11: no urban rent is carried.
TANK_FOOTPRINT_M2_PER_KWH_HHV = 0.20
RURAL_LAND_GBP_PER_ACRE_YEAR = 1_000.0
M2_PER_ACRE = 4_046.86
RURAL_LAND_PRICE_YEAR = 2023

# -----------------------------------------------------------------------------
# SOEC
# -----------------------------------------------------------------------------
# Central capital since 4 Nov 2026 (evening): the Danish Energy Agency's Renewable
# Fuels data sheet "80 SOEC 10 MW" (DNV, Aug 2026), 2025 column, in 2025 euros:
# the one current, technology-specific government figure. The BEIS 2021 annex's
# own level (dated: its PEM is a third of NESO's) is the low case and its ratio
# to PEM on NESO's PEM the high: 2.46x, above every other range read.
DEA_SOEC_EUR_PER_KWE = 2_959.1368842714164
DEA_SOEC_EUR_PER_KWE_RANGE = (2_850.9642857142853, 3_067.3094828285475)
# BEIS 2021 annex, "Technical and cost assumptions", commissioning 2025, real 2020
# pounds. Capital and fixed cost per kW of hydrogen (HHV), so the electrical
# conversion (kWh in per kWh of hydrogen, medium) brings them to per kWe.
SOE_PRICE_YEAR = 2020
SOE_BUILD_YEARS = 3
SOE_CAPEX_GBP_PER_KW_H2 = 1_304.19      # medium; low 891.09, high 2,081.32
SOE_KWH_IN_PER_KWH_H2 = 0.95885
PEM_CAPEX_GBP_PER_KW_H2 = 730.29        # the same sheet's PEM, medium
PEM_KWH_IN_PER_KWH_H2 = 1.3208
SOE_FIXED_GBP_PER_KW_H2_YEAR = {"low": 49.5, "central": 53.02, "high": 54.77}
# Annuitised stack replacement (report, §3): no water in it.
SOE_VARIABLE_GBP_PER_KWH_H2 = {"low": 0.0070, "central": 0.0104, "high": 0.0178}

GRADE = "derived"


def capital_recovery_factor(rate, lifetime_years):
    if rate <= 0:
        return 1.0 / lifetime_years
    return rate / (1.0 - (1.0 + rate) ** -lifetime_years)


def fc_stack_cost_fraction() -> float:
    """Stack share of fuel cell capital: ``FC_STACK_COST_FRACTION``, frozen.

    It used to be the LCA's carbon split, read live, which coupled cost to any
    carbon rebuild. See the constant.
    """
    return FC_STACK_COST_FRACTION


def fuel_cell_cost(case: str, bop_calendar_years: float | None = None) -> dict:
    """One case of ``fuel_cell_costs``, each number recorded for the cost map."""
    from optimisation import fuel_cell as fc
    # From the constant, not the decomposition cache: an assumption edited in
    # fuel_cell.py must reach the cost side without a Brightway rerun.
    life = T.cost("cost.fuel_cell.bop_life_years", float(bop_calendar_years or fc.BOP_CALENDAR_LIFETIME_YEARS),
                  "years", "Balance-of-plant calendar life, the same life the carbon side replaces it on",
                  grade="assumed", note="fuel_cell.BOP_CALENDAR_LIFETIME_YEARS")
    rate = T.cost("cost.h2_assets.discount_rate", FC_DISCOUNT_RATE, "fraction per year",
                  "Discount rate for the fuel cell and tank: CEPA's hydrogen-to-power and novel storage rate",
                  grade="transcribed", cites=[("cepa_hurdle_rates_2025", "Table E.1, hydrogen CCHT/OCHT emerging and "
                                                                          "novel LDES, 10.10 %")],
                  note="No fuel cell or hydrogen store row in the table; the nearest two agree")
    crf = T.cost("cost.fuel_cell.crf", capital_recovery_factor(rate, life), "per year",
                 "Capital recovery factor over the balance-of-plant life",
                 uses=["cost.h2_assets.discount_rate", "cost.fuel_cell.bop_life_years"])
    if case == "low":
        T.cost("cost.fuel_cell.nlr_overnight_USD_per_kW", NLR_TOTAL_OVERNIGHT_USD_PER_KW, "US $ per kW",
               "Total overnight cost of a modelled 100 MW PEM plant, 2022 dollars", grade="transcribed",
               cites=[("nlr_tp_91146", "Table 18, total overnight cost")],
               inputs={"sales_tax": NLR_SALES_TAX_USD_PER_KW, "transmission": NLR_TRANSMISSION_USD_PER_KW})
        P.record_fx()
        capex = T.cost("cost.fuel_cell.capex_per_kW", FC_GBP_PER_KW[case], "GBP per kW",
                       "Installed capital in 2025 £, less US sales tax and grid spur, inflated in dollars",
                       uses=["cost.fuel_cell.nlr_overnight_USD_per_kW", P.record_foreign("usd", NLR_PRICE_YEAR),
                             "fx.usd_per_gbp_2025"],
                       note="Modelled and unbuilt, on vehicle modules; the report says a data-centre build costs more")
    else:
        baringa = T.cost("cost.fuel_cell.baringa_installed_per_kW", FC_KOREAN_PLANT_GBP_PER_KW, "GBP per kW",
                         "Installed capital of a PEM fuel cell plant on pipeline hydrogen", grade="transcribed",
                         cites=[("baringa_h2p_2025", "§4.4, the 80 MW Korean plant, c. £2,700/kW")])
        purification = T.cost("cost.fuel_cell.purification_per_kW", FC_PURIFICATION_GBP_PER_KW, "GBP per kW",
                              "Hydrogen purification for pipeline supply", grade="transcribed",
                              cites=[("baringa_h2p_2025", "§5, additional CAPEX of around £485/kW")])
        capex = T.cost("cost.fuel_cell.capex_per_kW", FC_GBP_PER_KW[case], "GBP per kW",
                       "Installed capital in 2025 £" + (", purification kept" if case == "high"
                                                         else ", less purification: this hydrogen is not pipeline-supplied"),
                       uses=["cost.fuel_cell.baringa_installed_per_kW", "cost.fuel_cell.purification_per_kW"],
                       inputs={"baringa": baringa, "purification": purification})
    build = T.cost("cost.fuel_cell.construction_years", FC_BUILD_YEARS, "years", "Construction period",
                   grade="transcribed", cites=[("nlr_tp_91146", "Table 12, construction period 3 years")])
    finance = T.cost("cost.fuel_cell.building_finance_factor", tc.building_finance_factor(rate, build), "multiplier",
                     "Capital carried at the rate over the build",
                     uses=["cost.h2_assets.discount_rate", "cost.fuel_cell.construction_years"])
    # Split capital between stack and balance of plant on FC_STACK_COST_FRACTION.
    #
    # It matters because the stack wears out on *duty* while BoP runs to
    # calendar. Charging the whole system on calendar life made
    # running the fuel cell hard free in cost while still costing carbon, so
    # the two objectives were pricing different physics for one machine.
    stack_frac = T.cost("cost.fuel_cell.stack_cost_fraction", fc_stack_cost_fraction(), "fraction",
                        "Stack share of the fuel cell's capital: stack production cost over system cost, 51-500 kWe",
                        grade="derived", cites=[("clean_hydrogen_sria_kpis", "Table 21, 2020 state of the art: stack "
                                                                             "€400/kWe, system €1,900/kW")],
                        inputs={"stack_EUR_per_kWe": CH_STACK_EUR_PER_KWE, "system_EUR_per_kW": CH_SYSTEM_EUR_PER_KW},
                        note="Units up to 500 kWe. The UK figure, Element Energy's 45 %, read off a chart, is the high "
                             "case of a sweep (FC_STACK_COST_FRACTION_UK_HIGH); other shares read: 11-41 %")
    maintenance = T.cost("cost.fuel_cell.maintenance_per_kW_year", FC_MAINTENANCE_GBP_PER_KW_YEAR[case],
                         "GBP per kW per year", "Annual maintenance of a 1.4 MWe fuel cell, 2017 prices",
                         grade="transcribed", cites=[("element_energy_2018", "p. 94, annual maintenance, 1.4 MWe")],
                         note="Roland Berger 2015 converted to pounds, so inflating from 2017 may understate")
    inflate = P.to_2025(ELEMENT_ENERGY_PRICE_YEAR)
    insurance = T.cost("cost.fuel_cell.insurance_frac", FC_INSURANCE_FRAC_OF_CAPITAL, "fraction of capital per year",
                       "Insurance, at onshore wind's ratio to capital: an estimate that fails the 1 % test if left out",
                       grade="proxy", cites=[("desnz_arup_2024_onshore_solar", "Table 3, insurance over total capex, central")])
    # As a share of balance-of-plant capital, which is what the annuity below runs on
    opex = T.cost("cost.fuel_cell.fixed_opex_frac", (maintenance * inflate + insurance * capex) / (capex * (1.0 - stack_frac)),
                  "fraction of balance-of-plant capital per year", "Fixed operating cost",
                  uses=["cost.fuel_cell.maintenance_per_kW_year", f"price_base.{ELEMENT_ENERGY_PRICE_YEAR}_to_2025",
                        "cost.fuel_cell.insurance_frac", "cost.fuel_cell.capex_per_kW", "cost.fuel_cell.stack_cost_fraction"])
    # BoP, split the same way as the stack so that duty reaches the
    # cost objective as it reaches carbon. The LP charges
    #   A_bop * (CRF + o - 1/L) * cap_fc  +  A_bop * fc_bop_units
    # and fc_bop_units >= max(cap_fc/L, MWh/duty_hours). When calendar
    # binds that is A_bop * (CRF + o) * cap_fc, exactly the old
    # annuity; when duty binds it stays within about 2 % of the exact
    # CRF on the shortened life. Charging the annuity alone made BoP
    # replacements free in cost above 2,400 h/yr — up to 39 % low on
    # the fuel cell line at 8,760 h. REVIEW_RESPONSE_PLAN.md §1.
    annual = T.cost("cost.fuel_cell.annual_per_MW",
                    capex * 1000.0 * (1.0 - stack_frac) * (finance * crf + opex - 1.0 / life),
                    "GBP per MW per year", "Balance of plant: capital recovery (the first build carrying its "
                    "finance) and opex, less the calendar replacement the LP charges per replacement",
                    uses=["cost.fuel_cell.capex_per_kW", "cost.fuel_cell.stack_cost_fraction", "cost.fuel_cell.crf",
                          "cost.fuel_cell.building_finance_factor", "cost.fuel_cell.fixed_opex_frac",
                          "cost.fuel_cell.bop_life_years"])
    bop = T.cost("cost.fuel_cell.bop_per_MW", capex * 1000.0 * (1.0 - stack_frac), "GBP per MW replaced",
                 "Balance of plant capital, charged per replacement",
                 uses=["cost.fuel_cell.capex_per_kW", "cost.fuel_cell.stack_cost_fraction"])
    # Stack capital, charged per replacement. Undiscounted, matching the
    # carbon side, because the LP abstracts away *when* a replacement
    # falls and a discount factor would need that schedule. This
    # overstates a distant replacement slightly.
    stack = T.cost("cost.fuel_cell.stack_per_MW", capex * 1000.0 * stack_frac, "GBP per MW replaced",
                   "Stack capital, charged per replacement (undiscounted, as the carbon side)",
                   uses=["cost.fuel_cell.capex_per_kW", "cost.fuel_cell.stack_cost_fraction"])
    return {
        "asset": "fuel_cell", "case": case,
        "capex_GBP_per_kW": capex,
        "capex_GBP_per_MW": capex * 1000.0,
        "fixed_opex_frac": opex,
        "lifetime_years": life,
        "stack_cost_fraction": stack_frac,
        "annual_GBP_per_MW_year": annual,
        "bop_GBP_per_MW": bop,
        "stack_GBP_per_MW": stack,
        "grade": GRADE,
        "note": "Baringa for DESNZ 2025, limited evidence; stack share read off Element Energy's chart",
    }


def fuel_cell_costs(bop_calendar_years: float | None = None):
    """£/kW installed, and the annualised £/kW/year that follows.

    ``bop_calendar_years`` overrides ``fuel_cell.BOP_CALENDAR_LIFETIME_YEARS``
    for a sweep, so the cost annuity moves with the life the carbon side's
    replacement count uses.
    """
    with T.quiet():
        return pd.DataFrame([fuel_cell_cost(case, bop_calendar_years) for case in CASES])


def tank_capex_gbp_per_kg(case: str) -> float:
    """Vessel capital per kg of capacity in 2025 pounds, by case, unrecorded."""
    if case == "central":
        return TANK_VESSEL_INSTALLED_GBP / TANK_VESSEL_KG * P.factor(ELEMENT_ENERGY_PRICE_YEAR)
    if case == "low":
        return TANK_LOW_EUR_PER_KG / EUR_PER_GBP_2025
    return P.eur_to_gbp_2025(TANK_HIGH_EUR_PER_KG, DEA_TANK_PRICE_YEAR)


def _tank_capex_recorded(case: str) -> float:
    """``tank_capex_gbp_per_kg`` with its inputs recorded for the cost map."""
    if case == "central":
        price = T.cost("cost.h2_tank.vessel_installed", TANK_VESSEL_INSTALLED_GBP, "GBP per vessel",
                       "Installed price of a 95 m³ vessel at 50-80 bar", grade="transcribed",
                       cites=[("element_energy_2018", "p. 109, £182k per vessel, a supplier's quote × 1.3")],
                       note="Not the carbon side's 28 bar Gandiglio vessel: a stated mismatch")
        kg = T.cost("cost.h2_tank.vessel_kg", TANK_VESSEL_KG, "kg of hydrogen per vessel", "What the vessel holds",
                    grade="transcribed", cites=[("element_energy_2018", "p. 109, ~405 kg")])
        P.to_2025(ELEMENT_ENERGY_PRICE_YEAR)
        uses = ["cost.h2_tank.vessel_installed", "cost.h2_tank.vessel_kg", f"price_base.{ELEMENT_ENERGY_PRICE_YEAR}_to_2025"]
        inputs = {"price": price, "kg": kg}
    elif case == "low":
        eur = T.cost("cost.h2_tank.low_EUR_per_kg", TANK_LOW_EUR_PER_KG, "€ per kg of capacity",
                     "Above-ground storage at 20 t, the EU partnership's 2030 target", grade="transcribed",
                     cites=[("clean_hydrogen_sria_kpis", "Table 11, above-ground storage, 20 t, 2030: €600/kg")],
                     note="A target, not a price, and it includes compression to 120 bar and purification, so a floor "
                          "for a bare vessel. Price year not stated: taken as is. No UK range exists")
        P.record_fx()
        uses = ["cost.h2_tank.low_EUR_per_kg", "fx.eur_per_gbp_2025"]
        inputs = {"eur": eur}
    else:
        tanks = T.cost("cost.h2_tank.dea_tanks_EUR_per_kg", DEA_TANK_EUR_PER_KG, "€ per kg of capacity",
                       "Type I steel tanks in a 200 bar rack, 2020 euros", grade="transcribed",
                       cites=[("dea_energy_storage_2025", "Table 6, hydrogen battery, €600/kg")])
        piping = T.cost("cost.h2_tank.dea_piping_EUR_per_kg", DEA_TANK_PIPING_EUR_PER_SYSTEM / DEA_TANK_SYSTEM_KG,
                        "€ per kg of capacity", "Piping, power electronics and manhours per kg of a 500 kg system",
                        grade="derived", cites=[("dea_energy_storage_2025", "Table 6, ~€150,000 per system of 500 kg")])
        eur = T.cost("cost.h2_tank.high_EUR_per_kg", TANK_HIGH_EUR_PER_KG, "€ per kg of capacity",
                     "The Danish rack, installed, 2020 euros", uses=["cost.h2_tank.dea_tanks_EUR_per_kg",
                                                                     "cost.h2_tank.dea_piping_EUR_per_kg"],
                     note="200 bar and 0.5 t, so a fair top for a bulk low-pressure vessel. No UK range exists")
        P.record_fx()
        uses = ["cost.h2_tank.high_EUR_per_kg", P.record_foreign("eur", DEA_TANK_PRICE_YEAR), "fx.eur_per_gbp_2025"]
        inputs = {"eur": eur, "tanks": tanks, "piping": piping}
    return T.cost("cost.h2_tank.capex_per_kg", tank_capex_gbp_per_kg(case), "GBP per kg of capacity",
                  "Vessel capital in real 2025 £", uses=uses, inputs=inputs)


def tank_cost(case: str) -> dict:
    """One case of ``tank_costs``, each number recorded for the cost map."""
    import dc_config as cfg
    life = T.cost("cost.h2_tank.life_years", float(cfg.TANK_LIFETIME_YEARS), "years",
                  "Tank life: the plant's, never replaced", grade="assumed",
                  note="dc_config.TANK_LIFETIME_YEARS, Gandiglio's plant lifetime")
    rate = T.cost("cost.h2_assets.discount_rate", FC_DISCOUNT_RATE, "fraction per year",
                  "Discount rate for the fuel cell and tank: CEPA's hydrogen-to-power and novel storage rate",
                  grade="transcribed", cites=[("cepa_hurdle_rates_2025", "Table E.1, hydrogen CCHT/OCHT emerging and "
                                                                          "novel LDES, 10.10 %")],
                  note="No fuel cell or hydrogen store row in the table; the nearest two agree")
    crf = T.cost("cost.h2_tank.crf", capital_recovery_factor(rate, life), "per year",
                 "Capital recovery factor over the tank's life",
                 uses=["cost.h2_assets.discount_rate", "cost.h2_tank.life_years"])
    capex = _tank_capex_recorded(case)
    opex = T.cost("cost.h2_tank.fixed_opex_frac", TANK_FIXED_OPEX_FRAC, "fraction of capital per year",
                  "Fixed operating cost", grade="derived",
                  cites=[("element_energy_2018", "p. 112, medium pressure, £0.34 fixed on £11.45 capital per kWh stored")])
    land = T.cost("cost.h2_tank.land_per_kg_year",
                  TANK_FOOTPRINT_M2_PER_KWH_HHV * H2_HHV_KWH_PER_KG / M2_PER_ACRE * RURAL_LAND_GBP_PER_ACRE_YEAR
                  * P.to_2025(RURAL_LAND_PRICE_YEAR),
                  "GBP per kg of capacity per year", "Land under the tank: an estimate that fails the 1 % test if left out",
                  grade="proxy", uses=[f"price_base.{RURAL_LAND_PRICE_YEAR}_to_2025"],
                  cites=[("element_energy_2018", "p. 110, 0.20 m²/kWh HHV, high-pressure storage"),
                         ("desnz_arup_2024_onshore_solar", "§6.8.1, about £1.0k per acre per year")])
    build = T.cost("cost.h2_tank.construction_years", TANK_BUILD_YEARS, "years", "Construction period",
                   grade="transcribed", cites=[("mott_macdonald_storage_2018", "Table 53, hydrogen storage system, 1 year")])
    finance = T.cost("cost.h2_tank.building_finance_factor", tc.building_finance_factor(rate, build), "multiplier",
                     "Capital carried at the rate over the build",
                     uses=["cost.h2_assets.discount_rate", "cost.h2_tank.construction_years"])
    annual = T.cost("cost.h2_tank.annual_per_kg", capex * (finance * crf + opex) + land, "GBP per kg of capacity per year",
                    "Capital recovery (carrying the build's finance), fixed opex and land, per kg the tank holds",
                    uses=["cost.h2_tank.capex_per_kg", "cost.h2_tank.crf", "cost.h2_tank.building_finance_factor",
                          "cost.h2_tank.fixed_opex_frac", "cost.h2_tank.land_per_kg_year"])
    return {
        "asset": "h2_tank", "case": case,
        "capex_GBP_per_kg_capacity": capex,
        "fixed_opex_frac": TANK_FIXED_OPEX_FRAC,
        "lifetime_years": life,
        "annual_GBP_per_kg_year": annual,
        "grade": GRADE,
        "note": "Element Energy for BEIS 2018, one supplier's quote at 50-80 bar; the range is not government",
    }


def tank_costs():
    """£ per kg of hydrogen storage capacity."""
    with T.quiet():
        return pd.DataFrame([tank_cost(case) for case in CASES])


def _neso_pem_capex(build_year=2025):
    """PEM capex from the NESO table the repo already has."""
    df = pd.read_csv(PRICE_DIR / "electrolyser_costs_clean.csv")
    df = df[(df.technology == "PEM") & (df.build_year == build_year)]
    if df.empty:
        raise ValueError(f"No NESO PEM capex for build year {build_year}")
    return {"low": float(df[df.scenario == "Low"].iloc[0].capex_GBP_per_kWe),
            "central": float(df[df.scenario == "Central"].iloc[0].capex_GBP_per_kWe),
            "high": float(df[df.scenario == "High"].iloc[0].capex_GBP_per_kWe)}




def electrolyser_cost(tech: str, case: str, build_year=2025) -> dict:
    """One electrolyser's NESO (or, for SOEC, PEM-scaled) cost row, each number
    recorded for the cost map. ``tech`` is "ae", "pem" or "soec"."""
    with T.quiet():
        df = electrolyser_costs(build_year)
    r = df[(df.asset == f"electrolyser_{tech}") & (df.case == case)].iloc[0]
    k = f"cost.electrolyser_{tech}"
    scen = {"low": "Low", "central": "Central", "high": "High"}[case]
    neso = lambda what: [("neso_green_h2_portal_costs", f"{'PEM' if tech != 'ae' else 'Alkaline'}, "   # noqa: E731
                                                        f"{scen}, build year {build_year}, {what}")]
    if tech == "soec":
        annex = lambda what: [("beis_h2_costs_2021", f"Technical and cost assumptions, commissioning 2025, {what}")]  # noqa: E731
        P.to_2025(SOE_PRICE_YEAR)
        soe = T.cost(f"{k}.annex_capex_per_kW_H2", SOE_CAPEX_GBP_PER_KW_H2, "GBP per kW H2 (HHV)",
                     "Solid-oxide capital, medium, real 2020", grade="transcribed", cites=annex("SOE CAPEX, medium"))
        soe_in = T.cost(f"{k}.annex_kWh_in_per_kWh_H2", SOE_KWH_IN_PER_KWH_H2, "kWh per kWh H2", "Solid-oxide electrical input",
                        grade="transcribed", cites=annex("SOE electrical conversion, medium"))
        uses = [f"{k}.annex_capex_per_kW_H2", f"{k}.annex_kWh_in_per_kWh_H2"]
        if case == "low":
            uses.append(f"price_base.{SOE_PRICE_YEAR}_to_2025")
            why = "The annex's level as printed, inflated: dated, its PEM is a third of NESO's 2025 figure"
        elif case == "central":
            T.cost(f"{k}.dea_capex_EUR_per_kWe", DEA_SOEC_EUR_PER_KWE, "€ per kW of input electricity",
                   "Solid-oxide 10 MW, 2025, 2025 euros", grade="transcribed",
                   cites=[("dea_renewable_fuels_2026", "sheet 80 SOEC 10 MW, specific investment, 2025 column")],
                   inputs={"lower": DEA_SOEC_EUR_PER_KWE_RANGE[0], "upper": DEA_SOEC_EUR_PER_KWE_RANGE[1]})
            P.record_fx()
            uses = [f"{k}.dea_capex_EUR_per_kWe", "fx.eur_per_gbp_2025"]
            why = ("The Danish Energy Agency's figure, current and specific to the technology, from a body NESO cites; "
                   "the UK annex's method puts it 2.46x PEM, above every other range read, so that is the high case")
        else:
            pem = T.cost("cost.electrolyser_pem.capex_per_kWe", _neso_pem_capex(build_year)[case], "GBP per kWe",
                         "PEM electrolyser capital", grade="transcribed", cites=neso("capex_GBP_per_kWe"))
            T.cost(f"{k}.annex_pem_per_kWe", PEM_CAPEX_GBP_PER_KW_H2 / PEM_KWH_IN_PER_KWH_H2, "GBP per kWe",
                   "The same sheet's PEM, medium, real 2020", grade="derived",
                   cites=annex("PEM CAPEX and electrical conversion, medium"))
            T.cost(f"{k}.multiplier_of_pem", _soe_ratio_to_pem(), "multiplier", "Solid-oxide over PEM per kWe, in the annex",
                   uses=[*uses, f"{k}.annex_pem_per_kWe"], inputs={"soe_per_kWe": soe / soe_in, "neso_pem": pem})
            uses = ["cost.electrolyser_pem.capex_per_kWe", f"{k}.multiplier_of_pem"]
            why = ("The annex's ratio to PEM on NESO's PEM: the high case, since it assumes a mature plant and sits "
                   "above every other range read")
        T.cost(f"{k}.capex_per_kWe", float(r.capex_GBP_per_kWe), "GBP per kWe", "SOEC capital", uses=uses, note=why)
        T.cost(f"{k}.annex_fixed_per_kW_H2_year", SOE_FIXED_GBP_PER_KW_H2_YEAR[case], "GBP per kW H2 per year",
               "Solid-oxide fixed cost, real 2020", grade="transcribed", cites=annex(f"SOE fixed OPEX, {case}"))
        T.cost(f"{k}.fixed_opex_frac", float(r.fixed_opex_frac), "fraction of capital per year", "Fixed operating cost",
               uses=[f"{k}.annex_fixed_per_kW_H2_year", f"{k}.annex_kWh_in_per_kWh_H2",
                     f"price_base.{SOE_PRICE_YEAR}_to_2025", f"{k}.capex_per_kWe"])
        T.cost(f"{k}.annex_variable_per_kWh_H2", SOE_VARIABLE_GBP_PER_KWH_H2[case], "GBP per kWh H2 (HHV)",
               "Solid-oxide stack replacement, annuitised, real 2020", grade="transcribed",
               cites=annex(f"SOE variable OPEX, {case}"))
        T.cost(f"{k}.variable_opex_per_kg", float(r.variable_opex_GBP_per_kg), "GBP per kg H2",
               "Stack replacement per kg made", uses=[f"{k}.annex_variable_per_kWh_H2", f"price_base.{SOE_PRICE_YEAR}_to_2025"],
               inputs={"kWh_per_kg_HHV": H2_HHV_KWH_PER_KG})
        T.cost(f"{k}.lifetime_years", float(r.lifetime_years), "years", "Plant life", grade="assumed",
               note="PEM's 25 years, kept to match the carbon side; the annex says 30")
    else:
        T.cost(f"{k}.capex_per_kWe", float(r.capex_GBP_per_kWe), "GBP per kWe", "Electrolyser capital",
               grade="transcribed", cites=neso("capex_GBP_per_kWe"))
        T.cost(f"{k}.fixed_opex_frac", float(r.fixed_opex_frac), "fraction of capital per year",
               "Fixed operating cost", grade="transcribed", cites=neso("fixed_opex_pct_capex"))
        hhv = T.cost("h2.hhv_kwh_per_kg", H2_HHV_KWH_PER_KG, "kWh per kg", "Hydrogen's higher heating value",
                     grade="transcribed", source="the standard figure, 141.8 MJ/kg")
        T.cost(f"{k}.variable_opex_per_kg", float(r.variable_opex_GBP_per_kg), "GBP per kg H2",
               "Stack replacement and water per kg made (NESO charges stack wear on output)",
               uses=["h2.hhv_kwh_per_kg"], cites=neso("variable_opex_GBP_per_kWh_H2_HHV"),
               inputs={"GBP_per_kWh_HHV": float(r.variable_opex_GBP_per_kg) / hhv})
        T.cost(f"{k}.lifetime_years", float(r.lifetime_years), "years", "Plant life", grade="transcribed",
               cites=neso("plant_lifetime_years"))
    return {**r.to_dict(), "trace_prefix": k}


def _soe_ratio_to_pem() -> float:
    """Solid-oxide capital over PEM's per kWe, medium, in the BEIS 2021 annex."""
    return ((SOE_CAPEX_GBP_PER_KW_H2 / SOE_KWH_IN_PER_KWH_H2)
            / (PEM_CAPEX_GBP_PER_KW_H2 / PEM_KWH_IN_PER_KWH_H2))


def _soec_capex_gbp_per_kwe(case: str, build_year=2025) -> float:
    """Danish Energy Agency (central), the BEIS annex's level inflated (low), or
    the annex's ratio on NESO's PEM (high)."""
    if case == "low":
        return SOE_CAPEX_GBP_PER_KW_H2 / SOE_KWH_IN_PER_KWH_H2 * P.factor(SOE_PRICE_YEAR)
    if case == "central":
        return DEA_SOEC_EUR_PER_KWE / EUR_PER_GBP_2025
    return _neso_pem_capex(build_year)[case] * _soe_ratio_to_pem()


def electrolyser_costs(build_year=2025):
    """AE and PEM from NESO; SOEC from the BEIS 2021 annex, on NESO's PEM.

    ``variable_opex_GBP_per_kg`` is NESO's variable opex — stack replacement and
    water — per kg made. NESO charges stack wear on output, so it is the cost
    counterpart of the carbon side's duty-driven ``ely_stack_units``. SOEC's is
    the annex's annuitised stack replacement, per kg.
    """
    df = pd.read_csv(PRICE_DIR / "electrolyser_costs_clean.csv")
    df = df[df.build_year == build_year]
    scen = {"low": "Low", "central": "Central", "high": "High"}
    rows = []
    for tech, label in (("Alkaline", "electrolyser_ae"), ("PEM", "electrolyser_pem")):
        sub = df[df.technology == tech]
        for case in CASES:
            r = sub[sub.scenario == scen[case]]
            if r.empty:
                continue
            r = r.iloc[0]
            rows.append({
                "asset": label, "case": case,
                "capex_GBP_per_kWe": float(r.capex_GBP_per_kWe),
                "fixed_opex_frac": float(r.fixed_opex_pct_capex),
                "variable_opex_GBP_per_kg": float(r.variable_opex_GBP_per_kWh_H2_HHV)
                                            * H2_HHV_KWH_PER_KG,
                "lifetime_years": float(r.plant_lifetime_years),
                "grade": "transcribed",
                "note": "NESO Green Hydrogen Data Portal",
            })
    inflate = P.factor(SOE_PRICE_YEAR)
    for case in CASES:
        capex = _soec_capex_gbp_per_kwe(case, build_year)
        rows.append({
            "asset": "electrolyser_soec", "case": case,
            "capex_GBP_per_kWe": capex,
            # Labour, overheads, insurance and maintenance do not follow the ratio
            "fixed_opex_frac": SOE_FIXED_GBP_PER_KW_H2_YEAR[case] / SOE_KWH_IN_PER_KWH_H2 * inflate / capex,
            "variable_opex_GBP_per_kg": SOE_VARIABLE_GBP_PER_KWH_H2[case] * H2_HHV_KWH_PER_KG * inflate,
            "lifetime_years": 25.0,
            "grade": GRADE,
            "note": {"low": "BEIS 2021 annex's level, dated", "central": "Danish Energy Agency, 10 MW, 2025",
                     "high": f"BEIS 2021 annex's {_soe_ratio_to_pem():.2f}x NESO's PEM, a mature plant"}[case],
        })
    return pd.DataFrame(rows)


def check(fc_df, tank_df, ely_df):
    problems = []
    for df, col in ((fc_df, "capex_GBP_per_MW"), (tank_df, "capex_GBP_per_kg_capacity"),
                    (ely_df, "capex_GBP_per_kWe")):
        for _, r in df.iterrows():
            if r[col] <= 0:
                problems.append(f"{r['asset']}/{r['case']}: non-positive capex")
            if r["grade"] == GRADE and not str(r["note"]).strip():
                problems.append(f"{r['asset']}/{r['case']}: assumed with no note")
        for asset in df.asset.unique():
            sub = df[df.asset == asset].set_index("case")
            if not (sub.loc["low", col] <= sub.loc["central", col] <= sub.loc["high", col]):
                problems.append(f"{asset}: low/central/high not ordered")
    if problems:
        raise AssertionError("h2_capex failed:\n  " + "\n  ".join(problems))
    n_derived = sum((d.grade == GRADE).sum() for d in (fc_df, tank_df, ely_df))
    return (f"OK — {n_derived} derived rows, every one noted and ordered "
            f"low <= central <= high")


def run():
    fc_df, tank_df, ely_df = fuel_cell_costs(), tank_costs(), electrolyser_costs()
    print("=" * 100)
    print("HYDROGEN-CHAIN ASSET COSTS — real 2025 GBP")
    print("=" * 100)
    print(check(fc_df, tank_df, ely_df))

    print("\nFuel cell (Baringa for DESNZ 2025, installed)")
    print("-" * 100)
    print(f"  {'case':<10}{'GBP/kW':>10}{'GBP/MW/yr':>14}{'opex':>8}")
    for _, r in fc_df.iterrows():
        print(f"  {r.case:<10}{r.capex_GBP_per_kW:>10,.0f}"
              f"{r.annual_GBP_per_MW_year:>14,.0f}{r.fixed_opex_frac:>8.1%}")
    print("  The stack's share of capital is not sourced.")

    print("\nHydrogen vessel (Element Energy for BEIS 2018, central)")
    print("-" * 100)
    print(f"  {'case':<10}{'GBP/kg':>10}{'GBP/kg/yr':>14}")
    for _, r in tank_df.iterrows():
        print(f"  {r.case:<10}{r.capex_GBP_per_kg_capacity:>10,.0f}{r.annual_GBP_per_kg_year:>14,.1f}")

    print("\nElectrolysers")
    print("-" * 100)
    print(f"  {'asset':<20}{'case':<10}{'GBP/kWe':>10}{'grade':>14}")
    for _, r in ely_df.iterrows():
        print(f"  {r.asset:<20}{r.case:<10}{r.capex_GBP_per_kWe:>10,.0f}{r.grade:>14}")
    flat = [a for a in ely_df.asset.unique()
            if ely_df[ely_df.asset == a].capex_GBP_per_kWe.nunique() == 1]
    if flat:
        print(f"\n  NESO publishes a single capex per technology per build year — its")
        print(f"  Low/Central/High labels vary the LCOH scenario, not the capital cost.")
        print(f"  So {', '.join(flat)} carry **no published uncertainty range**, while")
        print("  every assumed input around them does. A cost-case sweep therefore moves")
        print("  the fuel cell and the tank but holds the electrolyser fixed, which")
        print("  understates the true spread on any on-site electrolysis result.")

    print("\nWhat this does to a 7.31 MW hydrogen backup chain, central case")
    print("-" * 100)
    fcc = fc_df[fc_df.case == "central"].iloc[0]
    tk = tank_df[tank_df.case == "central"].iloc[0]
    fc_year = fcc.annual_GBP_per_MW_year * 7.31
    for tonnes in (5, 10, 20, 50):
        tank_year = tk.annual_GBP_per_kg_year * tonnes * 1000
        print(f"  fuel cell 7.31 MW + {tonnes:>2} t tank    "
              f"£{(fc_year + tank_year) / 1e6:>5.2f} m/yr   "
              f"(fuel cell £{fc_year / 1e6:.2f} m + tank £{tank_year / 1e6:.2f} m)")
    crossover = fc_year / (tk.annual_GBP_per_kg_year * 1000)
    print(f"\n  Against a £6.60 m/yr delivered grid bill for the same data centre.")
    print(f"  The fuel cell dominates below {crossover:.0f} t of storage and the tank above it.")
    print("  Across the whole plausible range of tank sizes, the cost of a hydrogen chain")
    print("  is set by these two numbers, each on thin UK government evidence.")

    OUT_DIR.mkdir(exist_ok=True)
    out = pd.concat([fc_df, tank_df, ely_df], ignore_index=True)
    out.to_csv(OUT_DIR / "h2_capex.csv", index=False)
    print("\nWrote:\n  optimisation_outputs/h2_capex.csv")
    return out


if __name__ == "__main__":
    run()
