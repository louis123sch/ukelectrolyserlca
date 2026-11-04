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
from optimisation import trace as T  # noqa: E402

PRICE_DIR = ROOT / "price_outputs"
OUT_DIR = ROOT / "optimisation_outputs"

CASES = ("low", "central", "high")

# FES 2025 Data Workbook cross-rate, as h2_prices.py uses.
EUR_PER_GBP_2025 = 1.17

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
FC_INSTALLED_FLOOR_GBP_PER_KW = 2_500.0
FC_KOREAN_PLANT_GBP_PER_KW = 2_700.0
FC_PURIFICATION_GBP_PER_KW = 485.0
FC_GBP_PER_KW = {
    "low": FC_INSTALLED_FLOOR_GBP_PER_KW - FC_PURIFICATION_GBP_PER_KW,
    "central": FC_KOREAN_PLANT_GBP_PER_KW - FC_PURIFICATION_GBP_PER_KW,
    "high": FC_KOREAN_PLANT_GBP_PER_KW,
}
# Element Energy p. 94, 1.4 MWe, annual maintenance: 500 and 1 units per manufacturer.
FC_MAINTENANCE_GBP_PER_KW_YEAR = {"low": 42.0, "central": 48.0, "high": 48.0}
FC_DISCOUNT_RATE = 0.06         # as sizing.Electrolyser, for consistency
# Insurance, which the maintenance figure does not carry, at the ratio DESNZ's
# onshore wind gives (£3.6k/MW/yr on £1,588/kW). Estimate: cost_exclusions.py.
FC_INSURANCE_FRAC_OF_CAPITAL = 3.6 / 1_588.0
# Stack's share of fuel-cell capital, since 4 Nov 2026: Element Energy's stack
# replacement over its fully installed cost at 1.4 MWe, one unit: about £1,200
# (read off the chart, p. 93) over £2,642 (p. 94). A replacement cost is what the
# LP charges with it. 17.2 % until then, frozen from a carbon split. Cross-checks,
# not government: Battelle 22-41 % once the fuel processor and heat recovery are
# out; Roland Berger 34 % of a 1 MW gas unit.
FC_STACK_REPLACEMENT_GBP_PER_KW = 1_200.0
FC_INSTALLED_FOR_STACK_SHARE_GBP_PER_KW = 2_642.0
FC_STACK_COST_FRACTION = FC_STACK_REPLACEMENT_GBP_PER_KW / FC_INSTALLED_FOR_STACK_SHARE_GBP_PER_KW

