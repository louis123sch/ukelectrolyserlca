"""
=============================================================================
dc_config — the Data Centre Optimiser's fixed modelling assumptions.
=============================================================================

What goes in here: parameters that define the *inventories and coefficients*
the optimiser runs on — the Brightway project, the GB grid-mix scoring, and
the fuel cell, hydrogen tank, step-up transformer and utility-scale PV
foregrounds that ``2.tech_lca_foreground.ipynb`` builds. Notebook 2 reads
everything here with ``from dc_config import *``; the ``optimisation/``
modules read it as ``import dc_config as cfg``.

What does not: anything you choose per run. IT load, PUE, site, dates, which
assets to consider and the objective are inputs on the optimiser page (or
arguments to ``dc_runner`` / ``scripts/run_dc_*.py``), and a grid build takes
its region and window as arguments (``optimisation/grid_build.py``). Nothing
edits this file at run time.

Edit, save, then restart whatever imported it. Changing anything that notebook
2 uses means re-running notebook 2.
"""

# =============================================================================
# Brightway project / database settings
# =============================================================================
PROJECT_NAME      = "hydrogen-smr"
ECOINVENT_VERSION = "3.9.1"
SYSTEM_MODEL      = "apos"                       # "apos", "cutoff", "consequential", ...
FOREGROUND_DB     = "hydrogen foreground"
DC_FOREGROUND_DB  = "data centre foreground"  # separate DB for non-hydrogen foregrounds (e.g. notebook 2's Zhang et al. data centre process)
FC_FOREGROUND_DB  = "fuel cell foreground"    # separate DB for notebook 2's Babatunde et al. 1 kW PEM fuel cell stack

# Set True only if you need to import ecoinvent into the active Brightway project.
RUN_IMPORT_ECOINVENT = False

# Rebuilds the foreground database from the SimaPro-derived inventories.
# Leave False once the foreground database already exists.
RUN_BUILD_FOREGROUND_DATABASE = True

# =============================================================================
# Data centre facility (notebook 2 — "data centre foreground")
# =============================================================================
DC_OPERATION_YEARS = 25   # the data centre foreground's operating life
# Zhang et al.'s own PUE. Used once, to read an IT load out of the foreground's
# facility draw; every other PUE in this study is the one the caller sets.
DC_REFERENCE_PUE = 1.4

# =============================================================================
# GB grid carbon (optimisation/grid_build.py)
# =============================================================================
# Each Carbon Intensity API fuel is scored with one ecoinvent GB electricity
# activity: lca_helpers.TECH_SPECS holds the search query, and this picks which
# of the search results to use (0 = first hit). Changing one changes every grid
# series built afterwards — not the ones already on disk.
GRID_CANDIDATE_INDEX = {
    # Conventional generation
    "GAS":                3,
    "COAL":               0,
    "NUCLEAR":            1,
    # Wind sub-technologies (composite, split by lca_helpers.WIND_GROUP_WEIGHTS)
    "WIND_GT3_ONSHORE":   0,
    "WIND_13_OFFSHORE":   0,
    "WIND_13_ONSHORE":    0,
    "WIND_EMB":           0,
    # Hydro
    "HYDRO":              0,
    # Imports (composite, split by lca_helpers.IMPORT_GROUP_WEIGHTS)
    "IMPORTS_FR":         0,
    "IMPORTS_IE":         0,
    "IMPORTS_NL":         4,
    # Other generation
    "BIOMASS":            0,
    "OTHER":              0,
    "SOLAR":              0,
    "STORAGE":            0,
}

# Transmission and distribution losses: every kWh delivered needs this much more
# generated. Applied to the whole mix, so grid carbon is per kWh *delivered*.
APPLY_LOSSES          = True
MARKET_LOSS_SHARE     = 0.031642692177
MARKET_LOSS_FACTOR = (1.0 + MARKET_LOSS_SHARE) if APPLY_LOSSES else 1.0

# =============================================================================
# PEM fuel cell operation (notebook 2 — "fuel cell foreground")
# =============================================================================
# Turns the Babatunde et al. (2024) stack into a generator: 1 kWh of AC
# electricity from hydrogen. Every value here is a literature parameter, not a
# fitted one — see notebook 2's "PEM fuel cell operation" markdown for the
# citations and for why the activity has no direct biosphere flows.

FC_RATED_POWER_KW     = 1.0        # matches the paper's 1 kW stack
FC_H2_LHV_KWH_PER_KG  = 33.33      # hydrogen lower heating value, 120 MJ/kg

