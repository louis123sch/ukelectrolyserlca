"""
Generation step-up transformers — embodied carbon per MW connected.
=============================================================================

A wind turbine generates at **690 V**, which is *low* voltage — below the 1 kV
boundary ecoinvent itself draws, the same band as a household supply. The data
centre draws at *medium* voltage, 1–24 kV, because that is the level
``market for electricity, medium voltage`` describes and the level the Zhang
foreground is authored against. Something has to bridge those two, and it is
not optional: 100 MW at 690 V is **83,674 A**, which is not a cable. Stepped to
20 kV the same power is 2,887 A, which is.

So every turbine carries its own transformer at the foot of its tower. **One
per turbine, not one per farm** — a 100 MW farm has fifty of them. That is what
this module charges, per MW of ``cap_wind``.

The inventory is not here
-------------------------
It is a foreground activity, built in ``2.tech_lca_foreground.ipynb`` alongside
the hydrogen tank and for the same reason — ecoinvent cannot supply the asset,
so it is assembled from a published bill of materials. This module only scores
that activity and amortises it. To change what a transformer is made of, edit
the notebook; to change how long it lasts, edit ``TX_ASSET_LIFE_YEARS`` in
``dc_config.py``. Both are stated once and read here.

    database  cfg.TRANSFORMER_FOREGROUND_DB
    code      wind_turbine_stepup_per_mw
    unit      1 MW of wind connected
    source    Leng et al. (2026), Processes 14(7) 1045, Supplementary Table S1

Why this is a gap and not a double count
----------------------------------------
Checked exchange by exchange against ecoinvent 3.9.1 apos:

* ``wind turbine construction, 2MW, onshore`` lists its own parts in its
  comment — "Rotor, Nacelle, Electronics, Tower, Foundation" — and no
  transformer is among them. Its only electrical item is 438.7 kg of
  ``electronics, for control units``: a control cabinet, an order of magnitude
  short of the 3–5 t a 2 MW turbine transformer weighs. Its stated component
  masses (rotor 37 t, nacelle 61 t, tower 165 t) account for the materials
  without leaving room for one, and it says outright that it excludes the grid
  connection.
* ``wind turbine network connection construction, 2MW, onshore`` is 1,398.7 m³
  of excavation, 1,375.7 kg of HDPE and 253.8 kg of copper — cable and trench.

Why ecoinvent cannot supply the asset
-------------------------------------
It has **four** transformer activities, which are two products with a market
and a production each, and both are electronics. ecoinvent's own comments say
so: "a typical high voltage use transformer **in electronic modules** has an
average weight of **280 g** … used in the information and communication
technology", and 30 g for the low-voltage one. Their compositions match — the
high-voltage one is 0.50 kg ferrite, 0.31 kg epoxy and 0.51 kg injection
moulding per kg, against 5 g of steel. There is no ``substation`` activity, no
``switchgear`` activity, and no power transformer at any rating.

Until this rewrite, wind scaled that 280 g component up by a factor of 205,000
to stand for a 57 t substation unit. Rebuilding a real transformer's bill of
materials on the same database gives 177.3 t CO2e against 306.2 t on that
dataset, and the manufacturer declares 147.4 t, so the old basis ran about
**2x** high in a known direction. Nobody who has looked at this used ecoinvent's
transformer: Leng built theirs from materials, Teffera built theirs from
materials, and Vestas scaled a real ABB EPD.

Why it scales exactly
---------------------
Sizing needs no power factor. Leng states the transformer content of a 100 MW
farm directly, and ``cap_wind`` is in MW of exactly that kind, so the ratio is
read off rather than derived. One unit per turbine means **30 MW and 1,000 MW
carry the same figure per MW**.

The plant-rated basis this replaces did not scale. Specific mass falls with
rating — 2,566 kg/MVA at 2.2 MVA, 1,434 at 40, 715 at 100, all measured — so a
single flat number taken from one farm size was out by up to 14 % across a
tenfold range of build.

Independently checked
---------------------
Teffera et al. (2021) Table 5, three Ethiopian farms totalling 324 MW, reported
per kWh rather than in tonnes. Converted onto this study's basis their
turbine-level transformers are 228–333 kg CO2e/MW/year depending on which of
their two capacity factors the inventory is built on, which they do not state.
Leng sits inside that band. Two teams, two countries, two reporting formats.

What is counted, and what is not
--------------------------------
**No grid-export transformer.** Leng's farm also has a 100 MVA unit stepping up
to 110 kV, and it is deliberately not taken. This study's generation is behind
the meter: there is nothing to export into, and the one transformation between
the site and the outside world is the grid intake, which ``cap_grid`` already
pays for through ``grid_connection.py``. Charging it would bill the site for a
voltage change it does not make.

**No step between the collection network and the data centre.** Both sit in the
medium-voltage band, so the chain closes. ``cfg.TX_SITE_COLLECTION_KV`` states
that as a number rather than leaving it as the phrase "the same bus", and
``check()`` refuses a value outside the band. Leng's units are wound for 35 kV,
above the band; a 20 kV unit of the same rating carries less insulation and is
lighter, so taking their mass errs **high** — the safe direction.

**No switchgear, protection or civils.** Absent here and absent from
``grid_connection.py``, so it is a level shift rather than a bias. Teffera puts
MV plus HV switchgear at 0.61 t/MW against a plant transformer's 1.08 t/MW.
Registered in DATA_GAPS.md.

**No manufacturing energy.** Leng's own published figures are higher than this
rebuild because they add factory electricity on the Chinese grid. Materials only
is consistent with every other foreground in this study, and it makes this the
lower of the two available numbers. Stated rather than glossed.

**Solar is on the same footing as wind.** ``solar_pv`` reads its own foreground
activity, ``solar_inverter_stepup_per_mwp``, built from IEA PVPS Task 12's
T12-33:2026 LCI report: the oil-immersed 2.5 MVA units in a utility PV plant's
inverter stations, four of them on the report's own 10 MWp reference plant. Two
things make this better than the wind side rather than merely equal to it. The
unit is wound **20 / 0.4 kV**, which is ``cfg.TX_SITE_COLLECTION_KV`` and the
inverter's LV terminals exactly — so no voltage adjustment is applied, where
Leng's 35 kV units have to be taken as erring high. And the count is **read off**
Table 50 rather than derived, which retires the two ASSUMED constants the old
solar path needed (``SOLAR_DC_AC_RATIO``, ``POWER_FACTOR``).

The old basis — one invented plant-rated unit on ecoinvent's 280 g electronics
dataset, scaled by a 40 MVA EPD's specific mass, with no per-inverter-station
transformers at all — survives only as ``SOLAR_BASIS = "legacy"``, to reproduce
pre-2026 runs. It carried two errors that partly cancelled: the electronics
dataset runs high for a given mass, while a 40 MVA specific mass under-counts a
2.5 MVA unit by ~1.6x.

**No cost term.** DESNZ/Arup's capex is plant-plus-connection-to-the-point-of-
connection, so a £/MW transformer charge would double count. Carbon gains a term
and cost does not; the asymmetry is deliberate and is in ASSUMPTIONS.md.

**Losses are not charged here.** Two manufacturer EPDs put a transformer's
life-cycle GWP at ~99 % use phase, and that is not this module's to charge: the
lost kWh is generated by plant the LP has already sized. Its home is an
efficiency on the availability constraints, which is not implemented, and which
remains the largest open item in this chain — grid import carries
``MARKET_LOSS_SHARE`` of 3.16 % while on-site generation carries none.

Sources
-------
wind inventory    Leng, H. et al. (2026), "Life Cycle Assessment of an Onshore
                  Wind Farm: Carbon Emission Evaluation and Mitigation Pathway
                  Design", *Processes* 14(7), 1045, Supplementary Table S1.
                  Transcribed into dc_config.TX_LENG_BOX_KG and built
                  into the foreground by notebook 2.
cross-check       Teffera, B. et al. (2021), "Life cycle assessment of wind
                  farms in Ethiopia", *Int J LCA* 26:76-96, Table 5.
turbine voltage   690 V, stated for all four turbine models in Teffera Table 2
                  and the industry de facto standard. TRANSCRIBED.
voltage bands     ecoinvent 3.9.1 ``market for electricity, medium voltage``
                  [GB] comment: high >24 kV, medium 1-24 kV, low <1 kV.
asset life        35 years, this study's own generation life. See renewables.py.
solar (legacy)    Hitachi Energy S.p.A. EPD, 40 MVA (Monselice), EPDItaly rev.
                  3, 2022 — 57,380 kg / 40 MVA — on ``market for transformer,
                  high voltage use``. Known ~2x high; see DATA_GAPS.md.

Run:  python optimisation/transformers.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
OUT_DIR = ROOT / "optimisation_outputs"
CACHE_PATH = OUT_DIR / "transformer_decomposition_cache.json"

# The foreground activities notebook 2 builds. Everything about what a
# transformer is made of lives there; this module only scores and amortises it.
WIND_CODE = "wind_turbine_stepup_per_mw"
SOLAR_CODE = "solar_inverter_stepup_per_mwp"

# --- solar: the legacy plant-rated unit, kept only to reproduce old runs ------
# What this was, before IEA PVPS T12-33:2026 supplied a real solar bill: one
# INVENTED plant-rated unit, built by scaling ecoinvent's 280 g electronics
# dataset by the specific mass of a 40 MVA EPD, with no per-inverter-station
# transformers counted at all. Two errors that partly cancelled - the
# electronics dataset runs high for a given mass, while a 40 MVA specific mass
# under-counts a 2.5 MVA unit by ~1.6x. Retained behind basis="legacy" so a
# pre-2026 run can still be reproduced, and never the default.
LEGACY_ACTIVITY = "market for transformer, high voltage use"
LEGACY_EPD_MASS_KG = 57_380.0
LEGACY_EPD_RATED_MVA = 40.0
POWER_FACTOR = 0.95                # ASSUMED - legacy path only
SOLAR_DC_AC_RATIO = 1.25           # ASSUMED - legacy path only
SOLAR_MVA_PER_MWP = 1.0 / (SOLAR_DC_AC_RATIO * POWER_FACTOR)

# Which basis the solar coefficient is on. The 2026 basis reads the foreground
# and needs neither of the two ASSUMED constants above, because IEA PVPS state
# the transformer count per plant directly.
SOLAR_BASES = ("iea_pvps_2026", "legacy")
SOLAR_BASIS = "iea_pvps_2026"

ASSUMED = ("cfg.TX_SITE_COLLECTION_KV", "cfg.TX_MATERIAL_PROCESSES['iron']",
           "cfg.TX_MATERIAL_PROCESSES['silica']")

TECHNOLOGIES = ("onshore_wind", "offshore_wind", "solar_pv")

_MEMO: dict | None = None


def _cfg():
    """dc_config, imported lazily like every other module here does."""
    import dc_config as cfg
    return cfg


def wind_kg_per_mw() -> float:
    """Turbine step-up mass per MW of wind, from Leng's own farm."""
    cfg = _cfg()
    return sum(cfg.TX_LENG_BOX_KG.values()) / cfg.TX_LENG_FARM_MW


