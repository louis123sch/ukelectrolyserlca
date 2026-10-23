"""
The cut-off register — every flow the study leaves out, and how big it is.
=============================================================================

The rule (CUTOFF_RULE_PLAN.md, user, 20 Oct 2026)
---------------------------------------------------
A flow that is in a held source and inside the study's boundary is **always
in**, whatever its size. The boundary excludes exactly three things:
end-of-life, delivery to site (the site is not known) and the facility's
standby generator. Those are ``boundary`` entries here: reported, never tested.

The cut-off test applies only to flows **no held source itemises** — things a
real build has that the sources leave out (switchgear, forming of the tank
steel, Voß's processing materials). Each is estimated at an upper bound and
tested, per technology, by ``optimisation/cutoff.py``:

1. per flow, under **1 %** of its technology's carbon (the coefficient the LP
   charges, per unit of the asset per year);
2. per technology, all unsourced flows together under **5 %**;
3. per decision, adding every unsourced flow back at its upper estimate must
   not change the optimiser's best design (``sensitivity`` knob ``cutoff``).

A flow that fails is **included** — as an estimate on the coefficient
(``status="included_estimate"``) or, where a proper row is cheap, as an
inventory row in its module (``status="included_inventory"``). It is not
argued away. Boundary choices are not cut-offs; their justification is in
ASSUMPTIONS.md §6–7. This is not ecoinvent's "cut-off" *system model*, which
is an allocation choice and an unrelated use of the word.

A ``sourced`` entry is a flow a held source does itemise, inside the boundary,
not yet built because a decision or an amount is pending (Leng's booster
station, D2). It is flagged until it is built; it is never on the 1 % test.

The battery is tested two ways (BATTERY_CUTOFF_ANALYSIS.md §2): an
``energy``-side flow (per usable MWh) at its ceiling ``f / gwp_batt_e``, a
``power``-side flow (per MW of inverter) by its break-even duration against
``H_FLOOR_HOURS``. The fuel cell's denominator is calendar replacements only.

How an entry is written
-----------------------
Python only, like every inventory. ``mass_x_factor`` entries carry the amount
of an ecoinvent dataset per denominator unit per year and the dataset's
scored factor (kg CO₂e per unit, this study's method, ``scored_on`` a date;
``scripts/score_exclusions.py`` re-scores them); ``transcribed`` and
``assumed`` entries carry the estimate directly. ``where`` names the scope
dict or docstring that states the exclusion today, so the register and the
modules cannot drift (``tests/test_cutoff.py``). Lives: wind 35 y, solar 38 y,
battery 15 y, fuel cell BoP 20 y, tank 25 y, grid connection 40 y, facility
25 y — the same amortisation each coefficient uses.
"""
from __future__ import annotations

from dataclasses import dataclass

CUTOFF_FLOW_SHARE = 0.01          # rule 1
CUTOFF_TECHNOLOGY_SHARE = 0.05    # rule 2
H_FLOOR_HOURS = 1.0               # the shortest battery a power-side flow is tested at (Q1)

KINDS = ("cutoff", "boundary", "sourced")
STATUSES = ("excluded", "included_estimate", "included_inventory")
METHODS = ("transcribed", "mass_x_factor", "assumed")

# register key -> (dc_model.CHAINS key or None, the denominator, per year)
TECHNOLOGIES = {
    "wind":             ("wind",          "kg CO2e per MW per year (turbine + step-ups)"),
    "solar":            ("solar",         "kg CO2e per MWp per year (plant + step-ups)"),
    "battery":          ("battery",       "kg CO2e per MW per year (power side) or per usable MWh per year (energy side)"),
    "electrolyser":     ("electrolyser",  "kg CO2e per MW per year"),
    "hydrogen tank":    ("hydrogen tank", "kg CO2e per kg of capacity per year"),
    "fuel cell":        ("fuel cell",     "kg CO2e per MW per year, calendar replacements"),
    "grid connection":  ("grid",          "kg CO2e per MW of connection per year"),
    "grid electricity": ("grid",          "kg CO2e per kWh delivered"),
    "bought hydrogen":  (None,            "kg CO2e per kg delivered"),
    "facility":         (None,            "kg CO2e per year"),
    "all":              (None,            "every technology"),
}


