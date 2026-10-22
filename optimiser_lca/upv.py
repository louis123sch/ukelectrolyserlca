"""
Utility-scale PV plant — Smith et al. (NREL 2024), fixed tilt, rescored on apos.
=============================================================================

Source and scope
----------------
The solar generation coefficient, rebuilt. It replaces a basis that priced a
solar farm using the footprint of a 3 kWp domestic roof: IEA PVPS Task 12's
2023 data update, 35.8 g CO₂e/kWh — a good number for the system it describes
("1 kWh AC … produced with a 3 kWp PV system, rooftop mounted"), but
``cap_solar`` is a utility-scale MWp, so the study was charging solar for roof
rails and a domestic string inverter and no fence, no plant-scale cabling, no
land. It was also the one coefficient not scored on ecoinvent 3.9.1 apos.

    Smith, B.L., Sekar, A., Mirletz, H., Heath, G. & Margolis, R. (2024), "An
    Updated Life Cycle Assessment of Utility-Scale Solar Photovoltaic Systems
    Installed in the United States", NREL/TP-7A40-87372, Appendix A.

**Why a rebuild and not a citation.** Smith publishes on ecoinvent cut-off. A
cut-off result cannot be relabelled as APOS, because the two differ exactly
where recycled content matters — for a PV plant, the aluminium, steel and
copper. So his *inventory* is taken and rescored here, and his results are
never transcribed; that makes the answer 3.9.1 apos by construction, the way
every other foreground here is. His process names are ecoinvent-native and
resolve directly, 93 % with no decision at all.

**The chain** — eleven nested unit processes, each consuming the one above:
A1 silica sand (per 9.25e4 t) → A2 metallurgical silicon (+3.58 kg direct
fossil CO₂) → A3 polysilicon (72 kWh HV, China grid) → A4 Czochralski ingot →
A5 wafer (m²) → A7 PERC cell (m², + CF₄ and C₂F₆, GWP 7,380 and 12,400; A6
trimethylaluminum feeds it) → A8 PERC module (frame, glass, EVA) ; A10
inverter (2.7 MWac unit) ; A12 electrical BOS (m²) ; A13 fence (m²).

**Where the rows are.** Every Smith table this study uses is written out
below as one ``Activity``, row for row, with the amount as printed and the
flow named as Smith names it — so the inventory reads here, not in a PDF or a
data file. The transcription it was checked against is
``optimisation/data/smith-nrel-2024-life-cycle-inventory.md`` (all 23 tables,
including the end-of-life ones this study excludes). Rows knowingly dropped —
cells the PDF mangled, and ecoinvent v2 flow names with no 3.9.1 match — are
commented at the foot of the activity they belong to and listed with their
amounts in ``optimisation/data/UPV-DEFERRED-ISSUES.md``. Tables A14
(installation) and A15 (O&M) are not activities of their own: the parts kept
enter the plant and O&M activities as the parameters below.

**The four substitutions**:

1. **Fixed tilt for the tracker.** Smith's system is single-axis tracked; GB
   utility-scale is fixed tilt. Table A9 is dropped and IEA PVPS T12-33:2026
   ``Z-PV-239`` — a pile-driven steel table at 20° — put in its place. That
   makes the mounting *heavier* (9.730 vs 9.618 kg/m² of structure) and
   removes the motor, Li-ion cell and control electronics.
2. **No transformer.** ``stepup_transformers`` charges solar's step-up from
   IEA PVPS at 20/0.4 kV. Smith's A11 is unusable anyway at 19,796 kg/MVA,
   ~9× the measured specific mass at that rating.
3. **Inverter count from the stated ILR.** Smith's Table 3 says DC/AC 1.34;
   his Table A14 uses 4.30E-05 inverters/m², which at this module implies
   1.75. The two are inconsistent in the source; the stated design value is
   used, and ``check()`` refuses an implausible band.
4. **O&M keeps the replacement fraction, not the count.** A15 charges 30 % of
   the installed inverters over 30 years (Mason's 10 %/decade). The fraction
   transfers to our own count where his absolute number would not.

**Scope.** Included: manufacturing, mounting, electrical BOS, fence,
inverters, installation energy, land occupation (A14, zero GWP), 30 years of
O&M (rescaled to the study's life by ``renewables.py``). Excluded, each with
its direction: end-of-life (as everywhere in this study); delivery to site
(A14's transport rows — the sea leg alone is 201 t·km/m² for the import chain,
so this understates by ~1.5 %; outside the boundary because the site is not
known); the step-up transformer, charged elsewhere. Supply chain:
SE Asia import case — China national grid for the silicon chain, Thailand for
cell and module.

**How it is verified.** 290 of 290 scientific-notation values in Appendix A
appear in the transcription; 251 rows association-checked against the PDF,
249 clean (the 2 flagged are zero-GWP flows). Of 79 biosphere rows, exactly
four carry a non-zero GWP100 factor — the silicon CO₂ and the two fluorinated
cell gases — and all four are in. A8 lands at 684 kg CO₂e/kWdc; Smith states
his average-import module sits above the 630 kg CO₂e/kW EPEAT threshold, and
it does (``tests/test_coefficients.py``).

**Biosphere compartments.** Smith's biosphere rows name a substance, not a
compartment. The original build matched each by name to the *first* flow of
that name in the biosphere database — an accident of iteration order, which
has since changed (re-running that match today lands on different
compartments). The compartments the original build actually used are pinned
in the ``flows`` table below so the inventory is reproducible. The four
GWP-carrying flows (fossil CO₂ to air, CF₄, C₂F₆) are in sensible
compartments; the zero-GWP rest are arbitrary (cyanide to air, fluoride to
soil, waste heat to forestry soil) and must be fixed before any non-GWP
category is used.
"""
from __future__ import annotations

from optimiser_lca import registry as R
from optimiser_lca.common import FG, Activity, Flow, Inventory, Process

# =============================================================================
# Parameters
# =============================================================================
UPV_PV_SOURCE = ("Smith et al. (2024), NREL/TP-7A40-87372, Appendix A "
                 "(inventory rescored on ecoinvent 3.9.1 apos)")

# System spec — Smith Table 3. TRANSCRIBED.
UPV_PV_MODULE_W   = 405.0     # Wdc per module at STC
UPV_PV_MODULE_M2  = 1.99      # m2 per module
UPV_PV_MODULE_EFF = 0.203     # 20.3 %, the national average silicon module
UPV_PV_W_PER_M2   = UPV_PV_MODULE_W / UPV_PV_MODULE_M2      # 203.5
UPV_PV_M2_PER_MWP = 1e6 / UPV_PV_W_PER_M2                   # 4,914

# Inverter loading ratio: Smith STATES 1.34 (Table 3); his A14 implies 1.75.
# The stated design value is taken. ASSUMED where they disagree.
UPV_PV_ILR = 1.34
UPV_PV_INVERTER_MVA = 2.7
UPV_PV_INVERTERS_PER_MWP = 1.0 / (UPV_PV_INVERTER_MVA * UPV_PV_ILR)

UPV_PV_SCOPE = {
    "mounting": "fixed tilt (IEA PVPS T12-33:2026 Z-PV-239, 20 deg pile-driven steel table) "
                "SUBSTITUTED for Smith's single-axis tracker (A9). Near mass-neutral: 9.730 vs "
                "9.764 kg/m2, so the swap removes the motor, Li-ion cell and control "
                "electronics rather than buying a lighter structure.",
    "end_of_life": "EXCLUDED (Smith A16-A23), as everywhere else in this study.",
    "construction_transport": "EXCLUDED (Smith A14 rail/lorry/sea rows). The sea leg alone is "
                              "201 t*km/m2 for the import chain, so this UNDERSTATES by ~1.5 %.",
    "land_occupation": "INCLUDED since 21 Oct 2026 (Smith A14: 3 m2*a of 'Occupation, unspecified, natural "
                       "(non-use)' per m2 of module, on the plant activity). Zero GWP100; relevant to any land-use "
                       "category is scored.",
    "operation_maintenance": "INCLUDED (Smith A15): the basis being replaced is full-scope and "
                             "dropping O&M would be a scope change disguised as a data change. "
                             "Minus the tracker actuator (0.017 kg electric motor per m2), and "
                             "minus the transformer.",
    "step_up_transformer": "EXCLUDED here, charged by stepup_transformers at 20/0.4 kV. Smith's "
                           "own A11 is unusable at 19,796 kg/MVA, ~9x the measured specific mass.",
    "supply_chain": "SE Asia import case - China national grid for the silicon chain, Thailand "
                    "for cell fabrication and module assembly.",
}

