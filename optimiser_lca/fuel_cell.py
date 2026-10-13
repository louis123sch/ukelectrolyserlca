"""
PEM fuel cell — Babatunde et al. 2024 stack, and 1 kWh of electricity from it.
=============================================================================

Two activities in one database:

* ``pemfc_stack_1kw_babatunde`` — cradle-to-gate manufacture of **one 1 kW
  PEM fuel cell stack**, transcribed from the paper's supplementary Table S1.
* ``pemfc_op_1kwh_h2`` — **1 kWh of net AC electricity, low voltage**, from a
  1 kW hydrogen-fed PEMFC system: hydrogen, the stack amortised, balance of
  plant and maintenance from ecoinvent net of the stack they contain.

Stack — source and scope
------------------------
Babatunde, O.M., Akintayo, B.D., Emezirinwune, M.U., Olanrewaju, O.A. (2024).
"Environmental Impact Assessment of a 1 kW Proton-Exchange Membrane Fuel
Cell: A Mid-Point and End-Point Analysis." *Hydrogen* 5(2), 352–373.
https://doi.org/10.3390/hydrogen5020020 — supplementary Table S1 documents
the ecoinvent 3.7.1 dataset ``fuel cell production, stack polymer electrolyte
membrane, 2kW electrical, future`` that the study runs in SimaPro 9.2 with
ReCiPe 2016. Manufacturing only: the paper's 32,000 h operating life is
stated in its scope but nothing operational is inventoried.

**Two scale factors, both deliberate.** ``FC_SCALE`` is the product of:

1. ``FC_KW_SCALE = 0.5`` — Table S1's reference product is a 2 kW stack but
   the paper reports everything per 1 kW. Halving is what the paper itself
   did: every value in its Tables S2–S4 is exactly 2× the corresponding
   value in its headline Tables 3–5.
2. ``FC_S1_SCALE = 1.878606235`` — Table S1 as printed does **not** reproduce
   the paper's own results. Every amount is smaller than the live ecoinvent
   dataset it documents by this uniform factor (verified exchange by
   exchange: activated carbon 0.0008 vs 0.00150288, aluminium 0.3 vs
   0.563582, graphite 4.5 vs 8.45373, platinum 0.00075 vs 0.00140895,
   electricity 16.9 vs 31.748 kWh — identical to 9 significant figures).
   At face value the inventory reproduces only ~53 % of the paper's impacts;
   scaled, it reproduces them. A defect in the published table, not a
   modelling choice — amounts below stay as printed so they can be checked
   against the PDF, and the correction is applied once at write time.

**Validated against the paper** (``validate.fc_stack_vs_paper``): on ReCiPe
2016 v1.03 (H), damage totals 1.00 / 0.99 / 1.10 of the paper's Table 5,
mid-point median ratio 1.003 over 18 categories, end-point 1.013 over 22.
The misses (ecotoxicity, metal resources, land and water use) are the
categories whose factors changed most between ecoinvent 3.7.1 and 3.9.1.

**One substitution:** Table S1 prints one aggregated electricity row and one
heat row; the ecoinvent dataset splits them over regional markets. The GLO
market groups are used for both — the single-row equivalent of what the
paper prints — and reproduce the combustion-driven categories to ~1–2 %.

Table S1's two "by-products" are waste sent for treatment, so negative
technosphere amounts against the waste markets (ecoinvent's own convention).

Operation — source and scope
----------------------------
Functional unit 1 kWh net AC. Every parameter is a literature value, not a
fitted one:

1. **Hydrogen** = 1 / (η × LHV), with η a *net AC* efficiency so parasitic
   loads (air compressor, pumps, controls, inverter) are inside it.
   ``FC_ETA_NET_BOL = 0.50`` LHV is bracketed by DOE's stationary 1–25 kWe
   target of ≥45 % (on natural gas, so including reformer losses a pure-H2
   system does not pay), a reported ~51.6 % for a 1 kW H2-fed PEMFC, and the
   ~50 % usually quoted for mid-size stationary PEMFC; 0.45–0.55 is the
   defensible range and ±0.05 moves the result ±10 %. The 0.95 derate follows
   the convention that end of life is a 10 % drop in cell voltage (Stropnik
   et al. 2022); degrading linearly puts the lifetime mean at 95 % of BOL.
2. **Stack** = 1 / (1 kW × 32,000 h), the paper's own stated life (§3.4).
   ecoinvent independently implies 28,414 h from its 0.167-stack-per-service
   replacement rate — 0.89× the paper, from a separate source.
3. **Balance of plant** = ecoinvent's whole 2 kW PEMFC system *minus the stack
   it contains*, over 60,000 h (DOE 2020 stationary target; the inverter,
   housing and air handling outlive the membrane). The subtraction is exact:
   the CH system dataset contains precisely 1.0 unit of the CH stack activity,
   and ``_on_resolve`` asserts it. CH because it is the only location where
   ecoinvent links the stack directly; RoW routes it through the GLO market.
4. **Maintenance** = ecoinvent's service event minus the 0.167 of a stack it
   bundles in (already the stack line above). What is left is the real
   consumables: platinum top-up, chromium steel, charcoal, TiO₂. The rate is
   tied to the stack-replacement rate so the two can never drift.

**The domestic-CHP correction.** ecoinvent's PEMFC is a domestic micro-CHP
unit, and two of its items are artefacts of that setting: the hot-water /
hydronic kit inside the system (34 % of the system's GWP) and 200 km of
passenger-car travel per service visit. Neither survives contact with a data
centre, where thousands of stacks sit on one site. Both are subtracted by
default (``FC_DOMESTIC_CHP_ITEMS = False``); together they are worth
11.5 g CO2e/kWh against 14.0 g/kWh for the whole embodied burden. The
travel flow and distance are *read out of* ecoinvent's maintenance dataset at
build time rather than hard-coded, so the subtraction always targets exactly
what ecoinvent uses.

**No direct biosphere flows — deliberately.** A hydrogen PEMFC emits only
water, and it is not inventoried, for the same reason ecoinvent's own PEMFC
operation datasets do not: the product water is the electrolyser's feed water
coming back out, already counted as consumed upstream. Adding it as a
``Water → air`` emission would double-count (ReCiPe's water-use factor for
water emitted to air is +1.0).

What the optimiser reads: ``optimisation/fuel_cell.py`` splits the operation
activity into stack (per MW, replaced on max(calendar, duty)), balance of
plant (likewise) and maintenance (per MWh), and excludes the hydrogen, which
the LP supplies explicitly.
"""
from __future__ import annotations

