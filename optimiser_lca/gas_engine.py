"""
Gas engines — ecoinvent's 1 MW lean-burn gas engine set, run on British gas, power only.
=============================================================================

Source and scope
----------------
ecoinvent 3.9.1 apos, ``heat and power co-generation, natural gas, 1MW electrical, lean burn``
(Europe without Switzerland; ecoinvent v2 data, Jakobsberg/Basel engine inventories) and its
building sets, ``heat and power co-generation unit construction, 1MW electrical, common
components for heat+electricity`` and ``... components for electricity only`` (RER). ecoinvent
has no power-only gas engine; this is its only gas engine data, so it is used for power only.
The efficiency is the UK government's: DESNZ, *Unabated gas: electricity generation cost study*
(CEPA and GHD, 14 Jan 2026), Generation Option 5, Table 3.24, 44.6 % net on the lower heating
value. The decision record is ``docs/GAS_ENGINE_PLAN.md``.

Three activities; **functional units: 1 kWh of net electricity at 11 kV (running and maintenance)
and 1 MW of engines built (the plant)**:

* ``gas_engine_op_1kwh`` — **1 kWh of net electricity at 11 kV** from the engines, running:
  British high-pressure gas (``market for natural gas, high pressure`` GB, the gas the hydrogen
  inventories burn), the CO2 its carbon makes, and the engine's own exhaust and oil copied per m³
  of gas from the lean-burn dataset.
* ``gas_engine_maintenance_1kwh`` — the set's maintenance per kWh, over ecoinvent's own unit
  life of 100,000 running hours (its Jakobsberg comments: "Life time for operation assumed
  100'000 h"; DESNZ §3.5 gives engines ~100,000 h too), so it follows running hours as the cost
  side's per-MWh maintenance does.
* ``gas_engine_plant_1mw`` — **1 MW of engines, built**: the shared and electricity-only parts of
  ecoinvent's 1 MW set, less its maintenance (charged per kWh instead) and less its travel to
  site, plus a steel hall.

**Boundary.** In: the gas's supply chain and leaks, burning, the engine's exhaust and oil, the
engines, generators, controls, sound insulation, air handling, site work and concrete pads, the
hall, maintenance, and upstream transport inside the datasets (the car trips inside the
*production* of the electric parts and air units stay). Out (``GE_SCOPE``, ``exclusions.py``):
the car trips to site for building, start-up and maintenance; delivery to site (the datasets
carry no freight to site); the gas connection pipe (a user decision, 13 Nov 2026); end-of-life.

One unsourced item is carried as an estimate, not inventoried: medium-voltage switchgear, one
breaker per engine onto the 11 kV bus (``exclusions.py``, Teffera's 0.61 t per MW, as the fuel cell's).

**Substitutions.** The dataset's CO2 (2.18 kg/m³) is replaced by the carbon balance of the
British gas it burns (2.00 kg/m³ before the carbon leaving as methane and carbon monoxide):
the v2 figure is more carbon than the gas holds (``check()``). Its European gas is replaced by
British gas. Its methane line for "losses due to distribution in low pressure network" is left
out: a plant this size takes high-pressure gas, whose leaks are in the GB market already.

**Verified** by ``check()``: the carbon balance closes, the engine burns 0.224 m³ per kWh, and
the dataset's own CO2 exceeds the gas's carbon; ``tests/test_gas_engine.py`` holds the scored
total to a 0.50-0.65 kg CO2e/kWh band and against DESNZ's 2026 conversion factors.
"""
from __future__ import annotations

from optimiser_lca import registry as R
from optimiser_lca.common import Activity, Flow, Inventory, Process
from optimiser_lca.hydrogen import CO2_PER_KG_C, GAS_FOSSIL_C_PER_KG, GAS_KG_PER_M3

# =============================================================================
# Parameters
# =============================================================================
# --- the engine (DESNZ 2026, Generation Option 5) ------------------------------
GE_ETA_NET_LHV = 0.446              # TRANSCRIBED - DESNZ 2026 Table 3.24, net efficiency, all cases
GE_UNIT_LIFE_H = 100_000.0          # TRANSCRIBED - ecoinvent's Jakobsberg comments; DESNZ §3.5 "~100,000 hours"
GE_SET_KW = 1_000.0                 # TRANSCRIBED - the ecoinvent set is "1MW electrical"