# -----------------------------------------------------------------------------
# Hydrogen vessel
# -----------------------------------------------------------------------------
# Element Energy p. 109: installed price per vessel, with its 1.3 installation
# factor (the US DoE's H2A), and the hydrogen one holds.
TANK_VESSEL_INSTALLED_GBP = 182_000.0
TANK_VESSEL_KG = 405.0
TANK_INSTALLATION_FACTOR = 1.3
# Not government: no UK range exists. Rozzi's dataset, 30 bar, 50 t, 2020 euros
# and uninstalled; the older literature's top.
TANK_LOW_EUR_PER_KG = 289.0
TANK_LOW_PRICE_YEAR = 2020
TANK_HIGH_EUR_PER_KG = 1_040.0
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
# BEIS 2021 annex, "Technical and cost assumptions", commissioning 2025, real 2020
# pounds. Capital and fixed cost per kW of hydrogen (HHV), so the electrical
# conversion (kWh in per kWh of hydrogen, medium) brings them to per kWe.
SOE_PRICE_YEAR = 2020
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
                  "Discount rate for the fuel cell and tank", grade="assumed",
                  note="As the electrolyser's 6 %, for consistency; one discount-rate policy is open (audit §4)")
    crf = T.cost("cost.fuel_cell.crf", capital_recovery_factor(rate, life), "per year",
                 "Capital recovery factor over the balance-of-plant life",
                 uses=["cost.h2_assets.discount_rate", "cost.fuel_cell.bop_life_years"])
    baringa = T.cost(f"cost.fuel_cell.baringa_installed_{case}_per_kW",
                     FC_KOREAN_PLANT_GBP_PER_KW if case != "low" else FC_INSTALLED_FLOOR_GBP_PER_KW, "GBP per kW",
                     "Installed capital of a PEM fuel cell plant on pipeline hydrogen", grade="transcribed",
                     cites=[("baringa_h2p_2025", "§4.4, the 80 MW Korean plant, c. £2,700/kW" if case != "low"
                             else "§5, total installed CAPEX estimated to exceed £2,500/kW")])
    purification = T.cost("cost.fuel_cell.purification_per_kW", FC_PURIFICATION_GBP_PER_KW, "GBP per kW",
                          "Hydrogen purification for pipeline supply", grade="transcribed",
                          cites=[("baringa_h2p_2025", "§5, additional CAPEX of around £485/kW")])
    capex = T.cost("cost.fuel_cell.capex_per_kW", FC_GBP_PER_KW[case], "GBP per kW",
                   "Installed capital in 2025 £" + (", purification kept" if case == "high"
                                                     else ", less purification: this hydrogen is not pipeline-supplied"),
                   uses=[f"cost.fuel_cell.baringa_installed_{case}_per_kW", "cost.fuel_cell.purification_per_kW"],
                   inputs={"baringa": baringa, "purification": purification})
    # Split capital between stack and balance of plant on FC_STACK_COST_FRACTION.
    #
    # It matters because the stack wears out on *duty* while BoP runs to
    # calendar. Charging the whole system on calendar life made
    # running the fuel cell hard free in cost while still costing carbon, so
    # the two objectives were pricing different physics for one machine.
    stack_frac = T.cost("cost.fuel_cell.stack_cost_fraction", fc_stack_cost_fraction(), "fraction",
                        "Stack share of the fuel cell's capital: stack replacement over installed cost, 1.4 MWe",
                        grade="derived", cites=[("element_energy_2018", "p. 93 chart, about £1,200/kWe; p. 94, £2,642/kWe")],
                        inputs={"replacement": FC_STACK_REPLACEMENT_GBP_PER_KW,
                                "installed": FC_INSTALLED_FOR_STACK_SHARE_GBP_PER_KW},
                        note="Read off a chart; natural-gas data with the reformer removed. Battelle's cost-based "
                             "share, not government, is 22-41 %")
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
    annual = T.cost("cost.fuel_cell.annual_per_MW", capex * 1000.0 * (1.0 - stack_frac) * (crf + opex - 1.0 / life),
                    "GBP per MW per year", "Balance of plant: capital recovery and opex, less the calendar "
                    "replacement the LP charges per replacement",
                    uses=["cost.fuel_cell.capex_per_kW", "cost.fuel_cell.stack_cost_fraction", "cost.fuel_cell.crf",
                          "cost.fuel_cell.fixed_opex_frac", "cost.fuel_cell.bop_life_years"])
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
        return (TANK_LOW_EUR_PER_KG * TANK_INSTALLATION_FACTOR / EUR_PER_GBP_2025
                * P.factor(TANK_LOW_PRICE_YEAR))
    return TANK_HIGH_EUR_PER_KG / EUR_PER_GBP_2025


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
                     "Compressed vessel, 30 bar, 50 t, uninstalled, 2020", grade="transcribed",
                     cites=[("rozzi_2024", "H2_tank_raw, 30 bar, 50,000 kg")], note="Not government: no UK range exists")
        P.to_2025(TANK_LOW_PRICE_YEAR)
        T.cost("cost.h2_tank.installation_factor", TANK_INSTALLATION_FACTOR, "multiplier", "Installed over equipment",
               grade="transcribed", cites=[("element_energy_2018", "p. 109, 1.3, from the US DoE's H2A")])
        T.cost("fx.eur_per_gbp_2025", EUR_PER_GBP_2025, "€ per £", "2025 cross-rate, £ to €",
               grade="transcribed", cites=[("fes_2025_workbook", "cross-rates, 2025: £1 = €1.17")])
        uses = ["cost.h2_tank.low_EUR_per_kg", "cost.h2_tank.installation_factor", "fx.eur_per_gbp_2025",
                f"price_base.{TANK_LOW_PRICE_YEAR}_to_2025"]
        inputs = {"eur": eur}
    else:
        eur = T.cost("cost.h2_tank.high_EUR_per_kg", TANK_HIGH_EUR_PER_KG, "€ per kg of capacity",
                     "The older literature's top", grade="assumed", cites=[("h2_vessel_literature", "€1,040/kg")],
                     note="Not government, and not one document: no UK range exists")
        T.cost("fx.eur_per_gbp_2025", EUR_PER_GBP_2025, "€ per £", "2025 cross-rate, £ to €",
               grade="transcribed", cites=[("fes_2025_workbook", "cross-rates, 2025: £1 = €1.17")])
        uses = ["cost.h2_tank.high_EUR_per_kg", "fx.eur_per_gbp_2025"]
        inputs = {"eur": eur}
    return T.cost("cost.h2_tank.capex_per_kg", tank_capex_gbp_per_kg(case), "GBP per kg of capacity",
                  "Vessel capital in real 2025 £", uses=uses, inputs=inputs)


