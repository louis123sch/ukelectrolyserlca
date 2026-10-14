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
inverters, installation energy, 30 years of O&M (rescaled to the study's life
by ``renewables.py``). Excluded, each with its direction: end-of-life (as
everywhere in this study); construction transport — the sea leg alone is
201 t·km/m² for the import chain, so this understates by ~1.5 %; the step-up
transformer, charged elsewhere. Supply chain: SE Asia import case — China
national grid for the silicon chain, Thailand for cell and module.

**How it is verified.** 290 of 290 scientific-notation values in Appendix A
appear in the transcription; 251 rows association-checked against the PDF,
249 clean (the 2 flagged are zero-GWP flows). Of 79 biosphere rows, exactly
four carry a non-zero GWP100 factor — the silicon CO₂ and the two fluorinated
cell gases — and all four are in. A8 lands at 684 kg CO₂e/kWdc; Smith states
his average-import module sits above the 630 kg CO₂e/kW EPEAT threshold, and
it does (``tests/test_coefficients.py``).

The bill is frozen at ``optimisation/data/upv_smith_bill.json`` — the parsing
heuristics ran once and what ships is their reviewed output. Issues knowingly
parked are in ``optimisation/data/UPV-DEFERRED-ISSUES.md``.

**Biosphere compartments.** Smith's biosphere rows name a substance, not a
compartment. The original build matched each by name to the *first* flow of
that name in the biosphere database — an accident of iteration order, which
has since changed (re-running that match today lands on different
compartments). The compartments the original build actually used are pinned
in ``BIOSPHERE_CATEGORIES`` below so the inventory is reproducible. The four
GWP-carrying flows (fossil CO₂ to air, CF₄, C₂F₆) are in sensible
compartments; the zero-GWP rest are arbitrary (cyanide to air, fluoride to
soil, waste heat to forestry soil) and must be fixed before any non-GWP
category is used.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from optimiser_lca import registry as R
from optimiser_lca.common import FG, Activity, Flow, Inventory, Process

ROOT = Path(__file__).resolve().parent.parent

# =============================================================================
# Parameters
# =============================================================================
UPV_PV_SOURCE = ("Smith et al. (2024), NREL/TP-7A40-87372, Appendix A "
                 "(inventory rescored on ecoinvent 3.9.1 apos)")
UPV_PV_BILL = ROOT / "optimisation" / "data" / "upv_smith_bill.json"

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
                "SUBSTITUTED for Smith's single-axis tracker. Near mass-neutral: 9.730 vs "
                "9.764 kg/m2, so the swap removes the motor, Li-ion cell and control "
                "electronics rather than buying a lighter structure.",
    "end_of_life": "EXCLUDED (Smith A16-A23), as everywhere else in this study.",
    "construction_transport": "EXCLUDED (Smith A14 rail/lorry/sea rows). The sea leg alone is "
                              "201 t*km/m2 for the import chain, so this UNDERSTATES by ~1.5 %.",
    "operation_maintenance": "INCLUDED (Smith A15): the basis being replaced is full-scope and "
                             "dropping O&M would be a scope change disguised as a data change. "
                             "Minus the tracker actuator, and minus the transformer.",
    "step_up_transformer": "EXCLUDED here, charged by stepup_transformers at 20/0.4 kV. Smith's "
                           "own A11 is unusable at 19,796 kg/MVA, ~9x the measured specific mass.",
    "supply_chain": "SE Asia import case - China national grid for the silicon chain, Thailand "
                    "for cell fabrication and module assembly.",
}

