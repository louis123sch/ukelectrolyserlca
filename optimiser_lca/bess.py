"""
Grid-scale battery storage — Jasper et al. 2026 container, Voß et al. 2025 cell.
=============================================================================

Why this inventory exists
-------------------------
The battery used to be ecoinvent's ``market for battery, Li-ion, LFP,
rechargeable, prismatic`` [GLO]: an **electric-vehicle traction pack**
(Dai et al. / GREET lineage, 2016-era, 116 Wh/kg) with no container, racking,
HVAC or fire suppression — ``battery.CONTAINER_UPLIFT_FRACTION`` was 0.0 and
said so. A grid battery is neither of those things. It is large-format
prismatic cells in racks, in a 20 ft container, with its own thermal
management and fire suppression, and those non-cell parts are 18-23 % of the
DC block's carbon in every source that itemises them.

So the battery is assembled from two published inventories, the way the solar
plant and the step-up transformers are:

    container  F.B. Jasper, Y. Zhou, H. Ersoy, M. Baumann et al., "Life Cycle
               Assessment of Grid-Scale Battery Storage", Energy Advances 5
               (2026) 550-570, doi:10.1039/D5YA00341E. SI workbook (Zenodo
               doi:10.5281/zenodo.17651912), sheets "Air-cooled CSS -
               Production" and "Liquid-cooled CSS - Production". CC-BY-NC.
    cell       P. Voß, B. Gruber, M. Mitterfellner, J.-D. Plöpst, F. Degen,
               R. Schmuch, S. Lux, "Benchmarking state-of-the-art sodium-ion
               battery cells", Energy Environ. Sci. 18 (2025) 8104-8129,
               doi:10.1039/D5EE00415B. Main text Table 3 (the cell bill), ESI
               Tables S5, S31, S32, S35, S36 (the materials).

Jasper's own cell *is* Voß's: their workbook links ``LFP based LIB (Voß et
al.)`` at 176.6 Wh/kg and does not reproduce it. Voß is built on **ecoinvent
3.9.1** — this study's own database — so the cell rebuilds here without a
version mismatch, where Jasper re-scored it on 3.11.

Which of Jasper's designs
-------------------------
**Liquid-cooled LFP**: 1,600 kW / 3,008 kWh, eight racks of eight 47 kWh
modules, 306 Ah cells. Liquid cooling is what current containers ship with
(the Sungrow and Trina EPDs that sit beside this inventory are both
liquid-cooled); the air-cooled 2,064 kWh design is the older generation, and
the three sodium-ion chemistries are Jasper's comparison, not the market.
Current 20 ft products pack ~5 MWh; per-container items (container, fire
suppression, controller, part of the cooling) are ~7 kg CO2e/kWh here and would
be ~3 kg/kWh lower spread over 5 MWh. Built as published; the denser packing
is a sensitivity, not an invented design.

Choices this study makes, not the sources
-----------------------------------------
* **Cells made in China** (``CELL_FACTORY``). Voß model a German gigafactory;
  Jasper assume Chinese production, and Chinese makers supply most stationary
  LFP cells. The German cell is built too, as ``bess_lfp_cell_1kwh_de``, so
  Voß's own published figure can be reproduced (``describe()``).
* **Graphite 75:25 synthetic:natural** (``GRAPHITE_SYNTHETIC_SHARE``), Voß's
  benchmark, which they give as current market share. Jasper's 65:35 is
  ecoinvent 3.11's default mix, not a market statement.
* **Cell factory energy 18 kWh electricity + 19 kWh natural gas per kWh of
  cells**, Degen et al. (2023) as restated by Jasper §2.4.1. Voß do not
  tabulate it. The gas is charged as heat delivered (19 kWh = 68.4 MJ).

What is deliberately NOT here — the study's own boundary
--------------------------------------------------------
* **End-of-life**, as everywhere (ASSUMPTIONS.md §6). Jasper's
  ``treatment of used CSS`` and the whole EOL sheet are not taken.
* **Transport to site.** The study excludes delivery to site and nothing else,
  because the site is not known; upstream transport is in. Jasper's rows split
  on exactly that line (see ``_no_transport`` below): his 1,000 km lorry +
  8,000 km sea + 1,000 km rail legs ship finished parts from China to his
  German site and are left out, as ``upv.py`` leaves out Smith's A14; his
  100 km lorry + 600 km rail legs bring materials to the module and rack
  factories and are kept. Voß's China-to-Berlin legs (18.5 t·km sea, 1.0 and
  0.7 t·km lorry per kg) carry materials to *their* German factory, which this
  China-made cell does not have, so they are not taken; where Voß folded them
  into a published factor (natural graphite), the sea and European legs are
  removed with negative exchanges and the Chinese lorry leg stays. The same
  Chinese lorry leg is carried on every other cell material (ESI §3.1.3 add it
  "additionally" to each), as the upstream haul to the cell factory.
* **The power conversion system** (800 kg), charged separately by
  ``battery.PCS_ACTIVITY`` on the power term.
* **The battery transformer** (5,500 kg). Charged separately since 15 Oct, per
  MW of ``cap_batt_p``, by ``optimisation/transformers.py``: its mass from this
  bill, its composition from the IEA PVPS unit
  (``stepup_transformers.CSS_TX_KG``, which ``check()`` holds to this row).
  Jasper's own per-kg recipe (Hunziker 2020, a 630 kVA unit with an on-load
  tap changer) is set aside as a stated substitution; see stepup_transformers.
* **Voß's processing materials** (NMP, argon, nitrogen, compressed air), which
  they draw from Degen's source data and do not tabulate. Small; this errs low.

Factors that are pinned, not inventories
----------------------------------------
Five figures in the sources are carbon footprints rather than exchanges. Each
enters as a ``Carbon dioxide, fossil`` emission of its own size, so it is
correct for GWP100 and *only* for GWP100 — do not read other impact
categories off those five activities:

    natural graphite   5.19 kg CO2e/kg   Engels et al. 2022 via Voß §3.1.1.2,
                                         less the transport legs Voß added
    PVDF binder       60.6  kg CO2e/kg   Hu et al. via Voß §3.1.3.1
    separator          5.06 kg CO2e/kg   ecoinvent 3.8, as Voß §3.1.3.4 chose
                                         over 3.9.1's 39.6 ("unrealistically
                                         high"); 3.9.1 here scores 34.4-39.5
    graphitisation crucible  7.346 kg CO2e per kg SGr   Carrère via Voß Table S5
    packaging media + block  0.432 kg CO2e per kg SGr   Carrère via Voß Table S5

Units
-----
``bess_dc_block_per_kwh`` is per kWh of **nameplate** (cell) capacity, which is
what both sources report. ``optimisation/battery.py`` divides by its
``USABLE_FRACTION`` because the LP's ``cap_batt_e`` is the energy the battery
can actually swing.
"""
from __future__ import annotations

from optimiser_lca import registry as R
from optimiser_lca.common import FG, Activity, Flow, Inventory, Process

# =============================================================================
# Parameters
# =============================================================================
# --- the cell: Voß Table 3, LFP/graphite prismatic cell, grams per cell ---------
CELL_WH = 383.4                  # TRANSCRIBED - nominal energy per cell
CELL_STATED_MASS_G = 2_170.8     # TRANSCRIBED - total cell mass
CELL_STATED_WH_PER_KG = 176.6    # TRANSCRIBED - specific energy
CELL_BILL_G = {                  # TRANSCRIBED, grams per cell
    "anode_active":     387.6,   # graphite, split below
    "anode_cmc":          8.1,
    "anode_sbr":          6.1,
    "anode_carbon":       2.0,
    "anode_cu_foil":    164.9,
    "cathode_active":   726.0,   # LFP with 5 wt% carbon coating
    "cathode_pvdf":      15.1,
    "cathode_carbon":    15.1,
    "cathode_al_foil":   45.2,
    "electrolyte":      423.6,
    "separator":         47.0,
    "housing":          330.0,
}
CELLS_PER_KWH = 1000.0 / CELL_WH

# Voß's benchmark blend, stated as current market share (§4.2.1).
GRAPHITE_SYNTHETIC_SHARE = 0.75

# Voß Table S5: 98.8 % of the synthesis burden is allocated to the graphite,
# 1.2 % to the incinerator's surplus heat, by economic value.
SGR_ECONOMIC_ALLOCATION = 0.988

# Degen et al. 2023 as restated by Jasper §2.4.1, per kWh of LFP cells.
CELL_FACTORY_KWH_ELECTRICITY = 18.0
CELL_FACTORY_KWH_GAS = 19.0
CELL_FACTORY_MJ_HEAT = CELL_FACTORY_KWH_GAS * 3.6
CELL_FACTORIES = ("CN", "DE")
CELL_FACTORY = "CN"
if CELL_FACTORY not in CELL_FACTORIES:
    raise ValueError(f"CELL_FACTORY must be one of {CELL_FACTORIES}")

