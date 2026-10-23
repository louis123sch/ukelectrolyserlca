"""
Hydrogen production — Hermesmann & Müller 2022 (fossil routes), Gerloff 2021
(electrolysers), six routes.
=============================================================================

Source and scope
----------------
* SMR, SMR-CCS, CCS and MP-E: Hermesmann, M. & Müller, T.E. (2022), "Green,
  Turquoise, Blue, or Grey? Environmentally friendly Hydrogen Production in
  Transforming Energy Systems", Prog. Energy Combust. Sci. 90, 100996 —
  Tables 2–3 (inventories per kg H2) and §3.2.3 (CCS). Transcribed through the
  study's own SimaPro project (SMR.XLSX, smr ccs.XLSX, ccs.XLSX); checked row
  by row against the paper on 21–22 Oct 2026.
* AE, PEM and SOEC units and operation: Gerloff, N. (2021), J. Energy Storage
  43, 102759 — SI Figures 1–5 (the 1 MW bills, every row labelled BoP or
  Stack) and Tables 3–6 (manufacturing energy, lifetime hydrogen, operating
  data). Transcribed through the same SimaPro project; checked row by row
  against the SI on 22 Oct 2026.

**Functional units.** ``smr``, ``smr_ccs``, ``mp_e`` and the three ``*_op``
activities: **1 kg of hydrogen** at the production site (Hermesmann's FU is at
30 bar). ``ccs``: treatment of **1 kg of captured CO2**. ``ae_unit``,
``pem_unit``, ``soec_unit``: **one 1 MW electrolyser over Gerloff's 20-year
life**, which each operation activity draws on at 1 unit per lifetime hydrogen
output (3.09, 2.96 and 3.78 million kg; all three are 160 GWh of electricity
at 1 MW — ``electrolysers.py`` re-amortises per MW installed).

**Boundary.** Cradle to gate at the production site. Out: end-of-life
(Gerloff Table 4's disposal processes), delivery to site (Gerloff's second
250 km lorry leg), and every by-product credit — Hermesmann's excess
electricity (SMR 1.10 kWh, SMR-CCS 0.05 kWh per kg) and MP-E's 3.00 kg of solid
carbon are not credited; the whole burden sits on the hydrogen (attributional,
no system expansion, ASSUMPTIONS.md §5; user decision 21 Oct 2026). In: the
first 250 km leg (materials to assembly), three stacks per unit life (Gerloff
§2.1.2–2.1.3: the stack is "replaced 3 times", and SI Table 3's stack energy is
already ×3), manufacturing energy, foundations.

**Substitutions, each stated once where it applies.** Electricity: every kWh
except AE's is the study's own GB grid (``gb_grid.py``, GRID_DB), not
ecoinvent's 2018 GB market, so every grid kWh in the study is on one basis; AE
is as Gerloff export it, on the German LV market. Iridium: Gerloff's 0.8 kg of
anode iridium has no 3.9.1 dataset; platinum stands in for it (SOURCE_DIFF S3).
SOEC heat: on Mehmeti et al. 2018's natural-gas boiler, the source of the
5.24 kWh, rather than Gerloff's coal-heavy "other than natural gas" heat (see
``heat_ng_boiler``). CCS well drilling: Hermesmann's "15.4 kg diesel per kg
CO2" read as per tonne and burned (SOURCE_DIFF S4). LSM layer: Gerloff name
La2O3 and SrCO3 with no amount (#11); ASSUMED amounts from the layer's
geometry stand in until the sheet is held.

**Carbon balance (DERIVED, this module's addition).** Every carbon atom in the
gas an SMR plant takes leaves as CO2. ecoinvent's GB high-pressure gas carries
0.7410 kg fossil C per kg at 0.7350 kg/m3, i.e. 1.9956 kg CO2 per m3; the
paper's IEAGHG-based figures (9.00 kg on 4.85 m3) imply a leaner gas. The gap
is charged as CO2: all of it to air for SMR (0.679 kg); for SMR-CCS, which is
post-combustion flue-gas capture at 90 % (Hermesmann §4.1.1, Fig. 9), 90 % of
the gap to the capture train and 10 % to air. The paper's own SMR-CCS numbers
close on that reading: 9.00 × 5.33/4.85 = 9.89 kg, 0.99 emitted (printed),
8.90 captured. The export's 8.01 kg captured (= 9.00 − 0.99) was a slip and was
replaced on 22 Oct 2026.
"""
from __future__ import annotations

from optimiser_lca import registry as R
from optimiser_lca.common import FG, Activity, Flow, Inventory, Process

# =============================================================================
# Parameters
# =============================================================================
# --- Gerloff: capital good per kg H2 = 1 unit / lifetime hydrogen output ------
# TRANSCRIBED from the SimaPro exports, which round SI Table 4's outputs
# (3,085,961 / 2,964,315 / 3,779,894 kg): kept as exported, since the built
# databases and every cached coefficient carry these literals.
AE_UNITS_PER_KG_H2   = 3.24e-7      # TRANSCRIBED - as exported (1 / 3,085,961 kg)
PEM_UNITS_PER_KG_H2  = 3.37e-7      # TRANSCRIBED - as exported (1 / 2,964,315 kg)
SOEC_UNITS_PER_KG_H2 = 2.645e-7     # TRANSCRIBED - as exported (1 / 3,779,894 kg)
STACKS_PER_UNIT_LIFE = 3            # TRANSCRIBED - Gerloff §2.1.2-2.1.3, SI p.1: the stack is replaced 3 times
GERLOFF_LORRY_KM     = 250.0        # TRANSCRIBED - Gerloff §2.1: one leg to assembly (in), one to site (out)
# Operating data, Gerloff SI Table 6 (= paper Table 3). TRANSCRIBED.
AE_KWH_PER_KG, PEM_KWH_PER_KG, SOEC_KWH_PER_KG = 51.8, 54.0, 42.3
WATER_DEIONISED_KG_PER_KG = 8.9     # TRANSCRIBED - SI Table 6 "8.9 l"; the exports carried 8.99
SOEC_HEAT_KWH_PER_KG = 5.24         # TRANSCRIBED - Mehmeti et al. 2018 Table 1, copied by Gerloff Table 3
PEM_HEAT_KWH_PER_KG  = 0.28         # TRANSCRIBED - Gerloff Table 6

# --- Gerloff: the stack's rows, per stack (SI Figs 1, 2 and 5) ------------------
# TRANSCRIBED, kg. Multiplied by STACKS_PER_UNIT_LIFE in the unit activities.
AE_STACK_KG   = {"cr_steel": 20_194.4, "nickel": 2_884.9, "tfe": 144.2, "polysulfone": 48.8, "zro2": 73.0}
PEM_STACK_KG  = {"end_plate_al": 27.0, "titanium": 528.0, "tfe": 16.0, "carbon_black": 9.0,
                 "platinum_for_pt_and_ir": 0.875, "copper": 4.5, "bolts_cr_steel": 100.0, "rubber": 4.8}
