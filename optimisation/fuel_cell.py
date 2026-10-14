"""
PEM fuel cell — embodied carbon split into capital, wear and maintenance.
=============================================================================

``pemfc_op_1kwh_h2`` charges **everything per kWh delivered**: the stack over
30,000 operating hours, the balance of plant over 80,000, and a service every
8,000. For an attributional study of a fuel cell
that runs continuously, that is correct and elegant.

For an optimiser it is a trap, and a worse one than the electrolyser's. The
configuration ``grid_h2`` most wants to build is a fuel cell **installed at full
data-centre rating and run a few hundred hours a year** — backup, not baseload.
Charged per kWh delivered, that machine arrives with almost **no** embodied
burden at all, because it delivers almost no kWh. The steel, the platinum and
the graphite are real whether or not the thing ever runs.

So this module splits the inventory three ways:

| term | scales with | why |
|---|---|---|
| **balance of plant** | whichever runs out first: 20 calendar years, or 80,000 operating hours | a physical system that both ages and wears |
| **stack** | whichever runs out first: 10 calendar years, or 30,000 operating hours | you must buy one to have a fuel cell; you buy another every 30,000 hours of running |
| **maintenance** | MWh delivered | a service (air filter, coolant) every 8,000 operating hours |

Neither replaceable component is simply "capital" or "throughput". Each is

    replacements per MW per year = max( 1 / calendar_life_years ,
                                        full_load_hours_per_year / duty_life_hours )

which looks non-linear but is a maximum of two linear functions, so an LP
expresses it exactly: put ``units ≥ cap_fc / calendar_life`` and
``units ≥ throughput_MWh / duty_life`` on a free variable and let the objective
push it down onto whichever binds. ``REPLACEMENT_LP_NOTE`` carries the
formulation to the model layer so it cannot be lost in translation.

This matters at **both** ends. Charge the balance of plant on calendar life
alone and a fuel cell run flat out gets 20 years out of an 80,000-hour machine —
under-charged by 2.2x. Charge it on duty alone and a backup machine gets 400
years out of it. ``check_full_duty()`` asserts that at 8,760 h/yr the rule
reproduces the foreground's own per-kWh figure exactly, which is the case where
the two conventions must agree.

Hydrogen is deliberately **excluded** from every coefficient here. In the
optimiser the LP supplies hydrogen explicitly, from an electrolyser or a
purchase, each with its own burden; leaving the inventory's own hydrogen input
in would count the fuel twice. ``h2_kg_per_MWh`` is reported separately as the
consumption rate the LP needs.

Sources
-------
stack             Babatunde, S. et al. (2024), "Environmental Impact Assessment
                  of a 1 kW Proton-Exchange Membrane Fuel Cell", Table S1.
                  Built into ``fuel cell foreground`` by
                  ``optimiser_lca/fuel_cell.py`` (python -m optimiser_lca.build).
balance of plant  Usai et al. 2021 SI Table 1 process loops (80 kW H2 PEM
                  system, per kW net) + ecoinvent 500 kW inverter + the
                  battery's 20 ft container at one per MW. Built as
                  ``pemfc_bop_stationary_1kw`` by optimiser_lca/fuel_cell.py.
                  Replaced ecoinvent's 2 kW natural-gas micro-CHP on 14 Oct.
maintenance       an air filter and a coolant change every 8,000 h (ASSUMED
                  interval), Usai's amounts. Replaced ecoinvent's reformer-
                  catalyst service event.
stack duty life   30,000 h — stationary H2 stacks refurbished at 24-30k h
                  (Nedstack); Bionaz et al. 2022 use 40k.
system duty life  80,000 h — DOE's 100 kW-3 MW stationary class, and
                  ecoinvent's own system life. Was 60,000, the residential class.
embodied carbon   ecoinvent 3.9.1 apos, IPCC 2021 GWP100.

**BoP calendar life: 20 years.** Nedstack give 20 y for the balance of plant
of their 120 kW CHP unit (10 y for their mobile unit); DOE's backup-power target
is a 15-year system life. Sweep 15-25. Was 25 y, ASSUMED to match the
electrolyser.

**Stack calendar life: 10 years.** The Clean Hydrogen Partnership's stationary
PEMFC KPIs are set on a 10-year system life, and Nedstack's mobile unit is
10 y; Gandiglio et al. 2022 replace their 50 kW Engie-EPS unit every 5. PEM
membranes age at open circuit, so this is the life that binds for a backup
stack that sits idle. Sweep 5 / 10 / 15. It was a 25-year placeholder.

Neither calendar life is a manufacturer warranty on a MW-class H2 unit, and
none was found; both stay flagged ``*_IS_ASSUMED`` for that reason.

Both calendar lives are read from the constants below on every call, never from
the decomposition cache, so editing one takes effect without a Brightway rerun.

Run:  python optimisation/fuel_cell.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
OUT_DIR = ROOT / "optimisation_outputs"

CACHE_PATH = OUT_DIR / "fuel_cell_decomposition_cache.json"
_MEMO: dict | None = None

# See the module docstring: indicative sources, none of them for a MW-class
# H2 unit, so both stay flagged as assumptions.
BOP_CALENDAR_LIFETIME_YEARS = 20.0
BOP_LIFETIME_IS_ASSUMED = True
STACK_CALENDAR_LIFETIME_YEARS = 10.0
STACK_CALENDAR_LIFE_IS_ASSUMED = True

RECONSTRUCTION_TOLERANCE = 1e-4      # bw2calc solver noise; see electrolysers.py

REPLACEMENT_LP_NOTE = (
    "For each of stack and BoP: units_per_MW_per_year = "
    "max(1/calendar_life_years, full_load_hours_per_year/duty_life_hours). "
    "In an LP, on a free variable u the objective minimises: "
    "u >= cap_fc/calendar_life_years  and  u >= throughput_MWh/duty_life_hours. "
    "Charging the throughput term alone misses most of a backup fuel cell; "
    "charging the calendar term alone under-counts a baseload one."
)

# How each exchange of pemfc_op_1kwh_h2 is classified. Matching is on the
# input activity's name, and every exchange must match exactly one rule or the
# decomposition refuses to run — so a foreground rebuild that adds or renames
# an exchange fails loudly instead of silently dropping it.
CLASSIFICATION = [
    ("fuel",  "Hydrogen production"),
    ("stack", "Fuel cell stack production, PEM"),
    ("bop",   "Fuel cell balance of plant, stationary"),
    ("maint", "Fuel cell service, stationary"),
]


def _gwp_method(bd):
    return next(m for m in bd.methods
                if m[1] == "IPCC 2021" and m[2] == "climate change"
                and "GWP100" in str(m) and "no LT" not in str(m))


def _classify(name):
    for kind, pattern in CLASSIFICATION:
        if name.startswith(pattern):
            return kind
    raise ValueError(
        f"Unclassified exchange in pemfc_op_1kwh_h2: {name!r}. The fuel cell "
        "foreground has changed shape; update CLASSIFICATION before trusting "
        "any coefficient from this module.")


def _with_calendar_lives(d: dict) -> dict:
    """Overlay the calendar lives from the module constants.

    They are assumptions, not inventory, so the cache must not freeze them: an
    edited constant used to be silently ignored until the cache was deleted.
    """
    d["bop_calendar_lifetime_years"] = BOP_CALENDAR_LIFETIME_YEARS
    d["bop_lifetime_is_assumed"] = BOP_LIFETIME_IS_ASSUMED
    d["bop_kgco2e_per_MW_year"] = d["bop_kgco2e_per_MW"] / BOP_CALENDAR_LIFETIME_YEARS
    d["stack_calendar_lifetime_years"] = STACK_CALENDAR_LIFETIME_YEARS
    d["stack_calendar_life_is_assumed"] = STACK_CALENDAR_LIFE_IS_ASSUMED
    return d


# Which stack inventory the LP charges. Babatunde's 2 kW graphite-plate stack
# (ecoinvent's "future" dataset) is the default and the conservative one, at
# ~97 kg CO2e/kW; Gramc et al. 2025's 48 kW automotive stack, rebuilt on this
# study's ecoinvent 3.9.1 apos, is the sensitivity. Kept as the default after
# the 14 Oct comparison: Gramc's stack is a vehicle stack whose component
# manufacture is largely raw material only, so it errs low for a MW-class
# stationary unit, and Babatunde errs high. The band is reported, not chosen
# between (sensitivity.CARBON_KNOBS).
STACK_BASES = {
    "babatunde_2024": "Babatunde et al. 2024 / ecoinvent 'future' 2 kW graphite-plate stack",
    "gramc_2025": "Gramc et al. 2025, IJHE 104:623, 48 kW automotive stainless-plate stack",
}
STACK_BASIS = "babatunde_2024"


def stack_kgco2e_per_mw(d: dict, basis: str | None = None) -> float:
    """Embodied carbon of one MW of stack, on the named basis."""
    basis = basis or STACK_BASIS
    if basis == "babatunde_2024":
        return float(d["stack_kgco2e_per_MW"])
    if basis == "gramc_2025":
        return float(d["stack_kgco2e_per_MW_gramc_2025"])
    raise ValueError(f"stack basis must be one of {list(STACK_BASES)}, got {basis!r}")


def decompose(use_cache: bool = True, refresh: bool = False) -> dict:
    """Per-kWh inventory -> per-MW capital, per-MWh wear, per-MWh maintenance."""
    global _MEMO
    if refresh:
        _MEMO = None
        CACHE_PATH.unlink(missing_ok=True)
    if _MEMO is not None:
        return _with_calendar_lives(_MEMO)
    if use_cache and CACHE_PATH.exists():
        try:
            _MEMO = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
            return _with_calendar_lives(_MEMO)
        except Exception:
            pass

    import bw2data as bd
    import lca_helpers as H
    from optimiser_lca import fuel_cell as cfg      # the inventory's own parameters
    from optimiser_lca import registry as R

    H.setup_brightway()
    method = _gwp_method(bd)
    act = bd.get_activity((R.FUEL_CELL_DB, R.FC_OP))

    groups = {"fuel": 0.0, "stack": 0.0, "bop": 0.0, "maint": 0.0}
    container_per_kwh = 0.0
    h2_kg_per_kwh = 0.0
    stack_units_per_kwh = 0.0
    parts = []
    for e in act.technosphere():
        name = e.input["name"]
        amount = float(e["amount"])
        kind = _classify(name)
        score = H.run_lca_score(e.input, method) * amount
        groups[kind] += score
        if kind == "fuel":
            h2_kg_per_kwh += amount
        if kind == "stack":
            stack_units_per_kwh += amount
        if kind == "bop":
            # The enclosure, scored on its own so its ASSUMED one-per-MW count
            # can be swept without rebuilding the inventory.
            for sub in e.input.technosphere():
                if sub.input.key == (R.BESS_DB, R.BESS_PARTS["container"]):
                    container_per_kwh += (H.run_lca_score(sub.input, method)
                                          * float(sub["amount"]) * amount)
        parts.append({"name": name, "amount": amount, "kind": kind, "kgco2e_per_kwh": score})

    # The inventory's own amortisation bases, read back out of the amounts so
    # they cannot drift from the inventory module.
    stack_hours = 1.0 / (stack_units_per_kwh * cfg.FC_RATED_POWER_KW)
    bop_hours = float(cfg.FC_SYSTEM_LIFETIME_H)

    # Per kW installed: multiply the per-kWh amount by the hours it was
    # amortised over. Then per MW.
    stack_per_mw = groups["stack"] * stack_hours * 1000.0
    bop_per_mw = groups["bop"] * bop_hours * 1000.0

    out = {
        "activity": act["name"],
        "rated_kW": cfg.FC_RATED_POWER_KW,
        "eta_net_mean": cfg.FC_ETA_NET_MEAN,
        "h2_kg_per_kWh": h2_kg_per_kwh,
        "h2_kg_per_MWh": h2_kg_per_kwh * 1000.0,
        "stack_lifetime_hours": stack_hours,
        "bop_duty_lifetime_hours": bop_hours,
        "bop_calendar_lifetime_years": BOP_CALENDAR_LIFETIME_YEARS,
        "bop_lifetime_is_assumed": BOP_LIFETIME_IS_ASSUMED,

        "stack_kgco2e_per_MW": stack_per_mw,
        "stack_kgco2e_per_MWh": stack_per_mw / stack_hours,
        "bop_kgco2e_per_MW": bop_per_mw,
        "bop_kgco2e_per_MW_year": bop_per_mw / BOP_CALENDAR_LIFETIME_YEARS,
        # The sensitivity stack, per MW (its activity is per kW).
        "stack_kgco2e_per_MW_gramc_2025": H.run_lca_score(
            bd.get_activity((R.FUEL_CELL_DB, R.FC_STACK_GRAMC)), method) * 1000.0,
        # Of which the container, at the inventory's own kW per container.
        "bop_container_kgco2e_per_MW": container_per_kwh * bop_hours * 1000.0,
        "bop_kw_per_container": cfg.FC_KW_PER_CONTAINER,
        "maintenance_kgco2e_per_MWh": groups["maint"] * 1000.0,

        "_per_kwh": dict(groups),
        "_foreground_total_per_kWh": sum(groups.values()),
        "_parts": parts,
    }
    _with_calendar_lives(out)
    OUT_DIR.mkdir(exist_ok=True)
    CACHE_PATH.write_text(json.dumps(out, indent=2), encoding="utf-8")
    _MEMO = out
    return out


def check_reconstruction(d):
    """Re-amortising at the inventory's own bases must rebuild it exactly."""
    rebuilt = (d["stack_kgco2e_per_MW"] / 1000.0 / d["stack_lifetime_hours"]
               + d["bop_kgco2e_per_MW"] / 1000.0 / d["bop_duty_lifetime_hours"]
               + d["maintenance_kgco2e_per_MWh"] / 1000.0)
    ref = d["_foreground_total_per_kWh"] - d["_per_kwh"]["fuel"]
    err = abs(rebuilt - ref) / abs(ref)
    if err > RECONSTRUCTION_TOLERANCE:
        raise AssertionError(
            f"fuel cell decomposition failed: rebuilt {rebuilt:.9f} vs "
            f"foreground {ref:.9f} kg CO2e/kWh (non-fuel), {err:.1e} relative")
    return (f"OK — the three terms re-amortise to the foreground's own "
            f"{ref * 1000:.2f} g CO2e/kWh non-fuel burden, error {err:.1e}")


