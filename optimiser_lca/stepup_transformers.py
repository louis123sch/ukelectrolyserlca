"""
Generation step-up transformers — Leng et al. 2026 (wind), IEA PVPS 2026 (solar).
=============================================================================

Why this inventory exists
-------------------------
A wind turbine generates at **690 V**, which is *low* voltage (<1 kV, the band
ecoinvent itself draws). A PV inverter's terminals are 400 V. The data centre
draws at *medium* voltage, 1–24 kV, because that is the level ``market for
electricity, medium voltage`` describes and the level the Zhang foreground is
authored against. Something has to bridge those, and it is not optional:
100 MW at 690 V is 83,674 A, which is not a cable. So every turbine carries its
own transformer at the foot of its tower — one per turbine, not one per farm —
and every PV inverter station carries one.

**It is a gap, not a double count.** ecoinvent's ``wind turbine construction,
2MW, onshore`` lists its parts as "Rotor, Nacelle, Electronics, Tower,
Foundation"; its only electrical item is 438.7 kg of control electronics, an
order of magnitude short of the 3–5 t a 2 MW turbine transformer weighs, and
it says outright that it excludes the grid connection. Its network connection
dataset is cable and trench.

**And ecoinvent cannot supply the asset.** Its four transformer activities are
two products with a market and a production each, and both are *electronics*:
"a typical high voltage use transformer in electronic modules has an average
weight of 280 g … used in the information and communication technology" — and
30 g for the low-voltage one. There is no substation, switchgear or power
transformer dataset at any rating. Scaling a 280 g component up to stand for a
57 t substation unit is a factor of 205,000 and runs about 2× high. So both
transformers are assembled from a published bill of materials, the way the
hydrogen tank is.

Wind — Leng et al. 2026
-----------------------
    H. Leng, X. Zhou, J. Chen, D. Chen, M. Li, Y. Lin, Z. Yue, N. Zhong, "Life
    Cycle Assessment of an Onshore Wind Farm: Carbon Emission Evaluation and
    Mitigation Pathway Design", Processes 14(7), 1045 (2026), Supplementary
    Table S1. PowerChina Huadong Engineering.

Their Gaoyou farm is fifty 2 MW turbines, 100 MW, each with an S11-2200/35
box transformer; Table S1 gives the materials for all fifty as one bill.
Functional unit **1 MW of wind connected** = the bill ÷ 100, so it scales
exactly (one unit per turbine). Independently checked against Teffera et al.
(2021), Int J LCA 26:76–96, Table 5 — three Ethiopian farms, 228–333 kg
CO₂e/MW/year on this study's basis; Leng sits inside that band. Leng's units
are wound for 35 kV, above the medium-voltage band; a 20 kV unit of the same
rating is lighter, so their mass errs HIGH — the safe direction.

Solar — IEA PVPS Task 12, T12-33:2026
-------------------------------------
    M. Goetz, R. Deuber, N. Gazbour, P.H. Brailovsky, S. Nold, M.
    Marchand-Lasserre, R. Frischknecht, A.A. Khan, G. Bovo, M. Stucki (2026),
    "Life Cycle Inventories of Photovoltaic Systems", IEA PVPS Task 12, Report
    T12-33:2026, July 2026. DOI 10.69766/WJTE1771. Table 49 (the unit) and
    Table 50 (four of them per 10 MWp plant). Workbook shipped at
    optimisation/data/IEA-PVPS-T12-33-2026-LCI-PV-SupplyChains.xlsx.

The unit is wound **20 / 0.4 kV**, which is ``TX_SITE_COLLECTION_KV`` and the
inverter's LV terminals exactly, so no voltage adjustment is needed. The count
is *read off* Table 50 — "10 MW utility-scale electrical BoS including 4
units 2.5 MW transformers", 0.4 per MWp — which retires the DC/AC ratio and
power factor the old solar path assumed. The magnetic core is grain-oriented
electrical steel, which no LCI database carries; the report disaggregates it
into converter-route steel + MG-silicon + hot and cold rolling.

**A unit error in the source workbook, corrected.** The hardboard cell reads
36.96 m³ ≈ 47 tonnes, eight times the whole transformer. The report's own
total is ~5,680 kg; the transcribed materials sum to 5,633.04, leaving
46.9 kg = 0.03696 m³ at hardboard's ~1,270 kg/m³. So the cell is dm³
mislabelled as m³; ``check()`` guards the reconciliation.

What is deliberately NOT here (both): the grid-export transformer (this
study's generation is behind the meter; the grid intake is charged by
``grid_connection.py``); any step between the collection network and the data
centre (both sit in the medium-voltage band); switchgear, protection and
civils (absent from grid_connection.py too, so a level shift rather than a
bias); losses; end-of-life. **Manufacturing energy** is in the solar bill
(~6 % of it) and not in the wind one; materials-only the two land within 1 %.

What the optimiser reads: ``optimisation/transformers.py`` scores both
activities and amortises them over ``dc_config.TX_ASSET_LIFE_YEARS``.
"""
from __future__ import annotations