# Pinned footprints, kg CO2e per kg (see the docstring).
NGR_KGCO2E_PER_KG = 5.19
PVDF_KGCO2E_PER_KG = 60.6
SEPARATOR_KGCO2E_PER_KG = 5.06
SGR_CRUCIBLE_KGCO2E_PER_KG = 7.346
SGR_PACKAGING_KGCO2E_PER_KG = 0.432

# The China-to-Berlin legs Voß add to every material (ESI §3.1.1.1), per kg.
VOSS_SEA_TKM = 18.5
VOSS_LORRY_CN_TKM = 1.0
VOSS_LORRY_EU_TKM = 0.7

# --- the container: Jasper Table 2, liquid-cooled LFP --------------------------
CSS_KWH = 3_008.0                # TRANSCRIBED
CSS_KW = 1_600.0                 # TRANSCRIBED
CSS_RACKS = 8                    # TRANSCRIBED
CSS_MODULES_PER_RACK = 8         # TRANSCRIBED
CSS_MODULE_KWH = 47.0            # TRANSCRIBED - "LFP *47000/176.6" kg of cells
CSS_COOLING_PLATES = CSS_RACKS * CSS_MODULES_PER_RACK   # "num_powersection*num_batterypack"
CSS_NITRILE_KG = 0.75 * CSS_COOLING_PLATES              # "0.75*num_batterypack*num_powersection"

# ASSUMED. Jasper take the module's busbars from Ellingsen et al. (2014) and do
# not reproduce them. Aluminium endbars and copper end-busbars are what they
# say; "bimetallic busbars and washers" is split evenly between the two.
# 10.7 kg per 47 kWh module, ~1.8 kg CO2e/kWh, so the split moves the total
# by under 1 %.
BIMETALLIC_COPPER_SHARE = 0.5

# What Jasper's DC block carries and this study does not (see the docstring).
CSS_EXCLUDED = {
    "Power conversion system for CSS": (800.0, "kg", "battery.PCS_ACTIVITY charges the power term"),
    "transformer, for grid connection": (5_500.0, "kg", "charged per MW of cap_batt_p by transformers.py since "
                                                        "15 Oct (stepup_transformers.CSS_TX_KG reads this row)"),
}
# Jasper's 43.9 t concrete block was in this table until 21 Oct 2026 ("civils
# are outside every capital inventory here"). That was a consistency policy,
# not a study boundary; the block is in the source and inside the boundary, so
# it is now on the container activity, where the fuel cell shares it.

# Jasper's Fig. 4 for the liquid-cooled LFP system, kg CO2e per kWh, on
# ecoinvent 3.11 cut-off at EF 3.1, with transport. A comparison, not a target.
JASPER_FIG4_LC_LFP = {
    "cells": 95.44, "modules_wo_cells": 6.57, "racks": 6.59, "pcs": 8.29,
    "container": 3.50, "transformer": 14.01, "foundation": 2.06,
    "cooling": 2.64, "fire_suppression": 0.76, "others": 0.25, "sum": 140.11,
}
# Voß §4.2.1 on ecoinvent 3.9.1, German factory, with transport and processing
# materials: the cell this module's German variant should reproduce.
VOSS_LFP_CELL_DE_75_25 = 71.2

BESS_SCOPE = {
    "design": "Jasper et al. 2026 liquid-cooled LFP container, 1,600 kW / 3,008 kWh, as published.",
    "cell": "Voß et al. 2025 LFP/graphite prismatic cell, 176.6 Wh/kg, on ecoinvent 3.9.1; "
            f"made in {CELL_FACTORY}; graphite {GRAPHITE_SYNTHETIC_SHARE:.0%} synthetic.",
    "end_of_life": "EXCLUDED, as everywhere else in this study.",
    "transport": "Delivery to site EXCLUDED (Jasper's China-to-Germany rows); upstream legs to the "
                 "module and rack factories INCLUDED. Voß's legs to a German factory not taken, "
                 "the sea and European legs subtracted from the natural-graphite factor.",
    "pcs": "EXCLUDED here - charged by battery.PCS_ACTIVITY on the power term.",
    "transformer": "EXCLUDED here - charged per MW of cap_batt_p by transformers.py (Jasper's 5,500 kg on "
                   "the IEA PVPS composition, a stated substitution for Jasper's Hunziker-derived "
                   "recipe on representativeness, stepup_transformers.py).",
    "foundation": "INCLUDED since 21 Oct 2026 - Jasper's 43.9 t concrete block, on the container activity.",
    "processing_materials": "EXCLUDED - Voß do not tabulate NMP, argon, N2 or compressed air.",
}


def check() -> str:
    """The transcribed bills must rebuild their sources' stated figures."""
    mass = sum(CELL_BILL_G.values())
    if abs(mass - CELL_STATED_MASS_G) > 0.2:
        raise AssertionError(f"Voß cell bill sums to {mass:,.1f} g against the stated "
                             f"{CELL_STATED_MASS_G:,.1f} g")
    if abs(CELL_WH / mass * 1000.0 - CELL_STATED_WH_PER_KG) > 0.1:
        raise AssertionError("cell energy / cell mass no longer gives 176.6 Wh/kg")
    if abs(CSS_RACKS * CSS_MODULES_PER_RACK * CSS_MODULE_KWH - CSS_KWH) > 1e-9:
        raise AssertionError("8 racks x 8 modules x 47 kWh no longer makes the 3,008 kWh container")
    if not (0.0 <= GRAPHITE_SYNTHETIC_SHARE <= 1.0 and 0.0 <= BIMETALLIC_COPPER_SHARE <= 1.0):
        raise AssertionError("a share is outside [0, 1]")
    for a in activities:
        for key, *_ in a.technosphere:
            if not isinstance(key, FG) and key not in processes:
                raise AssertionError(f"{a.code}: no process {key!r}")
    return (f"OK - cell {mass:,.1f} g, {CELL_WH:g} Wh, {CELL_STATED_WH_PER_KG:g} Wh/kg; "
            f"container {CSS_RACKS}x{CSS_MODULES_PER_RACK}x{CSS_MODULE_KWH:g} kWh = "
            f"{CSS_KWH:,.0f} kWh; cells made in {CELL_FACTORY}")


# =============================================================================
# Processes
# =============================================================================
_kg, _kwh, _MJ, _unit, _tkm = "kilogram", "kilowatt hour", "megajoule", "unit", "ton kilometer"


def _p(name, loc, query, why=""):
    return Process(identity=(name, loc), query=query, why=why)