# Net AC electrical efficiency at beginning of life, LHV basis. DOE's stationary
# 1-25 kWe target is >=45% on natural gas (i.e. including reformer losses, so a
# pure-H2 system should beat it); reported stack efficiency for a 1 kW H2-fed
# PEMFC is ~51.6%, and ~50% is the usual figure quoted for mid-size stationary
# PEMFC. 0.50 sits in the middle; 0.45-0.55 is the defensible range.
FC_ETA_NET_BOL        = 0.50

# Mean-over-life efficiency as a fraction of beginning-of-life. PEMFC end of life
# is conventionally defined as a 10% drop in cell voltage (Stropnik et al. 2022);
# degrading linearly to that point gives a lifetime mean of 95% of BOL. Set to
# 1.0 to model a non-degrading stack.
FC_DEGRADATION_DERATE = 0.95

FC_STACK_LIFETIME_H   = 32_000     # Babatunde et al. 2024, section 3.4 (their own figure)
FC_SYSTEM_LIFETIME_H  = 60_000     # DOE 2020 stationary target; BoP outlives the stack

# Balance of plant and maintenance are taken from ecoinvent's own PEMFC datasets,
# each written as (ecoinvent dataset - its stack content), so the paper's stack
# can never be double-counted.
FC_BOP_LOCATION = "CH"   # the only location where ecoinvent links the stack directly

# ecoinvent's PEMFC is a domestic micro-CHP unit. Two of its items are artefacts
# of that setting rather than of fuel cells: the hot-water/hydronic kit (34% of
# the system's GWP) and 200 km of passenger-car travel per service visit (a
# technician driving to a house). Neither applies to a rack of stacks in a data
# centre, so both are subtracted by default. Set True if you are modelling a
# domestic micro-CHP instead.
FC_DOMESTIC_CHP_ITEMS = False

# Stack fraction inside one ecoinvent maintenance event — i.e. a full stack is
# replaced every 1/0.167 ~ 6 services. Used to scale maintenance to this
# notebook's own stack-replacement rate, and to subtract the stack ecoinvent
# bundles into it.
FC_MAINT_STACK_FRACTION = 0.167

# Which hydrogen the fuel cell burns: (database, activity code). Any per-kg-H2
# activity works — swap in ae_op_/soec_op_/smr_ for a different supply chain.
FC_H2_SOURCE = ("hydrogen foreground", "pem_op_hermesmann_1kg_h2")

# --- derived ---
FC_ETA_NET_MEAN = FC_ETA_NET_BOL * FC_DEGRADATION_DERATE
FC_H2_PER_KWH   = 1.0 / (FC_ETA_NET_MEAN * FC_H2_LHV_KWH_PER_KG)      # kg H2 / kWh AC
FC_STACK_PER_KWH = 1.0 / (FC_RATED_POWER_KW * FC_STACK_LIFETIME_H)    # unit / kWh AC
FC_BOP_PER_KWH   = 1.0 / (FC_RATED_POWER_KW * FC_SYSTEM_LIFETIME_H)   # unit / kWh AC
# Maintenance events per kWh, tied to the stack-replacement rate above so the two
# can never disagree: ~6 services per stack, then x0.5 for ecoinvent's 2 kW unit.
FC_MAINT_PER_KWH = (FC_STACK_PER_KWH / FC_MAINT_STACK_FRACTION) * 0.5

if not 0.0 < FC_ETA_NET_BOL <= 1.0:
    raise ValueError("FC_ETA_NET_BOL must be a fraction in (0, 1].")
if not 0.0 < FC_DEGRADATION_DERATE <= 1.0:
    raise ValueError("FC_DEGRADATION_DERATE must be a fraction in (0, 1].")
if FC_STACK_LIFETIME_H <= 0 or FC_SYSTEM_LIFETIME_H <= 0:
    raise ValueError("Fuel cell lifetimes must be positive.")
if not 0.0 < FC_MAINT_STACK_FRACTION <= 1.0:
    raise ValueError("FC_MAINT_STACK_FRACTION must be a fraction in (0, 1].")

