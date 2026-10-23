"""
PEM fuel cell — Babatunde 2024 stack, Usai 2021 balance of plant, 1 kWh from it.
=============================================================================

Four activities in one database:

* ``pemfc_stack_1kw_babatunde`` — cradle-to-gate manufacture of **one 1 kW
  PEM fuel cell stack**, transcribed from the paper's supplementary Table S1.
* ``pemfc_bop_stationary_1kw`` — the **balance of plant for 1 kW** of a
  stationary, hydrogen-fed unit: Usai et al. 2021's process loops, plus an
  inverter and a share of a container.
* ``pemfc_service_stationary_1kw`` — **one service of 1 kW**: air filter and
  coolant.
* ``pemfc_op_1kwh_h2`` — **1 kWh of net AC electricity, low voltage**, from a
  1 kW hydrogen-fed PEMFC system: hydrogen, and the three above amortised.

Stack — source and scope
------------------------
Babatunde, O.M., Akintayo, B.D., Emezirinwune, M.U., Olanrewaju, O.A. (2024).
"Environmental Impact Assessment of a 1 kW Proton-Exchange Membrane Fuel
Cell: A Mid-Point and End-Point Analysis." *Hydrogen* 5(2), 352–373.
https://doi.org/10.3390/hydrogen5020020 — supplementary Table S1 documents
the ecoinvent 3.7.1 dataset ``fuel cell production, stack polymer electrolyte
membrane, 2kW electrical, future`` that the study runs in SimaPro 9.2 with
ReCiPe 2016. Manufacturing only: the paper's 32,000 h operating life is
stated in its scope but nothing operational is inventoried.

**Two scale factors, both deliberate.** ``FC_SCALE`` is the product of:

1. ``FC_KW_SCALE = 0.5`` — Table S1's reference product is a 2 kW stack but
   the paper reports everything per 1 kW. Halving is what the paper itself
   did: every value in its Tables S2–S4 is about 2× the corresponding
   value in its headline Tables 3–5.
2. ``FC_S1_SCALE = 1.878606235`` — Table S1 as printed does **not** reproduce
   the paper's own results. Every amount is smaller than the live ecoinvent
   dataset it documents by this uniform factor (verified exchange by
   exchange: activated carbon 0.0008 vs 0.00150288, aluminium 0.3 vs
   0.563582, graphite 4.5 vs 8.45373, platinum 0.00075 vs 0.00140895,
   electricity 16.9 vs 31.748 kWh — identical to 9 significant figures).
   At face value the inventory reproduces only ~53 % of the paper's impacts;
   scaled, it reproduces them. A defect in the published table, not a
   modelling choice — amounts below stay as printed so they can be checked
   against the PDF, and the correction is applied once at write time.

**Validated against the paper** (``validate.fc_stack_vs_paper``): on ReCiPe
2016 v1.03 (H), damage totals 1.00 / 0.99 / 1.10 of the paper's Table 5,
mid-point median ratio 1.003 over 18 categories, end-point 1.013 over 22.
The misses (ecotoxicity, metal resources, land and water use) are the
categories whose factors changed most between ecoinvent 3.7.1 and 3.9.1.

**One substitution:** Table S1 prints one aggregated electricity row and one
heat row; the ecoinvent dataset splits them over regional markets. The GLO
market groups are used for both — the single-row equivalent of what the
paper prints — and reproduce the combustion-driven categories to ~1–2 %.

Table S1's two "by-products" are waste sent for treatment, so negative
technosphere amounts against the waste markets (ecoinvent's own convention).

Operation — source and scope
----------------------------
Functional unit 1 kWh net AC. Every parameter is a literature value, not a
fitted one:

1. **Hydrogen** = 1 / (η × LHV), with η a *net AC* efficiency so parasitic
   loads (air compressor, pumps, controls, inverter) are inside it.
   ``FC_ETA_NET_BOL = 0.50`` LHV is bracketed by DOE's stationary 1–25 kWe
   target of ≥45 % (on natural gas, so including reformer losses a pure-H2
   system does not pay), a reported ~51.6 % for a 1 kW H2-fed PEMFC, and the
   ~50 % usually quoted for mid-size stationary PEMFC; 0.45–0.55 is the
   defensible range and ±0.05 moves the result ±10 %. The 0.95 derate follows
   the convention that end of life is a 10 % drop in cell voltage (Stropnik
   et al. 2022); degrading linearly puts the lifetime mean at 95 % of BOL.
2. **Stack** = 1 / (1 kW × 30,000 h). Stationary H2 PEM stacks are refurbished
   at 24-30k running hours (Nedstack datasheets); Bionaz et al. 2022 use 40k;
   Babatunde's 32k is ecoinvent's own figure, not an independent one.
3. **Balance of plant** = ``pemfc_bop_stationary_1kw`` below, over 80,000 h
   (DOE's 100 kW-3 MW stationary class, and ecoinvent's own system life).
4. **Maintenance** = ``pemfc_service_stationary_1kw`` below, once per 8,000 h.

Balance of plant — source and scope
-----------------------------------
This used to be ecoinvent's ``fuel cell production, polymer electrolyte
membrane, 2kW electrical, future`` net of its stack: a **natural-gas domestic
micro-CHP** ("operation with connection to low pressure gas network"), carrying
fuel-processor items, a hot-water kit and 400 km of installer driving, scaled
linearly from 2 kW to MW. 469 t CO2e per MW. Its maintenance was reformer-
catalyst replacement. None of it describes a hydrogen-fed MW-class unit.

No published inventory does, either. A 2026 systematic review (Energies
19:3808) finds BoP inventories still "simplified using obsolete" bills; the
only H2-fed *stationary* system with a component bill is a 3 kW UPS (Stropnik
et al. 2018, Energy 165:824), and every heavy-duty LCA (Gentilucci et al.
2024, SAE 2024-24-0020, 200 kW; Syré et al. 2024, WEVJ 15:114) reuses an
automotive one. So the BoP is assembled, the way the battery is:

**Process loops — Usai et al. 2021**, J Cleaner Prod 280:125086, SI Table 1
(``usai 2021 fc lci per kw.pdf``): an 80 kW H2 PEM system, per kW net, every
line already named as an ecoinvent process. Air (compression-expansion motor,
filter, ducting, sensor), water (humidifier, Nafion tubes, pre-cooler,
demister), heat (fan, pumps, radiators, antifreeze), fuel (blower, ejectors,
pipes), controller, wiring, frame, fasteners. Two amounts are per *system* in
the printed table though labelled per kW — the 3 coolant pumps and 16 m of
wiring (Miotti's per-system figure) — and are divided by 80 here; as printed
they rebuild Usai's own heat and "other" results 17x and 35x over. Everything
else is as printed. Rebuilt on 3.9.1 the loops come to ~82 % of Usai's own
854 kg CO2e/80 kW (their results workbook): the table rounds to two decimals,
which loses most of the radiator and controller (0.27 and 0.63 of Usai).

**What a vehicle has and a container does not, and the reverse.** The
compression-expansion motor stands in for a stationary air blower (heavier,
so it errs high); the belly pan stands in for the module frame. Added for a
stationary unit, neither of which a vehicle FC system carries:
- *power conversion*: ecoinvent's 500 kW inverter, the dataset the battery's
  power term uses. The vehicle's DC/DC boost sits in its drivetrain, not its
  FC system, so nothing is counted twice.
- *enclosure*: the battery's own fire-lined 20 ft container (Jasper et al.
  2026, ``bess.py``), one per ``FC_KW_PER_CONTAINER`` = 1 MW. ASSUMED - no
  source states MW per container for fuel cells.

**Maintenance** is what an H2-fed unit actually consumes: an air filter and
a coolant change per service (Usai's own amounts), every 8,000 h (ASSUMED;
Battelle 2016 gives a one-year interval for backup units). No reformer
catalyst, no platinum top-up, no installer driving. Stack replacement is not
maintenance: it is the stack line, on the optimiser's max(calendar, duty)
rule.

**Benchmarks**, whole systems cradle-to-gate per kW: Usai 37.6 (no tank),
Miotti 29, Gentilucci 30.5-51.4 (200 kW HD), Ballard 73 (70 kW module, its own
note), Stropnik/Bionaz 405 (3 kW UPS). The vehicle figures carry no inverter
or enclosure; this one does, and its stack (Babatunde's 2 kW graphite-plate
unit) is heavier than any automotive stack.

**No direct biosphere flows — deliberately.** A hydrogen PEMFC emits only
water, and it is not inventoried, for the same reason ecoinvent's own PEMFC
operation datasets do not: the product water is the electrolyser's feed water
coming back out, already counted as consumed upstream. Adding it as a
``Water → air`` emission would double-count (ReCiPe's water-use factor for
water emitted to air is +1.0).

Boundary, as everywhere in this study: cradle-to-gate, no end-of-life, no
delivery transport.

What the optimiser reads: ``optimisation/fuel_cell.py`` splits the operation
activity into stack (per MW, replaced on max(calendar, duty)), balance of
plant (likewise) and maintenance (per MWh), and excludes the hydrogen, which
the LP supplies explicitly.
"""
from __future__ import annotations