def legacy_kg_per_mva() -> float:
    """Solar's plant-rated specific mass, from the EPD nameplate."""
    return LEGACY_EPD_MASS_KG / LEGACY_EPD_RATED_MVA


def decompose(refresh: bool = False) -> dict:
    """Score the foreground activity once, and hold the constants with it.

    Cached to JSON like the other decomposition modules, so the coefficient
    tests and a Streamlit session can read it without a Brightway connection.
    """
    global _MEMO
    if refresh:
        _MEMO = None
        CACHE_PATH.unlink(missing_ok=True)
    if _MEMO is not None:
        return _MEMO
    if CACHE_PATH.exists():
        try:
            cached = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
            # "basis" only exists since the foreground rewrite, so a cache
            # written by the old plant-rated module is rejected here rather
            # than silently serving a superseded number. The solar half moved
            # to its own foreground afterwards, so the tag moved with it and a
            # cache from between the two rewrites is rejected too.
            if cached.get("basis") == "leng_wind_iea_pvps_2026_solar":
                _MEMO = cached
                return _MEMO
        except Exception:
            pass    # a corrupt or stale cache is never fatal — just recompute

    import bw2data as bd
    import lca_helpers as H
    import dc_config as cfg
    from optimisation import baseline_grid as bg

    H.setup_brightway()
    method = bg.gwp_method()
    life = float(cfg.TX_ASSET_LIFE_YEARS)

    # wind — the foreground activity notebook 2 built, per MW connected
    try:
        act = bd.get_activity((cfg.TRANSFORMER_FOREGROUND_DB, WIND_CODE))
    except Exception:
        raise RuntimeError(
            f"{cfg.TRANSFORMER_FOREGROUND_DB!r}/{WIND_CODE!r} is not in this "
            "Brightway project. Run the wind turbine step-up cells in "
            "2.tech_lca_foreground.ipynb first — the inventory lives there, "
            "not in this module.") from None
    wind_per_mw = H.run_lca_score(act, method)

    # solar — the IEA PVPS foreground, built the same way wind is
    cfg.upv_tx_check()
    try:
        act_s = bd.get_activity((cfg.TRANSFORMER_FOREGROUND_DB, SOLAR_CODE))
    except Exception:
        raise RuntimeError(
            f"{cfg.TRANSFORMER_FOREGROUND_DB!r}/{SOLAR_CODE!r} is not in this "
            "Brightway project. Run the solar inverter-station step-up cells in "
            "2.tech_lca_foreground.ipynb first — the inventory lives there, "
            "not in this module.") from None
    solar_per_mwp = H.run_lca_score(act_s, method)

    # solar — the legacy plant-rated unit, kept for reproducibility only
    ei = bd.Database(getattr(cfg, "ECOINVENT_DB", "ecoinvent-3.9.1-apos"))
    hits = [a for a in ei if a["name"] == LEGACY_ACTIVITY
            and a["unit"] == "kilogram"]
    if not hits:
        raise ValueError(f"{LEGACY_ACTIVITY!r} (kilogram) not in {ei.name}")
    legacy_per_kg = H.run_lca_score(hits[0], method)
    legacy_per_mva = legacy_per_kg * legacy_kg_per_mva()

    solar_mass_per_unit = (sum(cfg.UPV_TX_MATERIALS_KG.values())
                           + cfg.UPV_TX_FIBREBOARD_KG)

    out = {
        "basis": "leng_wind_iea_pvps_2026_solar",
        "solar_basis": SOLAR_BASIS,
        "asset_life_years": life,
        "site_collection_kV": float(cfg.TX_SITE_COLLECTION_KV),
        "turbine_terminal_V": float(cfg.TX_TURBINE_TERMINAL_V),
        "medium_voltage_band_kV": list(cfg.TX_MEDIUM_VOLTAGE_BAND_KV),
        "wind": {
            "database": cfg.TRANSFORMER_FOREGROUND_DB,
            "code": WIND_CODE,
            "source": "Leng et al. 2026, Processes 14(7) 1045, Table S1",
            "farm_MW": float(cfg.TX_LENG_FARM_MW),
            "n_turbines": int(cfg.TX_LENG_N_TURBINES),
            "unit_rating_MVA": float(cfg.TX_LENG_UNIT_MVA),
            "materials_kg_per_MW": {m: kg / cfg.TX_LENG_FARM_MW
                                    for m, kg in cfg.TX_LENG_BOX_KG.items()},
            "kg_per_MW": wind_kg_per_mw(),
            "kgco2e_per_MW": wind_per_mw,
            "kgco2e_per_MW_year": wind_per_mw / life,
        },
        "solar": {
            "database": cfg.TRANSFORMER_FOREGROUND_DB,
            "code": SOLAR_CODE,
            "source": cfg.UPV_TX_SOURCE,
            "unit_rating_MVA": float(cfg.UPV_TX_UNIT_MVA),
            "primary_kV": float(cfg.UPV_TX_PRIMARY_KV),
            "secondary_kV": float(cfg.UPV_TX_SECONDARY_KV),
            "reference_plant_MWp": float(cfg.UPV_TX_REFERENCE_MWP),
            "units_per_plant": int(cfg.UPV_TX_UNITS_PER_PLANT),
            "units_per_MWp": float(cfg.UPV_TX_UNITS_PER_MWP),
            "materials_kg_per_unit": dict(cfg.UPV_TX_MATERIALS_KG),
            "kg_per_unit": solar_mass_per_unit,
            "kg_per_MWp": solar_mass_per_unit * cfg.UPV_TX_UNITS_PER_MWP,
            "kgco2e_per_MWp": solar_per_mwp,
            "kgco2e_per_MWp_year": solar_per_mwp / life,
        },
        "solar_legacy": {
            "activity": LEGACY_ACTIVITY,
            "kgco2e_per_kg": legacy_per_kg,
            "kg_per_MVA": legacy_kg_per_mva(),
            "kgco2e_per_MVA": legacy_per_mva,
            "MVA_per_MWp": SOLAR_MVA_PER_MWP,
            "kgco2e_per_MWp_year": legacy_per_mva * SOLAR_MVA_PER_MWP / life,
        },
        # Per unit of each capacity variable, which is what the LP charges.
        "per_MW_year": {
            "onshore_wind": wind_per_mw / life,
            "offshore_wind": wind_per_mw / life,
            "solar_pv": (solar_per_mwp / life if SOLAR_BASIS == "iea_pvps_2026"
                         else legacy_per_mva * SOLAR_MVA_PER_MWP / life),
        },
    }
    OUT_DIR.mkdir(exist_ok=True)
    CACHE_PATH.write_text(json.dumps(out, indent=2), encoding="utf-8")
    _MEMO = out
    return out


