"""
The cost side's cut-off register — what the cost objective leaves out, and how big.
=============================================================================

The carbon rule (``optimiser_lca/exclusions.py``) on the cost objective, by the
same principle: a cost a held source itemises, inside the boundary, is in whatever
its size. The test is for costs no source itemises for this asset:

1. per flow, its upper estimate under **1 %** of the coefficient the LP charges;
2. per coefficient, all of its excluded flows together under **5 %**;
3. per decision, adding them back must not change the best design
   (``dc_inputs.build_tech(cost_cutoff="upper")``,
   ``python -m optimisation.sensitivity cost_cutoff``).

A flow that fails is included as an estimate, not argued away: those are listed
here with ``status="included_estimate"`` and carried in their own modules. Status
``open`` means there is no figure to test, or one this register cannot hold (a step
charge on a linear coefficient): it is stated, and needs a person.

Run:  python optimisation/cost_exclusions.py
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

RULE_1 = 0.01
RULE_2 = 0.05
ACRE_M2 = 4_046.86
RURAL_RENT_GBP_PER_M2_YEAR = 1_000.0 * (103.6 / 96.3) / ACRE_M2     # DESNZ §6.8.1, 2025 pounds


@dataclass(frozen=True)
class CostFlow:
    key: str
    coefficient: str           # the Tech field it would land on ("" when none)
    kind: str                  # cutoff | boundary
    status: str                # excluded | included_estimate | open | boundary
    upper: float | None        # upper estimate, in the coefficient's own unit
    basis: str


REGISTER = (
    # --- tested and left out ------------------------------------------------
    CostFlow("battery land", "cost_batt_e", "cutoff", "excluded", 60.0 * RURAL_RENT_GBP_PER_M2_YEAR,
             "60 m²/MWh, the top of Lincolnshire CC's planning figures (Mott MacDonald for BEIS 2018: 9), at DESNZ's rural "
             "rent. Urban land is the open item below"),
    CostFlow("fuel cell land", "cost_fc", "cutoff", "excluded", 125.0 * 0.0872,
             "Reznicek et al. 2026, Table 18: $0.16/kW, annualised. Not government"),
    # --- failed, so carried in their own modules ----------------------------
    CostFlow("tank land", "cost_tank", "cutoff", "included_estimate", 2.09,
             "h2_capex.TANK_FOOTPRINT_M2_PER_KWH_HHV at the rural rent: about 2.3 % of cost_tank"),
    CostFlow("fuel cell insurance", "cost_fc", "cutoff", "included_estimate", 5_021.0,
             "h2_capex.FC_INSURANCE_FRAC_OF_CAPITAL, onshore wind's ratio: about 2.3 % of cost_fc"),
    CostFlow("supplier margin", "", "cutoff", "included_estimate", None,
             "levies.flat_components: 2.0 % of the extra-large price, £4.19/MWh; 1 % of the reference run's grid chain is "
             "crossed at about £1.60/MWh"),
    CostFlow("battery business rates", "cost_batt_p", "cutoff", "excluded", 0.0,
             "Zero to 31 March 2035: SI 2022/405 exempts plant used mainly for the storage of renewable power, which this "
             "battery is (its memorandum, §7.2). Solar's £1.8k/MW/yr is the figure to sweep for the years after"),
    CostFlow("hydrogen compressor capital", "cost_ely", "cutoff", "included_estimate", None,
             "Already charged by another route: compression power sits inside cap_ely at electrolyser rates, 47 kW per "
             "MW of solid-oxide, about £120k/MW, inside the calculated range of £72–215k/MW (textbook, Element Energy "
             "extrapolated, Danish Energy Agency). A separate line would double count. Zero on the PEM default"),
    CostFlow("battery step-up transformer", "cost_batt_p", "cutoff", "included_estimate", None,
             "Read as inside the capital: Mott MacDonald for BEIS (2018) lists electrical systems in and connection out. "
             "BEIS 2022, the figure charged, does not itemise its scope, so this is a reading, not a statement"),
    CostFlow("fuel cell step-up transformer", "cost_fc", "cutoff", "included_estimate", None,
             "Inside the capital: Baringa's figure is the installed cost of a real 80 MW plant, not equipment. If it were "
             "not, about £3k/MW/yr at half NGED's 33 kV double-transformer price per firm MVA"),
    CostFlow("major-hazard compliance", "", "cutoff", "included_estimate", None,
             "Sourced, so in whatever its size: HSE 0082 (2013 prices, per site), upper tier over 50 t, one-off £118k and "
             "£27k a year, about £56k a year in 2025 pounds. A step on tonnes held, carried flat at upper tier on any build "
             "allowed a tank (dc_model.major_hazard_cost), since every North Norfolk design holds 112-221 t; it overstates "
             "a small tank by at most that much"),
    CostFlow("the seller's hydrogen loading compressor", "", "cutoff", "excluded", None,
             "No public per-kg figure. Rule 3 without one: it could only make bought hydrogen dearer, and none of the 89 "
             "saved sweep rows buys any at today's price"),
    # --- needs a person -----------------------------------------------------
    CostFlow("land at an urban site", "", "cutoff", "open", None,
             "Every land figure charged is a rural rent and dc_model has no area limit. Left so by the user (4 Nov 2026): "
             "a central-London run is illustrative, not a use case. MHCLG industrial land values are in "
             "docs/COST_SOURCES_NON_UK_2026-11-04.md if this ever returns"),
    # --- the boundary: reported, never tested -------------------------------
    CostFlow("decommissioning", "", "boundary", "boundary", None,
             "DESNZ/Arup §5.8 and §6.8: £31k and £15k/MW once, at end of life; end-of-life is outside the carbon boundary too"),
    CostFlow("the data centre's building and IT, and its standby generator", "", "boundary", "boundary", None,
             "Constant across designs, so they move no choice, and the £/MWh is not an all-in figure"),
    CostFlow("road haulage of bought hydrogen", "", "boundary", "boundary", None,
             "Transport to site, the one transport the study leaves out: the site and seller are unknown"),
    CostFlow("selling power to the grid", "", "boundary", "boundary", None,
             "The model refuses export (dc_model.build_model), because it has no export price or carbon credit. Surplus "
             "power is worth nothing, so a design with spare generation reads dearer than it would be"),
    CostFlow("the time to get a grid connection", "", "boundary", "boundary", None,
             "Not a price per MW, and the study has one period. Published room is taken as available; a site with room may "
             "still wait in the queue"),
)


def check(tech) -> list[dict]:
    """Rule 1 on every flow with a coefficient and an upper estimate."""
    rows = []
    for f in REGISTER:
        if not f.coefficient or f.upper is None:
            continue
        share = f.upper / getattr(tech, f.coefficient)
        rows.append({"flow": f.key, "coefficient": f.coefficient, "status": f.status, "upper": f.upper, "share": share,
                     "passes_rule_1": share < RULE_1})
    return rows


def failures(tech) -> list[str]:
    """What breaks the rule among flows still left out: empty is a pass."""
    out = []
    totals: dict[str, float] = {}
    for r in check(tech):
        if r["status"] != "excluded":
            continue
        totals[r["coefficient"]] = totals.get(r["coefficient"], 0.0) + r["share"]
        if not r["passes_rule_1"]:
            out.append(f"{r['flow']}: {r['share']:.2%} of {r['coefficient']}, over {RULE_1:.0%}")
    out += [f"{c}: excluded flows together {s:.2%}, over {RULE_2:.0%}" for c, s in totals.items() if s >= RULE_2]
    return out


def upper_additions() -> dict[str, float]:
    """Rule 3: what ``cost_cutoff="upper"`` adds, by coefficient."""
    added: dict[str, float] = {}
    for f in REGISTER:
        if f.status == "excluded" and f.upper:
            added[f.coefficient] = added.get(f.coefficient, 0.0) + float(f.upper)
    return added


if __name__ == "__main__":
    print("The cost register\n")
    for f in REGISTER:
        print(f"  {f.status:<18}{f.key}\n{'':<20}{f.basis}\n")