# =============================================================================
# Hydrogen storage tank (notebook 2)
# =============================================================================
# ecoinvent 3.9.1 has no hydrogen storage vessel, so the tank is modelled the
# way Gandiglio et al. (2022) model theirs: as a mass of steel and nothing else.
#   M. Gandiglio, P. Marocco, I. Bianco, D. Lovera, G.A. Blengini, M. Santarelli,
#   "Life cycle assessment of a renewable energy system with hydrogen-battery
#   storage for a remote off-grid community", Int. J. Hydrogen Energy 47 (2022).
# Their inventory is one line - 15,652 kg of chromium steel 18/8 for the 21.6 m3
# / 28 bar vessel at Ginostra - amortised over the plant's 25-year output.
H2_STORAGE_FOREGROUND_DB = "hydrogen storage foreground"

TANK_DESIGNS = {
    # The real vessel in the paper. Low-pressure buffer, so heavy per kg stored.
    "gandiglio_28bar": {
        "steel_process": ("market for steel, chromium steel 18/8", "GLO"),
        "steel_kg": 15_652.0, "volume_m3": 21.6, "pressure_bar": 28.0,
        "note": "Gandiglio et al. 2022, Table 3 - as-built 21.6 m3 stainless vessel at Ginostra",
    },
    # Type I all-steel cylinder at 200 bar, sized from ~1 wt% gravimetric
    # capacity. Roughly 3x lighter per kg H2 than the 28 bar design above.
    "type1_200bar": {
        "steel_process": ("market for steel, low-alloyed, hot rolled", "GLO"),
        "steel_kg_per_kg_h2": 100.0, "pressure_bar": 200.0,
        "note": "Type I seamless cylinder, ~1 wt% H2 - typical industrial stationary bottle",
    },
}
TANK_DESIGN = "gandiglio_28bar"
if TANK_DESIGN not in TANK_DESIGNS:
    raise ValueError(f"TANK_DESIGN must be one of {list(TANK_DESIGNS)}")

# Conditions used to convert the paper's tank volume + pressure into kg of H2.
TANK_H2_TEMPERATURE_K   = 288.15   # 15 C
TANK_H2_COMPRESSIBILITY = 1.017    # Z for H2 at ~28 bar; 1.0 would be ideal gas

TANK_LIFETIME_YEARS = 25   # the paper's plant lifetime; the tank is never replaced
# Electrolyser delivers at ~30 bar. Charged as electricity in the dispatch, not
# as tank capital. Zero for the 28 bar design, which needs no extra compression.
TANK_COMPRESSION_KWH_PER_KG = 0.0 if TANK_DESIGNS[TANK_DESIGN]["pressure_bar"] <= 30 else 2.5

# =============================================================================
# Wind turbine step-up transformers (notebook 2)
# =============================================================================
# A turbine generates at 690 V, which is LOW voltage (<1 kV). The data centre
# draws at MEDIUM voltage (1-24 kV). Something must bridge those, and it is not
# optional: 100 MW at 690 V is 83,674 A, which is not a cable. So every turbine
# carries its own transformer at the foot of its tower - one per TURBINE, not
# one per farm, and a 100 MW farm has fifty of them.
#
# Nothing in this study contains them. ecoinvent's wind turbine dataset lists
# its own parts ("Rotor, Nacelle, Electronics, Tower, Foundation") and no
# transformer is among them; its only electrical item is 438.7 kg of control
# electronics, against the 3-5 t a 2 MW turbine transformer weighs. Its network
# connection dataset is cable and trench.
#
# And ecoinvent cannot supply the asset. It has four transformer activities,
# which are two products with a market and a production each, and BOTH are
# electronics - its own comment says "a typical high voltage use transformer in
# electronic modules has an average weight of 280 g ... used in the information
# and communication technology". There is no substation, switchgear or power
# transformer dataset at any rating. So the transformer is assembled here from a
# published bill of materials, the way the hydrogen tank above is.
#   H. Leng, X. Zhou, J. Chen, D. Chen, M. Li, Y. Lin, Z. Yue, N. Zhong,
#   "Life Cycle Assessment of an Onshore Wind Farm: Carbon Emission Evaluation
#   and Mitigation Pathway Design", Processes 14(7), 1045 (2026),
#   Supplementary Table S1. PowerChina Huadong Engineering.
# Their Gaoyou farm is fifty 2 MW turbines, 100 MW, each with an S11-2200/35 box
# transformer. Table S1 gives the materials for all fifty as one bill.
TRANSFORMER_FOREGROUND_DB = "transformer foreground"