def tank_cost(case: str) -> dict:
    """One case of ``tank_costs``, each number recorded for the cost map."""
    import dc_config as cfg
    life = T.cost("cost.h2_tank.life_years", float(cfg.TANK_LIFETIME_YEARS), "years",
                  "Tank life: the plant's, never replaced", grade="assumed",
                  note="dc_config.TANK_LIFETIME_YEARS, Gandiglio's plant lifetime")
    rate = T.cost("cost.h2_assets.discount_rate", FC_DISCOUNT_RATE, "fraction per year",
                  "Discount rate for the fuel cell and tank", grade="assumed",
                  note="As the electrolyser's 6 %, for consistency; one discount-rate policy is open (audit §4)")
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
    annual = T.cost("cost.h2_tank.annual_per_kg", capex * (crf + opex) + land, "GBP per kg of capacity per year",
                    "Capital recovery, fixed opex and land, per kg the tank holds",
                    uses=["cost.h2_tank.capex_per_kg", "cost.h2_tank.crf", "cost.h2_tank.fixed_opex_frac",
                          "cost.h2_tank.land_per_kg_year"])
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
        else:
            pem = T.cost("cost.electrolyser_pem.capex_per_kWe", _neso_pem_capex(build_year)[case], "GBP per kWe",
                         "PEM electrolyser capital", grade="transcribed", cites=neso("capex_GBP_per_kWe"))
            T.cost(f"{k}.annex_pem_per_kWe", PEM_CAPEX_GBP_PER_KW_H2 / PEM_KWH_IN_PER_KWH_H2, "GBP per kWe",
                   "The same sheet's PEM, medium, real 2020", grade="derived",
                   cites=annex("PEM CAPEX and electrical conversion, medium"))
            T.cost(f"{k}.multiplier_of_pem", _soe_ratio_to_pem(), "multiplier", "Solid-oxide over PEM per kWe, in the annex",
                   uses=[*uses, f"{k}.annex_pem_per_kWe"], inputs={"soe_per_kWe": soe / soe_in, "neso_pem": pem})
            uses = ["cost.electrolyser_pem.capex_per_kWe", f"{k}.multiplier_of_pem"]
            why = ("The annex's ratio to PEM on NESO's PEM, for consistency with the other types; assumes a mature "
                   "plant, and sits above every non-government range read")
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
    """The annex's level inflated (low), or its ratio on NESO's PEM. No government
    figure sits above the ratio, so high equals central."""
    if case == "low":
        return SOE_CAPEX_GBP_PER_KW_H2 / SOE_KWH_IN_PER_KWH_H2 * P.factor(SOE_PRICE_YEAR)
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
            "note": "BEIS 2021 annex: " + ("its level, dated" if case == "low" else
                                           f"{_soe_ratio_to_pem():.2f}x NESO's PEM") + "; assumes a mature plant",
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
