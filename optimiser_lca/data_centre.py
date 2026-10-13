"""
Data centre facility — Zhang et al. 2025, Virginia hyperscale.
=============================================================================

Source and scope
----------------
Materials-production + operation inventory for a representative hyperscale
data centre (10,000 m² white space, Virginia US, SERC grid, PUE 1.4 baseline,
25-year operating life), from Zhang, M., Carbajales-Dale, M., Ma, X., Guo, L.,
Fan, C. (2025). "Cleaner grid or smarter cooling? Environmental impact
trade-offs of a data center using the life cycle assessment method." *Cleaner
Energy Systems* 12, 100223. https://doi.org/10.1016/j.cles.2025.100223 —
quantities are from the paper's Table 1 / supplementary Table S1
(``...-mmc1.xlsx``); the search queries below are seeded from the exact
ecoinvent process names the paper cites in its own OpenLCA contribution
breakdown (``...-mmc2.xlsx``), then re-verified against this project's
ecoinvent 3.9.1 apos database.

Functional unit: **the whole facility over its 25-year operating life**
(1 unit), not a per-kWh or per-m² unit. ``baseline_grid.py`` splits it into a
fixed burden plus 1.60e9 kWh of electricity, and ``dc_inputs`` reads an IT
load out of that draw at the paper's PUE (``dc_config.DC_REFERENCE_PUE``).

**Boundary is deliberately narrowed to Material Production + Operation** —
Transportation, the separate Construction-phase energy/water, Disposal and
Recycling (including the avoided-burden credits) are excluded by scope choice,
not oversight. The full cradle-to-grave version (all 33 flows) is in git
history.

**Validated** (full cradle-to-grave version, before the boundary was narrowed):
every pick was checked against a live search of ecoinvent 3.9.1 apos, and the
LCA on the resulting activity with IPCC 2021 GWP100 gave 8.38×10⁸ kg CO2-eq
against the paper's 9.63×10⁸ (ratio 0.87 — a good match given the different
ecoinvent version/system model and LCIA method to the paper's ecoinvent 3.7
cutoff + TRACI 2.1). Electricity dominates, so the narrower boundary should
land in the same ballpark; ``validate.data_centre_vs_paper()`` reports the
current ratio.

**Three deliberate substitutions**, because ecoinvent 3.9.1 has no exact
equivalent of what the paper's ecoinvent 3.7 cutoff model used:

- ``battery`` → a specific chemistry (NMC111) standing in for the old
  undifferentiated "Li-ion, rechargeable, prismatic" market, which 3.9.1 has
  split by chemistry. Swap for LFP if the facility's real UPS chemistry is
  known — LFP is more typical for modern stationary storage.
- ``refrigerant_r134a`` → the paper's "Tetrafluoroethane" flow is R134a
  (1,1,1,2-tetrafluoroethane); 3.9.1 only has it under the refrigerant name.
- ``servers`` → ecoinvent's only embodied-manufacturing dataset for a generic
  server is ``market for computer, laptop`` — the same proxy the paper used
  (its own quantity is a server count with a refresh-cycle adjustment).

No direct biosphere flows: the source study has none in the foreground — all
impact runs through the technosphere links, matching the paper's finding that
>99 % of impact is electricity-driven.
"""
from __future__ import annotations

from optimiser_lca import registry as R
from optimiser_lca.common import Activity, Inventory, Process

# =============================================================================
# Parameters — all in dc_config (DC_OPERATION_YEARS, DC_REFERENCE_PUE); the
# inventory is a straight transcription with no derived amounts.
# =============================================================================

