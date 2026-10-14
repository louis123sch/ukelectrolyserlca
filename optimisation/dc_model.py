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

# Value of lost load. Not a market number — a penalty large enough that a
# shortfall within the unserved allowance is used only as a last resort. It
# turns an infeasible target into an expensive one only when that allowance
# is non-zero; at the default of zero the reliability constraint is hard.
# ASSUMED.
VOLL_GBP_PER_MWH = 100_000.0
VOLL_IS_ASSUMED = True

# The same penalty in the carbon objective, charged the same way: per MWh of
# demand left unmet. Without it unserved load was carbon-free, so a min-GWP
# solve with any allowance shed the dirtiest hours as an emissions "cut" —
# 455.7 against a 236.9 kg/MWh mean on the old grid (OBJECTIVE_AUDIT.md §3.7).
# Expressed at the study's carbon price (FES 2025 CP2, 2025, the figure
# dc_pareto reports the front against) so a shed MWh weighs the same in both
# objectives: £100,000/MWh at £78.96/t is 1,266 t CO2e/MWh. A penalty, not an
# emission — like VoLL, it is there so the reliability target binds in both
# objectives, and per-MWh intensities are reported without it.
VOLL_CARBON_PRICE_GBP_PER_T = 78.96
VOLL_KGCO2E_PER_MWH = VOLL_GBP_PER_MWH / VOLL_CARBON_PRICE_GBP_PER_T * 1000.0

# Hydrogen is an indirect greenhouse gas: it lengthens methane's lifetime and
# raises tropospheric ozone and stratospheric water vapour. IPCC 2021 GWP100 as
# implemented in ecoinvent 3.9.1 carries NO factor for it (checked 14 Oct), so
# under the study's own method a leaked kilogram scores zero. Charged here as
# a stated extension of that method, at Sand et al. (2023), Commun. Earth
# Environ. 4:203, GWP100 = 11.6 ± 2.8; Warwick et al. (2022) for BEIS give
# 11 ± 5. Only bites when tank leakage is non-zero, which by default it is not.
H2_GWP100 = 11.6
H2_GWP100_SOURCE = "Sand et al. 2023, Commun. Earth Environ. 4:203"


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
    # A second bought-hydrogen contract, running alongside the first. Two
    # colours at once is a real purchasing position rather than a modelling
    # convenience: a cheap dirty one and an expensive clean one are different
    # commodities, and what mix of them is right is exactly the question the
    # cost/carbon sweep answers. With one colour this stays off and nothing
    # about the model changes.
    buy_h2_2: bool = False

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
    fc_stack_calendar_years: float; fc_stack_duty_hours: float
    # cost, GBP per MW (or MWh / kg) per year
    cost_wind: float; cost_offshore: float; cost_solar: float
    cost_batt_p: float; cost_batt_e: float
    cost_ely: float; cost_tank: float; cost_fc: float
    # Per replacement, on fc_stack_units / fc_bop_units. cost_fc is the BoP
    # annuity *net* of its calendar replacement, which cost_fc_bop_per_mw
    # then charges — see h2_capex.fuel_cell_costs. Not defaulted, so a Tech
    # that forgets one fails loudly instead of running the fuel cell for free.
    cost_fc_stack_per_mw: float; cost_fc_bop_per_mw: float
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
    # The second bought colour. It sits down here rather than beside its
    # sibling above only because a dataclass cannot put a defaulted field
    # before an undefaulted one, and the default is what keeps every existing
    # single-colour Tech literal constructing unchanged.
    bought_h2_2_gbp_per_kg: float = 0.0
    bought_h2_2_gwp_per_kg: float = 0.0
    # Generation step-up transformers: the voltage change between a generator's
    # terminals and the site collection network, which none of the generation
    # inventories in this study contains. A turbine generates at 690 V, which is
    # LOW voltage; the data centre draws at MEDIUM, so the step is compulsory —
    # 100 MW at 690 V is 83,674 A. Wind is one transformer per TURBINE (fifty on
    # a 100 MW farm), which is why it scales exactly with cap_wind. Solar is
    # still one invented plant-rated unit and is the smaller of the two.
    # Carbon only: DESNZ/Arup capex already reaches the point of connection, so
    # a cost term would double count. See transformers.py. Defaulted so a Tech
    # written before they existed still constructs.
    gwp_tx_wind_per_mw: float = 0.0
    gwp_tx_solar_per_mwp: float = 0.0
    # kg CO2e per kg of hydrogen leaked from the tank. See H2_GWP100.
    gwp_h2_leaked_per_kg: float = H2_GWP100
    # Transformer conversion losses (conversion_losses.py). No-load: MW drawn
    # at the node per MW installed, every step. Load: share of delivered power
    # at full loading, scaled by the profile's energy-weighted loading — see
    # loss_factors. The grid's load loss is already a share of imports.
    # Defaulted to zero, which is exactly the lossless model, so a Tech written
    # before they existed reproduces its old answer.
    loss_wind_noload: float = 0.0
    loss_wind_load_at_full: float = 0.0
    loss_solar_noload: float = 0.0
    loss_solar_load_at_full: float = 0.0
    loss_grid_noload: float = 0.0
    loss_grid_load: float = 0.0
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


