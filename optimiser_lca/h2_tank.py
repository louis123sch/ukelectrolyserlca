"""
Hydrogen storage tank — Gandiglio et al. 2022, a steel vessel.
=============================================================================

Source and scope
----------------
    M. Gandiglio, P. Marocco, I. Bianco, D. Lovera, G.A. Blengini, M. Santarelli,
    "Life cycle assessment of a renewable energy system with hydrogen-battery
    storage for a remote off-grid community", Int. J. Hydrogen Energy 47 (2022)
    32822-32834. Table 5 (p. 32828): the hydrogen tank is one line, 15,652 kg of
    "Steel, chromium steel 18/8 {GLO}" for a 21.6 m³ vessel at 28 bar, over the
    plant's 25-year life, charged once.

ecoinvent 3.9.1 has no hydrogen storage vessel of any kind, so the tank is
built from that line. **Functional unit: 1 kg of hydrogen storage capacity.**
The paper's 21.6 m³ at 28 bar and 15 °C holds 50.0 kg of hydrogen
(``capacity_kg()``, real gas), so its vessel is 313 kg of stainless steel per
kg stored; ``optimisation/h2_storage.py`` amortises that over
``dc_config.TANK_LIFETIME_YEARS``.

**Boundary.** In: the shell, its plate-making or forming step (ADDED, 22 Oct
2026, CUTOFF_RULE_PLAN.md step 5; for the default carbon-steel vessel since
11 Nov 2026 the mill's hot rolling on unalloyed steel, for Gandiglio's stainless
vessel sheet rolling of chromium steel), and the frame and foundation pad
(ASSUMED from the design's own vessel geometry, 14 Oct 2026: a 0.5 m slab with
0.5 m clearance, rebar at 100 kg/m³, saddles and frame at 10 % of the shell, in
hot-rolled unalloyed steel). Bending and welding the plate are on the cut-off
register. Out: end-of-life, delivery to site, and the hydrogen itself (leakage is
the LP's ``H2 leaked from tank`` term). Valves, pipework and compressor hardware
are unsourced and sit on the cut-off register (``optimiser_lca/exclusions.py``).

**Three designs.** ``bulk_carbon_steel_28bar`` (the default since 4 Nov 2026) is
a bulk carbon-steel vessel at 28 bar sized by the thin-wall formula, about 161 kg
of steel per kg of hydrogen, the class of vessel the cost side prices.
``gandiglio_28bar`` is the paper's small stainless buffer, 313 kg per kg: heavy
because a 21.6 m³ vessel is set by its minimum plate, not hoop stress; it was the
default until 4 Nov 2026 and stays in the table, no longer tested (since 11 Nov
2026 the test is the tank's carbon at x0.5 / x1.5). A Type I seamless cylinder
at 200 bar reaches ~1 wt%, and needs 2.5 kWh/kg of compression (charged in the
dispatch, not here). ``TANK_DESIGN`` picks which is built.
"""
from __future__ import annotations

import math

from optimiser_lca import registry as R
from optimiser_lca.common import Activity, Inventory, Process