from optimiser_lca import registry as R
from optimiser_lca.common import FG, Activity, Flow, Inventory, Process

# =============================================================================
# Parameters
# =============================================================================
# --- stack: the two scale factors (see the docstring for the evidence) --------
FC_KW_SCALE = 0.5           # TRANSCRIBED - Table S1's reference product is a 2 kW stack; the paper's FU is 1 kW
FC_S1_SCALE = 1.878606235   # DERIVED - Table S1's printed amounts are uniformly this factor smaller than
                            # the ecoinvent dataset it documents; set to 1.0 to build it verbatim
FC_SCALE    = FC_KW_SCALE * FC_S1_SCALE

# --- operation ------------------------------------------------------------------
FC_RATED_POWER_KW     = 1.0        # TRANSCRIBED - the paper's 1 kW stack
FC_H2_LHV_KWH_PER_KG  = 33.33      # physical constant - hydrogen lower heating value, 120 MJ/kg
FC_ETA_NET_BOL        = 0.50       # ASSUMED - net AC electrical efficiency at beginning of life, LHV basis
FC_DEGRADATION_DERATE = 0.95       # ASSUMED - mean-over-life efficiency as a fraction of BOL; 1.0 = none
# Duty lives. Calendar lives are the optimiser's (optimisation/fuel_cell.py).
FC_STACK_LIFETIME_H   = 30_000     # ASSUMED - Nedstack stack refurbishment 24-30k h; Bionaz 2022 40k
FC_SYSTEM_LIFETIME_H  = 80_000     # TRANSCRIBED - ecoinvent's system-dataset comment; DOE's 100 kW-3 MW class
FC_SERVICE_INTERVAL_H = 8_000      # ASSUMED; Battelle 2016 gives one year for backup units
# Which hydrogen the fuel cell burns: (database, code). Any per-kg-H2 activity
# works — swap in AE_OP / SOEC_OP / SMR for a different supply chain.
FC_H2_SOURCE = (R.HYDROGEN_DB, R.PEM_OP)

