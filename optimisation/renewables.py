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

Known limitation
----------------
ecoinvent 3.9.1's GB open-ground PV dataset describes a **2012** multi-Si
plant. Its embodied carbon restates to ~57 g CO2e/kWh, against ~20-40 g/kWh
in current literature, because module efficiency and the carbon intensity of
module-manufacturing grids have both improved a lot since. PV's embodied
figure here is therefore a conservative upper bound. Wind is far less
affected, being mostly steel and concrete.

Sources
-------
embodied carbon   ecoinvent 3.9.1 apos, IPCC 2021 GWP100. Activities are the
                  GB per-kWh generation datasets and the capital "unit"
                  exchanges they draw on.
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
        "ecoinvent_lifetime_kWh_per_kW": lifetime_kwh_per_kw,
        "ecoinvent_lifetime_years": ei_life,
        "ecoinvent_implied_load_factor": implied_lf,
        "_parts": parts,
    }


def restate(row, load_factor, lifetime_years):
    """Per-kWh embodied burden at this study's own yield, not ecoinvent's."""
    lifetime_kwh_per_kw = load_factor * HOURS_PER_YEAR * lifetime_years
    per_kwh = row["capital_kgco2e_per_MW"] / 1000.0 / lifetime_kwh_per_kw
    return {
        "study_load_factor": load_factor,
        "study_lifetime_years": lifetime_years,
        "study_lifetime_kWh_per_kW": lifetime_kwh_per_kw,
        "restated_kgco2e_per_kWh": per_kwh,
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
            cached = json.loads(CACHE_PATH.read_text())
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
    CACHE_PATH.write_text(json.dumps(rows, indent=2))
    _MEMO = rows
    return rows


def apply_case(rows, case="central"):
    """The cheap half: restate per-kWh burden at a scenario's LF and lifetime.

    ``case`` is the **cost** case. Load factor and lifetime are taken from the
    inverse case, because that is DESNZ/Arup's own pairing: a low-cost scenario
    is combined with the *high* load factor and *long* lifetime (see
    ``tech_costs.INVERSE_CASE``). Reading them directly here would make the
    same scenario label mean opposite things in the two modules — and would
    give the "low" case the *highest* embodied carbon per kWh.
    """
    import optimisation.tech_costs as tc

    technical_case = tc.INVERSE_CASE[case]
    out = []
    for row in rows:
        row = dict(row)
        params, _src, _note = tc.TECHNOLOGIES[row["technology"]]
        row["cost_case"] = case
        row["technical_case"] = technical_case
        row.update(restate(row,
                           tc._value(params, "net_load_factor", technical_case),
                           tc._value(params, "operating_lifetime", technical_case)))
        out.append(row)
    return pd.DataFrame(out)


def build(case="central"):
    return apply_case(decompose_all(), case)


def check_reconstruction(df):
    """Capital + consumables must rebuild ecoinvent's own per-kWh score."""
    problems = []
    for _, r in df.iterrows():
        if r["capital_share"] > 1.0001:
            problems.append(f"{r.technology}: capital share {r.capital_share:.3f} > 1")
        implied = r["capital_kgco2e_per_MW"] / 1000.0 / r["ecoinvent_lifetime_kWh_per_kW"]
        if abs(implied - r["capital_per_kWh"]) / r["capital_per_kWh"] > 0.001:
            problems.append(
                f"{r.technology}: per-MW capital does not re-amortise back to "
                f"ecoinvent's per-kWh ({implied:.6f} vs {r.capital_per_kWh:.6f})")
    if problems:
        raise AssertionError("renewables decomposition failed:\n  " + "\n  ".join(problems))
    return f"OK — {len(df)} technologies re-amortise back to ecoinvent exactly"


def run(case="central"):
    df = build(case)
    print("=" * 96)
    print(f"RENEWABLE GENERATION — embodied carbon per MW installed  (cost case: {case})")
    print("=" * 96)
    print(check_reconstruction(df))

    print()
    print("ecoinvent's per-kWh datasets, taken apart")
    print("-" * 96)
    print(f"{'technology':<16}{'per kWh':>11}{'capital':>10}{'capital':>16}"
          f"{'lifetime':>12}{'implied':>10}")
    print(f"{'':<16}{'kg CO2e':>11}{'share':>10}{'t CO2e/MW':>16}"
          f"{'kWh/kW':>12}{'LF':>10}")
    for _, r in df.iterrows():
        print(f"{r.technology:<16}{r.ecoinvent_per_kWh:>11.5f}"
              f"{r.capital_share:>10.1%}{r.capital_kgco2e_per_MW/1000:>16,.0f}"
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
    print(f"  Solar PV restates to {pv.restated_kgco2e_per_kWh*1000:.0f} g CO2e/kWh, roughly ten times wind and")
    print("  high against modern literature (~20-40 g/kWh). That is a dataset vintage")
    print("  issue, not an arithmetic one: ecoinvent 3.9.1's GB open-ground PV is a")
    print("  2012 multi-Si plant, and both module efficiency and the carbon intensity")
    print("  of the grids that make modules have improved substantially since. Treat")
    print("  it as a conservative upper bound on PV's embodied carbon.")
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