processes = {
    # --- Voß: energy -----------------------------------------------------------
    "electricity_mv_cn": _p("market group for electricity, medium voltage", "CN",
                            "market group for electricity medium voltage CN",
                            "Voß's electricity for every material made in China"),
    "electricity_mv_de": _p("market for electricity, medium voltage", "DE",
                            "market for electricity medium voltage DE",
                            "Voß's gigafactory electricity, German variant only"),
    "heat_gas_small_row": _p("market for heat, central or small-scale, natural gas", "RoW",
                             "market for heat central or small-scale natural gas RoW"),
    "heat_gas_industrial_row": _p("market for heat, district or industrial, natural gas", "RoW",
                                  "market for heat district or industrial natural gas RoW",
                                  "cell factory gas in China; ecoinvent has no CN gas heat"),
    "heat_gas_industrial_rer": _p("market group for heat, district or industrial, natural gas", "RER",
                                  "market group for heat district or industrial natural gas RER",
                                  "Voß's own gigafactory heat dataset, German variant only"),
    # --- Voß: synthetic graphite (Table S5) ---------------------------------------
    "petroleum_coke": _p("market for petroleum coke", "GLO", "market for petroleum coke GLO",
                         "needle coke feed"),
    # --- Voß: LFP-C and FePO4 (Tables S31, S32) ---------------------------------
    "iron_sulfate": _p("market for iron sulfate", "RoW", "market for iron sulfate RoW"),
    "phosphoric_acid": _p("market for phosphoric acid, industrial grade, without water, in 85% solution state",
                          "GLO", "market for phosphoric acid industrial grade 85% GLO"),
    "hydrogen_peroxide": _p("market for hydrogen peroxide, without water, in 50% solution state", "RoW",
                            "market for hydrogen peroxide 50% solution RoW"),
    "sodium_hydroxide": _p("market for sodium hydroxide, without water, in 50% solution state", "GLO",
                           "market for sodium hydroxide 50% solution GLO"),
    "water_softened": _p("market for water, completely softened", "RoW",
                         "market for water completely softened RoW"),
    "lithium_carbonate": _p("market for lithium carbonate", "GLO", "market for lithium carbonate GLO"),
    "glucose": _p("market for glucose", "GLO", "market for glucose GLO"),
    "nitrogen_liquid": _p("market for nitrogen, liquid", "RoW", "market for nitrogen liquid RoW"),
    "water_deionised": _p("market for water, deionised", "RoW", "market for water deionised RoW"),
    # --- Voß: SBR (Table S35) ---------------------------------------------------
    "butadiene": _p("market for butadiene", "RoW", "market for butadiene RoW"),
    "styrene": _p("market for styrene", "GLO", "market for styrene GLO"),
    "chemical_organic": _p("market for chemical, organic", "GLO", "market for chemical organic GLO",
                           "Voß's proxy for the DDM chain-transfer agent"),
    "fatty_acid": _p("market for fatty acid", "GLO", "market for fatty acid GLO"),
    "chemical_inorganic": _p("market for chemical, inorganic", "GLO", "market for chemical inorganic GLO"),
    "steam_chemical_row": _p("market for steam, in chemical industry", "RoW",
                             "market for steam in chemical industry RoW"),
    # --- Voß: datasets named directly (ESI §3.1.3) -------------------------------
    "cmc": _p("carboxymethyl cellulose production, powder", "RoW",
              "carboxymethyl cellulose production powder RoW"),
    "carbon_black": _p("carbon black production", "GLO", "carbon black production GLO"),
    "cu_collector_foil": _p("copper collector foil production, for Li-ion battery", "GLO",
                            "copper collector foil production Li-ion battery GLO"),
    "al_collector_foil": _p("aluminium collector foil production, for Li-ion battery", "GLO",
                            "aluminium collector foil production Li-ion battery GLO"),
    "electrolyte": _p("electrolyte production, for Li-ion battery", "GLO",
                      "electrolyte production for Li-ion battery GLO",
                      "1M LiPF6 in EC:DMC, Voß's choice"),
    # --- Voß: cell housing (Table S36) --------------------------------------------
    "al_wrought": _p("market for aluminium, wrought alloy", "GLO", "market for aluminium wrought alloy GLO"),
    "sheet_rolling_al": _p("market for sheet rolling, aluminium", "GLO", "market for sheet rolling aluminium GLO"),
    "impact_extrusion_al": _p("market for impact extrusion of aluminium, 1 stroke", "GLO",
                              "market for impact extrusion of aluminium 1 stroke GLO"),
    "cu_anode": _p("market for copper, anode", "GLO", "market for copper anode GLO"),
    "sheet_rolling_cu": _p("market for sheet rolling, copper", "GLO", "market for sheet rolling copper GLO"),
    "pet_bottle": _p("market for polyethylene terephthalate, granulate, bottle grade", "GLO",
                     "market for polyethylene terephthalate granulate bottle grade GLO"),
    # --- transport --------------------------------------------------------------
    # Voß's legs to a German factory, only ever subtracted (see the natural graphite):
    "sea_container": _p("market for transport, freight, sea, container ship", "GLO",
                        "market for transport freight sea container ship GLO"),
    "lorry_euro3_rer": _p("market for transport, freight, lorry 16-32 metric ton, EURO3", "RER",
                          "market for transport freight lorry 16-32 metric ton EURO3 RER"),
    # Voß's 1,000 km "Truck China" leg (ESI §3.1.1.1), kept on every cell
    # material as the upstream haul to a Chinese factory. Positive here, and
    # inside the natural-graphite factor already.
    "lorry_euro3_row": _p("market for transport, freight, lorry 16-32 metric ton, EURO3", "RoW",
                          "market for transport freight lorry 16-32 metric ton EURO3 RoW"),
    # Jasper's provider for the container's concrete block.
    "concrete_block_de": _p("concrete block production", "DE", "concrete block production DE"),
    # Jasper's upstream material legs, kept (ecoinvent's default 100 km lorry +
    # 600 km rail per tonne to the module and rack factories). His 3.11 "train,
    # fleet average" is 3.9.1's market group for freight train.
    "lorry_euro5_row": _p("market for transport, freight, lorry 16-32 metric ton, EURO5", "RoW",
                          "market for transport freight lorry 16-32 metric ton EURO5 RoW"),
    "lorry_euro6_row": _p("market for transport, freight, lorry 16-32 metric ton, EURO6", "RoW",
                          "market for transport freight lorry 16-32 metric ton EURO6 RoW"),
    "train_glo": _p("market group for transport, freight train", "GLO",
                    "market group for transport freight train GLO",
                    "Jasper's 'transport, freight, train, fleet average' [GLO] on 3.11"),
    # --- Jasper: modules, racks ------------------------------------------------
    "cu_cathode": _p("market for copper, cathode", "GLO", "market for copper cathode GLO",
                     "ASSUMED for the Ellingsen copper busbars"),
    "injection_moulding": _p("market for injection moulding", "GLO", "market for injection moulding GLO"),
    "injection_moulding_row": _p("injection moulding", "RoW", "injection moulding RoW"),
    "metal_working_factory": _p("market for metal working factory", "GLO", "market for metal working factory GLO"),
    "mw_steel": _p("market for metal working, average for steel product manufacturing", "GLO",
                   "market for metal working average for steel product manufacturing GLO"),
    "mw_steel_row": _p("metal working, average for steel product manufacturing", "RoW",
                       "metal working average for steel product manufacturing RoW"),
    "polypropylene": _p("market for polypropylene, granulate", "GLO", "market for polypropylene granulate GLO"),
    "polypropylene_row": _p("polypropylene production, granulate", "RoW", "polypropylene production granulate RoW"),
    "pwb_through_hole": _p("market for printed wiring board, through-hole mounted, unspecified, Pb free", "GLO",
                           "market for printed wiring board through-hole mounted unspecified Pb free GLO"),
    "pwb_surface": _p("market for printed wiring board, surface mounted, unspecified, Pb free", "GLO",
                      "market for printed wiring board surface mounted unspecified Pb free GLO"),
    "steel_low_alloyed": _p("market for steel, low-alloyed", "GLO", "market for steel low-alloyed GLO"),
    "steel_low_alloyed_hr": _p("market for steel, low-alloyed, hot rolled", "GLO",
                               "market for steel low-alloyed hot rolled GLO"),
    "powder_coat_steel": _p("market for powder coat, steel", "GLO", "market for powder coat steel GLO"),
    "cable": _p("market for cable, unspecified", "GLO", "market for cable unspecified GLO"),
    "electronics_control": _p("market for electronics, for control units", "GLO",
                              "market for electronics for control units GLO",
                              "Jasper's HV control box; ASSUMED for the BESS controller too"),
    "electronics_control_row": _p("electronics production, for control units", "RoW",
                                  "electronics production for control units RoW"),
    # --- Jasper: liquid cooling ------------------------------------------------
    "cable_connector": _p("market for cable, connector for computer, without plugs", "GLO",
                          "market for cable connector for computer without plugs GLO"),
    "drawing_pipe_steel": _p("market for drawing of pipe, steel", "GLO", "market for drawing of pipe steel GLO"),
    "nitrile": _p("market for nitrile-compound", "GLO", "market for nitrile-compound GLO"),
    "hdpe": _p("market for polyethylene, high density, granulate", "GLO",
               "market for polyethylene high density granulate GLO"),
    "hdpe_row": _p("polyethylene production, high density, granulate", "RoW",
                   "polyethylene production high density granulate RoW"),
    "steel_cr": _p("market for steel, chromium steel 18/8", "GLO", "market for steel chromium steel 18/8 GLO"),
    "steel_cr_hr": _p("market for steel, chromium steel 18/8, hot rolled", "GLO",
                      "market for steel chromium steel 18/8 hot rolled GLO"),
    "al_almg3": _p("market for aluminium alloy, AlMg3", "GLO", "market for aluminium alloy AlMg3 GLO"),
    "mw_al": _p("market for metal working, average for aluminium product manufacturing", "GLO",
                "market for metal working average for aluminium product manufacturing GLO"),
    "mw_al_row": _p("metal working, average for aluminium product manufacturing", "RoW",
                    "metal working average for aluminium product manufacturing RoW"),
    "mw_cr": _p("market for metal working, average for chromium steel product manufacturing", "GLO",
                "market for metal working average for chromium steel product manufacturing GLO"),
    "mw_cu": _p("market for metal working, average for copper product manufacturing", "GLO",
                "market for metal working average for copper product manufacturing GLO"),
    "mw_cu_row": _p("metal working, average for copper product manufacturing", "RoW",
                    "metal working average for copper product manufacturing RoW"),
    "mw_metal": _p("market for metal working, average for metal product manufacturing", "GLO",
                   "market for metal working average for metal product manufacturing GLO"),
    "mw_metal_row": _p("metal working, average for metal product manufacturing", "RoW",
                       "metal working average for metal product manufacturing RoW"),
    "synthetic_rubber": _p("market for synthetic rubber", "GLO", "market for synthetic rubber GLO"),
    "aux_heater_5kw": _p("market for auxiliary heating unit, electric, 5kW", "GLO",
                         "market for auxiliary heating unit electric 5kW GLO"),
    "brass": _p("market for brass", "RoW", "market for brass RoW"),
    "r134a": _p("market for refrigerant R134a", "GLO", "market for refrigerant R134a GLO",
                "Jasper's 'market for tetrafluoroethane, R134a' is a 3.11 name"),
    "r134a_row": _p("refrigerant R134a production", "RoW", "refrigerant R134a production RoW"),
    "base_oil": _p("market for base oil", "GLO", "market for base oil GLO"),
    "reinforcing_steel": _p("market for reinforcing steel", "GLO", "market for reinforcing steel GLO"),
    "zeolite": _p("market for zeolite, powder", "GLO", "market for zeolite powder GLO"),
    "al_cast": _p("market for aluminium, cast alloy", "GLO", "market for aluminium cast alloy GLO"),
    "al_cast_primary": _p("aluminium ingot, primary, to aluminium, cast alloy market", "GLO",
                          "aluminium ingot primary to aluminium cast alloy market GLO",
                          "the air conditioner's provider in Jasper - primary ingot, not the market"),
    "cast_iron": _p("market for cast iron", "GLO", "market for cast iron GLO"),
    "cast_iron_row": _p("cast iron production", "RoW", "cast iron production RoW"),
    "ethylene_glycol": _p("market for ethylene glycol", "GLO", "market for ethylene glycol GLO",
                          "Jasper's RoW market does not exist in 3.9.1"),
    # --- Jasper: air conditioner ----------------------------------------------
    "abs_row": _p("acrylonitrile-butadiene-styrene copolymer production", "RoW",
                  "acrylonitrile-butadiene-styrene copolymer production RoW"),
    "abs": _p("market for acrylonitrile-butadiene-styrene copolymer", "GLO",
              "market for acrylonitrile-butadiene-styrene copolymer GLO"),
    "capacitor_electrolyte": _p("market for capacitor, electrolyte type, > 2cm height", "GLO",
                                "market for capacitor electrolyte type > 2cm height GLO"),
    "plastic_recycled_in": _p("market for plastic granulate, unspecified, recycled", "IN",
                              "market for plastic granulate unspecified recycled IN"),
    "polyester_resin_row": _p("polyester resin production, unsaturated", "RoW",
                              "polyester resin production unsaturated RoW"),
    "hips_row": _p("polystyrene production, high impact", "RoW", "polystyrene production high impact RoW"),
    "pu_flexible_row": _p("market for polyurethane, flexible foam", "RoW",
                          "market for polyurethane flexible foam RoW"),
    "san_row": _p("styrene-acrylonitrile copolymer production", "RoW",
                  "styrene-acrylonitrile copolymer production RoW"),
    "inductor_choke": _p("market for inductor, ring core choke type", "GLO",
                         "market for inductor ring core choke type GLO"),
    # --- Jasper: container and fire ----------------------------------------------
    "gypsum_board": _p("market for gypsum plasterboard", "GLO", "market for gypsum plasterboard GLO"),
    "iso_container_20ft": _p("market for intermodal shipping container, 20-foot", "GLO",
                             "market for intermodal shipping container 20-foot GLO"),
    "osb": _p("market for oriented strand board", "RoW", "market for oriented strand board RoW"),
    "plywood": _p("market for plywood", "RoW", "market for plywood RoW"),
    "pu_flexible_fr": _p("market for polyurethane, flexible foam, flame retardant", "GLO",
                         "market for polyurethane flexible foam flame retardant GLO"),
    "wood_wool_board": _p("market for wood wool boards, cement bonded", "RoW",
                          "market for wood wool boards cement bonded RoW"),
    "zinc_coat": _p("market for zinc coat, coils", "GLO", "market for zinc coat coils GLO"),
    "e_motor_scooter": _p("market for electric motor, for electric scooter", "GLO",
                          "market for electric motor for electric scooter GLO"),
    "gfrp_pa": _p("market for glass fibre reinforced plastic, polyamide, injection moulded", "GLO",
                  "market for glass fibre reinforced plastic polyamide injection moulded GLO"),
    "steel_unalloyed": _p("market for steel, unalloyed", "GLO", "market for steel unalloyed GLO"),
    "electricity_mv_glo": _p("market group for electricity, medium voltage", "GLO",
                             "market group for electricity medium voltage GLO"),
    "steam_heat_row": _p("steam production, as energy carrier, in chemical industry", "RoW",
                         "steam production as energy carrier in chemical industry RoW"),
    "hydrogen_fluoride": _p("market for hydrogen fluoride", "RoW", "market for hydrogen fluoride RoW"),
    "tetrafluoroethylene": _p("market for tetrafluoroethylene", "GLO", "market for tetrafluoroethylene GLO"),
    "hazardous_waste_incineration": _p("market for hazardous waste, for incineration", "RoW",
                                       "market for hazardous waste for incineration RoW",
                                       "production waste, inside the gate; negative = waste sent"),
    "polycarbonate": _p("market for polycarbonate", "GLO", "market for polycarbonate GLO",
                        "Jasper's RoW market does not exist in 3.9.1"),
}