# --- installation (Smith Table A14, per m2 of module) ---------------------------
# Of A14 only the diesel is kept: the component rows are the activities below,
# the transport rows are out of scope, and the tracker and transformer are
# substituted or charged elsewhere.
UPV_PV_INSTALL_DIESEL_MJ_PER_M2 = 2.6     # TRANSCRIBED.

# --- operation and maintenance (Smith Table A15, per m2 over 30 years) ---------
UPV_PV_OM_REFERENCE_YEARS  = 30.0
UPV_PV_OM_PETROL_KG_PER_M2 = 5.50e-2      # vegetation management. TRANSCRIBED.
UPV_PV_OM_PANEL_M2_PER_M2  = 1.50e-2      # 0.05 %/yr panel replacement
# Inverter replacement as a FRACTION of the installed count: Smith charges
# 1.30E-05/m2 in A15 against 4.30E-05/m2 installed in A14 -> 30 % over 30 y.
UPV_PV_OM_REPLACEMENT_FRACTION = 1.30e-5 / 4.30e-5

# --- the GB grid's own solar fleet, per kWh -------------------------------------
# The grid's solar share used to be scored on ecoinvent's 2008 El Tesoro plant
# (79.8 g/kWh), the plant this study rejects for its own cap_solar. This scores
# it on the same Smith plant instead, at the yield ecoinvent assigns its GB
# 570 kWp plant: 961.4 kWh/kWp/yr over 30 years, i.e. LF 10.97 % and 28,842
# kWh/kWp. Only the inventory changes, not the yield, and 30 years is Smith's
# own O&M period, so the O&M activity enters whole. TRANSCRIBED from
# renewables_embodied.csv (ecoinvent_lifetime_kWh_per_kW).
UPV_GRID_FLEET_KWH_PER_KWP = 28_842.0
UPV_GRID_FLEET_YEARS = 30.0

# --- fixed-tilt mounting (IEA PVPS T12-33:2026, Z-PV-239), per 1 m2 of module ---
# Keys are process keys in the table below.
UPV_MOUNT_SOURCE = ("IEA PVPS Task 12, Report T12-33:2026, Table 44 / workbook "
                    "sheet X-Montage-utility, dataset Z-PV-239")
UPV_MOUNT_KG_PER_M2 = {
    "steel_low_alloyed":  9.23544043035082,
    "aluminium_wrought":  0.284936216327312,
    "chromium_steel":     0.204341455164734,
    "polypropylene":      0.00533838344407142,
}
UPV_MOUNT_FORMING_PER_M2 = {
    "section_bar_rolling_steel": 9.23544043035082,   # kg
    "sheet_rolling_aluminium":   0.284936216327312,  # kg
    "wire_drawing_steel":        0.204341455164734,  # kg
    "zinc_coat_pieces":          0.514041839135378,  # m2
}
UPV_MOUNT_PACKAGING_KG_PER_M2 = {"corrugated_board_box_rer": 0.09259259259259259}
# The workbook's own "total weight, structure" cell, which the four material
# rows must reproduce. Packaging is NOT in that total.
UPV_MOUNT_STATED_TOTAL_KG_PER_M2 = 9.730056485286937


def check() -> str:
    mass = sum(UPV_MOUNT_KG_PER_M2.values())
    if abs(mass - UPV_MOUNT_STATED_TOTAL_KG_PER_M2) > 1e-6:
        raise AssertionError(
            f"fixed-tilt mounting sums to {mass:.6f} kg/m2 against IEA PVPS's stated "
            f"{UPV_MOUNT_STATED_TOTAL_KG_PER_M2:.6f}")
    if not (1.05 <= UPV_PV_ILR <= 1.60):
        raise AssertionError(
            f"inverter loading ratio {UPV_PV_ILR} is outside the plausible band for a utility "
            "PV plant - Smith's Table A14 implies 1.75, which is why his count is not used")
    for k in list(UPV_MOUNT_KG_PER_M2) + list(UPV_MOUNT_FORMING_PER_M2) + list(UPV_MOUNT_PACKAGING_KG_PER_M2):
        if k not in processes:
            raise AssertionError(f"no ecoinvent process mapped for mounting row {k!r}")
    if abs(UPV_PV_M2_PER_MWP * UPV_PV_W_PER_M2 - 1e6) > 1.0:
        raise AssertionError("m2/MWp does not invert the module power density")
    return (f"OK - {mass:.3f} kg/m2 of fixed-tilt structure, {UPV_PV_M2_PER_MWP:,.0f} m2/MWp at "
            f"{UPV_PV_W_PER_M2:.1f} W/m2, {UPV_PV_INVERTERS_PER_MWP:.4f} inverters/MWp at ILR "
            f"{UPV_PV_ILR:g}")


# =============================================================================
# Processes — one per distinct ecoinvent activity Smith names, in the order
# they first appear; then the mounting, installation and O&M rows.
# =============================================================================
_kg, _m2, _m3, _m = "kilogram", "square meter", "cubic meter", "meter"
_MJ, _kwh, _unit, _tkm = "megajoule", "kilowatt hour", "unit", "ton kilometer"


def _p(name, loc, product, why=""):
    """Smith prints the ecoinvent activity and location; the reference product
    is given too because a few names are multi-output (sulfuric acid)."""
    return Process(identity=(name, loc, product), query=f"{name} {loc}", why=why)


def _f(name, categories, why=""):
    return Flow(identity=(name, tuple(categories)), query=name, why=why)