@dataclass(frozen=True)
class Exclusion:
    technology: str
    flow: str
    kind: str                            # cutoff | boundary | sourced
    status: str = "excluded"             # excluded | included_estimate | included_inventory
    side: str | None = None              # battery only: energy | power
    method: str | None = None            # transcribed | mass_x_factor | assumed
    # mass_x_factor: units of the factor's dataset per denominator unit per year
    amount_central: float | None = None
    amount_upper: float | None = None
    factor_identity: tuple | None = None         # ecoinvent (name, location, product)
    factor_unit: str | None = None
    factor: float | None = None                  # kg CO2e per factor_unit, scored
    factor_identity_upper: tuple | None = None   # a second dataset for the upper bound
    factor_upper: float | None = None
    scored_on: str | None = None
    # transcribed / assumed: the estimate itself, kg CO2e per denominator unit per year
    central: float | None = None
    upper: float | None = None
    source: str = ""
    basis: str = ""
    note: str = ""
    where: tuple = ()                    # (module, attribute | "docstring", key | phrase), or a tuple of those

    def locations(self) -> tuple:
        """The (module, attribute, key) triples this entry is stated at."""
        if self.where and isinstance(self.where[0], tuple):
            return tuple(self.where)
        return (self.where,) if self.where else ()

    def estimate(self, which: str = "upper") -> float | None:
        """kg CO2e per denominator unit per year, or None if not yet scored."""
        direct = self.upper if which == "upper" else self.central
        if direct is not None:
            return float(direct)
        amount = self.amount_upper if which == "upper" else self.amount_central
        factor = (self.factor_upper if which == "upper" and self.factor_upper is not None
                  else self.factor)
        if amount is None or factor is None:
            return None
        return float(amount) * float(factor)


# =============================================================================
# Shared estimate bases
# =============================================================================
# Switchgear: Teffera et al. 2021 Table 5 give 0.61 t of MV + HV switchgear per
# MW of wind plant against 1.08 t/MW of transformer. ecoinvent 3.9.1 has no
# switchgear dataset (DATA_GAPS.md, *A power transformer in ecoinvent*), so the
# mass is carried at a per-kg carbon: 2.5 kg CO2e/kg (a steel-and-copper
# assembly, central) and 4.57 kg CO2e/kg (the IEA PVPS transformer's own per-kg
# figure, process energy included — transformers.decompose()['container'],
# upper). ASSUMED until a switchgear EPD is held.
SWITCHGEAR_KG_PER_MW = 610.0
SWITCHGEAR_KGCO2E_PER_KG = (2.5, 4.57)

# Factory energy a transformer bill does not carry (Leng publish none): the IEA
# PVPS unit's own process energy per kg, Table 49 — 2,368.3 kWh and 9,903.8 MJ
# on 5,670 kg — on the GB grid at 0.20 kg CO2e/kWh (central) or a Chinese
# grid at 0.70 (upper), heat at 0.075 kg CO2e/MJ. ASSUMED proxy.
TX_PROCESS_KWH_PER_KG = 2_368.3 / 5_670.0
TX_PROCESS_MJ_PER_KG = 9_903.8 / 5_670.0
TX_ELECTRICITY_KGCO2E_PER_KWH = (0.20, 0.70)
TX_HEAT_KGCO2E_PER_MJ = 0.075


def _tx_factory_energy(kg_per_mw: float, life_years: float) -> tuple[float, float]:
    kwh = TX_PROCESS_KWH_PER_KG * kg_per_mw / life_years
    mj = TX_PROCESS_MJ_PER_KG * kg_per_mw / life_years
    return tuple(kwh * e + mj * TX_HEAT_KGCO2E_PER_MJ for e in TX_ELECTRICITY_KGCO2E_PER_KWH)


def _switchgear(life_years: float, kg_per_unit: float = SWITCHGEAR_KG_PER_MW) -> tuple[float, float]:
    return tuple(kg_per_unit / life_years * f for f in SWITCHGEAR_KGCO2E_PER_KG)


