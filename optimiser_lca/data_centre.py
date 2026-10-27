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

**Boundary: Material Production + Construction + Operation.** Transportation
(delivery to site), Disposal and Recycling (including the avoided-burden
credits) are outside the study's boundary (ASSUMPTIONS.md §6). The
Construction-phase energy and water were also left out until 21 Oct 2026 as a
"scope choice"; they are in the source and inside the boundary, so they are
in. The full cradle-to-grave version (all 33 flows) is in git history and was
diffed against this module on 21 Oct (docs/SOURCE_DIFF.md).

**Validated** (full cradle-to-grave version, before the boundary was narrowed):
every pick was checked against a live search of ecoinvent 3.9.1 apos, and the
LCA on the resulting activity with IPCC 2021 GWP100 gave 8.38×10⁸ kg CO2-eq
against the paper's 9.63×10⁸ (ratio 0.87 — a good match given the different
ecoinvent version/system model and LCIA method to the paper's ecoinvent 3.7
cutoff + TRACI 2.1). Electricity dominates, so the narrower boundary should
land in the same ballpark; ``validate.data_centre_vs_paper()`` reports the
current ratio.

**Four deliberate substitutions**, because ecoinvent 3.9.1 has no exact
equivalent of what the paper's ecoinvent 3.7 cutoff model used, or because the
study's grid replaces the paper's:

- ``copper`` → the copper cathode market; Zhang's own dataset (mmc2) is
  ``market for metal part of electronics scrap, in copper, anode``, a scrap
  stream, which does not describe cabling. Order 1e5 kg CO2e over 25 years.
- construction electricity → the GB medium-voltage market, where the paper's
  operating electricity is on US-SERC; ``baseline_grid.py`` strips both out and
  puts the facility on the study's half-hourly GB series.

- ``battery`` → a specific chemistry (NMC111) standing in for the old
  undifferentiated "Li-ion, rechargeable, prismatic" market, which 3.9.1 has
  split by chemistry. Swap for LFP if the facility's real UPS chemistry is
  known — LFP is more typical for modern stationary storage.
- ``refrigerant_r134a`` → the paper's "Tetrafluoroethane" flow is R134a
  (1,1,1,2-tetrafluoroethane); 3.9.1 only has it under the refrigerant name.
- ``servers`` → ecoinvent's only embodied-manufacturing dataset for a generic
  server is ``market for computer, laptop`` — the same proxy the paper used
  (its own quantity is a server count with a refresh-cycle adjustment).

One direct biosphere flow, added 14 Oct 2026: the refrigerant leaked. Zhang's
supplementary Table S1 derives the 450 kg of R134a as "2 000 kg × 0.009 y⁻¹ ×
25 y = 450 kg top-up" — refrigerant bought to replace what leaked at 0.9 %/yr
— and the paper charges only its production (~6.6 kg CO2e/kg). A top-up that
replaces leakage is the leakage, so the same 450 kg is emitted as HFC-134a to
air (GWP100 1,530 in IPCC 2021): 688 t CO2e over the life, ~27.5 t/yr. Their
0.9 %/yr sits below the 1-3 %/yr they cite for best-practice sites, so this
errs low. The 2,000 kg initial charge is not in the inventory and its
end-of-life fate is outside the boundary.
"""
from __future__ import annotations

from optimiser_lca import registry as R
from optimiser_lca.common import Activity, Flow, Inventory, Process

# =============================================================================
# Parameters — DC_OPERATION_YEARS and DC_REFERENCE_PUE are in dc_config. The
# inventory is Zhang's printed amounts; three energy rows are his MJ figures as
# kWh, converted as he converts them (the notes say which).
# =============================================================================
# TRANSCRIBED - Zhang S1, Operation row 1 (cell D26): "10 000 m2 white space: 5.38 MW IT",
# the IT load every IT-driven row (servers, UPS, building, construction diesel) is sized on.
# The printed 1.60e9 kWh is 7.53 MW x 8,760 h x 25 y rounded down (the product is 1.649e9),
# so the IT load read back from it (5.219 MW) is 3 % under the one the inventory was built
# for. The IT-driven burden is normalised by this figure (user, 26 Oct 2026).
ZHANG_IT_MW = 5.38                  # TRANSCRIBED - S1 D26, see above
ZHANG_FACILITY_MW = 7.53            # TRANSCRIBED - same cell, "Facility load PUE 1.4 : 7.53 MW"
DC_SCOPE = {
    "material_production": "INCLUDED - Table S1 Material Production, the six rows at the printed amounts.",
    "construction": "INCLUDED since 21 Oct 2026 - Table S1 Construction (diesel, electricity, water).",
    "operation": "INCLUDED - Table S1 Operation; the electricity is stripped out by baseline_grid.py and "
                 "put on the study's half-hourly GB series.",
    "transport": "EXCLUDED - Table S1 Transportation, delivery of the materials to site (the site is unknown).",
    "end_of_life": "EXCLUDED - Table S1 Disposal and Recycling, with their avoided-burden credits.",
    "genset": "The standby generator's diesel (8.6e6 MJ) is IN this activity and scored, and left out of "
              "every objective by the optimiser (ASSUMPTIONS §7): backup is a decision variable.",
    "refrigerant_leak": "ADDED - the 450 kg top-up Zhang buy is emitted as HFC-134a to air.",
}


def check() -> str:
    """Zhang's own arithmetic reproduces: the top-up, the MJ -> kWh conversions."""
    top_up = 2_000.0 * 0.009 * 25.0
    problems = []
    if abs(top_up - 450.0) > 1e-9:
        problems.append(f"the R134a top-up 2,000 kg x 0.9 %/yr x 25 y = {top_up}, not 450")
    if abs(ZHANG_IT_MW * 1.4 - ZHANG_FACILITY_MW) > 0.01:
        problems.append(f"5.38 MW IT x PUE 1.4 is not Zhang's 7.53 MW facility")
    if abs(5.76e9 / 3.6 - 1.60e9) > 1e-3:
        problems.append("5.76e9 MJ / 3.6 is not 1.60e9 kWh")
    if abs(2.80e5 / 3.6 / 7.8e4 - 1) > 0.005:
        problems.append("2.80e5 MJ / 3.6 is not ~7.8e4 kWh")
    if problems:
        raise AssertionError("data_centre: " + "; ".join(problems))
    return "OK - data centre: Zhang's top-up and energy conversions reproduce"

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
        identity=("market for copper, cathode", "GLO", "copper, cathode"),
        why="SUBSTITUTED - Zhang's own dataset (mmc2) is a copper scrap stream, 'metal part of "
            "electronics scrap, in copper, anode'; the cathode market is the material for cabling"),
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
        identity=("market group for tap water", "GLO", "tap water"),
        why="the GLO market group; Zhang's is 'market for tap water' RoW. Immaterial (~1 t over 25 y)"),
    # Zhang's construction phase, in since 21 Oct 2026 (it is in the source and
    # inside the boundary; only transport to site and end-of-life are out).
    "diesel_construction": Process(
        query="market for diesel burned in building machine GLO", pick=0,
        identity=("market for diesel, burned in building machine", "GLO",
                  "diesel, burned in building machine")),
    "electricity_mv_gb": Process(
        query="market for electricity medium voltage GB", pick=0,
        identity=("market for electricity, medium voltage", "GB", "electricity, medium voltage"),
        why="construction electricity. Like the operating electricity it is stripped by "
            "baseline_grid.py and put on the half-hourly GB series; at 7.8e4 kWh against "
            "1.6e9 it is 0.005 % of the facility's electricity"),
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

