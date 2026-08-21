"""
Optimal wind / solar / battery sizing for an electrolyser.
=============================================================================

You fix the electrolyser — technology, rating, running strategy — and a site
and date range. This finds the cheapest wind, solar and battery build that
still meets an emissions threshold, by default the **UK Low Carbon Hydrogen
Standard: 20 gCO2e/MJ LHV**, which at hydrogen's 120 MJ/kg is 2.4 kg CO2e per
kg H2 at the point of production.

Method
------
A half-hourly chronological dispatch, then a search over four sizes (wind MW,
solar MWp, battery MW, battery MWh). Dispatch is a merit order, which is what
a price-taking plant with a fixed load actually does:

  1. wind and solar serve the electrolyser directly
  2. surplus charges the battery, then is curtailed
  3. shortfall is covered by the battery, then by the grid if the strategy
     allows it

The battery starts **full**, carries state between steps, and the series is
required to be chronological — ``profiles.py`` refuses sampled
"representative day" files for exactly this reason.

The objective is the levelised cost of hydrogen. The emissions threshold is a
constraint, applied as a penalty, so the answer is "cheapest build that
complies" rather than a weighted blend of the two.

Every number is listed in ``SOURCES.md`` alongside its provenance grade.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from optimisation import battery as batt_mod
from optimisation import renewables as ren_mod
from optimisation import tech_costs as tc

HOURS_PER_YEAR = 8760.0
H2_LHV_MJ_PER_KG = 120.0

# UK Low Carbon Hydrogen Standard v3 (December 2023): 20.0 gCO2e/MJ LHV at the
# point of production.
LCHS_GCO2E_PER_MJ = 20.0

STRATEGIES = {
    "baseload": "Run flat at rated power. The grid covers whatever wind, solar "
                "and the battery cannot.",
    "renewables_only": "Never import. The electrolyser follows whatever the site "
                       "and battery can deliver, and shuts down below minimum load.",
    "grid_when_clean": "Run flat, but only import when grid intensity is at or "
                       "below a chosen threshold; otherwise follow the site.",
}


def lchs_kgco2e_per_kg(g_per_mj: float = LCHS_GCO2E_PER_MJ) -> float:
    """Convert a gCO2e/MJ LHV threshold into kg CO2e per kg of hydrogen."""
    return g_per_mj * H2_LHV_MJ_PER_KG / 1000.0


@dataclass
class Electrolyser:
    """The fixed side of the problem — the user chooses all of this."""
    tech: str = "PEM operation"            # AE / PEM / SOEC operation
    capacity_mw: float = 10.0
    strategy: str = "renewables_only"
    min_load_fraction: float = 0.10
    clean_grid_threshold_kgco2e_per_kwh: float = 0.05   # grid_when_clean only
    kwh_per_kg: float = 54.0               # read from Brightway by load_electrolyser()
    fixed_kgco2e_per_kg: float = 0.1951    # non-electricity burden, same source
    capex_gbp_per_kwe: float = 2010.0      # NESO central 2025
    fixed_opex_frac: float = 0.0275
    lifetime_years: float = 25.0
    discount_rate: float = 0.06

    def __post_init__(self):
        if self.strategy not in STRATEGIES:
            raise ValueError(f"strategy must be one of {list(STRATEGIES)}")
        if not 0.0 <= self.min_load_fraction < 1.0:
            raise ValueError("min_load_fraction must be in [0, 1)")
        if self.capacity_mw <= 0:
            raise ValueError("capacity_mw must be positive")


@dataclass
class Sizing:
    wind_mw: float = 0.0
    solar_mwp: float = 0.0
    battery_mw: float = 0.0
    battery_mwh: float = 0.0


def load_electrolyser(tech: str, **overrides) -> Electrolyser:
    """Read a technology's real coefficients out of the Brightway foreground."""
    import bw2data as bd
    import lca_helpers as H

    _ei, _bio, _fg, _m = H.setup_brightway()
    method = next(m for m in bd.methods if m[1] == "IPCC 2021"
                  and m[2] == "climate change" and "GWP100" in str(m)
                  and "no LT" not in str(m))
    code = H.ELECTROLYSER_CODES[tech]
    act = bd.get_activity(("hydrogen foreground", code))
    fixed, kwh, _n = H.run_non_electricity_lca(act, method)
    return Electrolyser(tech=tech, kwh_per_kg=kwh,
                        fixed_kgco2e_per_kg=fixed, **overrides)