# =============================================================================
# Parameters
# =============================================================================
TANK_DESIGNS = {
    # The default since 4 Nov 2026 (evening): a bulk carbon-steel pressure vessel
    # at the study's 28 bar, DERIVED by the standard thin-wall cylinder formula
    # (SA-516 Gr 70 plate, 138 MPa allowable, design pressure 110 % of working,
    # 3 mm corrosion allowance, hemispherical heads, 7,850 kg/m3): 161-167 kg of
    # steel per kg of hydrogen for vessels of 95-500 m3, and the same at 50 and
    # 80 bar, because hoop stress and gas density both scale with pressure. The
    # cost side prices Element Energy's 95 m3 vessel of this class, so cost and
    # carbon now describe one vessel. Replaces Gandiglio's small stainless buffer
    # as the default under the cut-off rule's substitution clause (a stated
    # physical check: 313 kg of stainless per kg is a 21.6 m3 vessel, not a bulk
    # store); Gandiglio's stays as the sensitivity. docs/COST_BEST_SOURCE_PLAN.md.
    # Steel since 11 Nov 2026: SA-516 is plain carbon (carbon-manganese) steel, so
    # ecoinvent's "steel, unalloyed" plus one mill rolling step ("hot rolling,
    # steel") to make the plate. Until then "steel, low-alloyed, hot rolled" (which
    # already includes the mill rolling) plus "sheet rolling, steel" on top, the
    # mill step for thin cold-rolled sheet: rolling counted twice, about 17 % of
    # the tank. Bending and welding the plate stay on the cut-off register.
    "bulk_carbon_steel_28bar": {
        "steel_process": "steel_unalloyed", "forming_process": "hot_rolling_steel",
        "steel_kg_per_kg_h2": 161.2, "pressure_bar": 28.0, "volume_m3": 200.0,
        "note": "DERIVED - bulk carbon-steel vessel at 28 bar, thin-wall formula on a 200 m3 shell; "
                "the cost side's vessel class",
    },
    # TRANSCRIBED - Gandiglio et al. 2022 Table 5, the vessel at Ginostra.
    "gandiglio_28bar": {
        "steel_process": "steel_chromium_188", "forming_process": "sheet_rolling_cr_steel",
        "steel_kg": 15_652.0, "volume_m3": 21.6, "pressure_bar": 28.0,
        "note": "Gandiglio et al. 2022, Table 5 - 21.6 m3 stainless vessel at 28 bar (the sensitivity since "
                "4 Nov 2026)",
    },
    # ASSUMED - a Type I all-steel cylinder at ~1 wt% gravimetric capacity.
    "type1_200bar": {
        "steel_process": "steel_low_alloyed_hr", "forming_process": "sheet_rolling_steel",
        "steel_kg_per_kg_h2": 100.0, "pressure_bar": 200.0,
        "note": "Type I seamless cylinder, ~1 wt% H2 - typical industrial stationary bottle",
    },
}
TANK_DESIGN = "bulk_carbon_steel_28bar"
if TANK_DESIGN not in TANK_DESIGNS:
    raise ValueError(f"TANK_DESIGN must be one of {list(TANK_DESIGNS)}")

# Gas conditions for the paper's vessel. 15 C and Z for H2 at ~28 bar (physical constants).
TANK_H2_TEMPERATURE_K   = 288.15    # 15 C, a physical constant of the conversion
TANK_H2_COMPRESSIBILITY = 1.017     # Z for H2 at ~28 bar, physical constant
R_GAS_J_PER_MOL_K = 8.314           # physical constant
M_H2_KG_PER_MOL   = 0.002016        # physical constant

# Frame and foundations - ASSUMED, sized from the paper's vessel (see the docstring).
VESSEL_L_OVER_D = 3.5
PAD_CLEARANCE_M = 0.5
PAD_THICKNESS_M = 0.5
REBAR_KG_PER_M3_CONCRETE = 100.0    # ASSUMED
FRAME_STEEL_FRACTION_OF_SHELL = 0.10   # ASSUMED
_REF = TANK_DESIGNS["gandiglio_28bar"]

TANK_SCOPE = {
    "shell": "INCLUDED - Gandiglio Table 5's one line, 15,652 kg chromium steel 18/8.",
    "forming": "INCLUDED since 22 Oct 2026 (ADDED) - sheet rolling of the shell steel; the paper counts the "
               "steel only. Average metal working is the upper sensitivity (exclusions register).",
    "frame_and_pad": "INCLUDED since 14 Oct 2026 (ASSUMED) - saddles and frame at 10 % of the shell, a "
                     "0.5 m reinforced slab from the vessel's footprint.",
    "valves_pipework_compressor": "EXCLUDED - unsourced; on the cut-off register (exclusions.py), tested "
                                  "against 1 % of the tank's carbon.",
    "end_of_life": "EXCLUDED, as everywhere else in this study.",
}


def h2_kg_per_m3(design: dict) -> float:
    """Stored hydrogen density at the design's pressure, real gas at 15 C."""
    return (design["pressure_bar"] * 1e5 * M_H2_KG_PER_MOL) / (
        TANK_H2_COMPRESSIBILITY * R_GAS_J_PER_MOL_K * TANK_H2_TEMPERATURE_K)


def capacity_kg(design: dict) -> float | None:
    """kg of H2 a design holds, from its own volume and pressure; None for a per-kg
    design that states no vessel volume."""
    if "volume_m3" not in design:
        return None
    return h2_kg_per_m3(design) * design["volume_m3"]


def steel_kg_per_kg_h2(design: dict) -> float:
    if "steel_kg_per_kg_h2" in design:
        return float(design["steel_kg_per_kg_h2"])
    return design["steel_kg"] / capacity_kg(design)