# --- operation and maintenance (Smith Table A15, per m2 over 30 years) ---------
UPV_PV_OM_REFERENCE_YEARS  = 30.0
UPV_PV_OM_PETROL_KG_PER_M2 = 5.50e-2      # vegetation management. TRANSCRIBED.
UPV_PV_OM_PANEL_M2_PER_M2  = 1.50e-2      # 0.05 %/yr panel replacement
# Inverter replacement as a FRACTION of the installed count: Smith charges
# 1.30E-05/m2 in A15 against 4.30E-05/m2 installed in A14 -> 30 % over 30 y.
UPV_PV_OM_REPLACEMENT_FRACTION = 1.30e-5 / 4.30e-5
UPV_PV_INSTALL_DIESEL_MJ_PER_M2 = 2.6     # Smith A14. TRANSCRIBED.

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
    "zinc_coating_pieces":       0.514041839135378,  # m2
}
UPV_MOUNT_PACKAGING_KG_PER_M2 = {"corrugated_board": 0.09259259259259259}
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
        if "mount_" + k not in processes:
            raise AssertionError(f"no ecoinvent process mapped for mounting row {k!r}")
    if abs(UPV_PV_M2_PER_MWP * UPV_PV_W_PER_M2 - 1e6) > 1.0:
        raise AssertionError("m2/MWp does not invert the module power density")
    return (f"OK - {mass:.3f} kg/m2 of fixed-tilt structure, {UPV_PV_M2_PER_MWP:,.0f} m2/MWp at "
            f"{UPV_PV_W_PER_M2:.1f} W/m2, {UPV_PV_INVERTERS_PER_MWP:.4f} inverters/MWp at ILR "
            f"{UPV_PV_ILR:g}")


# The bill's unit strings -> Brightway's.
_UNITS = {"kg": "kilogram", "t": "tonne", "m2": "square meter", "m3": "cubic meter",
          "m": "meter", "MJ": "megajoule", "kWh": "kilowatt hour", "Item(s)": "unit",
          "t*km": "ton kilometer", "unit": "unit"}

# Compartment each of Smith's biosphere substances was matched to (see docstring).
BIOSPHERE_CATEGORIES = {
    "Aluminium": ("natural resource", "in ground"),
    "Antimony": ("natural resource", "in ground"),
    "Arsenic": ("natural resource", "in ground"),
    "BOD5, Biological Oxygen Demand": ("water", "surface water"),
    "Boron": ("air", "urban air close to ground"),
    "COD, Chemical Oxygen Demand": ("water", "ocean"),
    "Cadmium": ("natural resource", "in ground"),
    "Calcium": ("natural resource", "in ground"),
    "Carbon dioxide, fossil": ("air",),
    "Carbon dioxide, non-fossil": ("air",),
    "Carbon monoxide, fossil": ("air", "urban air close to ground"),
    "Chloride": ("water",),
    "Chlorine": ("water", "surface water"),
    "Chromium III": ("soil", "industrial"),
    "Cyanide": ("air", "low population density, long-term"),
    "DOC, Dissolved Organic Carbon": ("water", "ocean"),
    "Ethane, hexafluoro-, HFC-116": ("air", "urban air close to ground"),
    "Fluoride": ("soil", "agricultural"),
    "Fluorine": ("air", "low population density, long-term"),
    "Heat, waste": ("soil", "forestry"),
    "Hydrocarbons, unspecified": ("soil", "agricultural"),
    "Hydrogen fluoride": ("air", "low population density, long-term"),
    "Hydrogen sulfide": ("air", "lower stratosphere + upper troposphere"),
    "Hydroxide": ("water", "surface water"),
    "Iron": ("natural resource", "in ground"),
    "Lead": ("natural resource", "in ground"),
    "Mercury": ("natural resource", "in ground"),
    "Methane, tetrafluoro-, R-14": ("air", "non-urban air or from high stacks"),
    "Nitrogen": ("air",),
    "Nitrogen oxides": ("air", "lower stratosphere + upper troposphere"),
    "Particulate Matter, > 10 um": ("air", "urban air close to ground"),
    "Phosphate": ("water", "ground-"),
    "Potassium": ("natural resource", "in ground"),
    "Silicon": ("water", "surface water"),
    "Silver": ("natural resource", "in ground"),
    "Sodium": ("soil",),
    "Sulfur dioxide": ("air", "urban air close to ground"),
    "TOC, Total Organic Carbon": ("water", "surface water"),
    "Tin": ("natural resource", "in ground"),
    "Water": ("water", "ocean"),
}


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