# =============================================================================
# Dispatch
# =============================================================================
def simulate(profiles: pd.DataFrame, ely: Electrolyser, sizing: Sizing,
             dt_hours: float = 0.5, rte: float | None = None) -> dict:
    """One chronological pass. Returns energy and hydrogen totals for the window.

    The battery starts full, as specified. Round-trip efficiency is split
    evenly between charge and discharge so a full cycle costs exactly ``rte``.
    """
    rte = batt_mod.ROUND_TRIP_EFFICIENCY if rte is None else rte
    eta = np.sqrt(rte)

    wind_kw = sizing.wind_mw * 1000.0
    solar_kw = sizing.solar_mwp * 1000.0
    ely_kw = ely.capacity_mw * 1000.0
    bp_kw = sizing.battery_mw * 1000.0
    be_kwh = sizing.battery_mwh * 1000.0
    min_kw = ely_kw * ely.min_load_fraction

    avail = (profiles["wind_cf"].to_numpy() * wind_kw
             + profiles["solar_cf"].to_numpy() * solar_kw)
    grid_ef = profiles["grid_kgco2e_per_kwh"].to_numpy()
    price = profiles["price_GBP_per_MWh"].to_numpy()

    grid_allowed = {
        "baseload": np.ones(len(avail), dtype=bool),
        "renewables_only": np.zeros(len(avail), dtype=bool),
        "grid_when_clean": grid_ef <= ely.clean_grid_threshold_kgco2e_per_kwh,
    }[ely.strategy]

    soc = be_kwh                      # battery starts full
    max_step_kwh = bp_kw * dt_hours

    ely_kwh = grid_kwh = curtailed_kwh = 0.0
    grid_cost = grid_emissions = 0.0
    gen_kwh = 0.0
    soc_trace = np.empty(len(avail))

    for i in range(len(avail)):
        a_kwh = avail[i] * dt_hours
        gen_kwh += a_kwh
        target_kwh = ely_kw * dt_hours

        direct = min(a_kwh, target_kwh)
        surplus = a_kwh - direct
        deficit = target_kwh - direct

        discharge = 0.0
        if deficit > 0 and be_kwh > 0:
            discharge = min(deficit, max_step_kwh, soc * eta)
            soc -= discharge / eta
            deficit -= discharge

        imported = 0.0
        if deficit > 0 and grid_allowed[i]:
            imported = deficit
            deficit = 0.0

        load = direct + discharge + imported
        if load < min_kw * dt_hours:
            # Below minimum load the stack shuts down; anything already drawn
            # from the battery or grid would not have been taken at all.
            soc += discharge / eta
            imported = 0.0
            surplus += direct
            load = 0.0

        if surplus > 0 and be_kwh > 0:
            charge = min(surplus, max_step_kwh, (be_kwh - soc) / eta)
            soc += charge * eta
            surplus -= charge

        ely_kwh += load
        grid_kwh += imported
        curtailed_kwh += surplus
        grid_cost += imported / 1000.0 * price[i]
        grid_emissions += imported * grid_ef[i]
        soc_trace[i] = soc

    hours = len(avail) * dt_hours
    return {
        "hours": hours,
        "generated_kwh": gen_kwh,
        "electrolyser_kwh": ely_kwh,
        "grid_kwh": grid_kwh,
        "curtailed_kwh": curtailed_kwh,
        "grid_cost_gbp": grid_cost,
        "grid_emissions_kgco2e": grid_emissions,
        "h2_kg": ely_kwh / ely.kwh_per_kg,
        "capacity_factor": ely_kwh / (ely_kw * hours) if ely_kw else 0.0,
        "renewable_fraction": (ely_kwh - grid_kwh) / ely_kwh if ely_kwh else 0.0,
        "soc_final_frac": soc / be_kwh if be_kwh else float("nan"),
        "soc_min_frac": float(soc_trace.min() / be_kwh) if be_kwh else float("nan"),
    }


# =============================================================================
# Cost and emissions
# =============================================================================
def _annual_scale(hours: float) -> float:
    return HOURS_PER_YEAR / hours


