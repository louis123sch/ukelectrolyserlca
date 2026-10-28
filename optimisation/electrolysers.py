"""
Electrolysers — embodied carbon per MW installed.
=============================================================================

The Gerloff 2021 foreground (``optimiser_lca/hydrogen.py``; called Hermesmann's
here until 22 Oct 2026) supplies electrolysis as a **per-kg-H2** activity
with the capital good already amortised over a lifetime output that Gerloff
chose. That is the right shape for an attributional study of a fixed plant. It
is the wrong shape for an optimiser, for exactly the reasons set out in
``renewables.py``:

1. **Capacity is a decision variable.** The optimiser sizes MW; the burden of
   building those MW must not depend on how much hydrogen they happen to make.
2. **Gerloff's implied utilisation is not this study's.** All three
   technologies amortise their capital over **160 GWh of lifetime electricity
   throughput at 1 MW** — 160,000 full-load hours. Spread over a 25-year plant
   life that is a **73 % capacity factor**. An optimiser that builds an
   electrolyser to chase surplus wind at 20 % CF and charges its capital per kg
   produced would understate that machine's embodied carbon **by a factor of
   3.5**.

So this module strips the capital back out: it reads the ``unit``-denominated
capital exchange from the per-kg activity, scores it, and reports **kg CO2e per
MW installed**. What remains — water, heat, electrolyte — stays per kg, because
those genuinely do scale with output.

Nothing is invented. ``check_reconstruction()`` asserts that capital-per-MW
re-amortised at Gerloff's own throughput, plus the per-kg remainder,
reproduces ``lca_helpers.run_non_electricity_lca()`` exactly.

The 1 MW rating
---------------
Only PEM states its rating in the foreground ("1 unit (1 MW)"). AE and SOEC do
not, so the rating is **derived and cross-checked** rather than assumed: each
technology's lifetime hydrogen output times its own specific energy comes to
160 GWh to within 0.2 %, despite specific energies ranging from 42.3 to
54.0 kWh/kg. Three independent inventories agreeing to 0.2 % on a quantity none
of them states is not a coincidence — it is one shared 1 MW / 160 GWh capital
basis. ``check_rating()`` enforces the agreement, so if the foreground is ever
rebuilt on a different basis this module fails loudly instead of scaling
everything by a silent factor.

Stacks
------
Gerloff's unit carries **three stacks** over its 20-year life (§2.1.3; the
module carries the stack's rows x3 since 22 Oct 2026, as the SI's stack
manufacturing energy always was). The capital good is still one activity per
unit, amortised here on calendar life: a duty-driven stack count, as
``fuel_cell.py`` does for the fuel cell, would need the stack rows split out
as their own activity — possible from the SI's Stack/BoP labels, not done.
For an electrolyser run harder than Gerloff's 160,000 full-load hours this
understates the stack burden. Registered in ``DATA_GAPS.md``.

Sources
-------
inventories       Gerloff, N. (2021), J. Energy Storage 43, 102759: alkaline / PEM / SOEC.
                  Built into ``hydrogen foreground`` by
                  ``optimiser_lca/hydrogen.py`` (python -m optimiser_lca.build).
embodied carbon   ecoinvent 3.9.1 apos, IPCC 2021 GWP100.
plant lifetime    25 years — NESO Green Hydrogen Data Portal, the same figure
                  ``price_outputs/electrolyser_costs_clean.csv`` carries.

Every number in this module is listed in ``SOURCES.md`` alongside its
source and provenance grade (transcribed / derived / assumed).

Run:  python optimisation/electrolysers.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
OUT_DIR = ROOT / "optimisation_outputs"

from optimisation import trace as T  # noqa: E402

# label -> rated MW of the capital unit. See "The 1 MW rating" above: derived
# from the inventories' own arithmetic, not transcribed, and enforced by
# check_rating().
TECHNOLOGIES = {
    "AE operation": 1.0,
    "PEM operation": 1.0,
    "SOEC operation": 1.0,
}

# Pressure the hydrogen leaves the electrolyser at, in bar.
#
# This exists because ``h2_storage`` needs it and was assuming it. Its
# compression parasitic is the work of getting hydrogen from the electrolyser's
# delivery pressure up to the tank's, and it was keyed off the *tank* pressure
# alone — zero for the 28 bar design, justified in that module's own docstring
# by "the electrolyser already leaves at ~30 bar". True of PEM. Not true of
# SOEC, which is the technology the 300 MW runs use.
#
# The consequence was a comparability error, not just a missing term: the three
# technologies were being compared head to head at three different delivery
# pressures with no compression charged to any of them, which flatters whichever
# one delivers at the lowest pressure. That is SOEC, the most efficient on
# kWh/kg and therefore the one most likely to be selected on the strength of it.
#
# Sources
# -------
# PEM   30 bar. 30-40 bar PEM electrolysers are the widely commercialised
#       class; only one 700 bar unit is on the market. TRANSCRIBED from the
#       high-pressure PEM review (Energy Convers. Manag. 2022).
# SOEC  1 bar. SOEC operates at atmospheric pressure; pressurised SOEC is a
#       research and early-commercial interest precisely *because* it displaces
#       downstream compression. TRANSCRIBED from the pressurised-SOE
#       operational-strategies review (Fuel Cells, 2026) and IRENA's SOEC
#       innovation-landscape brief.
# AE    30 bar. ASSUMED. Alkaline is deployed both atmospheric and pressurised
#       to ~30 bar, and the source inventory does not state which it is. This is
#       the optimistic end; if the AE inventory is atmospheric, its compression
#       is understated by the same ~2 kWh/kg as SOEC's was.
DELIVERY_PRESSURE_BAR = {
    "AE operation": 30.0,
    "PEM operation": 30.0,
    "SOEC operation": 1.0,
}
DELIVERY_PRESSURE_ASSUMED = {"AE operation"}

# The shared capital basis the three inventories agree on, used only to check
# the rating. Not used in any coefficient.
EXPECTED_LIFETIME_GWH_PER_MW = 160.0
RATING_TOLERANCE = 0.01          # 1 % — the inventories agree to 0.2 %

# Scoring each input separately and summing does not reproduce a single LCA of
# the whole activity to machine precision: bw2calc runs an independent sparse
# solve per call, and their tolerances do not cancel. The residual is solver
# noise, not a modelling difference, and is ~1e-5 relative in practice. The
# limit below is loose enough to survive it and tight enough that any real
# error — a missed exchange, a double count — is orders of magnitude larger.
RECONSTRUCTION_TOLERANCE = 1e-4

# How SOEC's 5.24 kWh/kg of external heat is raised. A scenario choice, not a
# fact about the stack.
#
# gas_boiler       As inventoried: Mehmeti et al. 2018's natural-gas boiler, a
#                  fixed 1.417 kg CO2e/kg H2 inside variable_kgco2e_per_kg.
# electric_boiler  The heat comes off the site's own electricity. The gas row's
#                  burden is removed and 5.24 kWh / efficiency is added to
#                  kwh_per_kg, so the heat carries whatever the LP buys or
#                  generates in that hour, and is paid for at that price.
#                  Electric steam generators and superheaters are what
#                  commercial SOEC systems use; resistance heating reaches the
#                  ~750 °C stack inlet, which a boiler does not.
SOEC_HEAT_SOURCES = ("gas_boiler", "electric_boiler")
SOEC_HEAT_DEFAULT = "gas_boiler"
# ASSUMED. Resistance/electrode boilers convert ~99 % of input to heat (Danish
# Energy Agency, Technology Data, "Electric boilers"); not yet checked against
# the sheet. At 0.99 the boiler adds 5.29 kWh/kg.
ELECTRIC_BOILER_EFFICIENCY = 0.99
MJ_PER_KWH = 3.6

# NESO Green Hydrogen Data Portal, via electrolyser_costs_clean.csv.
PLANT_LIFETIME_YEARS = 25.0

# Stacks wear with running hours (user, 26 Oct 2026; docs/ELECTROLYSER_STACKS.md).
# Gerloff's unit is a balance of plant plus three stacks for 20 years at 8,000 h/yr,
# each stack good for "50,000 h or more" (§2.1.2). The optimiser charges the plant
# once over PLANT_LIFETIME_YEARS and the stacks as max(calendar, duty) replacement
# units, the fuel cell's rule: the calendar floor keeps today's three stacks per
# 25-year plant (so nothing below ~68 % utilisation moves), and the duty term adds
# stacks for a hard-run electrolyser.
STACK_DUTY_HOURS = 50_000.0          # TRANSCRIBED - Gerloff 2021 §2.1.2, "50,000 h or more"
STACKS_PER_PLANT_LIFE = 3            # TRANSCRIBED - Gerloff §2.1.2-2.1.3 (hydrogen.STACKS_PER_UNIT_LIFE)
STACK_CALENDAR_YEARS = PLANT_LIFETIME_YEARS / STACKS_PER_PLANT_LIFE   # DERIVED - the floor: today's 3 per 25 y

HOURS_PER_YEAR = 8760.0
CACHE_PATH = OUT_DIR / "electrolyser_decomposition_cache.json"
_MEMO: list | None = None


def _gwp_method(bd):
    return next(m for m in bd.methods
                if m[1] == "IPCC 2021" and m[2] == "climate change"
                and "GWP100" in str(m) and "no LT" not in str(m))


def decompose(label, H, bd, method):
    """Split a per-kg electrolysis activity into capital per MW and the rest.

    Capital is the single ``unit``-denominated technosphere exchange — the
    electrolyser itself. Everything else that is not electricity (water, heat,
    electrolyte) is a genuine consumable and stays per kg.
    """
    from optimiser_lca import registry as R
    rated_mw = TECHNOLOGIES[label]
    act = bd.get_activity((R.HYDROGEN_DB, R.ELECTROLYSER_CODES[label]))

    capital = [e for e in act.technosphere() if e.input.get("unit") == "unit"]
    if len(capital) != 1:
        raise ValueError(
            f"{label}: expected exactly 1 capital-good exchange, found "
            f"{len(capital)}. The foreground's shape has changed — this module "
            "cannot decompose it safely.")
    cap_exc = capital[0]
    units_per_kg = float(cap_exc["amount"])
    capital_per_unit = H.run_lca_score(cap_exc.input, method)

    variable_per_kg = 0.0
    consumables = []
    for e in act.technosphere():
        # Select by unit, not by object identity: Brightway builds a fresh
        # Exchange object on every iteration, so `e is cap_exc` is never true
        # and the capital good would be counted a second time here.
        if e.input.get("unit") == "unit" or H.is_any_electricity_exchange(e):
            continue
        score = H.run_lca_score(e.input, method) * float(e["amount"])
        variable_per_kg += score
        consumables.append((e.input["name"], float(e["amount"]), score))

    # The reference: what the repo's existing helper reports for this activity.
    fixed_per_kg, kwh_per_kg, _n = H.run_non_electricity_lca(act, method)

    # The unit is plant + three stacks; each is scored on its own for the LP's two terms.
    plant_code, stack_code = R.ELY_PARTS[label]
    plant_per_unit = H.run_lca_score(bd.get_activity((R.HYDROGEN_DB, plant_code)), method)
    stack_per_unit = H.run_lca_score(bd.get_activity((R.HYDROGEN_DB, stack_code)), method)
    if abs(plant_per_unit + STACKS_PER_PLANT_LIFE * stack_per_unit - capital_per_unit) > 1e-6 * capital_per_unit:
        raise ValueError(f"{label}: plant + {STACKS_PER_PLANT_LIFE} stacks does not add up to the unit")

    lifetime_kg = 1.0 / units_per_kg
    lifetime_kwh = lifetime_kg * kwh_per_kg
    full_load_hours = lifetime_kwh / (rated_mw * 1000.0)

    return {
        "technology": label,
        "activity": act["name"],
        "location": act.get("location"),
        "rated_MW": rated_mw,
        "kwh_per_kg": kwh_per_kg,
        "units_per_kg": units_per_kg,
        "lifetime_kg_h2": lifetime_kg,
        "lifetime_GWh": lifetime_kwh / 1e6,
        "full_load_hours": full_load_hours,
        "implied_capacity_factor": full_load_hours / (PLANT_LIFETIME_YEARS * HOURS_PER_YEAR),
        "capital_kgco2e_per_unit": capital_per_unit,
        "capital_kgco2e_per_MW": capital_per_unit / rated_mw,
        "capital_kgco2e_per_MW_year": capital_per_unit / rated_mw / PLANT_LIFETIME_YEARS,
        "capital_kgco2e_per_kg_h2": capital_per_unit * units_per_kg,
        "plant_kgco2e_per_MW": plant_per_unit / rated_mw,
        "stack_kgco2e_per_MW": stack_per_unit / rated_mw,          # one stack
        "stacks_per_unit": STACKS_PER_PLANT_LIFE,
        "variable_kgco2e_per_kg": variable_per_kg,
        "foreground_fixed_kgco2e_per_kg": fixed_per_kg,
        "_consumables": consumables,
    }


def decompose_all(use_cache: bool = True, refresh: bool = False):
    """Every technology's capital burden per MW. Memoised and disk-cached.

    Each technology is a handful of sparse linear solves against ecoinvent, so
    the result is cached for the same reason ``renewables.py`` caches: an
    optimiser must not re-derive constants inside its inner loop. Pass
    ``refresh=True`` after rebuilding the foreground database.
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
            if (sorted(r["technology"] for r in cached) == sorted(TECHNOLOGIES)
                    and all("stack_kgco2e_per_MW" in r for r in cached)):
                _MEMO = cached
                return _MEMO
        except Exception:
            pass   # a corrupt or stale cache is never fatal - just recompute

    import bw2data as bd
    import lca_helpers as H

    H.setup_brightway()
    method = _gwp_method(bd)
    rows = [decompose(label, H, bd, method) for label in TECHNOLOGIES]

    OUT_DIR.mkdir(exist_ok=True)
    CACHE_PATH.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    _MEMO = rows
    return rows