flows = {
    "co2": Flow(identity=("Carbon dioxide, fossil", ("air",)), query="Carbon dioxide fossil"),
}

# =============================================================================
# Activities - the cell (Voß)
# =============================================================================
_P = R.BESS_PARTS
_SGR, _NGR, _FEPO4, _LFP = _P["sgr"], _P["ngr"], _P["fepo4"], _P["lfp"]
_SBR, _PVDF, _SEP, _HOUSING, _CELL = _P["sbr"], _P["pvdf"], _P["separator"], _P["housing"], _P["cell"]

_voss_proxy = "a published carbon footprint, entered as fossil CO2 of its own size: GWP100 only"

voss_activities = [
    Activity(
        code=_SGR, name="Synthetic graphite, battery grade, Acheson powder route (Voß 2025)",
        reference_product="synthetic graphite", unit=_kg, location="CN",
        comment="Voß et al. 2025 ESI Table S5, from Carrère et al.'s industrial data: calcination "
                "of needle-coke feed, then graphitisation at ~3,000 C on the Chinese grid. "
                "ecoinvent 3.9.1's own synthetic graphite models the Acheson BLOCK route, which "
                "Voß show underestimates battery-grade graphite. The crucible and packaging "
                "lines are Carrère's footprints, not inventories (" + _voss_proxy + "). "
                "Voß's China-to-Berlin transport rows are not taken: they carry materials to Voß's "
                "German factory, and this cell is made in China.",
        technosphere=[
            ("petroleum_coke",       1.179, _kg,   "Table S5 calcination: green coke ('needle coke feed')"),
            ("heat_gas_small_row",   2.0,   _MJ,   "Table S5 calcination: natural gas"),
            ("electricity_mv_cn",   16.0,   _kwh,  "Table S5 graphitisation: electricity, CN"),
            ("lorry_euro3_row",     VOSS_LORRY_CN_TKM, _tkm, "Table S5 'Truck China', 1,000 km: upstream, kept"),
        ],
        biosphere=[
            ("co2", 0.190, _kg, "Table S5: direct CO2, calcination (rotary kiln and incinerator)"),
            ("co2", 0.725, _kg, "Table S5: direct CO2, graphitisation"),
            ("co2", SGR_CRUCIBLE_KGCO2E_PER_KG, _kg,
             "Table S5: crucible production, Carrère 11.9 kg CO2e/kg / 1.62 - " + _voss_proxy),
            ("co2", SGR_PACKAGING_KGCO2E_PER_KG, _kg,
             "Table S5: packaging media and graphite block, Carrère 0.7 / 1.62 - " + _voss_proxy),
        ],
        scale=SGR_ECONOMIC_ALLOCATION,
        scale_note="Voß's economic allocation: 98.8 % to graphite, 1.2 % to incinerator heat",
    ),
    Activity(
        code=_NGR, name="Natural graphite, battery grade (Engels 2022 via Voß 2025)",
        reference_product="natural graphite", unit=_kg, location="CN",
        comment="Voß ESI §3.1.1.2: Engels et al. 2022's 9.62 kg CO2e/kg from a Chinese producer, "
                "less the coating step and 25 % of spheronisation, plus transport China to Europe, "
                "= 5.19 kg CO2e/kg. " + _voss_proxy + ". Voß's sea and European lorry legs take "
                "the graphite to their German factory; this cell is made in China, so those two "
                "are taken back out, negative. The 1,000 km lorry leg in China stays, as the "
                "upstream haul to a Chinese cell factory (ASSUMED the same distance).",
        technosphere=[
            ("sea_container",  -VOSS_SEA_TKM,      _tkm, "removes Voß's sea leg to Europe, 18,500 km"),
            ("lorry_euro3_rer", -VOSS_LORRY_EU_TKM, _tkm, "removes Voß's lorry leg in Europe, 700 km"),
        ],
        biosphere=[("co2", NGR_KGCO2E_PER_KG, _kg, "Voß §3.1.1.2, 5.19 kg CO2e/kg - " + _voss_proxy)],
    ),
    Activity(
        code=_FEPO4, name="Iron phosphate, LFP precursor (Voß 2025)",
        reference_product="iron phosphate", unit=_kg, location="CN", production_amount=0.91,
        comment="Voß ESI Table S32, as printed: the inputs make 0.91 kg of FePO4, which is the "
                "amount one kg of LFP-C consumes (Table S31).",
        technosphere=[
            ("iron_sulfate",       1.00,  _kg,  "Table S32: FeSO4"),
            ("phosphoric_acid",    0.65,  _kg,  "Table S32: H3PO4, 85 %"),
            ("hydrogen_peroxide",  0.11,  _kg,  "Table S32: H2O2, 50 %"),
            ("sodium_hydroxide",   0.27,  _kg,  "Table S32: NaOH, 50 %"),
            ("water_softened",    50.00,  _kg,  "Table S32: water"),
            ("electricity_mv_cn",  0.972, _kwh, "Table S32: electricity, CN"),
            ("heat_gas_small_row", 8.10,  _MJ,  "Table S32: natural gas"),
        ],
    ),
    Activity(
        code=_LFP, name="LFP cathode active material, carbon coated (Voß 2025)",
        reference_product="lithium iron phosphate, carbon coated", unit=_kg, location="CN",
        comment="Voß ESI Table S31, after Quan et al.'s spray-drying and calcination route, with "
                "stoichiometric precursors. The in-China lorry leg is kept; Voß's sea and "
                "European legs serve their German factory and are not taken.",
        technosphere=[
            ("lorry_euro3_row",    VOSS_LORRY_CN_TKM, _tkm, "Table S31 'Truck China', 1,000 km: upstream, kept"),
            (FG(_FEPO4),           0.91,  _kg,  "Table S31: FePO4"),
            ("lithium_carbonate",  0.22,  _kg,  "Table S31: Li2CO3"),
            ("glucose",            0.13,  _kg,  "Table S31: glucose (the carbon coating)"),
            ("nitrogen_liquid",    0.21,  _kg,  "Table S31: nitrogen, inert atmosphere"),
            ("water_deionised",    3.05,  _kg,  "Table S31: deionised water"),
            ("electricity_mv_cn",  0.496, _kwh, "Table S31: electricity, CN"),
            ("heat_gas_small_row", 18.72, _MJ,  "Table S31: natural gas"),
        ],
        biosphere=[("co2", 0.17, _kg, "Table S31: direct CO2")],
    ),
    Activity(
        code=_SBR, name="Styrene-butadiene rubber binder (Voß 2025)",
        reference_product="styrene-butadiene rubber", unit=_kg, location="CN",
        comment="Voß ESI Table S35, after Chordia et al. The in-China lorry leg is kept; the sea "
                "and European legs serve Voß's German factory and are not taken.",
        technosphere=[
            ("lorry_euro3_row",    VOSS_LORRY_CN_TKM, _tkm, "Table S35 'Truck China', 1,000 km: upstream, kept"),
            ("butadiene",          0.757,  _kg,  "Table S35"),
            ("styrene",            0.252,  _kg,  "Table S35"),
            ("chemical_organic",   0.008,  _kg,  "Table S35: DDM"),
            ("fatty_acid",         0.051,  _kg,  "Table S35"),
            ("chemical_inorganic", 3e-6,   _kg,  "Table S35: potassium persulfate"),
            ("water_deionised",   27.5,    _kg,  "Table S35"),
            ("electricity_mv_cn",  4e-4,   _kwh, "Table S35"),
            ("steam_chemical_row", 0.0055, _kg,  "Table S35"),
        ],
    ),
    Activity(
        code=_PVDF, name="PVDF binder (Hu et al. via Voß 2025)",
        reference_product="polyvinylidene fluoride", unit=_kg, location="CN",
        comment="Voß ESI §3.1.3.1: Hu et al.'s 60.6 kg CO2e/kg for PVDF made in China. ecoinvent "
                "3.9.1 has no PVDF. " + _voss_proxy + ".",
        biosphere=[("co2", PVDF_KGCO2E_PER_KG, _kg, "Hu et al., 60.6 kg CO2e/kg - " + _voss_proxy)],
    ),
    Activity(
        code=_SEP, name="Battery separator, PE/PP (ecoinvent 3.8 via Voß 2025)",
        reference_product="battery separator", unit=_kg, location="CN",
        comment="Voß ESI §3.1.3.4 take ecoinvent 3.8's 'battery separator production - CN' at 5.06 "
                "kg CO2e/kg, judging 3.9.1's 39.6 'unrealistically high', after Peters et al. "
                "3.9.1 scores 34.4 (market) and 39.5 (CN) here. " + _voss_proxy + ".",
        biosphere=[("co2", SEPARATOR_KGCO2E_PER_KG, _kg, "ecoinvent 3.8 value, 5.06 kg CO2e/kg - " + _voss_proxy)],
    ),
    Activity(
        code=_HOUSING, name="Prismatic cell housing (Voß 2025)",
        reference_product="cell housing", unit=_kg, location="CN",
        comment="Voß ESI Table S36, the weight distribution of Fraunhofer FFB's large prismatic "
                "cell. The table repeats its first two rows across a page break (cap sheet 0.204, "
                "busbar copper 0.061/0.062); they are taken once, which is what makes the rows sum "
                "to 0.987 kg per kg as printed rather than 1.25. ASSUMED: the whole 330 g is "
                "charged on this table. Voß say fixing and isolation materials (Table S37, all "
                "PET) are part of the housing but give no split, and S36 already carries PET; "
                "putting part of the 330 g on S37 instead would lower the housing. The in-China "
                "lorry leg is kept; the sea and European legs are not taken.",
        technosphere=[
            ("lorry_euro3_row",     VOSS_LORRY_CN_TKM, _tkm, "S36 'Truck China', 1,000 km: upstream, kept"),
            ("al_wrought",          0.204, _kg, "S36 cap metal sheet"),
            ("sheet_rolling_al",    0.204, _kg, "S36 cap metal sheet"),
            ("cu_anode",            0.061, _kg, "S36 busbar anode, copper"),
            ("sheet_rolling_cu",    0.061, _kg, "S36 busbar anode, copper"),
            ("al_wrought",          0.032, _kg, "S36 busbar anode, aluminium"),
            ("sheet_rolling_al",    0.032, _kg, "S36 busbar anode, aluminium"),
            ("al_wrought",          0.006, _kg, "S36 connection terminals"),
            ("sheet_rolling_al",    0.006, _kg, "S36 connection terminals"),
            ("pet_bottle",          0.029, _kg, "S36 isolation busbars"),
            ("pet_bottle",          0.013, _kg, "S36 isolation terminal anode"),
            ("pet_bottle",          0.006, _kg, "S36 isolation terminal cathode"),
            ("al_wrought",          0.006, _kg, "S36 bursting membrane"),
            ("sheet_rolling_al",    0.006, _kg, "S36 bursting membrane"),
            ("al_wrought",          0.042, _kg, "S36 terminal anode"),
            ("sheet_rolling_al",    0.042, _kg, "S36 terminal anode"),
            ("al_wrought",          0.045, _kg, "S36 terminal cathode"),
            ("sheet_rolling_al",    0.045, _kg, "S36 terminal cathode"),
            ("pet_bottle",          0.003, _kg, "S36 sealing rubber"),
            ("al_wrought",          0.003, _kg, "S36 sealing plate"),
            ("sheet_rolling_al",    0.003, _kg, "S36 sealing plate"),
            ("al_wrought",          0.537, _kg, "S36 housing"),
            ("impact_extrusion_al", 0.537, _kg, "S36 housing"),
        ],
    ),
]