SOEC_STACK_KG = {                                       # TRANSCRIBED, kg per stack
    "cr_steel": 8_976.1, "pr_oxide": 9.0, "nickel": 144.1, "zro2": 170.7, "seg_oxide": 37.7,
    "ce_oxide": 91.5, "al2o3": 6.4, "b2o3": 6.4, "bao": 6.4, "silicone": 6.4}
# Materials per unit on one stack, excluding the foundation (DERIVED: the sum of
# the SI's material rows, docs/source_ledgers/gerloff_2021.md), for the lorry leg.
AE_MATERIALS_KG_ONE_STACK, PEM_MATERIALS_KG_ONE_STACK, SOEC_MATERIALS_KG_ONE_STACK = 43_993.0, 13_871.0, 48_237.0


def _unit_tkm(one_stack_kg: float, stack_kg: dict) -> float:
    """t·km of the 250 km assembly leg on a unit's whole material mass, three stacks."""
    return (one_stack_kg + (STACKS_PER_UNIT_LIFE - 1) * sum(stack_kg.values())) * GERLOFF_LORRY_KM / 1000.0


# --- SOEC LSM layer: La2O3 and SrCO3, amounts not held (SOURCE_DIFF #11) ----------
# ASSUMED from the layer's geometry: a 1 MW stack at ~1 W/cm2 is ~100 m2 of cell;
# a 30 um LSM layer at 6.5 g/cm3 is ~19.5 kg per stack, La0.8Sr0.2MnO3 splitting
# by stoichiometry 0.563 La2O3 / 0.128 SrCO3 / 0.375 MnO2 per kg. Manganese is
# not carried (no row in Gerloff either). Register: optimiser_lca/exclusions.py.
SOEC_LSM_KG_PER_STACK   = 19.5                      # ASSUMED, see above
SOEC_LA2O3_KG_PER_STACK = 0.563 * SOEC_LSM_KG_PER_STACK
SOEC_SRCO3_KG_PER_STACK = 0.128 * SOEC_LSM_KG_PER_STACK

# --- Hermesmann: the gas routes, per kg H2 ------------------------------------------
CO2_CAPTURED_PER_KG_H2 = 8.90       # TRANSCRIBED - 90 % of 9.00 x 5.33/4.85 = 9.89 kg (Table 2 prints 0.99 emitted)
SMR_CCS_CAPTURE_RATE   = 0.90       # TRANSCRIBED - post-combustion MEA, Hermesmann §4.1.1 / Fig. 9
SMR_GAS_M3, SMR_CO2_EMITTED = 4.85, 9.0               # TRANSCRIBED - Table 2
SMR_CCS_GAS_M3, SMR_CCS_CO2_EMITTED = 5.33, 0.99      # TRANSCRIBED - Table 2
# ecoinvent 3.9.1 'market for natural gas, high pressure' GB product properties
# (Bussa et al. 2021 composition, Meili et al. 2022 density). TRANSCRIBED.
GAS_KG_PER_M3 = 0.7350015434999999
GAS_FOSSIL_C_PER_KG = 0.7410015561000001
CO2_PER_KG_C = 44.0095 / 12.011     # molar-mass constant
GAS_CO2_KG_PER_M3 = GAS_KG_PER_M3 * GAS_FOSSIL_C_PER_KG * CO2_PER_KG_C
# DERIVED closures, see the docstring.
SMR_CO2_CLOSURE = SMR_GAS_M3 * GAS_CO2_KG_PER_M3 - SMR_CO2_EMITTED
SMR_CCS_CO2_GAP = SMR_CCS_GAS_M3 * GAS_CO2_KG_PER_M3 - SMR_CCS_CO2_EMITTED - CO2_CAPTURED_PER_KG_H2
SMR_CCS_CLOSURE_EMITTED  = (1.0 - SMR_CCS_CAPTURE_RATE) * SMR_CCS_CO2_GAP
SMR_CCS_CLOSURE_CAPTURED = SMR_CCS_CAPTURE_RATE * SMR_CCS_CO2_GAP
# CCS well drilling: Hermesmann §3.2.3 give Verma's "15.4 kg diesel / kg CO2";
# read as per tonne (per kg is 137 kg of diesel per kg H2, impossible against
# the paper's own blue total of 3.97) and burned, not linked as a product.
CCS_DIESEL_KG_PER_KG_CO2 = 0.0154   # TRANSCRIBED (÷1000, stated), SOURCE_DIFF S4
DIESEL_MJ_PER_KG = 42.8             # conversion, lower heating value

H2_SCOPE = {
    "electricity": "SUBSTITUTED - every kWh of the GB routes is the study's own grid kWh (gb_grid.py, "
                   "GRID_DB), not ecoinvent's 2018 GB market; AE is as exported, on the German LV market.",
    "credits": "No by-product credit is taken (ASSUMPTIONS §5): Hermesmann's excess electricity (SMR 1.10, "
               "SMR-CCS 0.05 kWh per kg) and MP-E's 3.00 kg of carbon stay uncredited. The dropped rows are "
               "at the foot of each activity with their amounts.",
    "stacks": "INCLUDED - three stacks' materials per unit life (Gerloff §2.1.3), matching the x3 already in "
              "SI Table 3's stack manufacturing energy; one stack's materials were carried until 22 Oct 2026.",
    "transport": "INCLUDED - Gerloff's 250 km lorry leg from the material suppliers to assembly, on the unit's "
                 "whole mass. EXCLUDED - the second 250 km leg to the plant site (delivery to site).",
    "iridium": "SUBSTITUTED - 0.8 kg of iridium (PEM anode) as platinum; no iridium dataset in 3.9.1.",
    "lsm": "ASSUMED - La2O3 and SrCO3 amounts for the SOEC's LSM layer, which Gerloff name without a figure.",
    "haulage": "EXCLUDED - road haulage of bought hydrogen from the seller to the site: delivery to site "
               "(h2_prices.py charges the trailer compression; the journey depends on where the seller is).",
    "end_of_life": "EXCLUDED, as everywhere else in this study (Gerloff Table 4's disposal processes).",
}