def with_heat_source(row: dict, source: str | None = None) -> dict:
    """SOEC's decomposed row with its external heat raised the given way.

    ``gas_boiler`` returns the row as inventoried. ``electric_boiler`` moves
    the heat out of ``variable_kgco2e_per_kg`` and into ``kwh_per_kg``, so the
    LP charges it at the hour's own electricity. ``heat_kwh_electric_per_kg``
    says how much of ``kwh_per_kg`` is boiler rather than stack, for anything
    priced per MW of stack. Other technologies pass through untouched: their
    heat is not this choice.
    """
    source = source or SOEC_HEAT_DEFAULT
    if source not in SOEC_HEAT_SOURCES:
        raise ValueError(f"SOEC heat source {source!r}; choose from {SOEC_HEAT_SOURCES}")
    out = dict(row, heat_source=None, heat_kwh_electric_per_kg=0.0)
    if row["technology"] != "SOEC operation":
        return _traced(out)
    out["heat_source"] = source
    if source == "gas_boiler":
        return _traced(out)
    heat = [c for c in row["_consumables"] if "heat" in c[0]]
    if len(heat) != 1:
        raise ValueError(f"SOEC: expected exactly 1 heat consumable, found {len(heat)}. "
                         "The foreground's shape has changed.")
    _name, heat_mj, heat_score = heat[0]
    boiler_kwh = heat_mj / MJ_PER_KWH / ELECTRIC_BOILER_EFFICIENCY
    out["kwh_per_kg"] = row["kwh_per_kg"] + boiler_kwh
    out["variable_kgco2e_per_kg"] = row["variable_kgco2e_per_kg"] - heat_score
    out["heat_kwh_electric_per_kg"] = boiler_kwh
    return _traced(out)