# Leng Table S1, box transformers - the whole population on one 100 MW farm.
# TRANSCRIBED. Masses in kg.
TX_LENG_FARM_MW      = 100.0
TX_LENG_N_TURBINES   = 50
TX_LENG_UNIT_MVA     = 2.2       # from the model number S11-2200/35
TX_LENG_BOX_KG = {
    "steel":  163_500.0,
    "iron":    53_300.0,
    "copper":  46_800.0,
    "oil":     17_600.0,
    "silica":   1_143.0,
}
# Each Leng material -> the ecoinvent activities that make it. Steel and copper
# carry their forming step, as grid_connection.py's own rebuild does.
TX_MATERIAL_PROCESSES = {
    "steel":  [("market for steel, low-alloyed", "GLO"),
               ("market for sheet rolling, steel", "GLO")],
    # ASSUMED: Leng lists Steel and Iron separately and does not say what the
    # second is. Read as core steel - a transformer contains no cast iron, and
    # Teffera's equivalent inventory is steel and copper only. Scoring it as
    # cast iron instead moves the answer ~4%.
    "iron":   [("market for steel, low-alloyed", "GLO"),
               ("market for sheet rolling, steel", "GLO")],
    "copper": [("market for copper, cathode", "GLO"),
               ("market for wire drawing, copper", "GLO")],
    "oil":    [("market for lubricating oil", "RER")],
    # ASSUMED proxy: ecoinvent has no silicon dioxide market. 0.4% of the mass
    # and 0.005% of the carbon, so the choice does not matter.
    "silica": [("market for silica sand", "GLO")],
}

# The voltage chain, which is what makes the above the RIGHT boundary.
TX_TURBINE_TERMINAL_V     = 690.0      # TRANSCRIBED - Teffera Table 2, all four models
TX_MEDIUM_VOLTAGE_BAND_KV = (1.0, 24.0)  # TRANSCRIBED - ecoinvent GB MV market comment
# ASSUMED. The site collects inside the band the data centre draws at, so the
# chain closes with no further transformation to charge. Leng's units are wound
# for 35 kV, above the band; a 20 kV unit of the same rating carries less
# insulation and is lighter, so taking their mass errs HIGH - the safe direction.
TX_SITE_COLLECTION_KV = 20.0

TX_ASSET_LIFE_YEARS = 35.0   # this study's own generation life; see renewables.py

# --- solar inverter-station step-up transformers ------------------------------
# The solar counterpart of the wind bill above, and it closes the gap DATA_GAPS
# registered: solar used to carry ONE invented plant-rated unit on ecoinvent's
# 280 g electronics dataset, with no per-inverter-station transformers at all.
#
# A utility PV plant collects at the inverter's LOW-voltage AC terminals and
# steps up to the site's medium-voltage collection network, exactly as a turbine
# does. The source unit is wound 20/0.4 kV - which is TX_SITE_COLLECTION_KV and
# 400 V, i.e. precisely this study's own chain, so unlike the wind units (wound
# for 35 kV, whose mass therefore errs high) no voltage adjustment is needed.
#
#   M. Goetz, R. Deuber, N. Gazbour, P.H. Brailovsky, S. Nold,
#   M. Marchand-Lasserre, R. Frischknecht, A.A. Khan, G. Bovo, M. Stucki (2026),
#   "Life Cycle Inventories of Photovoltaic Systems", IEA PVPS Task 12,
#   Report T12-33:2026, July 2026. DOI 10.69766/WJTE1771.
#   Table 49 (the transformer) and Table 50 (four of them per 10 MWp plant).
# Workbook shipped at optimisation/data/IEA-PVPS-T12-33-2026-LCI-PV-SupplyChains.xlsx
UPV_TX_SOURCE = ("IEA PVPS Task 12, Report T12-33:2026 (July 2026), "
                 "Tables 49 and 50")
UPV_TX_UNIT_MVA        = 2.5      # TRANSCRIBED - "oil-immersed, 2.5 MW"
UPV_TX_PRIMARY_KV      = 20.0     # TRANSCRIBED - voltage ratio 20/0.4 kV
UPV_TX_SECONDARY_KV    = 0.4      # TRANSCRIBED - inverter LV terminals
UPV_TX_REFERENCE_MWP   = 10.0     # TRANSCRIBED - the 10 MWp reference plant
UPV_TX_UNITS_PER_PLANT = 4        # TRANSCRIBED - Table 50 title, 4 x 2.5 MVA
# Units per MWp of cap_solar. Read off the reference plant rather than derived,
# so no DC/AC ratio and no power factor are needed - both were ASSUMED before.
UPV_TX_UNITS_PER_MWP = UPV_TX_UNITS_PER_PLANT / UPV_TX_REFERENCE_MWP