_g = CELL_BILL_G
voss_activities.append(Activity(
    code=_CELL, name="LFP/graphite prismatic cell, materials (Voß 2025)",
    reference_product="LFP/graphite prismatic cell, unassembled", unit=_unit, location="CN",
    comment=f"Voß et al. 2025 Table 3, LFP/graphite: one {CELL_WH:g} Wh, {CELL_STATED_MASS_G:,.1f} g "
            f"prismatic cell ({CELL_STATED_WH_PER_KG:g} Wh/kg), the cell Jasper et al. 2026 put in "
            f"their container. Materials only - the factory energy is added per kWh in "
            f"{R.BESS_CELL_CN} / {R.BESS_CELL_DE}. Graphite "
            f"{GRAPHITE_SYNTHETIC_SHARE:.0%} synthetic / {1 - GRAPHITE_SYNTHETIC_SHARE:.0%} natural, "
            "Voß's market-share benchmark.",
    technosphere=[
        (FG(_SGR),            _g["anode_active"] * GRAPHITE_SYNTHETIC_SHARE / 1000, _kg,
         f"Table 3 anode active material {_g['anode_active']} g x {GRAPHITE_SYNTHETIC_SHARE:.0%} synthetic"),
        (FG(_NGR),            _g["anode_active"] * (1 - GRAPHITE_SYNTHETIC_SHARE) / 1000, _kg,
         f"Table 3 anode active material {_g['anode_active']} g x {1 - GRAPHITE_SYNTHETIC_SHARE:.0%} natural"),
        ("cmc",               _g["anode_cmc"] / 1000,       _kg, "Table 3 anode CMC"),
        (FG(_SBR),            _g["anode_sbr"] / 1000,       _kg, "Table 3 anode SBR"),
        ("carbon_black",      _g["anode_carbon"] / 1000,    _kg, "Table 3 anode carbon black"),
        ("cu_collector_foil", _g["anode_cu_foil"] / 1000,   _kg, "Table 3 anode current collector, copper"),
        (FG(_LFP),            _g["cathode_active"] / 1000,  _kg, "Table 3 cathode active material, LFP-C"),
        (FG(_PVDF),           _g["cathode_pvdf"] / 1000,    _kg, "Table 3 cathode PVDF"),
        ("carbon_black",      _g["cathode_carbon"] / 1000,  _kg, "Table 3 cathode carbon black"),
        ("al_collector_foil", _g["cathode_al_foil"] / 1000, _kg, "Table 3 cathode current collector, aluminium"),
        ("electrolyte",       _g["electrolyte"] / 1000,     _kg, "Table 3 electrolyte"),
        (FG(_SEP),            _g["separator"] / 1000,       _kg, "Table 3 separator"),
        (FG(_HOUSING),        _g["housing"] / 1000,         _kg, "Table 3 cell housing"),
        # Voß ESI §3.1.3 add the standard legs "additionally" to every material
        # they take from a dataset or a published factor. The in-China lorry leg
        # is the upstream haul to the cell factory and is kept, 1 t·km per kg;
        # the graphite, LFP-C, SBR and housing carry theirs inside their own
        # activities, and the natural graphite inside its factor.
        ("lorry_euro3_row", VOSS_LORRY_CN_TKM * (_g["anode_cmc"] + _g["anode_carbon"] + _g["cathode_carbon"]
                                                 + _g["anode_cu_foil"] + _g["cathode_al_foil"]
                                                 + _g["cathode_pvdf"] + _g["electrolyte"]
                                                 + _g["separator"]) / 1000, _tkm,
         "§3.1.3 'Truck China', 1,000 km, on CMC, carbon black, both foils, PVDF, electrolyte and separator"),
    ],
))