@dataclass
class Coefficients:
    """Per-MW cost and emission rates, resolved once.

    ``evaluate`` used to rebuild the DESNZ cost table on every call, which made
    the optimiser spend eight times longer assembling DataFrames than running
    dispatches. Everything here is constant across a solve, so it is resolved
    once and passed in.
    """
    cost_wind_per_mw: float
    cost_solar_per_mwp: float
    em_wind_per_mw: float
    em_solar_per_mwp: float
    batt_cost_per_mw: float
    batt_cost_per_mwh: float
    batt_em_per_mw: float
    batt_em_per_mwh: float
    ely_cost_per_year: float

    @classmethod
    def build(cls, ely: "Electrolyser", renewable_embodied: pd.DataFrame,
              cost_case: str = "central") -> "Coefficients":
        ann = tc.annualised_table()
        emb = renewable_embodied.set_index("technology")

        def cost_of(asset):
            return float(ann[(ann.asset == asset) & (ann.case == cost_case)]
                         .iloc[0].total_annual_cost_GBP_per_MW_year)

        def em_of(asset):
            row = emb.loc[asset]
            return float(row.capital_kgco2e_per_MW / row.study_lifetime_years)

        bc = batt_mod.cost_components()[cost_case]
        crf_b = batt_mod.capital_recovery_factor(
            batt_mod.WACC_REAL, batt_mod.ASSET_LIFE_YEARS)
        annuity = crf_b + batt_mod.FIXED_OPEX_PCT_CAPEX[cost_case]
        be = batt_mod.embodied_components()

        ely_capex = ely.capex_gbp_per_kwe * ely.capacity_mw * 1000.0
        crf_e = batt_mod.capital_recovery_factor(ely.discount_rate, ely.lifetime_years)

        return cls(
            cost_wind_per_mw=cost_of("onshore_wind"),
            cost_solar_per_mwp=cost_of("solar_pv"),
            em_wind_per_mw=em_of("onshore_wind"),
            em_solar_per_mwp=em_of("solar_pv"),
            batt_cost_per_mw=bc["power_GBP_per_kW"] * 1000.0 * annuity,
            batt_cost_per_mwh=bc["energy_GBP_per_kWh"] * 1000.0 * annuity,
            batt_em_per_mw=be["power_kgco2e_per_kW"] * 1000.0 / batt_mod.ASSET_LIFE_YEARS,
            batt_em_per_mwh=be["energy_kgco2e_per_kWh"] * 1000.0 / batt_mod.ASSET_LIFE_YEARS,
            ely_cost_per_year=ely_capex * (crf_e + ely.fixed_opex_frac),
        )


def evaluate(sim: dict, ely: Electrolyser, sizing: Sizing,
             coeff: Coefficients) -> dict:
    """Turn a dispatch into annualised cost, emissions, LCOH and gCO2e/MJ.

    Everything is annualised so that assets with different lives — a 35-year
    turbine, a 15-year battery, a 25-year electrolyser — can be added up
    without one of them silently getting a longer life than it has.
    """
    scale = _annual_scale(sim["hours"])
    h2_kg = sim["h2_kg"] * scale
    if h2_kg <= 0:
        return {"feasible": False, "h2_kg_yr": 0.0, "lcoh_gbp_per_kg": float("inf"),
                "gco2e_per_mj": float("inf"), "kgco2e_per_kg": float("inf")}

    cost_wind = coeff.cost_wind_per_mw * sizing.wind_mw
    cost_solar = coeff.cost_solar_per_mwp * sizing.solar_mwp
    cost_batt = (coeff.batt_cost_per_mw * sizing.battery_mw
                 + coeff.batt_cost_per_mwh * sizing.battery_mwh)
    cost_ely = coeff.ely_cost_per_year
    cost_grid = sim["grid_cost_gbp"] * scale
    total_cost = cost_wind + cost_solar + cost_batt + cost_ely + cost_grid

    em_wind = coeff.em_wind_per_mw * sizing.wind_mw
    em_solar = coeff.em_solar_per_mwp * sizing.solar_mwp
    em_batt = (coeff.batt_em_per_mw * sizing.battery_mw
               + coeff.batt_em_per_mwh * sizing.battery_mwh)
    em_grid = sim["grid_emissions_kgco2e"] * scale
    em_stack = ely.fixed_kgco2e_per_kg * h2_kg
    total_em = em_wind + em_solar + em_batt + em_grid + em_stack

    kg_per_kg = total_em / h2_kg
    return {
        "feasible": True,
        "h2_kg_yr": h2_kg,
        "lcoh_gbp_per_kg": total_cost / h2_kg,
        "kgco2e_per_kg": kg_per_kg,
        "gco2e_per_mj": kg_per_kg * 1000.0 / H2_LHV_MJ_PER_KG,
        "cost_total_gbp_yr": total_cost,
        "cost_wind": cost_wind, "cost_solar": cost_solar,
        "cost_battery": cost_batt, "cost_electrolyser": cost_ely,
        "cost_grid": cost_grid,
        "em_total_kgco2e_yr": total_em,
        "em_wind": em_wind, "em_solar": em_solar, "em_battery": em_batt,
        "em_grid": em_grid, "em_stack": em_stack,
        "grid_kwh_yr": sim["grid_kwh"] * scale,
        "curtailed_kwh_yr": sim["curtailed_kwh"] * scale,
        "electrolyser_kwh_yr": sim["electrolyser_kwh"] * scale,
        "capacity_factor": sim["capacity_factor"],
        "renewable_fraction": sim["renewable_fraction"],
        "soc_min_frac": sim["soc_min_frac"],
    }