_WIND_TX_FACTORY = _tx_factory_energy(2_823.43, 35.0)       # Leng's box units, kg per MW
_GRID_TX_FACTORY = _tx_factory_energy(2 * 714.586, 40.0)    # Leng's main unit, 2 MVA per MW (N-1)
_TANK_STEEL_KG_PER_KG_H2_YEAR = 313.1 / 25.0                # Gandiglio's 28 bar vessel over the tank's life

# =============================================================================
# The register
# =============================================================================
REGISTER: list[Exclusion] = [
    # ------------------------------------------------------------ battery
    Exclusion(
        "battery", "cell processing materials (NMP make-up, argon, nitrogen, compressed air)",
        "cutoff", side="energy", method="mass_x_factor",
        amount_central=1.9 * 0.01 * 1000 / 0.9 / 15, amount_upper=1.9 * 0.05 * 1000 / 0.9 / 15,
        factor_identity=("market for N-methyl-2-pyrrolidone", "GLO", "N-methyl-2-pyrrolidone"),
        factor_unit="kilogram", factor=6.73, scored_on="2026-10-20",
        source="Voß et al. 2025 §3.1.3 name NMP, argon, N2 and compressed air from Degen's data and give no amounts",
        basis="NMP circulated ~1.9 kg per kWh of cells (about 1:1 with the 1.89 kg/kWh of cathode active "
              "material); make-up at 1 % (central) or 5 % (upper) of the circulation, ASSUMED; argon, "
              "nitrogen and compressed air taken as small beside it. Per usable MWh (÷0.90) per year (÷15).",
        where=("bess", "BESS_SCOPE", "processing_materials")),
    Exclusion(
        "battery", "site installation (crane and commissioning diesel)",
        "cutoff", side="energy", method="mass_x_factor",
        amount_central=100 * 35.95 / 3_008 * 1000 / 0.9 / 15, amount_upper=200 * 35.95 / 3_008 * 1000 / 0.9 / 15,
        factor_identity=("market for diesel, burned in building machine", "GLO", "diesel, burned in building machine"),
        factor_unit="megajoule", factor=0.0878, scored_on="2026-10-20",
        source="no source: Jasper's SI has no installation phase",
        basis="100 L (central) to 200 L (upper) of diesel per 3,008 kWh container, 35.95 MJ/L, ASSUMED. "
              "Site work, not transport, so it is a cut-off item; solar counts its installation diesel (Smith A14).",
        where=("bess", "BESS_SCOPE", "processing_materials")),
    Exclusion(
        "battery", "container switchgear (MV, one per container)",
        "cutoff", status="included_estimate", side="power", method="assumed",
        central=_switchgear(15.0)[0], upper=_switchgear(15.0)[1],
        source="Teffera et al. 2021 Table 5 (mass); no switchgear dataset in ecoinvent 3.9.1",
        basis="0.61 t per MW of inverter rating over the battery's 15 years, at 2.5–4.57 kg CO2e/kg (see "
              "SWITCHGEAR_KGCO2E_PER_KG). Power-side: tested by break-even duration against H_FLOOR_HOURS.",
        where=("bess", "BESS_SCOPE", "transformer")),
    # ------------------------------------------------------------ fuel cell
    Exclusion(
        "fuel cell", "container switchgear (MV, one per container)",
        "cutoff", status="included_estimate", method="assumed",
        central=_switchgear(20.0)[0], upper=_switchgear(20.0)[1],
        source="Teffera et al. 2021 Table 5 (mass); no switchgear dataset in ecoinvent 3.9.1",
        basis="0.61 t per MW over the BoP's 20-year calendar life, at 2.5–4.57 kg CO2e/kg. Per MW of cap_fc.",
        where=("fuel_cell", "docstring", "balance of plant")),
    Exclusion(
        "fuel cell", "balance-of-plant assembly energy",
        "cutoff", method="assumed",
        central=50_807 * 0.02 / 20.0, upper=50_807 * 0.05 / 20.0,
        source="Usai et al. 2021 SI Table 1 lists materials and parts only; no assembly energy (a coverage gap of the source)",
        basis="2 % (central) to 5 % (upper) of the BoP's 50,807 kg CO2e per MW per replacement, over its 20-year "
              "calendar life, ASSUMED. The literal follows the BoP coefficient of 21 Oct 2026.",
        where=("fuel_cell", "docstring", "balance of plant")),
    # ------------------------------------------------------------ hydrogen tank
    Exclusion(
        "hydrogen tank", "forming of the vessel steel (rolling, welding)",
        "cutoff", status="included_inventory", method="mass_x_factor",
        amount_central=_TANK_STEEL_KG_PER_KG_H2_YEAR, amount_upper=_TANK_STEEL_KG_PER_KG_H2_YEAR,
        factor_identity=("market for sheet rolling, chromium steel", "GLO", "sheet rolling, chromium steel"),
        factor_unit="kilogram", factor=0.64,
        factor_identity_upper=("market for metal working, average for chromium steel product manufacturing", "GLO",
                               "metal working, average for chromium steel product manufacturing"),
        factor_upper=2.71, scored_on="2026-10-20",
        source="Gandiglio et al. 2022 Table 5 count the steel only; a pressure vessel is rolled and welded",
        basis="313.1 kg of chromium steel per kg of H2 capacity over 25 years; sheet rolling as the lower bound, "
              "average metal working for chromium steel as the upper. Built as a row in h2_tank.py on "
              "22 Oct 2026 (sheet rolling); metal working stays the sensitivity.",
        where=("h2_tank", "TANK_SCOPE", "forming")),
    Exclusion(
        "hydrogen tank", "valves, pipework and fittings",
        "cutoff", status="included_estimate", method="mass_x_factor",
        amount_central=0.01 * _TANK_STEEL_KG_PER_KG_H2_YEAR, amount_upper=0.02 * _TANK_STEEL_KG_PER_KG_H2_YEAR,
        factor_identity=("market for steel, chromium steel 18/8", "GLO", "steel, chromium steel 18/8"),
        factor_unit="kilogram", factor=5.10, scored_on="2026-10-20",
        source="no source: Gandiglio et al. 2022 count the shell only",
        basis="1 % (central) to 2 % (upper) of the shell mass in chromium steel, ASSUMED, over the tank's 25 years.",
        where=("h2_tank", "TANK_SCOPE", "valves_pipework_compressor")),
    Exclusion(
        "hydrogen tank", "compressor hardware",
        "cutoff", method="assumed",
        central=0.01, upper=0.03,
        source="4 Sep 2026 estimate: ~12.8 t CO2e per 300 kW unit (DATA_GAPS.md, *Balance of plant judged negligible*)",
        basis="one 300 kW unit per ~50 t store over 25 years ≈ 0.01 kg CO2e per kg of capacity per year; ×3 upper. "
              "Compressor power is already in cap_ely's draw.",
        where=("h2_tank", "TANK_SCOPE", "valves_pipework_compressor")),
    # ------------------------------------------------------------ wind
    Exclusion(
        "wind", "step-up switchgear (turbine MV switchgear)",
        "cutoff", method="assumed",
        central=_switchgear(35.0)[0], upper=_switchgear(35.0)[1],
        source="Teffera et al. 2021 Table 5 (mass); Leng et al. 2026 Table S1 lists no switchgear",
        basis="0.61 t per MW over the 35-year step-up life at 2.5–4.57 kg CO2e/kg.",
        where=("stepup_transformers", "TX_SCOPE", "switchgear")),
    Exclusion(
        "wind", "step-up transformer replacement rate",
        "cutoff", method="assumed",
        central=0.0, upper=0.302 / 30.0 * 9_755.3,
        source="Leng et al. 2026 publish no replacement rate; Smith 2024 A15 gives 30.2 % of solar's step-ups over 30 years",
        basis="upper: Smith's fraction on the wind unit's transformer-only carbon (9,755 kg CO2e per MW, "
              "transformers.decompose()['wind']['kgco2e_per_MW_transformer']); central: none, as Leng.",
        where=("stepup_transformers", "TX_SCOPE", "switchgear")),
    Exclusion(
        "wind", "step-up transformer factory energy",
        "cutoff", method="assumed",
        central=_WIND_TX_FACTORY[0], upper=_WIND_TX_FACTORY[1],
        source="Leng et al. 2026 publish no factory energy (Table S1 materials, S2 transport, S3 civils; checked 21 Oct 2026)",
        basis="the IEA PVPS unit's process energy per kg (Table 49) on Leng's 2,823 kg per MW, GB grid (central) or "
              "Chinese grid (upper), over 35 years.",
        where=("stepup_transformers", "TX_SCOPE", "switchgear")),
    # ------------------------------------------------------------ solar
    Exclusion(
        "solar", "step-up switchgear (inverter-station MV switchgear)",
        "cutoff", method="assumed",
        central=_switchgear(38.0)[0], upper=_switchgear(38.0)[1],
        source="Teffera et al. 2021 Table 5 (mass); IEA PVPS T12-33:2026 Z-PV-238 lists no switchgear",
        basis="0.61 t per MWp (0.4 units × 2.5 MVA ≈ 1 MVA per MWp) over the plant's 38 years at 2.5–4.57 kg CO2e/kg.",
        where=("stepup_transformers", "TX_SCOPE", "switchgear")),
    # ------------------------------------------------------------ grid connection
    Exclusion(
        "grid connection", "switchgear, protection and the bay",
        "cutoff", status="included_estimate", method="assumed",
        central=_switchgear(40.0)[0], upper=_switchgear(40.0)[1],
        source="Teffera et al. 2021 Table 5 (mass); Leng et al. 2026 S3 'electrical installation' is civils-side only",
        basis="0.61 t per MW of connection over 40 years at 2.5–4.57 kg CO2e/kg. The connection's denominator is a "
              "materials-only transformer at 137.7 kg CO2e/MW/yr, so this fails per technology while being ~0.2 % "
              "of the system (CUTOFF_RULE_PLAN.md Q7).",
        where=("stepup_transformers", "TX_SCOPE", "switchgear")),
    Exclusion(
        "grid connection", "intake transformer factory energy",
        "cutoff", status="included_estimate", method="assumed",
        central=_GRID_TX_FACTORY[0], upper=_GRID_TX_FACTORY[1],
        source="Leng et al. 2026 publish no factory energy for the main transformer either",
        basis="the IEA PVPS unit's process energy per kg on 2 × 714.6 kg per MW (N-1), GB or Chinese grid, over 40 years.",
        where=("stepup_transformers", "TX_SCOPE", "switchgear")),
    Exclusion(
        "grid connection", "substation civils — Leng's outdoor venue (switchyard formation, concrete, rebar)",
        "sourced", status="included_inventory", method="transcribed",
        central=2_157_000 / 100.0 / 40.0, upper=2_157_000 / 100.0 / 40.0,
        source="Leng et al. 2026 Table S3 and Fig. 9c: outdoor venue 34.4 % of the booster station's 6,269 t CO2e per 100 MW",
        basis="in the source and inside the boundary; decision D2 taken 22 Oct 2026: the venue's nine rows per MW of "
              "connection as grid_intake_substation_civils_per_mw; the three buildings covered by Zhang's facility "
              "building (stated substitution). Not on the 1 % test.",
        where=("stepup_transformers", "TX_SCOPE", "grid_intake")),
    Exclusion(
        "grid connection", "booster-station construction machinery (Leng S3), the switchyard's share",
        "sourced", status="included_estimate", method="transcribed",
        central=6_269_000 * 0.009 * 0.344 / 100.0 / 40.0, upper=6_269_000 * 0.009 / 100.0 / 40.0,
        source="Leng et al. 2026 Fig. 9c: construction machinery 0.9 % of the booster station's 6,269 t CO2e per 100 MW",
        basis="sourced and inside the boundary, so in (22 Oct 2026). Leng list the station's machinery once, for all "
              "four building projects, so their own carbon figure for it is pro-rated to the outdoor venue by the "
              "venue's 34.4 % share and carried on the coefficient (central); the whole slice is the upper. Per MW "
              "of connection over 40 years.",
        where=("stepup_transformers", "TX_SCOPE", "machinery")),
    # ------------------------------------------------------------ electrolyser
    Exclusion(
        "electrolyser", "SOEC electrolyte layer — lanthanum oxide and strontium carbonate",
        "cutoff", status="included_inventory", method="assumed",
        central=75.0, upper=150.0,
        source="Gerloff 2021 SI Fig. 5 row 53 names both and points to a sheet not held; the SimaPro model carries 0 kg (#11)",
        basis="first estimate 50 kg La2O3 + 20 kg SrCO3 per unit at ~30 kg CO2e/kg over 20 years, x2 upper. Built on "
              "22 Oct 2026 as ASSUMED rows in hydrogen.py from the layer's geometry (11 kg La2O3 + 2.5 kg SrCO3 per "
              "stack, three stacks), on ecoinvent's own datasets.",
        where=("hydrogen", "H2_SCOPE", "lsm")),
    # ------------------------------------------------------------ facility
    Exclusion(
        "facility", "internal MV/LV electrical distribution (transformers, switchgear)",
        "cutoff", method="assumed",
        central=46_000.0, upper=93_000.0,
        source="Zhang et al. 2025 Table S1 carries no electrical distribution; 4 Sep 2026 bound (DATA_GAPS.md)",
        basis="1.08 t/MW of transformers + 0.61 t/MW of switchgear (Teffera) on a 150 MW facility at 4.57 kg CO2e/kg "
              "over 25 years ≈ 46 t/yr; ×2 upper.",
        where=("data_centre", "DC_SCOPE", "operation")),
    # ------------------------------------------------------------ boundary (reported, never tested)
    Exclusion("all", "end-of-life of every asset", "boundary",
              source="ASSUMPTIONS.md §6", note="cradle-to-gate throughout; APOS carries some EoL in the background",
              where=(("bess", "BESS_SCOPE", "end_of_life"), ("upv", "UPV_PV_SCOPE", "end_of_life"),
                     ("hydrogen", "H2_SCOPE", "end_of_life"), ("h2_tank", "TANK_SCOPE", "end_of_life"),
                     ("data_centre", "DC_SCOPE", "end_of_life"), ("stepup_transformers", "TX_SCOPE", "end_of_life"))),
    Exclusion("electrolyser", "delivery to site — Gerloff's second 250 km lorry leg", "boundary",
              source="ASSUMPTIONS.md §6; Gerloff 2021 §2.1", note="the first leg, to assembly, is in",
              where=("hydrogen", "H2_SCOPE", "transport")),
    Exclusion("solar", "delivery to site — Z-PV-239's 100 km light-commercial leg 'to construction place'", "boundary",
              source="ASSUMPTIONS.md §6; IEA PVPS workbook remark O29", note="out since 22 Oct 2026; was in from 21 Oct",
              where=("upv", "UPV_PV_SCOPE", "construction_transport")),
    Exclusion("battery", "delivery to site — Jasper's China-to-Germany lorry, sea and rail legs for finished parts",
              "boundary", source="ASSUMPTIONS.md §6; Jasper et al. 2026 SI transport rows",
              note="upstream legs to the module and rack factories are in", where=("bess", "BESS_SCOPE", "transport")),
    Exclusion("solar", "delivery to site — Smith A14 rail, lorry and sea rows", "boundary",
              source="ASSUMPTIONS.md §6; Smith 2024 Table A14",
              note="the sea leg alone is 201 t·km/m² for the import chain (~1.5 % of the plant)",
              where=("upv", "UPV_PV_SCOPE", "construction_transport")),
    Exclusion("facility", "delivery to site — Zhang's Transportation phase", "boundary",
              source="ASSUMPTIONS.md §6; Zhang et al. 2025 Table S1", where=("data_centre", "DC_SCOPE", "transport")),
    Exclusion("wind", "delivery to site — Leng Table S2 to-site legs (both transformers)", "boundary",
              source="ASSUMPTIONS.md §6; Leng et al. 2026 Table S2", where=("stepup_transformers", "TX_SCOPE", "delivery")),
    Exclusion("bought hydrogen", "road haulage from the seller to the site", "boundary",
              source="ASSUMPTIONS.md §3; TODO.md (parked)",
              note="trailer compression is charged; the journey depends on where the seller is",
              where=("hydrogen", "H2_SCOPE", "haulage")),
    Exclusion("facility", "standby diesel generator — Zhang's 8.6e6 MJ", "boundary",
              source="ASSUMPTIONS.md §7",
              note="scored and reported by data_centre.py / dc_inputs; out of every objective because backup is a decision variable",
              where=("data_centre", "DC_SCOPE", "genset")),
]