def _cell_per_kwh(code, factory, electricity, heat):
    return Activity(
        code=code, name=f"LFP/graphite prismatic cell, per kWh, made in {factory} (Voß 2025)",
        reference_product="LFP/graphite battery cell capacity", unit=_kwh, location=factory,
        comment=f"{CELLS_PER_KWH:.4f} Voß cells of {CELL_WH:g} Wh make one kWh of NAMEPLATE cell "
                f"capacity, plus Degen et al. 2023's gigafactory energy as restated by Jasper "
                f"§2.4.1: {CELL_FACTORY_KWH_ELECTRICITY:g} kWh electricity and "
                f"{CELL_FACTORY_KWH_GAS:g} kWh natural gas per kWh, the gas charged as "
                f"{CELL_FACTORY_MJ_HEAT:g} MJ of heat. Factory in {factory}. Excludes Voß's "
                "processing materials (NMP, argon, N2, compressed air), which they do not tabulate.",
        technosphere=[
            (FG(_CELL), CELLS_PER_KWH, _unit, f"1000 / {CELL_WH:g} Wh per cell"),
            (electricity, CELL_FACTORY_KWH_ELECTRICITY, _kwh, f"cell factory electricity, {factory}"),
            (heat, CELL_FACTORY_MJ_HEAT, _MJ, f"cell factory gas, {factory}"),
        ],
    )


voss_activities += [
    _cell_per_kwh(R.BESS_CELL_CN, "CN", "electricity_mv_cn", "heat_gas_industrial_row"),
    _cell_per_kwh(R.BESS_CELL_DE, "DE", "electricity_mv_de", "heat_gas_industrial_rer"),
]
CELL_CODE = {"CN": R.BESS_CELL_CN, "DE": R.BESS_CELL_DE}[CELL_FACTORY]

# =============================================================================
# Activities - the container (Jasper, liquid-cooled LFP)
# =============================================================================
_MODULE, _RACK_HOUSING, _RACK, _PLATE = _P["module"], _P["rack_housing"], _P["rack"], _P["plate"]
_COMPRESSOR, _DRIER, _PUMP, _COOLANT = _P["compressor"], _P["drier"], _P["pump"], _P["coolant"]
_AC_IN, _AC_OUT, _AC, _LCU, _COOLING = (_P["ac_indoor"], _P["ac_outdoor"], _P["ac"], _P["lcu"],
                                        _P["cooling"])
_DAMPER, _CONTAINER, _HFC, _TANK = _P["damper"], _P["container"], _P["hfc"], _P["tank"]
_PANEL, _FIRE, _CSS = _P["panel"], _P["fire"], _P["css"]

_J = "Jasper et al. 2026 SI"
# Jasper's transport rows come in two patterns. Per tonne of component, 1,000 km
# lorry + 8,000 km sea + 1,000 km European rail is the part leaving his Chinese
# factory for his German site: delivery to site, outside this study's boundary.
# 100 km lorry + 600 km rail is ecoinvent's default for materials reaching a
# factory: upstream, so it is kept (module, rack, rack housing).
_no_transport = " Jasper's delivery-to-site rows excluded."
_upstream_legs = " Jasper's upstream material legs kept; no delivery to site."