# --- British gas, ecoinvent 3.9.1 'market for natural gas, high pressure' GB properties ------
# Mass and carbon content are hydrogen.py's (one place); the heating values are the same
# exchange's properties (Meili et al. 2022 §5.2).
GAS_NET_MJ_PER_M3 = 36.0000756      # TRANSCRIBED - 'heating value, net'
GAS_GROSS_MJ_PER_M3 = 40.000084     # TRANSCRIBED - 'heating value, gross'
M_CH4, M_CO, M_C = 16.0425, 28.0101, 12.011     # constant - molar masses, g/mol

# --- the lean-burn dataset, per MJ of its heat (ecoinvent 3.9.1, Europe w/o CH) ------
LB_GAS_M3_PER_MJ = 0.009534260490612274         # TRANSCRIBED - 'market group for natural gas, high pressure'
LB_PER_MJ = {                                   # TRANSCRIBED - the engine's own rows, kg per MJ heat
    "ch4": 2.974689273071042e-05,               # 'Methane, fossil', urban air: "estimate based on different references"
    "n2o": 1.859180795669389e-06,               # "rough estimate"
    "co": 3.978646902732512e-05,
    "nox": 3.9042796709057285e-05,
    "nmvoc": 3.718361591338794e-06,
    "pm25": 5.5775423870081826e-08,
    "so2": 2.0450988752363395e-07,
    "lube_oil": 1.1155084774016385e-05,         # 'market for lubricating oil' RER, same mass to waste oil
}
LB_CO2_PER_MJ = 0.020822824911497232            # TRANSCRIBED - its CO2, replaced (see check())
LB_CH4_NETWORK_PER_MJ = 4.982604532393981e-05   # TRANSCRIBED - its low-pressure network methane, left out

# --- the 1 MW building set (ecoinvent 3.9.1, RER) --------------------------------
CHP_MAINT_PER_SET = 2.89            # TRANSCRIBED - maintenance, ... 160kW electrical, in the shared parts
CHP_CONSTRUCTION_PER_SET = 2.61     # TRANSCRIBED - construction work and start-up, ... 160kW, each
CAR_KM_CONSTRUCTION = 1_500.0       # TRANSCRIBED - passenger car km per construction work, RER
CAR_KM_STARTUP = 300.0              # TRANSCRIBED - passenger car km per start-up, RER
CAR_KM_MAINT = 6_000.0              # TRANSCRIBED - passenger car km per maintenance, RER
# The hall: ecoinvent's 3 MW organic Rankine cycle power unit, "the total needed area of the
# building (500m2)" (exchange comment), per MW. A stand-in: ecoinvent has no gas-engine hall.
GE_HALL_M2_PER_MW = 500.0 / 3.0     # DERIVED - 500 m2 per 3 MW unit

# --- derived ------------------------------------------------------------------
GE_GAS_M3_PER_KWH = 3.6 / GE_ETA_NET_LHV / GAS_NET_MJ_PER_M3        # DERIVED - 0.224 m3/kWh
GE_GAS_MWH_HHV_PER_MWH = GE_GAS_M3_PER_KWH * GAS_GROSS_MJ_PER_M3 / 3.6   # DERIVED - 2.49, the gas bill's basis
GE_PER_KWH = {k: v / LB_GAS_M3_PER_MJ * GE_GAS_M3_PER_KWH for k, v in LB_PER_MJ.items()}   # DERIVED
GE_GAS_C_KG_PER_KWH = GE_GAS_M3_PER_KWH * GAS_KG_PER_M3 * GAS_FOSSIL_C_PER_KG             # DERIVED
GE_CO2_KG_PER_KWH = (GE_GAS_C_KG_PER_KWH - GE_PER_KWH["ch4"] * M_C / M_CH4
                     - GE_PER_KWH["co"] * M_C / M_CO) * CO2_PER_KG_C                     # DERIVED
GE_MAINT_PER_KWH = CHP_MAINT_PER_SET / (GE_SET_KW * GE_UNIT_LIFE_H)                      # DERIVED
GE_CAR_KM_TO_SITE_PER_SET = CHP_CONSTRUCTION_PER_SET * (CAR_KM_CONSTRUCTION + CAR_KM_STARTUP)  # DERIVED 4,698

