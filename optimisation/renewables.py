"""
Renewable generation — embodied carbon per MW installed.
=============================================================================

ecoinvent supplies renewable electricity as a **per-kWh** activity, with the
plant's capital burden already amortised over a lifetime output that ecoinvent
chose. That is the right shape for an attributional study of a fixed plant. It
is the wrong shape here, for two reasons:

1. **Capacity is a decision variable.** The optimiser sizes MW; the burden of
   building those MW should not be a function of how much they happen to
   generate in the modelled year.
2. **ecoinvent's implied yield is not this study's yield.** Generation comes
   from Renewables.ninja at a chosen site, and the cost side uses DESNZ/Arup's
   load factors and lifetimes. Neither matches ecoinvent's own assumption, and
   for onshore wind the gap is a factor of 2.5.

So this module strips the capital back out: it reads the plant/turbine unit
exchange from the per-kWh activity, scores that unit, and reports **kg CO2e per
MW installed**. Per-kWh burden is then recomputed at whatever load factor and
lifetime the study actually uses. Nothing is invented - the reconstruction is
checked against ecoinvent's own per-kWh score, which it reproduces exactly.

Every number in this module is listed in ``SOURCES.md`` alongside its
source and provenance grade (transcribed / derived / assumed).

Solar is not scored on ecoinvent, and why
-----------------------------------------
ecoinvent 3.9.1's GB open-ground PV activity is the 570 kWp Solarpark El
Tesoro in Andalusia, **installed in 2008**, carrying 4,401.7 m2 of panel for
570 kWp - a 129.5 W/m2, **12.95 %** module. It restates to 57 g CO2e/kWh,
about ten times onshore wind, which is not a defensible basis for a plant that
has not been built yet. 95.5 % of that burden is in the two exchanges that
scale with panel area, so the vintage is the whole story.

The obvious fixes are both closed. Upgrading the database does nothing: the
plant inventory is byte-identical in ecoinvent 3.10.1, so only the background
would move. And no other GB PV activity exists at utility scale - the only
alternatives are 3 kWp slanted-roof systems of the same vintage.

So the default basis for solar is **IEA PVPS Task 12**, the standard reference
for PV LCA, whose 2023 data update uses the same IPCC 2021 GWP100 method this
study uses throughout: 35.8 g CO2e/kWh for mono-Si at 976 kWh/kWp/year over 30
years, which is 1,048 kg CO2e/kWp of embodied carbon against ecoinvent's
2,303. Their reference yield sits within 10 % of the DESNZ GB solar load
factor, so the figure transfers with no irradiance correction - unusual, and
the reason this substitution is clean rather than a fudge.

Mono-Si, and not the like-for-like multi-Si IEA PVPS also publish, because
``cap_solar`` is a *decision variable* for a plant that does not exist yet, so
the question is what would actually be built. IEA PVPS record multi-Si market
share falling below 3 % in 2022 and to ~1 % in 2023 - they could not update
its parameters for want of current data. That is the same argument this module
already makes about not inheriting ecoinvent's yield for a sized asset, and it
is why multi-Si is not offered as a basis: it would fail the test on exactly
the ground ecoinvent fails it. Its number is kept in SOURCES.md as evidence,
where it answers the reviewer who suspects the technology was switched to
flatter the result.

So there are two bases, and the second exists only to reproduce older runs.
Pass ``solar_basis="ecoinvent"`` for that; both live in
``SOLAR_EMBODIED_BASES``. Wind and offshore wind are untouched, being mostly
steel and concrete and ageing far more slowly than a PV module.

Sources
-------
embodied carbon   ecoinvent 3.9.1 apos, IPCC 2021 GWP100. Activities are the
wind, offshore    GB per-kWh generation datasets and the capital "unit"
                  exchanges they draw on.
embodied carbon   IEA PVPS Task 12, "Environmental Life Cycle Assessment of
solar             Electricity from PV systems - 2023 data update", Stucki M.,
                  Goetz M., de Wild-Scholten M. & Frischknecht R., May 2024.
load factor,      DESNZ/Arup 2024 Cost of Electricity reports, via
lifetime          ``tech_costs.py``. See SOURCES.md.

Run:  python optimisation/renewables.py
"""
import json
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
OUT_DIR = ROOT / "optimisation_outputs"