def burden_kgco2e_per_year(cap_mw, mwh_per_year, stack_calendar_years=None):
    """Annual embodied burden of a fuel cell of ``cap_mw`` delivering ``mwh_per_year``.

    Applies the max(calendar, duty) replacement rule to both the stack and the
    balance of plant, which is what makes a lightly-used backup machine and a
    baseload one both cost what they actually cost.
    """
    d = decompose()
    stack_calendar_years = stack_calendar_years or d["stack_calendar_lifetime_years"]
    h = (mwh_per_year / cap_mw) if cap_mw else 0.0        # full-load-equiv h/yr

    stack_rate = max(1.0 / stack_calendar_years, h / d["stack_lifetime_hours"])
    bop_rate = max(1.0 / d["bop_calendar_lifetime_years"], h / d["bop_duty_lifetime_hours"])
    return {
        "bop": d["bop_kgco2e_per_MW"] * cap_mw * bop_rate,
        "stack": d["stack_kgco2e_per_MW"] * cap_mw * stack_rate,
        "maintenance": d["maintenance_kgco2e_per_MWh"] * mwh_per_year,
        "stack_units_per_MW_year": stack_rate,
        "bop_units_per_MW_year": bop_rate,
        "full_load_hours_per_year": h,
        "stack_binding": "duty" if h / d["stack_lifetime_hours"] > 1.0 / stack_calendar_years else "calendar",
        "bop_binding": "duty" if h / d["bop_duty_lifetime_hours"] > 1.0 / d["bop_calendar_lifetime_years"] else "calendar",
    }