# =============================================================================
# Processes and flows — generated from the frozen bill, one per distinct row
# =============================================================================
BILL = json.loads(UPV_PV_BILL.read_text(encoding="utf-8"))

processes: dict = {}
flows: dict = {}
_bill_rows: dict = {}      # code -> [(key | FG, amount, unit, note)] technosphere
_bill_bio: dict = {}       # code -> [(flow key, amount, unit, note)]

for _tab, _code in R.UPV_TABLES.items():
    _t = BILL["tables"][_tab]
    _rows, _bio = [], []
    for _r in _t["technosphere"]:
        _ident = (_r["activity"], _r["location"]) + (
            (_r["reference_product"],) if _r.get("reference_product") else ())
        _key = f"{_slug(_r['activity'])}__{_slug(_r['location'])}"
        if _r.get("reference_product"):
            _key += "__" + _slug(_r["reference_product"])
        processes.setdefault(_key, Process(identity=_ident,
                                           query=f"{_r['activity']} {_r['location']}",
                                           why=_r.get("note", "")))
        _amt = -_r["amount"] if _r.get("waste") else _r["amount"]
        _rows.append((_key, _amt, _UNITS[_r["unit"]], f"{_r['flow']} - Smith Table {_tab} ({_r['note']})"))
    for _r in _t["biosphere"]:
        if not _r["matched"]:
            continue
        _name = _r["ecoinvent_flow"]
        _cats = BIOSPHERE_CATEGORIES[_name]
        _fkey = "bio_" + _slug(_name)
        flows.setdefault(_fkey, Flow(identity=(_name, _cats), query=_name))
        _bio.append((_fkey, _r["amount"], _UNITS[_r["unit"]], f"{_r['flow']} - Smith Table {_tab}"))
    for _r in _t["chain_links"]:
        _rows.append((FG(R.UPV_TABLES[_r["table"]]), _r["amount"], _UNITS[_r["unit"]],
                      f"{_r['flow']} - Smith Table {_tab} -> {_r['table']}"))
    _bill_rows[_code] = _rows
    _bill_bio[_code] = _bio

# Mounting, installation and O&M processes — locations pinned.
processes.update({
    "mount_steel_low_alloyed":  Process(identity=("market for steel, low-alloyed", "GLO"),
                                        query="market for steel low-alloyed GLO"),
    "mount_aluminium_wrought":  Process(identity=("market for aluminium, wrought alloy", "GLO"),
                                        query="market for aluminium wrought alloy GLO"),
    "mount_chromium_steel":     Process(identity=("market for steel, chromium steel 18/8", "GLO"),
                                        query="market for steel chromium steel 18/8 GLO"),
    "mount_polypropylene":      Process(identity=("market for polypropylene, granulate", "GLO"),
                                        query="market for polypropylene granulate GLO"),
    "mount_corrugated_board":   Process(identity=("market for corrugated board box", "RER"),
                                        query="market for corrugated board box RER"),
    "mount_section_bar_rolling_steel": Process(identity=("market for section bar rolling, steel", "GLO"),
                                               query="market for section bar rolling steel GLO"),
    "mount_sheet_rolling_aluminium":   Process(identity=("market for sheet rolling, aluminium", "GLO"),
                                               query="market for sheet rolling aluminium GLO"),
    "mount_wire_drawing_steel":        Process(identity=("market for wire drawing, steel", "GLO"),
                                               query="market for wire drawing steel GLO"),
    "mount_zinc_coating_pieces":       Process(identity=("market for zinc coat, pieces", "GLO"),
                                               query="market for zinc coat pieces GLO"),
    "install_diesel": Process(identity=("market for diesel, burned in building machine", "GLO"),
                              query="market for diesel burned in building machine GLO"),
    "om_petrol":      Process(identity=("petrol production, low-sulfur", "RoW"),
                              query="petrol production low-sulfur RoW",
                              why="vegetation management fuel, Smith A15"),
})