# (electricity activity name, location, rated kW of the capital unit, cost key)
TECHNOLOGIES = {
    "onshore_wind": (
        "electricity production, wind, 1-3MW turbine, onshore", "GB", 2000.0),
    "offshore_wind": (
        "electricity production, wind, 1-3MW turbine, offshore", "GB", 2000.0),
    "solar_pv": (
        "electricity production, photovoltaic, 570kWp open ground installation, "
        "multi-Si", "GB", 570.0),
}

# ecoinvent's own assumed operating lives, used only to report the load factor
# its amortisation implies. Not used in any calculation.
ECOINVENT_LIFETIME_YEARS = {
    "onshore_wind": 20.0,     # ecoinvent wind turbine, onshore
    "offshore_wind": 20.0,
    "solar_pv": 30.0,         # ecoinvent open-ground PV
}

HOURS_PER_YEAR = 8760.0

# IEA PVPS Task 12, 2023 data update (May 2024). The reference system its
# per-kWh results are quoted against. TRANSCRIBED.
IEA_PVPS_REFERENCE = {
    "yield_kwh_per_kwp_year": 976.0,   # includes linear degradation at 0.7 %/a
    "lifetime_years": 30.0,            # panel; inverter replaced at 15 y
    "in_plane_irradiation_kwh_per_m2": 1331.0,
    "system": "3 kWp rooftop, 1 kWh AC at the grid connection point",
    "method": "IPCC 2021 GWP100",
}

# Where solar's embodied carbon comes from. ``gco2e_per_kwh`` of None means
# "use the figure decomposed out of ecoinvent" - see solar_capital_kgco2e_per_mw.
SOLAR_EMBODIED_BASES = {
    "iea_pvps_2023_mono_si": {
        "gco2e_per_kwh": 35.8, "module_efficiency": 0.209,
        "data_reference_period": "2020-2023",
        "label": "IEA PVPS Task 12 2023 update, mono-Si",
        "grade": "transcribed",
    },
    # IEA PVPS also publish multi-Si at 43.6 g CO2e/kWh (1,277 t CO2e/MWp).
    # Deliberately not offered as a basis: at ~1 % of the 2023 market it fails
    # the same test ecoinvent fails, since cap_solar is capacity that has not
    # been built yet. Its value is as *evidence* rather than as a scenario —
    # holding the technology fixed and updating only the manufacturing still
    # takes 2,303 t/MWp to 1,277, which is what shows this correction is not
    # merely an efficiency story. Recorded in SOURCES.md.
    "ecoinvent": {
        "gco2e_per_kwh": None, "module_efficiency": 0.1295,
        "data_reference_period": "2008 plant",
        "label": "ecoinvent 3.9.1 apos, GB 570 kWp open ground, multi-Si",
        "grade": "transcribed",
    },
}
SOLAR_EMBODIED_BASIS = "iea_pvps_2023_mono_si"
if SOLAR_EMBODIED_BASIS not in SOLAR_EMBODIED_BASES:
    raise ValueError(f"SOLAR_EMBODIED_BASIS must be one of {list(SOLAR_EMBODIED_BASES)}")