processes = {
    # --- first used in Smith A1 (Silica sand production) ---
    "building_hall": _p("building construction, hall", "RoW", "building, hall"),
    "conveyor_belt": _p("market for conveyor belt", "GLO", "conveyor belt",
                        why="Smith prints 'conveyor belt production RoW'; the GLO market stands in"),
    "diesel": _p("diesel production, petroleum refinery operation", "RoW", "diesel"),
    "electricity_mv_cn": _p("market group for electricity, medium voltage", "CN",
                            "electricity, medium voltage",
                            why="Smith: 'varies by case'; the SE Asia import case puts the silicon chain on China's national grid"),
    "quarry_infrastructure": _p("gravel/sand quarry construction", "RoW",
                                "gravel/sand quarry infrastructure"),
    "heat_hfo": _p("heat production, heavy fuel oil, at industrial furnace 1MW", "RoW",
                   "heat, district or industrial, other than natural gas"),
    "heavy_fuel_oil": _p("heavy fuel oil production, petroleum refinery operation", "RoW",
                         "heavy fuel oil"),
    "industrial_machine": _p("industrial machine production, heavy, unspecified", "RoW",
                             "industrial machine, heavy, unspecified"),
    "lime_packed": _p("lime production, milled, packed", "RoW", "lime, packed"),
    "lubricating_oil_production": _p("lubricating oil production", "RoW", "lubricating oil"),
    "steel_unalloyed_converter": _p("steel production, converter, unalloyed", "RoW",
                                    "steel, unalloyed"),
    "synthetic_rubber": _p("synthetic rubber production", "RoW", "synthetic rubber"),
    "light_commercial_vehicle": _p("transport, freight, light commercial vehicle", "RoW",
                                   "transport, freight, light commercial vehicle"),
    "lorry": _p("market group for transport, freight, lorry, unspecified", "GLO",
                "transport, freight, lorry, unspecified"),
    # --- first used in Smith A2 (Silicon metal production) ---
    "charcoal": _p("market for charcoal", "GLO", "charcoal"),
    "coke": _p("market for coke", "GLO", "coke"),
    "eaf_converter": _p("market for electric arc furnace converter", "GLO",
                        "electric arc furnace converter"),
    "graphite": _p("market for graphite", "GLO", "graphite"),
    "oxygen_liquid": _p("market for oxygen, liquid", "RoW", "oxygen, liquid"),
    "petroleum_coke": _p("market for petroleum coke", "GLO", "petroleum coke"),
    "freight_train_us": _p("market for transport, freight train", "US", "transport, freight train"),
    "wood_chips": _p("market for wood chips, wet, measured as dry mass", "RoW",
                     "wood chips, wet, measured as dry mass"),
    "slag_mg_silicon": _p("market for slag from metallurgical grade silicon production", "GLO",
                          "slag from metallurgical grade silicon production"),
    # --- first used in Smith A3 (Polysilicon production) ---
    "chlorine_gas": _p("market for chlorine, gaseous", "RoW", "chlorine, gaseous"),
    "electricity_hv_cn": _p("market group for electricity, high voltage", "CN",
                            "electricity, high voltage",
                            why="as electricity_mv_cn; polysilicon takes high voltage"),
    "heat_gas": _p("heat production, natural gas, at industrial furnace >100kW", "RoW",
                   "heat, district or industrial, natural gas"),
    "hydrogen_liquid": _p("market for hydrogen, liquid", "RoW", "hydrogen, liquid"),
    "nitrogen_liquid": _p("market for nitrogen, liquid", "RoW", "nitrogen, liquid"),
    "quicklime_packed": _p("market for quicklime, milled, packed", "RoW",
                           "quicklime, milled, packed"),
    "silicone_factory": _p("market for silicone factory", "GLO", "silicone factory"),
    "naoh_50pct": _p("market for sodium hydroxide, without water, in 50% solution state", "GLO",
                     "sodium hydroxide, without water, in 50% solution state"),
    # --- first used in Smith A4 (Czochralski ingot production) ---
    "acetone": _p("market for acetone, liquid", "RoW", "acetone, liquid"),
    "argon_liquid": _p("market for argon, liquid", "RoW", "argon, liquid"),
    "ceramic_tile": _p("market for ceramic tile", "GLO", "ceramic tile"),
    "hcl_30pct_production": _p("hydrochloric acid production, from the reaction of hydrogen with chlorine", "RoW",
                               "hydrochloric acid, without water, in 30% solution state"),
    "hydrogen_fluoride": _p("market for hydrogen fluoride", "RoW", "hydrogen fluoride"),
    "lime_hydrated": _p("market for lime, hydrated, packed", "RoW", "lime, hydrated, packed"),
    "nitric_acid_50pct": _p("market for nitric acid, without water, in 50% solution state", "RoW",
                            "nitric acid, without water, in 50% solution state"),
    "water_softened_us": _p("market for water, completely softened", "US",
                            "water, completely softened"),
    "waste_wafer_inorganic": _p("market for waste, from silicon wafer production, inorganic", "GLO",
                                "waste, from silicon wafer production, inorganic"),
    # --- first used in Smith A5 (Monocrystalline silicon wafer production) ---
    "acrylic_binder_54pct": _p("market for acrylic binder, with water, in 54% solution state", "RoW",
                               "acrylic binder, with water, in 54% solution state"),
    "alkylbenzene_sulfonate": _p("market for alkylbenzene sulfonate, linear, petrochemical", "GLO",
                                 "alkylbenzene sulfonate, linear, petrochemical"),
    "brass": _p("market for brass", "RoW", "brass"),
    "citric_acid": _p("market for citric acid", "GLO", "citric acid"),
    "glass_wool_mat": _p("market for glass wool mat", "GLO", "glass wool mat"),
    "h2o2_50pct": _p("hydrogen peroxide production, product in 50% solution state", "RoW",
                     "hydrogen peroxide, without water, in 50% solution state"),
    "koh": _p("market for potassium hydroxide", "GLO", "potassium hydroxide"),
    "steel_low_alloyed_hr": _p("market for steel, low-alloyed, hot rolled", "GLO",
                               "steel, low-alloyed, hot rolled"),
    "wafer_factory": _p("market for wafer factory", "GLO", "wafer factory"),
    "wire_drawing_steel": _p("market for wire drawing, steel", "GLO", "wire drawing, steel"),
    "waste_wafer": _p("market for waste, from silicon wafer production", "GLO",
                      "waste, from silicon wafer production"),
    # --- first used in Smith A6 (Trimethylaluminum production) ---
    "aluminium_chloride": _p("aluminium chloride production", "GLO", "aluminium chloride"),
    "aluminium_wrought": _p("market for aluminium, wrought alloy", "GLO",
                            "aluminium, wrought alloy"),
    "helium": _p("market for helium", "GLO", "helium"),
    "methylchloride": _p("market for methylchloride", "RoW", "methylchloride"),
    "paraffin": _p("market for paraffin", "GLO", "paraffin"),
    "sodium": _p("market for sodium", "GLO", "sodium"),
    "fly_ash_incineration": _p("treatment of fly ash and scrubber sludge, hazardous waste incineration", "RoW",
                               "fly ash and scrubber sludge"),
    "hazardous_waste_incineration": _p("treatment of hazardous waste, hazardous waste incineration", "RoW",
                                       "hazardous waste, for incineration"),
    # --- first used in Smith A7 (PERC cell production) ---
    "ammonia": _p("market for ammonia, anhydrous, liquid", "RoW", "ammonia, anhydrous, liquid"),
    "calcium_chloride": _p("market for calcium chloride", "RoW", "calcium chloride"),
    "electricity_mv_th": _p("market for electricity, medium voltage", "TH",
                            "electricity, medium voltage",
                            why="Smith: 'varies by case'; the import case assembles cell and module in Thailand"),
    "hcl_30pct": _p("market for hydrochloric acid, without water, in 30% solution state", "RoW",
                    "hydrochloric acid, without water, in 30% solution state"),
    "paste_back": _p("market for metallization paste, back side", "RoW",
                     "metallization paste, back side",
                     why="Smith cites Muller et al. 2021 as the provider; ecoinvent's back-side paste market stands in"),
    "paste_back_aluminium": _p("market for metallization paste, back side, aluminium", "RoW",
                               "metallization paste, back side, aluminium"),
    "paste_front": _p("market for metallization paste, front side", "RoW",
                      "metallization paste, front side"),
    "nitrous_oxide": _p("market for nitrous oxide", "GLO", "nitrous oxide"),
    "phosphorus_oxychloride": _p("market for phosphorus oxychloride", "RoW",
                                 "phosphorus oxychloride"),
    "cell_factory": _p("market for photovoltaic cell factory", "GLO", "photovoltaic cell factory"),
    "propane": _p("market for propane", "GLO", "propane"),
    "silane": _p("market for silicon tetrahydride", "GLO", "silicon tetrahydride"),
    "solvent_organic": _p("market for solvent, organic", "GLO", "solvent, organic"),
    "sulfuric_acid": _p("sulfuric acid production", "RoW", "sulfuric acid"),
    "freight_train_row": _p("market for transport, freight train", "RoW",
                            "transport, freight train"),
    "container_ship": _p("transport, freight, sea, container ship", "GLO",
                         "transport, freight, sea, container ship"),
    # --- IEA PVPS Z-PV-239 fixed-tilt mounting: upstream transport and packaging waste ---
    "freight_train_rer": _p("market group for transport, freight train", "RER",
                            "transport, freight train"),
    "waste_paperboard_incineration_row": _p("treatment of waste paperboard, municipal incineration", "RoW",
                                            "waste paperboard"),
    "waste_pe_pp_row": _p("market for waste polyethylene/polypropylene product", "RoW",
                          "waste polyethylene/polypropylene product"),
    "water_softened_row": _p("market for water, completely softened", "RoW",
                             "water, completely softened"),
    "water_deionised": _p("water production, deionised", "RoW", "water, deionised"),
    "wastewater_pv_cell": _p("market for wastewater from PV cell production", "RoW",
                             "wastewater from PV cell production"),
    # --- first used in Smith A8 (PERC module production) ---
    "adipic_acid": _p("market for adipic acid", "GLO", "adipic acid"),
    "aluminium_almg3": _p("market for aluminium alloy, AlMg3", "GLO", "aluminium alloy, AlMg3"),
    "copper_cathode": _p("market for copper, cathode", "GLO", "copper, cathode"),
    "corrugated_board_box": _p("market for corrugated board box", "RoW", "corrugated board box"),
    "diode": _p("diode production, auxilliaries and energy use", "GLO",
                "diode, auxilliaries and energy use"),
    "eva_foil": _p("market for ethylvinylacetate, foil", "GLO", "ethylvinylacetate, foil"),
    "eur_pallet": _p("EUR-flat pallet production", "RoW", "EUR-flat pallet"),
    "gfrp_polyamide": _p("market for glass fibre reinforced plastic, polyamide, injection moulded", "GLO",
                         "glass fibre reinforced plastic, polyamide, injection moulded"),
    "lead": _p("market for lead", "GLO", "lead"),
    "lubricating_oil": _p("market for lubricating oil", "RoW", "lubricating oil"),
    "metal_working_aluminium": _p("market for metal working, average for aluminium product manufacturing", "GLO",
                                  "metal working, average for aluminium product manufacturing"),
    "ldpe_film": _p("market for packaging film, low density polyethylene", "GLO",
                    "packaging film, low density polyethylene"),
    "panel_factory": _p("market for photovoltaic panel factory", "GLO",
                        "photovoltaic panel factory"),
    "pet_granulate": _p("market for polyethylene terephthalate, granulate, amorphous", "GLO",
                        "polyethylene terephthalate, granulate, amorphous"),
    "hdpe_granulate": _p("market for polyethylene, high density, granulate", "GLO",
                         "polyethylene, high density, granulate"),
    "ldpe_granulate": _p("market for polyethylene, low density, granulate", "GLO",
                         "polyethylene, low density, granulate"),
    "pvf_film": _p("market for polyvinylfluoride, film", "GLO", "polyvinylfluoride, film"),
    "silicone_product": _p("market for silicone product", "RoW", "silicone product"),
    "solar_glass": _p("market for solar glass, low-iron", "GLO", "solar glass, low-iron"),
    "glass_tempering": _p("market for tempering, flat glass", "GLO", "tempering, flat glass"),
    "tin": _p("market for tin", "GLO", "tin"),
    "wire_drawing_copper": _p("market for wire drawing, copper", "GLO", "wire drawing, copper"),
    "municipal_solid_waste": _p("market for municipal solid waste", "RoW", "municipal solid waste"),
    "waste_mineral_oil": _p("market for waste mineral oil", "RoW", "waste mineral oil"),
    "waste_plastic": _p("market for waste plastic, mixture", "RoW", "waste plastic, mixture"),
    "waste_pvf": _p("market for waste polyvinylfluoride", "RoW", "waste polyvinylfluoride"),
    # --- first used in Smith A10 (Inverter (2.7 MWac)) ---
    "cable_cat5": _p("market for cable, network cable, category 5, without plugs", "GLO",
                     "cable, network cable, category 5, without plugs"),
    "cable_three_conductor": _p("market for cable, three-conductor cable", "GLO",
                                "cable, three-conductor cable"),
    "capacitor_electrolyte": _p("market for capacitor, electrolyte type, > 2cm height", "GLO",
                                "capacitor, electrolyte type, > 2cm height"),
    "capacitor_film": _p("market for capacitor, film type, for through-hole mounting", "GLO",
                         "capacitor, film type, for through-hole mounting"),
    "concrete_slab": _p("market for concrete slab", "RoW", "concrete slab",
                        why="Smith prints 'concrete slab - RoW'. Scores ~1,025 kg CO2e/m3, which looks high - 2.7 % of the inverter (UPV-DEFERRED-ISSUES.md)"),
    "inductor": _p("market for inductor, ring core choke type", "GLO",
                   "inductor, ring core choke type"),
    "integrated_circuit": _p("market for integrated circuit, logic type", "GLO",
                             "integrated circuit, logic type"),
    "pwb_through_hole": _p("market for printed wiring board, through-hole mounted, unspecified, Pb free", "GLO",
                           "printed wiring board, through-hole mounted, unspecified, Pb free"),
    "reinforcing_steel": _p("market for reinforcing steel", "GLO", "reinforcing steel"),
    "transformer_hv": _p("market for transformer, high voltage use", "GLO",
                         "transformer, high voltage use"),
    "transistor": _p("market for transistor, wired, big size, through-hole mounting", "GLO",
                     "transistor, wired, big size, through-hole mounting"),
    "fan": _p("market for fan, for power supply unit, desktop computer", "GLO",
              "fan, for power supply unit, desktop computer"),
    # --- first used in Smith A12 (Cables, conduit, other electrical balance of system) ---
    "epoxy_resin": _p("market for epoxy resin, liquid", "RoW", "epoxy resin, liquid"),
    "nylon_6": _p("market for nylon 6", "RoW", "nylon 6"),
    "polycarbonate": _p("market for polycarbonate", "GLO", "polycarbonate"),
    "pvc": _p("market for polyvinylchloride, bulk polymerised", "GLO",
              "polyvinylchloride, bulk polymerised"),
    # --- first used in Smith A13 (Fence) ---
    "concrete_25mpa": _p("market for concrete, 25MPa", "RoW", "concrete, 25MPa"),
    "section_bar_rolling_steel": _p("market for section bar rolling, steel", "GLO",
                                    "section bar rolling, steel"),
    "steel_low_alloyed": _p("market for steel, low-alloyed", "GLO", "steel, low-alloyed"),
    "zinc_coat_coils": _p("market for zinc coat, coils", "GLO", "zinc coat, coils"),
    # --- fixed-tilt mounting (IEA PVPS Z-PV-239), installation (A14) and O&M (A15) ---
    "chromium_steel": _p("market for steel, chromium steel 18/8", "GLO", "steel, chromium steel 18/8"),
    "polypropylene": _p("market for polypropylene, granulate", "GLO", "polypropylene, granulate"),
    "corrugated_board_box_rer": _p("market for corrugated board box", "RER", "corrugated board box",
                                   why="IEA PVPS's own packaging row; Smith's A8 box is the RoW market"),
    "sheet_rolling_aluminium": _p("market for sheet rolling, aluminium", "GLO", "sheet rolling, aluminium"),
    "zinc_coat_pieces": _p("market for zinc coat, pieces", "GLO", "zinc coat, pieces"),
    "diesel_building_machine": _p("market for diesel, burned in building machine", "GLO",
                                  "diesel, burned in building machine",
                                  why="installation energy, Smith A14"),
    "petrol_low_sulfur": _p("petrol production, low-sulfur", "RoW", "petrol, low-sulfur",
                            why="vegetation management fuel, Smith A15"),
}