import math

from optimiser_lca import registry as R
from optimiser_lca.common import Activity, Inventory, Process

# =============================================================================
# Parameters — the voltage chain
# =============================================================================
TX_TURBINE_TERMINAL_V     = 690.0        # TRANSCRIBED - Teffera Table 2, all four models
TX_MEDIUM_VOLTAGE_BAND_KV = (1.0, 24.0)  # TRANSCRIBED - ecoinvent GB MV market comment
# ASSUMED. The site collects inside the band the data centre draws at, so the
# chain closes with no further transformation to charge.
TX_SITE_COLLECTION_KV = 20.0

# --- wind: Leng Table S1, box transformers, the whole population on one farm ---
TX_LENG_FARM_MW    = 100.0
TX_LENG_N_TURBINES = 50
TX_LENG_UNIT_MVA   = 2.2       # from the model number S11-2200/35
TX_LENG_BOX_KG = {             # TRANSCRIBED, kg for all fifty units
    "steel":  163_500.0,
    "iron":    53_300.0,
    "copper":  46_800.0,
    "oil":     17_600.0,
    "silica":   1_143.0,
}
TX_KG_PER_MW = {m: kg / TX_LENG_FARM_MW for m, kg in TX_LENG_BOX_KG.items()}
# Each Leng material -> the processes that make it. Steel and copper carry
# their forming step, as grid_connection.py's own rebuild does.
TX_MATERIAL_PROCESSES = {
    "steel":  ["steel_low_alloyed", "sheet_rolling_steel"],
    # ASSUMED: Leng lists Steel and Iron separately and does not say what the
    # second is. Read as core steel - a transformer contains no cast iron, and
    # Teffera's equivalent inventory is steel and copper only. Scoring it as
    # cast iron instead moves the answer ~4%.
    "iron":   ["steel_low_alloyed", "sheet_rolling_steel"],
    "copper": ["copper_cathode", "wire_drawing_copper"],
    "oil":    ["lubricating_oil"],
    # ASSUMED proxy: ecoinvent has no silicon dioxide market. 0.4% of the mass
    # and 0.005% of the carbon, so the choice does not matter.
    "silica": ["silica_sand"],
}