GE_SCOPE = {
    "gas": "SUBSTITUTED - British high-pressure gas (GB market) for the dataset's European gas; its supply "
           "chain and leaks are in. High pressure: the local network would add ~2.6 %",
    "co2": "SUBSTITUTED - CO2 from the carbon balance of the gas burned, for the dataset's v2 figure, which "
           "exceeds the gas's carbon content",
    "network_methane": "SUBSTITUTED - the dataset's low-pressure network methane is not this plant's: it takes "
                       "high-pressure gas, whose leaks the GB market carries",
    "heat_parts": "INCLUDED - a power-only set: the shared and electricity-only parts; the heat-only parts "
                  "(hot-water storage, heating equipment, heat pump) serve a heat use this plant does not have",
    "maintenance": "INCLUDED - per running hour, over the set's 100,000 h, not per MW built",
    "hall": "INCLUDED - a steel hall at 500 m2 per 3 MW (ecoinvent's organic Rankine cycle unit), a stand-in; "
            "both the hall floor and the engine pads are kept, which errs high",
    "transport": "EXCLUDED - travel to site: the set's construction-work and start-up car trips (and the "
                 "maintenance trips, which leave with the maintenance); delivery to site, which the datasets "
                 "do not carry. Upstream trips inside part production stay in",
    "gas_connection": "EXCLUDED - the pipe from the gas network to the site (user decision, 13 Nov 2026; "
                      "recorded in TODO.md); errs low",
    "end_of_life": "EXCLUDED - cradle-to-gate, as everywhere in this study",
}


def check() -> str:
    """The carbon balance closes, the gas burned is ~0.224 m3/kWh, and the dataset's own CO2 is more
    carbon than its gas holds (the reason it is replaced)."""
    problems = []
    gas_c = GE_GAS_C_KG_PER_KWH
    out_c = (GE_CO2_KG_PER_KWH / CO2_PER_KG_C + GE_PER_KWH["ch4"] * M_C / M_CH4
             + GE_PER_KWH["co"] * M_C / M_CO)
    if abs(out_c / gas_c - 1.0) > 1e-12:
        problems.append(f"carbon balance: {out_c:.6f} kg C out vs {gas_c:.6f} in")
    if not 0.220 < GE_GAS_M3_PER_KWH < 0.230:
        problems.append(f"gas burned {GE_GAS_M3_PER_KWH:.4f} m3/kWh, expected ~0.224")
    if not 2.45 < GE_GAS_MWH_HHV_PER_MWH < 2.52:
        problems.append(f"gas {GE_GAS_MWH_HHV_PER_MWH:.3f} MWh (gross) per MWh, expected ~2.49")
    lb_co2_per_m3 = LB_CO2_PER_MJ / LB_GAS_M3_PER_MJ
    gas_co2_per_m3 = GAS_KG_PER_M3 * GAS_FOSSIL_C_PER_KG * CO2_PER_KG_C
    if not lb_co2_per_m3 > gas_co2_per_m3 * 1.05:
        problems.append(f"the dataset's CO2 ({lb_co2_per_m3:.3f} kg/m3) no longer exceeds its gas's carbon "
                        f"({gas_co2_per_m3:.3f}): the substitution's reason has gone")
    if abs(GE_CAR_KM_TO_SITE_PER_SET - 4_698.0) > 0.5:
        problems.append(f"car trips to site {GE_CAR_KM_TO_SITE_PER_SET:,.0f} km per set, expected 4,698")
    if problems:
        raise AssertionError("gas_engine:\n  " + "\n  ".join(problems))
    return (f"OK - gas engine: {GE_GAS_M3_PER_KWH * 1000:.1f} m3 per MWh, {GE_CO2_KG_PER_KWH * 1000:.1f} kg CO2 "
            f"per MWh from burning; the dataset's {lb_co2_per_m3:.3f} kg/m3 exceeds the gas's "
            f"{gas_co2_per_m3:.3f}")


