"""
Power transformers — Leng et al. 2026 (wind step-ups and the grid intake),
IEA PVPS 2026 (solar step-ups).
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
57 t substation unit is a factor of 205,000 and runs about 2× high. So all
three transformers here — the two generation step-ups and the grid intake —
are assembled from a published bill of materials, the way the hydrogen tank
is, and nothing in the optimiser's default path scores ecoinvent's transformer
any more (only ``transformers.SOLAR_BASIS = "legacy"`` still does, to
reproduce pre-2026 runs).

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
36.96 with unit m³ ≈ 47 tonnes, eight times the whole transformer. Its own
comment reads "Al × 0.115 × 0.52 = 36.96 kg", and the end-of-life sheet's
paper row is 71.07 kg = 34.11 kraft + 36.96 pressboard, so the cell is kg
mislabelled as m³: 36.96 kg = 0.0291 m³ at hardboard's ~1,270 kg/m³. The bill
then sums to 5,670.0 kg against the report's "approximately 5,680";
``check()`` holds it within 0.5 %. (Until 21 Oct 2026 the row was back-solved
to 46.9 kg to hit 5,680 exactly, which reconciled on the wrong lever.)

Grid intake — Leng et al. 2026, the farm's main transformer
-----------------------------------------------------------
The same Table S1 also bills the Gaoyou farm's grid-end **main transformer,
XZ11-100000/110**: one 100 MVA unit stepping the 35 kV collection bus up to
110 kV, 71,458.6 kg = 714.6 kg/MVA. That is the only published bill of
materials in this study for a transformer of grid-intake class, so it is the
basis of ``cap_grid``'s embodied carbon: functional unit **1 MVA of
grid-intake transformer capacity** = the bill ÷ 100, mapped through the same
``TX_MATERIAL_PROCESSES`` as the wind units (the "Iron" reading is the same
judgement). ``optimisation/grid_connection.py`` scores it, applies N-1
redundancy and the power factor, and amortises it.

**The voltage judgement.** A 110 kV unit fits a GB **132 kV** EHV/DNO
connection, which is the common case for a ~100 MW data centre. For a site
connected at **275/400 kV** it errs LOW: supergrid transformers carry more
insulation and are heavier per MVA. Leng's unit is used for every site as the
default; it is stated in DATA_GAPS.md rather than varied by voltage.

**Materials only, because that is all Leng publish.** Their Table S1 is a
materials bill, S2 is transport and S3 is civils; no factory energy appears
for either transformer (checked against the SI and main text, 21 Oct 2026).
Their own 342 t CO₂e for this unit against ~275 t here is a scoring
difference — ecoinvent 3.11 with RoW steel proxies against 3.9.1 apos GLO
markets — not a dropped flow. The civils and installation Leng attribute to
the transformers (Table S3) are in: the box-transformer foundations (21 Oct)
and the electrical installation (section steel, terminal blocks, welding rod,
lead seals; 22 Oct) on the wind step-ups, per MW of the farm; the booster
station's **outdoor venue** — the 110 kV switchyard's site formation,
foundation beams, formwork, concrete, water and rebar, Leng's own 34.4 % of
the station — as its own activity per MW of connection (decision D2,
22 Oct 2026: the station serves 100 MW through one transformer, so its yard
scales with the connection, not the MVA). The station's three *buildings*
(control, auxiliary, production: 64.7 %) are treated as covered by Zhang's
facility building, which already houses the data centre's electrical rooms —
a stated substitution, not an omission. The station-wide construction
machinery (0.9 %) is listed once for all four projects, so its share is
pro-rated to the switchyard from Leng's own figure and carried on the
connection's coefficient (``exclusions.py``).

Battery and fuel cell — Jasper et al. 2026's mass on the IEA composition
-------------------------------------------------------------------------
A battery's PCS and a fuel cell's inverters put out LOW voltage too, so each
container needs the same LV → 20 kV step. Jasper et al. (2026)'s liquid-cooled
CSS bill (``bess.py``) lists one "transformer, for grid connection" of
**5,500 kg per 1,600 kW container**. That mass is spread over the IEA PVPS
20/0.4 kV unit's composition, forming and factory energy per kg.

**A stated substitution, on technological representativeness** (22 Oct 2026).
Jasper do give a per-kg recipe (air-cooled sheet rows 225–236; until 21 Oct
this module wrongly said they did not). Their §2.4.3 says it is derived from
Hunziker et al. (2020): a **630 kVA** line-frequency transformer with an
**on-load tap changer**, scaled by mass to the 1,800 kVA unit the container
needs. The IEA unit is a current **2,500 kVA, 20/0.4 kV oil-immersed
distribution transformer**, built from product documentation, at exactly the
step the container makes. The parent source's recipe is set aside because it
represents a different machine, not because it is missing. Jasper's recipe
scores 7.85 kg CO₂e/kg against 4.57 here (+72 %), most of the gap being its
0.09 kg/kg of control electronics, plausibly the tap changer's; it is carried
as the sensitivity case (SOURCES.md). Hunziker 2020 is not held, so the link
between the tap changer and the electronics row is inferred.

One activity, **per MW of inverter rating**, serves the
battery (``cap_batt_p``) and the fuel cell (``cap_fc``; one container of
``fuel_cell.FC_KW_PER_CONTAINER`` with the same 500 kW inverters), each
amortised over the asset's own life. Closed as negligible on 4 Sep 2026 and
modelled on 15 Oct: once the inventory and loss machinery existed, leaving
them out was a one-way bias against the generation chains, which pay for
theirs.

What is deliberately NOT here (all four): the grid-*export* transformer
charged to generation (this study's generation is behind the meter; Leng's
grid-end unit is used for the grid *intake* instead, charged per MW of
``cap_grid`` by ``grid_connection.py``); any step between the collection
network and the data centre (both sit in the medium-voltage band); switchgear
and protection (absent from the grid intake too, so a level shift rather than
a bias); losses; end-of-life. **Manufacturing energy** is in the solar bill
(~6 % of it) and in neither Leng bill, because Leng do not publish it;
materials-only wind and solar land within 1 %. **Civils**: the wind units
carry Leng's box-transformer foundations and the solar units the IEA PVPS
transformer station building, both since 21 Oct 2026.

What the optimiser reads: ``optimisation/transformers.py`` scores the two
step-ups and amortises them over ``dc_config.TX_ASSET_LIFE_YEARS``;
``optimisation/grid_connection.py`` scores the grid intake and amortises it
over its own ``ASSET_LIFE_YEARS``.
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
TX_LENG_FARM_MW    = 100.0     # TRANSCRIBED - Gaoyou, fifty 2 MW turbines
TX_LENG_N_TURBINES = 50        # TRANSCRIBED
TX_LENG_UNIT_MVA   = 2.2       # TRANSCRIBED - from the model number S11-2200/35 (the main text's 3,500 kVA is a slip)
TX_LENG_BOX_KG = {             # TRANSCRIBED, kg for all fifty units
    "steel":  163_500.0,
    "iron":    53_300.0,
    "copper":  46_800.0,
    "oil":     17_600.0,
    "silica":   1_143.0,
}
TX_KG_PER_MW = {m: kg / TX_LENG_FARM_MW for m, kg in TX_LENG_BOX_KG.items()}

# --- grid intake: Leng Table S1, the farm's main transformer XZ11-100000/110 ----
TX_LENG_MAIN_MVA = 100.0       # TRANSCRIBED - from the model number XZ11-100000/110 (kVA / kV)
TX_LENG_MAIN_KV  = 110.0       # TRANSCRIBED - from the same model number, the HV winding
TX_LENG_MAIN_KG = {            # TRANSCRIBED, kg for the one unit (t x 1000)
    "steel":  30_200.0,
    "iron":   20_800.0,
    "copper": 16_800.0,
    "oil":     3_430.0,
    "silica":    228.6,        # printed in kg, not t
}
TX_LENG_MAIN_STATED_KG = 71_458.6   # DERIVED - the five Table S1 rows summed by hand
                                    # from the PDF; check() holds the dict to it
TX_GRID_KG_PER_MVA = {m: kg / TX_LENG_MAIN_MVA for m, kg in TX_LENG_MAIN_KG.items()}

# Each Leng material -> the processes that make it. Steel and copper carry
# their forming step. Used for both Leng bills, box and main.
TX_MATERIAL_PROCESSES = {
    "steel":  ["steel_low_alloyed", "sheet_rolling_steel"],
    # ASSUMED: Leng list Steel and Iron separately; their own Table S5 files the
    # iron as cast iron. Read here as core steel - a transformer contains no cast
    # iron, and Teffera's equivalent inventory is steel, copper and aluminium - a
    # stated departure from the source's treatment. Scoring it as cast iron
    # instead moves the answer ~4%.
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
# Hardboard pressboard: the workbook's "36.96 m3" is 36.96 kg mislabelled (its
# own cell comment and the EoL sheet both say kg; see docstring).
UPV_TX_FIBREBOARD_KG   = 36.96     # TRANSCRIBED, from the cell's comment
UPV_TX_FIBREBOARD_DENSITY_KG_M3 = 1_270.0   # hardboard, ASSUMED
UPV_TX_FIBREBOARD_M3   = UPV_TX_FIBREBOARD_KG / UPV_TX_FIBREBOARD_DENSITY_KG_M3   # 0.0291, the row's unit
UPV_TX_STATED_TOTAL_KG = 5_680.0   # TRANSCRIBED - the report's "approximately 5680"; the bill sums to 5,670.0
UPV_TX_TOTAL_TOLERANCE = 0.005     # check(): within 0.5 % of the rounded figure
# Forming and process energy, per unit. Rolling and metal-working rows are
# FORMING of mass already counted, held apart so they are never summed into it. TRANSCRIBED.
UPV_TX_FORMING_KG = {
    "hot_rolling":         2_153.0,   # = core mass, hot rolled
    "sheet_rolling_steel": 4_306.0,   # = core mass rolled twice (hot then cold)
    "sheet_rolling_alu":     618.0,   # = the aluminium winding
    "alu_metalworking":      618.0,
}
UPV_TX_ELECTRICITY_KWH = 2_368.3   # TRANSCRIBED - Table 49 (the printed '2.37E+0' is a slip; the workbook has 2,368.3)
UPV_TX_HEAT_MJ         = 9_903.8   # TRANSCRIBED - Table 49
# Smith 2024 Table A15 replaces 1.30E-05 transformers per m2 over 30 years
# against 4.30E-05 installed (A14): 30.2 % of the fleet. The same ratio
# upv.UPV_PV_OM_REPLACEMENT_FRACTION applies to the inverters in the same row;
# until 21 Oct 2026 the transformer half was dropped when A11 was substituted.
# Carried as its own 30-year activity, like upv's O&M, so transformers.py can
# charge it per year whatever life the unit itself is amortised over.
UPV_TX_REPLACEMENT_FRACTION_30Y = 1.30e-5 / 4.30e-5
UPV_TX_REPLACEMENT_REFERENCE_YEARS = 30.0   # TRANSCRIBED - Smith A15's horizon

# --- battery and fuel cell: the containerised LV step-up, Jasper's mass on the IEA unit ---
CSS_TX_SOURCE    = "Jasper et al. 2026, CSS (liquid cooled) bill, 'transformer, for grid connection'"
CSS_TX_KG        = 5_500.0     # TRANSCRIBED - one unit per container; check() holds it to bess.CSS_EXCLUDED
CSS_TX_KW        = 1_600.0     # TRANSCRIBED - the container's PCS rating, bess.CSS_KW
CSS_TX_KG_PER_MW = CSS_TX_KG / CSS_TX_KW * 1000.0
# The composition is per kg of the IEA unit, so every Table 49 row is scaled by
# the mass ratio: how many of that unit one MW of container step-up weighs. On
# the transcribed bill's own sum (5,670.0 kg), not the report's rounded 5,680,
# so per kg the two activities score identically.
UPV_TX_BILL_KG = sum(UPV_TX_MATERIALS_KG.values()) + UPV_TX_FIBREBOARD_KG
CSS_TX_UNITS_PER_MW = CSS_TX_KG_PER_MW / UPV_TX_BILL_KG

TX_SCOPE = {
    "wind_step_up": "INCLUDED - Leng Table S1's fifty box transformers per 100 MW, their pads (S3) and "
                    "electrical installation (S3); no factory energy, because Leng publish none.",
    "solar_step_up": "INCLUDED - IEA PVPS Table 49's unit, its forming and factory energy, Z-PV-238's "
                     "station building, and Smith A15's 30-year replacements.",
    "grid_intake": "INCLUDED - Leng's main transformer per MVA (materials only) and the switchyard's civils "
                   "per MW of connection (S3 outdoor venue, D2).",
    "container_step_up": "SUBSTITUTED - Jasper's 5,500 kg on the IEA unit's composition; Jasper's own "
                         "Hunziker-derived recipe is the sensitivity (representativeness, 22 Oct 2026).",
    "buildings": "SUBSTITUTED - the booster station's control, auxiliary and production buildings (Leng S3, "
                 "64.7 % of the station) are covered by Zhang's facility building, not charged twice.",
    "machinery": "INCLUDED - the booster station's construction machinery (0.9 % of the station) is listed "
                 "station-wide, so Leng's own figure for it is pro-rated to the venue (34.4 %) and carried on the "
                 "connection's coefficient (exclusions.py).",
    "switchgear": "EXCLUDED - switchgear and protection at every transformer: no source itemises them; on "
                  "the cut-off register (exclusions.py).",
    "losses": "Charged as energy in the LP (conversion_losses.py), not here.",
    "end_of_life": "EXCLUDED, as everywhere else in this study.",
    "delivery": "EXCLUDED - Leng Table S2's legs to site and IEA's to the construction place: delivery to "
                "site, outside the boundary.",
}


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
    if abs(mass - UPV_TX_STATED_TOTAL_KG) > UPV_TX_TOTAL_TOLERANCE * UPV_TX_STATED_TOTAL_KG:
        raise AssertionError(
            f"UPV transformer bill sums to {mass:,.2f} kg against the report's stated "
            f"~{UPV_TX_STATED_TOTAL_KG:,.0f} kg per unit")
    for key in list(UPV_TX_MATERIALS_KG) + list(UPV_TX_FORMING_KG):
        if "upv_" + key not in processes:
            raise AssertionError(f"no ecoinvent process mapped for UPV transformer row {key!r}")
    for m, procs in TX_MATERIAL_PROCESSES.items():
        for p in procs:
            if p not in processes:
                raise AssertionError(f"no ecoinvent process {p!r} for Leng material {m!r}")
    main = sum(TX_LENG_MAIN_KG.values())
    if abs(main - TX_LENG_MAIN_STATED_KG) > 1e-6:
        raise AssertionError(
            f"Leng main-transformer bill sums to {main:,.1f} kg against the "
            f"{TX_LENG_MAIN_STATED_KG:,.1f} kg of Table S1's five rows")
    for bill, label in ((TX_LENG_BOX_KG, "box"), (TX_LENG_MAIN_KG, "main")):
        unmapped = set(bill) - set(TX_MATERIAL_PROCESSES)
        if unmapped:
            raise AssertionError(f"Leng {label} transformer rows {sorted(unmapped)} have no process")
    # The container step-up's mass and rating are Jasper's, read from the battery
    # inventory's own excluded-rows table, so the two modules cannot drift apart.
    from optimiser_lca import bess
    jasper_kg = bess.CSS_EXCLUDED["transformer, for grid connection"][0]
    if abs(jasper_kg - CSS_TX_KG) > 1e-9 or abs(bess.CSS_KW - CSS_TX_KW) > 1e-9:
        raise AssertionError(
            f"the containerised step-up reads {CSS_TX_KG:,.0f} kg per {CSS_TX_KW:,.0f} kW but "
            f"bess.py's Jasper bill says {jasper_kg:,.0f} kg per {bess.CSS_KW:,.0f} kW")
    return (f"OK - wind {sum(TX_KG_PER_MW.values()):,.0f} kg/MW; solar {mass:,.0f} kg per "
            f"{UPV_TX_UNIT_MVA:g} MVA unit, {UPV_TX_UNITS_PER_MWP:g} units/MWp; "
            f"grid intake {main / TX_LENG_MAIN_MVA:,.1f} kg/MVA; "
            f"container step-up {CSS_TX_KG_PER_MW:,.1f} kg/MW; "
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
    # --- civils, in since 21 Oct 2026: Leng Table S3 box-transformer foundations
    #     (wind) and IEA PVPS Z-PV-238's transformer station building (solar) ---
    "excavation":              Process(identity=("market for excavation, hydraulic digger", "GLO"), unit="cubic meter",
                                       query="market for excavation hydraulic digger GLO"),
    "concrete_20mpa":          Process(identity=("market for concrete, 20MPa", "RoW"), unit="cubic meter",
                                       query="market for concrete 20MPa RoW",
                                       why="Leng's C15 cushion concrete; 20 MPa is the nearest grade in 3.9.1"),
    "concrete_normal":         Process(identity=("market for concrete, normal strength", "RoW"), unit="cubic meter",
                                       query="market for concrete normal strength RoW",
                                       why="Leng's C30 cushion concrete"),
    "reinforcing_steel_glo":   Process(identity=("market for reinforcing steel", "GLO"), unit=_kg,
                                       query="market for reinforcing steel GLO"),
    "diesel_building_machine": Process(identity=("market for diesel, burned in building machine", "GLO"),
                                       unit="megajoule", query="market for diesel burned in building machine GLO"),
    "building_hall":           Process(identity=("market for building, hall, steel construction", "GLO"),
                                       unit="square meter", query="market for building hall steel construction GLO"),
    # --- Leng Table S3 electrical installation and the booster station's outdoor venue (22 Oct 2026) ---
    "lead":                    Process(identity=("market for lead", "GLO"), unit=_kg, query="market for lead GLO",
                                       why="Leng's 'lead seal' row"),
    "wire_drawing_steel":      Process(identity=("market for wire drawing, steel", "GLO"), unit=_kg,
                                       query="market for wire drawing steel GLO", why="the venue's iron wire, drawn"),
    "tap_water_row":           Process(identity=("market for tap water", "RoW"), unit=_kg,
                                       query="market for tap water RoW", why="the venue's construction water"),
    "sawnwood_board":          Process(identity=("market for sawnwood, board, softwood, raw, dried (u=20%)",
                                                 "Europe without Switzerland"), unit="cubic meter",
                                       query="market for sawnwood board softwood raw dried",
                                       why="Leng's 'board material' for the formwork; softwood board is the nearest dataset"),
}

# Leng Table S3, "Transformer substation foundation project" under wind-turbine
# engineering: the pads the fifty box transformers stand on (main text §2.3,
# "installed on ... concrete foundations"). Per 100 MW farm, TRANSCRIBED. The
# machinery column gives machine-teams x a rating: Eq. (S2) states the truck's
# rating in litres of diesel per team (TRANSCRIBED); the welder's is read as kWh
# per team (ASSUMED). 35.95 MJ per litre.
TX_LENG_PAD_PER_FARM = {
    "excavation_m3": 728.0, "concrete_c15_m3": 56.0, "concrete_c30_m3": 280.0,
    "rebar_kg": 19_600.0, "welding_kwh": 2.5 * 60.27, "truck_diesel_l": 202.5 * 32.19,
}
DIESEL_MJ_PER_L = 0.84 * 42.8        # conversion: 0.84 kg/l x 42.8 MJ/kg
# Leng Table S3 "electrical installation" under wind-turbine engineering, per
# 100 MW farm, TRANSCRIBED. Left behind by the 21 Oct restore; in since 22 Oct 2026.
TX_LENG_INSTALLATION_PER_FARM = {
    "section_steel_kg": 261.0, "terminal_block_kg": 375.0, "welding_rod_kg": 18.0, "lead_seal_kg": 114.15,
}
# Leng Table S3 "outdoor venue project": the 110 kV booster station's switchyard,
# per 100 MW farm, TRANSCRIBED (its own nine-row block; 34.4 % of the station's
# carbon in Leng's Fig. 9c). Taken per MW of connection (decision D2).
TX_LENG_VENUE_PER_FARM = {
    "site_formation_m3": 23_650.0, "foundation_beam_m3": 30.0, "steel_formwork_kg": 13_659.0,
    "board_m3": 19.1, "iron_nails_kg": 257.5, "iron_wire_kg": 301.0, "concrete_m3": 896.1,
    "water_m3": 1_218.0, "rebar_kg": 12_000.0,
}
VENUE_BEAM_REBAR_FRACTION = 0.03     # ASSUMED - midpoint of Leng's "1-6 % reinforcement" for foundation beams
STEEL_KG_PER_M3 = 7_850.0            # physical constant
_pad = {k: v / TX_LENG_FARM_MW for k, v in TX_LENG_PAD_PER_FARM.items()}   # per MW of wind
_wind_pad_exchanges = [
    ("excavation",              _pad["excavation_m3"],  "cubic meter", "Leng S3 pad: earthwork backfill"),
    ("concrete_20mpa",          _pad["concrete_c15_m3"], "cubic meter", "Leng S3 pad: cushion concrete C15"),
    ("concrete_normal",         _pad["concrete_c30_m3"], "cubic meter", "Leng S3 pad: cushion concrete C30"),
    ("reinforcing_steel_glo",   _pad["rebar_kg"],       _kg,           "Leng S3 pad: reinforcement"),
    ("upv_electricity",         _pad["welding_kwh"],    "kilowatt hour", "Leng S3 pad: AC welding (unit ASSUMED kWh)"),
    ("diesel_building_machine", _pad["truck_diesel_l"] * DIESEL_MJ_PER_L, "megajoule",
                                "Leng S3 pad: heavy truck 5 t (litres per machine-team, Eq. S2)"),
]
_inst = {k: v / TX_LENG_FARM_MW for k, v in TX_LENG_INSTALLATION_PER_FARM.items()}   # per MW of wind
_wind_installation_exchanges = [
    ("steel_low_alloyed",   _inst["section_steel_kg"],  _kg, "Leng S3 electrical installation: section steel"),
    ("sheet_rolling_steel", _inst["section_steel_kg"],  _kg, "Leng S3 electrical installation: section steel, formed"),
    ("copper_cathode",      _inst["terminal_block_kg"], _kg,
     "Leng S3 electrical installation: terminal blocks (ASSUMED copper; Leng's dataset is not stated)"),
    ("steel_low_alloyed",   _inst["welding_rod_kg"],    _kg, "Leng S3 electrical installation: welding rod"),
    ("lead",                _inst["lead_seal_kg"],      _kg, "Leng S3 electrical installation: lead seals"),
]
_venue = {k: v / TX_LENG_FARM_MW for k, v in TX_LENG_VENUE_PER_FARM.items()}   # per MW of connection
_venue_exchanges = [
    ("excavation",            _venue["site_formation_m3"], "cubic meter",
     "Leng S3 venue: site formation, loose-rock excavation"),
    ("concrete_normal",       _venue["foundation_beam_m3"] * (1 - VENUE_BEAM_REBAR_FRACTION), "cubic meter",
     "Leng S3 venue: foundation beams, the concrete (97 % by volume, ASSUMED split)"),
    ("reinforcing_steel_glo", _venue["foundation_beam_m3"] * VENUE_BEAM_REBAR_FRACTION * STEEL_KG_PER_M3, _kg,
     "Leng S3 venue: foundation beams, the rebar (3 % by volume, ASSUMED split)"),
    ("steel_low_alloyed",     _venue["steel_formwork_kg"], _kg, "Leng S3 venue: steel formwork (temporary works, as Leng count them)"),
    ("sheet_rolling_steel",   _venue["steel_formwork_kg"], _kg, "Leng S3 venue: steel formwork, formed"),
    ("sawnwood_board",        _venue["board_m3"],          "cubic meter", "Leng S3 venue: board material"),
    ("steel_low_alloyed",     _venue["iron_nails_kg"],     _kg, "Leng S3 venue: iron nails"),
    ("steel_low_alloyed",     _venue["iron_wire_kg"],      _kg, "Leng S3 venue: iron wire"),
    ("wire_drawing_steel",    _venue["iron_wire_kg"],      _kg, "Leng S3 venue: iron wire, drawn"),
    ("concrete_normal",       _venue["concrete_m3"],       "cubic meter", "Leng S3 venue: concrete"),
    ("tap_water_row",         _venue["water_m3"] * 1000.0, _kg, "Leng S3 venue: water (1 m3 = 1,000 kg)"),
    ("reinforcing_steel_glo", _venue["rebar_kg"],          _kg, "Leng S3 venue: reinforcement steel"),
]
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

_grid_exchanges = []
for _material, _kg_per_mva in TX_GRID_KG_PER_MVA.items():
    for _p in TX_MATERIAL_PROCESSES[_material]:
        _grid_exchanges.append((_p, _kg_per_mva, _kg,
                                f"{_material} in the grid-intake transformer — Leng "
                                f"Table S1 main transformer XZ11-100000/110, "
                                f"{TX_LENG_MAIN_KG[_material]:,.1f} kg per "
                                f"{TX_LENG_MAIN_MVA:.0f} MVA unit"))

_per_mwp = UPV_TX_UNITS_PER_MWP


def _solar_row(key, amount_per_unit, unit, note):
    return ("upv_" + key, amount_per_unit * _per_mwp, unit,
            f"{note} - IEA PVPS T12-33:2026 Table 49, {amount_per_unit:,.3f} per "
            f"{UPV_TX_UNIT_MVA:g} MVA unit x {_per_mwp:g} units/MWp")


_solar_exchanges = (
    [_solar_row(k, kg, _kg, f"{k} in the solar inverter-station step-ups")
     for k, kg in UPV_TX_MATERIALS_KG.items()]
    + [_solar_row("fibreboard", UPV_TX_FIBREBOARD_M3, "cubic meter",
                  "hardboard pressboard (workbook '36.96 m3' is 36.96 kg; see docstring)")]
    + [_solar_row(k, kg, _kg, f"{k}, forming of mass already counted")
       for k, kg in UPV_TX_FORMING_KG.items()]
    + [_solar_row("electricity", UPV_TX_ELECTRICITY_KWH, "kilowatt hour", "factory electricity"),
       _solar_row("heat", UPV_TX_HEAT_MJ, "megajoule", "factory heat")]
    # Z-PV-238 (Table 50) puts a steel-construction transformer station on the
    # 10 MWp plant: 4 x 10 m2 for its four units. In since 21 Oct 2026.
    + [("building_hall", 10.0 * _per_mwp, "square meter",
        f"transformer station building - IEA PVPS T12-33:2026 Z-PV-238, 10 m2 per unit x {_per_mwp:g} units/MWp")]
)
# The unit rows only (no building), x Smith's 30-year replacement fraction.
_solar_replacement_exchanges = [
    (k, amt * UPV_TX_REPLACEMENT_FRACTION_30Y, unit,
     f"replacement over {UPV_TX_REPLACEMENT_REFERENCE_YEARS:.0f} y, "
     f"{UPV_TX_REPLACEMENT_FRACTION_30Y:.1%} of the installed units (Smith 2024 A15) - {note}")
    for k, amt, unit, note in _solar_exchanges if str(k).startswith("upv_")
]


def _container_row(key, amount_per_unit, unit, note):
    return ("upv_" + key, amount_per_unit * CSS_TX_UNITS_PER_MW, unit,
            f"{note} - {CSS_TX_SOURCE}: {CSS_TX_KG:,.0f} kg per {CSS_TX_KW:,.0f} kW = "
            f"{CSS_TX_KG_PER_MW:,.1f} kg/MW, as {CSS_TX_UNITS_PER_MW:.4f} of the IEA PVPS Table 49 "
            f"unit's composition ({amount_per_unit:,.3f} per {UPV_TX_BILL_KG:,.0f} kg unit)")


_container_exchanges = (
    [_container_row(k, kg, _kg, f"{k} in the battery / fuel-cell container step-up")
     for k, kg in UPV_TX_MATERIALS_KG.items()]
    + [_container_row("fibreboard", UPV_TX_FIBREBOARD_M3, "cubic meter", "hardboard pressboard")]
    + [_container_row(k, kg, _kg, f"{k}, forming of mass already counted")
       for k, kg in UPV_TX_FORMING_KG.items()]
    + [_container_row("electricity", UPV_TX_ELECTRICITY_KWH, "kilowatt hour", "factory electricity"),
       _container_row("heat", UPV_TX_HEAT_MJ, "megajoule", "factory heat")]
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
            "INCLUDES Leng Table S3's box-transformer foundations (since 21 Oct 2026) and "
            "electrical installation - section steel, terminal blocks, welding rod, lead seals "
            "(since 22 Oct 2026), per MW of the same farm. "
            "EXCLUDES: the grid-export transformer (this study is behind the meter, "
            "there is nothing to export into, and the grid intake is charged by "
            "grid_connection.py); any step between the collection network and the "
            "data centre (both sit in the medium-voltage band); switchgear and "
            "protection; losses; end-of-life. Leng publish no factory energy for "
            "the unit, so none is charged."
        ),
        technosphere=_wind_exchanges + _wind_pad_exchanges + _wind_installation_exchanges,
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
            "The workbook's '36.96 m3' hardboard cell is 36.96 kg mislabelled (its own "
            "comment says kg), carried as 0.0291 m3; the bill then sums to 5,670 kg "
            "against the report's 'approximately 5,680' (stepup_transformers.check). "
            "Functional unit is 1 MWp of PV CONNECTED - amortise over "
            "TX_ASSET_LIFE_YEARS (dc_config). "
            "INCLUDES factory electricity and heat, which the wind bill does not - "
            "process energy is ~6% here, so materials-only the two land within 1% of "
            "each other; the asymmetry is stated in SOURCES.md. "
            "INCLUDES (since 21 Oct 2026) the transformer station building from "
            "Z-PV-238, 10 m2 per unit. "
            "EXCLUDES: the grid-export transformer (behind the meter); any step "
            "between collection and the data centre (both medium voltage); "
            "switchgear and protection; losses; end-of-life."
        ),
        technosphere=_solar_exchanges,
    ),
    Activity(
        code=R.TX_SOLAR_REPL30,
        name="Solar inverter-station step-up transformer replacements, 30 years, per MWp of PV connected",
        reference_product="30 years of solar step-up transformer replacements, per MWp",
        unit="megawatt", location="GLO",
        comment=(
            "Smith 2024 Table A15 charges 1.30E-05 transformer replacements per m2 of "
            "module over 30 years against 4.30E-05 installed (A14): "
            f"{UPV_TX_REPLACEMENT_FRACTION_30Y:.1%} of the fleet, the same fraction "
            "upv.py keeps for the inverters in the same row. The fraction transfers to "
            "this study's unit and count where Smith's absolute number (for his 2.7 MVA "
            "A11 unit) would not. Functional unit is 30 years of replacements for 1 MWp "
            "of PV CONNECTED; transformers.py charges it per year, independently of the "
            "life the unit itself is amortised over. In since 21 Oct 2026; the wind "
            "step-ups have no replacement rate because Leng publish none (an unsourced "
            "flow, registered for the cut-off test). Same boundary as the unit: no "
            "delivery to site, no end-of-life."
        ),
        technosphere=_solar_replacement_exchanges,
    ),
    Activity(
        code=R.TX_GRID,
        name="Grid-intake transformer, per MVA of grid-intake transformer capacity",
        reference_product="grid-intake transformer capacity",
        unit="megavolt ampere", location="GLO",
        comment=(
            "The power transformer that steps the network's high voltage down onto "
            "the site, sized by cap_grid. Functional unit is 1 MVA of rating; "
            "grid_connection.py turns it into a per-MW figure with N-1 redundancy "
            "and the power factor, and amortises it over its own ASSET_LIFE_YEARS. "
            "ecoinvent 3.9.1 has no power transformer at any rating - its four "
            "transformer activities are two electronic components of 280 g and 30 g "
            "average weight, 'used in the information and communication technology' "
            "by its own comments - and no substation or switchgear dataset either. "
            "So this is assembled from Leng et al. (2026), Processes 14(7) 1045, "
            "Supplementary Table S1: the Gaoyou farm's grid-end main transformer, "
            f"XZ11-100000/110, one {TX_LENG_MAIN_MVA:.0f} MVA unit wound for "
            f"{TX_LENG_MAIN_KV:.0f} kV, {sum(TX_LENG_MAIN_KG.values()):,.1f} kg in "
            f"total = {sum(TX_GRID_KG_PER_MVA.values()):,.1f} kg/MVA, divided by its "
            "rating. Materials mapped exactly as the wind step-ups are, Iron read as "
            "core steel. VOLTAGE: a 110 kV unit fits a GB 132 kV EHV/DNO connection, "
            "the common case for a ~100 MW data centre; for a 275/400 kV "
            "transmission-connected site it errs LOW, supergrid transformers being "
            "heavier per MVA. Used for every site as the default. "
            "EXCLUDES: switchgear and protection (cut-off register); the line to the site "
            "(grid_connection.py reports it separately); losses; end-of-life. The switchyard's "
            "civils are their own activity, grid_intake_substation_civils_per_mw (Leng Table S3's "
            "outdoor venue, decision D2, 22 Oct 2026). Leng publish no factory energy for "
            "this unit; their 342 t CO2e against ~275 t here is a scoring difference "
            "(ecoinvent 3.11 v 3.9.1), not a dropped flow."
        ),
        technosphere=_grid_exchanges,
    ),
    Activity(
        code=R.TX_GRID_CIVILS,
        name="Grid-intake substation civils (switchyard), per MW of connection",
        reference_product="grid-intake substation civils",
        unit="megawatt", location="GLO",
        comment=(
            "The civils of the intake substation's switchyard, per MW of connection: Leng et al. "
            "(2026) Table S3 'outdoor venue project' of the Gaoyou farm's 110 kV booster station - "
            "site formation, foundation beams, steel formwork, board, nails and wire, concrete, "
            "water and reinforcement, every row at the printed amount, divided by the 100 MW the "
            "station serves (decision D2, 22 Oct 2026: one yard serves both intake transformers, so "
            "it scales with the connection, not the MVA installed). Leng's own score for the venue is "
            "2,157 t CO2e per 100 MW (34.4 % of the station). The station's buildings are covered by "
            "Zhang's facility building (stated substitution); its construction machinery is not "
            "separable and is on the cut-off register. grid_connection.py charges this per MW of "
            "cap_grid over ASSET_LIFE_YEARS. EXCLUDES switchgear, protection, delivery to site, end-of-life."
        ),
        technosphere=_venue_exchanges,
    ),
    Activity(
        code=R.TX_LV_CONTAINER,
        name="Containerised LV step-up transformer, per MW of inverter rating (battery PCS, fuel cell)",
        reference_product="containerised step-up transformer capacity",
        unit="megawatt", location="GLO",
        comment=(
            "The transformer that steps a battery container's PCS output, or a fuel-cell "
            "container's inverter output, from LOW voltage (400 V) up to the site collection "
            f"voltage ({TX_SITE_COLLECTION_KV:g} kV). Functional unit is 1 MW of inverter rating: "
            "transformers.py charges it per MW of cap_batt_p and per MW of cap_fc, each amortised "
            "over the asset's own life (the battery's 15 y; the fuel cell's BoP calendar life). "
            f"MASS from {CSS_TX_SOURCE}: {CSS_TX_KG:,.0f} kg per {CSS_TX_KW:,.0f} kW container = "
            f"{CSS_TX_KG_PER_MW:,.1f} kg/MW, on the measured curve (2,566 kg/MVA at 2.2 MVA, 2,272 at "
            "2.5). COMPOSITION, forming and factory energy per kg from the IEA PVPS T12-33:2026 Table "
            "49 20/0.4 kV oil-immersed unit, a STATED SUBSTITUTION for Jasper's own recipe on "
            "technological representativeness (decided 22 Oct 2026). Jasper give a per-kg split "
            "(air-cooled sheet rows 225-236), but their §2.4.3 says it is derived from Hunziker et "
            "al. (2020): a 630 kVA line-frequency transformer with an ON-LOAD TAP CHANGER, scaled "
            "by mass to 1,800 kVA. The IEA unit is a current 2,500 kVA distribution transformer "
            "built from product documentation at exactly the 20/0.4 kV step the container needs. "
            "Jasper's recipe scores 7.85 kg CO2e/kg against 4.57 here (+72 %, mostly its 0.09 kg/kg "
            "of control electronics, likely the tap changer's); it is the sensitivity case. "
            "Closed as negligible on 4 Sep 2026 and modelled on 15 Oct: the inventory and "
            "loss machinery existed by then, and leaving it out favoured the storage chains against "
            "the generation chains, which pay for theirs. "
            "EXCLUDES: switchgear, protection and civils (as every transformer here); losses, which "
            "conversion_losses.py charges as energy; end-of-life."
        ),
        technosphere=_container_exchanges,
    ),
]


def inventory() -> Inventory:
    return Inventory(name="power transformers (Leng 2026 wind + grid intake, IEA PVPS 2026 solar, "
                          "Jasper 2026 container step-up)",
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
        f"Grid intake: Leng main transformer XZ11-100000/110, {TX_LENG_MAIN_MVA:.0f} MVA at "
        f"{TX_LENG_MAIN_KV:.0f} kV -> {sum(TX_GRID_KG_PER_MVA.values()):,.1f} kg/MVA",
        f"Container step-up (battery PCS, fuel cell): {CSS_TX_SOURCE}, {CSS_TX_KG:,.0f} kg per "
        f"{CSS_TX_KW:,.0f} kW -> {CSS_TX_KG_PER_MW:,.1f} kg/MW on the IEA unit's composition",
        "Step-ups amortised over TX_ASSET_LIFE_YEARS in optimisation/transformers.py; "
        "the grid intake over ASSET_LIFE_YEARS in optimisation/grid_connection.py.",
    ])