flows = {
    "antimony": _f("Antimony", ("natural resource", "in ground")),
    "arsenic": _f("Arsenic", ("natural resource", "in ground")),
    "boron": _f("Boron", ("air", "urban air close to ground")),
    "cadmium": _f("Cadmium", ("natural resource", "in ground")),
    "calcium": _f("Calcium", ("natural resource", "in ground")),
    "co2_biogenic": _f("Carbon dioxide, non-fossil", ("air",)),
    "co2_fossil": _f("Carbon dioxide, fossil", ("air",),
                      why="GWP100 = 1; the direct CO2 of carbothermic silicon (A2) and module lamination (A8)"),
    "co_fossil": _f("Carbon monoxide, fossil", ("air", "urban air close to ground")),
    "chlorine": _f("Chlorine", ("water", "surface water")),
    "chromium_iii": _f("Chromium III", ("soil", "industrial")),
    "cyanide": _f("Cyanide", ("air", "low population density, long-term")),
    "fluorine": _f("Fluorine", ("air", "low population density, long-term")),
    "heat_waste": _f("Heat, waste", ("soil", "forestry")),
    "hf": _f("Hydrogen fluoride", ("air", "low population density, long-term")),
    "h2s": _f("Hydrogen sulfide", ("air", "lower stratosphere + upper troposphere")),
    "iron": _f("Iron", ("natural resource", "in ground")),
    "lead_resource": _f("Lead", ("natural resource", "in ground")),
    "mercury": _f("Mercury", ("natural resource", "in ground")),
    "nox": _f("Nitrogen oxides", ("air", "lower stratosphere + upper troposphere")),
    "pm10": _f("Particulate Matter, > 10 um", ("air", "urban air close to ground")),
    "potassium": _f("Potassium", ("natural resource", "in ground")),
    "silicon": _f("Silicon", ("water", "surface water")),
    "sodium_soil": _f("Sodium", ("soil",)),
    "so2": _f("Sulfur dioxide", ("air", "urban air close to ground")),
    "tin_resource": _f("Tin", ("natural resource", "in ground")),
    "bod5": _f("BOD5, Biological Oxygen Demand", ("water", "surface water")),
    "chloride": _f("Chloride", ("water",)),
    "cod": _f("COD, Chemical Oxygen Demand", ("water", "ocean")),
    "doc": _f("DOC, Dissolved Organic Carbon", ("water", "ocean")),
    "nitrogen": _f("Nitrogen", ("air",)),
    "phosphate": _f("Phosphate", ("water", "ground-")),
    "toc": _f("TOC, Total Organic Carbon", ("water", "surface water")),
    "fluoride": _f("Fluoride", ("soil", "agricultural")),
    "hydrocarbons": _f("Hydrocarbons, unspecified", ("soil", "agricultural")),
    "hydroxide": _f("Hydroxide", ("water", "surface water")),
    "water": _f("Water", ("water", "ocean")),
    "aluminium": _f("Aluminium", ("natural resource", "in ground")),
    # Land flows, all zero GWP100: Smith A14 and IEA PVPS Z-PV-239. In since
    # 21 Oct 2026 because they are in the sources and inside the boundary.
    "occupation_natural": _f("Occupation, unspecified, natural (non-use)", ("natural resource", "land")),
    "occupation_industrial": _f("Occupation, industrial area", ("natural resource", "land")),
    "transformation_from_pasture": _f("Transformation, from pasture, man made", ("natural resource", "land")),
    "transformation_to_industrial": _f("Transformation, to industrial area", ("natural resource", "land")),
    "c2f6": _f("Ethane, hexafluoro-, HFC-116", ("air", "urban air close to ground"),
                why="GWP100 12,400; cell etch gas"),
    "cf4": _f("Methane, tetrafluoro-, R-14", ("air", "non-urban air or from high stacks"),
               why="GWP100 7,380; cell etch gas"),
    "silver": _f("Silver", ("natural resource", "in ground")),
}

check()

