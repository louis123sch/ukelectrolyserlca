"""
PEM fuel cell — embodied carbon split into capital, wear and maintenance.
=============================================================================

``pemfc_op_1kwh_h2`` charges **everything per kWh delivered**: the stack over
32,000 operating hours, the balance of plant over 60,000, and maintenance over
the service events those hours imply. For an attributional study of a fuel cell
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
| **balance of plant** | whichever runs out first: 25 calendar years, or 60,000 operating hours | a physical system that both ages and wears |
| **stack** | whichever runs out first: the horizon, or 32,000 operating hours | you must buy one to have a fuel cell; you buy another every 32,000 hours of running |
| **maintenance** | MWh delivered | service events are driven by runtime, as the inventory itself models them |

Neither replaceable component is simply "capital" or "throughput". Each is

    replacements per MW per year = max( 1 / calendar_life_years ,
                                        full_load_hours_per_year / duty_life_hours )

which looks non-linear but is a maximum of two linear functions, so an LP
expresses it exactly: put ``units ≥ cap_fc / calendar_life`` and
``units ≥ throughput_MWh / duty_life`` on a free variable and let the objective
push it down onto whichever binds. ``REPLACEMENT_LP_NOTE`` carries the
formulation to the model layer so it cannot be lost in translation.

This matters at **both** ends. Charge the balance of plant on calendar life
alone and a fuel cell run flat out gets 25 years out of a 60,000-hour machine —
under-charged by 3.7x. Charge it on duty alone and a backup machine gets 300
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
                  ``2.tech_lca_foreground.ipynb``.
balance of plant  ecoinvent 3.9.1 "fuel cell production, polymer electrolyte
                  membrane, 2 kW" net of its own stack, and net of the
                  domestic-micro-CHP hot-water kit ecoinvent bundles with it.
stack life        32,000 h — Babatunde et al. 2024 §3.4, their own figure.
system duty life  60,000 h — DOE 2020 stationary target.
embodied carbon   ecoinvent 3.9.1 apos, IPCC 2021 GWP100.

**BoP calendar life is ASSUMED.** 60,000 h is a *duty* figure, not a calendar
one — at 200 h/yr it implies a 300-year asset. No public calendar life was
found for a stationary PEMFC balance of plant, so this study charges it over
the same 25 years it gives the electrolyser and the data centre. Registered in
``DATA_GAPS.md``; every result that depends on it should say so.

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

# ASSUMED — see the module docstring. Not a published figure.
BOP_CALENDAR_LIFETIME_YEARS = 25.0
BOP_LIFETIME_IS_ASSUMED = True

RECONSTRUCTION_TOLERANCE = 1e-4      # bw2calc solver noise; see electrolysers.py

REPLACEMENT_LP_NOTE = (
    "For each of stack and BoP: units_per_MW_per_year = "
    "max(1/calendar_life_years, full_load_hours_per_year/duty_life_hours). "
    "In an LP, on a free variable u the objective minimises: "
    "u >= cap_fc/calendar_life_years  and  u >= throughput_MWh/duty_life_hours. "
    "Charging the throughput term alone under-counts a backup fuel cell 16x; "
    "charging the calendar term alone under-counts a baseload one 3.7x."
)

# How each exchange of pemfc_op_1kwh_h2 is classified. Matching is on the
# input activity's name, and every exchange must match exactly one rule or the
# decomposition refuses to run — so a foreground rebuild that adds or renames
# an exchange fails loudly instead of silently dropping it.
CLASSIFICATION = [
    ("fuel",  "Hydrogen production"),
    ("stack", "Fuel cell stack production, PEM"),
    ("bop",   "fuel cell production, polymer electrolyte membrane"),
    ("bop",   "fuel cell production, stack polymer electrolyte membrane"),
    ("bop",   "heating and sanitary equipment production, mini CHP"),
    ("maint", "maintenance, polymer electrolyte membrane fuel cell"),
    ("maint", "market for transport, passenger car"),
]
# "fuel cell production, stack polymer electrolyte membrane" appears twice with
# opposite signs: once netting ecoinvent's stack out of its own 2 kW system
# (BoP), once netting it out of a maintenance service event (maintenance).
# Sign tells them apart — the maintenance one is the smaller in magnitude.
STACK_NETTING_NAME = "fuel cell production, stack polymer electrolyte membrane"


def _gwp_method(bd):
    return next(m for m in bd.methods
                if m[1] == "IPCC 2021" and m[2] == "climate change"
                and "GWP100" in str(m) and "no LT" not in str(m))


def _classify(name, amount, seen_stack_netting):
    if name.startswith(STACK_NETTING_NAME):
        # first (larger magnitude) = the BoP netting, second = maintenance
        return "bop" if not seen_stack_netting else "maint"
    for kind, pattern in CLASSIFICATION:
        if name.startswith(pattern):
            return kind
    raise ValueError(
        f"Unclassified exchange in pemfc_op_1kwh_h2: {name!r}. The fuel cell "
        "foreground has changed shape; update CLASSIFICATION before trusting "
        "any coefficient from this module.")


def decompose(use_cache: bool = True, refresh: bool = False) -> dict:
    """Per-kWh inventory -> per-MW capital, per-MWh wear, per-MWh maintenance."""
    global _MEMO
    if refresh:
        _MEMO = None
        CACHE_PATH.unlink(missing_ok=True)
    if _MEMO is not None:
        return _MEMO
    if use_cache and CACHE_PATH.exists():
        try:
            _MEMO = json.loads(CACHE_PATH.read_text())
            return _MEMO
        except Exception:
            pass

    import bw2data as bd
    import lca_helpers as H
    import dashboard_config as cfg

    H.setup_brightway()
    method = _gwp_method(bd)
    act = bd.get_activity((cfg.FC_FOREGROUND_DB, "pemfc_op_1kwh_h2"))

    groups = {"fuel": 0.0, "stack": 0.0, "bop": 0.0, "maint": 0.0}
    h2_kg_per_kwh = 0.0
    stack_units_per_kwh = 0.0
    parts, seen_netting = [], False
    for e in act.technosphere():
        name = e.input["name"]
        amount = float(e["amount"])
        kind = _classify(name, amount, seen_netting)
        if name.startswith(STACK_NETTING_NAME):
            seen_netting = True
        score = H.run_lca_score(e.input, method) * amount
        groups[kind] += score
        if kind == "fuel":
            h2_kg_per_kwh += amount
        if kind == "stack":
            stack_units_per_kwh += amount
        parts.append({"name": name, "amount": amount, "kind": kind, "kgco2e_per_kwh": score})

    # The inventory's own amortisation bases, read back out of the amounts so
    # they cannot drift from dashboard_config.
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
        "maintenance_kgco2e_per_MWh": groups["maint"] * 1000.0,

        "_per_kwh": dict(groups),
        "_foreground_total_per_kWh": sum(groups.values()),
        "_parts": parts,
    }
    OUT_DIR.mkdir(exist_ok=True)
    CACHE_PATH.write_text(json.dumps(out, indent=2))
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


def burden_kgco2e_per_year(cap_mw, mwh_per_year, horizon_years=None):
    """Annual embodied burden of a fuel cell of ``cap_mw`` delivering ``mwh_per_year``.

    Applies the max(calendar, duty) replacement rule to both the stack and the
    balance of plant, which is what makes a lightly-used backup machine and a
    baseload one both cost what they actually cost.
    """
    d = decompose()
    horizon_years = horizon_years or d["bop_calendar_lifetime_years"]
    h = (mwh_per_year / cap_mw) if cap_mw else 0.0        # full-load-equiv h/yr

    stack_rate = max(1.0 / horizon_years, h / d["stack_lifetime_hours"])
    bop_rate = max(1.0 / d["bop_calendar_lifetime_years"], h / d["bop_duty_lifetime_hours"])
    return {
        "bop": d["bop_kgco2e_per_MW"] * cap_mw * bop_rate,
        "stack": d["stack_kgco2e_per_MW"] * cap_mw * stack_rate,
        "maintenance": d["maintenance_kgco2e_per_MWh"] * mwh_per_year,
        "stack_units_per_MW_year": stack_rate,
        "bop_units_per_MW_year": bop_rate,
        "full_load_hours_per_year": h,
        "stack_binding": "duty" if h / d["stack_lifetime_hours"] > 1.0 / horizon_years else "calendar",
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
          f"max(horizon, {d['stack_lifetime_hours']:,.0f} h)")
    print(f"  maintenance        {d['maintenance_kgco2e_per_MWh']:>10,.2f} kg CO2e/MWh delivered")
    print(f"  hydrogen           {d['h2_kg_per_MWh']:>10,.2f} kg H2/MWh "
          f"(eta {d['eta_net_mean']:.3f} net AC)")

    print("\nWhy the split matters — a 7.31 MW fuel cell, 25 years, by duty")
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