from optimiser_lca import registry as R
from optimiser_lca.common import FG, Activity, Flow, Inventory, Process

# =============================================================================
# Parameters
# =============================================================================
# --- stack: the two scale factors (see the docstring for the evidence) --------
FC_KW_SCALE = 0.5           # Table S1's reference product is a 2 kW stack; the paper's FU is 1 kW
FC_S1_SCALE = 1.878606235   # Table S1's printed amounts are uniformly this factor smaller than
                            # the ecoinvent dataset it documents; set to 1.0 to build it verbatim
FC_SCALE    = FC_KW_SCALE * FC_S1_SCALE

# --- operation ------------------------------------------------------------------
FC_RATED_POWER_KW     = 1.0        # matches the paper's 1 kW stack
FC_H2_LHV_KWH_PER_KG  = 33.33      # hydrogen lower heating value, 120 MJ/kg
FC_ETA_NET_BOL        = 0.50       # net AC electrical efficiency at beginning of life, LHV basis
FC_DEGRADATION_DERATE = 0.95       # mean-over-life efficiency as a fraction of BOL; 1.0 = no degradation
FC_STACK_LIFETIME_H   = 32_000     # Babatunde et al. 2024, section 3.4 (their own figure)
FC_SYSTEM_LIFETIME_H  = 60_000     # DOE 2020 stationary target; BoP outlives the stack
FC_BOP_LOCATION       = "CH"       # the only location where ecoinvent links the stack directly
FC_DOMESTIC_CHP_ITEMS = False      # True to model a domestic micro-CHP instead
FC_MAINT_STACK_FRACTION = 0.167    # stack fraction inside one ecoinvent maintenance event
# Which hydrogen the fuel cell burns: (database, code). Any per-kg-H2 activity
# works — swap in AE_OP / SOEC_OP / SMR for a different supply chain.
FC_H2_SOURCE = (R.HYDROGEN_DB, R.PEM_OP)