def loss_factors(series: Series, tech: Tech) -> dict:
    """Load-loss shares of delivered power for this window: wind, solar, grid.

    A step-up's load loss is quadratic in its loading x. Linearised as
    ``loss_at_full · x_eff · p`` with ``x_eff = Σcf² / Σcf``, the energy-weighted
    loading of the availability profile, it is exact in energy terms when the
    unit carries that profile (curtailment lowers the true loading, so this
    errs slightly high). From the window's own capacity factors, so it follows
    the site and the resampling.
    """
    def x_eff(cf):
        cf = np.asarray(cf, dtype=float)
        tot = cf.sum()
        return float((cf * cf).sum() / tot) if tot > 0 else 0.0
    return {"wind": tech.loss_wind_load_at_full * x_eff(series.cf_wind),
            "solar": tech.loss_solar_load_at_full * x_eff(series.cf_solar),
            "grid": tech.loss_grid_load}


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

    # The bought-hydrogen streams, in the order the UI shows them. Each is a
    # separate contract with its own price and its own gate burden, so each
    # gets its own variable; the tank does not care which one filled it.
    bought = (("h2_buy", assets.buy_h2,
               tech.bought_h2_gbp_per_kg, tech.bought_h2_gwp_per_kg,
               "buy_h2", "h2_colour"),
              ("h2_buy_2", assets.buy_h2_2,
               tech.bought_h2_2_gbp_per_kg, tech.bought_h2_2_gwp_per_kg,
               "buy_h2_2", "h2_colour_2"))
    for var, on, gbp, _gwp, flag, colour_key in bought:
        if on and gbp <= 0:
            raise ValueError(
                f"This architecture may buy hydrogen on the {var!r} stream but "
                f"no colour was priced, so its £/kg is 0 — the LP would buy "
                f"free, zero-carbon hydrogen and every result would be "
                f"nonsense. Set {colour_key} on the scenario, or lock {flag} "
                f"off.")
    if assets.grid and assets.allow_export:
        # Nothing in the study switches export on, and it is not fit to be:
        # exported MWh are credited at the *demand* price (wholesale plus
        # volumetric network charges), carry no carbon credit, and are missing
        # from contributions(). Refused rather than silently wrong. OBJECTIVE_
        # AUDIT.md §3.5.
        raise NotImplementedError(
            "Export is not modelled correctly yet — it would be credited at "
            "demand rates with no carbon credit. Leave allow_export off.")

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
        "h2_buy_2": flow(assets.buy_h2_2, "h2_buy_2"),
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
    lf = loss_factors(series, tech)

    # --- (1) energy balance, one node -----------------------------------
    # Imports arrive through the site's intake transformer, which keeps a
    # share of them; every installed transformer draws its no-load loss at the
    # node, whether or not anything flows. conversion_losses.py.
    m.add_constraints(
        V["p_wind"] + V["p_offshore"] + V["p_solar"] + V["dis"] + V["p_fc"]
        + (1.0 - lf["grid"]) * V["imp"] + V["unserved"]
        - V["ch"] - V["p_ely"] - V["exp"]
        - tech.loss_wind_noload * (V["cap_wind"] + V["cap_offshore"])
        - tech.loss_solar_noload * V["cap_solar"]
        - tech.loss_grid_noload * V["cap_grid"] == demand, name="balance")

    # --- (2) VRE availability; curtailment is implicit ------------------
    # p_* is power delivered to the node, after the generator's step-up.
    m.add_constraints(V["p_wind"] - (1.0 - lf["wind"]) * cf_w * V["cap_wind"] <= 0,
                      name="wind_cf")
    m.add_constraints(V["p_offshore"] - (1.0 - lf["wind"]) * cf_w * V["cap_offshore"] <= 0,
                      name="offshore_cf")
    m.add_constraints(V["p_solar"] - (1.0 - lf["solar"]) * cf_s * V["cap_solar"] <= 0,
                      name="solar_cf")

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
        - kg_per_mwh_in * dt * V["p_ely"] - V["h2_buy"] - V["h2_buy_2"]
        + V["h2_fc"] == 0, name="tank_soc")
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
        V["fc_stack_units"] - V["cap_fc"] / tech.fc_stack_calendar_years >= 0,
        name="fc_stack_calendar")
    m.add_constraints(
        V["fc_stack_units"] - fc_mwh / tech.fc_stack_duty_hours >= 0, name="fc_stack_duty")

    # --- strategies ------------------------------------------------------
    apply_strategy(m, V, series, assets, ely_strategy, islanded_baseload_uses_cf_floor,
                   tech=tech)

    # --- objectives ------------------------------------------------------
    # One definition, shared with contributions() and myopic.evaluate, so a
    # term added here cannot be missing from the breakdown or the bracket.
    terms = objective_terms(V, series, tech,
                            price=series_da(series.grid_price_per_mwh),
                            ci=series_da(series.grid_gwp_per_mwh))
    cost = _total(terms["cost_capital"], terms["cost_operational"])
    gwp = _total(terms["gwp_embodied"], terms["gwp_operational"])
    cost_const, gwp_const = objective_constants(series, tech, grid=assets.grid)

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