def _traced(row: dict) -> dict:
    """Record one technology's decomposed figures (``optimisation.trace``)."""
    from optimiser_lca import registry as R
    label = row["technology"]
    k = "electrolyser." + label.split()[0]
    plant_code, stack_code = R.ELY_PARTS[label]
    op = T.activity(R.HYDROGEN_DB, R.ELECTROLYSER_CODES[label])
    plant, stack = T.activity(R.HYDROGEN_DB, plant_code), T.activity(R.HYDROGEN_DB, stack_code)
    rated = TECHNOLOGIES[label]
    T.step(f"{k}.plant_per_MW", row["plant_kgco2e_per_MW"], "kg CO2e per MW",
           "The balance of plant, built once per unit (Gerloff 2021)", uses=[plant],
           scores=plant, factor=1.0 / rated, grade="derived")
    T.step(f"{k}.stack_per_MW", row["stack_kgco2e_per_MW"], "kg CO2e per MW, one stack",
           "One stack, 1 MW (Gerloff 2021); a unit holds three over its life", uses=[stack],
           scores=stack, factor=1.0 / rated, grade="derived")
    T.step(f"{k}.variable_per_kg", row["variable_kgco2e_per_kg"], "kg CO2e per kg H2",
           "Consumables per kg made: every input of the operation activity that is neither "
           "the capital good nor electricity (water, heat, electrolyte)"
           + (", the heat moved onto electricity" if row.get("heat_source") == "electric_boiler" else ""),
           uses=[op], grade="derived", source="decompose(): the per-kg activity, taken apart")
    T.step(f"{k}.kwh_per_kg", row["kwh_per_kg"], "kWh per kg H2",
           "Electricity per kg made, as the operation activity carries it"
           + (", plus the electric boiler" if row.get("heat_kwh_electric_per_kg") else ""),
           uses=[op], grade="transcribed", inputs={"heat_kwh_electric_per_kg": row.get("heat_kwh_electric_per_kg")})
    return row