# =============================================================================
# Activities — Smith's tables, one each, rows as printed
# =============================================================================
_T = R.UPV_TABLES
_COMMENT = (
    f"{UPV_PV_SOURCE}. Smith publishes on ecoinvent CUT-OFF; his "
    "inventory is rescored here on ecoinvent 3.9.1 apos, and his "
    "results are never transcribed - a cut-off figure cannot be "
    "relabelled as APOS because the two differ exactly where recycled "
    "content matters. Fixed tilt: Smith's single-axis tracker (A9) is "
    "replaced by IEA PVPS T12-33:2026 Z-PV-239, a 20 deg pile-driven "
    "steel table, which is HEAVIER (9.730 vs 9.618 kg/m2 of structure) "
    "- the module frame is unaffected, being 1.51 kg/m2 of AlMg3 in the "
    "module itself. EXCLUDES end-of-life; construction transport (the "
    "sea leg alone is 201 t*km/m2 for this import chain, so this "
    "understates by ~1.5 %); and the step-up transformer, which "
    "stepup_transformers charges from IEA PVPS at 20/0.4 kV. Supply chain "
    "is the SE Asia import case - China national grid for the silicon "
    "chain, Thailand for cell and module. Verified: 290/290 "
    "scientific-notation values transcribed, 251 rows association-"
    "checked (249 clean), and the module reproduces Smith's own stated "
    "EPEAT result of >630 kg CO2e/kWdc."
)


def _smith(tab: str) -> str:
    return f"Smith Table {tab}, rows as printed. " + _COMMENT