# =============================================================================
# Processes
# =============================================================================
processes = {
    "concrete": Process(
        query="market for concrete 30-32MPa", pick=0,
        identity=("market for concrete, 30-32MPa", "RNA", "concrete, 30-32MPa"),
        why="the paper's own named process; North American market suits a Virginia build"),
    "reinforcing_steel": Process(
        query="market for reinforcing steel GLO", pick=0,
        identity=("market for reinforcing steel", "GLO", "reinforcing steel")),
    "structural_steel": Process(
        query="market for steel low-alloyed hot rolled GLO", pick=0,
        identity=("market for steel, low-alloyed, hot rolled", "GLO", "steel, low-alloyed, hot rolled")),
    "copper": Process(
        query="market for copper cathode GLO", pick=0,
        identity=("market for copper, cathode", "GLO", "copper, cathode")),
    "aluminium_alloy": Process(
        query="market for aluminium alloy metal matrix composite GLO", pick=0,
        identity=("market for aluminium alloy, metal matrix composite", "GLO",
                  "aluminium alloy, metal matrix composite")),
    "insulation_pur": Process(
        query="market for polyurethane rigid foam RoW", pick=0,
        identity=("market for polyurethane, rigid foam", "RoW", "polyurethane, rigid foam")),
    "electricity_mv_serc": Process(
        query="market for electricity medium voltage US-SERC", pick=0,
        identity=("market for electricity, medium voltage", "US-SERC", "electricity, medium voltage"),
        why="the paper's grid. baseline_grid.py strips this exchange out and puts the "
            "facility on the half-hourly GB series instead"),
    "tap_water": Process(
        query="market group for tap water GLO", pick=0,
        identity=("market group for tap water", "GLO", "tap water")),
    "diesel_generator": Process(
        query="market for diesel burned in diesel-electric generating set 10MW GLO", pick=0,
        identity=("market for diesel, burned in diesel-electric generating set, 10MW", "GLO",
                  "diesel, burned in diesel-electric generating set, 10MW")),
    "servers": Process(
        query="market for computer laptop", pick=6,
        identity=("market for computer, laptop", "GLO", "computer, laptop"),
        why="ecoinvent's only generic embodied-manufacturing dataset for a server; the "
            "same proxy the paper used. The search ranks it at 6, past several "
            "'operation, ...' use-phase variants"),
    "battery": Process(
        query="market for battery Li-ion NMC111 rechargeable prismatic GLO", pick=0,
        identity=("market for battery, Li-ion, NMC111, rechargeable, prismatic", "GLO",
                  "battery, Li-ion, NMC111, rechargeable, prismatic"),
        why="3.9.1 split the old generic Li-ion market by chemistry; NMC111 is a "
            "representative default. LFP is now common for stationary UPS"),
    "sodium_hypochlorite": Process(
        query="market for sodium hypochlorite without water in 15% solution state RoW", pick=0,
        identity=("market for sodium hypochlorite, without water, in 15% solution state", "RoW",
                  "sodium hypochlorite, without water, in 15% solution state")),
    "refrigerant_r134a": Process(
        query="market for refrigerant R134a GLO", pick=1,
        identity=("market for refrigerant R134a", "GLO", "refrigerant R134a"),
        why="the paper's 'tetrafluoroethane' is R134a; 3.9.1 has no bare tetrafluoroethane market"),
}

flows = {}

# =============================================================================
# Activities
# =============================================================================
activities = [
    Activity(
        code=R.DATA_CENTRE,
        name="Data centre facility, hyperscale, Virginia (Zhang et al. 2025)",
        reference_product="data centre facility, materials + operation (25-year)",
        unit="unit", location="US-SERC",
        comment="25-year hyperscale data centre (10,000 m^2 white space), Virginia US, SERC "
                "grid, PUE 1.4 baseline. Zhang et al. 2025, Cleaner Energy Systems 12, 100223, "
                "Table 1 / supplementary Table S1. Boundary narrowed to Material Production + "
                "Operation only (Transportation, Construction energy/water, Disposal and "
                "Recycling excluded by scope choice). Functional unit is the whole facility "
                "over its 25-year operating life, not a per-kWh or per-m^2 unit.",
        technosphere=[
            # --- Material production ---
            ("concrete",          4000,   "cubic meter",   "Concrete, 30-32MPa, building shell and foundation"),
            ("reinforcing_steel",  4.80e5, "kilogram",      "Reinforcing steel"),
            ("structural_steel",   1.20e5, "kilogram",      "Structural steel"),
            ("copper",             2.00e4, "kilogram",      "Copper, cabling and architectural elements"),
            ("aluminium_alloy",    1.50e4, "kilogram",      "Aluminium alloy"),
            ("insulation_pur",     2.50e4, "kilogram",      "Insulation, rigid PUR foam"),
            # --- Operation (25 years, PUE 1.4 baseline) ---
            ("electricity_mv_serc", 1.60e9, "kilowatt hour", "Electricity MV, US-SERC — IT + cooling/aux over 25y (5.76e9 MJ / 3.6)"),
            ("tap_water",            2.9e9, "kilogram",      "Tap water — cooling, WUE 1.8 L/kWh over 25y"),
            ("diesel_generator",    8.60e6, "megajoule",     "Diesel, burned in diesel-electric generating set 10MW — backup gen"),
            ("servers",              1.0e5, "unit",          "Computer/laptop (ecoinvent proxy for IT servers, incl. refresh cycles)"),
            ("battery",              2.0e4, "kilogram",      "Battery, Li-ion, rechargeable, prismatic — UPS"),
            ("sodium_hypochlorite", 1.30e5, "kilogram",      "Sodium hypochlorite — cooling water treatment"),
            ("refrigerant_r134a",       450, "kilogram",     "Tetrafluoroethane / R134a — cooling-system refrigerant top-up"),
        ],
    ),
]


def inventory() -> Inventory:
    return Inventory(name="data centre (Zhang 2025)", database=R.DATA_CENTRE_DB,
                     processes=processes, flows=flows, activities=activities)