# --- balance of plant: Usai et al. 2021 SI Table 1 -------------------------------
USAI_SYSTEM_KW = 80.0               # TRANSCRIBED - the system the table describes
# Printed per kW but per SYSTEM (see the docstring): divided by USAI_SYSTEM_KW.
USAI_COOLANT_PUMPS_PER_SYSTEM = 3   # "40W pump pc 3"
USAI_WIRING_M_PER_SYSTEM = 16.0     # "Cables m 16" - Miotti's 16 m per system
# Stationary additions.
FC_INVERTER_KW = 500.0              # ASSUMED - ecoinvent's 500 kW inverter, as battery.PCS_ACTIVITY
FC_KW_PER_CONTAINER = 1_000.0       # ASSUMED - one 20 ft container per MW; sweep 500-2,000

# --- derived --------------------------------------------------------------------
FC_ETA_NET_MEAN  = FC_ETA_NET_BOL * FC_DEGRADATION_DERATE
FC_H2_PER_KWH    = 1.0 / (FC_ETA_NET_MEAN * FC_H2_LHV_KWH_PER_KG)      # kg H2 / kWh AC
FC_STACK_PER_KWH = 1.0 / (FC_RATED_POWER_KW * FC_STACK_LIFETIME_H)    # unit / kWh AC
FC_BOP_PER_KWH   = 1.0 / (FC_RATED_POWER_KW * FC_SYSTEM_LIFETIME_H)   # kW of BoP / kWh AC
FC_SERVICE_PER_KWH = 1.0 / (FC_RATED_POWER_KW * FC_SERVICE_INTERVAL_H)  # kW-services / kWh AC


def check_parameters() -> str:
    if not 0.0 < FC_ETA_NET_BOL <= 1.0:
        raise ValueError("FC_ETA_NET_BOL must be a fraction in (0, 1].")
    if not 0.0 < FC_DEGRADATION_DERATE <= 1.0:
        raise ValueError("FC_DEGRADATION_DERATE must be a fraction in (0, 1].")
    if min(FC_STACK_LIFETIME_H, FC_SYSTEM_LIFETIME_H, FC_SERVICE_INTERVAL_H) <= 0:
        raise ValueError("Fuel cell lifetimes and service interval must be positive.")
    if FC_SYSTEM_LIFETIME_H < FC_STACK_LIFETIME_H:
        raise AssertionError("the balance of plant must outlive the stack it carries")
    if FC_KW_PER_CONTAINER <= 0 or FC_INVERTER_KW <= 0:
        raise ValueError("container and inverter ratings must be positive")
    return (f"OK - eta {FC_ETA_NET_MEAN:.3f} mean, {FC_H2_PER_KWH:.5f} kg H2/kWh, "
            f"stack {FC_STACK_PER_KWH:.3e}/kWh, BoP {FC_BOP_PER_KWH:.3e}/kWh, "
            f"service {FC_SERVICE_PER_KWH:.3e}/kWh")


check_parameters()

