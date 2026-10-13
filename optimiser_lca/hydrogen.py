"""
Hydrogen production — Hermesmann et al., six routes.
=============================================================================

Source and scope
----------------
Inventories recreated from the SimaPro exports of Hermesmann, M. et al.
(SMR.XLSX, smr ccs.XLSX, ccs.XLSX, alkaline electrolyser.XLSX, alkaline
operation.XLSX, uk pem construction.XLSX, ukpemoperation.XLSX,
uksoecconstruction.XLSX, uksoecoperation.XLSX) plus methane pyrolysis MP-E from
the paper's Table 3.

Functional units:

* ``smr``, ``smr_ccs``, ``mp_e`` and the three ``*_op`` activities: **1 kg of
  hydrogen**.
* ``ccs``: treatment of **1 kg of captured CO2** (a foreground waste treatment
  the SMR-CCS route links to, 8.01 kg per kg H2).
* ``ae_unit``, ``pem_unit``, ``soec_unit``: **one electrolyser** — a 1 MW
  capital good, which each operation activity draws on at 1 unit per lifetime
  hydrogen output (3.09, 2.96 and 3.78 million kg respectively: all three
  amortise over 160 GWh of electricity at 1 MW, see ``electrolysers.py``).

Electricity is GB high voltage for the gas routes and GB low voltage for PEM
and SOEC; alkaline electrolysis is as exported, on the DE low-voltage market
(both construction and operation). SMR and SMR-CCS carry a small *avoided*
electricity credit (negative kWh) as the source does.

Biosphere flows: the SMR routes emit fossil CO2 directly (9.0 kg for SMR,
0.99 kg residual for SMR-CCS) and the CCS treatment has a fugitive 1.36e-7 kg.
Three further flows — oxygen, water vapour, cooling water — are carried as the
notebook built them, by the first search hit, and two of those hits are the
wrong compartment (see the ``why`` on each). They carry zero GWP so the
carbon result is unaffected; fix them before using any non-GWP category.

What the optimiser reads: ``electrolysers.py`` strips the capital good back
out of the ``*_op`` activities to get kg CO2e per MW installed;
``h2_prices.py`` scores the four bought colours (grey = SMR, blue = SMR-CCS,
turquoise = MP-E, green = PEM operation) per kg.
"""
from __future__ import annotations

from optimiser_lca import registry as R
from optimiser_lca.common import FG, Activity, Flow, Inventory, Process

# =============================================================================
# Parameters
# =============================================================================
# Capital good per kg H2 = 1 unit / lifetime hydrogen output. Hermesmann's own
# lifetime outputs, transcribed; all three come to 160 GWh at 1 MW.
AE_UNITS_PER_KG_H2   = 3.24e-7     # 1 / 3,085,961 kg
PEM_UNITS_PER_KG_H2  = 3.37e-7     # 1 / 2,964,315 kg
SOEC_UNITS_PER_KG_H2 = 2.645e-7    # 1 / 3,779,894 kg
CO2_CAPTURED_PER_KG_H2 = 8.01      # kg, SMR-CCS -> CCS waste treatment