def pad_m3_per_m3_vessel(design: dict | None = None) -> float:
    """Concrete per m3 of vessel volume, from the vessel's own geometry where the
    design states a volume (a pad scales with footprint, so a bulk vessel needs
    less per m3), else the reference vessel's."""
    v = (design or {}).get("volume_m3", _REF["volume_m3"])
    d = (4.0 * v / (math.pi * VESSEL_L_OVER_D)) ** (1.0 / 3.0)
    length = VESSEL_L_OVER_D * d
    area = (length + 2 * PAD_CLEARANCE_M) * (d + 2 * PAD_CLEARANCE_M)
    return area * PAD_THICKNESS_M / v


def foundations_per_kg_h2(design: dict) -> dict:
    """Concrete (m3), rebar (kg) and frame steel (kg) per kg of H2 capacity."""
    concrete = pad_m3_per_m3_vessel(design) / h2_kg_per_m3(design)
    return {"concrete_m3": concrete,
            "rebar_kg": concrete * REBAR_KG_PER_M3_CONCRETE,
            "frame_kg": FRAME_STEEL_FRACTION_OF_SHELL * steel_kg_per_kg_h2(design)}


DESIGN = TANK_DESIGNS[TANK_DESIGN]
TANK_STEEL_KG_PER_KG_H2 = steel_kg_per_kg_h2(DESIGN)
TANK_FOUNDATIONS = foundations_per_kg_h2(DESIGN)


def check() -> str:
    """The paper's vessel reproduces: 50 kg of H2, 313 kg of steel per kg, and its own
    3.65e-3 kg of steel per kWh over 25 years of 171.5 MWh."""
    ref = TANK_DESIGNS["gandiglio_28bar"]
    held = capacity_kg(ref)
    problems = []
    if abs(held - 50.0) > 0.3:
        problems.append(f"the 21.6 m3 / 28 bar vessel holds {held:.2f} kg, not ~50")
    if abs(steel_kg_per_kg_h2(ref) - 313.0) > 2.0:
        problems.append(f"{steel_kg_per_kg_h2(ref):.1f} kg steel per kg H2, not ~313")
    per_kwh = ref["steel_kg"] / (25.0 * 171_540.0)
    if abs(per_kwh / 3.65e-3 - 1) > 0.01:
        problems.append(f"Gandiglio's own 3.65e-3 kg/kWh does not reproduce ({per_kwh:.3e})")
    if problems:
        raise AssertionError("h2_tank: " + "; ".join(problems))
    return (f"OK - tank: {held:.1f} kg H2 in the paper's vessel, {TANK_STEEL_KG_PER_KG_H2:.1f} kg steel per kg, "
            f"pad {TANK_FOUNDATIONS['concrete_m3']:.4f} m3 per kg")


# =============================================================================
# Processes
# =============================================================================
# Every process any design can use; ``processes`` below is the as-built design's
# subset (the build's static check wants every declared process on a row), and
# ``optimisation.h2_storage`` scores all designs from this full table.
ALL_PROCESSES = {
    "steel_chromium_188": Process(
        identity=("market for steel, chromium steel 18/8", "GLO"),
        query="market for steel chromium steel 18/8 GLO",
        why="the paper's own line: 'Steel, chromium steel 18/8 {GLO}'"),
    "sheet_rolling_cr_steel": Process(
        identity=("market for sheet rolling, chromium steel", "GLO", "sheet rolling, chromium steel"),
        query="market for sheet rolling chromium steel GLO",
        why="forming of a stainless shell plate; the lower of the two forming factors the cut-off plan tested "
            "(average metal working for chromium steel is the upper, kept as the sensitivity)"),
    "sheet_rolling_steel": Process(
        identity=("market for sheet rolling, steel", "GLO", "sheet rolling, steel"),
        query="market for sheet rolling steel GLO",
        why="forming of a carbon-steel shell plate, the same step as the stainless one for its own steel"),
    "steel_low_alloyed_hr": Process(
        identity=("market for steel, low-alloyed, hot rolled", "GLO"),
        query="market for steel low-alloyed hot rolled GLO",
        why="a Type I seamless cylinder is quenched-and-tempered low-alloy (Cr-Mo) steel, not stainless"),
    "steel_unalloyed": Process(
        identity=("market for steel, unalloyed", "GLO", "steel, unalloyed"),
        query="market for steel unalloyed GLO",
        why="SA-516 Gr 70 plate is carbon-manganese steel, ecoinvent's unalloyed; also the frame (11 Nov 2026)"),
    "hot_rolling_steel": Process(
        identity=("market for hot rolling, steel", "GLO", "hot rolling, steel"),
        query="market for hot rolling steel GLO",
        why="the plate mill's rolling of the unalloyed steel, once; the shell and the frame (11 Nov 2026)"),
    "concrete_normal": Process(
        identity=("concrete, all types to generic market for concrete, normal strength",
                  "RoW", "concrete, normal strength"),
        query="market for concrete normal RoW",
        why="the pad; the same concrete the SMR plant inventory uses"),
    "reinforcing_steel": Process(
        identity=("market for reinforcing steel", "GLO", "reinforcing steel"),
        query="market for reinforcing steel GLO"),
}
# The frame and saddles, every design: hot-rolled unalloyed (structural) steel.
FRAME_PROCESSES = ("steel_unalloyed", "hot_rolling_steel")
processes = {k: v for k, v in ALL_PROCESSES.items()
             if k in (DESIGN["steel_process"], DESIGN["forming_process"],
                      *FRAME_PROCESSES, "concrete_normal", "reinforcing_steel")}