# =============================================================================
# Processes
# =============================================================================
processes = {
    # --- stack, Table S1 ---------------------------------------------------------
    "activated_carbon": Process(
        query="market for activated carbon granular GLO", pick=0,
        identity=("market for activated carbon, granular", "GLO", "activated carbon, granular")),
    "aluminium_wrought": Process(
        query="market for aluminium wrought alloy GLO", pick=1,
        identity=("market for aluminium, wrought alloy", "GLO", "aluminium, wrought alloy"),
        why="hit 0 is the ingot-to-market transfer; the market is the dataset"),
    "building_hall": Process(
        query="market for building hall steel construction GLO", pick=0,
        identity=("market for building, hall, steel construction", "GLO", "building, hall, steel construction")),
    "building_multi": Process(
        query="market for building multi-storey GLO", pick=0,
        identity=("market for building, multi-storey", "GLO", "building, multi-storey")),
    "electricity_mv": Process(
        query="market group for electricity medium voltage GLO", pick=0,
        identity=("market group for electricity, medium voltage", "GLO", "electricity, medium voltage"),
        why="Table S1 prints one aggregated 16.9 kWh row; the ecoinvent dataset splits it "
            "over 8 regional markets - the GLO market group is the single-row equivalent"),
    "glass_fibre": Process(
        query="market for glass fibre GLO", pick=1,
        identity=("market for glass fibre", "GLO", "glass fibre"),
        why="hit 0 is glass-fibre reinforced plastic; Usai name glass fibre"),
    "graphite": Process(
        query="market for graphite GLO", pick=0,
        identity=("market for graphite", "GLO", "graphite")),
    "heat_natural_gas": Process(
        query="market group for heat district or industrial natural gas GLO", pick=0,
        identity=("market group for heat, district or industrial, natural gas", "GLO",
                  "heat, district or industrial, natural gas"),
        why="same aggregation as electricity (Table S1: one 22.3 MJ row, dataset: 3 regional markets)"),
    "isopropanol": Process(
        query="market for isopropanol RoW", pick=0,
        identity=("market for isopropanol", "RoW", "isopropanol")),
    "phenolic_resin": Process(
        query="market for phenolic resin RoW", pick=0,
        identity=("market for phenolic resin", "RoW", "phenolic resin")),
    "platinum": Process(
        query="market for platinum GLO", pick=0,
        identity=("market for platinum", "GLO", "platinum")),
    "steel_chromium_188": Process(
        query="market for steel chromium steel 18/8 hot rolled GLO", pick=0,
        identity=("market for steel, chromium steel 18/8, hot rolled", "GLO",
                  "steel, chromium steel 18/8, hot rolled")),
    "tetrafluoroethylene": Process(
        query="market for tetrafluoroethylene GLO", pick=1,
        identity=("market for tetrafluoroethylene", "GLO", "tetrafluoroethylene"),
        why="hit 0 is PTFE film on glass; the polymer itself"),
    "water_deionised": Process(
        query="market for water deionised RoW", pick=0,
        identity=("market for water, deionised", "RoW", "water, deionised")),
    "waste_plastic": Process(
        query="market for waste plastic industrial electronics RoW", pick=0,
        identity=("market for waste plastic, industrial electronics", "RoW",
                  "waste plastic, industrial electronics")),
    "waste_pvf": Process(
        query="market for waste polyvinylfluoride RoW", pick=0,
        identity=("market for waste polyvinylfluoride", "RoW", "waste polyvinylfluoride")),
    # --- balance of plant: Usai et al. 2021 SI Table 1, processes as Usai name them.
    # Where Usai's ecoinvent 3.6 GLO market is regional in 3.9.1, RoW stands in,
    # Usai having aimed at "global average productions".
    "bop_al_cast": Process(
        query="market for aluminium cast alloy GLO",
        identity=("market for aluminium, cast alloy", "GLO", "aluminium, cast alloy")),
    "bop_steel_la_hr": Process(
        query="market for steel low-alloyed hot rolled GLO",
        identity=("market for steel, low-alloyed, hot rolled", "GLO", "steel, low-alloyed, hot rolled")),
    "bop_magnet": Process(
        query="permanent magnet production for electric motor GLO",
        identity=("permanent magnet production, for electric motor", "GLO",
                  "permanent magnet, for electric motor"),
        why="Usai's own provider for the compression-expansion motor's magnets"),
    "bop_air_filter": Process(
        query="market for air filter in exhaust air valve GLO",
        identity=("market for air filter, in exhaust air valve", "GLO", "air filter, in exhaust air valve")),
    "bop_extrusion_pipes": Process(
        query="market for extrusion plastic pipes GLO",
        identity=("market for extrusion, plastic pipes", "GLO", "extrusion, plastic pipes")),
    "bop_electronics": Process(
        query="market for electronics for control units GLO",
        identity=("market for electronics, for control units", "GLO", "electronics, for control units")),
    "bop_pps": Process(
        query="market for polyphenylene sulfide GLO",
        identity=("market for polyphenylene sulfide", "GLO", "polyphenylene sulfide")),
    "bop_so3": Process(
        query="market for sulfur trioxide RoW",
        identity=("market for sulfur trioxide", "RoW", "sulfur trioxide")),
    "bop_extrusion_film": Process(
        query="market for extrusion plastic film GLO",
        identity=("market for extrusion, plastic film", "GLO", "extrusion, plastic film"),
        why="Usai name 'extrusion production, plastic film' RER; 3.9.1 carries it as 'extrusion, "
            "plastic film' (RER/RoW); the GLO market is taken, 0.01 kg"),
    "bop_pu_rigid": Process(
        query="market for polyurethane rigid foam RoW",
        identity=("market for polyurethane, rigid foam", "RoW", "polyurethane, rigid foam"),
        why="Usai's proxy for the humidifier's cordierite honeycomb"),
    "bop_nylon6": Process(
        query="market for nylon 6 RoW",
        identity=("market for nylon 6", "RoW", "nylon 6")),
    "bop_hdpe": Process(
        query="market for polyethylene high density granulate GLO",
        identity=("market for polyethylene, high density, granulate", "GLO",
                  "polyethylene, high density, granulate")),
    "bop_pump_40w": Process(
        query="market for pump 40W GLO",
        identity=("market for pump, 40W", "GLO", "pump, 40W")),
    "bop_ethylene_glycol": Process(
        query="market for ethylene glycol GLO",
        identity=("market for ethylene glycol", "GLO", "ethylene glycol")),
    "bop_cable": Process(
        query="market for cable three-conductor cable GLO",
        identity=("market for cable, three-conductor cable", "GLO", "cable, three-conductor cable")),
    # --- Gramc et al. 2025 stack (sensitivity basis) -----------------------------
    "carbon_black": Process(
        query="market for carbon black GLO",
        identity=("market for carbon black", "GLO", "carbon black")),
    "pet_amorphous": Process(
        query="market for polyethylene terephthalate granulate amorphous GLO",
        identity=("market for polyethylene terephthalate, granulate, amorphous", "GLO",
                  "polyethylene terephthalate, granulate, amorphous"),
        why="the PEN/PET subgasket film; PEN has no dataset"),
    "cfrp_proxy": Process(
        query="market for carbon fibre reinforced plastic injection moulded GLO",
        identity=("market for carbon fibre reinforced plastic, injection moulded", "GLO",
                  "carbon fibre reinforced plastic, injection moulded"),
        why="the carbon-cloth GDL; ecoinvent 3.9.1 has no carbon fibre on its own. PROXY"),
    "silicone_rer": Process(
        query="market for silicone product RER",
        identity=("market for silicone product", "RER", "silicone product")),
    "grtp": Process(
        query="market for glass fibre reinforced plastic polyamide injection moulded GLO",
        identity=("market for glass fibre reinforced plastic, polyamide, injection moulded",
                  "GLO", "glass fibre reinforced plastic, polyamide, injection moulded"),
        why="Gramc's glass-fibre-reinforced thermoplastic endplates"),
    "copper_cathode": Process(
        query="market for copper cathode GLO",
        identity=("market for copper, cathode", "GLO", "copper, cathode")),
    "steel_unalloyed": Process(
        query="market for steel unalloyed GLO",
        identity=("market for steel, unalloyed", "GLO", "steel, unalloyed")),
    "electricity_mv_rer": Process(
        query="market group for electricity medium voltage RER",
        identity=("market group for electricity, medium voltage", "RER", "electricity, medium voltage"),
        why="Gramc's 'European grid mix' for stack manufacture"),
    # --- stationary additions ---------------------------------------------------
    "inverter_500kw": Process(
        query="market for inverter 500kW GLO",
        identity=("market for inverter, 500kW", "GLO", "inverter, 500kW"),
        why="the same power-conversion dataset as the battery's power term"),
}