# --- derived --------------------------------------------------------------------
FC_ETA_NET_MEAN  = FC_ETA_NET_BOL * FC_DEGRADATION_DERATE
FC_H2_PER_KWH    = 1.0 / (FC_ETA_NET_MEAN * FC_H2_LHV_KWH_PER_KG)      # kg H2 / kWh AC
FC_STACK_PER_KWH = 1.0 / (FC_RATED_POWER_KW * FC_STACK_LIFETIME_H)    # unit / kWh AC
FC_BOP_PER_KWH   = 1.0 / (FC_RATED_POWER_KW * FC_SYSTEM_LIFETIME_H)   # unit / kWh AC
# Maintenance events per kWh, tied to the stack-replacement rate so the two can
# never disagree: ~6 services per stack, then x0.5 for ecoinvent's 2 kW unit.
FC_MAINT_PER_KWH = (FC_STACK_PER_KWH / FC_MAINT_STACK_FRACTION) * 0.5
# ecoinvent's 2 kW system scaled to FC_RATED_POWER_KW = 1 kW.
_BOP   = FC_BOP_PER_KWH * 0.5
_MAINT = FC_MAINT_PER_KWH          # already carries the same 0.5


def check_parameters() -> str:
    if not 0.0 < FC_ETA_NET_BOL <= 1.0:
        raise ValueError("FC_ETA_NET_BOL must be a fraction in (0, 1].")
    if not 0.0 < FC_DEGRADATION_DERATE <= 1.0:
        raise ValueError("FC_DEGRADATION_DERATE must be a fraction in (0, 1].")
    if FC_STACK_LIFETIME_H <= 0 or FC_SYSTEM_LIFETIME_H <= 0:
        raise ValueError("Fuel cell lifetimes must be positive.")
    if not 0.0 < FC_MAINT_STACK_FRACTION <= 1.0:
        raise ValueError("FC_MAINT_STACK_FRACTION must be a fraction in (0, 1].")
    # The maintenance subtraction must exactly cancel the stack ecoinvent bundles in.
    if abs(_MAINT * FC_MAINT_STACK_FRACTION - FC_STACK_PER_KWH * 0.5) > 1e-15:
        raise AssertionError("Maintenance stack content and the stack line have drifted apart.")
    return (f"OK - eta {FC_ETA_NET_MEAN:.3f} mean, {FC_H2_PER_KWH:.5f} kg H2/kWh, "
            f"stack {FC_STACK_PER_KWH:.3e}/kWh, BoP {_BOP:.3e}/kWh, maint {_MAINT:.3e}/kWh")


check_parameters()