# =============================================================================
# Processes and flows — exact identities, with the search that found each one
# =============================================================================
processes = {
    "gas_hp_gb": Process(
        query="market for natural gas high pressure GB", pick=1,
        identity=("market for natural gas, high pressure", "GB", "natural gas, high pressure"),
        why="the hydrogen inventories' gas; hit 0 is the pressure reduction to low pressure"),
    "lube_oil": Process(
        query="market for lubricating oil RER", pick=0,
        identity=("market for lubricating oil", "RER", "lubricating oil")),
    "waste_oil": Process(
        query="market for waste mineral oil Europe without Switzerland", pick=0,
        identity=("market for waste mineral oil", "Europe without Switzerland", "waste mineral oil")),
    "chp_common": Process(
        query="heat and power co-generation unit construction 1MW electrical common components", pick=0,
        identity=("heat and power co-generation unit construction, 1MW electrical, common components for "
                  "heat+electricity", "RER",
                  "heat and power co-generation unit, 1MW electrical, common components for heat+electricity")),
    "chp_elec": Process(
        query="heat and power co-generation unit construction 1MW electrical components for electricity only",
        pick=0,
        identity=("heat and power co-generation unit construction, 1MW electrical, components for electricity "
                  "only", "RER",
                  "heat and power co-generation unit, 1MW electrical, components for electricity only")),
    "chp_maint": Process(
        query="maintenance heat and power co-generation unit 160kW electrical", pick=0,
        identity=("maintenance, heat and power co-generation unit, 160kW electrical", "RER",
                  "maintenance, heat and power co-generation unit, 160kW electrical")),
    "car_rer": Process(
        query="market for transport passenger car RER", pick=0,
        identity=("market for transport, passenger car", "RER", "transport, passenger car"),
        why="the set's own car trips are this market, RER; used only to take them back out"),
    "hall_steel": Process(
        query="market for building hall steel construction GLO", pick=0,
        identity=("market for building, hall, steel construction", "GLO", "building, hall, steel construction"),
        why="a steel hall for an engine plant (user, 13 Nov 2026); the organic Rankine unit uses the generic hall"),
}

_AIR = ("air", "urban air close to ground")
flows = {
    "co2": Flow(query="Carbon dioxide fossil", identity=("Carbon dioxide, fossil", _AIR)),
    "ch4": Flow(query="Methane fossil", identity=("Methane, fossil", _AIR)),
    "n2o": Flow(query="Dinitrogen monoxide", identity=("Dinitrogen monoxide", _AIR)),
    "co": Flow(query="Carbon monoxide fossil", identity=("Carbon monoxide, fossil", _AIR)),
    "nox": Flow(query="Nitrogen oxides", identity=("Nitrogen oxides", _AIR)),
    "nmvoc": Flow(query="NMVOC non-methane volatile organic compounds",
                  identity=("NMVOC, non-methane volatile organic compounds", _AIR)),
    "pm25": Flow(query="Particulate Matter < 2.5 um", identity=("Particulate Matter, < 2.5 um", _AIR)),
    "so2": Flow(query="Sulfur dioxide", identity=("Sulfur dioxide", _AIR)),
}

# =============================================================================
# Activities
# =============================================================================
_LB = "ecoinvent 3.9.1 lean burn 1 MW, per m3 of gas"
OP = Activity(
    code=R.GE_OP,
    name="Electricity from gas engines, 1 kWh net at 11 kV (ecoinvent lean-burn 1 MW engine, British gas)",
    reference_product="electricity, medium voltage", unit="kilowatt hour", location="GB",
    comment="ecoinvent 3.9.1 'heat and power co-generation, natural gas, 1MW electrical, lean burn' (Europe w/o "
            "CH), its exhaust and oil per m3 of gas, on British high-pressure gas at DESNZ 2026's 44.6 % net "
            "efficiency (Table 3.24). CO2 from the gas's carbon balance. No maintenance or building here "
            "(gas_engine_maintenance_1kwh, gas_engine_plant_1mw).",
    technosphere=[
        ("gas_hp_gb", GE_GAS_M3_PER_KWH, "cubic meter", "DERIVED - 3.6 MJ / 0.446 / 36.0 MJ per m3 (net)"),
        ("lube_oil",  GE_PER_KWH["lube_oil"], "kilogram", _LB),
        ("waste_oil", -GE_PER_KWH["lube_oil"], "kilogram", _LB + "; the used oil to treatment"),
    ],
    biosphere=[
        ("co2",   GE_CO2_KG_PER_KWH, "kilogram", "DERIVED - the gas's fossil carbon less that in CH4 and CO"),
        ("ch4",   GE_PER_KWH["ch4"], "kilogram", _LB + ", the engine line"),
        ("n2o",   GE_PER_KWH["n2o"], "kilogram", _LB),
        ("co",    GE_PER_KWH["co"], "kilogram", _LB),
        ("nox",   GE_PER_KWH["nox"], "kilogram", _LB),
        ("nmvoc", GE_PER_KWH["nmvoc"], "kilogram", _LB),
        ("pm25",  GE_PER_KWH["pm25"], "kilogram", _LB),
        ("so2",   GE_PER_KWH["so2"], "kilogram", _LB),
    ],
)
# Left out of the dataset: CO2 0.0208 kg/MJ (replaced, check()); methane 4.98e-5 kg/MJ, "losses due to
# distribution in low pressure network" (high-pressure supply); its European gas; its three construction lines.