# =============================================================================
# Processes — exact identities, with the search that found each one
# =============================================================================
processes = {
    # --- utilities shared by the gas routes ---------------------------------
    "electricity_hv_gb": Process(
        query="market for electricity high voltage GB", pick=10,
        identity=("market for electricity, high voltage", "GB", "electricity, high voltage"),
        why="GB HV market; the SMR plant takes grid power at transmission voltage"),
    "gas_hp_gb": Process(
        query="market for natural gas high pressure GB", pick=1,
        identity=("market for natural gas, high pressure", "GB", "natural gas, high pressure")),
    "tap_water": Process(
        query="market for tap water Europe without Switzerland", pick=0,
        identity=("market for tap water", "Europe without Switzerland", "tap water")),
    "wastewater": Process(
        query="market for wastewater average Europe without Switzerland", pick=0,
        identity=("market for wastewater, average", "Europe without Switzerland", "wastewater, average")),
    # --- SMR plant materials -------------------------------------------------
    "concrete_normal": Process(
        query="market for concrete normal RoW", pick=0,
        identity=("concrete, all types to generic market for concrete, normal strength",
                  "RoW", "concrete, normal strength")),
    "steel_unalloyed": Process(
        query="market for steel unalloyed GLO", pick=0,
        identity=("market for steel, unalloyed", "GLO", "steel, unalloyed")),
    "aluminium_cast": Process(
        query="aluminium primary cast alloy slab continuous casting GLO", pick=0,
        identity=("market for aluminium, primary, cast alloy slab from continuous casting",
                  "GLO", "aluminium, primary, cast alloy slab from continuous casting")),
    "cast_iron_glo": Process(
        query="market for cast iron GLO", pick=0,
        identity=("market for cast iron", "GLO", "cast iron")),
    "gas_turbine": Process(
        query="gas turbine 10MW electrical GLO", pick=0,
        identity=("market for gas turbine, 10MW electrical", "GLO", "gas turbine, 10MW electrical")),
    # --- CCS transport and storage -------------------------------------------
    "ccs_pipeline": Process(
        query="pipeline natural gas long distance low capacity onshore GLO", pick=0,
        identity=("market for pipeline, natural gas, long distance, low capacity, onshore",
                  "GLO", "pipeline, natural gas, long distance, low capacity, onshore"),
        why="a gas pipeline standing in for a CO2 pipeline; ecoinvent has no CO2 pipeline"),
    "ccs_well": Process(
        query="onshore well oil gas GLO", pick=1,
        identity=("market for onshore well, oil/gas", "GLO", "onshore well, oil/gas"),
        why="injection well, as the source models it"),
    "ccs_diesel": Process(
        query="market group for diesel RER", pick=0,
        identity=("market group for diesel", "RER", "diesel")),
    # --- methane pyrolysis -----------------------------------------------------
    "steel_chromium_188": Process(
        query="Market for steel, chromium steel 18/8 GLO", pick=1,
        identity=("market for steel, chromium steel 18/8", "GLO", "steel, chromium steel 18/8")),
    "steel_low_alloyed": Process(
        query="Market for steel, low-alloyed GLO", pick=1,
        identity=("market for steel, low-alloyed", "GLO", "steel, low-alloyed")),
    "palladium": Process(
        query="Market for palladium GLO", pick=1,
        identity=("palladium to generic market for metal catalyst for catalytic converter",
                  "GLO", "metal catalyst for catalytic converter"),
        why="as built: the search hit is palladium routed to the catalyst market, "
            "not 'market for palladium' itself; 8.5 mg/kg H2, so immaterial"),
    "copper_cathode": Process(
        query="market for copper cathode GLO", pick=0,
        identity=("market for copper, cathode", "GLO", "copper, cathode")),
    "silica_sand": Process(
        query="Market for silica sand GLO", pick=0,
        identity=("market for silica sand", "GLO", "silica sand")),
    "tin": Process(
        query="Market for tin GLO", pick=0,
        identity=("market for tin", "GLO", "tin")),
    "silicon_carbide": Process(
        query="Market for silicon carbide GLO", pick=0,
        identity=("market for silicon carbide", "GLO", "silicon carbide")),
    # --- electrolyser balance of plant, shared ----------------------------------
    "extrusion_pipes": Process(
        query="extrusion plastic pipes market", pick=0,
        identity=("market for extrusion, plastic pipes", "GLO", "extrusion, plastic pipes")),
    "sheet_rolling_steel": Process(
        query="sheet rolling steel GLO market", pick=0,
        identity=("market for sheet rolling, steel", "GLO", "sheet rolling, steel")),
    "sheet_rolling_aluminium": Process(
        query="sheet rolling aluminium GLO market", pick=0,
        identity=("market for sheet rolling, aluminium", "GLO", "sheet rolling, aluminium")),
    "sheet_rolling_cr_steel": Process(
        query="sheet rolling chromium steel GLO market", pick=0,
        identity=("market for sheet rolling, chromium steel", "GLO", "sheet rolling, chromium steel")),
    "sheet_rolling_copper": Process(
        query="sheet rolling copper GLO market", pick=0,
        identity=("market for sheet rolling, copper", "GLO", "sheet rolling, copper")),
    "wire_drawing_copper": Process(
        query="wire drawing copper GLO market", pick=0,
        identity=("market for wire drawing, copper", "GLO", "wire drawing, copper")),
    "welding_arc_steel": Process(
        query="welding arc steel GLO market", pick=0,
        identity=("market for welding, arc, steel", "GLO", "welding, arc, steel")),
    "injection_moulding": Process(
        query="injection moulding GLO market", pick=0,
        identity=("market for injection moulding", "GLO", "injection moulding")),
    "aluminium_wrought": Process(
        query="aluminium wrought alloy GLO market", pick=1,
        identity=("market for aluminium, wrought alloy", "GLO", "aluminium, wrought alloy")),
    "tube_insulation": Process(
        query="tube insulation elastomere", pick=1,
        identity=("tube insulation production, elastomere", "RoW", "tube insulation, elastomere")),
    "nickel_class1": Process(
        query="nickel class 1 market GLO", pick=0,
        identity=("market for nickel, class 1", "GLO", "nickel, class 1")),
    # --- alkaline electrolyser, RoW datasets as exported ------------------------
    "polyethylene_hd_row": Process(
        query="polyethylene production high density granulate", pick=8,
        identity=("polyethylene production, high density, granulate", "RoW",
                  "polyethylene, high density, granulate")),
    "reinforcing_steel_row": Process(
        query="reinforcing steel production", pick=2,
        identity=("reinforcing steel production", "RoW", "reinforcing steel")),
    "electronics_row": Process(
        query="electronics production control units", pick=1,
        identity=("electronics production, for control units", "RoW", "electronics, for control units")),
    "glass_fibre_row": Process(
        query="glass fibre production", pick=2,
        identity=("glass fibre production", "RoW", "glass fibre")),
    "cr_steel_hot_rolled_row": Process(
        query="steel chromium steel 18/8 hot rolled production", pick=1,
        identity=("steel production, chromium steel 18/8, hot rolled", "RoW",
                  "steel, chromium steel 18/8, hot rolled")),
    "cast_iron_row": Process(
        query="cast iron production", pick=6,
        identity=("cast iron production", "RoW", "cast iron")),
    "ethylene_glycol_row": Process(
        query="ethylene glycol production", pick=0,
        identity=("ethylene glycol production", "RoW", "ethylene glycol")),
    "polypropylene_row": Process(
        query="polypropylene granulate production", pick=1,
        identity=("polypropylene production, granulate", "RoW", "polypropylene, granulate")),
    "low_alloyed_steel_hr_row": Process(
        query="steel low-alloyed hot rolled production", pick=1,
        identity=("steel production, low-alloyed, hot rolled", "RoW", "steel, low-alloyed, hot rolled")),
    "concrete_35mpa_cem3": Process(
        query="concrete production 35MPa", pick=0,
        identity=("concrete production, 35MPa, for building construction, with cement, CEM III/A",
                  "GLO", "concrete, 35MPa"),
        why="as built: AE's 'concrete production 35MPa' search landed on CEM III/A (hit 0); "
            "PEM and SOEC on CEM II/B (hit 2). Same strength class, different cement"),
    "tetrafluoroethylene_row": Process(
        query="tetrafluoroethylene production", pick=2,
        identity=("tetrafluoroethylene production", "RoW", "tetrafluoroethylene")),
    "polysulfone": Process(
        query="polysulfone production membrane filtration", pick=0,
        identity=("polysulfone production, for membrane filtration production", "GLO", "polysulfone")),
    "zirconium_oxide_row": Process(
        query="zirconium oxide production", pick=1,
        identity=("zirconium oxide production", "RoW", "zirconium oxide")),
    "electricity_lv_de": Process(
        query="market for electricity low voltage DE", pick=0,
        identity=("market for electricity, low voltage", "DE", "electricity, low voltage"),
        why="alkaline is as exported by Hermesmann, on the German LV market; "
            "PEM and SOEC were re-based to GB"),
    "water_deionised": Process(
        query="market for water deionised Europe without Switzerland", pick=0,
        identity=("market for water, deionised", "Europe without Switzerland", "water, deionised")),
    "water_softened": Process(
        query="market for water completely softened RER", pick=0,
        identity=("market for water, completely softened", "RER", "water, completely softened")),
    "electrolyte_koh": Process(
        query="market for electrolyte KOH LiOH additive", pick=0,
        identity=("market for electrolyte, KOH, LiOH additive", "GLO", "electrolyte, KOH, LiOH additive")),
    # --- PEM and SOEC, RER datasets as exported -----------------------------------
    "carbon_black": Process(
        query="carbon black production GLO", pick=0,
        identity=("carbon black production", "GLO", "carbon black")),
    "cast_iron_rer": Process(
        query="cast iron production RER", pick=0,
        identity=("cast iron production", "RER", "cast iron")),
    "concrete_35mpa_cem2": Process(
        query="concrete production 35MPa", pick=2,
        identity=("concrete production, 35MPa, with cement, CEM II/B", "GLO", "concrete, 35MPa")),
    "electronics_rer": Process(
        query="electronics production control units RER", pick=0,
        identity=("electronics production, for control units", "RER", "electronics, for control units")),
    "ethylene_glycol_rer": Process(
        query="ethylene glycol production RER", pick=4,
        identity=("ethylene glycol production", "RER", "ethylene glycol")),
    "lubricating_oil": Process(
        query="market for lubricating oil", pick=1,
        identity=("market for lubricating oil", "RER", "lubricating oil")),
    "polyethylene_ld_rer": Process(
        query="polyethylene production low density granulate RER", pick=0,
        identity=("polyethylene production, low density, granulate", "RER",
                  "polyethylene, low density, granulate")),
    "polypropylene_rer": Process(
        query="polypropylene granulate production RER", pick=0,
        identity=("polypropylene production, granulate", "RER", "polypropylene, granulate")),
    "reinforcing_steel_eur": Process(
        query="reinforcing steel production Europe without Austria", pick=0,
        identity=("reinforcing steel production", "Europe without Austria", "reinforcing steel")),
    "cr_steel_hr_rer": Process(
        query="steel chromium steel 18/8 hot rolled production RER", pick=0,
        identity=("steel production, chromium steel 18/8, hot rolled", "RER",
                  "steel, chromium steel 18/8, hot rolled")),
    "low_alloyed_steel_hr_rer": Process(
        query="steel low-alloyed hot rolled production RER", pick=0,
        identity=("steel production, low-alloyed, hot rolled", "RER", "steel, low-alloyed, hot rolled")),
    "synthetic_rubber": Process(
        query="synthetic rubber production RER", pick=0,
        identity=("synthetic rubber production", "RER", "synthetic rubber")),
    "tetrafluoroethylene_rer": Process(
        query="tetrafluoroethylene production", pick=3,
        identity=("tetrafluoroethylene production", "RER", "tetrafluoroethylene")),
    "titanium": Process(
        query="titanium production GLO", pick=2,
        identity=("titanium production", "GLO", "titanium")),
    "zeolite": Process(
        query="zeolite powder production RER", pick=0,
        identity=("zeolite production, powder", "RER", "zeolite, powder")),
    "platinum": Process(
        query="market for platinum GLO", pick=0,
        identity=("market for platinum", "GLO", "platinum")),
    "electricity_lv_gb": Process(
        query="market for electricity low voltage GB", pick=0,
        identity=("market for electricity, low voltage", "GB", "electricity, low voltage")),
    "heat_rer": Process(
        query="market group for heat district or industrial other than natural gas RER", pick=0,
        identity=("market group for heat, district or industrial, other than natural gas", "RER",
                  "heat, district or industrial, other than natural gas")),
    # --- SOEC ceramics ---------------------------------------------------------------
    "abs_row": Process(
        query="acrylonitrile-butadiene-styrene copolymer production RoW", pick=0,
        identity=("acrylonitrile-butadiene-styrene copolymer production", "RoW",
                  "acrylonitrile-butadiene-styrene copolymer")),
    "aluminium_oxide": Process(
        query="aluminium oxide metallurgical IAI market", pick=0,
        identity=("aluminium oxide, non-metallurgical to generic market for refractory material, acid",
                  "IAI Area, EU27 & EFTA", "refractory material, acid"),
        why="as built: the search landed on alumina routed to the refractory market; "
            "6.4 kg per unit, immaterial. 'market for aluminium oxide, non-metallurgical' "
            "would be the cleaner pick"),
    "barium_oxide": Process(
        query="barium oxide production GLO", pick=0,
        identity=("barium oxide production", "GLO", "barium oxide")),
    "boric_oxide": Process(
        query="boric oxide production GLO", pick=0,
        identity=("boric oxide production", "GLO", "boric oxide")),
    "cerium_oxide": Process(
        query="cerium oxide market GLO", pick=0,
        identity=("cerium oxide to generic market for mischmetal", "GLO", "mischmetal"),
        why="as built: cerium oxide routed to the mischmetal market, not 'market for "
            "cerium oxide'; revisit if the SOEC stack is ever scored on resource categories"),
    "praseodymium_oxide": Process(
        query="praseodymium oxide market GLO", pick=0,
        identity=("market for praseodymium-neodymium oxide", "GLO", "praseodymium-neodymium oxide"),
        why="ecoinvent has no praseodymium oxide alone; the mixed Pr-Nd oxide market stands in"),
    "samarium_seg_oxide": Process(
        query="samarium europium gadolinium oxide market GLO", pick=0,
        identity=("market for samarium-europium-gadolinium oxide", "GLO",
                  "samarium-europium-gadolinium oxide")),
    "silicone_product": Process(
        query="silicone product production RER", pick=0,
        identity=("silicone product production", "RER", "silicone product")),
    "zirconium_oxide_row_soec": Process(
        query="zirconium oxide production RoW", pick=0,
        identity=("zirconium oxide production", "RoW", "zirconium oxide")),
}