flows = {}

# =============================================================================
# Activities
# =============================================================================
def _steel_rows():
    """The shell's steel and its rolling, and the frame's. Where the shell and the
    frame use the same datasets (the carbon-steel vessel since 11 Nov 2026) each
    dataset is one row carrying both masses, so every input appears once."""
    shell, frame = TANK_STEEL_KG_PER_KG_H2, TANK_FOUNDATIONS["frame_kg"]
    shell_rows = [(DESIGN["steel_process"], shell,
                   f"vessel steel, {TANK_DESIGN}, {DESIGN['pressure_bar']:g} bar: {DESIGN['note']}"),
                  (DESIGN["forming_process"], shell,
                   "ADDED — rolling the shell's steel into plate or sheet, on the shell mass (22 Oct 2026; "
                   "the mill's hot rolling for the carbon-steel vessel since 11 Nov 2026)")]
    frame_rows = [(FRAME_PROCESSES[0], frame,
                   f"ASSUMED — saddles and frame, {FRAME_STEEL_FRACTION_OF_SHELL:.0%} of the shell mass"),
                  (FRAME_PROCESSES[1], frame, "ASSUMED — hot rolling of the frame's steel (11 Nov 2026)")]
    if (DESIGN["steel_process"], DESIGN["forming_process"]) == FRAME_PROCESSES:
        return [(s[0], s[1] + f[1], "kilogram", f"{s[2]}; plus {f[1]:.2f} kg: {f[2]}")
                for s, f in zip(shell_rows, frame_rows)]
    return [(k, amt, "kilogram", note) for k, amt, note in shell_rows + frame_rows]


activities = [
    Activity(
        code=R.H2_TANK,
        name=f"Hydrogen storage tank, steel vessel, per kg capacity ({TANK_DESIGN})",
        reference_product="hydrogen storage capacity",
        unit="kilogram", location="GLO",
        comment=f"One kg of hydrogen storage capacity, design {TANK_DESIGN!r}: {DESIGN['note']}; "
                f"{TANK_STEEL_KG_PER_KG_H2:.1f} kg steel per kg H2 at {DESIGN['pressure_bar']:g} bar, the rolling "
                "of that steel into plate or sheet (ADDED 22 Oct 2026; hot rolling of unalloyed steel since 11 Nov "
                "2026), and a frame in hot-rolled unalloyed steel and a reinforced pad from the design's own vessel "
                "geometry (ASSUMED). Gandiglio et al. 2022 Table 5's vessel (15,652 kg chromium "
                "steel 18/8, 21.6 m3, 28 bar, 50.0 kg of H2) is the 'gandiglio_28bar' design. Amortised over "
                "TANK_LIFETIME_YEARS (dc_config). Out: valves, pipework, compressor hardware (cut-off register), "
                "end-of-life, delivery to site.",
        technosphere=[
            *_steel_rows(),
            ("concrete_normal", TANK_FOUNDATIONS["concrete_m3"], "cubic meter",
             f"ASSUMED — pad, {PAD_THICKNESS_M:g} m slab with {PAD_CLEARANCE_M:g} m clearance round the vessel"),
            ("reinforcing_steel", TANK_FOUNDATIONS["rebar_kg"], "kilogram",
             f"ASSUMED — pad reinforcement, {REBAR_KG_PER_M3_CONCRETE:g} kg per m3 of concrete"),
        ],
    ),
]


def inventory() -> Inventory:
    return Inventory(name=f"hydrogen tank ({TANK_DESIGN})", database=R.H2_STORAGE_DB,
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
    lines.append("  forming (sheet rolling) on the shell mass; frame and pad ASSUMED")
    return "\n".join(lines)