check()

# =============================================================================
# Activities
# =============================================================================
_UNIT_PRODUCT = {
    "upv_silica_sand": ("tonne", "silica sand"),
    "upv_silicon_metal": ("kilogram", "silicon, metallurgical grade"),
    "upv_polysilicon": ("kilogram", "silicon, solar grade"),
    "upv_cz_ingot": ("kilogram", "silicon, single crystal, Czochralski"),
    "upv_wafer": ("square meter", "single-Si wafer, photovoltaic"),
    "upv_trimethylaluminum": ("kilogram", "trimethylaluminum, purified"),
    "upv_perc_cell": ("square meter", "photovoltaic cell, single-Si wafer"),
    "upv_perc_module": ("square meter", "photovoltaic panel, PERC"),
    "upv_inverter_2700kva": ("unit", "inverter, 2.7 MWac"),
    "upv_electrical_bos": ("square meter", "electrical balance of system"),
    "upv_fence": ("square meter", "fence"),
    R.UPV_MOUNT: ("square meter", "fixed-tilt mounting structure, 20 deg"),
    R.UPV_CAPITAL: ("megawatt", "utility-scale PV plant, fixed tilt, per MWp"),
    R.UPV_OM30: ("megawatt", "30 years of operation and maintenance, per MWp"),
}
# A unit process is written per ONE of its reference product, so Smith's batch
# sizes (92,500 t of sand; 18 kg of TMA) are the production amounts.
_REF_AMOUNT = {c: float(BILL["tables"][t]["reference_amount"]) for t, c in R.UPV_TABLES.items()}

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


def _activity(code, technosphere, biosphere=()):
    unit, product = _UNIT_PRODUCT[code]
    return Activity(code=code, name=f"UPV, {product}", reference_product=product,
                    unit=unit, location="GB", comment=_COMMENT,
                    technosphere=list(technosphere), biosphere=list(biosphere),
                    production_amount=_REF_AMOUNT.get(code, 1.0))