def solar_capital_kgco2e_per_mw(basis: str, ecoinvent_value: float) -> float:
    """Embodied carbon per MWp under one basis, in this module's own units.

    A published per-kWh figure carries its author's yield and lifetime, so it
    has to be turned back into a per-capacity number before ``restate()`` can
    put it on this study's yield. That is what the reference system in
    ``IEA_PVPS_REFERENCE`` is for.

    The unit step looks like a missing conversion and is not: g/kWh x
    kWh/kWp/year x years gives g per kWp, and g/kWp and kg/MWp are the same
    number, since both scale by 1000 in numerator and denominator.
    """
    spec = SOLAR_EMBODIED_BASES[basis]
    if spec["gco2e_per_kwh"] is None:
        return ecoinvent_value
    return (spec["gco2e_per_kwh"]
            * IEA_PVPS_REFERENCE["yield_kwh_per_kwp_year"]
            * IEA_PVPS_REFERENCE["lifetime_years"])


def _gwp_method(bd):
    return next(m for m in bd.methods
                if m[1] == "IPCC 2021" and m[2] == "climate change"
                and "GWP100" in str(m) and "no LT" not in str(m))


def decompose(tech, ei, H, method):
    """Split a per-kWh renewable activity into capital per MW and its yield.

    Capital is every technosphere exchange whose input is measured in
    ``unit`` - for wind that is the turbine plus its network connection, for
    PV the plant. Consumables (lubricating oil, water) stay per-kWh.
    """
    name, loc, rated_kw = TECHNOLOGIES[tech]
    act = [a for a in ei if a["name"] == name and a["location"] == loc][0]
    total_per_kwh = H.run_lca_score(act, method)

    capital_per_kwh = 0.0
    units_per_kwh = None
    parts = []
    for exc in act.technosphere():
        if exc.input.get("unit") != "unit":
            continue
        score = H.run_lca_score(exc.input, method)
        amount = float(exc["amount"])
        capital_per_kwh += score * amount
        parts.append((exc.input["name"], score, amount))
        # the largest unit exchange sets the amortisation denominator
        if units_per_kwh is None or amount > units_per_kwh:
            units_per_kwh = amount

    lifetime_kwh_per_unit = 1.0 / units_per_kwh
    lifetime_kwh_per_kw = lifetime_kwh_per_unit / rated_kw
    capital_per_mw = capital_per_kwh / units_per_kwh / (rated_kw / 1000.0)

    ei_life = ECOINVENT_LIFETIME_YEARS[tech]
    implied_lf = lifetime_kwh_per_kw / ei_life / HOURS_PER_YEAR

    return {
        "technology": tech,
        "activity": name, "location": loc, "rated_kW": rated_kw,
        "ecoinvent_per_kWh": total_per_kwh,
        "capital_per_kWh": capital_per_kwh,
        "capital_share": capital_per_kwh / total_per_kwh,
        "capital_kgco2e_per_MW": capital_per_mw,
        # Held separately so it survives whatever basis apply_case selects.
        # check_reconstruction anchors on this one, so the guarantee that the
        # decomposition rebuilds ecoinvent exactly is never quietly retired.
        "ecoinvent_capital_kgco2e_per_MW": capital_per_mw,
        "ecoinvent_lifetime_kWh_per_kW": lifetime_kwh_per_kw,
        "ecoinvent_lifetime_years": ei_life,
        "ecoinvent_implied_load_factor": implied_lf,
        "_parts": parts,
    }


def restate(row, load_factor, lifetime_years):
    """Per-kWh embodied burden at this study's own yield, not ecoinvent's."""
    lifetime_kwh_per_kw = load_factor * HOURS_PER_YEAR * lifetime_years
    eco_per_mw = row.get("ecoinvent_capital_kgco2e_per_MW", row["capital_kgco2e_per_MW"])
    per_kwh = row["capital_kgco2e_per_MW"] / 1000.0 / lifetime_kwh_per_kw
    return {
        "study_load_factor": load_factor,
        "study_lifetime_years": lifetime_years,
        "study_lifetime_kWh_per_kW": lifetime_kwh_per_kw,
        "restated_kgco2e_per_kWh": per_kwh,
        # What ecoinvent's own capital restates to at the same yield. Where a
        # non-ecoinvent basis is in force this separates the two effects: this
        # column moves only with yield, restated_kgco2e_per_kWh with both.
        "ecoinvent_restated_kgco2e_per_kWh": eco_per_mw / 1000.0 / lifetime_kwh_per_kw,
        "ratio_to_ecoinvent": per_kwh / row["ecoinvent_per_kWh"],
    }