# Table 49, per ONE 2.5 MVA unit. TRANSCRIBED except where noted.
# Rolling and metal-working rows are FORMING of mass already counted, so they
# are held separately from the materials and never summed into the mass.
UPV_TX_MATERIALS_KG = {
    "steel_converter":  2_079.8,   # GOES core base material, converter route
    "mg_silicon":          73.202, # the core's silicon alloying input
    "oil":              1_060.0,
    "aluminium":          618.0,   # winding conductors - ALUMINIUM, not copper
    "steel_lowalloy":   1_734.52,  # tank, frame, fittings
    "kraft_paper":         34.11,
    "epoxy":               15.0,
    "copper":               2.1,   # contacts only; the windings are aluminium
    "chromium_steel":       2.5,
    "rubber":               0.2,
    "paint":               13.61,
}
# Hardboard pressboard. The workbook cell reads 36.96 m3, which is out by 1000x:
# 36.96 m3 of hardboard is ~47 TONNES, eight times the whole transformer. The
# report states a total of ~5,680 kg, and the materials above sum to 5,633.04,
# leaving 46.9 kg = 0.03696 m3 at hardboard's ~1,270 kg/m3. So the cell is dm3
# mislabelled as m3, and the corrected value closes the report's own total to
# three significant figures. DERIVED, and checked by upv_tx_check() below.
UPV_TX_FIBREBOARD_M3      = 0.03696
UPV_TX_FIBREBOARD_KG      = 46.9      # only used to reconcile the stated total
UPV_TX_STATED_TOTAL_KG    = 5_680.0   # TRANSCRIBED - the report's own figure

# Forming and process energy, per unit. TRANSCRIBED.
UPV_TX_FORMING_KG = {
    "hot_rolling":        2_153.0,   # = core mass, hot rolled
    "sheet_rolling_steel": 4_306.0,  # = core mass rolled twice (hot then cold)
    "sheet_rolling_alu":     618.0,  # = the aluminium winding
    "alu_metalworking":      618.0,
}
UPV_TX_ELECTRICITY_KWH = 2_368.3
UPV_TX_HEAT_MJ         = 9_903.8

# Each row -> exactly one ecoinvent 3.9.1 apos activity. Locations are pinned so
# a match is never ambiguous; the notebook refuses anything that is not unique.
UPV_TX_PROCESSES = {
    "steel_converter":     ("steel production, converter, unalloyed", "RER"),
    "mg_silicon":          ("market for silicon, metallurgical grade", "GLO"),
    "oil":                 ("market for lubricating oil", "RER"),
    "aluminium":           ("market for aluminium, wrought alloy", "GLO"),
    "steel_lowalloy":      ("market for steel, low-alloyed", "GLO"),
    # ASSUMED proxy: ecoinvent has no unbleached kraft paper. Average kraft is
    # slightly the more burdened, so 34 kg of 5,680 errs marginally high.
    "kraft_paper":         ("market for kraft paper", "RER"),
    "epoxy":               ("market for epoxy resin, liquid", "RER"),
    "copper":              ("market for copper, cathode", "GLO"),
    "chromium_steel":      ("market for steel, chromium steel 18/8", "GLO"),
    "rubber":              ("market for synthetic rubber", "GLO"),
    "paint":               ("market for alkyd paint, white, without water, "
                            "in 60% solution state", "RER"),
    "hot_rolling":         ("market for hot rolling, steel", "GLO"),
    "sheet_rolling_steel": ("market for sheet rolling, steel", "GLO"),
    "sheet_rolling_alu":   ("market for sheet rolling, aluminium", "GLO"),
    "alu_metalworking":    ("market for metal working, average for aluminium "
                            "product manufacturing", "GLO"),
}
UPV_TX_FIBREBOARD_PROCESS  = ("market for fibreboard, hard", "RER")
# GB rather than the source's ENTSO-E: the factory is not the point, and this
# study is GB throughout. Moves the answer <1% - process energy is 6% of total.
UPV_TX_ELECTRICITY_PROCESS = ("market for electricity, medium voltage", "GB")
UPV_TX_HEAT_PROCESS        = ("heat production, natural gas, at industrial "
                              "furnace >100kW", "Europe without Switzerland")


