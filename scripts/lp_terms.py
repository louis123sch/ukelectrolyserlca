"""Display names for the LP's carbon terms, and the names the energy-flow tab links to.

The terms themselves are read from ``dc_model.objective_terms`` and
``facility_terms`` by ``build_lca_map.py``; this only names their boxes. A
term with no entry here is shown by its key. Shared with energy_map.py so a
rename cannot leave the energy tab pointing at a box that no longer exists.
"""

T_WIND = "Onshore wind"
T_SOLAR = "Solar PV (utility, fixed tilt 20°)"
T_TX_WIND = "Wind step-up transformers (0.69 → 20 kV, one per turbine)"
T_TX_SOLAR = "Solar step-up transformers (0.4 → 20 kV, at the inverter station)"
T_TX_BATT = "Battery step-up transformers (0.4 → 20 kV, one per container)"
T_TX_FC = "Fuel-cell step-up transformers (0.4 → 20 kV, one per container)"
T_GRID_CONN = "Grid connection (intake transformers, N-1)"
T_BATT_E = "Battery cells, racks and container (energy capacity)"
T_BATT_P = "Battery power conversion system (power capacity)"
T_ELY = "Electrolyser balance of plant (PEM default; AE, SOEC selectable)"
T_ELY_STACK = "Electrolyser stack replacements (max(calendar, duty))"
T_TANK = "Hydrogen tank (Gandiglio 28 bar vessel)"
T_FC_STACK = "Fuel cell stack replacements (max(calendar, duty))"
T_FC_BOP = "Fuel cell balance-of-plant replacements (max(calendar, duty))"
T_IMPORT = "Grid imports (half-hourly, regional)"
T_ELY_CONS = "Electrolyser consumables (water, heat)"
T_FC_MAINT = "Fuel cell service"
T_LEAK = "Hydrogen leaked from the tank"
T_VOLL = "Unserved load (penalty, not an emission)"
T_BOUGHT = "Bought hydrogen — one term per stream, keyed 'bought H2 (<colour>)'; one or two streams"      # a group of the four colour boxes, not a term of its own
T_DC_IT = "Data centre, IT capacity"
T_DC_ENERGY = "Data centre, cooling consumables"

# objective_terms key -> box name (the bought-hydrogen streams are keyed
# "bought H2 (<colour>)" and named by colour in the generator).
KEY_TO_NAME = {
    "wind": T_WIND, "solar": T_SOLAR,
    "wind step-up transformers": T_TX_WIND, "solar step-up transformers": T_TX_SOLAR,
    "battery step-up transformers": T_TX_BATT, "fuel cell step-up transformers": T_TX_FC,
    "grid connection": T_GRID_CONN,
    "battery cells and container": T_BATT_E, "battery power conversion": T_BATT_P,
    "electrolyser": T_ELY, "electrolyser stack replacements": T_ELY_STACK, "H2 tank": T_TANK,
    "fuel cell stack replacements": T_FC_STACK, "fuel cell BoP replacements": T_FC_BOP,
    "grid import": T_IMPORT, "electrolyser consumables": T_ELY_CONS,
    "fuel cell maintenance": T_FC_MAINT, "H2 leaked from tank": T_LEAK, "unserved (VoLL)": T_VOLL,
}
CONSTANTS = {"data centre, IT capacity": T_DC_IT, "data centre, cooling consumables": T_DC_ENERGY}