# Table S1's "Inputs from environment" + "Emissions to air/water". Categories fix
# the compartment - the two "Water" flows are the same substance in different ones.
flows = {
    "propanol_air": Flow(identity=("Propanol", ("air", "urban air close to ground")),
                         query="Propanol", why="the isopropanol input, evaporated"),
    "water_air":    Flow(identity=("Water", ("air",)), query="Water air"),
    "water_water":  Flow(identity=("Water", ("water",)), query="Water water", pick=2),
    "occupation_industrial": Flow(identity=("Occupation, industrial area", ("natural resource", "land")),
                                  query="Occupation industrial area"),
    "transformation_from": Flow(identity=("Transformation, from unspecified", ("natural resource", "land")),
                                query="Transformation from unspecified"),
    "transformation_to": Flow(identity=("Transformation, to industrial area", ("natural resource", "land")),
                              query="Transformation to industrial area"),
}

# =============================================================================
# Activities
# =============================================================================
_kg, _kwh, _MJ, _unit, _m2, _m3 = ("kilogram", "kilowatt hour", "megajoule", "unit",
                                   "square meter", "cubic meter")

STACK = Activity(
    code=R.FC_STACK,
    name="Fuel cell stack production, PEM, 1 kW (Babatunde et al. 2024)",
    reference_product="fuel cell stack, polymer electrolyte membrane, 1 kW electrical",
    unit=_unit, location="GLO",
    comment="Cradle-to-gate manufacture of one 1 kW PEM fuel cell stack. Babatunde et al. "
            "2024, Hydrogen 5(2), 352-373, supplementary Table S1 (which documents the "
            "ecoinvent 3.7.1 dataset 'fuel cell production, stack polymer electrolyte "
            f"membrane, 2kW electrical, future'). Amounts as printed in Table S1, scaled by "
            f"{FC_SCALE:.9f} = {FC_KW_SCALE} (2 kW reference product -> 1 kW functional unit, "
            f"the same halving the paper applies between its Tables S2-S4 and Tables 3-5) x "
            f"{FC_S1_SCALE} (Table S1's printed amounts are uniformly this factor smaller "
            "than the ecoinvent dataset they document, and reproduce only ~53% of the "
            "paper's own results without it). Manufacturing only - no use phase.",
    # Amounts exactly as printed in Table S1 (per one 2 kW stack); FC_SCALE is
    # applied once, when the exchanges are written.
    scale=FC_SCALE, scale_note="(FC_KW_SCALE x FC_S1_SCALE)",
    technosphere=[
        # --- Inputs from technosphere ---
        ("activated_carbon",     0.0008,  _kg,  "Activated carbon, granular"),
        ("aluminium_wrought",    0.3,     _kg,  "Aluminium, wrought alloy — end plates / housing"),
        ("building_hall",        0.00022, _m2,  "Building, hall, steel construction — factory infrastructure"),
        ("building_multi",       0.0013,  _m3,  "Building, multi-storey — factory infrastructure"),
        ("electricity_mv",      16.9,     _kwh, "Electricity, medium voltage — stack manufacturing"),
        ("glass_fibre",          0.1,     _kg,  "Glass fibre"),
        ("graphite",             4.5,     _kg,  "Graphite — bipolar plates"),
        ("heat_natural_gas",    22.3,     _MJ,  "Heat, district or industrial, natural gas — stack manufacturing"),
        ("isopropanol",          0.0095,  _kg,  "Isopropanol — electrode ink solvent"),
        ("phenolic_resin",       1.1,     _kg,  "Phenolic resin — bipolar plate binder"),
        ("platinum",             0.00075, _kg,  "Platinum — anode + cathode catalyst"),
        ("steel_chromium_188",   0.1,     _kg,  "Steel, chromium steel 18/8, hot rolled — tie rods / current collectors"),
        ("tetrafluoroethylene",  0.052,   _kg,  "Tetrafluoroethylene — PFSA (Nafion) membrane precursor"),
        ("water_deionised",      0.006,   _kg,  "Water, deionised"),
        # --- By-products (Table S1) — waste to treatment, hence negative ---
        ("waste_plastic",       -6.6,     _kg,  "Waste plastic, industrial electronics — to treatment"),
        ("waste_pvf",           -0.052,   _kg,  "Waste polyvinylfluoride — to treatment"),
    ],
    biosphere=[
        ("propanol_air",           0.0095, _kg,                "Propanol to air — the isopropanol input, evaporated"),
        ("water_air",              9e-7,   _m3,                "Water to air"),
        ("water_water",            5.1e-6, _m3,                "Water to water"),
        ("occupation_industrial",  0.0395, "square meter-year", "Occupation, industrial area"),
        ("transformation_from",    0.0008, _m2,                "Transformation, from unspecified"),
        ("transformation_to",      0.0008, _m2,                "Transformation, to industrial area"),
    ],
)