def upv_tx_check():
    """The transcribed bill must rebuild the report's own stated unit mass.

    This is the guard on the fibreboard correction above: if someone restores
    the workbook's literal 36.96 m3, or edits a material, the reconciliation
    against the report's 5,680 kg fails here rather than silently in the LCA.
    """
    mass = sum(UPV_TX_MATERIALS_KG.values()) + UPV_TX_FIBREBOARD_KG
    if abs(mass - UPV_TX_STATED_TOTAL_KG) > 1.0:
        raise AssertionError(
            f"UPV transformer bill sums to {mass:,.2f} kg against the report's "
            f"stated {UPV_TX_STATED_TOTAL_KG:,.0f} kg per unit")
    missing = (set(UPV_TX_MATERIALS_KG) | set(UPV_TX_FORMING_KG)) - set(UPV_TX_PROCESSES)
    if missing:
        raise AssertionError(f"no ecoinvent process mapped for {sorted(missing)}")
    if not (1.0 <= UPV_TX_SITE_KV_CHECK() <= 24.0):
        raise AssertionError("the solar step-up does not land in the medium-"
                             "voltage band the data centre draws at")
    return (f"OK - {mass:,.0f} kg per {UPV_TX_UNIT_MVA:g} MVA unit "
            f"({mass / UPV_TX_UNIT_MVA:,.0f} kg/MVA), "
            f"{UPV_TX_UNITS_PER_MWP:g} units per MWp")


# =============================================================================
# 4.4 utility-scale PV plant — embodied carbon per MWp installed
# =============================================================================
# The solar generation coefficient, rebuilt. What it replaces: the default basis
# was IEA PVPS Task 12's 2023 data update, 35.8 g CO2e/kWh — a fine number, but
# quoted against a **3 kWp ROOFTOP** reference system. `cap_solar` is a
# utility-scale MWp, so a solar farm was being priced with roof rails, a
# domestic string inverter, no perimeter fence, no plant-scale site cabling and
# no land. That basis is also the one coefficient in the study not scored on
# ecoinvent 3.9.1 apos (IEA PVPS use UVEK in SimaPro, with recycled-content
# allocation rather than APOS).
#
# This basis is built the way every other foreground here is: take a published
# bill of materials and rescore it in this project, which makes it ecoinvent
# 3.9.1 apos BY CONSTRUCTION.
#
#   Smith, B.L., Sekar, A., Mirletz, H., Heath, G. & Margolis, R. (2024),
#   "An Updated Life Cycle Assessment of Utility-Scale Solar Photovoltaic
#   Systems Installed in the United States", NREL/TP-7A40-87372, Appendix A.
#
# Smith publishes on ecoinvent **cut-off**. His INVENTORY is used and rescored
# on apos; his results are never transcribed. That is the whole reason this is
# a rebuild rather than a citation — a cut-off number cannot simply be
# relabelled, because APOS and cut-off differ exactly where recycled content
# matters, which for a PV plant is the aluminium, steel and copper.
SOLAR_FOREGROUND_DB = "solar foreground"
UPV_PV_SOURCE = ("Smith et al. (2024), NREL/TP-7A40-87372, Appendix A "
                 "(inventory rescored on ecoinvent 3.9.1 apos)")
UPV_PV_BILL = "optimisation/data/upv_smith_bill.json"

# System spec — Smith Table 3. TRANSCRIBED.
UPV_PV_MODULE_W   = 405.0     # Wdc per module at STC
UPV_PV_MODULE_M2  = 1.99      # m2 per module
UPV_PV_MODULE_EFF = 0.203     # 20.3 %, the national average silicon module
UPV_PV_W_PER_M2   = UPV_PV_MODULE_W / UPV_PV_MODULE_M2      # 203.5
UPV_PV_M2_PER_MWP = 1e6 / UPV_PV_W_PER_M2                   # 4,914

# Inverter loading ratio. Smith STATES 1.34 in Table 3, but his Table A14 uses
# 4.30E-05 inverters/m2, which at this module implies 1.75. The two are
# inconsistent in the source; 1.34 is taken because it is the stated design
# value and 1.75 is not a plausible UPV loading ratio. ASSUMED where they
# disagree; see upv_pv_check(), which refuses an implausible band.
UPV_PV_ILR = 1.34
UPV_PV_INVERTER_MVA = 2.7
UPV_PV_INVERTERS_PER_MWP = 1.0 / (UPV_PV_INVERTER_MVA * UPV_PV_ILR)