jasper_activities = [
    Activity(
        code=_MODULE, name="Battery module, 47 kWh, for liquid-cooled container (Jasper 2026)",
        reference_product="battery module", unit=_unit, location="CN",
        comment=f"{_J}, 'production of battery module for CSS', liquid-cooled: 48 LFP cells in "
                "series, module packaging after Baumann et al. (2020) and Ellingsen et al. (2014). "
                f"The cells are Voß's, made in {CELL_FACTORY}. Ellingsen's busbars are not in the SI "
                f"and are mapped to their metals (ASSUMED, {BIMETALLIC_COPPER_SHARE:.0%} copper for "
                "the bimetallic set)." + _upstream_legs,
        technosphere=[
            (FG(CELL_CODE), CSS_MODULE_KWH, _kwh, "'LFP based LIB (Voß et al.)', 47000/176.6 kg = 47 kWh"),
            ("al_wrought",       3.1302, _kg, "Aluminium endbars (Ellingsen) - ASSUMED wrought Al"),
            ("sheet_rolling_al", 3.1302, _kg, "Aluminium endbars (Ellingsen) - ASSUMED rolled"),
            ("cu_cathode",       6.6517 * BIMETALLIC_COPPER_SHARE, _kg, "Bimetallic busbars and washers (Ellingsen) - copper share"),
            ("sheet_rolling_cu", 6.6517 * BIMETALLIC_COPPER_SHARE, _kg, "Bimetallic busbars and washers (Ellingsen) - copper share"),
            ("al_wrought",       6.6517 * (1 - BIMETALLIC_COPPER_SHARE), _kg, "Bimetallic busbars and washers (Ellingsen) - aluminium share"),
            ("sheet_rolling_al", 6.6517 * (1 - BIMETALLIC_COPPER_SHARE), _kg, "Bimetallic busbars and washers (Ellingsen) - aluminium share"),
            ("cu_cathode",       0.9586, _kg, "Copper end-busbars (Ellingsen) - ASSUMED copper"),
            ("sheet_rolling_cu", 0.9586, _kg, "Copper end-busbars (Ellingsen) - ASSUMED rolled"),
            ("injection_moulding",     2.7838,  _kg,  _J),
            ("metal_working_factory",  4.58e-10, _unit, _J),
            ("mw_steel",               28.4727, _kg,  _J),
            ("polypropylene",          2.7838,  _kg,  _J),
            ("pwb_through_hole",       0.6442,  _kg,  _J),
            ("steel_low_alloyed",      28.4727, _kg,  _J),
            ("lorry_euro5_row",        3.9857,  _tkm, _J + ", upstream: materials to the module factory"),
            ("train_glo",             23.9144,  _tkm, _J + ", upstream: materials to the module factory"),
        ],
    ),
    Activity(
        code=_RACK_HOUSING, name="Battery rack housing, steel, per kg (Jasper 2026)",
        reference_product="battery rack housing", unit=_kg, location="GLO",
        comment=f"{_J}, 'Rack, 48x43, for stationary battery storage system'." + _upstream_legs,
        technosphere=[
            ("metal_working_factory", 4.58e-10, _unit, _J),
            ("mw_steel",              1.0,      _kg,   _J),
            ("powder_coat_steel",     0.055,    "square meter", _J),
            ("steel_low_alloyed",     1.0,      _kg,   _J),
            ("lorry_euro5_row",       0.10053075, _tkm, _J + ", upstream: materials to the rack factory"),
            ("train_glo",             0.6031845,  _tkm, _J + ", upstream: materials to the rack factory"),
        ],
    ),
    Activity(
        code=_RACK, name="Battery rack, liquid-cooled, 8 modules, 376 kWh (Jasper 2026)",
        reference_product="battery rack", unit=_unit, location="GLO",
        comment=f"{_J}, 'Battery rack (liquid cooled)'. The HV control box is ecoinvent's "
                "electronics for control units, as Jasper name it." + _upstream_legs,
        technosphere=[
            (FG(_MODULE),        CSS_MODULES_PER_RACK, _unit, _J),
            ("cable",            17.907, _kg, _J),
            ("electronics_control", 15.5, _kg, "High voltage control box (electronics for control units)"),
            (FG(_RACK_HOUSING),  431.8,  _kg, _J),
            ("lorry_euro6_row",  0.0962, _tkm, _J + ", upstream"),
            ("train_glo",        0.58,   _tkm, _J + ", upstream"),
        ],
    ),
    Activity(
        code=_PLATE, name="Cooling plate in battery module, liquid cooling (Jasper 2026)",
        reference_product="cooling plate", unit=_unit, location="GLO",
        comment=_J + ".",
        technosphere=[
            ("al_almg3",         5.2,  _kg, _J),
            ("mw_al",            5.2,  _kg, _J),
            ("synthetic_rubber", 0.32, _kg, _J),
        ],
    ),
    Activity(
        code=_COMPRESSOR, name="Chiller compressor, per kg (Jasper 2026)",
        reference_product="compressor", unit=_kg, location="GLO",
        comment=_J + ", after Catrini et al. (2018).",
        technosphere=[
            ("base_oil",          0.0404, _kg, _J),
            ("cu_anode",          0.1442, _kg, _J),
            ("mw_cr",             0.8154, _kg, _J),
            ("mw_cu",             0.1442, _kg, _J),
            ("reinforcing_steel", 0.8154, _kg, _J),
        ],
    ),
    Activity(
        code=_DRIER, name="Chiller filter drier, per kg (Jasper 2026)",
        reference_product="filter drier", unit=_kg, location="GLO",
        comment=_J + ".",
        technosphere=[
            ("mw_cr",    0.5325, _kg, _J),
            ("steel_cr", 0.5325, _kg, _J),
            ("zeolite",  0.4675, _kg, _J),
        ],
    ),
    Activity(
        code=_PUMP, name="Coolant pump, per kg (Jasper 2026)",
        reference_product="pump for liquid cooling unit", unit=_kg, location="GLO",
        comment=_J + ".",
        technosphere=[
            ("al_cast",   0.4402, _kg, _J),
            ("cast_iron", 0.4821, _kg, _J),
            ("cu_anode",  0.0777, _kg, _J),
            ("mw_al",     0.4402, _kg, _J),
            ("mw_cu",     0.0777, _kg, _J),
            ("mw_metal",  0.4821, _kg, _J),
        ],
    ),
    Activity(
        code=_COOLANT, name="Secondary coolant, 50:50 ethylene glycol and water (Jasper 2026)",
        reference_product="secondary coolant", unit=_kg, location="GLO",
        comment=_J + ".",
        technosphere=[
            ("ethylene_glycol", 0.5, _kg, _J + " (RoW market in the source, GLO in 3.9.1)"),
            ("water_deionised", 0.5, _kg, _J),
        ],
    ),
    Activity(
        code=_AC_IN, name="Air conditioner indoor unit, per kg (Jasper 2026)",
        reference_product="indoor unit", unit=_kg, location="GLO",
        comment=_J + ", from the EPD of a 3.6 kW, 37 kg unit.",
        technosphere=[
            ("abs_row",                  0.1158, _kg, _J),
            ("al_cast_primary",          0.0979, _kg, _J),
            ("capacitor_electrolyte",    0.0125, _kg, _J),
            ("cu_anode",                 0.1392, _kg, _J),
            ("electronics_control_row",  0.0552, _kg, _J),
            ("injection_moulding",       0.5654, _kg, _J),
            ("mw_al_row",                0.0979, _kg, _J),
            ("mw_cu_row",                0.1392, _kg, _J),
            ("mw_steel_row",             0.1298, _kg, _J),
            ("plastic_recycled_in",      0.0097, _kg, _J),
            ("polyester_resin_row",      0.0656, _kg, _J),
            ("hdpe_row",                 0.0662, _kg, _J),
            ("polypropylene_row",        0.0406, _kg, _J),
            ("hips_row",                 0.1668, _kg, _J),
            ("pu_flexible_row",          0.0501, _kg, _J),
            ("steel_low_alloyed",        0.1298, _kg, _J),
            ("san_row",                  0.0505, _kg, _J),
        ],
    ),
    Activity(
        code=_AC_OUT, name="Air conditioner outdoor unit, per kg (Jasper 2026)",
        reference_product="outdoor unit", unit=_kg, location="GLO",
        comment=_J + ", from the EPD of a 3.6 kW, 37 kg unit.",
        technosphere=[
            ("al_cast_primary",          0.0648, _kg, _J),
            ("capacitor_electrolyte",    0.0259, _kg, _J),
            ("cast_iron_row",            0.0523, _kg, _J),
            ("cu_anode",                 0.206,  _kg, _J),
            ("electronics_control_row",  0.0301, _kg, _J),
            ("inductor_choke",           0.0829, _kg, _J),
            ("injection_moulding_row",   0.0645, _kg, _J),
            ("mw_al_row",                0.0648, _kg, _J),
            ("mw_cu_row",                0.206,  _kg, _J),
            ("mw_metal_row",             0.0523, _kg, _J),
            ("mw_steel_row",             0.4736, _kg, _J),
            ("plastic_recycled_in",      0.0101, _kg, _J),
            ("polypropylene_row",        0.0188, _kg, _J),
            ("steel_low_alloyed",        0.4736, _kg, _J),
            ("san_row",                  0.0147, _kg, _J),
            ("r134a_row",                0.021,  _kg, _J),
        ],
    ),
    Activity(
        code=_AC, name="Air conditioner, per kg (Jasper 2026)",
        reference_product="air conditioner", unit=_kg, location="GLO",
        comment=_J + ".",
        technosphere=[
            (FG(_AC_IN),  0.27, _kg, _J),
            (FG(_AC_OUT), 0.73, _kg, _J),
        ],
    ),
    Activity(
        code=_LCU, name="Liquid cooling unit, 40 kW chiller (Jasper 2026)",
        reference_product="liquid cooling unit", unit=_unit, location="GLO",
        comment=_J + ": condenser, evaporator, compressor, pump and PTC heater, after Catrini et "
                "al. (2018) scaled to 40 kW, plus three 5 kW auxiliary heaters. R134a is the "
                "charge, not a leak.",
        technosphere=[
            ("aux_heater_5kw", 3,      _unit, _J),
            ("brass",          0.4,    _kg,   _J),
            (FG(_COMPRESSOR),  44.36,  _kg,   _J),
            ("cu_anode",       7.44,   _kg,   _J),
            (FG(_DRIER),       0.73,   _kg,   _J),
            ("mw_cr",          153.18, _kg,   _J),
            ("mw_cu",          7.44,   _kg,   _J),
            ("mw_metal",       0.4,    _kg,   _J),
            (FG(_PUMP),        29.96,  _kg,   _J),
            ("steel_cr",       37.83,  _kg,   _J),
            ("steel_cr",       34.46,  _kg,   _J),
            ("steel_cr_hr",    80.89,  _kg,   _J),
            ("synthetic_rubber", 0.068, _kg,  _J),
            ("r134a",          9.0,    _kg,   _J + " ('market for tetrafluoroethane, R134a' in 3.11)"),
        ],
    ),
    Activity(
        code=_COOLING, name="Liquid cooling system for 20 ft container (Jasper 2026)",
        reference_product="liquid cooling system", unit=_unit, location="GLO",
        comment=_J + ": one cooling plate per module, nitrile hoses, steel pipework, the 40 kW "
                "chiller, 126 kg of coolant, and one 3.6 kW air conditioner for the "
                "balance-of-system cabinet." + _no_transport,
        technosphere=[
            (FG(_AC),             37.0,   _kg,   _J),
            ("cable_connector",   8.0,    "meter", _J),
            (FG(_PLATE),          CSS_COOLING_PLATES, _unit, _J + " - num_powersection x num_batterypack"),
            ("drawing_pipe_steel", 138.92, _kg,  _J),
            (FG(_LCU),            1,      _unit, _J),
            ("nitrile",           CSS_NITRILE_KG, _kg, _J + " - 0.75 kg x 64 modules"),
            ("hdpe",              1.37,   _kg,   _J),
            (FG(_COOLANT),        126.43, _kg,   _J),
            ("steel_cr",          138.92, _kg,   _J),
        ],
    ),
    Activity(
        code=_DAMPER, name="Fire damper (Jasper 2026)",
        reference_product="fire damper", unit=_unit, location="GLO",
        comment=_J + ".",
        technosphere=[
            ("chemical_inorganic",   0.9,  _kg, _J),
            ("e_motor_scooter",      1.2,  _kg, _J),
            ("gfrp_pa",              0.09, _kg, _J),
            ("injection_moulding",   0.09, _kg, _J),
            ("plastic_recycled_in",  0.09, _kg, _J),
            ("steel_cr",             0.06, _kg, _J),
            ("steel_low_alloyed",    0.12, _kg, _J),
            ("steel_low_alloyed_hr", 4.14, _kg, _J),
            ("synthetic_rubber",     0.02, _kg, _J),
            ("zinc_coat",            0.5,  "square meter", _J),
        ],
    ),
    Activity(
        code=_CONTAINER, name="20 ft battery container, fire-lined (Jasper 2026)",
        reference_product="battery container", unit=_unit, location="GLO",
        comment=_J + ": ecoinvent's 20 ft intermodal container lined with cement board, OSB and "
                "flame-retardant PU after McKinnon et al. (2022), with two fire dampers. ecoinvent "
                "3.9.1's container scores ~2.9 t CO2e; Jasper's container line on 3.11 is ~3x "
                "this inventory's." + _no_transport,
        technosphere=[
            (FG(_DAMPER),          2,      _unit, _J),
            ("gypsum_board",       664.66, _kg,   _J),
            ("iso_container_20ft", 1,      _unit, _J),
            ("osb",                0.76,   "cubic meter", _J),
            ("plywood",            0.14,   "cubic meter", _J),
            ("pu_flexible_fr",     2.5,    _kg,   _J),
            ("steel_low_alloyed_hr", 5.0,  _kg,   _J),
            ("wood_wool_board",    0.19,   "cubic meter", _J),
            ("zinc_coat",          3.18,   "square meter", _J),
            # Jasper list the block on the CSS, one per container; it sits here so
            # the fuel cell, which takes this container at one per MW, shares it.
            ("concrete_block_de",  43_900.0, _kg, _J + ", 'concrete block' 43.9 t on the CSS (liquid cooled)"),
        ],
    ),
    Activity(
        code=_HFC, name="Heptafluoropropane (HFC-227ea) fire suppressant, per kg (Jasper 2026)",
        reference_product="heptafluoropropane", unit=_kg, location="GLO",
        comment=_J + ". The 0.1 kg of tetrafluoroethylene is the source's avoided co-product and "
                "is kept as it is printed, the way SMR keeps its avoided electricity. The "
                "suppressant is the charge, not a release - nothing is emitted here.",
        technosphere=[
            ("electricity_mv_glo",  5.0,   _kwh, _J),
            ("steam_heat_row",      20.0,  _MJ,  _J),
            ("hydrogen_fluoride",   0.131, _kg,  _J),
            ("tetrafluoroethylene", 0.981, _kg,  _J),
            ("tetrafluoroethylene", -0.1,  _kg,  _J + " - avoided product"),
            ("hazardous_waste_incineration", -0.02, _kg, _J + " - production waste sent to treatment"),
        ],
    ),
    Activity(
        code=_TANK, name="Fire extinguisher tank, charged, per kg (Jasper 2026)",
        reference_product="fire extinguisher tank", unit=_kg, location="GLO",
        comment=_J + ".",
        technosphere=[
            (FG(_HFC),         0.7, _kg, _J),
            ("steel_unalloyed", 0.3, _kg, _J),
        ],
    ),
    Activity(
        code=_PANEL, name="Fire suppression panel, per kg (Jasper 2026)",
        reference_product="fire suppression panel", unit=_kg, location="GLO",
        comment=_J + ".",
        technosphere=[
            ("abs",           0.5472, _kg, _J),
            ("cable",         0.088,  _kg, _J),
            ("polycarbonate", 0.1159, _kg, _J + " (RoW market in the source, GLO in 3.9.1)"),
            ("pwb_surface",   0.2488, _kg, _J),
        ],
    ),
    Activity(
        code=_FIRE, name="Fire suppression system for 20 ft container (Jasper 2026)",
        reference_product="fire suppression system", unit=_unit, location="GLO",
        comment=_J + "." + _no_transport,
        technosphere=[
            (FG(_TANK),          21.0, _kg, _J),
            (FG(_PANEL),         2.5,  _kg, _J),
            ("mw_steel",         30.0, _kg, _J),
            ("steel_low_alloyed", 30.0, _kg, _J),
        ],
    ),
    Activity(
        code=_CSS, name=f"Battery DC block, liquid-cooled LFP container, {CSS_KWH:,.0f} kWh (Jasper 2026)",
        reference_product="battery DC block", unit=_unit, location="GLO",
        comment=f"{_J}, 'CSS (liquid cooled)': {CSS_RACKS} racks of {CSS_MODULES_PER_RACK} modules, "
                f"{CSS_KWH:,.0f} kWh nameplate, {CSS_KW:,.0f} kW. The BESS controller has no "
                "inventory in the SI and is charged as electronics for control units (ASSUMED). "
                "EXCLUDES, from Jasper's own CSS: the 800 kg power conversion system (battery.py "
                "charges the power term separately); the 5,500 kg transformer (charged per MW of "
                "cap_batt_p by transformers.py since 15 Oct); delivery to site; end-of-life. The 43.9 t "
                "concrete block is on the container activity (since 21 Oct).",
        technosphere=[
            (FG(_RACK),           CSS_RACKS, _unit, _J),
            ("electronics_control", 30.0,    _kg,   "BESS controller - ASSUMED electronics for control units"),
            (FG(_CONTAINER),      1,         _unit, _J),
            (FG(_FIRE),           1,         _unit, _J),
            (FG(_COOLING),        1,         _unit, _J),
        ],
    ),
    Activity(
        code=R.BESS_DC_BLOCK_KWH,
        name="Battery DC block, liquid-cooled LFP, per kWh nameplate (Jasper 2026 / Voß 2025)",
        reference_product="battery energy capacity, nameplate", unit=_kwh, location="GLO",
        comment=f"One kWh of NAMEPLATE cell capacity in Jasper's liquid-cooled container: 1/"
                f"{CSS_KWH:,.0f} of the DC block. This is what optimisation/battery.py scores for "
                "the energy term, and it divides by battery.USABLE_FRACTION because cap_batt_e is "
                "the energy the battery can swing, not the cells it holds.",
        technosphere=[(FG(_CSS), 1.0 / CSS_KWH, _unit, f"1 / {CSS_KWH:,.0f} kWh")],
    ),
]