CACHE_PATH = OUT_DIR / "renewables_decomposition_cache.json"
_MEMO: list | None = None


def decompose_all(use_cache: bool = True, refresh: bool = False):
    """The Brightway half: every technology's capital burden per MW.

    Deliberately **independent of the cost case** — ecoinvent scoring does not
    depend on which DESNZ scenario is chosen, only the restatement does.

    Each technology costs ~8 s of sparse linear solves, so results are memoised
    in-process and cached to JSON. Without that the sizing optimiser spent
    thirty seconds re-deriving constants before it ran a single dispatch. Pass
    ``refresh=True`` after changing the Brightway project or the activity
    selection.
    """
    global _MEMO
    if refresh:
        _MEMO = None
        CACHE_PATH.unlink(missing_ok=True)
    if _MEMO is not None:
        return _MEMO
    if use_cache and CACHE_PATH.exists():
        try:
            cached = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
            if sorted(r["technology"] for r in cached) == sorted(TECHNOLOGIES):
                _MEMO = cached
                return _MEMO
        except Exception:
            pass   # a corrupt or stale cache is never fatal - just recompute

    import bw2data as bd
    import lca_helpers as H

    ei, _bio, _fg, _m = H.setup_brightway()
    method = _gwp_method(bd)
    rows = [decompose(tech, ei, H, method) for tech in TECHNOLOGIES]

    OUT_DIR.mkdir(exist_ok=True)
    CACHE_PATH.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    _MEMO = rows
    return rows


def apply_case(rows, case="central", solar_basis=None):
    """The cheap half: restate per-kWh burden at a scenario's LF and lifetime.

    ``case`` is the **cost** case. Load factor and lifetime are taken from the
    inverse case, because that is DESNZ/Arup's own pairing: a low-cost scenario
    is combined with the *high* load factor and *long* lifetime (see
    ``tech_costs.INVERSE_CASE``). Reading them directly here would make the
    same scenario label mean opposite things in the two modules — and would
    give the "low" case the *highest* embodied carbon per kWh.

    ``solar_basis`` picks which inventory supplies solar's embodied carbon,
    defaulting to ``SOLAR_EMBODIED_BASIS``. This is the seam the module
    docstring describes: everything downstream reads ``capital_kgco2e_per_MW``,
    so selecting a basis here reaches the LP, the sizing optimiser and the
    dashboard without any of them needing to know a choice was made. Each row
    carries ``embodied_basis`` so a result can say which one it used.
    """
    import optimisation.tech_costs as tc

    basis = solar_basis or SOLAR_EMBODIED_BASIS
    if basis not in SOLAR_EMBODIED_BASES:
        raise ValueError(
            f"solar_basis must be one of {list(SOLAR_EMBODIED_BASES)}, got {basis!r}")

    technical_case = tc.INVERSE_CASE[case]
    out = []
    for row in rows:
        row = dict(row)
        params, _src, _note = tc.TECHNOLOGIES[row["technology"]]
        row["cost_case"] = case
        row["technical_case"] = technical_case
        # Tolerate a cache written before this column existed.
        row.setdefault("ecoinvent_capital_kgco2e_per_MW", row["capital_kgco2e_per_MW"])
        if row["technology"] == "solar_pv":
            spec = SOLAR_EMBODIED_BASES[basis]
            row["capital_kgco2e_per_MW"] = solar_capital_kgco2e_per_mw(
                basis, row["ecoinvent_capital_kgco2e_per_MW"])
            row["embodied_basis"] = basis
            row["embodied_basis_label"] = spec["label"]
            row["embodied_basis_grade"] = spec["grade"]
        else:
            row["embodied_basis"] = "ecoinvent"
            row["embodied_basis_label"] = "ecoinvent 3.9.1 apos"
            row["embodied_basis_grade"] = "transcribed"
        row.update(restate(row,
                           tc._value(params, "net_load_factor", technical_case),
                           tc._value(params, "operating_lifetime", technical_case)))
        out.append(row)
    return pd.DataFrame(out)