# =============================================================================
# Processes
# =============================================================================
processes = {
    # --- stack, Table S1 ---------------------------------------------------------
    "activated_carbon": Process(
        query="market for activated carbon granular GLO", pick=0,
        identity=("market for activated carbon, granular", "GLO", "activated carbon, granular")),
    "aluminium_wrought": Process(
        query="market for aluminium wrought alloy GLO", pick=1,
        identity=("market for aluminium, wrought alloy", "GLO", "aluminium, wrought alloy")),
    "building_hall": Process(
        query="market for building hall steel construction GLO", pick=0,
        identity=("market for building, hall, steel construction", "GLO", "building, hall, steel construction")),
    "building_multi": Process(
        query="market for building multi-storey GLO", pick=0,
        identity=("market for building, multi-storey", "GLO", "building, multi-storey")),
    "electricity_mv": Process(
        query="market group for electricity medium voltage GLO", pick=0,
        identity=("market group for electricity, medium voltage", "GLO", "electricity, medium voltage"),
        why="Table S1 prints one aggregated 16.9 kWh row; the ecoinvent dataset splits it "
            "over 8 regional markets - the GLO market group is the single-row equivalent"),
    "glass_fibre": Process(
        query="market for glass fibre GLO", pick=1,
        identity=("market for glass fibre", "GLO", "glass fibre")),
    "graphite": Process(
        query="market for graphite GLO", pick=0,
        identity=("market for graphite", "GLO", "graphite")),
    "heat_natural_gas": Process(
        query="market group for heat district or industrial natural gas GLO", pick=0,
        identity=("market group for heat, district or industrial, natural gas", "GLO",
                  "heat, district or industrial, natural gas"),
        why="same aggregation as electricity (Table S1: one 22.3 MJ row, dataset: 3 regional markets)"),
    "isopropanol": Process(
        query="market for isopropanol RoW", pick=0,
        identity=("market for isopropanol", "RoW", "isopropanol")),
    "phenolic_resin": Process(
        query="market for phenolic resin RoW", pick=0,
        identity=("market for phenolic resin", "RoW", "phenolic resin")),
    "platinum": Process(
        query="market for platinum GLO", pick=0,
        identity=("market for platinum", "GLO", "platinum")),
    "steel_chromium_188": Process(
        query="market for steel chromium steel 18/8 hot rolled GLO", pick=0,
        identity=("market for steel, chromium steel 18/8, hot rolled", "GLO",
                  "steel, chromium steel 18/8, hot rolled")),
    "tetrafluoroethylene": Process(
        query="market for tetrafluoroethylene GLO", pick=1,
        identity=("market for tetrafluoroethylene", "GLO", "tetrafluoroethylene")),
    "water_deionised": Process(
        query="market for water deionised RoW", pick=0,
        identity=("market for water, deionised", "RoW", "water, deionised")),
    "waste_plastic": Process(
        query="market for waste plastic industrial electronics RoW", pick=0,
        identity=("market for waste plastic, industrial electronics", "RoW",
                  "waste plastic, industrial electronics")),
    "waste_pvf": Process(
        query="market for waste polyvinylfluoride RoW", pick=0,
        identity=("market for waste polyvinylfluoride", "RoW", "waste polyvinylfluoride")),
    # --- operation: ecoinvent's own PEMFC system, picked by exact name -------------
    # The search for the system ranks the *stack* dataset first (its name is a
    # superstring), so these were never index picks.
    "fc_system_ecoinvent": Process(
        query="fuel cell production polymer electrolyte membrane 2kW electrical future",
        identity=("fuel cell production, polymer electrolyte membrane, 2kW electrical, future",
                  FC_BOP_LOCATION, "fuel cell, polymer electrolyte membrane, 2kW electrical, future"),
        why="the whole system - stack + inverter + housing + air handling + hydronic kit"),
    "fc_stack_ecoinvent": Process(
        query="fuel cell production stack polymer electrolyte membrane 2kW electrical future",
        identity=("fuel cell production, stack polymer electrolyte membrane, 2kW electrical, future",
                  FC_BOP_LOCATION, "fuel cell, stack polymer electrolyte membrane, 2kW electrical, future"),
        why="subtracted from the system and from maintenance so the paper's stack is counted once"),
    "chp_hydronics": Process(
        query="heating and sanitary equipment production mini CHP plant",
        identity=("heating and sanitary equipment production, mini CHP plant",
                  FC_BOP_LOCATION, "heating and sanitary equipment, mini CHP plant"),
        why="the domestic hot-water kit inside ecoinvent's system; 34 % of its GWP"),
    "maintenance": Process(
        query="maintenance polymer electrolyte membrane fuel cell 2kW electrical",
        identity=("maintenance, polymer electrolyte membrane fuel cell 2kW electrical",
                  FC_BOP_LOCATION, "maintenance, polymer electrolyte membrane fuel cell, 2kW electrical")),
    # Pinned at build time from the maintenance dataset itself (see _on_resolve),
    # so the subtraction targets exactly the flow ecoinvent uses.
    "service_transport": Process(
        query="transport passenger car RER",
        identity=("market for transport, passenger car", "RER", "transport, passenger car"),
        why="the technician driving to a house, read out of ecoinvent's maintenance event"),
}