MAINT = Activity(
    code=R.GE_MAINT,
    name="Gas engine maintenance, per kWh run (ecoinvent 1 MW set's maintenance over 100,000 h)",
    reference_product="gas engine maintenance", unit="kilowatt hour", location="RER",
    comment="ecoinvent 3.9.1 '...unit construction, 1MW electrical, common components' carries 2.89 "
            "'maintenance, heat and power co-generation unit, 160kW electrical' per 1 MW set; charged here over "
            "the set's 100,000 running hours, less the maintenance visits' car trips (travel to site).",
    technosphere=[
        ("chp_maint", GE_MAINT_PER_KWH, "unit", "DERIVED - 2.89 per set / (1,000 kW x 100,000 h)"),
        ("car_rer",   -GE_MAINT_PER_KWH * CAR_KM_MAINT, "kilometer",
         "DERIVED - the maintenance's own 6,000 km of car trips per visit, taken back out: travel to site"),
    ],
)

PLANT = Activity(
    code=R.GE_PLANT,
    name="Gas engine plant, 1 MW built (ecoinvent 1 MW set, power parts, and a steel hall)",
    reference_product="gas engine plant, 1 MW", unit="unit", location="GB",
    comment="ecoinvent 3.9.1 '...unit construction, 1MW electrical' shared and electricity-only parts (RER), "
            "less the set's maintenance (charged per kWh, gas_engine_maintenance_1kwh) and its construction and "
            "start-up car trips (travel to site), plus a steel hall at ecoinvent's organic Rankine unit's "
            "500 m2 per 3 MW.",
    technosphere=[
        ("chp_common", 1.0, "unit", "ecoinvent set: engines, controls, sound insulation, air, site work, planning"),
        ("chp_elec",   1.0, "unit", "ecoinvent set: generators, electric parts, assembly"),
        ("chp_maint",  -CHP_MAINT_PER_SET, "unit", "DERIVED - the shared parts' 2.89 maintenance, moved to per kWh"),
        ("car_rer",    -GE_CAR_KM_TO_SITE_PER_SET, "kilometer",
         "DERIVED - 2.61 x (1,500 + 300) km of construction and start-up car trips, out: travel to site"),
        ("hall_steel", GE_HALL_M2_PER_MW, "square meter",
         "ecoinvent ORC 3 MW unit comment, 500 m2 per 3 MW - a stand-in"),
    ],
)
# Left out of the set: 'components for heat only' (hot-water storage, heating equipment, heat pump).

activities = [OP, MAINT, PLANT]


def inventory() -> Inventory:
    return Inventory(name="gas engines (ecoinvent lean-burn 1 MW, British gas)", database=R.GAS_ENGINE_DB,
                     processes=processes, flows=flows, activities=activities)


def describe() -> str:
    return (f"Gas engines at {GE_ETA_NET_LHV:.1%} net: {GE_GAS_M3_PER_KWH * 1000:.1f} m3 of British gas per MWh "
            f"({GE_GAS_MWH_HHV_PER_MWH:.3f} MWh gross); CO2 {GE_CO2_KG_PER_KWH * 1000:.1f} kg/MWh; methane "
            f"{GE_PER_KWH['ch4'] * 1000:.3f} kg/MWh; maintenance over {GE_UNIT_LIFE_H:,.0f} h; hall "
            f"{GE_HALL_M2_PER_MW:.1f} m2 per MW")
