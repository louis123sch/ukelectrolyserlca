"""
The data centre powering LP — size and dispatch, solved together.
=============================================================================

Give it a data centre size, a site, a window and a power option; it returns the
cheapest or the cleanest set of kit that keeps that data centre running every
half-hour of the window, and the dispatch that goes with it.

Why a linear program
--------------------
``sizing.py`` searches four dimensions with differential evolution over a
merit-order dispatch. That works for its question — cheapest build for a *fixed*
electrolyser. This problem has **nine** sizing dimensions and an inter-seasonal
hydrogen store, and at ~17,000 half-hourly steps per evaluation a population
search would take hours per configuration and still not find the global optimum.

Both objectives are linear in the same decision variables. That is not luck: it
is what ``baseline_grid.py``'s ``fixed + Σ kWh × EF`` decomposition established,
and what the capacity-shaped coefficients in ``electrolysers.py``,
``fuel_cell.py`` and ``h2_storage.py`` preserve. So the sizing and the dispatch
can be solved *jointly and exactly*, and the Pareto front between cost and
carbon is exact rather than sampled.

Solving them jointly is the point. A tank's value comes from filling in March
and draining in November, so its size cannot be chosen before its dispatch is
known. A merit-order rule — like the one in ``4.3.wind_h2_storage_system.ipynb``
— has no foresight and systematically mis-sizes the store.

One node, and what that means
-----------------------------
Constraint (1) is a copper plate at the campus. There is deliberately no
"route renewables to the data centre" variable separate from "route renewables
to the electrolyser": the allocation is what the LP *solves for* when it picks
``p_ely[t]`` against ``demand[t]``, and generation not consumed is curtailed
because (2) is an inequality. Adding routing variables would double the model
and change nothing. It does mean no internal network, no transmission limits and
no curtailment priority within the site.

Perfect foresight is an optimistic bound
----------------------------------------
The LP sees every half-hour at once, so it will electrolyse in March surplus
*because* it knows a November lull is coming. No operator has that forecast.
This is a legitimate way to answer **"what should I build?"** and an illegitimate
way to answer **"what will I achieve?"**. Every result carries
``perfect_foresight=True`` so the distinction survives into the write-up.

Linearisations, stated
----------------------
* **No unit commitment.** Minimum load on the electrolyser and the fuel cell is
  genuinely a binary constraint. The LP will run an electrolyser at 1 % of
  rating, which is physically wrong and economically near-irrelevant since full
  capital is charged either way. Revisit only if a result looks wrong.
* **Replacement counts** for the fuel cell stack and BoP use the convex
  ``max(calendar, duty)`` rule from ``fuel_cell.REPLACEMENT_LP_NOTE``, expressed
  exactly as two ``>=`` constraints on a free variable the objective minimises.
* **Storage is cyclic.** ``soc.roll(t=1)`` wraps the last step into the first, so
  the store cannot free-ride on ending the year empty.
* **Surplus-only is a window constraint**, not a per-step one — the per-step form
  is infeasible rather than binding whenever generation falls short. See
  ``apply_strategy``. One consequence, expected rather than a bug: in the
  islanded rows ``flexible`` and ``free`` land close together, because with no
  grid and no battery the only alternatives to serving demand from renewables
  are unserved load or a lossy round trip through the tank. The real contrast
  there is ``baseload`` against the rest.

Run:  python optimisation/dc_model.py
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

HOURS_PER_YEAR = 8760.0
H2_LHV_KWH_PER_KG = 33.33

# Value of lost load. Not a market number — a penalty large enough that an
# infeasible reliability target surfaces as an expensive answer rather than a
# solver failure, which is far easier to diagnose. ASSUMED.
VOLL_GBP_PER_MWH = 100_000.0
VOLL_IS_ASSUMED = True


@dataclass
class Assets:
    """Which assets this architecture may build. Zero means it does not exist.

    Everything is an upper bound, never a requirement: the LP sets an unlocked
    asset to zero whenever it is not worth building.
    """
    grid: bool = True
    wind: bool = False
    offshore_wind: bool = False
    solar: bool = False
    battery: bool = False
    electrolyser: bool = False
    tank: bool = False
    fuel_cell: bool = False
    buy_h2: bool = False

    grid_limit_mw: float | None = None
    allow_export: bool = False


@dataclass
class Tech:
    """Every coefficient the LP needs, resolved before the model is built.

    Assembled by ``build_tech()`` from the coefficient modules so that nothing
    here touches Brightway or the network-charge APIs during a solve.
    """
    # carbon, per MW (or per MWh / per kg) per year
    gwp_wind: float; gwp_offshore: float; gwp_solar: float
    gwp_batt_p: float; gwp_batt_e: float
    gwp_ely: float; gwp_tank: float
    gwp_fc_bop_per_mw: float; gwp_fc_stack_per_mw: float
    gwp_fc_maint_per_mwh: float
    gwp_grid_per_mw: float
    fc_bop_calendar_years: float; fc_bop_duty_hours: float
    fc_stack_duty_hours: float
    # cost, GBP per MW (or MWh / kg) per year
    cost_wind: float; cost_offshore: float; cost_solar: float
    cost_batt_p: float; cost_batt_e: float
    cost_ely: float; cost_tank: float; cost_fc: float
    cost_fc_stack_per_mw: float
    cost_grid_per_mw_year: float; cost_grid_fixed_per_year: float
    # flows
    ely_kwh_per_kg: float; ely_variable_gwp_per_kg: float
    tank_compression_kwh_per_kg: float
    tank_leakage_per_hour: float
    batt_rte: float; batt_leakage_per_hour: float
    fc_kg_h2_per_mwh: float
    bought_h2_gbp_per_kg: float; bought_h2_gwp_per_kg: float
    # data centre itself, constant across options
    dc_fixed_gwp_per_year: float; dc_other_gwp_per_mwh: float
    horizon_years: float
    labels: dict = field(default_factory=dict)


@dataclass
class Series:
    """The aligned half-hourly inputs for one site and window."""
    index: pd.DatetimeIndex
    dt_hours: float
    demand_mw: np.ndarray
    cf_wind: np.ndarray
    cf_solar: np.ndarray
    grid_gwp_per_mwh: np.ndarray        # kg CO2e per MWh imported
    grid_price_per_mwh: np.ndarray      # GBP per MWh, wholesale + volumetric network

    @property
    def n(self) -> int:
        return len(self.index)

    @property
    def hours(self) -> float:
        return self.n * self.dt_hours

    @property
    def annual_scale(self) -> float:
        """Scale a window total to an annual one, as sizing.evaluate() does."""
        return HOURS_PER_YEAR / self.hours


def build_model(series: Series, assets: Assets, tech: Tech, *,
                objective: str = "cost",
                gwp_limit: float | None = None,
                cost_limit: float | None = None,
                unserved_fraction: float = 0.0,
                ely_strategy: str = "free",
                islanded_baseload_uses_cf_floor: bool = True):
    """Build the LP. Returns (model, variables dict).

    ``objective`` is "cost" or "gwp". ``gwp_limit`` / ``cost_limit`` add the
    epsilon-constraint the Pareto sweep needs.
    """
    import linopy

    if assets.buy_h2 and tech.bought_h2_gbp_per_kg <= 0:
        raise ValueError(
            "This architecture may buy hydrogen but no colour was priced, so "
            "bought_h2_gbp_per_kg is 0 — the LP would buy free, zero-carbon "
            "hydrogen and every result would be nonsense. Set h2_colour on the "
            "scenario, or lock buy_h2 off.")

    n, dt = series.n, series.dt_hours
    t = pd.RangeIndex(n, name="t")
    m = linopy.Model()

    def series_da(a):
        return xr.DataArray(np.asarray(a, dtype=float), coords=[t])

    demand = series_da(series.demand_mw)
    inf = float("inf")

    def cap(flag, name, upper=inf):
        return m.add_variables(lower=0.0, upper=(upper if flag else 0.0), name=name)

    def flow(flag, name):
        return m.add_variables(lower=0.0, upper=(inf if flag else 0.0),
                               coords=[t], name=name)

    # --- capacities -----------------------------------------------------
    grid_upper = assets.grid_limit_mw if assets.grid_limit_mw is not None else inf
    V = {
        "cap_wind": cap(assets.wind, "cap_wind"),
        "cap_offshore": cap(assets.offshore_wind, "cap_offshore"),
        "cap_solar": cap(assets.solar, "cap_solar"),
        "cap_batt_p": cap(assets.battery, "cap_batt_p"),
        "cap_batt_e": cap(assets.battery, "cap_batt_e"),
        "cap_ely": cap(assets.electrolyser, "cap_ely"),
        "cap_tank": cap(assets.tank, "cap_tank"),
        "cap_fc": cap(assets.fuel_cell, "cap_fc"),
        "cap_grid": cap(assets.grid, "cap_grid", grid_upper),
    }
    # --- flows ----------------------------------------------------------
    V.update({
        "p_wind": flow(assets.wind, "p_wind"),
        "p_offshore": flow(assets.offshore_wind, "p_offshore"),
        "p_solar": flow(assets.solar, "p_solar"),
        "ch": flow(assets.battery, "ch"),
        "dis": flow(assets.battery, "dis"),
        "soc": flow(assets.battery, "soc"),
        "p_ely": flow(assets.electrolyser, "p_ely"),
        "h2_buy": flow(assets.buy_h2, "h2_buy"),
        "tank": flow(assets.tank, "tank"),
        "h2_fc": flow(assets.fuel_cell, "h2_fc"),
        "p_fc": flow(assets.fuel_cell, "p_fc"),
        "imp": flow(assets.grid, "imp"),
        "exp": flow(assets.grid and assets.allow_export, "exp"),
        "unserved": m.add_variables(lower=0.0, coords=[t], name="unserved"),
    })
    # fuel cell replacement counts — the convex max(calendar, duty) rule
    V["fc_bop_units"] = m.add_variables(lower=0.0, name="fc_bop_units")
    V["fc_stack_units"] = m.add_variables(lower=0.0, name="fc_stack_units")

    cf_w, cf_s = series_da(series.cf_wind), series_da(series.cf_solar)

    # --- (1) energy balance, one node -----------------------------------
    m.add_constraints(
        V["p_wind"] + V["p_offshore"] + V["p_solar"] + V["dis"] + V["p_fc"]
        + V["imp"] + V["unserved"]
        - V["ch"] - V["p_ely"] - V["exp"] == demand, name="balance")

    # --- (2) VRE availability; curtailment is implicit ------------------
    m.add_constraints(V["p_wind"] - cf_w * V["cap_wind"] <= 0, name="wind_cf")
    m.add_constraints(V["p_offshore"] - cf_w * V["cap_offshore"] <= 0, name="offshore_cf")
    m.add_constraints(V["p_solar"] - cf_s * V["cap_solar"] <= 0, name="solar_cf")

    # --- (3)-(5) battery ------------------------------------------------
    eta = float(np.sqrt(tech.batt_rte))
    m.add_constraints(V["ch"] - V["cap_batt_p"] <= 0, name="batt_ch_cap")
    m.add_constraints(V["dis"] - V["cap_batt_p"] <= 0, name="batt_dis_cap")
    m.add_constraints(V["soc"] - V["cap_batt_e"] <= 0, name="batt_soc_cap")
    keep_b = 1.0 - tech.batt_leakage_per_hour * dt
    m.add_constraints(
        V["soc"] - keep_b * V["soc"].roll(t=1) - dt * (eta * V["ch"] - V["dis"] / eta) == 0,
        name="batt_soc")          # roll wraps T-1 into 0 => cyclic

    # --- (6)-(8) hydrogen ------------------------------------------------
    kwh_per_kg = tech.ely_kwh_per_kg + tech.tank_compression_kwh_per_kg
    kg_per_mwh_in = 1000.0 / kwh_per_kg
    m.add_constraints(V["p_ely"] - V["cap_ely"] <= 0, name="ely_cap")
    m.add_constraints(V["p_fc"] - V["cap_fc"] <= 0, name="fc_cap")
    m.add_constraints(
        V["h2_fc"] - tech.fc_kg_h2_per_mwh * dt * V["p_fc"] == 0, name="fc_fuel")
    keep_h = 1.0 - tech.tank_leakage_per_hour * dt
    m.add_constraints(
        V["tank"] - keep_h * V["tank"].roll(t=1)
        - kg_per_mwh_in * dt * V["p_ely"] - V["h2_buy"] + V["h2_fc"] == 0, name="tank_soc")
    m.add_constraints(V["tank"] - V["cap_tank"] <= 0, name="tank_cap")

    # --- (9) grid --------------------------------------------------------
    m.add_constraints(V["imp"] - V["cap_grid"] <= 0, name="import_cap")
    if assets.grid and assets.allow_export:
        m.add_constraints(V["exp"] - V["cap_grid"] <= 0, name="export_cap")

    # --- (10) reliability ------------------------------------------------
    total_demand_mwh = float(series.demand_mw.sum() * dt)
    m.add_constraints((V["unserved"] * dt).sum() <= unserved_fraction * total_demand_mwh,
                      name="reliability")

    # --- fuel cell replacements: max(calendar, duty), exactly ------------
    fc_mwh = (V["p_fc"] * dt).sum() * series.annual_scale
    m.add_constraints(
        V["fc_bop_units"] - V["cap_fc"] / tech.fc_bop_calendar_years >= 0,
        name="fc_bop_calendar")
    m.add_constraints(
        V["fc_bop_units"] - fc_mwh / tech.fc_bop_duty_hours >= 0, name="fc_bop_duty")
    m.add_constraints(
        V["fc_stack_units"] - V["cap_fc"] / tech.horizon_years >= 0,
        name="fc_stack_calendar")
    m.add_constraints(
        V["fc_stack_units"] - fc_mwh / tech.fc_stack_duty_hours >= 0, name="fc_stack_duty")

    # --- strategies ------------------------------------------------------
    apply_strategy(m, V, series, assets, ely_strategy, islanded_baseload_uses_cf_floor)

    # --- objectives ------------------------------------------------------
    scale = series.annual_scale
    price = series_da(series.grid_price_per_mwh)
    ci = series_da(series.grid_gwp_per_mwh)

    # Constants are held out of the LP expression: linopy refuses them in an
    # objective, and they cannot change an argmin anyway. They are added back
    # for reporting, and — importantly — netted off any epsilon limit, which is
    # stated against the *total* the user sees, not the variable part.
    cost_const = tech.cost_grid_fixed_per_year
    gwp_const = (tech.dc_fixed_gwp_per_year
                 + tech.dc_other_gwp_per_mwh
                 * float(series.demand_mw.sum() * dt) * scale)

    cost = (
        tech.cost_wind * V["cap_wind"] + tech.cost_offshore * V["cap_offshore"]
        + tech.cost_solar * V["cap_solar"]
        + tech.cost_batt_p * V["cap_batt_p"] + tech.cost_batt_e * V["cap_batt_e"]
        + tech.cost_ely * V["cap_ely"] + tech.cost_tank * V["cap_tank"]
        + tech.cost_fc * V["cap_fc"]
        # Stack replacements, on the same convex max(calendar, duty) count the
        # carbon side uses. Without this, running the fuel cell hard buys extra
        # stacks in carbon and nothing in cost.
        + tech.cost_fc_stack_per_mw * V["fc_stack_units"]
        + tech.cost_grid_per_mw_year * V["cap_grid"]
        + scale * (price * V["imp"] * dt).sum()
        + scale * (tech.bought_h2_gbp_per_kg * V["h2_buy"]).sum()
        + scale * (VOLL_GBP_PER_MWH * V["unserved"] * dt).sum()
        - scale * (price * V["exp"] * dt).sum()
    )
    gwp = (
        tech.gwp_wind * V["cap_wind"] + tech.gwp_offshore * V["cap_offshore"]
        + tech.gwp_solar * V["cap_solar"]
        + tech.gwp_batt_p * V["cap_batt_p"] + tech.gwp_batt_e * V["cap_batt_e"]
        + tech.gwp_ely * V["cap_ely"] + tech.gwp_tank * V["cap_tank"]
        + tech.gwp_fc_bop_per_mw * V["fc_bop_units"]
        + tech.gwp_fc_stack_per_mw * V["fc_stack_units"]
        # The connection is a built asset like any other. Without this term a
        # carbon-only solve cannot see cap_grid at all, and — once a
        # transmission-connected site in a floored TNUoS zone pays nothing per
        # MW either — neither objective can, leaving its size to the solver's
        # stopping vertex. See grid_connection.py.
        + tech.gwp_grid_per_mw * V["cap_grid"]
        + scale * (tech.gwp_fc_maint_per_mwh * V["p_fc"] * dt).sum()
        + scale * (ci * V["imp"] * dt).sum()
        + scale * (tech.bought_h2_gwp_per_kg * V["h2_buy"]).sum()
        + scale * (tech.ely_variable_gwp_per_kg * kg_per_mwh_in * V["p_ely"] * dt).sum()
    )

    if gwp_limit is not None:
        m.add_constraints(gwp <= gwp_limit - gwp_const, name="gwp_epsilon")
    if cost_limit is not None:
        m.add_constraints(cost <= cost_limit - cost_const, name="cost_epsilon")

    if objective == "cost":
        m.add_objective(cost)
    elif objective == "gwp":
        m.add_objective(gwp)
    elif objective == "connection":
        # Smallest grid connection, for use only as a final tie-break with both
        # cost and gwp already pinned by epsilon constraints. cap_grid is priced
        # in cost and absent from gwp, so at a site where the connection charge
        # is zero — a transmission connection in a floored TNUoS zone — neither
        # objective has any preference between connections, and the reported
        # size is whichever vertex the solver stopped at. Minimising it directly
        # is the only thing that makes the number mean "the connection this
        # build actually needs".
        m.add_objective(1.0 * V["cap_grid"])
    else:
        raise ValueError(
            f"objective must be 'cost', 'gwp' or 'connection', got {objective!r}")

    return m, V, {"cost": cost, "gwp": gwp,
                  "cost_const": cost_const, "gwp_const": gwp_const}


def apply_strategy(m, V, series, assets, strategy, islanded_uses_cf_floor):
    """Force a mode of operation so its cost and carbon penalty can be measured.

    An unconstrained LP always picks the optimal dispatch itself, so a "running
    strategy" is not an algorithm to choose between — it is a constraint set
    imposed so the penalty of that mode becomes visible.
    """
    if strategy == "free" or not assets.electrolyser:
        return
    n, dt = series.n, series.dt_hours
    t = pd.RangeIndex(n, name="t")

    if strategy == "baseload":
        if assets.grid or not islanded_uses_cf_floor:
            # Per-step floor. Meaningful only with a grid to hold the
            # electrolyser up in any half-hour.
            m.add_constraints(V["p_ely"] - 0.8 * V["cap_ely"] >= 0, name="baseload_floor")
        # Annual capacity-factor floor, in both forms.
        m.add_constraints((V["p_ely"] * dt).sum() - 0.85 * V["cap_ely"] * series.hours >= 0,
                          name="baseload_cf")
    elif strategy == "flexible":
        if not assets.grid:
            # Surplus-only: the data centre gets first claim on renewable output.
            #
            # Stated over the window, not per step, and that is deliberate. The
            # per-step form `p_ely[t] <= G[t] - demand[t]` is *infeasible*
            # whenever generation falls short, because p_ely >= 0 cannot satisfy
            # a negative bound — it forces generation to exceed demand in every
            # half-hour rather than forcing the electrolyser to zero. Writing
            # `max(0, G - demand)` would need a binary. The window form is
            # linear, always feasible, and says the meaningful thing: the
            # electrolyser may consume no more than the generation left over
            # after demand has been served.
            #
            # Served demand, not gross demand — otherwise a system that builds
            # nothing has a negative allowance and the model is infeasible again.
            # Against *available* generation, not dispatched. Curtailment is
            # implicit — p_wind <= cf x cap is an inequality — so writing this
            # against p_wind makes it self-referential: the LP satisfies it by
            # curtailing, which starves the electrolyser and drives the model to
            # oversize generation absurdly instead of building storage. Measured:
            # the dispatched form built 1,152 MW of wind and no hydrogen chain at
            # all for a 7.31 MW load, against 33 MW of wind and a 60 t tank once
            # corrected.
            cf_w = xr.DataArray(np.asarray(series.cf_wind, dtype=float), coords=[t])
            cf_s = xr.DataArray(np.asarray(series.cf_solar, dtype=float), coords=[t])
            available = ((cf_w * V["cap_wind"] + cf_w * V["cap_offshore"]
                          + cf_s * V["cap_solar"]) * dt).sum()
            served = float((series.demand_mw * dt).sum()) - (V["unserved"] * dt).sum()
            m.add_constraints((V["p_ely"] * dt).sum() - available + served <= 0,
                              name="surplus_only")
    else:
        raise ValueError(f"Unknown electrolyser strategy {strategy!r}. "
                         "Use 'baseload', 'flexible' or 'free'.")


def totals(obj: dict) -> dict:
    """Cost and GWP of a solved model, constants included.

    Always use this rather than reading the objective value: the objective is
    the variable part only, so a raw objective value understates both totals by
    the fixed connection charge and the facility's own embodied burden.
    """
    return {
        "cost_GBP_per_year": float(obj["cost"].solution) + obj["cost_const"],
        "gwp_kgco2e_per_year": float(obj["gwp"].solution) + obj["gwp_const"],
        "cost_const_GBP_per_year": obj["cost_const"],
        "gwp_const_kgco2e_per_year": obj["gwp_const"],
    }


def solve(m, solver="highs", **kw):
    import logging
    logging.getLogger("linopy").setLevel(logging.ERROR)
    m.solve(solver_name=solver, output_flag=False, progress=False, **kw)
    if m.termination_condition != "optimal":
        raise RuntimeError(
            f"LP did not solve to optimality: {m.status} / {m.termination_condition}. "
            "An islanded architecture with a zero-unserved target and no store big "
            "enough to ride the year is the usual cause — the VoLL penalty should "
            "make that expensive rather than infeasible, so this is worth reading.")
    return m

def contributions(V, obj, series, tech, assets) -> dict:
    """Break a solved system's cost and carbon into where they came from.

    The LCA question the totals cannot answer: how much of this is the steel we
    put in the ground, how much is the electricity we imported, and how much is
    the building itself? Embodied against operational is the split that decides
    whether an option is actually better or has just moved its burden upstream.
    """
    dt, scale = series.dt_hours, series.annual_scale
    cap = {k: float(V[k].solution) for k in
           ("cap_wind", "cap_offshore", "cap_solar", "cap_batt_p", "cap_batt_e",
            "cap_ely", "cap_tank", "cap_fc")}
    ser = {k: V[k].solution.values for k in ("imp", "p_ely", "p_fc", "h2_buy", "unserved")}
    kg_per_mwh_in = 1000.0 / (tech.ely_kwh_per_kg + tech.tank_compression_kwh_per_kg)

    gwp = {
        "wind": tech.gwp_wind * cap["cap_wind"],
        "offshore wind": tech.gwp_offshore * cap["cap_offshore"],
        "solar": tech.gwp_solar * cap["cap_solar"],
        "battery": tech.gwp_batt_p * cap["cap_batt_p"] + tech.gwp_batt_e * cap["cap_batt_e"],
        "electrolyser": tech.gwp_ely * cap["cap_ely"],
        "H2 tank": tech.gwp_tank * cap["cap_tank"],
        "fuel cell": (tech.gwp_fc_bop_per_mw * float(V["fc_bop_units"].solution)
                      + tech.gwp_fc_stack_per_mw * float(V["fc_stack_units"].solution)),
        "grid connection": tech.gwp_grid_per_mw * float(V["cap_grid"].solution),
    }
    gwp_op = {
        "grid import": scale * float((series.grid_gwp_per_mwh * ser["imp"] * dt).sum()),
        "bought H2": scale * tech.bought_h2_gwp_per_kg * float(ser["h2_buy"].sum()),
        "electrolyser consumables": scale * tech.ely_variable_gwp_per_kg
                                    * kg_per_mwh_in * float((ser["p_ely"] * dt).sum()),
        "fuel cell maintenance": scale * tech.gwp_fc_maint_per_mwh
                                 * float((ser["p_fc"] * dt).sum()),
    }
    cost = {
        "wind": tech.cost_wind * cap["cap_wind"],
        "offshore wind": tech.cost_offshore * cap["cap_offshore"],
        "solar": tech.cost_solar * cap["cap_solar"],
        "battery": tech.cost_batt_p * cap["cap_batt_p"] + tech.cost_batt_e * cap["cap_batt_e"],
        "electrolyser": tech.cost_ely * cap["cap_ely"],
        "H2 tank": tech.cost_tank * cap["cap_tank"],
        "fuel cell": (tech.cost_fc * cap["cap_fc"]
                      + tech.cost_fc_stack_per_mw * float(V["fc_stack_units"].solution)),
        "grid connection": tech.cost_grid_per_mw_year * float(V["cap_grid"].solution),
    }
    cost_op = {
        "grid energy + network": scale * float((series.grid_price_per_mwh * ser["imp"] * dt).sum()),
        "bought H2": scale * tech.bought_h2_gbp_per_kg * float(ser["h2_buy"].sum()),
        "unserved (VoLL)": scale * VOLL_GBP_PER_MWH * float((ser["unserved"] * dt).sum()),
        "connection fixed": tech.cost_grid_fixed_per_year,
    }
    mwh = float(series.demand_mw.sum() * dt) * scale
    return {
        "gwp_embodied": gwp, "gwp_operational": gwp_op,
        "gwp_facility": {"data centre itself": tech.dc_fixed_gwp_per_year},
        "cost_capital": cost, "cost_operational": cost_op,
        "demand_MWh_per_year": mwh,
        "totals": totals(obj),
    }


# The order demand is attributed to sources in serve_stack, and the labels the
# UI shows. Renewables first is not an assumption about the solver — it is the
# only reading of a half-hour in which both renewables and imports are flowing
# that does not imply the site curtailed its own free energy to buy some.
SERVE_SOURCES = ("Solar PV", "Wind", "Offshore wind", "Battery", "Fuel cell",
                 "Grid import", "Unserved")


def serve_stack(df: pd.DataFrame) -> pd.DataFrame:
    """Attribute each period's *served demand* to a source. Long, one row per pair.

    **This is a convention, not an LP output.** The model conserves energy over
    the whole site — generation, charging, electrolysis, import and export all
    balance against demand — but it never labels an electron. When the battery
    discharges at the same half-hour the grid is importing, nothing in the
    solution says which one served the load and which one charged the tank.

    The convention here: renewables serve load first (split pro rata between
    solar, onshore and offshore by their output in that period, so no
    technology is privileged), then the battery, then the fuel cell, then the
    grid takes the residual. Unserved demand is carried as its own band, so the
    bands always sum to demand rather than to what happened to be generated.

    What this means for reading the chart: a band is what that source
    *contributed to the load*, not what it produced. Renewable output that went
    to the battery, the electrolyser, an export or a curtailment is not in the
    stack — ``dispatch_frame`` carries those columns for anyone who wants them.
    """
    served = (df.demand - df.unserved).clip(lower=0.0)
    ren = df.p_solar + df.p_wind + df.p_offshore
    to_load = pd.concat([ren, served], axis=1).min(axis=1)
    share = to_load / ren.where(ren > 0)

    rem = served - to_load
    batt = pd.concat([df.dis, rem], axis=1).min(axis=1)
    rem = rem - batt
    fc = pd.concat([df.p_fc, rem], axis=1).min(axis=1)
    rem = (rem - fc).clip(lower=0.0)          # the grid is the residual

    bands = {
        "Solar PV": (df.p_solar * share).fillna(0.0),
        "Wind": (df.p_wind * share).fillna(0.0),
        "Offshore wind": (df.p_offshore * share).fillna(0.0),
        "Battery": batt,
        "Fuel cell": fc,
        "Grid import": rem,
        "Unserved": df.unserved,
    }
    # Solver noise puts -0.0 and the odd -1e-12 in the flows; a negative band
    # would draw below the axis and read as a source consuming demand.
    out = pd.DataFrame(bands, index=df.index)[list(SERVE_SOURCES)].clip(lower=0.0)
    out.index.name = "t"
    long = out.reset_index().melt(id_vars="t", var_name="source", value_name="mw")
    # Carried as a column because a chart cannot stack on a tuple: renewables at
    # the bottom, then the stores that shift them, then the grid, and unserved
    # demand on top where its absence is the thing you are checking for.
    long["rank"] = long.source.map({s: i for i, s in enumerate(SERVE_SOURCES)})
    return long


def dispatch_frame(V, series) -> pd.DataFrame:
    """The solved dispatch as a tidy half-hourly (or hourly) frame."""
    cols = ("p_wind", "p_offshore", "p_solar", "ch", "dis", "soc", "p_ely",
            "h2_buy", "tank", "h2_fc", "p_fc", "imp", "exp", "unserved")
    df = pd.DataFrame({k: V[k].solution.values for k in cols}, index=series.index)
    df.insert(0, "demand", series.demand_mw)
    df["grid_gwp_per_mwh"] = series.grid_gwp_per_mwh
    df["price_per_mwh"] = series.grid_price_per_mwh
    df["curtailed"] = (series.cf_wind * float(V["cap_wind"].solution)
                       + series.cf_wind * float(V["cap_offshore"].solution)
                       + series.cf_solar * float(V["cap_solar"].solution)
                       - df.p_wind - df.p_offshore - df.p_solar)
    return df