def build(case="central", solar_basis=None):
    return apply_case(decompose_all(), case, solar_basis=solar_basis)


def check_reconstruction(df):
    """Capital + consumables must rebuild ecoinvent's own per-kWh score.

    Anchored on ``ecoinvent_capital_kgco2e_per_MW`` rather than the column the
    LP consumes, so the check still means what it says under a substituted
    basis: it verifies the *decomposition*, which is ecoinvent's either way.
    """
    problems = []
    for _, r in df.iterrows():
        if r["capital_share"] > 1.0001:
            problems.append(f"{r.technology}: capital share {r.capital_share:.3f} > 1")
        eco_per_mw = r.get("ecoinvent_capital_kgco2e_per_MW", r["capital_kgco2e_per_MW"])
        implied = eco_per_mw / 1000.0 / r["ecoinvent_lifetime_kWh_per_kW"]
        if abs(implied - r["capital_per_kWh"]) / r["capital_per_kWh"] > 0.001:
            problems.append(
                f"{r.technology}: per-MW capital does not re-amortise back to "
                f"ecoinvent's per-kWh ({implied:.6f} vs {r.capital_per_kWh:.6f})")
    if problems:
        raise AssertionError("renewables decomposition failed:\n  " + "\n  ".join(problems))
    return f"OK — {len(df)} technologies re-amortise back to ecoinvent exactly"


