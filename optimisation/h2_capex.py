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
    """Stack share of fuel cell capital, taken from the LCA's own split."""
    from optimisation import fuel_cell as fc
    d = fc.decompose()
    stack, bop = d["stack_kgco2e_per_MW"], d["bop_kgco2e_per_MW"]
    return stack / (stack + bop)


def fuel_cell_costs():
    """£/kW installed, and the annualised £/kW/year that follows."""
    from optimisation import fuel_cell as fc
    d = fc.decompose()
    life = d["bop_calendar_lifetime_years"]
    crf = capital_recovery_factor(FC_DISCOUNT_RATE, life)
    rows = []
    for case in CASES:
        capex = FC_USD_PER_KW[case] / USD_PER_GBP_2025
        # Split capital between stack and balance of plant on the *same*
        # fraction the LCA uses, because it is the same physical decomposition
        # and a second free parameter would only invite the two to drift apart.
        # DOE's independent finding agrees with the shape: for stationary PEM
        # systems the stack is under 50 % of system cost and typically under
        # 15 % at volume, with BoP dominating. This study's carbon split puts
        # the stack at 17 %, inside that range.
        #
        # It matters because the stack wears out on *duty* — 32,000 hours — while
        # BoP runs to calendar. Charging the whole system on calendar life made
        # running the fuel cell hard free in cost while still costing carbon, so
        # the two objectives were pricing different physics for one machine.
        stack_frac = fc_stack_cost_fraction()
        rows.append({
            "asset": "fuel_cell", "case": case,
            "capex_GBP_per_kW": capex,
            "capex_GBP_per_MW": capex * 1000.0,
            "fixed_opex_frac": FC_FIXED_OPEX_FRAC[case],
            "lifetime_years": life,
            "stack_cost_fraction": stack_frac,
            # BoP only: the calendar-driven part, annualised as before.
            "annual_GBP_per_MW_year": (capex * 1000.0 * (1.0 - stack_frac)
                                       * (crf + FC_FIXED_OPEX_FRAC[case])),
            # Stack capital, charged per replacement. Undiscounted, matching the
            # carbon side, because the LP abstracts away *when* a replacement
            # falls and a discount factor would need that schedule. This
            # overstates a distant replacement slightly.
            "stack_GBP_per_MW": capex * 1000.0 * stack_frac,
            "grade": GRADE,
            "note": "DOE natural-gas system — includes a reformer this study does "
                    "not have, so biased high" if FC_INCLUDES_REFORMER else "",
        })
    return pd.DataFrame(rows)


def tank_costs():
    """£ per kg of hydrogen storage capacity."""
    import dc_config as cfg
    life = float(cfg.TANK_LIFETIME_YEARS)
    crf = capital_recovery_factor(FC_DISCOUNT_RATE, life)
    rows = []
    for case in CASES:
        capex = TANK_EUR_PER_KG_CAPACITY[case] / EUR_PER_GBP_2025
        rows.append({
            "asset": "h2_tank", "case": case,
            "capex_GBP_per_kg_capacity": capex,
            "fixed_opex_frac": TANK_FIXED_OPEX_FRAC[case],
            "lifetime_years": life,
            "annual_GBP_per_kg_year": capex * (crf + TANK_FIXED_OPEX_FRAC[case]),
            "grade": GRADE,
            "note": "spread across the literature is over 2x; none of the sources "
                    "is UK or recent",
        })
    return pd.DataFrame(rows)


def _neso_pem_capex(build_year=2025):
    """PEM capex from the NESO table the repo already has."""
    df = pd.read_csv(PRICE_DIR / "electrolyser_costs_clean.csv")
    df = df[(df.technology == "PEM") & (df.build_year == build_year)]
    if df.empty:
        raise ValueError(f"No NESO PEM capex for build year {build_year}")
    return {"low": float(df[df.scenario == "Low"].iloc[0].capex_GBP_per_kWe),
            "central": float(df[df.scenario == "Central"].iloc[0].capex_GBP_per_kWe),
            "high": float(df[df.scenario == "High"].iloc[0].capex_GBP_per_kWe)}


def electrolyser_costs(build_year=2025):
    """AE and PEM from NESO (sourced); SOEC scaled off PEM (assumed)."""
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
                "lifetime_years": float(r.plant_lifetime_years),
                "grade": "transcribed",
                "note": "NESO Green Hydrogen Data Portal",
            })
    pem = _neso_pem_capex(build_year)
    for case in CASES:
        rows.append({
            "asset": "electrolyser_soec", "case": case,
            "capex_GBP_per_kWe": pem[case] * SOEC_MULTIPLIER_OF_PEM[case],
            "fixed_opex_frac": 0.0275,
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