def check() -> str:
    """The three capital bases are one 160 GWh basis; the gas routes' carbon closes; stack masses tie."""
    problems = []
    for name, units, kwh in (("AE", AE_UNITS_PER_KG_H2, AE_KWH_PER_KG), ("PEM", PEM_UNITS_PER_KG_H2, PEM_KWH_PER_KG),
                             ("SOEC", SOEC_UNITS_PER_KG_H2, SOEC_KWH_PER_KG)):
        gwh = kwh / units / 1e6
        if abs(gwh / 160.0 - 1) > 0.005:
            problems.append(f"{name}: lifetime electricity {gwh:.1f} GWh, not Gerloff's 160")
    total = SMR_CCS_GAS_M3 * GAS_CO2_KG_PER_M3
    if abs(SMR_CCS_CO2_EMITTED + CO2_CAPTURED_PER_KG_H2 + SMR_CCS_CO2_GAP - total) > 1e-9:
        problems.append("SMR-CCS carbon does not close")
    if abs(CO2_CAPTURED_PER_KG_H2 / (SMR_CCS_CO2_EMITTED + CO2_CAPTURED_PER_KG_H2) - SMR_CCS_CAPTURE_RATE) > 0.001:
        problems.append("the printed SMR-CCS rows are not a 90 % capture")
    for name, d, want in (("AE", AE_STACK_KG, 23_345.3), ("PEM", PEM_STACK_KG, 690.175), ("SOEC", SOEC_STACK_KG, 9_454.7)):
        if abs(sum(d.values()) - want) > 0.05:
            problems.append(f"{name} stack mass {sum(d.values()):.1f} kg, ledger says {want}")
    if problems:
        raise AssertionError("hydrogen: " + "; ".join(problems))
    return f"OK - hydrogen: 160 GWh basis x3, carbon closes (gas {GAS_CO2_KG_PER_M3:.4f} kg CO2/m3), stacks tie"


# =============================================================================
# Processes — exact identities, with the search that found each one
# =============================================================================
processes = {
    # --- utilities shared by the gas routes ---------------------------------
    "gas_hp_gb": Process(
        query="market for natural gas high pressure GB", pick=1,
        identity=("market for natural gas, high pressure", "GB", "natural gas, high pressure"),
        why="hit 0 is the pressure-reduction step to low pressure; the reformer takes high-pressure gas"),
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
        identity=("market for gas turbine, 10MW electrical", "GLO", "gas turbine, 10MW electrical"),
        why="Hermesmann's own proxy for the steam turbine (SI Table S1)"),
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
    "ccs_diesel_burned": Process(
        query="market for diesel burned in building machine GLO", pick=0,
        identity=("market for diesel, burned in building machine", "GLO",
                  "diesel, burned in building machine"),
        why="the source linked diesel as a product and never burned it"),
    # --- methane pyrolysis -----------------------------------------------------
    "steel_chromium_188": Process(
        query="Market for steel, chromium steel 18/8 GLO", pick=1,
        identity=("market for steel, chromium steel 18/8", "GLO", "steel, chromium steel 18/8"),
        why="hit 0 is the hot-rolled variant; Hermesmann name the plain 18/8 market"),
    "steel_low_alloyed": Process(
        query="Market for steel, low-alloyed GLO", pick=1,
        identity=("market for steel, low-alloyed", "GLO", "steel, low-alloyed"),
        why="hit 0 is the hot-rolled variant; the plain low-alloyed market as named"),
    "palladium": Process(
        query="Market for palladium GLO", pick=1,
        identity=("palladium to generic market for metal catalyst for catalytic converter",
                  "GLO", "metal catalyst for catalytic converter"),
        why="as built: the search hit is palladium routed to the catalyst market, "
            "not 'market for palladium' itself; 8.5 mg/kg H2, 2.6 % of MP-E"),
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
        identity=("market for aluminium, wrought alloy", "GLO", "aluminium, wrought alloy"),
        why="hit 0 is the ingot-to-market transfer; the market is the dataset"),
    "tube_insulation": Process(
        query="tube insulation elastomere", pick=1,
        identity=("tube insulation production, elastomere", "RoW", "tube insulation, elastomere"),
        why="the RoW production dataset as exported; hit 0 is the GLO market"),
    "nickel_class1": Process(
        query="nickel class 1 market GLO", pick=0,
        identity=("market for nickel, class 1", "GLO", "nickel, class 1"),
        why="the 3.9.1 successor of the SI's 'market for nickel, 99.5%'"),
    "lorry_32t_euro6": Process(
        query="transport freight lorry >32 metric ton EURO6 RER", pick=0,
        identity=("market for transport, freight, lorry >32 metric ton, EURO6", "RER",
                  "transport, freight, lorry >32 metric ton, EURO6"),
        why="Gerloff §2.1: materials reach assembly by lorry >32 t EURO6 over 250 km"),
    # --- alkaline electrolyser, RoW datasets as exported ------------------------
    "polyethylene_ld_row": Process(
        query="polyethylene production low density granulate RoW", pick=0,
        identity=("polyethylene production, low density, granulate", "RoW",
                  "polyethylene, low density, granulate"),
        why="Gerloff SI Fig. 1 names low-density polyethylene; the export (and this module "
            "until 22 Oct 2026) carried high-density. RoW as exported"),
    "reinforcing_steel_row": Process(
        query="reinforcing steel production", pick=2,
        identity=("reinforcing steel production", "RoW", "reinforcing steel"),
        why="RoW as exported for the AE unit; hits 0-1 are the European and Austrian datasets"),
    "electronics_row": Process(
        query="electronics production control units", pick=1,
        identity=("electronics production, for control units", "RoW", "electronics, for control units"),
        why="RoW as exported for the AE unit; hit 0 is RER, which PEM and SOEC use"),
    "glass_fibre_row": Process(
        query="glass fibre production", pick=2,
        identity=("glass fibre production", "RoW", "glass fibre"),
        why="hits 0-1 are glass-fibre reinforced plastics; the plain glass fibre, RoW as exported"),
    "cr_steel_hot_rolled_row": Process(
        query="steel chromium steel 18/8 hot rolled production", pick=1,
        identity=("steel production, chromium steel 18/8, hot rolled", "RoW",
                  "steel, chromium steel 18/8, hot rolled"),
        why="RoW as exported for the AE unit; hit 0 is RER (PEM, SOEC)"),
    "cast_iron_row": Process(
        query="cast iron production", pick=6,
        identity=("cast iron production", "RoW", "cast iron"),
        why="hits 0-5 are machining-removal services; the production dataset, RoW as exported"),
    "ethylene_glycol_row": Process(
        query="ethylene glycol production", pick=0,
        identity=("ethylene glycol production", "RoW", "ethylene glycol")),
    "polypropylene_row": Process(
        query="polypropylene granulate production", pick=1,
        identity=("polypropylene production, granulate", "RoW", "polypropylene, granulate"),
        why="RoW as exported for the AE unit; hit 0 is RER"),
    "low_alloyed_steel_hr_row": Process(
        query="steel low-alloyed hot rolled production", pick=1,
        identity=("steel production, low-alloyed, hot rolled", "RoW", "steel, low-alloyed, hot rolled"),
        why="RoW as exported for the AE unit; hit 0 is RER"),
    "concrete_35mpa_cem3": Process(
        query="concrete production 35MPa", pick=0,
        identity=("concrete production, 35MPa, for building construction, with cement, CEM III/A",
                  "GLO", "concrete, 35MPa"),
        why="as built: AE's 'concrete production 35MPa' search landed on CEM III/A (hit 0); "
            "PEM and SOEC on CEM II/B (hit 2). Same strength class, different cement; the SI "
            "names a North-American recipe with RoW geography"),
    "tetrafluoroethylene_row": Process(
        query="tetrafluoroethylene production", pick=2,
        identity=("tetrafluoroethylene production", "RoW", "tetrafluoroethylene"),
        why="hits 0-1 are PTFE films on glass; the polymer itself, RoW as exported"),
    "polysulfone": Process(
        query="polysulfone production membrane filtration", pick=0,
        identity=("polysulfone production, for membrane filtration production", "GLO", "polysulfone")),
    "zirconium_oxide_row": Process(
        query="zirconium oxide production", pick=1,
        identity=("zirconium oxide production", "RoW", "zirconium oxide"),
        why="hit 0 is the Australian dataset; RoW as exported. Serves the AE diaphragm and the "
            "SOEC blocking layer (one process since 22 Oct 2026; two identical ones before)"),
    "electricity_lv_de": Process(
        query="market for electricity low voltage DE", pick=0,
        identity=("market for electricity, low voltage", "DE", "electricity, low voltage"),
        why="alkaline is as exported by Gerloff, on the German LV market; PEM and SOEC were re-based to GB"),
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
        identity=("concrete production, 35MPa, with cement, CEM II/B", "GLO", "concrete, 35MPa"),
        why="as built: PEM and SOEC's search landed on CEM II/B (hit 2); AE's on CEM III/A (hit 0). "
            "Same strength class"),
    "electronics_rer": Process(
        query="electronics production control units RER", pick=0,
        identity=("electronics production, for control units", "RER", "electronics, for control units")),
    "ethylene_glycol_rer": Process(
        query="ethylene glycol production RER", pick=4,
        identity=("ethylene glycol production", "RER", "ethylene glycol"),
        why="hits 0-3 are the monoethyl ether and the RoW glycols; the RER ethylene glycol as exported"),
    "lubricating_oil": Process(
        query="market for lubricating oil", pick=1,
        identity=("market for lubricating oil", "RER", "lubricating oil"),
        why="RER as exported; hit 0 is RoW"),
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
        identity=("tetrafluoroethylene production", "RER", "tetrafluoroethylene"),
        why="RER as exported for PEM and SOEC; hits 0-1 are PTFE films, hit 2 the RoW polymer (AE)"),
    "titanium": Process(
        query="titanium production GLO", pick=2,
        identity=("titanium production", "GLO", "titanium"),
        why="hits 0-1 are the ore markets (rutile, ilmenite); titanium metal, for the bipolar plates"),
    "zeolite": Process(
        query="zeolite powder production RER", pick=0,
        identity=("zeolite production, powder", "RER", "zeolite, powder")),
    "platinum": Process(
        query="market for platinum GLO", pick=0,
        identity=("market for platinum", "GLO", "platinum"),
        why="Gerloff's cathode catalyst is 0.075 kg of platinum and the anode's 0.8 kg of iridium, "
            "which has no 3.9.1 dataset; platinum stands in for both (SUBSTITUTED, SOURCE_DIFF S3) "
            "and is 21.7 % of the PEM unit at platinum's factor"),
    "electricity_lv_gb": Process(
        query="market for electricity low voltage GB", pick=0,
        identity=("market for electricity, low voltage", "GB", "electricity, low voltage"),
        why="manufacturing electricity of the PEM and SOEC units as exported (GB LV); the operation "
            "activities' electricity is stripped out by electrolysers.py and charged by the LP"),
    "heat_rer": Process(
        query="market group for heat district or industrial other than natural gas RER", pick=0,
        identity=("market group for heat, district or industrial, other than natural gas", "RER",
                  "heat, district or industrial, other than natural gas"),
        why="PEM's 0.28 kWh/kg of heat, on the dataset Gerloff export; the SOEC's heat is moved to "
            "Mehmeti's gas boiler because that is its source (heat_ng_boiler), PEM's stays as exported"),
    "heat_ng_boiler": Process(
        query="heat production natural gas at boiler modulating >100kW Europe without Switzerland", pick=0,
        identity=("heat production, natural gas, at boiler modulating >100kW",
                  "Europe without Switzerland", "heat, district or industrial, natural gas"),
        why="SOEC's 5.24 kWh/kg is Mehmeti et al. 2018 (Table 1), who supply it from "
            "'Heat, natural gas, at boiler modulating'; this is that dataset's v3 "
            "successor. >100kW because a 1 MW SOEC draws ~124 kW of heat. Gerloff 2021 "
            "copied the amount but swapped in heat_rer (52 % coal and peat). No GB boiler exists in 3.9.1"),
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
            "6.4 kg per stack, immaterial. 'market for aluminium oxide, non-metallurgical' "
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
                  "samarium-europium-gadolinium oxide"),
        why="Gerloff's own stand-in for yttria (paper §2.2.3)"),
    "silicone_product": Process(
        query="silicone product production RER", pick=0,
        identity=("silicone product production", "RER", "silicone product")),
    "lanthanum_oxide": Process(
        query="market for lanthanum oxide", pick=0,
        identity=("market for lanthanum oxide", "GLO", "lanthanum oxide"),
        why="the LSM layer's lanthanum, which Gerloff SI Fig. 5 row 53 names without an amount"),
    "strontium_carbonate": Process(
        query="strontium carbonate", pick=1,
        identity=("market for strontium carbonate", "GLO", "strontium carbonate"),
        why="the LSM layer's strontium (row 53); hit 0 is the production dataset, the market is taken"),
}