GRAMC_STACK_KW = 48.0      # TRANSCRIBED - Gramc et al. 2025's functional unit

# Gramc, J. et al. (2025), "Ecodesign as a key concept for improving the life
# cycle environmental performance of proton-exchange membrane fuel cells",
# Int J Hydrogen Energy 104:623-634, doi:10.1016/j.ijhydene.2024.08.020, open
# access. Table 3, reference case, per 48 kWe automotive stack, divided by 48.
# A *sensitivity* basis, not a like-for-like replacement for Babatunde: an
# automotive stack with stainless-steel bipolar plates (Babatunde's is a
# graphite-plate 2 kW unit), components mostly raw material only plus a total
# 410 kWh electricity estimate, on ecoinvent 3.9 + Sphera in GaBi. Their own
# result is 1.21 t CO2e per stack (25.2 kg/kW, EF 3.1), MEA ~78 %, Pt 63.5 %
# (Mori 2023). End-of-life burdens are 1.8 % of their total and recycling
# credits are reported separately; neither is taken here. Nafion is on the
# tetrafluoroethylene precursor, as in the Babatunde stack, where Gramc use an
# elementary-flow inventory.
GRAMC_STACK = Activity(
    code=R.FC_STACK_GRAMC,
    name="Fuel cell stack production, PEM, 1 kW (Gramc et al. 2025, 48 kW automotive)",
    reference_product="fuel cell stack, polymer electrolyte membrane, 1 kW electrical",
    unit="unit", location="GLO",
    comment="1 kW of the 48 kWe reference stack in Gramc et al. 2025 (IJHE 104:623, Table 3), "
            "amounts as printed per stack x 1/48. Cradle-to-gate; no end-of-life, no "
            "recycling credit. Sensitivity basis for the Babatunde stack.",
    scale=1.0 / GRAMC_STACK_KW, scale_note="(per 48 kWe stack -> per kW)",
    technosphere=[
        ("platinum",            0.026,  "kilogram", "Pt, virgin - 26 g, 0.465 mg/cm2"),
        ("carbon_black",        0.039,  "kilogram", "Carbon black - catalyst support"),
        ("tetrafluoroethylene", 0.144,  "kilogram", "PFSA ionomer - Nafion precursor proxy"),
        ("water_deionised",     0.490,  "kilogram", "Water - ink"),
        ("isopropanol",         0.220,  "kilogram", "Alcohol - ink solvent"),
        ("pet_amorphous",       1.820,  "kilogram", "PEN/PET subgasket film"),
        ("bop_extrusion_film",  1.820,  "kilogram", "Subgasket film extrusion"),
        ("cfrp_proxy",          1.249,  "kilogram", "Carbon cloth GDL - CFRP proxy"),
        ("steel_chromium_188", 21.623,  "kilogram", "Bipolar plates, stainless steel"),
        ("silicone_rer",        1.265,  "kilogram", "Gaskets, silicone"),
        ("grtp",                3.800,  "kilogram", "Endplates, glass-fibre-reinforced thermoplastic"),
        ("copper_cathode",      0.950,  "kilogram", "Current collectors, copper"),
        ("steel_chromium_188",  0.852,  "kilogram", "Connecting components, chromium steel"),
        ("steel_unalloyed",     2.820,  "kilogram", "Connecting components, steel"),
        ("electricity_mv_rer", 410.0,   "kilowatt hour", "Stack production, European grid mix"),
    ],
    biosphere=[
        ("propanol_air", 0.220, "kilogram", "ink alcohol, evaporated"),
    ],
)

