"""
Every foreground database name and activity code, in one place.
=============================================================================

The ``optimisation/`` modules fetch foreground activities by ``(database,
code)``. Those pairs used to be string literals in seven modules and in the
notebook; they are declared here once and imported everywhere else, so a
rename happens in one line and a typo fails at import rather than at
``bd.get_activity``.

Nothing here needs Brightway.
"""
from __future__ import annotations

# --- databases ----------------------------------------------------------------
# One database per source, so rebuilding one never touches another.
HYDROGEN_DB     = "hydrogen foreground"          # Hermesmann fossil routes, Gerloff electrolysers
DATA_CENTRE_DB  = "data centre foreground"       # Zhang et al. 2025 facility
FUEL_CELL_DB    = "fuel cell foreground"         # Babatunde 2024 stack, Usai 2021 BoP, operation
H2_STORAGE_DB   = "hydrogen storage foreground"  # Gandiglio et al. 2022 vessel
TRANSFORMER_DB  = "transformer foreground"       # Leng 2026 wind + grid intake, IEA PVPS 2026 solar
SOLAR_DB        = "solar foreground"             # Smith et al. 2024 utility PV, on apos
BESS_DB         = "battery foreground"           # Jasper 2026 container, Voß 2025 cell
GRID_DB         = "grid foreground"              # the study's own GB grid, one kWh

# Build order. Later databases link into earlier ones (the fuel cell burns
# hydrogen from HYDROGEN_DB, and sits in BESS_DB's container; the fossil
# hydrogen routes take GRID_DB's electricity, whose solar share is SOLAR_DB's
# plant), so this is a dependency order, not a preference.
DATABASES = [SOLAR_DB, GRID_DB, HYDROGEN_DB, DATA_CENTRE_DB, BESS_DB, FUEL_CELL_DB,
             H2_STORAGE_DB, TRANSFORMER_DB]

# --- hydrogen: Hermesmann & Müller 2022 (fossil routes), Gerloff 2021 (electrolysers) ---
SMR        = "smr_hermesmann_1kg_h2"
SMR_CCS    = "smr_ccs_hermesmann_1kg_h2"
CCS        = "ccs_hermesmann_1kg_co2"           # waste treatment of 1 kg captured CO2
MP_E       = "mp_e_1kg_h2"
# Gerloff's bills; the codes said "hermesmann" until 22 Oct 2026 (a misattribution).
AE_UNIT    = "ae_gerloff_1unit"                 # capital good, 1 MW over 20 years, three stacks
AE_OP      = "ae_op_gerloff_1kg_h2"
PEM_UNIT   = "pem_gerloff_1unit"
PEM_OP     = "pem_op_gerloff_1kg_h2"
SOEC_UNIT  = "soec_gerloff_1unit"
SOEC_OP    = "soec_op_gerloff_1kg_h2"

# Hydrogen-producing activities by the label the optimiser uses.
H2_CODES = {
    "SMR":            SMR,
    "SMR-CCS":        SMR_CCS,
    "AE operation":   AE_OP,
    "PEM operation":  PEM_OP,
    "SOEC operation": SOEC_OP,
    "MP-E":           MP_E,
}
ELECTROLYSER_CODES = {
    "AE operation":   AE_OP,
    "PEM operation":  PEM_OP,
    "SOEC operation": SOEC_OP,
}

# --- GB grid ---------------------------------------------------------------------
GB_GRID_HV_2025 = "gb_grid_2025_hv_delivered"     # 1 kWh, 2025 mean, at high voltage

# --- data centre ---------------------------------------------------------------
DATA_CENTRE = "dc_zhang_virginia_baseline_25y"

# --- fuel cell -----------------------------------------------------------------
FC_STACK   = "pemfc_stack_1kw_babatunde"        # 1 kW stack, manufactured
FC_STACK_GRAMC = "pemfc_stack_1kw_gramc"        # 1 kW of Gramc 2025's 48 kW stack (sensitivity)
FC_BOP     = "pemfc_bop_stationary_1kw"         # 1 kW of stationary H2 balance of plant
FC_SERVICE = "pemfc_service_stationary_1kw"     # one service of 1 kW
FC_OP      = "pemfc_op_1kwh_h2"                 # 1 kWh net AC from hydrogen

# --- hydrogen storage ----------------------------------------------------------
H2_TANK = "h2_tank_steel_1kg_capacity"          # per kg of storage capacity