def check_full_duty(d):
    """At continuous duty the rule must reproduce the foreground exactly.

    This is the case where "per MW on a duty life" and "per kWh delivered" are
    the same statement, so any disagreement is a bug in the decomposition
    rather than a modelling choice.
    """
    cap, hours = 1.0, 8760.0
    b = burden_kgco2e_per_year(cap, cap * hours)
    rebuilt = (b["bop"] + b["stack"] + b["maintenance"]) / (cap * hours * 1000.0)
    ref = d["_foreground_total_per_kWh"] - d["_per_kwh"]["fuel"]
    err = abs(rebuilt - ref) / abs(ref)
    if err > RECONSTRUCTION_TOLERANCE:
        raise AssertionError(
            f"fuel cell full-duty check failed: {rebuilt * 1000:.4f} vs "
            f"{ref * 1000:.4f} g CO2e/kWh, {err:.1e} relative. The max(calendar, "
            "duty) rule does not collapse onto the foreground at 8,760 h/yr.")
    return (f"OK — at 8,760 h/yr the rule reproduces the foreground's "
            f"{ref * 1000:.2f} g CO2e/kWh exactly (error {err:.1e})")


def run():
    d = decompose()
    print("=" * 100)
    print("PEM FUEL CELL — embodied carbon, split by what it actually scales with")
    print("=" * 100)
    print(check_reconstruction(d))
    print(check_full_duty(d))

    print("\nAs the foreground charges it (everything per kWh delivered)")
    print("-" * 100)
    for k in ("stack", "bop", "maint"):
        print(f"  {k:<14}{d['_per_kwh'][k] * 1000:>10.3f} g CO2e/kWh")
    print(f"  {'fuel (H2)':<14}{d['_per_kwh']['fuel'] * 1000:>10.3f} g CO2e/kWh   "
          f"— excluded from every coefficient below; the LP supplies hydrogen")

    print("\nDecomposed for the optimiser")
    print("-" * 100)
    print(f"  balance of plant   {d['bop_kgco2e_per_MW'] / 1000:>10,.1f} t CO2e/MW, replaced on "
          f"max({d['bop_calendar_lifetime_years']:.0f} y"
          f"{' ASSUMED' if d['bop_lifetime_is_assumed'] else ''}, "
          f"{d['bop_duty_lifetime_hours']:,.0f} h)")
    print(f"  stack              {d['stack_kgco2e_per_MW'] / 1000:>10,.1f} t CO2e/MW, replaced on "
          f"max({d['stack_calendar_lifetime_years']:.0f} y"
          f"{' ASSUMED' if d['stack_calendar_life_is_assumed'] else ''}, "
          f"{d['stack_lifetime_hours']:,.0f} h)")
    print(f"  maintenance        {d['maintenance_kgco2e_per_MWh']:>10,.2f} kg CO2e/MWh delivered")
    print(f"  hydrogen           {d['h2_kg_per_MWh']:>10,.2f} kg H2/MWh "
          f"(eta {d['eta_net_mean']:.3f} net AC)")

    print("\nWhy the split matters — a 7.31 MW fuel cell, by duty")
    print("-" * 100)
    print(f"  {'run hours/yr':>13}{'t CO2e/yr, split':>19}{'t CO2e/yr, per-kWh':>21}{'ratio':>16}   binding")
    for hours in (100, 500, 2000, 8760):
        mwh = 7.31 * hours
        b = burden_kgco2e_per_year(7.31, mwh)
        split = (b["bop"] + b["stack"] + b["maintenance"]) / 1000.0
        naive = (d["_foreground_total_per_kWh"] - d["_per_kwh"]["fuel"]) * mwh * 1000 / 1000.0
        print(f"  {hours:>13,}{split:>19,.1f}{naive:>21,.1f}{split / naive:>15.1f}x"
              f"   {b['stack_binding']}/{b['bop_binding']}")
    print("\n  The per-kWh column is what the foreground charges as-is. At backup duty it")
    print("  misses the machine almost entirely — exactly the configuration a grid+hydrogen")
    print("  architecture wants to build. The last column says which limit binds for")
    print("  stack/BoP; at 8,760 h/yr both are duty-bound and the two columns agree.")
    print(f"\n  LP formulation: {REPLACEMENT_LP_NOTE}")

    OUT_DIR.mkdir(exist_ok=True)
    df = pd.DataFrame([{k: v for k, v in d.items() if not k.startswith("_")}])
    path = OUT_DIR / "fuel_cell_embodied.csv"
    df.to_csv(path, index=False)
    print(f"\nWrote:\n  {path.relative_to(ROOT)}")
    return d


if __name__ == "__main__":
    run()