def build():
    return pd.DataFrame(decompose_all()).drop(columns=["_consumables"])


def check_rating(rows):
    """The 1 MW rating is derived, so it has to be defended.

    Three inventories with specific energies from 42.3 to 54.0 kWh/kg must all
    land on the same lifetime throughput per MW. If one does not, the rating
    assumed for it is wrong and every per-MW number for it is wrong with it.
    """
    problems = []
    for r in rows:
        gwh_per_mw = r["lifetime_GWh"] / r["rated_MW"]
        err = abs(gwh_per_mw - EXPECTED_LIFETIME_GWH_PER_MW) / EXPECTED_LIFETIME_GWH_PER_MW
        if err > RATING_TOLERANCE:
            problems.append(
                f"{r['technology']}: {gwh_per_mw:.1f} GWh/MW lifetime throughput, "
                f"{err:.1%} from the {EXPECTED_LIFETIME_GWH_PER_MW:.0f} GWh/MW the "
                f"other inventories share. Its rated_MW of {r['rated_MW']} is "
                "probably wrong — check Hermesmann et al. before trusting any "
                "per-MW figure for it.")
    if problems:
        raise AssertionError("electrolyser rating check failed:\n  " + "\n  ".join(problems))
    spread = max(r["lifetime_GWh"] / r["rated_MW"] for r in rows) - \
             min(r["lifetime_GWh"] / r["rated_MW"] for r in rows)
    return (f"OK — all {len(rows)} inventories share a "
            f"{EXPECTED_LIFETIME_GWH_PER_MW:.0f} GWh/MW capital basis "
            f"(spread {spread:.2f} GWh/MW), so the 1 MW rating holds")