# A unit process is written per ONE of its reference product, so Smith's batch
# sizes (92,500 t of sand; 18 kg of TMA) are production amounts. Waste
# treatment rows are negative, ecoinvent's sign for a treatment service.
smith_activities = [
    Activity(
        code=_T["A1"], name="UPV, silica sand", reference_product="silica sand",
        unit="tonne", location="GB", comment=_smith("A1"), production_amount=92_500.0,
        technosphere=[
            ("building_hall",                    48.4, _m2,      "building, hall"),
            ("conveyor_belt",                    9.15, _m,       "conveyor belt"),
            ("diesel",                         31_600, _kg,      "diesel"),
            ("electricity_mv_cn",             262_000, _kwh,     "electricity, medium voltage"),
            ("quarry_infrastructure",         0.00457, _unit,    "gravel/sand quarry infrastructure"),
            ("heat_hfo",                   18_500_000, _MJ,      "heat, district or industrial, other than natural gas"),
            ("heavy_fuel_oil",                   5250, _kg,      "heavy fuel oil"),
            ("industrial_machine",               1080, _kg,      "industrial machine, heavy, unspecified"),
            ("lime_packed",                      2720, _kg,      "lime, packed"),
            ("lubricating_oil_production",        118, _kg,      "lubricating oil"),
            ("steel_unalloyed_converter",        1250, _kg,      "steel, unalloyed"),
            ("synthetic_rubber",                  192, _kg,      "synthetic rubber"),
            ("light_commercial_vehicle",         1490, _tkm,     "transport, freight, light commercial vehicle"),
            ("lorry",                          10_100, _tkm,     "transport, freight, lorry, unspecified"),
        ],
        # not carried - mangled rows in the source PDF (UPV-DEFERRED-ISSUES.md):
        #   sand, quartz 100_000 t
        #   Water, process and cooling, unspecified natural origin 133_000 m3
        #   Water, process, unspecified natural origin 971_000 m3
    ),
    Activity(
        code=_T["A2"], name="UPV, silicon, metallurgical grade", reference_product="silicon, metallurgical grade",
        unit=_kg, location="GB", comment=_smith("A2"),
        technosphere=[
            (FG(_T["A1"]),         0.0027, "tonne",  "silica sand - 2.7 kg as printed"),
            ("charcoal",             0.17, _kg,      "charcoal"),
            ("coke",                 23.1, _MJ,      "coke"),
            ("eaf_converter",       1e-11, _unit,    "electric arc furnace converter"),
            ("electricity_mv_cn",      13, _kwh,     "electricity, medium voltage"),
            ("graphite",              0.1, _kg,      "graphite"),
            ("oxygen_liquid",        0.02, _kg,      "oxygen, liquid"),
            ("petroleum_coke",        0.5, _kg,      "petroleum coke"),
            ("freight_train_us",    0.069, _tkm,     "transport, freight train"),
            ("lorry",               0.156, _tkm,     "transport, freight, lorry, unspecified"),
            ("wood_chips",        0.00325, _kg,      "wood chips, wet, measured as dry mass"),
            # waste treatment: negative, ecoinvent's sign for a treatment service
            ("slag_mg_silicon",    -0.025, _kg,      "slag from metallurgical grade silicon production"),
        ],
        biosphere=[
            ("antimony",       7.85e-9, _kg,      "antimony"),
            ("arsenic",        9.42e-9, _kg,      "arsenic"),
            ("boron",          2.79e-7, _kg,      "boron"),
            ("cadmium",       3.14e-10, _kg,      "cadmium"),
            ("calcium",        7.75e-7, _kg,      "calcium"),
            ("co2_biogenic",      1.61, _kg,      "carbon dioxide, biogenic"),
            ("co2_fossil",        3.58, _kg,      "carbon dioxide, fossil"),
            ("co_fossil",      0.00138, _kg,      "carbon monoxide, fossil"),
            ("chlorine",       7.85e-8, _kg,      "chlorine"),
            ("chromium_iii",   7.85e-9, _kg,      "chromium III"),
            ("cyanide",        6.87e-6, _kg,      "cyanide"),
            ("fluorine",       3.88e-8, _kg,      "fluorine"),
            ("heat_waste",        71.3, _MJ,      "heat, waste"),
            ("hf",              0.0005, _kg,      "hydrogen fluoride"),
            ("h2s",             0.0005, _kg,      "hydrogen sulfide"),
            ("iron",           3.88e-6, _kg,      "iron"),
            ("lead_resource",  3.44e-7, _kg,      "lead"),
            ("mercury",        7.85e-9, _kg,      "mercury"),
            ("nox",            0.00974, _kg,      "nitrogen oxides"),
            ("pm10",           0.00775, _kg,      "particulates, >10 μm"),
            ("potassium",       6.2e-5, _kg,      "potassium"),
            ("silicon",        0.00751, _kg,      "silicon"),
            ("sodium_soil",    7.75e-7, _kg,      "sodium"),
            ("so2",             0.0122, _kg,      "sulfur dioxide"),
            ("tin_resource",   7.85e-9, _kg,      "tin"),
        ],
        # not carried - ecoinvent v2 flow names with no 3.9.1 match, believed zero GWP:
        #   carbon monoxide, land transformation 0.00062 kg
        #   NMVOC, non-methane volatile organic compounds, unspecified origin 9.6e-5 kg
    ),
    Activity(
        code=_T["A3"], name="UPV, silicon, solar grade", reference_product="silicon, solar grade",
        unit=_kg, location="GB", comment=_smith("A3"),
        technosphere=[
            (FG(_T["A2"]),          1.26, _kg,      "silicon, metallurgical grade"),
            ("chlorine_gas",       0.215, _kg,      "chlorine, gaseous"),
            ("electricity_hv_cn",     72, _kwh,     "electricity, high voltage"),
            ("graphite",          0.0054, _kg,      "graphite"),
            ("heat_gas",              70, _MJ,      "heat, district or industrial, natural gas"),
            ("hydrogen_liquid",   0.0536, _kg,      "hydrogen, liquid"),
            ("nitrogen_liquid",     12.9, _kg,      "nitrogen, liquid"),
            ("quicklime_packed",    0.58, _kg,      "quicklime, milled, packed"),
            ("silicone_factory",   1e-11, _unit,    "silicone factory"),
            ("naoh_50pct",          0.35, _kg,      "sodium hydroxide, without water, in 50% solution state"),
            ("freight_train_us",    3.65, _tkm,     "transport, freight train"),
            ("lorry",               2.87, _tkm,     "transport, freight, lorry, unspecified"),
        ],
        biosphere=[
            ("bod5",       0.000205, _kg,      "BOD5, biological oxygen demand"),
            ("chloride",      0.036, _kg,      "chloride"),
            ("cod",         0.00202, _kg,      "COD, chemical oxygen demand"),
            ("doc",         0.00091, _kg,      "DOC, dissolved organic carbon"),
            ("heat_waste",      396, _MJ,      "heat, waste"),
            ("nitrogen",   0.000208, _kg,      "nitrogen"),
            ("phosphate",    2.8e-6, _kg,      "phosphate"),
            ("toc",         0.00091, _kg,      "TOC, total organic carbon"),
        ],
        # not carried - ecoinvent v2 flow names with no 3.9.1 match, believed zero GWP:
        #   AOX, adsorbable organic halogen as Cl 1.26e-5 kg
        #   copper, ion 1.02e-7 kg
        #   iron, ion 5.61e-6 kg
        #   sodium, ion 0.0338 kg
        #   zinc, ion 1.96e-6 kg
    ),
    Activity(
        code=_T["A4"], name="UPV, silicon, single crystal, Czochralski", reference_product="silicon, single crystal, Czochralski",
        unit=_kg, location="GB", comment=_smith("A4"),
        technosphere=[
            (FG(_T["A3"]),                1.03, _kg,      "silicon, solar grade"),
            ("acetone",                  0.049, _kg,      "acetone, liquid"),
            ("argon_liquid",             0.046, _kg,      "argon, liquid"),
            ("ceramic_tile",             0.062, _kg,      "ceramic tile"),
            ("electricity_mv_cn",         38.4, _kwh,     "electricity, medium voltage"),
            ("hcl_30pct_production",  0.000438, _kg,      "hydrochloric acid, without water, in 30% solution state"),
            ("hydrogen_fluoride",      0.00351, _kg,      "hydrogen fluoride"),
            ("lime_hydrated",            0.022, _kg,      "lime, hydrated, packed"),
            ("nitric_acid_50pct",      0.00778, _kg,      "nitric acid, without water, in 50% solution state"),
            ("silicone_factory",         5e-12, _unit,    "silicone factory"),
            ("naoh_50pct",             0.00478, _kg,      "sodium hydroxide, without water, in 50% solution state"),
            ("freight_train_us",          1.41, _tkm,     "transport, freight train"),
            ("lorry",                     1.13, _tkm,     "transport, freight, lorry, unspecified"),
            ("water_softened_us",       0.0684, _kg,      "water, completely softened"),
            # waste treatment: negative, ecoinvent's sign for a treatment service
            ("waste_wafer_inorganic",     -0.1, _kg,      "waste, from silicon wafer production, inorganic"),
        ],
        biosphere=[
            ("bod5",            0.13, _kg,      "BOD5, biological oxygen demand"),
            ("cod",             0.13, _kg,      "COD, chemical oxygen demand"),
            ("doc",           0.0405, _kg,      "DOC, dissolved organic carbon"),
            ("fluoride",     0.00237, _kg,      "fluoride"),
            ("heat_waste",       115, _MJ,      "heat, waste"),
            ("hydrocarbons",  0.0228, _kg,      "hydrocarbons, unspecified"),
            ("hydroxide",    0.00742, _kg,      "hydroxide"),
            ("nitrogen",      0.0091, _kg,      "nitrogen"),
            ("toc",           0.0405, _kg,      "TOC, total organic carbon"),
            ("water",            0.3, _m3,      "water"),
            ("water",            2.2, _m3,      "water"),
        ],
        # not carried - mangled rows in the source PDF (UPV-DEFERRED-ISSUES.md):
        #   Water, cooling, unspecified natural origin 2.33 m3
    ),
    Activity(
        code=_T["A5"], name="UPV, single-Si wafer, photovoltaic", reference_product="single-Si wafer, photovoltaic",
        unit=_m2, location="GB", comment=_smith("A5"),
        technosphere=[
            (FG(_T["A4"]),                0.595, _kg,      "silicon, single crystal, Czochralski process, photovoltaics"),
            ("acrylic_binder_54pct",      0.002, _kg,      "acrylic binder, with water, in 54% solution state"),
            ("alkylbenzene_sulfonate",    0.034, _kg,      "alkylbenzene sulfonate, linear, petrochemical"),
            ("brass",                   0.00745, _kg,      "brass"),
            ("citric_acid",               0.187, _kg,      "citric acid"),
            ("electricity_mv_cn",          2.35, _kwh,     "electricity, medium voltage"),
            ("glass_wool_mat",           0.0106, _kg,      "glass wool mat"),
            ("heat_gas",                    1.8, _MJ,      "heat, district or industrial, natural gas"),
            ("h2o2_50pct",               0.0253, _kg,      "hydrogen peroxide, without water, in 50% solution state"),
            ("koh",                     0.00381, _kg,      "potassium hydroxide"),
            ("naoh_50pct",                0.015, _kg,      "sodium hydroxide, without water, in 50% solution state"),
            ("steel_low_alloyed_hr",   0.000896, _kg,      "steel, low-alloyed, hot rolled"),
            ("wafer_factory",              2e-6, _unit,    "wafer factory"),
            ("water_softened_us",          21.7, _kg,      "water, completely softened"),
            ("wire_drawing_steel",     0.000896, _kg,      "wire drawing, steel"),
            # waste treatment: negative, ecoinvent's sign for a treatment service
            ("waste_wafer",               -0.02, _kg,      "waste, from silicon wafer production"),
        ],
        biosphere=[
            ("bod5",        0.0296, _kg,      "BOD5, biological oxygen demand"),
            ("cod",         0.0296, _kg,      "COD, chemical oxygen demand"),
            ("doc",         0.0111, _kg,      "DOC, dissolved organic carbon"),
            ("heat_waste",       8, _MJ,      "heat, waste"),
            ("nitrogen",   0.00994, _kg,      "nitrogen"),
            ("toc",         0.0111, _kg,      "TOC, total organic carbon"),
            ("water",      0.00975, _m3,      "water"),
            ("water",       0.0553, _m3,      "water"),
        ],
        # not carried - ecoinvent v2 flow names with no 3.9.1 match, believed zero GWP:
        #   AOX, adsorbable organic halogen as Cl 0.000501 kg
        #   copper, ion 6.05e-5 kg
    ),
    Activity(
        code=_T["A6"], name="UPV, trimethylaluminum, purified", reference_product="trimethylaluminum, purified",
        unit=_kg, location="GB", comment=_smith("A6"), production_amount=18.0,
        technosphere=[
            ("aluminium_chloride",            1.34, _kg,      "aluminium chloride"),
            ("aluminium_wrought",             21.6, _kg,      "aluminium, wrought alloy"),
            ("electricity_mv_cn",             5.57, _kwh,     "electricity, medium voltage"),
            ("helium",                        0.12, _kg,      "helium"),
            ("methylchloride",                60.9, _kg,      "methylchloride"),
            ("nitrogen_liquid",              0.825, _kg,      "nitrogen, liquid"),
            ("paraffin",                     0.153, _kg,      "paraffin"),
            ("sodium",                          33, _kg,      "sodium"),
            # waste treatment: negative, ecoinvent's sign for a treatment service
            ("fly_ash_incineration",          -3.8, _kg,      "fly ash and scrubber sludge"),
            ("hazardous_waste_incineration",  -107, _kg,      "hazardous waste, for incineration"),
        ],
    ),
    Activity(
        code=_T["A7"], name="UPV, photovoltaic cell, single-Si wafer", reference_product="photovoltaic cell, single-Si wafer",
        unit=_m2, location="GB", comment=_smith("A7"),
        technosphere=[
            (FG(_T["A5"]),                 1.02, _m2,      "single-Si wafer, photovoltaic"),
            (FG(_T["A6"]),             0.000288, _kg,      "trimethylaluminum"),
            ("ammonia",                  0.0165, _kg,      "ammonia, anhydrous, liquid"),
            ("calcium_chloride",         0.0207, _kg,      "calcium chloride"),
            ("electricity_mv_th",          6.03, _kwh,     "electricity, medium voltage"),
            ("heat_gas",                   3.55, _MJ,      "heat, district or industrial, natural gas"),
            ("hcl_30pct",                0.0681, _kg,      "hydrochloric acid, without water, in 30% solution state"),
            ("hydrogen_fluoride",        0.0747, _kg,      "hydrogen fluoride"),
            ("paste_back",              0.00102, _kg,      "metallization paste, back side"),
            ("paste_back_aluminium",    0.00901, _kg,      "metallization paste, back side, aluminium"),
            ("paste_front",             0.00348, _kg,      "metallization paste, front side"),
            ("nitric_acid_50pct",        0.0822, _kg,      "nitric acid, without water, in 50% solution state"),
            ("nitrogen_liquid",            2.62, _kg,      "nitrogen, liquid"),
            ("nitrous_oxide",           0.00766, _kg,      "nitrous oxide"),
            ("oxygen_liquid",             0.334, _kg,      "oxygen, liquid"),
            ("phosphorus_oxychloride", 0.000182, _kg,      "phosphorus oxychloride"),
            ("cell_factory",               4e-7, _unit,    "photovoltaic cell factory"),
            ("koh",                       0.151, _kg,      "potassium hydroxide"),
            ("propane",                  0.0414, _kg,      "propane"),
            ("silane",                  0.00283, _kg,      "silicon tetrahydride"),
            ("solvent_organic",          0.0123, _kg,      "solvent, organic"),
            ("sulfuric_acid",            0.0206, _kg,      "sulfuric acid"),
            ("freight_train_row",          1.52, _tkm,     "transport, freight train"),
            ("lorry",                     0.274, _tkm,     "transport, freight, lorry, unspecified"),
            ("container_ship",             1.57, _tkm,     "transport, freight, sea, container ship"),
            ("water_softened_row",         23.2, _kg,      "water, completely softened"),
            ("water_deionised",            39.4, _kg,      "water, deionised"),
            # waste treatment: negative, ecoinvent's sign for a treatment service
            ("waste_wafer_inorganic",  -0.00641, _kg,      "waste, from silicon wafer production, inorganic"),
            ("wastewater_pv_cell",      -0.0132, _m3,      "wastewater from PV cell production"),
        ],
        biosphere=[
            ("aluminium",     0.000773, _kg,      "aluminium"),
            ("c2f6",          0.000119, _kg,      "ethane, hexafluoro-, HFC-116"),
            ("heat_waste",        51.8, _MJ,      "heat, waste"),
            ("hf",             4.85e-6, _kg,      "hydrogen fluoride"),
            ("lead_resource",  3.48e-7, _kg,      "lead"),
            ("cf4",           0.000248, _kg,      "methane, tetrafluoro-, R-14"),
            ("nox",               5e-5, _kg,      "nitrogen oxides"),
            ("silicon",        7.27e-5, _kg,      "silicon"),
            ("silver",          6.6e-6, _kg,      "silver"),
            ("water",           0.0168, _m3,      "water"),
            ("water",            0.277, _m3,      "water"),
        ],
        # not carried - mangled rows in the source PDF (UPV-DEFERRED-ISSUES.md):
        #   Water, cooling, unspecified natural origin 0.231 m3
        # not carried - ecoinvent v2 flow names with no 3.9.1 match, believed zero GWP:
        #   hydrogen chloride 0.000266 kg
        #   NMVOC, non-methane volatile organic compounds, unspecified origin 0.194 kg
        #   particulates, <2.5 μm 0.00266 kg
    ),
    Activity(
        code=_T["A8"], name="UPV, photovoltaic panel, PERC", reference_product="photovoltaic panel, PERC",
        unit=_m2, location="GB", comment=_smith("A8"),
        technosphere=[
            (FG(_T["A7"]),                    0.9, _m2,      "photovoltaic cell, single-Si wafer"),
            ("adipic_acid",              0.000369, _kg,      "adipic acid"),
            ("aluminium_almg3",              1.51, _kg,      "aluminium alloy, AlMg3"),
            ("copper_cathode",              0.148, _kg,      "copper, cathode"),
            ("corrugated_board_box",        0.763, _kg,      "corrugated board box"),
            ("diode",                     0.00281, _kg,      "diode, auxilliaries and energy use"),
            ("electricity_mv_th",            3.32, _kwh,     "electricity, medium voltage"),
            ("eva_foil",                    0.793, _kg,      "ethylvinylacetate, foil"),
            ("eur_pallet",                   0.05, _unit,    "EUR-flat pallet"),
            ("gfrp_polyamide",              0.188, _kg,      "glass fibre reinforced plastic, polyamide, injection moulded"),
            ("lead",                       0.0108, _kg,      "lead"),
            ("lubricating_oil",           0.00161, _kg,      "lubricating oil"),
            ("metal_working_aluminium",      1.51, _kg,      "metal working, average for aluminium product manufacturing"),
            ("ldpe_film",                  0.0401, _kg,      "packaging film, low density polyethylene"),
            ("panel_factory",                4e-6, _unit,    "photovoltaic panel factory"),
            ("pet_granulate",               0.281, _kg,      "polyethylene terephthalate, granulate, amorphous"),
            ("hdpe_granulate",             0.0242, _kg,      "polyethylene, high density, granulate"),
            ("ldpe_granulate",             0.0548, _kg,      "polyethylene, low density, granulate"),
            ("pvf_film",                   0.0451, _kg,      "polyvinylfluoride, film"),
            ("silicone_product",            0.144, _kg,      "silicone product"),
            ("solar_glass",                     8, _kg,      "solar glass, low-iron"),
            ("glass_tempering",                 8, _kg,      "tempering, flat glass"),
            ("tin",                        0.0104, _kg,      "tin"),
            ("freight_train_row",            16.6, _tkm,     "transport, freight train"),
            ("lorry",                        2.99, _tkm,     "transport, freight, lorry, unspecified"),
            ("wire_drawing_copper",         0.148, _kg,      "wire drawing, copper"),
            # waste treatment: negative, ecoinvent's sign for a treatment service
            ("municipal_solid_waste",     -0.0934, _kg,      "municipal solid waste"),
            ("waste_mineral_oil",        -0.00161, _kg,      "waste mineral oil"),
            ("waste_plastic",             -0.0248, _kg,      "waste plastic, mixture"),
            ("waste_pvf",               -0.000902, _kg,      "waste polyvinylfluoride"),
            ("waste_wafer",              -0.00352, _kg,      "waste, from silicon wafer production"),
        ],
        biosphere=[
            ("co2_fossil", 0.0218, _kg,      "carbon dioxide, fossil"),
            ("heat_waste",   13.4, _MJ,      "heat, waste"),
            ("water",      0.0279, _kg,      "water"),
        ],
        # not carried - mangled rows in the source PDF (UPV-DEFERRED-ISSUES.md):
        #   Water, cooling, unspecified natural origin 0.0716 m3
        # not carried - ecoinvent v2 flow names with no 3.9.1 match, believed zero GWP:
        #   NMVOC, non-methane volatile organic compounds, unspecified origin 0.00806 kg
    ),
    Activity(
        code=_T["A10"], name="UPV, inverter, 2.7 MWac", reference_product="inverter, 2.7 MWac",
        unit=_unit, location="GB", comment=_smith("A10"),
        technosphere=[
            ("aluminium_wrought",       80, _kg,      "aluminium, wrought alloy"),
            ("cable_cat5",             940, _m,       "cable, network cable, category 5, without plugs"),
            ("cable_three_conductor",   61, _m,       "cable, three-conductor cable"),
            ("capacitor_electrolyte",    5, _kg,      "capacitor, electrolyte type, >2 cm height"),
            ("capacitor_film",          50, _kg,      "capacitor, film type, for through-hole mounting"),
            ("concrete_slab",          1.1, _m3,      "concrete slab"),
            ("copper_cathode",         430, _kg,      "copper, cathode"),
            ("gfrp_polyamide",          30, _kg,      "glass fibre reinforced plastic, polyamide, injection moulded"),
            ("inductor",               650, _kg,      "inductor, ring core choke type"),
            ("integrated_circuit",     0.2, _kg,      "integrated circuit, logic type"),
            ("lubricating_oil",          1, _kg,      "lubricating oil"),
            ("pwb_through_hole",         3, _kg,      "printed wiring board, through- hole mounted, unspecified, Pb free"),
            ("reinforcing_steel",     1200, _kg,      "reinforcing steel"),
            ("transformer_hv",         100, _kg,      "transformer, high voltage use"),
            ("transistor",             0.3, _kg,      "transistor, wired, big size, through-hole mounting"),
            ("fan",                    0.2, _kg,      "fan, for power supply unit, desktop computer"),
        ],
    ),
    Activity(
        code=_T["A12"], name="UPV, electrical balance of system", reference_product="electrical balance of system",
        unit=_m2, location="GB", comment=_smith("A12"),
        technosphere=[
            ("aluminium_wrought",      0.4, _kg,      "aluminium, wrought alloy"),
            ("epoxy_resin",         4.9e-5, _kg,      "epoxy resin, liquid"),
            ("nylon_6",             0.0064, _kg,      "nylon 6"),
            ("polycarbonate",       6.1e-5, _kg,      "polycarbonate"),
            ("pvc",                   0.11, _kg,      "polyvinylchloride, bulk polymerised"),
            ("wire_drawing_copper",    0.4, _kg,      "wire drawing, copper"),
        ],
    ),
    Activity(
        code=_T["A13"], name="UPV, fence", reference_product="fence",
        unit=_m2, location="GB", comment=_smith("A13"),
        technosphere=[
            ("concrete_25mpa",            2.9e-5, _m3,      "concrete, 25MPa"),
            ("section_bar_rolling_steel",  0.046, _kg,      "section bar rolling, steel"),
            ("steel_low_alloyed",          0.099, _kg,      "steel, low-alloyed"),
            ("wire_drawing_steel",         0.053, _kg,      "wire drawing, steel"),
            ("zinc_coat_coils",           0.0033, _m2,      "zinc coat, coils"),
        ],
    ),
]