def run(case="central", solar_basis=None):
    basis = solar_basis or SOLAR_EMBODIED_BASIS
    df = build(case, solar_basis=basis)
    print("=" * 96)
    print(f"RENEWABLE GENERATION — embodied carbon per MW installed  (cost case: {case})")
    print("=" * 96)
    print(check_reconstruction(df))
    print(f"Solar embodied basis: {SOLAR_EMBODIED_BASES[basis]['label']} "
          f"[{basis}, {SOLAR_EMBODIED_BASES[basis]['grade']}]")

    print()
    print("ecoinvent's per-kWh datasets, taken apart")
    print("-" * 96)
    print(f"{'technology':<16}{'per kWh':>11}{'capital':>10}{'capital':>16}"
          f"{'lifetime':>12}{'implied':>10}")
    print(f"{'':<16}{'kg CO2e':>11}{'share':>10}{'t CO2e/MW':>16}"
          f"{'kWh/kW':>12}{'LF':>10}")
    for _, r in df.iterrows():
        # Always ecoinvent's own capital here: this table is the decomposition,
        # not the basis in force. Solar's substituted figure is reported below.
        print(f"{r.technology:<16}{r.ecoinvent_per_kWh:>11.5f}"
              f"{r.capital_share:>10.1%}{r.ecoinvent_capital_kgco2e_per_MW/1000:>16,.0f}"
              f"{r.ecoinvent_lifetime_kWh_per_kW:>12,.0f}"
              f"{r.ecoinvent_implied_load_factor:>10.1%}")

    print()
    print("Restated at this study's own load factors and lifetimes (DESNZ/Arup 2024)")
    print("-" * 96)
    print(f"{'technology':<16}{'study LF':>10}{'life':>7}{'kWh/kW':>12}"
          f"{'g CO2e/kWh':>13}{'ecoinvent':>12}{'ratio':>8}")
    for _, r in df.iterrows():
        print(f"{r.technology:<16}{r.study_load_factor:>10.1%}"
              f"{r.study_lifetime_years:>7.0f}{r.study_lifetime_kWh_per_kW:>12,.0f}"
              f"{r.restated_kgco2e_per_kWh*1000:>13.1f}"
              f"{r.ecoinvent_per_kWh*1000:>12.1f}{r.ratio_to_ecoinvent:>8.2f}")

    print()
    print("Why this matters")
    print("-" * 96)
    w = df[df.technology == "onshore_wind"].iloc[0]
    print(f"  ecoinvent's GB onshore wind assumes {w.ecoinvent_implied_load_factor:.1%} over "
          f"{w.ecoinvent_lifetime_years:.0f} y ({w.ecoinvent_lifetime_kWh_per_kW:,.0f} kWh/kW).")
    print(f"  DESNZ/Arup 2024 give {w.study_load_factor:.1%} over {w.study_lifetime_years:.0f} y "
          f"({w.study_lifetime_kWh_per_kW:,.0f} kWh/kW) - {w.study_lifetime_kWh_per_kW/w.ecoinvent_lifetime_kWh_per_kW:.1f}x more")
    print(f"  lifetime output. Charging embodied carbon at ecoinvent's per-kWh rate")
    print(f"  therefore overstates it by the same factor: {w.ecoinvent_per_kWh*1000:.1f} vs "
          f"{w.restated_kgco2e_per_kWh*1000:.1f} g CO2e/kWh.")
    pv = df[df.technology == "solar_pv"].iloc[0]
    print()
    print(f"  Solar PV is not scored on ecoinvent. Its GB open-ground activity is the")
    print(f"  570 kWp Solarpark El Tesoro, installed 2008, at a {SOLAR_EMBODIED_BASES['ecoinvent']['module_efficiency']:.2%} module — it")
    print(f"  restates to {pv.ecoinvent_restated_kgco2e_per_kWh*1000:.0f} g CO2e/kWh, about ten times wind. The inventory is")
    print("  byte-identical in ecoinvent 3.10.1 and no other GB PV activity exists at")
    print("  utility scale, so the database cannot fix it.")
    print()
    print(f"  Basis in force: {SOLAR_EMBODIED_BASES[basis]['label']}")
    print(f"    {pv.capital_kgco2e_per_MW/1000:>10,.0f} t CO2e/MWp  "
          f"(ecoinvent: {pv.ecoinvent_capital_kgco2e_per_MW/1000:,.0f})")
    print(f"    {pv.capital_kgco2e_per_MW/pv.study_lifetime_years:>10,.0f} kg CO2e/MWp/year  — this is what the LP charges")
    print(f"    {pv.restated_kgco2e_per_kWh*1000:>10.1f} g CO2e/kWh at {pv.study_load_factor:.1%} over "
          f"{pv.study_lifetime_years:.0f} y  (ecoinvent: {pv.ecoinvent_restated_kgco2e_per_kWh*1000:.1f})")
    w2 = df[df.technology == "onshore_wind"].iloc[0]
    print(f"    {pv.restated_kgco2e_per_kWh/w2.restated_kgco2e_per_kWh:>10.1f}x onshore wind per kWh  "
          f"(on ecoinvent: {pv.ecoinvent_restated_kgco2e_per_kWh/w2.restated_kgco2e_per_kWh:.1f}x)")
    print()
    print("  Other bases: " + ", ".join(k for k in SOLAR_EMBODIED_BASES if k != basis))
    print()
    print("  Notebooks 4.1 and 4.3 charge wind per kWh generated, so they carry")
    print("  ecoinvent's yield assumption. That is defensible for a fixed plant but")
    print("  wrong once capacity is being optimised - use the per-MW figures here.")

    OUT_DIR.mkdir(exist_ok=True)
    out = df.drop(columns=["_parts"])
    out.to_csv(OUT_DIR / "renewables_embodied.csv", index=False)
    print()
    print("Wrote: optimisation_outputs/renewables_embodied.csv")
    return df


if __name__ == "__main__":
    run()