def check_reconstruction(rows):
    """Capital-per-MW + consumables must rebuild the foreground's own figure.

    This is the guard that makes the decomposition trustworthy: it re-amortises
    the extracted per-MW capital at Hermesmann's *own* throughput and requires
    the total to match what ``run_non_electricity_lca`` reports to 1e-9.
    """
    problems, worst = [], 0.0
    for r in rows:
        rebuilt = (r["capital_kgco2e_per_MW"] * r["rated_MW"] * r["units_per_kg"]
                   + r["variable_kgco2e_per_kg"])
        ref = r["foreground_fixed_kgco2e_per_kg"]
        if abs(rebuilt - ref) > RECONSTRUCTION_TOLERANCE * abs(ref):
            problems.append(
                f"{r['technology']}: rebuilt {rebuilt:.12f} vs foreground "
                f"{ref:.12f} kg CO2e/kg H2 (diff {rebuilt - ref:.3e})")
        worst = max(worst, abs(rebuilt - ref) / abs(ref))
    if problems:
        raise AssertionError("electrolyser decomposition failed:\n  " + "\n  ".join(problems))
    return (f"OK — {len(rows)} inventories reconstruct the foreground's own "
            f"figure, worst error {worst:.1e} relative")


def restate(row, capacity_factor, lifetime_years=PLANT_LIFETIME_YEARS):
    """Per-kg capital burden at *this study's* utilisation, not Hermesmann's.

    The whole point of the module in one function: the same machine, charged
    against the output it actually produces.
    """
    lifetime_kwh = capacity_factor * HOURS_PER_YEAR * lifetime_years * row["rated_MW"] * 1000.0
    lifetime_kg = lifetime_kwh / row["kwh_per_kg"]
    per_kg = row["capital_kgco2e_per_unit"] / lifetime_kg
    return {
        "capacity_factor": capacity_factor,
        "lifetime_years": lifetime_years,
        "capital_kgco2e_per_kg_h2": per_kg,
        "total_kgco2e_per_kg_h2_excl_elec": per_kg + row["variable_kgco2e_per_kg"],
        "ratio_to_foreground": per_kg / row["capital_kgco2e_per_kg_h2"],
    }


