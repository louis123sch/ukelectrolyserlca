"""
Hydrogen-chain asset costs — the weakest numbers in the study.
=============================================================================

Three inputs the cost objective needs and no UK source provides: what a
stationary fuel cell costs per kW, what a hydrogen vessel costs per kg of
capacity, and what an SOEC electrolyser costs. Every other cost in this study is
transcribed from a named table in a named UK document. **None of these three
is.** They are here so the cost objective can run at all, and every one is
graded ``assumed``.

Read the caveats before quoting any hydrogen cost result
--------------------------------------------------------

**Fuel cell.** DOE's targets are for systems *operating on natural gas*, which
include a reformer this study does not have — a hydrogen-fed unit should be
cheaper, so these figures are biased **high**. The $1,000/kW figure is an
aspirational 2020 target at 100 MW/yr production volume, not an observed price;
the 2015 status range is what was actually being paid. No US inflation
adjustment is applied, because a 3.75x spread between low and high dwarfs a
decade of deflator.

**Hydrogen vessel.** Quotes for above-ground compressed storage span €500/kg to
€1,040/kg of capacity across studies, with DOE's 2005 status for 430 bar at
$1,100/kg. None is UK, none is recent, and the spread is over 2x. Gandiglio et
al. 2022 supplies this study's *inventory* and would be the right source for its
cost too — that has not been checked and should be.

**SOEC.** No cost source was found at all. It is scaled off PEM, which is a
guess about a technology gap rather than a measurement. SOEC is less mature than
PEM and generally costs more, so the multipliers are all above 1.0, but their
size is not evidence-based. **An SOEC carbon result is sound; an SOEC cost
result is not.** Consider reporting SOEC carbon-only.

Because all three are assumed, they are given as low/central/high spanning the
full published range rather than a point estimate with a nominal spread. Run the
cost case as a sensitivity, not as a scenario label — if a conclusion flips
between low and high, it is not a conclusion.

Currency
--------
Real 2025 GBP, using the same FES 2025 cross-rates as ``h2_prices.py`` so every
conversion in the study traces to one published table.

Sources
-------
fuel cell     U.S. Department of Energy, *Technical Targets for 100 kW-3 MW
              Combined Heat and Power and Distributed Generation Fuel Cell
              Systems Operating on Natural Gas*. 2015 status $1,200-4,500/kW;
              2020 target $1,000/kW; 80,000 h to >10 % net power degradation;
              42-47 % LHV electrical efficiency.
H2 vessel     Range across the compressed-storage literature: EUR 500/kg and
              EUR 1,040/kg of capacity for above-ground compressed tanks;
              DOE 2005 status $1,100/kg for 430 bar stationary.
SOEC          No source. Scaled off the NESO PEM capex in
              `price_outputs/electrolyser_costs_clean.csv`.

Run:  python optimisation/h2_capex.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from optimisation import trace as T  # noqa: E402

PRICE_DIR = ROOT / "price_outputs"
OUT_DIR = ROOT / "optimisation_outputs"

CASES = ("low", "central", "high")

# FES 2025 Data Workbook cross-rates, as h2_prices.py uses.
EUR_PER_GBP_2025 = 1.17
USD_PER_GBP_2025 = 1.17 / 0.913

# -----------------------------------------------------------------------------
# Fuel cell — ASSUMED
# -----------------------------------------------------------------------------
# DOE, 100 kW-3 MW stationary CHP/DG fuel cell systems on natural gas.
FC_USD_PER_KW = {
    "low": 1_000.0,      # 2020 target, 100 MW/yr volume — aspirational
    "central": 2_300.0,  # 2015 status, lower half of the observed range
    "high": 4_500.0,     # 2015 status, top of the observed range
}
FC_FIXED_OPEX_FRAC = {"low": 0.02, "central": 0.03, "high": 0.05}
FC_INCLUDES_REFORMER = True     # biases every figure high for a H2-fed unit
FC_DISCOUNT_RATE = 0.06         # as sizing.Electrolyser, for consistency
# Stack share of fuel-cell capex. FROZEN on 14 Oct 2026 at the value the old
# carbon split gave (stack / (stack + BoP), ecoinvent micro-CHP BoP), because it
# used to be read live from the LCA: rebuilding the fuel cell's *carbon* would
# have silently moved both cost coefficients. A carbon split was never the right
# basis for a cost split — Battelle's cost-based stack share is 22-41 % for a
# hydrogen-fed unit (audit §3.4). Sourcing it is the fuel-cell capex job (TODO).
FC_STACK_COST_FRACTION = 0.1719969013679964
FC_STACK_COST_FRACTION_IS_ASSUMED = True

# -----------------------------------------------------------------------------
# Hydrogen vessel — ASSUMED
# -----------------------------------------------------------------------------
TANK_EUR_PER_KG_CAPACITY = {"low": 500.0, "central": 770.0, "high": 1_040.0}
TANK_FIXED_OPEX_FRAC = {"low": 0.01, "central": 0.02, "high": 0.03}

# -----------------------------------------------------------------------------
# SOEC — ASSUMED, scaled off PEM
# -----------------------------------------------------------------------------
SOEC_MULTIPLIER_OF_PEM = {"low": 1.2, "central": 1.5, "high": 2.0}
SOEC_HAS_NO_SOURCE = True

GRADE = "assumed"


def capital_recovery_factor(rate, lifetime_years):
    if rate <= 0:
        return 1.0 / lifetime_years
    return rate / (1.0 - (1.0 + rate) ** -lifetime_years)


def fc_stack_cost_fraction() -> float:
    """Stack share of fuel cell capital: ``FC_STACK_COST_FRACTION``, frozen.

    It used to be the LCA's carbon split, read live, which coupled cost to any
    carbon rebuild. See the constant.
    """
    return FC_STACK_COST_FRACTION


def fuel_cell_cost(case: str, bop_calendar_years: float | None = None) -> dict:
    """One case of ``fuel_cell_costs``, each number recorded for the cost map."""
    from optimisation import fuel_cell as fc
    # From the constant, not the decomposition cache: an assumption edited in
    # fuel_cell.py must reach the cost side without a Brightway rerun.
    life = T.cost("cost.fuel_cell.bop_life_years", float(bop_calendar_years or fc.BOP_CALENDAR_LIFETIME_YEARS),
                  "years", "Balance-of-plant calendar life, the same life the carbon side replaces it on",
                  grade="assumed", note="fuel_cell.BOP_CALENDAR_LIFETIME_YEARS")
    rate = T.cost("cost.h2_assets.discount_rate", FC_DISCOUNT_RATE, "fraction per year",
                  "Discount rate for the fuel cell and tank", grade="assumed",
                  note="As the electrolyser's 6 %, for consistency; one discount-rate policy is open (audit §4)")
    crf = T.cost("cost.fuel_cell.crf", capital_recovery_factor(rate, life), "per year",
                 "Capital recovery factor over the balance-of-plant life",
                 uses=["cost.h2_assets.discount_rate", "cost.fuel_cell.bop_life_years"])
    usd = T.cost("cost.fuel_cell.capex_USD_per_kW", FC_USD_PER_KW[case], "US $ per kW",
                 "Installed capital of a 100 kW-3 MW stationary fuel cell on natural gas", grade="assumed",
                 cites=[("doe_fc_chp_targets", {"low": "2020 target", "central": "2015 status, lower half",
                                                 "high": "2015 status, top of range"}[case])],
                 note="Includes a reformer this study's hydrogen-fed unit does not have: biased high")
    fx = T.cost("fx.usd_per_gbp_2025", USD_PER_GBP_2025, "US $ per £", "2025 cross-rate, £ to US $",
                grade="transcribed", cites=[("fes_2025_workbook", "cross-rates, 2025: £1 = €1.17, $1 = €0.913")])
    capex = T.cost("cost.fuel_cell.capex_per_kW", usd / fx, "GBP per kW", "Installed capital in real 2025 £",
                   uses=["cost.fuel_cell.capex_USD_per_kW", "fx.usd_per_gbp_2025"])
    # Split capital between stack and balance of plant on
    # FC_STACK_COST_FRACTION (17 %), frozen at what the old carbon split
    # gave; see the constant for why it is no longer read from the LCA.
    #
    # It matters because the stack wears out on *duty* while BoP runs to
    # calendar. Charging the whole system on calendar life made
    # running the fuel cell hard free in cost while still costing carbon, so
    # the two objectives were pricing different physics for one machine.
    stack_frac = T.cost("cost.fuel_cell.stack_cost_fraction", fc_stack_cost_fraction(), "fraction",
                        "Stack share of the fuel cell's capital", grade="assumed",
                        note="Frozen 14 Oct 2026 at the old carbon split; Battelle's cost-based share is 22-41 % "
                             "(audit §3.4)")
    opex = T.cost("cost.fuel_cell.fixed_opex_frac", FC_FIXED_OPEX_FRAC[case], "fraction of capital per year",
                  "Fixed operating cost", grade="assumed",
                  note="h2_capex.FC_FIXED_OPEX_FRAC: no source; 2 / 3 / 5 % spans the low, central and high cases")
    # BoP, split the same way as the stack so that duty reaches the
    # cost objective as it reaches carbon. The LP charges
    #   A_bop * (CRF + o - 1/L) * cap_fc  +  A_bop * fc_bop_units
    # and fc_bop_units >= max(cap_fc/L, MWh/duty_hours). When calendar
    # binds that is A_bop * (CRF + o) * cap_fc, exactly the old
    # annuity; when duty binds it stays within about 2 % of the exact
    # CRF on the shortened life. Charging the annuity alone made BoP
    # replacements free in cost above 2,400 h/yr — up to 39 % low on
    # the fuel cell line at 8,760 h. REVIEW_RESPONSE_PLAN.md §1.
    annual = T.cost("cost.fuel_cell.annual_per_MW", capex * 1000.0 * (1.0 - stack_frac) * (crf + opex - 1.0 / life),
                    "GBP per MW per year", "Balance of plant: capital recovery and opex, less the calendar "
                    "replacement the LP charges per replacement",
                    uses=["cost.fuel_cell.capex_per_kW", "cost.fuel_cell.stack_cost_fraction", "cost.fuel_cell.crf",
                          "cost.fuel_cell.fixed_opex_frac", "cost.fuel_cell.bop_life_years"])
    bop = T.cost("cost.fuel_cell.bop_per_MW", capex * 1000.0 * (1.0 - stack_frac), "GBP per MW replaced",
                 "Balance of plant capital, charged per replacement",
                 uses=["cost.fuel_cell.capex_per_kW", "cost.fuel_cell.stack_cost_fraction"])
    # Stack capital, charged per replacement. Undiscounted, matching the
    # carbon side, because the LP abstracts away *when* a replacement
    # falls and a discount factor would need that schedule. This
    # overstates a distant replacement slightly.
    stack = T.cost("cost.fuel_cell.stack_per_MW", capex * 1000.0 * stack_frac, "GBP per MW replaced",
                   "Stack capital, charged per replacement (undiscounted, as the carbon side)",
                   uses=["cost.fuel_cell.capex_per_kW", "cost.fuel_cell.stack_cost_fraction"])
    return {
        "asset": "fuel_cell", "case": case,
        "capex_GBP_per_kW": capex,
        "capex_GBP_per_MW": capex * 1000.0,
        "fixed_opex_frac": FC_FIXED_OPEX_FRAC[case],
        "lifetime_years": life,
        "stack_cost_fraction": stack_frac,
        "annual_GBP_per_MW_year": annual,
        "bop_GBP_per_MW": bop,
        "stack_GBP_per_MW": stack,
        "grade": GRADE,
        "note": "DOE natural-gas system — includes a reformer this study does "
                "not have, so biased high" if FC_INCLUDES_REFORMER else "",
    }


def fuel_cell_costs(bop_calendar_years: float | None = None):
    """£/kW installed, and the annualised £/kW/year that follows.

    ``bop_calendar_years`` overrides ``fuel_cell.BOP_CALENDAR_LIFETIME_YEARS``
    for a sweep, so the cost annuity moves with the life the carbon side's
    replacement count uses.
    """
    with T.quiet():
        return pd.DataFrame([fuel_cell_cost(case, bop_calendar_years) for case in CASES])


def tank_cost(case: str) -> dict:
    """One case of ``tank_costs``, each number recorded for the cost map."""
    import dc_config as cfg
    life = T.cost("cost.h2_tank.life_years", float(cfg.TANK_LIFETIME_YEARS), "years",
                  "Tank life: the plant's, never replaced", grade="assumed",
                  note="dc_config.TANK_LIFETIME_YEARS, Gandiglio's plant lifetime")
    rate = T.cost("cost.h2_assets.discount_rate", FC_DISCOUNT_RATE, "fraction per year",
                  "Discount rate for the fuel cell and tank", grade="assumed",
                  note="As the electrolyser's 6 %, for consistency; one discount-rate policy is open (audit §4)")
    crf = T.cost("cost.h2_tank.crf", capital_recovery_factor(rate, life), "per year",
                 "Capital recovery factor over the tank's life",
                 uses=["cost.h2_assets.discount_rate", "cost.h2_tank.life_years"])
    eur = T.cost("cost.h2_tank.capex_EUR_per_kg", TANK_EUR_PER_KG_CAPACITY[case], "€ per kg of capacity",
                 "Above-ground compressed vessel capital", grade="assumed",
                 cites=[("h2_vessel_literature", {"low": "€500/kg", "central": "midpoint of €500 and €1,040/kg",
                                                  "high": "€1,040/kg"}[case])],
                 note="Prices a different vessel from the carbon side's 28 bar Gandiglio tank (TODO)")
    fx = T.cost("fx.eur_per_gbp_2025", EUR_PER_GBP_2025, "€ per £", "2025 cross-rate, £ to €",
                grade="transcribed", cites=[("fes_2025_workbook", "cross-rates, 2025: £1 = €1.17")])
    capex = T.cost("cost.h2_tank.capex_per_kg", eur / fx, "GBP per kg of capacity", "Vessel capital in real 2025 £",
                   uses=["cost.h2_tank.capex_EUR_per_kg", "fx.eur_per_gbp_2025"])
    opex = T.cost("cost.h2_tank.fixed_opex_frac", TANK_FIXED_OPEX_FRAC[case], "fraction of capital per year",
                  "Fixed operating cost", grade="assumed",
                  note="h2_capex.TANK_FIXED_OPEX_FRAC: no source; 1 / 2 / 3 % spans the low, central and high cases")
    annual = T.cost("cost.h2_tank.annual_per_kg", capex * (crf + opex), "GBP per kg of capacity per year",
                    "Capital recovery plus fixed opex, per kg the tank holds",
                    uses=["cost.h2_tank.capex_per_kg", "cost.h2_tank.crf", "cost.h2_tank.fixed_opex_frac"])
    return {
        "asset": "h2_tank", "case": case,
        "capex_GBP_per_kg_capacity": capex,
        "fixed_opex_frac": TANK_FIXED_OPEX_FRAC[case],
        "lifetime_years": life,
        "annual_GBP_per_kg_year": annual,
        "grade": GRADE,
        "note": "spread across the literature is over 2x; none of the sources "
                "is UK or recent",
    }


def tank_costs():
    """£ per kg of hydrogen storage capacity."""
    with T.quiet():
        return pd.DataFrame([tank_cost(case) for case in CASES])


def _neso_pem_capex(build_year=2025):
    """PEM capex from the NESO table the repo already has."""
    df = pd.read_csv(PRICE_DIR / "electrolyser_costs_clean.csv")
    df = df[(df.technology == "PEM") & (df.build_year == build_year)]
    if df.empty:
        raise ValueError(f"No NESO PEM capex for build year {build_year}")
    return {"low": float(df[df.scenario == "Low"].iloc[0].capex_GBP_per_kWe),
            "central": float(df[df.scenario == "Central"].iloc[0].capex_GBP_per_kWe),
            "high": float(df[df.scenario == "High"].iloc[0].capex_GBP_per_kWe)}


# Hydrogen's higher heating value, to turn NESO's per-kWh-HHV variable opex into
# per kg. 39.4 kWh/kg is the standard figure (141.8 MJ/kg).
H2_HHV_KWH_PER_KG = 39.4


def electrolyser_cost(tech: str, case: str, build_year=2025) -> dict:
    """One electrolyser's NESO (or, for SOEC, PEM-scaled) cost row, each number
    recorded for the cost map. ``tech`` is "ae", "pem" or "soec"."""
    with T.quiet():
        df = electrolyser_costs(build_year)
    r = df[(df.asset == f"electrolyser_{tech}") & (df.case == case)].iloc[0]
    k = f"cost.electrolyser_{tech}"
    scen = {"low": "Low", "central": "Central", "high": "High"}[case]
    neso = lambda what: [("neso_green_h2_portal_costs", f"{'PEM' if tech != 'ae' else 'Alkaline'}, "   # noqa: E731
                                                        f"{scen}, build year {build_year}, {what}")]
    if tech == "soec":
        pem = T.cost("cost.electrolyser_pem.capex_per_kWe", _neso_pem_capex(build_year)[case], "GBP per kWe",
                     "PEM electrolyser capital", grade="transcribed", cites=neso("capex_GBP_per_kWe"))
        mult = T.cost(f"{k}.multiplier_of_pem", SOEC_MULTIPLIER_OF_PEM[case], "multiplier",
                      "SOEC capital as a multiple of PEM's", grade="assumed",
                      note="NO SOURCE: SOEC is less mature than PEM and generally dearer; the size is a guess")
        T.cost(f"{k}.capex_per_kWe", pem * mult, "GBP per kWe", "SOEC capital, scaled off PEM",
               uses=["cost.electrolyser_pem.capex_per_kWe", f"{k}.multiplier_of_pem"], grade="assumed",
               note="No SOEC cost source was found: an SOEC carbon result is sound, an SOEC cost result is not")
        T.cost(f"{k}.fixed_opex_frac", float(r.fixed_opex_frac), "fraction of capital per year",
               "Fixed operating cost: PEM's", grade="assumed", note="No SOEC source: PEM's 2.75 % taken")
        T.cost(f"{k}.variable_opex_per_kg", float(r.variable_opex_GBP_per_kg), "GBP per kg H2",
               "Stack replacement and water per kg made: PEM's, a floor (SOEC stacks wear faster)",
               grade="proxy", cites=neso("variable_opex_GBP_per_kWh_H2_HHV x 39.4 kWh/kg"))
        T.cost(f"{k}.lifetime_years", float(r.lifetime_years), "years", "Plant life", grade="assumed",
               note="No SOEC source: PEM's 25 years taken")
    else:
        T.cost(f"{k}.capex_per_kWe", float(r.capex_GBP_per_kWe), "GBP per kWe", "Electrolyser capital",
               grade="transcribed", cites=neso("capex_GBP_per_kWe"))
        T.cost(f"{k}.fixed_opex_frac", float(r.fixed_opex_frac), "fraction of capital per year",
               "Fixed operating cost", grade="transcribed", cites=neso("fixed_opex_pct_capex"))
        hhv = T.cost("h2.hhv_kwh_per_kg", H2_HHV_KWH_PER_KG, "kWh per kg", "Hydrogen's higher heating value",
                     grade="transcribed", source="the standard figure, 141.8 MJ/kg")
        T.cost(f"{k}.variable_opex_per_kg", float(r.variable_opex_GBP_per_kg), "GBP per kg H2",
               "Stack replacement and water per kg made (NESO charges stack wear on output)",
               uses=["h2.hhv_kwh_per_kg"], cites=neso("variable_opex_GBP_per_kWh_H2_HHV"),
               inputs={"GBP_per_kWh_HHV": float(r.variable_opex_GBP_per_kg) / hhv})
        T.cost(f"{k}.lifetime_years", float(r.lifetime_years), "years", "Plant life", grade="transcribed",
               cites=neso("plant_lifetime_years"))
    return {**r.to_dict(), "trace_prefix": k}


def electrolyser_costs(build_year=2025):
    """AE and PEM from NESO (sourced); SOEC scaled off PEM (assumed).

    ``variable_opex_GBP_per_kg`` is NESO's variable opex — stack replacement and
    water — per kg made. NESO charges stack wear on output, so it is the cost
    counterpart of the carbon side's duty-driven ``ely_stack_units``. SOEC has
    no NESO figure and takes PEM's, as a floor: its stacks wear faster.
    """
    df = pd.read_csv(PRICE_DIR / "electrolyser_costs_clean.csv")
    df = df[df.build_year == build_year]
    scen = {"low": "Low", "central": "Central", "high": "High"}
    rows = []
    for tech, label in (("Alkaline", "electrolyser_ae"), ("PEM", "electrolyser_pem")):
        sub = df[df.technology == tech]
        for case in CASES:
            r = sub[sub.scenario == scen[case]]
            if r.empty:
                continue
            r = r.iloc[0]
            rows.append({
                "asset": label, "case": case,
                "capex_GBP_per_kWe": float(r.capex_GBP_per_kWe),
                "fixed_opex_frac": float(r.fixed_opex_pct_capex),
                "variable_opex_GBP_per_kg": float(r.variable_opex_GBP_per_kWh_H2_HHV)
                                            * H2_HHV_KWH_PER_KG,
                "lifetime_years": float(r.plant_lifetime_years),
                "grade": "transcribed",
                "note": "NESO Green Hydrogen Data Portal",
            })
    pem = _neso_pem_capex(build_year)
    pem_var = {row["case"]: row["variable_opex_GBP_per_kg"] for row in rows
               if row["asset"] == "electrolyser_pem"}
    for case in CASES:
        rows.append({
            "asset": "electrolyser_soec", "case": case,
            "capex_GBP_per_kWe": pem[case] * SOEC_MULTIPLIER_OF_PEM[case],
            "fixed_opex_frac": 0.0275,
            "variable_opex_GBP_per_kg": pem_var[case],
            "lifetime_years": 25.0,
            "grade": GRADE,
            "note": f"NO SOURCE — PEM x {SOEC_MULTIPLIER_OF_PEM[case]:.1f}. "
                    "SOEC carbon results are sound; SOEC cost results are not",
        })
    return pd.DataFrame(rows)


def check(fc_df, tank_df, ely_df):
    problems = []
    for df, col in ((fc_df, "capex_GBP_per_MW"), (tank_df, "capex_GBP_per_kg_capacity"),
                    (ely_df, "capex_GBP_per_kWe")):
        for _, r in df.iterrows():
            if r[col] <= 0:
                problems.append(f"{r['asset']}/{r['case']}: non-positive capex")
            if r["grade"] == GRADE and not str(r["note"]).strip():
                problems.append(f"{r['asset']}/{r['case']}: assumed with no note")
        for asset in df.asset.unique():
            sub = df[df.asset == asset].set_index("case")
            if not (sub.loc["low", col] <= sub.loc["central", col] <= sub.loc["high", col]):
                problems.append(f"{asset}: low/central/high not ordered")
    if problems:
        raise AssertionError("h2_capex failed:\n  " + "\n  ".join(problems))
    n_assumed = sum((d.grade == GRADE).sum() for d in (fc_df, tank_df, ely_df))
    return (f"OK — {n_assumed} assumed rows, every one noted and ordered "
            f"low <= central <= high")


def run():
    fc_df, tank_df, ely_df = fuel_cell_costs(), tank_costs(), electrolyser_costs()
    print("=" * 100)
    print("HYDROGEN-CHAIN ASSET COSTS — real 2025 GBP.  EVERY FIGURE HERE IS ASSUMED")
    print("=" * 100)
    print(check(fc_df, tank_df, ely_df))

    print("\nFuel cell (DOE 100 kW-3 MW stationary, natural gas)")
    print("-" * 100)
    print(f"  {'case':<10}{'USD/kW':>10}{'GBP/kW':>10}{'GBP/MW/yr':>14}{'opex':>8}")
    for _, r in fc_df.iterrows():
        print(f"  {r.case:<10}{FC_USD_PER_KW[r.case]:>10,.0f}{r.capex_GBP_per_kW:>10,.0f}"
              f"{r.annual_GBP_per_MW_year:>14,.0f}{r.fixed_opex_frac:>8.1%}")
    print("  Includes a reformer this study does not have — biased high.")

    print("\nHydrogen vessel")
    print("-" * 100)
    print(f"  {'case':<10}{'EUR/kg':>10}{'GBP/kg':>10}{'GBP/kg/yr':>14}")
    for _, r in tank_df.iterrows():
        print(f"  {r.case:<10}{TANK_EUR_PER_KG_CAPACITY[r.case]:>10,.0f}"
              f"{r.capex_GBP_per_kg_capacity:>10,.0f}{r.annual_GBP_per_kg_year:>14,.1f}")

    print("\nElectrolysers")
    print("-" * 100)
    print(f"  {'asset':<20}{'case':<10}{'GBP/kWe':>10}{'grade':>14}")
    for _, r in ely_df.iterrows():
        print(f"  {r.asset:<20}{r.case:<10}{r.capex_GBP_per_kWe:>10,.0f}{r.grade:>14}")
    flat = [a for a in ely_df.asset.unique()
            if ely_df[ely_df.asset == a].capex_GBP_per_kWe.nunique() == 1]
    if flat:
        print(f"\n  NESO publishes a single capex per technology per build year — its")
        print(f"  Low/Central/High labels vary the LCOH scenario, not the capital cost.")
        print(f"  So {', '.join(flat)} carry **no published uncertainty range**, while")
        print("  every assumed input around them does. A cost-case sweep therefore moves")
        print("  the fuel cell and the tank but holds the electrolyser fixed, which")
        print("  understates the true spread on any on-site electrolysis result.")

    print("\nWhat this does to a 7.31 MW hydrogen backup chain, central case")
    print("-" * 100)
    fcc = fc_df[fc_df.case == "central"].iloc[0]
    tk = tank_df[tank_df.case == "central"].iloc[0]
    fc_year = fcc.annual_GBP_per_MW_year * 7.31
    for tonnes in (5, 10, 20, 50):
        tank_year = tk.annual_GBP_per_kg_year * tonnes * 1000
        print(f"  fuel cell 7.31 MW + {tonnes:>2} t tank    "
              f"£{(fc_year + tank_year) / 1e6:>5.2f} m/yr   "
              f"(fuel cell £{fc_year / 1e6:.2f} m + tank £{tank_year / 1e6:.2f} m)")
    crossover = fc_year / (tk.annual_GBP_per_kg_year * 1000)
    print(f"\n  Against a £6.60 m/yr delivered grid bill for the same data centre.")
    print(f"  The fuel cell dominates below {crossover:.0f} t of storage and the tank above it.")
    print("  Both are ASSUMED. So across the whole plausible range of tank sizes, the")
    print("  cost of a hydrogen chain is set by two numbers with no UK source and")
    print("  spreads of 4.5x and 2x respectively. The carbon side of these same")
    print("  architectures is fully sourced; the cost side is not. Rank hydrogen")
    print("  options on carbon with confidence, and on cost only with the caveat.")

    OUT_DIR.mkdir(exist_ok=True)
    out = pd.concat([fc_df, tank_df, ely_df], ignore_index=True)
    out.to_csv(OUT_DIR / "h2_capex.csv", index=False)
    print("\nWrote:\n  optimisation_outputs/h2_capex.csv")
    return out


if __name__ == "__main__":
    run()
