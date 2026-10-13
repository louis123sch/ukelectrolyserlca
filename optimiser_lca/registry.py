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
HYDROGEN_DB     = "hydrogen foreground"          # Hermesmann hydrogen routes
DATA_CENTRE_DB  = "data centre foreground"       # Zhang et al. 2025 facility
FUEL_CELL_DB    = "fuel cell foreground"         # Babatunde et al. 2024 stack + operation
H2_STORAGE_DB   = "hydrogen storage foreground"  # Gandiglio et al. 2022 vessel
TRANSFORMER_DB  = "transformer foreground"       # Leng 2026 wind + IEA PVPS 2026 solar step-ups
SOLAR_DB        = "solar foreground"             # Smith et al. 2024 utility PV, on apos

# Build order. Later databases link into earlier ones (the fuel cell burns
# hydrogen from HYDROGEN_DB), so this is a dependency order, not a preference.
DATABASES = [HYDROGEN_DB, DATA_CENTRE_DB, FUEL_CELL_DB, H2_STORAGE_DB,
             TRANSFORMER_DB, SOLAR_DB]

# --- hydrogen (Hermesmann) -----------------------------------------------------
SMR        = "smr_hermesmann_1kg_h2"
SMR_CCS    = "smr_ccs_hermesmann_1kg_h2"
CCS        = "ccs_hermesmann_1kg_co2"           # waste treatment of 1 kg captured CO2
MP_E       = "mp_e_1kg_h2"
AE_UNIT    = "ae_hermesmann_1unit"              # capital good, 1 MW
AE_OP      = "ae_op_hermesmann_1kg_h2"
PEM_UNIT   = "pem_con_hermesmann_1unit"
PEM_OP     = "pem_op_hermesmann_1kg_h2"
SOEC_UNIT  = "soec_con_hermesmann_1unit"
SOEC_OP    = "soec_op_hermesmann_1kg_h2"

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

# --- data centre ---------------------------------------------------------------
DATA_CENTRE = "dc_zhang_virginia_baseline_25y"

# --- fuel cell -----------------------------------------------------------------
FC_STACK = "pemfc_stack_1kw_babatunde"          # 1 kW stack, manufactured
FC_OP    = "pemfc_op_1kwh_h2"                   # 1 kWh net AC from hydrogen

# --- hydrogen storage ----------------------------------------------------------
H2_TANK = "h2_tank_steel_1kg_capacity"          # per kg of storage capacity

# --- step-up transformers ------------------------------------------------------
TX_WIND  = "wind_turbine_stepup_per_mw"         # per MW of wind connected
TX_SOLAR = "solar_inverter_stepup_per_mwp"      # per MWp of PV connected

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

# --- what each database must contain, for the build and the tests ---------------
CODES_BY_DATABASE = {
    HYDROGEN_DB:    [SMR, SMR_CCS, CCS, MP_E, AE_UNIT, AE_OP, PEM_UNIT, PEM_OP,
                     SOEC_UNIT, SOEC_OP],
    DATA_CENTRE_DB: [DATA_CENTRE],
    FUEL_CELL_DB:   [FC_STACK, FC_OP],
    H2_STORAGE_DB:  [H2_TANK],
    TRANSFORMER_DB: [TX_WIND, TX_SOLAR],
    SOLAR_DB:       list(UPV_TABLES.values()) + [UPV_MOUNT, UPV_CAPITAL, UPV_OM30],
}