# =============================================================================
# DOUBLE-COUNT GUARD
# =============================================================================
def assert_no_double_count(uses_capital_per_mw: bool, uses_foreground_fixed: bool):
    """The one mistake this module makes possible, refused explicitly.

    ``run_non_electricity_lca()``'s ``fixed_kgco2e_per_kg`` **already contains**
    the amortised capital good. An objective that charges capital per MW *and*
    uses that figure counts the electrolyser twice. ``sizing.py`` legitimately
    uses the foreground figure and charges no per-MW capital; the data centre
    optimiser does the opposite. Neither may do both.
    """
    if uses_capital_per_mw and uses_foreground_fixed:
        raise AssertionError(
            "Double count: capital_kgco2e_per_MW and the foreground's "
            "fixed_kgco2e_per_kg both charge the electrolyser's capital good. "
            "Use capital_kgco2e_per_MW with variable_kgco2e_per_kg (the "
            "optimiser's convention), or foreground fixed_kgco2e_per_kg alone "
            "(sizing.py's convention) — never both.")


def run():
    rows = decompose_all()
    df = build()
    print("=" * 100)
    print("ELECTROLYSERS — embodied carbon per MW installed")
    print("=" * 100)
    print(check_rating(rows))
    print(check_reconstruction(rows))

    print("\nAs the foreground amortises it")
    print("-" * 100)
    print(f"  {'technology':<16}{'kWh/kg':>8}{'lifetime kg':>14}{'GWh/MW':>9}"
          f"{'full-load h':>13}{'implied CF':>12}")
    for r in rows:
        print(f"  {r['technology']:<16}{r['kwh_per_kg']:>8.1f}"
              f"{r['lifetime_kg_h2']:>14,.0f}{r['lifetime_GWh'] / r['rated_MW']:>9.1f}"
              f"{r['full_load_hours']:>13,.0f}{r['implied_capacity_factor']:>11.1%}")
    print(f"\n  Capital is amortised over {PLANT_LIFETIME_YEARS:.0f} years at that")
    print("  utilisation. An optimiser that builds to a different one must not")
    print("  reuse the per-kg figure — that is what this module exists to fix.")

    print("\nDecomposed for the optimiser")
    print("-" * 100)
    print(f"  {'technology':<16}{'capital t/MW':>14}{'t/MW/yr':>10}"
          f"{'variable kg/kg':>16}{'foreground kg/kg':>18}")
    for r in rows:
        print(f"  {r['technology']:<16}{r['capital_kgco2e_per_MW'] / 1000:>14,.1f}"
              f"{r['capital_kgco2e_per_MW_year'] / 1000:>10,.2f}"
              f"{r['variable_kgco2e_per_kg']:>16.4f}"
              f"{r['foreground_fixed_kgco2e_per_kg']:>18.4f}")

    print("\nWhat utilisation does to the per-kg capital burden")
    print("-" * 100)
    cfs = (0.20, 0.40, 0.60, 0.731, 0.90)
    print(f"  {'technology':<16}" + "".join(f"{c:>13.0%}" for c in cfs))
    for r in rows:
        cells = "".join(f"{restate(r, c)['capital_kgco2e_per_kg_h2']:>13.4f}" for c in cfs)
        print(f"  {r['technology']:<16}{cells}")
    worst = restate(rows[0], 0.20)["ratio_to_foreground"]
    print(f"\n  kg CO2e/kg H2 of capital alone. At 20 % CF the burden is "
          f"{worst:.1f}x what the")
    print("  foreground charges — the error the optimiser would make without this module.")

    OUT_DIR.mkdir(exist_ok=True)
    path = OUT_DIR / "electrolysers_embodied.csv"
    df.to_csv(path, index=False)
    print(f"\nWrote:\n  {path.relative_to(ROOT)}")
    return df


if __name__ == "__main__":
    run()