# --- scope, as decided ------------------------------------------------------
# Every exclusion here is a scope choice, not a data gap, and each one is
# stated with its direction of bias.
UPV_PV_SCOPE = {
    "mounting": "fixed tilt (IEA PVPS T12-33:2026 Z-PV-239, 20 deg pile-driven "
                "steel table) SUBSTITUTED for Smith's single-axis tracker. "
                "Near mass-neutral: 9.730 vs 9.764 kg/m2, so the swap removes "
                "the motor, Li-ion cell and control electronics rather than "
                "buying a lighter structure.",
    "end_of_life": "EXCLUDED (Smith A16-A23), as everywhere else in this study.",
    "construction_transport": "EXCLUDED (Smith A14 rail/lorry/sea rows). The "
                              "sea leg alone is 201 t*km/m2 for the import "
                              "chain, so this UNDERSTATES by roughly 1.5 %.",
    "operation_maintenance": "INCLUDED (Smith A15), because the basis being "
                             "replaced is full-scope and dropping O&M would be "
                             "a scope change disguised as a data change. Minus "
                             "the tracker actuator, and minus the transformer "
                             "- transformers.py already charges the step-up.",
    "step_up_transformer": "EXCLUDED here, charged by transformers.py from IEA "
                           "PVPS T12-33:2026 at 20/0.4 kV. Smith's own A11 is "
                           "unusable at 19,796 kg/MVA, ~9x the measured "
                           "specific mass at that rating.",
    "supply_chain": "SE Asia import case - China national grid for the silicon "
                    "chain, Thailand for cell fabrication and module assembly.",
}

# --- operation and maintenance (Smith Table A15, per m2 over 30 years) -------
UPV_PV_OM_REFERENCE_YEARS = 30.0
UPV_PV_OM_PETROL_KG_PER_M2 = 5.50e-2      # vegetation management. TRANSCRIBED.
UPV_PV_OM_PANEL_M2_PER_M2  = 1.50e-2      # 0.05 %/yr panel replacement
# Inverter replacement as a FRACTION of the installed count: Smith charges
# 1.30E-05/m2 in A15 against 4.30E-05/m2 installed in A14, i.e. 30 % over 30
# years (Mason et al.'s 10 % by weight per decade). The fraction transfers to
# our own inverter count where his absolute number would not, because we size
# inverters from the stated ILR rather than his implied one. DERIVED.
UPV_PV_OM_REPLACEMENT_FRACTION = 1.30e-5 / 4.30e-5
UPV_PV_INSTALL_DIESEL_MJ_PER_M2 = 2.6     # Smith A14. TRANSCRIBED.

# --- fixed-tilt mounting (IEA PVPS T12-33:2026, Z-PV-239) -------------------
# Per 1 m2 of module. Materials and their forming steps; transport, disposal
# and land occupation are excluded by scope (land is zero under GWP100 anyway).
UPV_MOUNT_SOURCE = ("IEA PVPS Task 12, Report T12-33:2026, Table 44 / workbook "
                    "sheet X-Montage-utility, dataset Z-PV-239")
UPV_MOUNT_KG_PER_M2 = {
    "steel_low_alloyed":  9.23544043035082,
    "aluminium_wrought":  0.284936216327312,
    "chromium_steel":     0.204341455164734,
    "polypropylene":      0.00533838344407142,
}
UPV_MOUNT_FORMING_PER_M2 = {
    "section_bar_rolling_steel": 9.23544043035082,   # kg
    "sheet_rolling_aluminium":   0.284936216327312,  # kg
    "wire_drawing_steel":        0.204341455164734,  # kg
    "zinc_coating_pieces":       0.514041839135378,  # m2
}
UPV_MOUNT_PACKAGING_KG_PER_M2 = {"corrugated_board": 0.09259259259259259}
# The workbook's own "total weight, structure" cell, which the four material
# rows must reproduce. Packaging is NOT in that total and must be left out of
# the check or it fails by 0.0926 kg.
UPV_MOUNT_STATED_TOTAL_KG_PER_M2 = 9.730056485286937
UPV_MOUNT_PROCESSES = {
    "steel_low_alloyed":  ("market for steel, low-alloyed", "GLO"),
    "aluminium_wrought":  ("market for aluminium, wrought alloy", "GLO"),
    "chromium_steel":     ("market for steel, chromium steel 18/8", "GLO"),
    "polypropylene":      ("market for polypropylene, granulate", "GLO"),
    "corrugated_board":   ("market for corrugated board box", "RER"),
    "section_bar_rolling_steel": ("market for section bar rolling, steel", "GLO"),
    "sheet_rolling_aluminium":   ("market for sheet rolling, aluminium", "GLO"),
    "wire_drawing_steel":        ("market for wire drawing, steel", "GLO"),
    "zinc_coating_pieces":       ("market for zinc coat, pieces", "GLO"),
}