flows = {
    "co2": Flow(query="Carbon dioxide fossil", pick=0,
                identity=("Carbon dioxide, fossil", ("air",))),
    "oxygen_air": Flow(query="Oxygen", pick=0,
                       identity=("Oxygen", ("water",)),
                       why="as built, by first search hit: this is oxygen to WATER, not to air. "
                           "Zero GWP, so harmless for carbon; wrong for anything else"),
    "water_air": Flow(query="Water air", pick=0,
                      identity=("Water, in air", ("natural resource", "in air")),
                      why="as built, by first search hit: a natural-resource flow, not an "
                          "emission to air. Zero GWP; fix before any water-use category"),
    "water_resource": Flow(query="Water cooling unspecified natural origin", pick=0,
                           identity=("Water, cooling, unspecified natural origin",
                                     ("natural resource", "in water"))),
}

# =============================================================================
# Activities
# =============================================================================
_kg, _m3, _kwh, _MJ, _unit, _m = ("kilogram", "cubic meter", "kilowatt hour",
                                  "megajoule", "unit", "meter")

activities = [
    Activity(
        code=R.SMR, name="Hydrogen production, SMR Hermesmann",
        reference_product="hydrogen", unit=_kg, location="GB",
        comment="Recreated from SimaPro export SMR.XLSX.",
        technosphere=[
            ("electricity_hv_gb", -1.1,    _kwh,  "Avoided product: Electricity, high voltage GB"),
            ("gas_hp_gb",         4.85,    _m3,   "Natural gas, high pressure GB"),
            ("tap_water",         6.64,    _kg,   "Tap water"),
            ("concrete_normal",   6.60e-6, _m3,   "Concrete, normal RoW"),
            ("steel_unalloyed",   5.06e-3, _kg,   "Steel, unalloyed GLO"),
            ("aluminium_cast",    4.17e-5, _kg,   "Aluminium, primary, cast alloy slab"),
            ("cast_iron_glo",     6.18e-5, _kg,   "Cast iron GLO"),
            ("gas_turbine",       7.90e-10, _unit, "Gas turbine, 10MW electrical GLO"),
            ("wastewater",        0.00172, _m3,   "Wastewater, average"),
        ],
        biosphere=[
            ("co2",            9.0,  _kg, "Carbon dioxide; modelled as fossil CO2"),
            ("oxygen_air",     0.31, _kg, "Oxygen to air"),
            ("water_air",      2.93, _kg, "Water to air"),
            ("water_resource", 0.38, _m3, "Water, cooling, GB"),
        ],
    ),
    Activity(
        code=R.SMR_CCS, name="Hydrogen production, SMR-CCS Hermesmann",
        reference_product="hydrogen", unit=_kg, location="GB",
        comment="Recreated from SimaPro export smr ccs.XLSX. CCS WT linked as foreground.",
        technosphere=[
            (FG(R.CCS),           CO2_CAPTURED_PER_KG_H2, _kg,
             "8.01 kg CO2 per kg H2 to foreground CCS waste-treatment"),
            ("electricity_hv_gb", -0.05,   _kwh,  "Avoided electricity"),
            ("gas_hp_gb",         5.33,    _m3,   "Natural gas, high pressure GB"),
            ("tap_water",         4.68,    _kg,   "Tap water"),
            ("concrete_normal",   6.60e-6, _m3,   "Concrete RoW"),
            ("steel_unalloyed",   5.06e-3, _kg,   "Steel unalloyed GLO"),
            ("aluminium_cast",    4.17e-5, _kg,   "Aluminium, primary"),
            ("cast_iron_glo",     6.18e-5, _kg,   "Cast iron GLO"),
            ("gas_turbine",       7.90e-10, _unit, "Gas turbine 10MW"),
            ("wastewater",        0.00183, _m3,   "Wastewater, average"),
        ],
        biosphere=[
            ("co2",            0.99, _kg, "CO2 residual, not captured"),
            ("oxygen_air",     0.41, _kg, "Oxygen to air"),
            ("water_air",      1.33, _kg, "Water to air"),
            ("water_resource", 1.18, _m3, "Water, cooling, GB"),
        ],
    ),
    Activity(
        code=R.CCS, name="Carbon capture and storage, Hermesmann",
        reference_product="carbon dioxide, captured", unit=_kg, location="GB",
        comment="Foreground CCS waste treatment from ccs.XLSX. Treats 1 kg captured CO2.",
        technosphere=[
            ("ccs_pipeline",      2.34666e-9, "kilometer", "Pipeline, natural gas, long distance"),
            ("ccs_well",          9.863e-8,   _m,          "Onshore well, oil/gas"),
            ("ccs_diesel",        0.0154,     _kg,         "Diesel"),
            ("electricity_hv_gb", 0.0171,     _kwh,        "Electricity HV GB — pipeline pumping"),
            ("electricity_hv_gb", 0.0070,     _kwh,        "Electricity HV GB — compressor"),
        ],
        biosphere=[
            ("co2", 1.36106e-7, _kg, "CO2 fugitive emissions from CCS pipeline/well"),
        ],
    ),
    Activity(
        code=R.MP_E, name="Hydrogen production, methane pyrolysis MP-E",
        reference_product="hydrogen", unit=_kg, location="DE",
        comment="Methane pyrolysis MP-E from Table 3. Electric heating; no direct CO2.",
        technosphere=[
            ("gas_hp_gb",          5.72,    _m3,  "Natural gas, high pressure GB"),
            ("electricity_hv_gb",  10.29,   _kwh, "Electricity HV GB"),
            ("palladium",          8.45e-6, _kg,  "Palladium GLO"),
            ("copper_cathode",     5.63e-6, _kg,  "Copper GLO"),
            ("steel_low_alloyed",  1.99e-3, _kg,  "Steel low-alloyed"),
            ("steel_chromium_188", 3.89e-4, _kg,  "Steel chromium 18/8"),
            ("silica_sand",        6.18e-5, _kg,  "Silica sand"),
            ("tin",                2.58e-2, _kg,  "Tin"),
            ("silicon_carbide",    3.23e-6, _kg,  "Silicon carbide"),
        ],
    ),
    Activity(
        code=R.AE_UNIT, name="Alkaline electrolyser, Hermesmann",
        reference_product="alkaline electrolyser", unit=_unit, location="GLO",
        comment="AE manufacturing from alkaline electrolyser.XLSX. Capital good: 1 unit.",
        technosphere=[
            ("polyethylene_hd_row",       464.6,    _kg,  "Water purifier / feed tank"),
            ("extrusion_pipes",           464.6,    _kg,  "Water purifier / feed tank"),
            ("reinforcing_steel_row",    5214.4,    _kg,  "Reinforcing steel, aggregated BoP"),
            ("sheet_rolling_steel",     10215.0,    _kg,  "Sheet rolling steel, aggregated BoP"),
            ("electronics_row",           100.0,    _kg,  "Control panel / electronics"),
            ("aluminium_wrought",         160.0,    _kg,  "Transformer + frequency converter"),
            ("copper_cathode",            616.7,    _kg,  "Transformer + compressor + tubing/cables"),
            ("sheet_rolling_aluminium",   100.0,    _kg,  "Transformer and rectifier"),
            ("tube_insulation",           207.9,    _kg,  "Transformer + compressor + tubing"),
            ("wire_drawing_copper",       616.7,    _kg,  "Transformer + compressor + tubing"),
            ("glass_fibre_row",           464.6,    _kg,  "H2 drier and deoxidiser"),
            ("sheet_rolling_cr_steel",  26892.2,    _kg,  "Sheet rolling Cr steel, aggregated"),
            ("cr_steel_hot_rolled_row", 26892.2,    _kg,  "Cr steel 18/8 hot rolled, aggregated"),
            ("cast_iron_row",             716.1,    _kg,  "Compressor + pumps and coolers"),
            ("ethylene_glycol_row",         7.0,    _kg,  "Diaphragm for compressor"),
            ("welding_arc_steel",          29.0,    _m,   "Buffertank"),
            ("polypropylene_row",           3.0,    _kg,  "Alkali-resistant rotary pump"),
            ("injection_moulding",          3.0,    _kg,  "Alkali-resistant rotary pump"),
            ("low_alloyed_steel_hr_row", 6075.6,    _kg,  "Container"),
            ("concrete_35mpa_cem3",         7.7,    _m3,  "Fundament"),
            ("nickel_class1",            2884.9,    _kg,  "Anode + cathode with frame"),
            ("tetrafluoroethylene_row",   144.2,    _kg,  "Gasket"),
            ("polysulfone",                48.8,    _kg,  "Diaphragm zirfon"),
            ("zirconium_oxide_row",        73.0,    _kg,  "Diaphragm zirfon"),
            ("electricity_lv_de",      323773.4,    _kwh, "BoP + Stack manufacturing electricity"),
        ],
    ),
    Activity(
        code=R.AE_OP, name="Hydrogen production, alkaline electrolysis Hermesmann",
        reference_product="hydrogen", unit=_kg, location="DE",
        comment="AE operation from alkaline operation.XLSX. AE capital good linked.",
        technosphere=[
            (FG(R.AE_UNIT),     AE_UNITS_PER_KG_H2, _unit,
             "Capital good: 1 unit / 3,085,961 kg H2 lifetime = 3.24e-7 unit/kg H2"),
            ("water_deionised",  8.99,   _kg,  "Water, deionised"),
            ("water_softened",  88.1,    _kg,  "Water, completely softened"),
            ("electrolyte_koh",  0.0037, _kg,  "Electrolyte KOH/LiOH"),
            ("electricity_lv_de", 51.8,  _kwh, "Electricity LV GB — electrolysis"),
        ],
    ),
    Activity(
        code=R.PEM_UNIT, name="PEM electrolyser, Hermesmann",
        reference_product="PEM electrolyser", unit=_unit, location="GB",
        comment="PEM manufacturing from uk pem construction.XLSX. 1 unit (1 MW).",
        technosphere=[
            ("extrusion_pipes",           464.6,    _kg,  "Water purifier / feed tank"),
            ("polyethylene_ld_rer",       464.6,    _kg,  "Water purifier / feed tank"),
            ("aluminium_wrought",         287.0,    _kg,  "Power electronics + purification + end plate"),
            ("sheet_rolling_aluminium",   227.0,    _kg,  "Power electronics + purification + end plate"),
            ("electronics_rer",           100.0,    _kg,  "Control panel/electronics"),
            ("cast_iron_rer",             600.0,    _kg,  "Diaphragm compressor"),
            ("ethylene_glycol_rer",         7.0,    _kg,  "Diaphragm compressor"),
            ("copper_cathode",            349.5,    _kg,  "Power elec + water gas sep + compressor + current collector"),
            ("sheet_rolling_copper",      104.5,    _kg,  "Water gas separator + current collector"),
            ("wire_drawing_copper",       245.0,    _kg,  "Power electronics + compressor"),
            ("injection_moulding",        300.0,    _kg,  "Valve"),
            ("polypropylene_rer",         300.0,    _kg,  "Valve"),
            ("lubricating_oil",           100.0,    _kg,  "Back pressure regulator"),
            ("reinforcing_steel_eur",    3312.3,    _kg,  "Power elec + water purifier + compressor + container"),
            ("sheet_rolling_cr_steel",   4427.0,    _kg,  "Steel + heat ex + compressor + buffer + bolts"),
            ("sheet_rolling_steel",      5382.3,    _kg,  "Power elec + tubing + water purifier + compressor"),
            ("cr_steel_hr_rer",          4427.0,    _kg,  "Steel + heat ex + compressor + buffer + bolts (RER)"),
            ("low_alloyed_steel_hr_rer", 3150.0,    _kg,  "Tubing/pump + container"),
            ("welding_arc_steel",          29.0,    _m,   "Buffer tank"),
            ("tube_insulation",           115.0,    _kg,  "Power electronics + compressor"),
            ("zeolite",                   100.0,    _kg,  "Ion exchanger"),
            ("concrete_35mpa_cem2",         2.3,    _m3,  "Foundation"),
            ("carbon_black",                9.0,    _kg,  "Electrocatalyst anode + cathode"),
            ("platinum",                    0.875,  _kg,  "Electrocatalyst anode + cathode"),
            ("tetrafluoroethylene_rer",    16.0,    _kg,  "Membrane polymer"),
            ("synthetic_rubber",            4.8,    _kg,  "Gasket"),
            ("titanium",                  528.0,    _kg,  "Bipolar plate"),
            ("electricity_lv_gb",      361672.3,    _kwh, "PEM stack + BoP manufacturing"),
        ],
    ),
    Activity(
        code=R.PEM_OP, name="Hydrogen production, PEM electrolysis Hermesmann",
        reference_product="hydrogen", unit=_kg, location="GB",
        comment="PEM operation from ukpemoperation.XLSX. PEM capital good linked.",
        technosphere=[
            (FG(R.PEM_UNIT),    PEM_UNITS_PER_KG_H2, _unit,
             "Capital good: 1 unit / 2,964,315 kg H2 lifetime = 3.37e-7 unit/kg H2"),
            ("water_deionised",    8.99,  _kg,  "Water, deionised"),
            ("water_softened",    88.1,   _kg,  "Water, completely softened"),
            ("electricity_lv_gb", 54.0,   _kwh, "Electricity LV GB"),
            ("heat_rer",           1.008, _MJ,  "Heat district/industrial RER (0.28 kWh × 3.6)"),
        ],
    ),
    Activity(
        code=R.SOEC_UNIT, name="SOEC electrolyser, Hermesmann",
        reference_product="SOEC electrolyser", unit=_unit, location="GB",
        comment="SOEC manufacturing from uksoecconstruction.XLSX.",
        technosphere=[
            ("extrusion_pipes",           534.0,    _kg,  "Water purifier / pre-heating"),
            ("polyethylene_ld_rer",       534.0,    _kg,  "Water purifier / pre-heating"),
            ("aluminium_wrought",         401.0,    _kg,  "Freq converters + power electronics + water pump"),
            ("sheet_rolling_aluminium",   100.0,    _kg,  "Power electronics"),
            ("electronics_rer",           100.0,    _kg,  "Control electronics"),
            ("abs_row",                     1.4,    _kg,  "Control panel / heater"),
            ("injection_moulding",          1.4,    _kg,  "Control panel / heater"),
            ("cast_iron_rer",            3000.0,    _kg,  "Diaphragm compressors 1-5"),
            ("ethylene_glycol_rer",        35.0,    _kg,  "Diaphragm compressors 1-5"),
            ("copper_cathode",            428.5,    _kg,  "Control + freq conv + power electronics + freq conv water pump"),
            ("wire_drawing_copper",       428.5,    _kg,  "Control + freq conv + power electronics + freq conv water pump"),
            ("tube_insulation",           176.6,    _kg,  "Freq conv + power electronics + control + freq conv water pump"),
            ("reinforcing_steel_eur",   13730.6,    _kg,  "BoP steel components"),
            ("sheet_rolling_cr_steel",  25597.5,    _kg,  "BoP Cr steel components + air electrode"),
            ("sheet_rolling_steel",     12081.2,    _kg,  "BoP steel components"),
            ("cr_steel_hr_rer",         25597.5,    _kg,  "BoP Cr steel components + air electrode"),
            ("low_alloyed_steel_hr_rer", 3753.6,    _kg,  "Tubing + container — pre-heating"),
            ("welding_arc_steel",          33.3,    _m,   "Buffer tank (pre-heating)"),
            ("concrete_35mpa_cem2",         2.3,    _m3,  "Foundation"),
            ("aluminium_oxide",             6.4,    _kg,  "Electrolyte + H2 electrode"),
            ("barium_oxide",                6.4,    _kg,  "Electrolyte + H2 electrode"),
            ("boric_oxide",                 6.4,    _kg,  "Electrolyte + H2 electrode"),
            ("silicone_product",            6.4,    _kg,  "Electrolyte sealant"),
            ("nickel_class1",             144.1,    _kg,  "Air electrode + firing"),
            ("praseodymium_oxide",          9.0,    _kg,  "Air electrode screen printing"),
            ("samarium_seg_oxide",         37.7,    _kg,  "Blocking layer + screen printing"),
            ("cerium_oxide",               91.5,    _kg,  "Blocking layer screen printing"),
            ("zirconium_oxide_row_soec",  170.7,    _kg,  "Blocking layer"),
            ("electricity_lv_gb",      443093.5,    _kwh, "SOEC BoP + Stack manufacturing"),
        ],
    ),
    Activity(
        code=R.SOEC_OP, name="Hydrogen production, SOEC electrolysis Hermesmann",
        reference_product="hydrogen", unit=_kg, location="GB",
        comment="SOEC operation from uksoecoperation.XLSX. SOEC capital good linked.",
        technosphere=[
            (FG(R.SOEC_UNIT),   SOEC_UNITS_PER_KG_H2, _unit,
             "Capital good: 1 unit / 3,779,894 kg H2 lifetime = 2.645e-7 unit/kg H2"),
            ("water_deionised",    8.99,  _kg,  "Water, deionised"),
            ("water_softened",   644.7,   _kg,  "Water, completely softened"),
            ("electricity_lv_gb", 42.3,   _kwh, "Electricity LV GB"),
            ("heat_rer",          18.864, _MJ,  "Heat district/industrial RER (5.24 kWh × 3.6)"),
        ],
    ),
]


def inventory() -> Inventory:
    return Inventory(name="hydrogen (Hermesmann)", database=R.HYDROGEN_DB,
                     processes=processes, flows=flows, activities=activities)
