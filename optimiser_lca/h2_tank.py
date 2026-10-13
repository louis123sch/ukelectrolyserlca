"""
Hydrogen storage tank — Gandiglio et al. 2022, a mass of steel.
=============================================================================

Source and scope
----------------
ecoinvent 3.9.1 has no hydrogen storage vessel of any kind (the search returns
compressed-air plants and LNG tankers), so the tank is assembled, following:

    M. Gandiglio, P. Marocco, I. Bianco, D. Lovera, G.A. Blengini, M. Santarelli,
    "Life cycle assessment of a renewable energy system with hydrogen-battery
    storage for a remote off-grid community", Int. J. Hydrogen Energy 47 (2022).

That paper is an LCA of the architecture this repo builds — PV + battery +
alkaline electrolyser + hydrogen tank + PEM fuel cell, dispatched hourly over
a year, at Ginostra on Stromboli. **Their hydrogen tank is one inventory
line: 15,652 kg of ``Steel, chromium steel 18/8 {GLO}`` for a 21.6 m³, 28 bar
vessel, 25 years, never replaced.** Nothing else — no forming, no valves, no
foundations, no end-of-life.

Functional unit here is **1 kg of hydrogen storage capacity**; the paper
divides the steel by the plant's 25-year output instead (15,652 kg ÷ 25 y ×
171.5 MWh/y = 3.65e-3 kg/kWh, their Table 3). Keeping it per kg of capacity
lets ``optimisation/h2_storage.py`` amortise it over
``dc_config.TANK_LIFETIME_YEARS`` and survive a change of tank size.

**Converting their vessel into kg of steel per kg of H₂.** 21.6 m³ at 28 bar
and 15 °C, with compressibility 1.017, holds 50.0 kg of hydrogen, so the
paper's tank is 313 kg of stainless per kg of H₂ stored — computed in
``steel_kg_per_kg_h2()`` rather than hard-coded.

**Why that is three times heavier than a gas bottle.** 28 bar is a
low-pressure buffer; at low pressure the steel is set by volume, not hoop
stress. A Type I seamless cylinder at 200 bar reaches ~1 wt%, i.e.
~100 kg/kg. Both designs are in ``TANK_DESIGNS``; ``TANK_DESIGN`` picks which
is built. The paper's design is the conservative choice with a real published
inventory behind it, so it is the default — but it is a 50 kg store for a
village of 30 houses, and a data-centre-scale store would almost certainly
run at higher pressure. Switching to ``type1_200bar`` makes the tank ~3×
lighter and switches on 2.5 kWh/kg of compression electricity (charged in
the dispatch, not here).

**Still missing**, following the paper: forming, valves and pipework,
foundations, compressor hardware, end-of-life, hydrogen leakage. All push the
same way, so the tank is a floor with a published inventory behind it.
"""
from __future__ import annotations

from optimiser_lca import registry as R
from optimiser_lca.common import Activity, Inventory, Process