# --- solar: IEA PVPS T12-33:2026 Table 49, per ONE 2.5 MVA unit ------------------
UPV_TX_SOURCE = ("IEA PVPS Task 12, Report T12-33:2026 (July 2026), Tables 49 and 50")
UPV_TX_UNIT_MVA        = 2.5      # TRANSCRIBED - "oil-immersed, 2.5 MW"
UPV_TX_PRIMARY_KV      = 20.0     # TRANSCRIBED - voltage ratio 20/0.4 kV
UPV_TX_SECONDARY_KV    = 0.4      # TRANSCRIBED - inverter LV terminals
UPV_TX_REFERENCE_MWP   = 10.0     # TRANSCRIBED - the 10 MWp reference plant
UPV_TX_UNITS_PER_PLANT = 4        # TRANSCRIBED - Table 50 title, 4 x 2.5 MVA
UPV_TX_UNITS_PER_MWP   = UPV_TX_UNITS_PER_PLANT / UPV_TX_REFERENCE_MWP   # read off, not derived
UPV_TX_MATERIALS_KG = {           # TRANSCRIBED except where noted
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
# Hardboard pressboard: the workbook's 36.96 m3 is dm3 mislabelled (see docstring).
UPV_TX_FIBREBOARD_M3   = 0.03696   # DERIVED, checked by check()
UPV_TX_FIBREBOARD_KG   = 46.9      # only used to reconcile the stated total
UPV_TX_STATED_TOTAL_KG = 5_680.0   # TRANSCRIBED - the report's own figure
# Forming and process energy, per unit. Rolling and metal-working rows are
# FORMING of mass already counted, held apart so they are never summed into it.
UPV_TX_FORMING_KG = {
    "hot_rolling":         2_153.0,   # = core mass, hot rolled
    "sheet_rolling_steel": 4_306.0,   # = core mass rolled twice (hot then cold)
    "sheet_rolling_alu":     618.0,   # = the aluminium winding
    "alu_metalworking":      618.0,
}
UPV_TX_ELECTRICITY_KWH = 2_368.3
UPV_TX_HEAT_MJ         = 9_903.8


def check() -> str:
    """The transcribed bills must rebuild their sources' own stated masses,
    and the voltage chain must close inside the medium-voltage band."""
    lo, hi = TX_MEDIUM_VOLTAGE_BAND_KV
    if not (lo <= TX_SITE_COLLECTION_KV <= hi):
        raise AssertionError(
            f"TX_SITE_COLLECTION_KV={TX_SITE_COLLECTION_KV} kV is outside the medium-voltage "
            f"band {TX_MEDIUM_VOLTAGE_BAND_KV} the data centre draws at")
    if abs(UPV_TX_PRIMARY_KV - TX_SITE_COLLECTION_KV) > 1e-9:
        raise AssertionError(
            f"the IEA PVPS unit is wound {UPV_TX_PRIMARY_KV:g}/{UPV_TX_SECONDARY_KV:g} kV but "
            f"the site collects at {TX_SITE_COLLECTION_KV:g} kV - one of them has moved")
    mass = sum(UPV_TX_MATERIALS_KG.values()) + UPV_TX_FIBREBOARD_KG
    if abs(mass - UPV_TX_STATED_TOTAL_KG) > 1.0:
        raise AssertionError(
            f"UPV transformer bill sums to {mass:,.2f} kg against the report's stated "
            f"{UPV_TX_STATED_TOTAL_KG:,.0f} kg per unit")
    for key in list(UPV_TX_MATERIALS_KG) + list(UPV_TX_FORMING_KG):
        if "upv_" + key not in processes:
            raise AssertionError(f"no ecoinvent process mapped for UPV transformer row {key!r}")
    for m, procs in TX_MATERIAL_PROCESSES.items():
        for p in procs:
            if p not in processes:
                raise AssertionError(f"no ecoinvent process {p!r} for Leng material {m!r}")
    return (f"OK - wind {sum(TX_KG_PER_MW.values()):,.0f} kg/MW; solar {mass:,.0f} kg per "
            f"{UPV_TX_UNIT_MVA:g} MVA unit, {UPV_TX_UNITS_PER_MWP:g} units/MWp; "
            f"site collects at {TX_SITE_COLLECTION_KV:g} kV")


def amps(mw: float, volts: float) -> float:
    """Three-phase current - why the step-up is not optional."""
    return mw * 1e6 / (math.sqrt(3) * volts)


# =============================================================================
# Processes
# =============================================================================
_kg = "kilogram"
processes = {
    # --- wind (Leng) ------------------------------------------------------------
    "steel_low_alloyed":   Process(identity=("market for steel, low-alloyed", "GLO"), unit=_kg,
                                   query="market for steel low-alloyed GLO"),
    "sheet_rolling_steel": Process(identity=("market for sheet rolling, steel", "GLO"), unit=_kg,
                                   query="market for sheet rolling steel GLO"),
    "copper_cathode":      Process(identity=("market for copper, cathode", "GLO"), unit=_kg,
                                   query="market for copper cathode GLO"),
    "wire_drawing_copper": Process(identity=("market for wire drawing, copper", "GLO"), unit=_kg,
                                   query="market for wire drawing copper GLO"),
    "lubricating_oil":     Process(identity=("market for lubricating oil", "RER"), unit=_kg,
                                   query="market for lubricating oil RER"),
    "silica_sand":         Process(identity=("market for silica sand", "GLO"), unit=_kg,
                                   query="market for silica sand GLO"),
    # --- solar (IEA PVPS Table 49), one per row, locations pinned ----------------
    "upv_steel_converter":     Process(identity=("steel production, converter, unalloyed", "RER"), unit=_kg,
                                       query="steel production converter unalloyed RER",
                                       why="GOES core base metal; converter route because GOES composition "
                                           "limits cannot be met from scrap (the report's own reasoning)"),
    "upv_mg_silicon":          Process(identity=("market for silicon, metallurgical grade", "GLO"), unit=_kg,
                                       query="market for silicon metallurgical grade GLO"),
    "upv_oil":                 Process(identity=("market for lubricating oil", "RER"), unit=_kg,
                                       query="market for lubricating oil RER"),
    "upv_aluminium":           Process(identity=("market for aluminium, wrought alloy", "GLO"), unit=_kg,
                                       query="market for aluminium wrought alloy GLO"),
    "upv_steel_lowalloy":      Process(identity=("market for steel, low-alloyed", "GLO"), unit=_kg,
                                       query="market for steel low-alloyed GLO"),
    "upv_kraft_paper":         Process(identity=("market for kraft paper", "RER"), unit=_kg,
                                       query="market for kraft paper RER",
                                       why="ASSUMED proxy: no unbleached kraft paper in ecoinvent; average "
                                           "kraft is slightly the more burdened, 34 kg of 5,680"),
    "upv_epoxy":               Process(identity=("market for epoxy resin, liquid", "RER"), unit=_kg,
                                       query="market for epoxy resin liquid RER"),
    "upv_copper":              Process(identity=("market for copper, cathode", "GLO"), unit=_kg,
                                       query="market for copper cathode GLO"),
    "upv_chromium_steel":      Process(identity=("market for steel, chromium steel 18/8", "GLO"), unit=_kg,
                                       query="market for steel chromium steel 18/8 GLO"),
    "upv_rubber":              Process(identity=("market for synthetic rubber", "GLO"), unit=_kg,
                                       query="market for synthetic rubber GLO"),
    "upv_paint":               Process(identity=("market for alkyd paint, white, without water, in 60% solution state", "RER"),
                                       unit=_kg, query="market for alkyd paint white RER"),
    "upv_hot_rolling":         Process(identity=("market for hot rolling, steel", "GLO"), unit=_kg,
                                       query="market for hot rolling steel GLO"),
    "upv_sheet_rolling_steel": Process(identity=("market for sheet rolling, steel", "GLO"), unit=_kg,
                                       query="market for sheet rolling steel GLO"),
    "upv_sheet_rolling_alu":   Process(identity=("market for sheet rolling, aluminium", "GLO"), unit=_kg,
                                       query="market for sheet rolling aluminium GLO"),
    "upv_alu_metalworking":    Process(identity=("market for metal working, average for aluminium product manufacturing", "GLO"),
                                       unit=_kg, query="market for metal working average aluminium GLO"),
    "upv_fibreboard":          Process(identity=("market for fibreboard, hard", "RER"), unit="cubic meter",
                                       query="market for fibreboard hard RER"),
    # GB rather than the source's ENTSO-E: the factory is not the point, and
    # this study is GB throughout. Moves the answer <1 % (process energy is 6 %).
    "upv_electricity":         Process(identity=("market for electricity, medium voltage", "GB"), unit="kilowatt hour",
                                       query="market for electricity medium voltage GB"),
    "upv_heat":                Process(identity=("heat production, natural gas, at industrial furnace >100kW",
                                                 "Europe without Switzerland"), unit="megajoule",
                                       query="heat production natural gas industrial furnace >100kW"),
}
flows = {}

check()

# =============================================================================
# Activities
# =============================================================================
_wind_exchanges = []
for _material, _kg_per_mw in TX_KG_PER_MW.items():
    for _p in TX_MATERIAL_PROCESSES[_material]:
        _wind_exchanges.append((_p, _kg_per_mw, _kg,
                                f"{_material} in the turbine step-up transformers — "
                                f"Leng Table S1, {TX_LENG_BOX_KG[_material]:,.0f} kg per "
                                f"{TX_LENG_FARM_MW:.0f} MW farm"))

_per_mwp = UPV_TX_UNITS_PER_MWP


def _solar_row(key, amount_per_unit, unit, note):
    return ("upv_" + key, amount_per_unit * _per_mwp, unit,
            f"{note} - IEA PVPS T12-33:2026 Table 49, {amount_per_unit:,.3f} per "
            f"{UPV_TX_UNIT_MVA:g} MVA unit x {_per_mwp:g} units/MWp")


_solar_exchanges = (
    [_solar_row(k, kg, _kg, f"{k} in the solar inverter-station step-ups")
     for k, kg in UPV_TX_MATERIALS_KG.items()]
    + [_solar_row("fibreboard", UPV_TX_FIBREBOARD_M3, "cubic meter",
                  "hardboard pressboard (workbook 36.96 m3 corrected to dm3; see docstring)")]
    + [_solar_row(k, kg, _kg, f"{k}, forming of mass already counted")
       for k, kg in UPV_TX_FORMING_KG.items()]
    + [_solar_row("electricity", UPV_TX_ELECTRICITY_KWH, "kilowatt hour", "factory electricity"),
       _solar_row("heat", UPV_TX_HEAT_MJ, "megajoule", "factory heat")]
)

activities = [
    Activity(
        code=R.TX_WIND,
        name="Wind turbine step-up transformers, per MW of wind connected",
        reference_product="wind turbine step-up transformer capacity",
        unit="megawatt", location="GLO",
        comment=(
            "The transformers at the foot of each turbine tower, which step 690 V "
            "(LOW, <1 kV) up to the site collection voltage so the data centre can "
            "draw at MEDIUM voltage (1-24 kV). One unit per TURBINE, not one per "
            "farm. Not optional: 100 MW at 690 V is 83,674 A. "
            "ecoinvent 3.9.1 has no power transformer at any rating - its four "
            "transformer activities are two electronic components of 280 g and 30 g "
            "average weight, by its own comments - and its wind turbine dataset "
            "lists its parts as Rotor/Nacelle/Electronics/Tower/Foundation with no "
            "transformer among them, its only electrical item being 438.7 kg of "
            "control electronics. So this is assembled from "
            "Leng et al. (2026), Processes 14(7) 1045, Supplementary Table S1: the "
            f"{TX_LENG_N_TURBINES} x {TX_LENG_UNIT_MVA:g} MVA S11-2200/35 box "
            f"transformers on their {TX_LENG_FARM_MW:.0f} MW Gaoyou farm, "
            f"{sum(TX_LENG_BOX_KG.values()):,.0f} kg in total, divided by the farm. "
            "Cross-checked against Teffera et al. (2021) Int J LCA 26:76-96 Table 5, "
            "which lands within the same band by a different route. "
            "Functional unit is 1 MW of wind CONNECTED - amortise over "
            "TX_ASSET_LIFE_YEARS (dc_config). "
            "EXCLUDES: the grid-export transformer (this study is behind the meter, "
            "there is nothing to export into, and the grid intake is charged by "
            "grid_connection.py); any step between the collection network and the "
            "data centre (both sit in the medium-voltage band); switchgear, "
            "protection and civils; manufacturing energy, which Leng include and "
            "this does not, making this the lower of the two; losses; end-of-life."
        ),
        technosphere=_wind_exchanges,
    ),
    Activity(
        code=R.TX_SOLAR,
        name="Solar inverter-station step-up transformers, per MWp of PV connected",
        reference_product="solar inverter-station step-up transformer capacity",
        unit="megawatt", location="GLO",
        comment=(
            "The oil-immersed transformers in a utility PV plant's inverter stations, "
            "stepping the inverters' 400 V (LOW, <1 kV) up to the site collection "
            "voltage so the data centre can draw at MEDIUM voltage (1-24 kV). The "
            f"source unit is wound {UPV_TX_PRIMARY_KV:g}/{UPV_TX_SECONDARY_KV:g} kV, "
            f"which is TX_SITE_COLLECTION_KV ({TX_SITE_COLLECTION_KV:g} kV) exactly, "
            "so no voltage adjustment is applied - unlike the wind units, which are "
            "wound for 35 kV and whose mass therefore errs high. "
            "ecoinvent 3.9.1 has no power transformer at any rating, so this is "
            "assembled from a published bill of materials: "
            f"{UPV_TX_SOURCE}. Table 49 gives one "
            f"{UPV_TX_UNIT_MVA:g} MVA unit at {UPV_TX_STATED_TOTAL_KG:,.0f} kg; "
            f"Table 50 puts {UPV_TX_UNITS_PER_PLANT} of them on the "
            f"{UPV_TX_REFERENCE_MWP:.0f} MWp reference plant, so the count is READ "
            f"OFF at {UPV_TX_UNITS_PER_MWP:g} units/MWp rather than derived - which "
            "retires the ASSUMED SOLAR_DC_AC_RATIO and POWER_FACTOR the old path "
            "needed. The magnetic core is grain-oriented electrical steel, "
            "disaggregated by the source into converter-route steel + MG-silicon + "
            "hot and cold rolling because no LCI database carries a GOES dataset. "
            "The workbook's 36.96 m3 hardboard cell is out by 1000x and is corrected "
            "to 0.03696 m3; the corrected bill reconciles to the report's own stated "
            "unit mass to three significant figures (stepup_transformers.check). "
            "Functional unit is 1 MWp of PV CONNECTED - amortise over "
            "TX_ASSET_LIFE_YEARS (dc_config). "
            "INCLUDES factory electricity and heat, which the wind bill does not - "
            "process energy is ~6% here, so materials-only the two land within 1% of "
            "each other; the asymmetry is stated in SOURCES.md. "
            "EXCLUDES: the grid-export transformer (behind the meter); any step "
            "between collection and the data centre (both medium voltage); "
            "switchgear, protection and civils; losses; end-of-life."
        ),
        technosphere=_solar_exchanges,
    ),
]


def inventory() -> Inventory:
    return Inventory(name="step-up transformers (Leng 2026 wind, IEA PVPS 2026 solar)",
                     database=R.TRANSFORMER_DB, processes=processes, flows=flows,
                     activities=activities)


def describe() -> str:
    mass_unit = sum(UPV_TX_MATERIALS_KG.values()) + UPV_TX_FIBREBOARD_KG
    return "\n".join([
        f"Wind: Leng et al. 2026, {TX_LENG_N_TURBINES} x {TX_LENG_UNIT_MVA:g} MVA on a "
        f"{TX_LENG_FARM_MW:.0f} MW farm -> {sum(TX_KG_PER_MW.values()):,.0f} kg/MW",
        f"  turbines at {TX_TURBINE_TERMINAL_V:.0f} V: {amps(TX_LENG_FARM_MW, TX_TURBINE_TERMINAL_V):,.0f} A "
        f"for 100 MW; at {TX_SITE_COLLECTION_KV:g} kV: {amps(TX_LENG_FARM_MW, TX_SITE_COLLECTION_KV * 1e3):,.0f} A",
        f"Solar: {UPV_TX_SOURCE}",
        f"  {UPV_TX_UNITS_PER_PLANT} x {UPV_TX_UNIT_MVA:g} MVA units on {UPV_TX_REFERENCE_MWP:.0f} MWp "
        f"-> {UPV_TX_UNITS_PER_MWP:g}/MWp; {mass_unit:,.0f} kg/unit -> {mass_unit * UPV_TX_UNITS_PER_MWP:,.0f} kg/MWp",
        f"  inverters at {UPV_TX_SECONDARY_KV * 1000:.0f} V: {amps(UPV_TX_UNIT_MVA, UPV_TX_SECONDARY_KV * 1e3):,.0f} A "
        f"per unit; at {UPV_TX_PRIMARY_KV:g} kV: {amps(UPV_TX_UNIT_MVA, UPV_TX_PRIMARY_KV * 1e3):,.0f} A",
        "Amortised over TX_ASSET_LIFE_YEARS in optimisation/transformers.py, not here.",
    ])