# =============================================================================
# Views and the static check
# =============================================================================
def cutoffs(status: str | None = "excluded") -> list[Exclusion]:
    return [e for e in REGISTER if e.kind == "cutoff" and (status is None or e.status == status)]


def boundaries() -> list[Exclusion]:
    return [e for e in REGISTER if e.kind == "boundary"]


def sourced_pending() -> list[Exclusion]:
    return [e for e in REGISTER if e.kind == "sourced" and e.status == "excluded"]


def by_technology(entries=None) -> dict[str, list[Exclusion]]:
    out: dict[str, list[Exclusion]] = {}
    for e in (REGISTER if entries is None else entries):
        out.setdefault(e.technology, []).append(e)
    return out


def check() -> str:
    """Every entry well-formed; every cutoff entry has an estimate or something to score."""
    problems = []
    seen = set()
    for e in REGISTER:
        tag = (e.technology, e.flow)
        if tag in seen:
            problems.append(f"duplicate entry {tag}")
        seen.add(tag)
        if any(len(loc) != 3 for loc in e.locations()):
            problems.append(f"{tag}: every 'where' is a (module, attribute, key) triple")
        if e.technology not in TECHNOLOGIES:
            problems.append(f"{tag}: unknown technology")
        if e.kind not in KINDS:
            problems.append(f"{tag}: kind {e.kind!r}")
        if e.status not in STATUSES:
            problems.append(f"{tag}: status {e.status!r}")
        if e.side not in (None, "energy", "power") or (e.side and e.technology != "battery"):
            problems.append(f"{tag}: side {e.side!r}")
        if e.technology == "battery" and e.kind == "cutoff" and e.side is None:
            problems.append(f"{tag}: a battery cut-off must say energy or power side")
        if not e.where:
            problems.append(f"{tag}: no 'where' — which module states this exclusion?")
        if e.kind in ("cutoff", "sourced"):
            if e.method not in METHODS:
                problems.append(f"{tag}: method {e.method!r}")
            if e.method == "mass_x_factor":
                if e.factor_identity is None or e.amount_upper is None:
                    problems.append(f"{tag}: mass_x_factor needs factor_identity and amounts")
                if e.factor is None:
                    problems.append(f"{tag}: not yet scored (run scripts/score_exclusions.py)")
            elif e.upper is None:
                problems.append(f"{tag}: no upper estimate")
            if e.estimate("upper") is not None and e.estimate("central") is not None \
                    and e.estimate("central") > e.estimate("upper") + 1e-12:
                problems.append(f"{tag}: central above upper")
        else:
            if e.upper is not None or e.factor is not None:
                problems.append(f"{tag}: a boundary entry carries no estimate")
    if problems:
        raise AssertionError("exclusions register:\n  " + "\n  ".join(problems))
    n_c, n_b, n_s = len(cutoffs(None)), len(boundaries()), len([e for e in REGISTER if e.kind == "sourced"])
    return f"OK - register: {n_c} cut-off entries, {n_b} boundary, {n_s} sourced-pending"


if __name__ == "__main__":
    print(check())
    for tech, entries in by_technology().items():
        print(f"\n{tech}")
        for e in entries:
            est = e.estimate("upper")
            print(f"  [{e.kind:8s} {e.status:18s}] {e.flow[:70]:70s} "
                  + (f"upper {est:,.3g}" if est is not None else "unscored"))