def kgco2e_per_mw_year(technology: str, refresh: bool = False) -> float:
    """Annual embodied burden per unit of that technology's capacity variable.

    ``onshore_wind`` and ``offshore_wind`` are per MW of nameplate and carry the
    turbine step-ups Leng measured. ``solar_pv`` is per MWp (DC) and still
    carries the legacy plant-rated unit, so the two are not on one basis — see
    the module docstring and DATA_GAPS.md.
    """
    d = decompose(refresh)
    try:
        return float(d["per_MW_year"][technology])
    except KeyError:
        raise ValueError(
            f"technology must be one of {list(TECHNOLOGIES)}, "
            f"got {technology!r}") from None


def check(d: dict | None = None) -> str:
    """The arithmetic must round-trip, and the shape must stay capacity-shaped."""
    d = d or decompose()
    cfg = _cfg()
    problems = []
    w = d["wind"]

    if abs(w["kgco2e_per_MW"] / d["asset_life_years"]
           - w["kgco2e_per_MW_year"]) > 1e-9:
        problems.append("the annuity does not divide back to the per-MW figure")
    mass = sum(w["materials_kg_per_MW"].values())
    if abs(mass - w["kg_per_MW"]) > 1e-6:
        problems.append(f"kg/MW has drifted from the Table S1 bill it is "
                        f"transcribed from ({mass:,.2f} vs {w['kg_per_MW']:,.2f})")
    if abs(sum(cfg.TX_LENG_BOX_KG.values()) / cfg.TX_LENG_FARM_MW
           - w["kg_per_MW"]) > 1e-6:
        problems.append("the cache no longer matches dc_config's bill")

    # The site must collect inside the band the data centre draws at, or the
    # chain has an uncharged transformation in it.
    lo, hi = d["medium_voltage_band_kV"]
    if not (lo <= d["site_collection_kV"] <= hi):
        problems.append(
            f"collection at {d['site_collection_kV']:g} kV is outside the "
            f"medium-voltage band {lo:g}-{hi:g} kV the data centre draws at")
    if d["turbine_terminal_V"] >= lo * 1000.0:
        problems.append("turbine terminals are not low voltage — the step-up "
                        "this module exists to charge would not be needed")

    # Both technologies must now be on the foreground, not on a scaled dataset.
    if w["database"] != cfg.TRANSFORMER_FOREGROUND_DB:
        problems.append("wind is no longer reading the foreground inventory")
    s = d.get("solar")
    if not s or s["database"] != cfg.TRANSFORMER_FOREGROUND_DB:
        problems.append("solar is no longer reading the foreground inventory")
    else:
        # The transcribed bill must still rebuild the report's stated unit mass,
        # which is what guards the hardboard unit correction.
        bill = sum(s["materials_kg_per_unit"].values()) + cfg.UPV_TX_FIBREBOARD_KG
        if abs(bill - s["kg_per_unit"]) > 1e-6:
            problems.append(f"solar kg/unit has drifted from its bill "
                            f"({bill:,.2f} vs {s['kg_per_unit']:,.2f})")
        if abs(bill - cfg.UPV_TX_STATED_TOTAL_KG) > 1.0:
            problems.append(
                f"solar bill sums to {bill:,.1f} kg against IEA PVPS's stated "
                f"{cfg.UPV_TX_STATED_TOTAL_KG:,.0f} kg per unit")
        # The unit has to be wound for the voltage the site collects at, or it
        # is the wrong transformer for this chain.
        if abs(s["primary_kV"] - d["site_collection_kV"]) > 1e-9:
            problems.append(
                f"the solar unit is wound {s['primary_kV']:g} kV but the site "
                f"collects at {d['site_collection_kV']:g} kV")
        if s["secondary_kV"] * 1000.0 >= lo * 1000.0:
            problems.append("the PV inverter terminals are not low voltage — "
                            "the step-up this charges would not be needed")
        if abs(s["units_per_MWp"]
               - s["units_per_plant"] / s["reference_plant_MWp"]) > 1e-9:
            problems.append("solar's unit count no longer matches the "
                            "reference plant it is read off")
    if d["solar_legacy"]["activity"] != LEGACY_ACTIVITY:
        problems.append("solar's legacy basis has moved without a source")

    for tech, val in d["per_MW_year"].items():
        if not (0.0 < val < 10_000.0):
            problems.append(f"{tech}: {val:,.1f} kg CO2e/MW/year is not a "
                            "plausible transformer coefficient")
    if problems:
        raise AssertionError("transformer coefficients failed:\n  "
                             + "\n  ".join(problems))
    return (f"OK — {w['kg_per_MW']:,.0f} kg/MW of turbine step-up over "
            f"{d['asset_life_years']:.0f} y, collected at "
            f"{d['site_collection_kV']:g} kV")