# --- array geometry, which was previously an undocumented function default ---
# tilt/azimuth/loss/tracking were hardcoded in profiles.fetch_solar_cf's
# signature, never threaded through dc_inputs.build_series (so the data centre
# model could not set them), and absent from this file and ASSUMPTIONS.md.
# 20 deg is the tilt of the mounting structure whose embodied carbon is charged
# above, and is GB utility-scale practice; the old 35 deg default was described
# in its own docstring as "a conventional GB utility-scale choice", which it is
# not - it is closer to a domestic roof pitch.
PV_TILT_DEG    = 20.0     # matches UPV_MOUNT_*, IEA PVPS T12-33:2026
PV_AZIMUTH_DEG = 180.0    # due south
PV_SYSTEM_LOSS = 0.10     # Renewables.ninja default. ASSUMED.
PV_TRACKING    = 0        # fixed tilt; the tracker variant is not this study


def upv_pv_check():
    """The mounting bill must rebuild the workbook's own stated structure mass,
    and the derived inverter count must stay in a plausible loading band."""
    mass = sum(UPV_MOUNT_KG_PER_M2.values())
    if abs(mass - UPV_MOUNT_STATED_TOTAL_KG_PER_M2) > 1e-6:
        raise AssertionError(
            f"fixed-tilt mounting sums to {mass:.6f} kg/m2 against IEA PVPS's "
            f"stated {UPV_MOUNT_STATED_TOTAL_KG_PER_M2:.6f}")
    if not (1.05 <= UPV_PV_ILR <= 1.60):
        raise AssertionError(
            f"inverter loading ratio {UPV_PV_ILR} is outside the plausible "
            "band for a utility PV plant - Smith's Table A14 implies 1.75, "
            "which is why his count is not used")
    missing = ((set(UPV_MOUNT_KG_PER_M2) | set(UPV_MOUNT_FORMING_PER_M2)
                | set(UPV_MOUNT_PACKAGING_KG_PER_M2)) - set(UPV_MOUNT_PROCESSES))
    if missing:
        raise AssertionError(f"no ecoinvent process mapped for {sorted(missing)}")
    if abs(UPV_PV_M2_PER_MWP * UPV_PV_W_PER_M2 - 1e6) > 1.0:
        raise AssertionError("m2/MWp does not invert the module power density")
    return (f"OK - {mass:.3f} kg/m2 of fixed-tilt structure, "
            f"{UPV_PV_M2_PER_MWP:,.0f} m2/MWp at {UPV_PV_W_PER_M2:.1f} W/m2, "
            f"{UPV_PV_INVERTERS_PER_MWP:.4f} inverters/MWp at ILR "
            f"{UPV_PV_ILR:g}")


def UPV_TX_SITE_KV_CHECK():
    """The primary side must be the voltage the site actually collects at."""
    if abs(UPV_TX_PRIMARY_KV - TX_SITE_COLLECTION_KV) > 1e-9:
        raise AssertionError(
            f"the IEA PVPS unit is wound {UPV_TX_PRIMARY_KV:g}/"
            f"{UPV_TX_SECONDARY_KV:g} kV but the site collects at "
            f"{TX_SITE_COLLECTION_KV:g} kV - one of them has moved")
    return UPV_TX_PRIMARY_KV



def print_dashboard():
    """Print the settings notebook 2 builds against."""
    print("dc_config")
    print("---------")
    print("Brightway project:      ", PROJECT_NAME, f"(ecoinvent {ECOINVENT_VERSION} {SYSTEM_MODEL})")
    print("Foreground databases:   ", ", ".join([FOREGROUND_DB, DC_FOREGROUND_DB, FC_FOREGROUND_DB,
                                                 H2_STORAGE_FOREGROUND_DB, TRANSFORMER_FOREGROUND_DB,
                                                 SOLAR_FOREGROUND_DB]))
    print("Fuel cell:              ", f"eta {FC_ETA_NET_MEAN:.3f} mean, stack {FC_STACK_LIFETIME_H:,} h,"
          f" system {FC_SYSTEM_LIFETIME_H:,} h")
    print("Hydrogen tank design:   ", TANK_DESIGN)
    print("Grid loss factor:       ", MARKET_LOSS_FACTOR)