# Table S1's "Inputs from environment" + "Emissions to air/water". Categories fix
# the compartment - the two "Water" flows are the same substance in different ones.
flows = {
    "propanol_air": Flow(identity=("Propanol", ("air", "urban air close to ground")),
                         query="Propanol", why="the isopropanol input, evaporated"),
    "water_air":    Flow(identity=("Water", ("air",)), query="Water air"),
    "water_water":  Flow(identity=("Water", ("water",)), query="Water water", pick=2),
    "occupation_industrial": Flow(identity=("Occupation, industrial area", ("natural resource", "land")),
                                  query="Occupation industrial area"),
    "transformation_from": Flow(identity=("Transformation, from unspecified", ("natural resource", "land")),
                                query="Transformation from unspecified"),
    "transformation_to": Flow(identity=("Transformation, to industrial area", ("natural resource", "land")),
                              query="Transformation to industrial area"),
}

# =============================================================================
# Activities
# =============================================================================
_kg, _kwh, _MJ, _unit, _m2, _m3 = ("kilogram", "kilowatt hour", "megajoule", "unit",
                                   "square meter", "cubic meter")

STACK = Activity(
    code=R.FC_STACK,
    name="Fuel cell stack production, PEM, 1 kW (Babatunde et al. 2024)",
    reference_product="fuel cell stack, polymer electrolyte membrane, 1 kW electrical",
    unit=_unit, location="GLO",
    comment="Cradle-to-gate manufacture of one 1 kW PEM fuel cell stack. Babatunde et al. "
            "2024, Hydrogen 5(2), 352-373, supplementary Table S1 (which documents the "
            "ecoinvent 3.7.1 dataset 'fuel cell production, stack polymer electrolyte "
            f"membrane, 2kW electrical, future'). Amounts as printed in Table S1, scaled by "
            f"{FC_SCALE:.9f} = {FC_KW_SCALE} (2 kW reference product -> 1 kW functional unit, "
            f"the same halving the paper applies between its Tables S2-S4 and Tables 3-5) x "
            f"{FC_S1_SCALE} (Table S1's printed amounts are uniformly this factor smaller "
            "than the ecoinvent dataset they document, and reproduce only ~53% of the "
            "paper's own results without it). Manufacturing only - no use phase.",
    # Amounts exactly as printed in Table S1 (per one 2 kW stack); FC_SCALE is
    # applied once, when the exchanges are written.
    scale=FC_SCALE, scale_note="(FC_KW_SCALE x FC_S1_SCALE)",
    technosphere=[
        # --- Inputs from technosphere ---
        ("activated_carbon",     0.0008,  _kg,  "Activated carbon, granular"),
        ("aluminium_wrought",    0.3,     _kg,  "Aluminium, wrought alloy — end plates / housing"),
        ("building_hall",        0.00022, _m2,  "Building, hall, steel construction — factory infrastructure"),
        ("building_multi",       0.0013,  _m3,  "Building, multi-storey — factory infrastructure"),
        ("electricity_mv",      16.9,     _kwh, "Electricity, medium voltage — stack manufacturing"),
        ("glass_fibre",          0.1,     _kg,  "Glass fibre"),
        ("graphite",             4.5,     _kg,  "Graphite — bipolar plates"),
        ("heat_natural_gas",    22.3,     _MJ,  "Heat, district or industrial, natural gas — stack manufacturing"),
        ("isopropanol",          0.0095,  _kg,  "Isopropanol — electrode ink solvent"),
        ("phenolic_resin",       1.1,     _kg,  "Phenolic resin — bipolar plate binder"),
        ("platinum",             0.00075, _kg,  "Platinum — anode + cathode catalyst"),
        ("steel_chromium_188",   0.1,     _kg,  "Steel, chromium steel 18/8, hot rolled — tie rods / current collectors"),
        ("tetrafluoroethylene",  0.052,   _kg,  "Tetrafluoroethylene — PFSA (Nafion) membrane precursor"),
        ("water_deionised",      0.006,   _kg,  "Water, deionised"),
        # --- By-products (Table S1) — waste to treatment, hence negative ---
        ("waste_plastic",       -6.6,     _kg,  "Waste plastic, industrial electronics — to treatment"),
        ("waste_pvf",           -0.052,   _kg,  "Waste polyvinylfluoride — to treatment"),
    ],
    biosphere=[
        ("propanol_air",           0.0095, _kg,                "Propanol to air — the isopropanol input, evaporated"),
        ("water_air",              9e-7,   _m3,                "Water to air"),
        ("water_water",            5.1e-6, _m3,                "Water to water"),
        ("occupation_industrial",  0.0395, "square meter-year", "Occupation, industrial area"),
        ("transformation_from",    0.0008, _m2,                "Transformation, from unspecified"),
        ("transformation_to",      0.0008, _m2,                "Transformation, to industrial area"),
    ],
)