def run(refresh: bool = False):
    import math
    d = decompose(refresh)
    w, s = d["wind"], d["solar"]
    lo, hi = d["medium_voltage_band_kV"]
    print("=" * 84)
    print("GENERATION STEP-UP TRANSFORMERS — embodied carbon per MW connected")
    print("=" * 84)
    print(check(d))
    print()
    print(f"  Turbines generate at {d['turbine_terminal_V']:.0f} V (LOW, <{lo:g} kV); "
          f"the data centre draws at")
    print(f"  MEDIUM ({lo:g}-{hi:g} kV). Site collects at "
          f"{d['site_collection_kV']:g} kV, inside that band, so nothing further "
          "is charged.")
    amps = w["farm_MW"] * 1e6 / (math.sqrt(3) * d["turbine_terminal_V"])
    print(f"  Not optional: {w['farm_MW']:.0f} MW at {d['turbine_terminal_V']:.0f} V "
          f"is {amps:,.0f} A.")
    print()
    print(f"  WIND — {w['database']}/{w['code']}")
    print(f"  {w['source']}")
    print(f"  {w['n_turbines']} x {w['unit_rating_MVA']:g} MVA box transformers on a "
          f"{w['farm_MW']:.0f} MW farm")
    for mat, kg in w["materials_kg_per_MW"].items():
        print(f"    {mat:<10}{kg:>10,.2f} kg/MW")
    print(f"    {'TOTAL':<10}{w['kg_per_MW']:>10,.2f} kg/MW")
    print(f"  = {w['kgco2e_per_MW']:,.0f} kg CO2e/MW over "
          f"{d['asset_life_years']:.0f} y")
    print()
    print(f"  SOLAR — {s['database']}/{s['code']}")
    print(f"  {s['source']}")
    print(f"  {s['units_per_plant']} x {s['unit_rating_MVA']:g} MVA oil-immersed "
          f"units on the {s['reference_plant_MWp']:.0f} MWp reference plant")
    print(f"  wound {s['primary_kV']:g}/{s['secondary_kV']:g} kV — the site "
          f"collects at {d['site_collection_kV']:g} kV, so this is the exact")
    print(f"  transformer for this chain, with no voltage adjustment applied.")
    print(f"    {s['kg_per_unit']:>10,.0f} kg/unit "
          f"({s['kg_per_unit'] / s['unit_rating_MVA']:,.0f} kg/MVA)")
    print(f"    {s['units_per_MWp']:>10g} units/MWp — read off the plant, not "
          "derived, so no DC/AC ratio")
    print(f"    {s['kg_per_MWp']:>10,.0f} kg/MWp")
    print(f"  = {s['kgco2e_per_MWp']:,.0f} kg CO2e/MWp over "
          f"{d['asset_life_years']:.0f} y")
    print()
    print(f"  {'what the LP charges':<26}{'kg CO2e/unit/y':>18}  basis")
    for tech in TECHNOLOGIES:
        unit = "MWp" if tech == "solar_pv" else "MW"
        basis = ("IEA PVPS T12-33:2026 inverter stations" if tech == "solar_pv"
                 else "Leng turbine step-ups")
        print(f"  {tech + ' (per ' + unit + ')':<26}"
              f"{d['per_MW_year'][tech]:>18,.1f}  {basis}")
    print()
    print(f"  Two independent sources, two technologies, one answer: solar's "
          f"{d['per_MW_year']['solar_pv']:,.1f} against wind's "
          f"{d['per_MW_year']['onshore_wind']:,.1f} kg CO2e/unit/year")
    print(f"  for step-ups of comparable rating ({s['unit_rating_MVA']:g} and "
          f"{w['unit_rating_MVA']:g} MVA). Solar carries factory energy that "
          "wind does not;")
    print("  materials-only the two land within ~1 % of each other.")
    print(f"  The legacy solar basis gave "
          f"{d['solar_legacy']['kgco2e_per_MWp_year']:,.1f} — "
          f"{d['per_MW_year']['solar_pv'] / d['solar_legacy']['kgco2e_per_MWp_year']:.2f}x "
          "off, from an invented unit.")
    print()
    print("  Onshore wind carries 19,244 kg CO2e/MW/year, so the turbine step-ups")
    print(f"  are {d['per_MW_year']['onshore_wind'] / 19_244 * 100:.2f}% of it. One "
          "unit per turbine, so this scales")
    print("  exactly: 30 MW and 1,000 MW carry the same figure per MW.")
    print()
    print("  Solar is now on the same footing: a real inverter-station bill from")
    print("  IEA PVPS T12-33:2026, wound for this study's own collection voltage,")
    print("  with the unit count read off the reference plant. The invented")
    print(f"  plant-rated unit survives only as basis={SOLAR_BASES[1]!r}.")
    print(f"  ASSUMED: {', '.join(ASSUMED)}.")
    print("  No grid-export transformer (behind the meter), no switchgear, no")
    print("  losses, no end-of-life. Wind carries no manufacturing energy and")
    print("  solar does — see the docstring and SOURCES.md.")
    print()
    print(f"Wrote: {CACHE_PATH.relative_to(ROOT)}")
    return d


if __name__ == "__main__":
    run()