flows = {
    "co2": Flow(query="Carbon dioxide fossil", pick=0,
                identity=("Carbon dioxide, fossil", ("air",))),
    "nitrogen_air": Flow(query="Nitrogen air", pick=0,
                         identity=("Nitrogen", ("air",)),
                         why="Hermesmann Table 2 'Nitrogen to air', the reformer's inert vent; zero GWP"),
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
_kg, _m3, _kwh, _MJ, _unit, _m, _tkm = ("kilogram", "cubic meter", "kilowatt hour",
                                        "megajoule", "unit", "meter", "ton kilometer")
_GRID = FG(R.GB_GRID_HV_2025, database=R.GRID_DB)     # the study's own GB grid kWh
_N = STACKS_PER_UNIT_LIFE

activities = [
    Activity(
        code=R.SMR, name="Hydrogen production, SMR (Hermesmann & Müller 2022)",
        reference_product="hydrogen", unit=_kg, location="GB",
        comment="Steam methane reforming, 1 kg H2 at the plant: Hermesmann & Müller 2022 Table 2, every "
                "row at the printed amount (through SMR.XLSX), gas and electricity on GB datasets. The "
                "paper's excess-electricity credit is not taken; a carbon-balance closure on the gas's "
                "own carbon is added (DERIVED). No end-of-life, no delivery.",
        technosphere=[
            ("gas_hp_gb",         SMR_GAS_M3, _m3, "Natural gas, high pressure (Table 2)"),
            ("tap_water",         6.64,    _kg,   "Tap water"),
            ("concrete_normal",   6.60e-6, _m3,   "Concrete, plant"),
            ("steel_unalloyed",   5.06e-3, _kg,   "Steel, unalloyed, plant"),
            ("aluminium_cast",    4.17e-5, _kg,   "Aluminium, primary, cast alloy slab, plant"),
            ("cast_iron_glo",     6.18e-5, _kg,   "Cast iron, plant"),
            ("gas_turbine",       7.90e-10, _unit, "Gas turbine, 10MW — the paper's proxy for the steam turbine"),
            ("wastewater",        0.00172, _m3,   "Wastewater, average"),
            # Dropped, 22 Oct 2026: Table 2 "Output flows: Electricity 1.10 kWh" — the
            # paper's avoided-burden credit for excess steam (§3.1.1, Table 7). No
            # credits in this study (ASSUMPTIONS §5); -0.156 kg CO2e/kg on the study grid.
        ],
        biosphere=[
            ("co2",            SMR_CO2_EMITTED, _kg, "Carbon dioxide (Table 2); modelled as fossil"),
            ("co2",            SMR_CO2_CLOSURE, _kg,
             "DERIVED — carbon-balance closure on the linked gas's own carbon content, all to air"),
            ("oxygen_air",     0.31, _kg, "Oxygen to air"),
            ("nitrogen_air",  16.41, _kg, "Nitrogen to air (Table 2); zero GWP"),
            ("water_air",      2.93, _kg, "Water to air"),
            ("water_resource", 0.38, _m3, "Water, cooling"),
        ],
    ),
    Activity(
        code=R.SMR_CCS, name="Hydrogen production, SMR with 90 % CCS (Hermesmann & Müller 2022)",
        reference_product="hydrogen", unit=_kg, location="GB",
        comment="SMR with post-combustion MEA capture at 90 %, 1 kg H2 at the plant: Hermesmann & Müller "
                "2022 Table 2 at the printed amounts, the captured CO2 (8.90 kg, the paper's 90 % of "
                "9.89) sent to the foreground CCS treatment. The excess-electricity credit is not taken; "
                "the carbon-balance gap to the gas's own carbon is split 90 % to capture, 10 % to air "
                "(DERIVED). No end-of-life, no delivery.",
        technosphere=[
            (FG(R.CCS),           CO2_CAPTURED_PER_KG_H2, _kg,
             "CO2 captured, to the foreground CCS treatment: 90 % of 9.00 x 5.33/4.85 (Table 2, §4.1.1)"),
            (FG(R.CCS),           SMR_CCS_CLOSURE_CAPTURED, _kg,
             "DERIVED — the closure gap's captured share (90 %)"),
            ("gas_hp_gb",         SMR_CCS_GAS_M3, _m3, "Natural gas, high pressure (Table 2)"),
            ("tap_water",         4.68,    _kg,   "Tap water"),
            ("concrete_normal",   6.60e-6, _m3,   "Concrete, plant"),
            ("steel_unalloyed",   5.06e-3, _kg,   "Steel, unalloyed, plant"),
            ("aluminium_cast",    4.17e-5, _kg,   "Aluminium, primary, cast alloy slab, plant"),
            ("cast_iron_glo",     6.18e-5, _kg,   "Cast iron, plant"),
            ("gas_turbine",       7.90e-10, _unit, "Gas turbine, 10MW — the paper's proxy for the steam turbine"),
            ("wastewater",        0.00183, _m3,   "Wastewater, average"),
            # Dropped, 22 Oct 2026: Table 2 "Output flows: Electricity 0.05 kWh", the
            # avoided-burden credit; -0.007 kg CO2e/kg. Until 22 Oct the captured CO2 was
            # the export's 8.01 kg (= 9.00 - 0.99), not the paper's.
        ],
        biosphere=[
            ("co2",            SMR_CCS_CO2_EMITTED, _kg, "Carbon dioxide, the 10 % not captured (Table 2)"),
            ("co2",            SMR_CCS_CLOSURE_EMITTED, _kg,
             "DERIVED — the closure gap's emitted share (10 %)"),
            ("oxygen_air",     0.41, _kg, "Oxygen to air"),
            ("nitrogen_air",  20.84, _kg, "Nitrogen to air (Table 2, SMR-CCS 90 %); zero GWP"),
            ("water_air",      1.33, _kg, "Water to air"),
            ("water_resource", 1.18, _m3, "Water, cooling"),
        ],
    ),
    Activity(
        code=R.CCS, name="Carbon capture and storage, per kg CO2 (Hermesmann & Müller 2022 §3.2.3)",
        reference_product="carbon dioxide, captured", unit=_kg, location="GB",
        comment="Transport and storage of 1 kg of captured CO2: Hermesmann & Müller 2022 §3.2.3 (pipeline, "
                "injection well, well-drilling diesel at 15.4 kg per tonne, pumping and compression "
                "electricity), as the study's SimaPro project transcribed it (ccs.XLSX). A waste "
                "treatment the SMR-CCS route links to.",
        technosphere=[
            ("ccs_pipeline",      2.34666e-9, "kilometer", "Pipeline, natural gas, long distance — the CO2 pipeline"),
            ("ccs_well",          9.863e-8,   _m,          "Onshore well, oil/gas — the injection well"),
            ("ccs_diesel_burned", CCS_DIESEL_KG_PER_KG_CO2 * DIESEL_MJ_PER_KG, _MJ,
             "SUBSTITUTED — well drilling, Verma's 15.4 kg diesel read per tonne of CO2 and burned "
             "(the export linked it unburned)"),
            (_GRID, 0.0171, _kwh, "Electricity — pipeline pumping, on the study's GB grid"),
            (_GRID, 0.0070, _kwh, "Electricity — compressor to 150 bar, on the study's GB grid"),
        ],
        biosphere=[
            ("co2", 1.36106e-7, _kg, "CO2 fugitive emissions from pipeline and well"),
        ],
    ),
    Activity(
        code=R.MP_E, name="Hydrogen production, methane pyrolysis MP-E (Hermesmann & Müller 2022)",
        reference_product="hydrogen", unit=_kg, location="GB",
        comment="Electrically heated methane pyrolysis, 1 kg H2 at the plant: Hermesmann & Müller 2022 "
                "Table 3, every row at the printed amount, gas and electricity on GB datasets. The "
                "3.00 kg of solid carbon per kg H2 (Table 3 'Output flows: Carbon') is not credited "
                "against carbon black as §3.2.4 do: the whole burden sits on the hydrogen "
                "(ASSUMPTIONS §5; user decision 21 Oct 2026). No direct CO2.",
        technosphere=[
            ("gas_hp_gb",          5.72,    _m3,  "Natural gas, high pressure (Table 3)"),
            (_GRID,               10.29,    _kwh, "Electricity — electric heating, on the study's GB grid"),
            ("palladium",          8.45e-6, _kg,  "Palladium, catalyst"),
            ("copper_cathode",     5.63e-6, _kg,  "Copper, plant"),
            ("steel_low_alloyed",  1.99e-3, _kg,  "Steel, low-alloyed, plant"),
            ("steel_chromium_188", 3.89e-4, _kg,  "Steel, chromium 18/8, plant"),
            ("silica_sand",        6.18e-5, _kg,  "Silica sand"),
            ("tin",                2.58e-2, _kg,  "Tin, the molten-metal medium make-up"),
            ("silicon_carbide",    3.23e-6, _kg,  "Silicon carbide"),
            # Dropped by decision: Table 3 "Output flows: Carbon 3.00 kg" — no credit.
        ],
    ),
    Activity(
        code=R.AE_UNIT, name="Alkaline electrolyser, 1 MW, 20-year life (Gerloff 2021)",
        reference_product="alkaline electrolyser", unit=_unit, location="GLO",
        comment="One 1 MW alkaline electrolyser over its 20-year life: Gerloff 2021 SI Fig. 1 (18 BoP and "
                "3 stack components, every row at the printed amount, RoW datasets as exported), the "
                "stack's rows three times over (§2.1.3), SI Table 3's manufacturing electricity "
                "(already x3 on the stack) on the German LV market, and the 250 km assembly leg "
                "(§2.1). No delivery to site, no end-of-life.",
        technosphere=[
            ("polyethylene_ld_row",       464.6,    _kg,  "Water purifier / feed tank (SI Fig. 1 names LD polyethylene)"),
            ("extrusion_pipes",           464.6,    _kg,  "Water purifier / feed tank"),
            # SI Fig. 1 prints the gas separator's steel as 80 "(2 x)" and the diaphragm's
            # sheet rolling as 400; the export had 80 + 80 twice and 405 (corrected 21 Oct 2026).
            ("reinforcing_steel_row",    5134.4,    _kg,  "Reinforcing steel, BoP (aggregated as printed)"),
            ("sheet_rolling_steel",     10130.0,    _kg,  "Sheet rolling, steel, BoP (aggregated)"),
            ("electronics_row",           100.0,    _kg,  "Control panel / electronics"),
            ("aluminium_wrought",         160.0,    _kg,  "Transformer + frequency converter"),
            ("copper_cathode",            616.7,    _kg,  "Transformer + compressor + tubing/cables"),
            ("sheet_rolling_aluminium",   100.0,    _kg,  "Transformer and rectifier"),
            ("tube_insulation",           207.9,    _kg,  "Transformer + compressor + tubing"),
            ("wire_drawing_copper",       616.7,    _kg,  "Transformer + compressor + tubing"),
            ("glass_fibre_row",           464.6,    _kg,  "H2 drier and deoxidiser"),
            ("sheet_rolling_cr_steel",   6697.8,    _kg, 
             "Sheet rolling, chromium steel, BoP (26,892.2 less the stack's 20,194.4)"),
            ("cr_steel_hot_rolled_row",  6697.8,    _kg,  "Chromium steel 18/8 hot rolled, BoP (as above)"),
            ("cast_iron_row",             716.1,    _kg,  "Compressor + pumps and coolers"),
            ("ethylene_glycol_row",         7.0,    _kg,  "Diaphragm for compressor"),
            ("welding_arc_steel",          29.0,    _m,   "Buffer tank (SI prints m)"),
            ("polypropylene_row",           3.0,    _kg,  "Alkali-resistant rotary pump"),
            ("injection_moulding",          3.0,    _kg,  "Alkali-resistant rotary pump"),
            ("low_alloyed_steel_hr_row", 6075.6,    _kg,  "Container"),
            ("concrete_35mpa_cem3",         7.7,    _m3,  "Foundation"),
            # --- the stack, three times over its 20-year life (SI Fig. 1 rows 19-21, §2.1.3) ---
            ("sheet_rolling_cr_steel",   AE_STACK_KG["cr_steel"] * _N, _kg,
             "Stack x3 — anode and cathode with frame, sheet rolling, chromium steel (20,194.4 per stack)"),
            ("cr_steel_hot_rolled_row",  AE_STACK_KG["cr_steel"] * _N, _kg,
             "Stack x3 — anode and cathode with frame, chromium steel 18/8 hot rolled"),
            ("nickel_class1",            AE_STACK_KG["nickel"] * _N, _kg, "Stack x3 — anode + cathode, nickel (2,884.9 per stack)"),
            ("tetrafluoroethylene_row",  AE_STACK_KG["tfe"] * _N, _kg, "Stack x3 — gasket (144.2 per stack)"),
            ("polysulfone",              AE_STACK_KG["polysulfone"] * _N, _kg, "Stack x3 — diaphragm, Zirfon (48.8 per stack)"),
            ("zirconium_oxide_row",      AE_STACK_KG["zro2"] * _N, _kg, "Stack x3 — diaphragm, Zirfon (73.0 per stack)"),
            ("electricity_lv_de",      323773.4,    _kwh,
             "SI Table 3: BoP 37,113.5 + stack 286,659.9 kWh (the stack x3 already)"),
            ("lorry_32t_euro6",          _unit_tkm(AE_MATERIALS_KG_ONE_STACK, AE_STACK_KG), _tkm,
             "ADDED — Gerloff §2.1: materials to assembly, 250 km on the unit's mass with three stacks"),
        ],
    ),
    Activity(
        code=R.AE_OP, name="Hydrogen production, alkaline electrolysis (Gerloff 2021)",
        reference_product="hydrogen", unit=_kg, location="DE",
        comment="1 kg H2 from the alkaline unit: Gerloff 2021 SI Table 6 operating data at the printed "
                "amounts, the capital good at 1 unit per lifetime output (SI Table 4), electricity as "
                "exported on the German LV market (electrolysers.py strips it out and the LP charges "
                "the site's own power).",
        technosphere=[
            (FG(R.AE_UNIT),     AE_UNITS_PER_KG_H2, _unit, "Capital good: 1 unit per lifetime H2 (SI Table 4, as exported)"),
            ("water_deionised",  WATER_DEIONISED_KG_PER_KG, _kg, "Water, deionised (SI Table 6: 8.9 l)"),
            ("water_softened",  88.1,    _kg,  "Water, completely softened"),
            ("electrolyte_koh",  0.0037, _kg,  "Electrolyte KOH/LiOH"),
            ("electricity_lv_de", AE_KWH_PER_KG, _kwh, "Electricity LV DE — electrolysis, as exported (SI Table 6)"),
        ],
    ),
    Activity(
        code=R.PEM_UNIT, name="PEM electrolyser, 1 MW, 20-year life (Gerloff 2021)",
        reference_product="PEM electrolyser", unit=_unit, location="GB",
        comment="One 1 MW PEM electrolyser over its 20-year life: Gerloff 2021 SI Fig. 2 (17 BoP and 8 stack "
                "components at the printed amounts, RER datasets as exported), the stack's rows three "
                "times over (§2.1.3), SI Table 3's manufacturing electricity on GB LV, and the 250 km "
                "assembly leg. Platinum stands in for the anode's 0.8 kg of iridium. No delivery to "
                "site, no end-of-life.",
        technosphere=[
            ("extrusion_pipes",           464.6,    _kg,  "Water purifier / feed tank"),
            ("polyethylene_ld_rer",       464.6,    _kg,  "Water purifier / feed tank"),
            ("aluminium_wrought",         260.0,    _kg, 
             "Power electronics + purification, BoP (287.0 less the end plate's 27.0)"),
            ("sheet_rolling_aluminium",   200.0,    _kg, 
             "Power electronics + purification, BoP (227.0 less the end plate's 27.0)"),
            ("electronics_rer",           100.0,    _kg,  "Control panel / electronics"),
            ("cast_iron_rer",             600.0,    _kg,  "Diaphragm compressor"),
            ("ethylene_glycol_rer",         7.0,    _kg,  "Diaphragm compressor"),
            ("copper_cathode",            345.0,    _kg, 
             "Power electronics + gas separator + compressor, BoP (349.5 less the collector's 4.5)"),
            ("sheet_rolling_copper",      100.0,    _kg,  "Water gas separator, BoP (104.5 less the collector's 4.5)"),
            ("wire_drawing_copper",       245.0,    _kg,  "Power electronics + compressor"),
            ("injection_moulding",        300.0,    _kg,  "Valve"),
            ("polypropylene_rer",         300.0,    _kg,  "Valve"),
            ("lubricating_oil",           100.0,    _kg,  "Back pressure regulator"),
            ("reinforcing_steel_eur",    3312.3,    _kg,  "Power electronics + water purifier + compressor + container"),
            ("sheet_rolling_cr_steel",   4327.0,    _kg, 
             "Steel + heat exchanger + compressor + buffer, BoP (4,427.0 less the bolts' 100.0)"),
            ("sheet_rolling_steel",      5382.3,    _kg,  "Power electronics + tubing + water purifier + compressor"),
            ("cr_steel_hr_rer",          4327.0,    _kg,  "Chromium steel 18/8 hot rolled, BoP (as above)"),
            ("low_alloyed_steel_hr_rer", 3150.0,    _kg,  "Tubing/pump + container"),
            ("welding_arc_steel",          29.0,    _m,   "Buffer tank (SI prints kg; welding is per metre)"),
            ("tube_insulation",           115.0,    _kg,  "Power electronics + compressor"),
            ("zeolite",                   100.0,    _kg,  "Ion exchanger"),
            ("concrete_35mpa_cem2",         2.3,    _m3,  "Foundation"),
            # --- the stack, three times over its 20-year life (SI Fig. 2 rows 19-26, §2.1.3) ---
            ("aluminium_wrought",         PEM_STACK_KG["end_plate_al"] * _N, _kg, "Stack x3 — end plate, aluminium (27.0 per stack)"),
            ("sheet_rolling_aluminium",   PEM_STACK_KG["end_plate_al"] * _N, _kg, "Stack x3 — end plate, sheet rolling"),
            ("titanium",                  PEM_STACK_KG["titanium"] * _N, _kg, "Stack x3 — bipolar plates (528.0 per stack)"),
            ("tetrafluoroethylene_rer",   PEM_STACK_KG["tfe"] * _N, _kg, "Stack x3 — membrane polymer, Nafion proxy (16.0 per stack)"),
            ("carbon_black",              PEM_STACK_KG["carbon_black"] * _N, _kg,
             "Stack x3 — electrocatalyst support, anode + cathode (4.5 + 4.5 per stack)"),
            ("platinum",                  PEM_STACK_KG["platinum_for_pt_and_ir"] * _N, _kg,
             "SUBSTITUTED — Stack x3: 0.075 kg platinum (cathode) + 0.8 kg iridium (anode) per stack, both as platinum"),
            ("copper_cathode",            PEM_STACK_KG["copper"] * _N, _kg, "Stack x3 — current collector, copper (4.5 per stack)"),
            ("sheet_rolling_copper",      PEM_STACK_KG["copper"] * _N, _kg, "Stack x3 — current collector, sheet rolling"),
            ("sheet_rolling_cr_steel",    PEM_STACK_KG["bolts_cr_steel"] * _N, _kg,
             "Stack x3 — bolts and screws, sheet rolling (100.0 per stack)"),
            ("cr_steel_hr_rer",           PEM_STACK_KG["bolts_cr_steel"] * _N, _kg, "Stack x3 — bolts and screws, chromium steel"),
            ("synthetic_rubber",          PEM_STACK_KG["rubber"] * _N, _kg, "Stack x3 — gasket (4.8 per stack)"),
            ("electricity_lv_gb",      361672.3,    _kwh,
             "SI Table 3: BoP 50,000 + stack 311,672.3 kWh (the stack x3 already)"),
            ("lorry_32t_euro6",          _unit_tkm(PEM_MATERIALS_KG_ONE_STACK, PEM_STACK_KG), _tkm,
             "ADDED — Gerloff §2.1: materials to assembly, 250 km on the unit's mass with three stacks"),
        ],
    ),
    Activity(
        code=R.PEM_OP, name="Hydrogen production, PEM electrolysis (Gerloff 2021)",
        reference_product="hydrogen", unit=_kg, location="GB",
        comment="1 kg H2 from the PEM unit: Gerloff 2021 SI Table 6 operating data at the printed amounts, "
                "the capital good at 1 unit per lifetime output (SI Table 4), electricity on GB LV as "
                "exported (stripped out by electrolysers.py; the LP charges the site's own power), heat "
                "on the dataset Gerloff export.",
        technosphere=[
            (FG(R.PEM_UNIT),    PEM_UNITS_PER_KG_H2, _unit, "Capital good: 1 unit per lifetime H2 (SI Table 4, as exported)"),
            ("water_deionised",   WATER_DEIONISED_KG_PER_KG, _kg, "Water, deionised (SI Table 6: 8.9 l)"),
            ("water_softened",    88.1,   _kg,  "Water, completely softened"),
            ("electricity_lv_gb", PEM_KWH_PER_KG, _kwh, "Electricity LV GB — electrolysis (SI Table 6)"),
            ("heat_rer",           1.008, _MJ,  "Heat, district or industrial (SI Table 6: 0.28 kWh = 1.008 MJ)"),
        ],
    ),
    Activity(
        code=R.SOEC_UNIT, name="SOEC electrolyser, 1 MW, 20-year life (Gerloff 2021)",
        reference_product="SOEC electrolyser", unit=_unit, location="GB",
        comment="One 1 MW solid-oxide electrolyser over its 20-year life: Gerloff 2021 SI Figs 3-5 (48 BoP "
                "and 7 stack components at the printed amounts, RER datasets as exported), the stack's "
                "rows three times over (§2.1.3), SI Table 3's manufacturing electricity on GB LV, the "
                "250 km assembly leg, and ASSUMED La2O3 and SrCO3 for the LSM layer Gerloff name without "
                "an amount. No delivery to site, no end-of-life.",
        technosphere=[
            ("extrusion_pipes",           534.0,    _kg,  "Water purifier / pre-heating"),
            ("polyethylene_ld_rer",       534.0,    _kg,  "Water purifier / pre-heating"),
            ("aluminium_wrought",         401.0,    _kg,  "Frequency converters + power electronics + water pump"),
            ("sheet_rolling_aluminium",   100.0,    _kg,  "Power electronics"),
            ("electronics_rer",           100.0,    _kg,  "Control electronics"),
            ("abs_row",                     1.4,    _kg,  "Control panel / heater"),
            ("injection_moulding",          1.4,    _kg,  "Control panel / heater"),
            ("cast_iron_rer",            3000.0,    _kg,  "Diaphragm compressors 1-5"),
            ("ethylene_glycol_rer",        35.0,    _kg,  "Diaphragm compressors 1-5"),
            ("copper_cathode",            428.5,    _kg,  "Control + frequency converters + power electronics + pump"),
            ("wire_drawing_copper",       428.5,    _kg,  "Control + frequency converters + power electronics + pump"),
            ("tube_insulation",           176.6,    _kg,  "Frequency converters + power electronics + control + pump"),
            ("reinforcing_steel_eur",   13730.6,    _kg,  "BoP steel components"),
            ("sheet_rolling_cr_steel",  16621.4,    _kg, 
             "BoP chromium steel components, sheet rolling (25,597.5 less the air electrode's 8,976.1)"),
            ("sheet_rolling_steel",     12081.2,    _kg,  "BoP steel components"),
            ("cr_steel_hr_rer",         16621.4,    _kg,  "BoP chromium steel 18/8 hot rolled (as above)"),
            ("low_alloyed_steel_hr_rer", 3753.6,    _kg,  "Tubing + container — pre-heating"),
            ("welding_arc_steel",          33.3,    _m,   "Buffer tank (pre-heating)"),
            ("concrete_35mpa_cem2",         2.3,    _m3,  "Foundation"),
            # --- the stack, three times over its 20-year life (SI Fig. 5 rows 49-55, §2.1.3) ---
            ("sheet_rolling_cr_steel",  SOEC_STACK_KG["cr_steel"] * _N, _kg,
             "Stack x3 — air electrode / interconnect, sheet rolling, chromium steel (8,976.1 per stack)"),
            ("cr_steel_hr_rer",         SOEC_STACK_KG["cr_steel"] * _N, _kg,
             "Stack x3 — air electrode / interconnect, chromium steel 18/8 hot rolled"),
            ("praseodymium_oxide",      SOEC_STACK_KG["pr_oxide"] * _N, _kg, "Stack x3 — air electrode screen printing (9.0 per stack)"),
            ("nickel_class1",           SOEC_STACK_KG["nickel"] * _N, _kg, "Stack x3 — air electrode 7.5 + firing 136.6 per stack"),
            ("zirconium_oxide_row",     SOEC_STACK_KG["zro2"] * _N, _kg, "Stack x3 — blocking layer (170.7 per stack)"),
            ("samarium_seg_oxide",      SOEC_STACK_KG["seg_oxide"] * _N, _kg,
             "Stack x3 — blocking layer 14.8 + screen printing 22.9 per stack"),
            ("cerium_oxide",            SOEC_STACK_KG["ce_oxide"] * _N, _kg, "Stack x3 — blocking layer screen printing (91.5 per stack)"),
            ("aluminium_oxide",         SOEC_STACK_KG["al2o3"] * _N, _kg,
             "Stack x3 — electrolyte + H2 electrode, glass sealant (6.4 per stack)"),
            ("boric_oxide",             SOEC_STACK_KG["b2o3"] * _N, _kg, "Stack x3 — electrolyte + H2 electrode (6.4 per stack)"),
            ("barium_oxide",            SOEC_STACK_KG["bao"] * _N, _kg, "Stack x3 — electrolyte + H2 electrode (6.4 per stack)"),
            ("silicone_product",        SOEC_STACK_KG["silicone"] * _N, _kg,
             "Stack x3 — electrolyte sealant (6.4 per stack; the figure's dataset)"),
            ("lanthanum_oxide",         SOEC_LA2O3_KG_PER_STACK * _N, _kg,
             "ASSUMED — Stack x3: LSM layer's La2O3, 0.563 of a 19.5 kg layer per stack (Gerloff row 53 gives no amount)"),
            ("strontium_carbonate",     SOEC_SRCO3_KG_PER_STACK * _N, _kg,
             "ASSUMED — Stack x3: LSM layer's SrCO3, 0.128 of a 19.5 kg layer per stack"),
            ("electricity_lv_gb",      443093.5,    _kwh,
             "SI Table 3: BoP 76,420.2 + stack 366,673.3 kWh (the stack x3 already)"),
            ("lorry_32t_euro6",          _unit_tkm(SOEC_MATERIALS_KG_ONE_STACK, SOEC_STACK_KG), _tkm,
             "ADDED — Gerloff §2.1: materials to assembly, 250 km on the unit's mass with three stacks"),
        ],
    ),
    Activity(
        code=R.SOEC_OP, name="Hydrogen production, SOEC electrolysis (Gerloff 2021)",
        reference_product="hydrogen", unit=_kg, location="GB",
        comment="1 kg H2 from the SOEC unit: Gerloff 2021 SI Table 6 operating data at the printed amounts, "
                "the capital good at 1 unit per lifetime output (SI Table 4), electricity on GB LV as "
                "exported (stripped out by electrolysers.py), and the 5.24 kWh of heat on Mehmeti et al. "
                "2018's natural-gas boiler, the source Gerloff copied the amount from.",
        technosphere=[
            (FG(R.SOEC_UNIT),   SOEC_UNITS_PER_KG_H2, _unit, "Capital good: 1 unit per lifetime H2 (SI Table 4, as exported)"),
            ("water_deionised",    WATER_DEIONISED_KG_PER_KG, _kg, "Water, deionised (SI Table 6: 8.9 l)"),
            ("water_softened",   644.7,   _kg,  "Water, completely softened"),
            ("electricity_lv_gb", SOEC_KWH_PER_KG, _kwh, "Electricity LV GB — electrolysis (SI Table 6)"),
            ("heat_ng_boiler",    SOEC_HEAT_KWH_PER_KG * 3.6, _MJ,
             "SUBSTITUTED — heat on Mehmeti 2018's natural-gas boiler (5.24 kWh = 18.864 MJ), not Gerloff's coal-heavy heat"),
        ],
    ),
]


def inventory() -> Inventory:
    return Inventory(name="hydrogen (Hermesmann & Müller 2022 fossil routes, Gerloff 2021 electrolysers)",
                     database=R.HYDROGEN_DB, processes=processes, flows=flows, activities=activities)