OPERATION = Activity(
    code=R.FC_OP,
    name="Electricity, low voltage, from PEM fuel cell (hydrogen)",
    reference_product="electricity, low voltage",
    unit=_kwh, location="GB",
    comment=f"1 kWh net AC from a {FC_RATED_POWER_KW:g} kW hydrogen-fed PEMFC system. "
            f"Hydrogen {FC_H2_PER_KWH:.5f} kg/kWh = 1/(eta {FC_ETA_NET_MEAN:.3f} x LHV "
            f"{FC_H2_LHV_KWH_PER_KG} kWh/kg), where eta is a NET AC efficiency "
            f"({FC_ETA_NET_BOL:.2f} at beginning of life x {FC_DEGRADATION_DERATE:.2f} for "
            "degradation to a 10% cell-voltage end-of-life criterion), so parasitic loads are "
            f"inside it. Stack (Babatunde et al. 2024) amortised over {FC_STACK_LIFETIME_H:,} h "
            "- the paper's own stated life - which doubles as the stack-replacement/maintenance "
            "model. Balance of plant is ecoinvent's whole 2 kW PEMFC system minus its own stack "
            f"(exact subtraction, no double counting), over {FC_SYSTEM_LIFETIME_H:,} h; "
            f"maintenance is ecoinvent's service event minus the stack it bundles in, at "
            f"{1/FC_MAINT_STACK_FRACTION:.1f} services per stack"
            + ("" if FC_DOMESTIC_CHP_ITEMS else
               ", with the domestic hot-water kit and technician-driving subtracted as "
               "artefacts of ecoinvent's micro-CHP setting")
            + ". No direct biosphere flows: the product water is the electrolyser's feed water "
            "returning, already counted as consumed upstream.",
    technosphere=[
        (FG(FC_H2_SOURCE[1], database=FC_H2_SOURCE[0]), FC_H2_PER_KWH, _kg,
         f"Hydrogen — 1 / (eta {FC_ETA_NET_MEAN:.3f} x LHV {FC_H2_LHV_KWH_PER_KG} kWh/kg)"),
        (FG(R.FC_STACK), FC_STACK_PER_KWH, _unit,
         f"Stack (Babatunde et al. 2024) over {FC_STACK_LIFETIME_H:,} h"),
        # Balance of plant = ecoinvent's whole system minus its own stack.
        ("fc_system_ecoinvent", _BOP, _unit,
         f"BoP: ecoinvent's whole 2 kW PEMFC system, over {FC_SYSTEM_LIFETIME_H:,} h"),
        ("fc_stack_ecoinvent", -_BOP, _unit,
         "BoP: minus ecoinvent's own stack, so the paper's stack above is not double-counted"),
        # Maintenance = ecoinvent's service event minus the stack it bundles in.
        ("maintenance", _MAINT, _unit,
         f"Maintenance: platinum top-up, chromium steel, consumables — {1/FC_MAINT_STACK_FRACTION:.1f} services per stack"),
        ("fc_stack_ecoinvent", -_MAINT * FC_MAINT_STACK_FRACTION, _unit,
         "Maintenance: minus the stack ecoinvent bundles into a service event — already counted above"),
    ] + ([] if FC_DOMESTIC_CHP_ITEMS else [
        ("chp_hydronics", -0.65 * _BOP, _unit,
         "Domestic-CHP artefact: minus the hot-water/hydronic kit — no such kit in a data centre"),
        # The driving exchange is appended by _on_resolve, with the distance read
        # from ecoinvent's maintenance dataset.
    ]),
)