def objective_terms(q, series: Series, tech: Tech, *, price, ci) -> dict:
    """Every term of both objectives, labelled, from one set of quantities.

    ``q`` maps the LP's variable names to quantities: linopy variables when the
    model is built, plain floats and arrays when a solution or a myopic dispatch
    is scored. ``price`` and ``ci`` are the half-hourly import price and carbon
    in whichever of those two forms ``q`` is in. Every term is linear in ``q``,
    so the same arithmetic serves both.

    This is the only place an objective term is written. ``build_model`` sums
    it, ``contributions`` reports it line by line, and ``myopic.evaluate``
    scores a merit-order dispatch with it — before it existed those were three
    hand-written copies, and the myopic one had drifted (no grid connection
    carbon, no bought hydrogen).
    """
    dt, scale = series.dt_hours, series.annual_scale
    kg_per_mwh_in = 1000.0 / (tech.ely_kwh_per_kg + tech.tank_compression_kwh_per_kg)

    # Two bought colours are two line items, not one: the whole reason for
    # buying both is that they differ in price and in burden, and a single
    # merged row would hide exactly the trade being made. Named by colour where
    # build_tech recorded one, so the reader knows which is which.
    def bought_row(key: str, fallback: str) -> str:
        colour = (tech.labels or {}).get(key)
        return f"bought H2 ({colour})" if colour else fallback

    buy_1, buy_2 = (bought_row("h2_colour", "bought H2"),
                    bought_row("h2_colour_2", "bought H2, second colour"))
    if buy_1 == buy_2:                       # the same colour on both streams
        buy_2 += ", second stream"

    gwp_embodied = {
        "wind": tech.gwp_wind * q["cap_wind"],
        "offshore wind": tech.gwp_offshore * q["cap_offshore"],
        "solar": tech.gwp_solar * q["cap_solar"],
        "battery": tech.gwp_batt_p * q["cap_batt_p"] + tech.gwp_batt_e * q["cap_batt_e"],
        "electrolyser": tech.gwp_ely * q["cap_ely"],
        "H2 tank": tech.gwp_tank * q["cap_tank"],
        "fuel cell": (tech.gwp_fc_bop_per_mw * q["fc_bop_units"]
                      + tech.gwp_fc_stack_per_mw * q["fc_stack_units"]),
        # The connection is a built asset like any other. Without this term a
        # carbon-only solve cannot see cap_grid at all, and — once a
        # transmission-connected site in a floored TNUoS zone pays nothing per
        # MW either — neither objective can, leaving its size to the solver's
        # stopping vertex. See grid_connection.py.
        "grid connection": tech.gwp_grid_per_mw * q["cap_grid"],
        # Step-up transformers, on capacity rather than output: a transformer is
        # sized to the peak MVA it must pass and does not care how many hours a
        # year that happens. Solar is charged per MWp against an AC-rated asset,
        # which is why its coefficient already carries the DC:AC ratio. Its own
        # line rather than folded into wind and solar: it is a different asset,
        # on a different life.
        "generation step-up transformers": (
            tech.gwp_tx_wind_per_mw * (q["cap_wind"] + q["cap_offshore"])
            + tech.gwp_tx_solar_per_mwp * q["cap_solar"]),
    }
    gwp_operational = {
        "grid import": scale * (ci * q["imp"] * dt).sum(),
        buy_1: scale * (tech.bought_h2_gwp_per_kg * q["h2_buy"]).sum(),
        buy_2: scale * (tech.bought_h2_2_gwp_per_kg * q["h2_buy_2"]).sum(),
        "electrolyser consumables": scale * (tech.ely_variable_gwp_per_kg
                                             * kg_per_mwh_in * q["p_ely"] * dt).sum(),
        "fuel cell maintenance": scale * (tech.gwp_fc_maint_per_mwh * q["p_fc"] * dt).sum(),
        "unserved (VoLL)": scale * (VOLL_KGCO2E_PER_MWH * q["unserved"] * dt).sum(),
        # The tank loses leakage x dt of the previous step's stock each step.
        # Storage is cyclic, so summed over the window the previous steps'
        # stocks are exactly this window's stocks and no roll is needed.
        "H2 leaked from tank": scale * (tech.tank_leakage_per_hour * dt
                                        * tech.gwp_h2_leaked_per_kg * q["tank"]).sum(),
    }
    cost_capital = {
        "wind": tech.cost_wind * q["cap_wind"],
        "offshore wind": tech.cost_offshore * q["cap_offshore"],
        "solar": tech.cost_solar * q["cap_solar"],
        "battery": tech.cost_batt_p * q["cap_batt_p"] + tech.cost_batt_e * q["cap_batt_e"],
        "electrolyser": tech.cost_ely * q["cap_ely"],
        "H2 tank": tech.cost_tank * q["cap_tank"],
        # Stack and BoP replacements, on the same convex max(calendar, duty)
        # counts the carbon side uses. Without them, running the fuel cell hard
        # buys extra kit in carbon and nothing in cost.
        "fuel cell": (tech.cost_fc * q["cap_fc"]
                      + tech.cost_fc_stack_per_mw * q["fc_stack_units"]
                      + tech.cost_fc_bop_per_mw * q["fc_bop_units"]),
        "grid connection": tech.cost_grid_per_mw_year * q["cap_grid"],
    }
    cost_operational = {
        "grid energy + network": scale * (price * q["imp"] * dt).sum(),
        buy_1: scale * (tech.bought_h2_gbp_per_kg * q["h2_buy"]).sum(),
        buy_2: scale * (tech.bought_h2_2_gbp_per_kg * q["h2_buy_2"]).sum(),
        "unserved (VoLL)": scale * (VOLL_GBP_PER_MWH * q["unserved"] * dt).sum(),
        "export credit": -scale * (price * q["exp"] * dt).sum(),
    }
    return {"gwp_embodied": gwp_embodied, "gwp_operational": gwp_operational,
            "cost_capital": cost_capital, "cost_operational": cost_operational}