# =============================================================================
# Activities — the plant: mounting, capital, O&M, and the grid fleet's kWh
# =============================================================================
_M2 = UPV_PV_M2_PER_MWP
_IEA = f"- {UPV_MOUNT_SOURCE}"

plant_activities = [
    # Fixed-tilt mounting, per m2 of module.
    Activity(
        code=R.UPV_MOUNT, name="UPV, fixed-tilt mounting structure, 20 deg",
        reference_product="fixed-tilt mounting structure, 20 deg",
        unit=_m2, location="GB", comment=_COMMENT,
        technosphere=[
            ("steel_low_alloyed",          UPV_MOUNT_KG_PER_M2["steel_low_alloyed"],      _kg, f"table and piles {_IEA}"),
            ("aluminium_wrought",          UPV_MOUNT_KG_PER_M2["aluminium_wrought"],      _kg, f"clamps {_IEA}"),
            ("chromium_steel",             UPV_MOUNT_KG_PER_M2["chromium_steel"],         _kg, f"fasteners {_IEA}"),
            ("polypropylene",              UPV_MOUNT_KG_PER_M2["polypropylene"],          _kg, f"spacers {_IEA}"),
            ("corrugated_board_box_rer",   UPV_MOUNT_PACKAGING_KG_PER_M2["corrugated_board_box_rer"], _kg,
             f"packaging, not in the stated structure mass {_IEA}"),
            ("section_bar_rolling_steel",  UPV_MOUNT_FORMING_PER_M2["section_bar_rolling_steel"], _kg,
             f"forming of the steel already counted {_IEA}"),
            ("sheet_rolling_aluminium",    UPV_MOUNT_FORMING_PER_M2["sheet_rolling_aluminium"],   _kg,
             f"forming of the aluminium already counted {_IEA}"),
            ("wire_drawing_steel",         UPV_MOUNT_FORMING_PER_M2["wire_drawing_steel"],        _kg,
             f"forming of the chromium steel already counted {_IEA}"),
            ("zinc_coat_pieces",           UPV_MOUNT_FORMING_PER_M2["zinc_coat_pieces"],          _m2,
             f"galvanising of the steel already counted {_IEA}"),
            # The rest of Z-PV-239, carried since 21 Oct 2026: ecoinvent's standard
            # material-to-factory legs (200 / 600 / 100 km on the 9.73 kg), the
            # packaging that leaves as waste, and the land the table occupies. The
            # dataset is cradle-to-gate, so none of this is delivery to site.
            ("lorry",                      1.946,  _tkm, f"materials to the factory, lorry {_IEA}"),
            ("freight_train_rer",          5.838,  _tkm, f"materials to the factory, rail {_IEA}"),
            ("light_commercial_vehicle",   0.973,  _tkm, f"materials to the factory, light commercial vehicle {_IEA}"),
            ("waste_paperboard_incineration_row", -0.0926, _kg, f"packaging cardboard to incineration {_IEA}"),
            ("waste_pe_pp_row",                   -0.00534, _kg, f"PE/PP spacer waste {_IEA}"),
        ],
        biosphere=[
            ("transformation_from_pasture", 2.25, _m2, f"land transformation from pasture {_IEA}"),
            ("transformation_to_industrial", 2.25, _m2,
             f"land transformation to industrial area, built-up 0.25 + vegetation 2 {_IEA}"),
            ("occupation_industrial", 67.5, "square meter-year",
             f"occupation, industrial area, built-up 7.5 + vegetation 60 {_IEA}"),
        ],
    ),
    # The plant, per 1 MWp DC. Capital only - O&M is its own activity.
    Activity(
        code=R.UPV_CAPITAL, name="UPV, utility-scale PV plant, fixed tilt, per MWp",
        reference_product="utility-scale PV plant, fixed tilt, per MWp",
        unit="megawatt", location="GB", comment=_COMMENT,
        technosphere=[
            (FG(R.UPV_MODULE),     _M2, _m2, f"PV modules, {_M2:,.0f} m2 at {UPV_PV_W_PER_M2:.1f} W/m2"),
            (FG(R.UPV_MOUNT),      _M2, _m2, "fixed-tilt mounting, 20 deg (IEA PVPS T12-33:2026)"),
            (FG(_T["A12"]),        _M2, _m2, "electrical balance of system"),
            (FG(_T["A13"]),        _M2, _m2, "perimeter fence"),
            (FG(R.UPV_INVERTER),   UPV_PV_INVERTERS_PER_MWP, _unit,
             f"inverters, {UPV_PV_INVERTERS_PER_MWP:.4f} x {UPV_PV_INVERTER_MVA:g} MVA at the STATED "
             f"ILR {UPV_PV_ILR:g} (Smith's own count implies 1.75)"),
            ("diesel_building_machine", _M2 * UPV_PV_INSTALL_DIESEL_MJ_PER_M2, _MJ,
             "installation energy - Smith A14 diesel only; his transport rows are delivery to "
             "site (outside the boundary) and his component rows are counted above"),
        ],
        biosphere=[
            ("occupation_natural", _M2 * 3.0, "square meter-year",
             "Smith A14: 3 m2*a of 'Occupation, unspecified, natural (non-use)' per m2 of module; "
             "zero GWP100, in since 21 Oct 2026"),
        ],
    ),
    # Thirty years of O&M, per MWp. renewables.py scales this to the study life.
    Activity(
        code=R.UPV_OM30, name="UPV, 30 years of operation and maintenance, per MWp",
        reference_product="30 years of operation and maintenance, per MWp",
        unit="megawatt", location="GB", comment=_COMMENT,
        technosphere=[
            ("petrol_low_sulfur",  _M2 * UPV_PV_OM_PETROL_KG_PER_M2, _kg, "vegetation management - Smith A15"),
            (FG(R.UPV_MODULE),     _M2 * UPV_PV_OM_PANEL_M2_PER_M2, _m2,
             "panel replacement, 0.05 %/yr over 30 y - Smith A15"),
            (FG(R.UPV_INVERTER),   UPV_PV_INVERTERS_PER_MWP * UPV_PV_OM_REPLACEMENT_FRACTION, _unit,
             f"inverter replacement, {UPV_PV_OM_REPLACEMENT_FRACTION:.1%} of the installed count "
             "over 30 y (Mason 10 %/decade) - Smith A15"),
        ],
    ),
    # One kWh from the GB grid's solar fleet: the plant and its 30 years of
    # O&M spread over the lifetime yield. optimiser_lca.grid scores the
    # grid's solar share on this.
    Activity(
        code=R.UPV_GRID_KWH, name="UPV, GB grid solar fleet, electricity per kWh",
        reference_product="electricity, low voltage", unit=_kwh, location="GB",
        comment=_COMMENT + (
            f" Per kWh at {UPV_GRID_FLEET_KWH_PER_KWP:,.0f} kWh/kWp over "
            f"{UPV_GRID_FLEET_YEARS:g} y, ecoinvent's own yield for its GB "
            "570 kWp plant; only the inventory is Smith's."),
        technosphere=[
            (FG(R.UPV_CAPITAL), 1.0 / (UPV_GRID_FLEET_KWH_PER_KWP * 1000.0), "megawatt",
             "plant, per MWp, over its lifetime yield"),
            (FG(R.UPV_OM30), (UPV_GRID_FLEET_YEARS / UPV_PV_OM_REFERENCE_YEARS)
             / (UPV_GRID_FLEET_KWH_PER_KWP * 1000.0), "megawatt",
             "30 years of O&M, per MWp, over the same yield"),
        ],
    ),
]