activities = voss_activities + jasper_activities

check()


def inventory() -> Inventory:
    return Inventory(name="grid battery (Jasper 2026 container, Voß 2025 cell)",
                     database=R.BESS_DB, processes=processes, flows=flows,
                     activities=activities)


def describe() -> str:
    return "\n".join([
        f"Cell: Voß et al. 2025 Table 3, {CELL_WH:g} Wh, {sum(CELL_BILL_G.values()):,.1f} g, "
        f"{CELL_STATED_WH_PER_KG:g} Wh/kg -> {CELLS_PER_KWH:.4f} cells/kWh",
        f"  graphite {GRAPHITE_SYNTHETIC_SHARE:.0%} synthetic (Acheson powder, Table S5) / "
        f"{1 - GRAPHITE_SYNTHETIC_SHARE:.0%} natural (Engels, 5.19 less the legs to Europe)",
        f"  factory {CELL_FACTORY}: {CELL_FACTORY_KWH_ELECTRICITY:g} kWh electricity + "
        f"{CELL_FACTORY_KWH_GAS:g} kWh gas per kWh (Degen 2023 via Jasper)",
        f"  Voß's own German cell, with transport and processing materials: "
        f"{VOSS_LFP_CELL_DE_75_25} kg CO2e/kWh - {R.BESS_CELL_DE} should land near it",
        f"Container: Jasper et al. 2026 liquid-cooled LFP, {CSS_RACKS} x {CSS_MODULES_PER_RACK} x "
        f"{CSS_MODULE_KWH:g} kWh = {CSS_KWH:,.0f} kWh, {CSS_KW:,.0f} kW",
        "  excluded: " + "; ".join(f"{k} ({v[0]:,.0f} {v[1]})" for k, v in CSS_EXCLUDED.items()),
        f"Per kWh nameplate: {R.BESS_DC_BLOCK_KWH}; battery.py divides by USABLE_FRACTION.",
    ])