_m = "meter"
_U = "Usai et al. 2021 SI Table 1, per kW net"
_per_sys = 1.0 / USAI_SYSTEM_KW

BOP = Activity(
    code=R.FC_BOP,
    name="Fuel cell balance of plant, stationary, hydrogen-fed, per kW",
    reference_product="fuel cell balance of plant, polymer electrolyte membrane, stationary",
    unit=_unit, location="GLO",
    comment="Everything a hydrogen-fed PEM fuel cell needs besides its stack, for 1 kW net. "
            "Process loops from Usai et al. 2021 (J Cleaner Prod 280:125086) SI Table 1, an "
            "80 kW H2 system, per kW net, each line on the ecoinvent process Usai name: air "
            "management (compression-expansion motor, filter, ducting, mass-flow sensor), water "
            "management (humidifier, Nafion tubes, pre-cooler, demister), heat management (fan, "
            "coolant pumps, radiators, antifreeze), fuel management (blower, ejectors, pipes), "
            "controller, wiring, frame and fasteners. The 3 coolant pumps and 16 m of wiring are "
            f"per system in the printed table and are divided by {USAI_SYSTEM_KW:g} kW here. "
            f"Stationary additions: ecoinvent's {FC_INVERTER_KW:g} kW inverter, and the battery's "
            f"fire-lined 20 ft container (Jasper et al. 2026) at one per {FC_KW_PER_CONTAINER:,.0f} "
            "kW (ASSUMED). Replaces ecoinvent's 2 kW natural-gas micro-CHP net of its stack, "
            "which carried a fuel processor, a hot-water kit and installer driving. Cradle-to-"
            "gate; no end-of-life; no delivery transport.",
    technosphere=[
        # --- air management ---
        ("steel_chromium_188",  0.02,  _kg, f"{_U}: compression-expansion motor, chromium steel"),
        ("bop_al_cast",         0.04,  _kg, f"{_U}: compression-expansion motor, aluminium"),
        ("bop_steel_la_hr",     0.01,  _kg, f"{_U}: compression-expansion motor, low-alloyed steel"),
        ("bop_magnet",          0.01,  _kg, f"{_U}: compression-expansion motor, permanent magnet"),
        ("bop_air_filter",      0.013, _unit, f"{_U}: air filter"),
        ("tetrafluoroethylene", 0.001, _kg, f"{_U}: air ducting"),
        ("bop_extrusion_pipes", 0.03,  _kg, f"{_U}: air ducting, plastic pipes"),
        ("bop_electronics",     0.004, _kg, f"{_U}: mass flow sensor"),
        # --- water management ---
        ("bop_pps",             0.01,  _kg, f"{_U}: humidifier housing"),
        ("bop_so3",             0.0,   _kg, f"{_U}: Nafion tubes, sulfur trioxide (printed 0.00)"),
        ("tetrafluoroethylene", 0.01,  _kg, f"{_U}: Nafion tubes"),
        ("bop_extrusion_film",  0.01,  _kg, f"{_U}: Nafion tubes, extrusion"),
        ("aluminium_wrought",   0.08825, _kg, f"{_U}: air pre-cooler"),
        ("bop_pu_rigid",        0.019, _kg, f"{_U}: humidifier honeycomb, proxy for cordierite"),
        ("bop_nylon6",          0.03,  _kg, f"{_U}: demister"),
        # --- heat management ---
        ("bop_hdpe",            0.01,  _kg, f"{_U}: fan"),
        ("bop_pump_40w",        USAI_COOLANT_PUMPS_PER_SYSTEM * _per_sys, _unit,
         f"{_U}: coolant pumps, printed '3' - per system, so / {USAI_SYSTEM_KW:g} kW"),
        ("bop_al_cast",         0.01,  _kg, f"{_U}: radiators"),
        ("bop_ethylene_glycol", 0.01,  _kg, f"{_U}: antifreeze"),
        # --- fuel management ---
        ("bop_steel_la_hr",     0.06,  _kg, f"{_U}: hydrogen blower"),
        ("steel_chromium_188",  0.02,  _kg, f"{_U}: hydrogen blower"),
        ("aluminium_wrought",   0.03,  _kg, f"{_U}: blower, ejectors, pipes"),
        # --- controller and other ---
        ("bop_electronics",     0.03,  _kg, f"{_U}: controller"),
        ("bop_cable",           USAI_WIRING_M_PER_SYSTEM * _per_sys, _m,
         f"{_U}: wiring, printed '16 m' - per system (Miotti), so / {USAI_SYSTEM_KW:g} kW"),
        ("aluminium_wrought",   0.10,  _kg, f"{_U}: mounting and belly pan - the module frame here"),
        ("bop_steel_la_hr",     0.013, _kg, f"{_U}: fasteners"),
        # --- stationary additions ---
        ("inverter_500kw", 1.0 / FC_INVERTER_KW, _unit,
         f"Power conversion to AC: ecoinvent's {FC_INVERTER_KW:g} kW inverter, per kW"),
        (FG(R.BESS_PARTS["container"], database=R.BESS_DB), 1.0 / FC_KW_PER_CONTAINER, _unit,
         f"Enclosure: the battery's fire-lined 20 ft container (Jasper 2026), one per "
         f"{FC_KW_PER_CONTAINER:,.0f} kW - ASSUMED"),
    ],
)