# =============================================================================
# Parameters
# =============================================================================
TANK_DESIGNS = {
    # The real vessel in the paper. Low-pressure buffer, so heavy per kg stored.
    "gandiglio_28bar": {
        "steel_process": "steel_chromium_188",
        "steel_kg": 15_652.0, "volume_m3": 21.6, "pressure_bar": 28.0,
        "note": "Gandiglio et al. 2022, Table 3 - as-built 21.6 m3 stainless vessel at Ginostra",
    },
    # Type I all-steel cylinder at 200 bar, sized from ~1 wt% gravimetric
    # capacity. Roughly 3x lighter per kg H2 than the 28 bar design above.
    "type1_200bar": {
        "steel_process": "steel_low_alloyed_hr",
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
R_GAS_J_PER_MOL_K = 8.314
M_H2_KG_PER_MOL   = 0.002016

# Electrolyser delivers at ~30 bar. Charged as electricity in the dispatch, not
# as tank capital. Zero for the 28 bar design, which needs no extra compression.
TANK_COMPRESSION_KWH_PER_KG = 0.0 if TANK_DESIGNS[TANK_DESIGN]["pressure_bar"] <= 30 else 2.5


def capacity_kg(design: dict) -> float | None:
    """kg of H2 a design holds, from its own volume and pressure (real gas)."""
    if "steel_kg_per_kg_h2" in design:
        return None
    rho = (design["pressure_bar"] * 1e5 * M_H2_KG_PER_MOL) / (
        TANK_H2_COMPRESSIBILITY * R_GAS_J_PER_MOL_K * TANK_H2_TEMPERATURE_K)   # kg/m3
    return rho * design["volume_m3"]


def steel_kg_per_kg_h2(design: dict) -> float:
    if "steel_kg_per_kg_h2" in design:
        return float(design["steel_kg_per_kg_h2"])
    return design["steel_kg"] / capacity_kg(design)


DESIGN = TANK_DESIGNS[TANK_DESIGN]
TANK_STEEL_KG_PER_KG_H2 = steel_kg_per_kg_h2(DESIGN)

# =============================================================================
# Processes
# =============================================================================
processes = {
    "steel_chromium_188": Process(
        identity=("market for steel, chromium steel 18/8", "GLO"),
        query="market for steel chromium steel 18/8 GLO",
        why="the paper's own line: 'Steel, chromium steel 18/8 {GLO}'"),
    "steel_low_alloyed_hr": Process(
        identity=("market for steel, low-alloyed, hot rolled", "GLO"),
        query="market for steel low-alloyed hot rolled GLO",
        why="a Type I cylinder is carbon/low-alloy steel, not stainless"),
}
flows = {}

# =============================================================================
# Activities — one line, as in the source
# =============================================================================
activities = [
    Activity(
        code=R.H2_TANK,
        name=f"Hydrogen storage tank, steel vessel, per kg capacity ({TANK_DESIGN})",
        reference_product="hydrogen storage capacity",
        unit="kilogram", location="GLO",
        comment="Hydrogen storage vessel modelled as a mass of steel and nothing else, following "
                "Gandiglio et al. 2022 (Int. J. Hydrogen Energy 47), whose LCA of a PV + battery "
                "+ electrolyser + tank + fuel cell off-grid system inventories its 21.6 m3 / 28 bar "
                "vessel as a single line of 15,652 kg chromium steel 18/8. ecoinvent 3.9.1 has no "
                f"hydrogen storage dataset. Design {TANK_DESIGN!r}: "
                f"{TANK_STEEL_KG_PER_KG_H2:.1f} kg steel per kg H2 at "
                f"{DESIGN['pressure_bar']:g} bar. Functional unit is 1 kg of "
                "storage CAPACITY - amortise over TANK_LIFETIME_YEARS (dc_config). "
                "Excludes forming, valves, foundations, compressor hardware, end-of-life and "
                "hydrogen leakage, as the source does.",
        technosphere=[
            (DESIGN["steel_process"], TANK_STEEL_KG_PER_KG_H2, "kilogram",
             f"Vessel steel — {TANK_DESIGN}, {DESIGN['pressure_bar']:g} bar"),
        ],
    ),
]


def inventory() -> Inventory:
    return Inventory(name="hydrogen tank (Gandiglio 2022)", database=R.H2_STORAGE_DB,
                     processes=processes, flows=flows, activities=activities)


def describe() -> str:
    lines = [f"Tank design: {TANK_DESIGN!r}\n  {DESIGN['note']}"]
    if "steel_kg_per_kg_h2" in DESIGN:
        lines.append(f"  {TANK_STEEL_KG_PER_KG_H2:.1f} kg steel per kg H2 (given directly)")
    else:
        h2 = capacity_kg(DESIGN)
        lines.append(f"  {DESIGN['volume_m3']:g} m3 at {DESIGN['pressure_bar']:g} bar, "
                     f"{TANK_H2_TEMPERATURE_K:.2f} K, Z={TANK_H2_COMPRESSIBILITY}")
        lines.append(f"  -> {h2 / DESIGN['volume_m3']:.4f} kg/m3 -> {h2:.2f} kg H2 in the vessel")
        lines.append(f"  -> {DESIGN['steel_kg']:,.0f} kg steel / {h2:.2f} kg H2 = "
                     f"{TANK_STEEL_KG_PER_KG_H2:.1f} kg steel per kg H2")
    lines.append(f"  compression {TANK_COMPRESSION_KWH_PER_KG} kWh/kg, charged in the dispatch")
    return "\n".join(lines)