flows = {
    "hfc134a_air": Flow(
        query="Ethane, 1,1,1,2-tetrafluoro-, HFC-134a",
        identity=("Ethane, 1,1,1,2-tetrafluoro-, HFC-134a", ("air",)),
        why="the refrigerant top-up replaces refrigerant that leaked"),
}

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
                "Table 1 / supplementary Table S1: Material Production, Construction and Operation "
                "at the printed amounts, plus the refrigerant top-up emitted as a leak (ADDED). "
                "Transportation (delivery to site), Disposal and Recycling (end-of-life, with their "
                "credits) are outside the boundary. Functional unit is the whole facility over its "
                "25-year operating life, not a per-kWh or per-m^2 unit.",
        technosphere=[
            # --- Material production ---
            ("concrete",          4000,   "cubic meter",   "Concrete, 30-32MPa, building shell and foundation"),
            ("reinforcing_steel",  4.80e5, "kilogram",      "Reinforcing steel"),
            ("structural_steel",   1.20e5, "kilogram",      "Structural steel"),
            ("copper",             2.00e4, "kilogram",      "Copper, cabling and architectural elements"),
            ("aluminium_alloy",    1.50e4, "kilogram",      "Aluminium alloy"),
            ("insulation_pur",     2.50e4, "kilogram",      "Insulation, rigid PUR foam"),
            # --- Construction (Zhang S1; in since 21 Oct 2026) ---
            ("diesel_construction", 2.10e6, "megajoule",     "Diesel, burned in building machine — construction"),
            ("electricity_mv_gb",   7.8e4,  "kilowatt hour", "Electricity MV — construction (Zhang's 78,000 kWh, 2.80e5 MJ)"),
            ("tap_water",           1.20e6, "kilogram",      "Tap water — construction"),
            # --- Operation (25 years, PUE 1.4 baseline) ---
            ("electricity_mv_serc", 5.76e9 / 3.6, "kilowatt hour", "Electricity MV, US-SERC — IT + cooling over 25y (5.76e9 MJ as kWh)"),
            ("tap_water",            2.9e9, "kilogram",      "Tap water — cooling, WUE 1.8 L/kWh over 25y (Zhang's rounded 2.9e9)"),
            ("diesel_generator",    8.60e6, "megajoule",     "Diesel, burned in diesel-electric generating set 10MW — backup gen"),
            ("servers",              1.0e5, "unit",          "Computer/laptop (ecoinvent proxy for IT servers, incl. refresh cycles)"),
            ("battery",              2.0e4, "kilogram",      "Battery, Li-ion, rechargeable, prismatic — UPS"),
            ("sodium_hypochlorite", 1.30e5, "kilogram",      "Sodium hypochlorite — cooling water treatment"),
            ("refrigerant_r134a",       450, "kilogram",     "Tetrafluoroethane / R134a — cooling-system refrigerant top-up"),
        ],
        biosphere=[
            ("hfc134a_air", 450, "kilogram",
             "ADDED — R134a leaked: the 450 kg top-up replaces leakage at 0.9 %/yr (Zhang Table S1: "
             "2,000 kg x 0.009 x 25 y)"),
        ],
    ),
]


def inventory() -> Inventory:
    return Inventory(name="data centre (Zhang 2025)", database=R.DATA_CENTRE_DB,
                     processes=processes, flows=flows, activities=activities)