SERVICE = Activity(
    code=R.FC_SERVICE,
    name="Fuel cell service, stationary, hydrogen-fed, per kW",
    reference_product="maintenance, polymer electrolyte membrane fuel cell, stationary",
    unit=_unit, location="GLO",
    comment="One service of 1 kW of a hydrogen-fed PEM fuel cell: the air filter and the "
            "antifreeze replaced, in Usai et al. 2021's own amounts. Battelle 2016 lists these, "
            "with a de-ionisation polisher whose resin no source quantifies, as the recurring "
            "items of an H2 backup unit. No reformer catalyst, no platinum top-up, no driving - "
            "the replaced ecoinvent event was a natural-gas micro-CHP's. Stack replacement is "
            "the stack line, not maintenance.",
    technosphere=[
        ("bop_air_filter",      0.013, _unit, f"{_U}: air filter, replaced"),
        ("bop_ethylene_glycol", 0.01,  _kg,   f"{_U}: antifreeze, replaced"),
    ],
)

OPERATION = Activity(
    code=R.FC_OP,
    name="Electricity, low voltage, from PEM fuel cell (hydrogen)",
    reference_product="electricity, low voltage",
    unit=_kwh, location="GB",
    comment=f"1 kWh net AC from a {FC_RATED_POWER_KW:g} kW hydrogen-fed PEMFC system. "
            f"Hydrogen {FC_H2_PER_KWH:.5f} kg/kWh = 1/(eta {FC_ETA_NET_MEAN:.3f} x LHV "
            f"{FC_H2_LHV_KWH_PER_KG} kWh/kg), where eta is a NET AC efficiency "
            f"({FC_ETA_NET_BOL:.2f} at beginning of life x {FC_DEGRADATION_DERATE:.2f} for "
            "degradation to a 10% cell-voltage end-of-life criterion), so parasitic loads are "
            f"inside it. Stack (Babatunde et al. 2024) over {FC_STACK_LIFETIME_H:,} h; balance "
            f"of plant (Usai et al. 2021 + inverter + container) over {FC_SYSTEM_LIFETIME_H:,} h; "
            f"one service every {FC_SERVICE_INTERVAL_H:,} h. No direct biosphere flows: the "
            "product water is the electrolyser's feed water returning, already counted as "
            "consumed upstream.",
    technosphere=[
        (FG(FC_H2_SOURCE[1], database=FC_H2_SOURCE[0]), FC_H2_PER_KWH, _kg,
         f"Hydrogen — 1 / (eta {FC_ETA_NET_MEAN:.3f} x LHV {FC_H2_LHV_KWH_PER_KG} kWh/kg)"),
        (FG(R.FC_STACK), FC_STACK_PER_KWH, _unit,
         f"Stack (Babatunde et al. 2024) over {FC_STACK_LIFETIME_H:,} h"),
        (FG(R.FC_BOP), FC_BOP_PER_KWH, _unit,
         f"Balance of plant over {FC_SYSTEM_LIFETIME_H:,} h"),
        (FG(R.FC_SERVICE), FC_SERVICE_PER_KWH, _unit,
         f"One service every {FC_SERVICE_INTERVAL_H:,} h"),
    ],
)

activities = [STACK, GRAMC_STACK, BOP, SERVICE, OPERATION]


def inventory() -> Inventory:
    return Inventory(name="PEM fuel cell (Babatunde 2024 stack, Usai 2021 BoP)",
                     database=R.FUEL_CELL_DB, processes=processes, flows=flows,
                     activities=activities)


def describe() -> str:
    return "\n".join([
        "PEM fuel cell operation, per 1 kWh net AC:",
        f"  hydrogen         {FC_H2_PER_KWH:>12.5f} kg    "
        f"(eta {FC_ETA_NET_BOL:.2f} BOL x {FC_DEGRADATION_DERATE:.2f} degradation = {FC_ETA_NET_MEAN:.3f})",
        f"  stack            {FC_STACK_PER_KWH:>12.4e} unit  (1 / {FC_RATED_POWER_KW:g} kW / {FC_STACK_LIFETIME_H:,} h)",
        f"  balance of plant {FC_BOP_PER_KWH:>12.4e} kW    (1 / {FC_RATED_POWER_KW:g} kW / {FC_SYSTEM_LIFETIME_H:,} h)",
        f"  service          {FC_SERVICE_PER_KWH:>12.4e} kW    (one per {FC_SERVICE_INTERVAL_H:,} h)",
        f"  BoP: Usai 2021 loops + {FC_INVERTER_KW:g} kW inverter + one container per "
        f"{FC_KW_PER_CONTAINER:,.0f} kW",
        f"  hydrogen source  {FC_H2_SOURCE[1]!r} in {FC_H2_SOURCE[0]!r}",
        f"  stack scale      {FC_SCALE:.9f} (= {FC_KW_SCALE} kW-scale x {FC_S1_SCALE} Table-S1 correction)",
    ])