activities = smith_activities + plant_activities


def inventory() -> Inventory:
    return Inventory(name="utility-scale PV (Smith 2024 on apos)", database=R.SOLAR_DB,
                     processes=processes, flows=flows, activities=activities)


def describe() -> str:
    by_code = {a.code: a for a in activities}
    lines = [f"Source: {UPV_PV_SOURCE}",
             f"  {UPV_PV_W_PER_M2:.1f} W/m2 -> {UPV_PV_M2_PER_MWP:,.0f} m2/MWp; "
             f"{UPV_PV_INVERTERS_PER_MWP:.4f} inverters/MWp at ILR {UPV_PV_ILR:g}",
             "  supply chain: SE Asia import (CN silicon chain, TH cell + module)"]
    for tab, code in R.UPV_TABLES.items():
        a = by_code[code]
        chain = sum(isinstance(k, FG) for k, *_ in a.technosphere)
        lines.append(f"  {tab:<4} {code:<26} {len(a.technosphere) - chain:>3} technosphere, "
                     f"{len(a.biosphere):>2} biosphere, {chain} chain  per {a.production_amount:g} "
                     f"{a.unit} {a.reference_product}")
    lines.append("EXCLUDED and why: " + "; ".join(f"{k}: {v}" for k, v in UPV_PV_SCOPE.items()
                                                 if "EXCLUDED" in v))
    return "\n".join(lines)