activities = [STACK, OPERATION]

SERVICE_TRANSPORT_KM = None   # filled by _on_resolve


def _on_resolve(resolved: dict) -> None:
    """Guards that only Brightway can check, and the one exchange whose amount
    is read out of ecoinvent rather than written here."""
    global SERVICE_TRANSPORT_KM
    system, stack = resolved["fc_system_ecoinvent"], resolved["fc_stack_ecoinvent"]
    stack_in_system = [e.amount for e in system.technosphere() if e.input.key == stack.key]
    if stack_in_system != [1.0]:
        raise ValueError(
            f"Expected exactly one 1.0-unit stack exchange inside {system.get('name')!r} "
            f"({FC_BOP_LOCATION}), found {stack_in_system}. The BoP subtraction would not be "
            "exact — FC_BOP_LOCATION must be CH.")
    drive = [e for e in resolved["maintenance"].technosphere()
             if "transport, passenger car" in e.input.get("name", "")]
    if len(drive) != 1:
        raise ValueError(f"Expected exactly 1 passenger-car transport exchange in ecoinvent's "
                         f"PEMFC maintenance dataset, found {len(drive)}.")
    if drive[0].input.key != resolved["service_transport"].key:
        raise ValueError(
            f"ecoinvent's maintenance event drives {drive[0].input} but 'service_transport' "
            f"is pinned to {processes['service_transport'].identity}; re-pin it.")
    SERVICE_TRANSPORT_KM = float(drive[0].amount)
    if not FC_DOMESTIC_CHP_ITEMS and not any(
            k == "service_transport" for k, *_ in OPERATION.technosphere):
        OPERATION.technosphere.append(
            ("service_transport", -SERVICE_TRANSPORT_KM * _MAINT, "kilometer",
             f"Domestic-CHP artefact: minus {SERVICE_TRANSPORT_KM:g} km of technician driving per "
             "service — thousands of stacks on one site, not one unit per house"))


def inventory() -> Inventory:
    return Inventory(name="PEM fuel cell (Babatunde 2024)", database=R.FUEL_CELL_DB,
                     processes=processes, flows=flows, activities=activities,
                     on_resolve=_on_resolve)


def describe() -> str:
    return "\n".join([
        "PEM fuel cell operation, per 1 kWh net AC:",
        f"  hydrogen         {FC_H2_PER_KWH:>12.5f} kg    "
        f"(eta {FC_ETA_NET_BOL:.2f} BOL x {FC_DEGRADATION_DERATE:.2f} degradation = {FC_ETA_NET_MEAN:.3f})",
        f"  stack            {FC_STACK_PER_KWH:>12.4e} unit  (1 / {FC_RATED_POWER_KW:g} kW / {FC_STACK_LIFETIME_H:,} h)",
        f"  balance of plant {_BOP:>12.4e} unit  (1 / {FC_RATED_POWER_KW:g} kW / {FC_SYSTEM_LIFETIME_H:,} h, net of its stack)",
        f"  maintenance      {_MAINT:>12.4e} unit  ({1/FC_MAINT_STACK_FRACTION:.1f} services per stack, net of its stack)",
        f"  domestic-CHP items {'INCLUDED' if FC_DOMESTIC_CHP_ITEMS else 'excluded'}",
        f"  hydrogen source  {FC_H2_SOURCE[1]!r} in {FC_H2_SOURCE[0]!r}",
        f"  stack scale      {FC_SCALE:.9f} (= {FC_KW_SCALE} kW-scale x {FC_S1_SCALE} Table-S1 correction)",
    ])