_M2 = UPV_PV_M2_PER_MWP
activities = (
    [_activity(c, _bill_rows[c], _bill_bio[c]) for c in R.UPV_TABLES.values()]
    + [
        # Fixed-tilt mounting, per m2 of module.
        _activity(R.UPV_MOUNT,
                  [("mount_" + k, kg, "kilogram", f"{k} - {UPV_MOUNT_SOURCE}")
                   for k, kg in {**UPV_MOUNT_KG_PER_M2, **UPV_MOUNT_PACKAGING_KG_PER_M2}.items()]
                  + [("mount_" + k, amt, "square meter" if k.startswith("zinc") else "kilogram",
                      f"{k}, forming of mass already counted - {UPV_MOUNT_SOURCE}")
                     for k, amt in UPV_MOUNT_FORMING_PER_M2.items()]),
        # The plant, per 1 MWp DC. Capital only - O&M is its own activity.
        _activity(R.UPV_CAPITAL, [
            (FG(R.UPV_MODULE), _M2, "square meter",
             f"PV modules, {_M2:,.0f} m2 at {UPV_PV_W_PER_M2:.1f} W/m2"),
            (FG(R.UPV_MOUNT), _M2, "square meter", "fixed-tilt mounting, 20 deg (IEA PVPS T12-33:2026)"),
            (FG(R.UPV_TABLES["A12"]), _M2, "square meter", "electrical balance of system"),
            (FG(R.UPV_TABLES["A13"]), _M2, "square meter", "perimeter fence"),
            (FG(R.UPV_INVERTER), UPV_PV_INVERTERS_PER_MWP, "unit",
             f"inverters, {UPV_PV_INVERTERS_PER_MWP:.4f} x {UPV_PV_INVERTER_MVA:g} MVA "
             f"at the STATED ILR {UPV_PV_ILR:g} (Smith's own count implies 1.75)"),
            ("install_diesel", _M2 * UPV_PV_INSTALL_DIESEL_MJ_PER_M2, "megajoule",
             "installation energy - Smith A14 diesel only; his transport rows are "
             "excluded by scope and his component rows are counted above"),
        ]),
        # Thirty years of O&M, per MWp. renewables.py scales this to the study life.
        _activity(R.UPV_OM30, [
            ("om_petrol", _M2 * UPV_PV_OM_PETROL_KG_PER_M2, "kilogram", "vegetation management - Smith A15"),
            (FG(R.UPV_MODULE), _M2 * UPV_PV_OM_PANEL_M2_PER_M2, "square meter",
             "panel replacement, 0.05 %/yr over 30 y - Smith A15"),
            (FG(R.UPV_INVERTER), UPV_PV_INVERTERS_PER_MWP * UPV_PV_OM_REPLACEMENT_FRACTION, "unit",
             f"inverter replacement, {UPV_PV_OM_REPLACEMENT_FRACTION:.1%} of the installed count "
             "over 30 y (Mason 10 %/decade) - Smith A15"),
        ]),
        # One kWh from the GB grid's solar fleet: the plant and its 30 years of
        # O&M spread over the lifetime yield. optimiser_lca.grid scores the
        # grid's solar share on this.
        Activity(
            code=R.UPV_GRID_KWH, name="UPV, GB grid solar fleet, electricity per kWh",
            reference_product="electricity, low voltage", unit="kilowatt hour",
            location="GB", comment=_COMMENT + (
                f" Per kWh at {UPV_GRID_FLEET_KWH_PER_KWP:,.0f} kWh/kWp over "
                f"{UPV_GRID_FLEET_YEARS:g} y, ecoinvent's own yield for its GB "
                "570 kWp plant; only the inventory is Smith's."),
            technosphere=[
                (FG(R.UPV_CAPITAL), 1.0 / (UPV_GRID_FLEET_KWH_PER_KWP * 1000.0), "megawatt",
                 "plant, per MWp, over its lifetime yield"),
                (FG(R.UPV_OM30), (UPV_GRID_FLEET_YEARS / UPV_PV_OM_REFERENCE_YEARS)
                 / (UPV_GRID_FLEET_KWH_PER_KWP * 1000.0), "megawatt",
                 "30 years of O&M, per MWp, over the same yield"),
            ]),
    ]
)


def inventory() -> Inventory:
    return Inventory(name="utility-scale PV (Smith 2024 on apos)", database=R.SOLAR_DB,
                     processes=processes, flows=flows, activities=activities)


def describe() -> str:
    lines = [f"Source: {UPV_PV_SOURCE}", f"  bill: {UPV_PV_BILL.relative_to(ROOT)}",
             f"  {BILL['_verification']}",
             f"  {UPV_PV_W_PER_M2:.1f} W/m2 -> {UPV_PV_M2_PER_MWP:,.0f} m2/MWp; "
             f"{UPV_PV_INVERTERS_PER_MWP:.4f} inverters/MWp at ILR {UPV_PV_ILR:g}",
             "  supply chain: SE Asia import (CN silicon chain, TH cell + module)"]
    for tab, code in R.UPV_TABLES.items():
        t = BILL["tables"][tab]
        lines.append(f"  {tab:<4} {code:<26} {len(_bill_rows[code]) + len(_bill_bio[code]):>3} exchanges "
                     f"({len(_bill_bio[code])} biosphere, {len(t['chain_links'])} chain, "
                     f"{len(t['skipped'])} skipped)  per {t['reference_amount']:g} "
                     f"{t['reference_unit']} {t['reference_product']}")
    lines.append("EXCLUDED and why: " + "; ".join(f"{k}: {v}" for k, v in UPV_PV_SCOPE.items()
                                                 if "EXCLUDED" in v))
    return "\n".join(lines)