# =============================================================================
# Optimiser
# =============================================================================
@dataclass
class Bounds:
    """Search space, expressed as multiples of the electrolyser's rating."""
    wind_mw: tuple = (0.0, 5.0)
    solar_mwp: tuple = (0.0, 5.0)
    battery_mw: tuple = (0.0, 2.0)
    battery_hours: tuple = (0.0, 8.0)


def optimise(profiles: pd.DataFrame, ely: Electrolyser, *,
             threshold_g_per_mj: float = LCHS_GCO2E_PER_MJ,
             cost_case: str = "central", bounds: Bounds | None = None,
             maxiter: int = 40, popsize: int = 12, seed: int = 0,
             progress=None, embodied: pd.DataFrame | None = None) -> dict:
    """Cheapest wind/solar/battery build that meets the emissions threshold.

    Battery energy is searched as *hours of duration* rather than MWh, because
    duration and power are only weakly coupled and the solver converges far
    better on that parameterisation than on two independent capacities.
    """
    from scipy.optimize import differential_evolution

    bounds = bounds or Bounds()
    rating = ely.capacity_mw
    limit_kg = lchs_kgco2e_per_kg(threshold_g_per_mj)
    # `embodied` is exposed so a caller can substitute a different embodied
    # carbon basis - most usefully a modern PV figure, since ecoinvent 3.9.1's
    # GB PV dataset is a 2012 plant. See SOURCES.md.
    if embodied is None:
        embodied = ren_mod.apply_case(ren_mod.decompose_all(), cost_case)
    coeff = Coefficients.build(ely, embodied, cost_case)

    lo_hi = [tuple(b * rating for b in bounds.wind_mw),
             tuple(b * rating for b in bounds.solar_mwp),
             tuple(b * rating for b in bounds.battery_mw),
             bounds.battery_hours]

    calls = {"n": 0}

    def unpack(x):
        wind, solar, bmw, bhours = x
        return Sizing(wind_mw=wind, solar_mwp=solar, battery_mw=bmw,
                      battery_mwh=bmw * bhours)

    def objective(x):
        calls["n"] += 1
        if progress is not None and calls["n"] % 25 == 0:
            progress(calls["n"])
        sizing = unpack(x)
        res = evaluate(simulate(profiles, ely, sizing), ely, sizing, coeff)
        if not res["feasible"]:
            return 1e6
        penalty = max(0.0, res["kgco2e_per_kg"] - limit_kg)
        # Scaled so a 0.1 kg/kg breach costs more than any plausible LCOH
        # saving, making the threshold a constraint rather than a trade-off.
        return res["lcoh_gbp_per_kg"] + 1000.0 * penalty

    result = differential_evolution(
        objective, lo_hi, maxiter=maxiter, popsize=popsize, seed=seed,
        tol=0.01, polish=True, init="sobol")

    best = unpack(result.x)
    sim = simulate(profiles, ely, best)
    res = evaluate(sim, ely, best, coeff)

    # A bound the solver pressed against means the answer is limited by the
    # search space, not by physics or economics — worth saying so, because the
    # usual cause of an infeasible result is a ceiling set too low.
    binding = []
    for name, value, (lo, hi) in zip(
            ("wind_mw", "solar_mwp", "battery_mw", "battery_hours"),
            (best.wind_mw, best.solar_mwp, best.battery_mw,
             best.battery_mwh / best.battery_mw if best.battery_mw else 0.0),
            lo_hi):
        span = hi - lo
        if span > 0 and value >= hi - 0.01 * span:
            binding.append(name)

    res.update({
        "wind_mw": best.wind_mw, "solar_mwp": best.solar_mwp,
        "battery_mw": best.battery_mw, "battery_mwh": best.battery_mwh,
        "battery_hours": best.battery_mwh / best.battery_mw if best.battery_mw else 0.0,
        "threshold_g_per_mj": threshold_g_per_mj,
        "threshold_kgco2e_per_kg": limit_kg,
        "meets_threshold": res["kgco2e_per_kg"] <= limit_kg + 1e-9,
        "binding_bounds": binding,
        "evaluations": calls["n"],
        "cost_case": cost_case,
    })
    if not res["meets_threshold"]:
        res["infeasible_reason"] = (
            f"No build in the search space meets {threshold_g_per_mj:g} gCO2e/MJ. "
            f"The best achievable is {res['gco2e_per_mj']:.1f} gCO2e/MJ"
            + (f", and the solver is against its {', '.join(binding)} "
               f"limit{'s' if len(binding) > 1 else ''} — raise the bounds and "
               "retry." if binding else
               ", with no bound binding, so the limit is the strategy or the "
               "grid, not the search space.")
        )
    return res