# --- step-up transformers ------------------------------------------------------
TX_WIND  = "wind_turbine_stepup_per_mw"         # per MW of wind connected
TX_SOLAR = "solar_inverter_stepup_per_mwp"      # per MWp of PV connected
TX_GRID  = "grid_intake_transformer_per_mva"    # per MVA of grid-intake capacity
TX_LV_CONTAINER = "containerised_lv_stepup_per_mw"   # per MW of inverter rating: battery PCS, fuel cell
TX_SOLAR_REPL30 = "solar_inverter_stepup_replacements_30y_per_mwp"   # Smith A15's 30 % over 30 y
TX_GRID_CIVILS = "grid_intake_substation_civils_per_mw"   # per MW of connection: Leng S3's outdoor venue (D2)

# --- utility-scale PV ------------------------------------------------------------
UPV_TABLES = {                                   # Smith Appendix A table -> code
    "A1": "upv_silica_sand", "A2": "upv_silicon_metal",
    "A3": "upv_polysilicon", "A4": "upv_cz_ingot", "A5": "upv_wafer",
    "A6": "upv_trimethylaluminum", "A7": "upv_perc_cell",
    "A8": "upv_perc_module", "A10": "upv_inverter_2700kva",
    "A12": "upv_electrical_bos", "A13": "upv_fence",
}
UPV_MODULE   = UPV_TABLES["A8"]
UPV_INVERTER = UPV_TABLES["A10"]
UPV_MOUNT    = "upv_fixed_tilt_mounting"         # per m2 of module
UPV_CAPITAL  = "upv_fixed_tilt_plant_per_mwp"    # per MWp DC, capital only
UPV_OM30     = "upv_fixed_tilt_om30_per_mwp"     # per MWp DC, 30 years of O&M
UPV_GRID_KWH = "upv_gb_grid_fleet_1kwh"          # per kWh, the grid's solar share

# --- grid battery ------------------------------------------------------------------
BESS_DC_BLOCK_KWH = "bess_dc_block_per_kwh"      # per kWh nameplate, what battery.py scores
BESS_CELL_CN = "bess_lfp_cell_1kwh_cn"           # Voß cell per kWh, factory in China
BESS_CELL_DE = "bess_lfp_cell_1kwh_de"           # Voß cell per kWh, Voß's own German factory
BESS_PARTS = {                                    # the sub-assemblies, by role
    "sgr": "bess_synthetic_graphite_1kg", "ngr": "bess_natural_graphite_1kg",
    "fepo4": "bess_iron_phosphate_0p91kg", "lfp": "bess_lfp_cam_1kg",
    "sbr": "bess_sbr_1kg", "pvdf": "bess_pvdf_1kg", "separator": "bess_separator_1kg",
    "housing": "bess_cell_housing_1kg", "cell": "bess_lfp_cell_materials_1unit",
    "module": "bess_module_47kwh_liquid", "rack_housing": "bess_rack_housing_1kg",
    "rack": "bess_rack_liquid_1unit", "plate": "bess_cooling_plate_1unit",
    "compressor": "bess_compressor_1kg", "drier": "bess_filter_drier_1kg",
    "pump": "bess_pump_1kg", "coolant": "bess_secondary_coolant_1kg",
    "ac_indoor": "bess_ac_indoor_unit_1kg", "ac_outdoor": "bess_ac_outdoor_unit_1kg",
    "ac": "bess_air_conditioner_1kg", "lcu": "bess_liquid_cooling_unit_1unit",
    "cooling": "bess_liquid_cooling_system_1unit", "damper": "bess_fire_damper_1unit",
    "container": "bess_container_20ft_1unit", "hfc": "bess_hfc227ea_1kg",
    "tank": "bess_extinguisher_tank_1kg", "panel": "bess_suppression_panel_1kg",
    "fire": "bess_fire_suppression_1unit", "css": "bess_dc_block_liquid_1unit",
}

# --- what each database must contain, for the build and the tests ---------------
CODES_BY_DATABASE = {
    SOLAR_DB:       list(UPV_TABLES.values()) + [UPV_MOUNT, UPV_CAPITAL, UPV_OM30,
                                                 UPV_GRID_KWH],
    GRID_DB:        [GB_GRID_HV_2025],
    HYDROGEN_DB:    [SMR, SMR_CCS, CCS, MP_E, AE_UNIT, AE_OP, PEM_UNIT, PEM_OP,
                     SOEC_UNIT, SOEC_OP],
    DATA_CENTRE_DB: [DATA_CENTRE],
    BESS_DB:        list(BESS_PARTS.values()) + [BESS_CELL_CN, BESS_CELL_DE,
                                                 BESS_DC_BLOCK_KWH],
    FUEL_CELL_DB:   [FC_STACK, FC_STACK_GRAMC, FC_BOP, FC_SERVICE, FC_OP],
    H2_STORAGE_DB:  [H2_TANK],
    TRANSFORMER_DB: [TX_WIND, TX_SOLAR, TX_GRID, TX_LV_CONTAINER, TX_SOLAR_REPL30, TX_GRID_CIVILS],
}