def objective_constants(series: Series, tech: Tech, *, grid: bool) -> tuple[float, float]:
    """The parts of each objective no decision variable moves: (cost, gwp).

    Held out of the LP expression: linopy refuses constants in an objective,
    and they cannot change an argmin anyway. They are added back for reporting,
    and — importantly — netted off any epsilon limit, which is stated against
    the *total* the user sees, not the variable part.

    The fixed connection charge belongs to the connection. An islanded build
    has none, so charging it put £271k/yr (London) to £4.67m/yr on every
    architecture that never touches the grid.
    """
    cost_const = tech.cost_grid_fixed_per_year if grid else 0.0
    gwp_const = (tech.dc_fixed_gwp_per_year
                 + tech.dc_other_gwp_per_mwh
                 * float(series.demand_mw.sum() * series.dt_hours) * series.annual_scale)
    return cost_const, gwp_const


def _total(*groups):
    """Sum labelled terms. ``sum()`` would start from int 0, which a linopy
    expression accepts but a reader should not have to wonder about."""
    from functools import reduce
    import operator
    return reduce(operator.add, [v for g in groups for v in g.values()])


def apply_strategy(m, V, series, assets, strategy, islanded_uses_cf_floor, tech=None):
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
            # Delivered to the node, after the step-ups, as the availability
            # constraints state it.
            lf = loss_factors(series, tech) if tech is not None else \
                {"wind": 0.0, "solar": 0.0}
            available = (((1.0 - lf["wind"]) * cf_w * (V["cap_wind"] + V["cap_offshore"])
                          + (1.0 - lf["solar"]) * cf_s * V["cap_solar"]) * dt).sum()
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


def intensities(cost: float, gwp: float, unserved_mwh: float,
                demand_mwh: float) -> dict:
    """£/MWh and g/kWh of a build, on the demand it actually *served*.

    Both VoLL penalties come off first: they are there to make a reliability
    target bind, not to be read as money spent or carbon emitted. Dividing by
    gross demand, as every intensity did until 14 Oct, credited a build for
    load it never carried.
    """
    served = demand_mwh - unserved_mwh
    cost_x = cost - VOLL_GBP_PER_MWH * unserved_mwh
    gwp_x = gwp - VOLL_KGCO2E_PER_MWH * unserved_mwh
    return {"served_MWh_per_year": served,
            "cost_excl_VoLL_GBP_per_year": cost_x,
            "gwp_excl_VoLL_kgco2e_per_year": gwp_x,
            "cost_GBP_per_MWh": cost_x / served if served > 0 else float("nan"),
            "gwp_g_per_kWh": gwp_x / served if served > 0 else float("nan")}


def solve(m, solver="highs", **kw):
    import logging
    logging.getLogger("linopy").setLevel(logging.ERROR)
    m.solve(solver_name=solver, output_flag=False, progress=False, **kw)
    if m.termination_condition != "optimal":
        raise RuntimeError(
            f"LP did not solve to optimality: {m.status} / {m.termination_condition}. "
            "An islanded architecture with a zero-unserved target and no store big "
            "enough to ride the year is the usual cause. The VoLL penalties turn "
            "a shortfall into an expensive answer only when an unserved "
            "allowance is given (unserved_fraction > 0); at the default of zero "
            "the reliability constraint is hard and this is the result.")
    return m

def contributions(V, obj, series, tech, assets) -> dict:
    """Break a solved system's cost and carbon into where they came from.

    The LCA question the totals cannot answer: how much of this is the steel we
    put in the ground, how much is the electricity we imported, and how much is
    the building itself? Embodied against operational is the split that decides
    whether an option is actually better or has just moved its burden upstream.
    """
    dt, scale = series.dt_hours, series.annual_scale
    terms = score(solution_quantities(V), series, tech)
    terms["cost_operational"]["connection fixed"] = obj["cost_const"]
    mwh = float(series.demand_mw.sum() * dt) * scale
    return {
        "gwp_embodied": terms["gwp_embodied"],
        "gwp_operational": terms["gwp_operational"],
        "gwp_facility": {"data centre, IT capacity": tech.dc_fixed_gwp_per_year,
                         "data centre, cooling consumables":
                             tech.dc_other_gwp_per_mwh * mwh},
        "cost_capital": terms["cost_capital"],
        "cost_operational": terms["cost_operational"],
        "demand_MWh_per_year": mwh,
        "totals": totals(obj),
    }


def solution_quantities(V) -> dict:
    """A solved model's variables as plain numbers: floats for the scalars,
    arrays for the per-step flows — the form ``score`` takes."""
    out = {}
    for k, var in V.items():
        sol = var.solution
        out[k] = float(sol) if sol.ndim == 0 else np.asarray(sol.values, dtype=float)
    return out


def score(q: dict, series: Series, tech: Tech) -> dict:
    """``objective_terms`` evaluated on numbers, every term a float."""
    terms = objective_terms(q, series, tech,
                            price=np.asarray(series.grid_price_per_mwh, dtype=float),
                            ci=np.asarray(series.grid_gwp_per_mwh, dtype=float))
    return {g: {k: float(v) for k, v in d.items()} for g, d in terms.items()}


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


def dispatch_frame(V, series, tech=None) -> pd.DataFrame:
    """The solved dispatch as a tidy half-hourly (or hourly) frame.

    Pass ``tech`` to have ``curtailed`` net of the step-up losses; without it
    the transformer losses count as curtailment.
    """
    cols = ("p_wind", "p_offshore", "p_solar", "ch", "dis", "soc", "p_ely",
            "h2_buy", "h2_buy_2", "tank", "h2_fc", "p_fc", "imp", "exp",
            "unserved")
    df = pd.DataFrame({k: V[k].solution.values for k in cols}, index=series.index)
    df.insert(0, "demand", series.demand_mw)
    df["grid_gwp_per_mwh"] = series.grid_gwp_per_mwh
    df["price_per_mwh"] = series.grid_price_per_mwh
    lf = loss_factors(series, tech) if tech is not None else {"wind": 0.0, "solar": 0.0}
    df["curtailed"] = ((1.0 - lf["wind"]) * series.cf_wind
                       * (float(V["cap_wind"].solution) + float(V["cap_offshore"].solution))
                       + (1.0 - lf["solar"]) * series.cf_solar * float(V["cap_solar"].solution)
                       - df.p_wind - df.p_offshore - df.p_solar)
    return df
