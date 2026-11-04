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
    # The smallest connection in the band the charges were read for
    # (network_charges.band_floor_mw). Ignored when grid is off.
    grid_floor_mw: float = 0.0
    allow_export: bool = False


@dataclass(frozen=True)
class ConnectionOption:
    """One price list the grid connection may be on (COST_PLAN §1.11, 30 Oct
    2026): a tier, a voltage and a charging band at one substation, with the
    size range the rules allow it and the charges it carries. ``build_model``
    gives each option an on/off switch, exactly one on, and a connection of
    its own inside its range; their sum is ``cap_grid``. ``group`` names the
    import series the option shares (``Series.grid_groups``): one per voltage,
    because losses, unit rates and delivered carbon differ by voltage and the
    bands at one voltage differ only in fixed charge and size range.
    Assembled by ``dc_inputs.build_tech`` from ``connection_options``."""
    key: str
    group: str
    floor_mw: float
    ceiling_mw: float
    # £/MW/year on this option's connection: DUoS capacity and the connection
    # capital per MW. The zonal HH TNUoS tariff is the same for every option
    # and stays on triad_mw (Tech.cost_grid_triad_per_mw_year).
    cost_per_mw_year: float
    # £/year while this option is on: TDR, DUoS fixed, the cable and switchgear.
    cost_fixed_per_year: float
    # Embodied carbon per MW of this option's connection; None takes the Tech's
    # gwp_grid_per_mw (with its cut-off estimates), the same unit for every voltage.
    gwp_per_mw_year: float | None = None
    # The cable to this option's substation, kg CO2e per year while the option
    # is on (its own route, two circuits, over the asset's life). The cost side
    # has charged the cable since 29 Oct 2026; the carbon side only since 30 Oct.
    gwp_fixed_per_year: float = 0.0
    info: dict = field(default_factory=dict)


def connection_options_of(tech) -> tuple | None:
    """The options a Tech carries, or None for the single-price-list model.
    (A Tech whose fields are symbols, as the LCA map builds, has none.)"""
    opts = getattr(tech, "connection_options", None)
    if isinstance(opts, (list, tuple)) and len(opts):
        return tuple(opts)
    return None


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
    # IEA PVPS T12-33:2026's 2.5 MVA inverter-station units, four per 10 MWp,
    # and is the larger of the two per MW.
    # Carbon only: DESNZ/Arup capex already reaches the point of connection, so
    # a cost term would double count. See transformers.py. Defaulted so a Tech
    # written before they existed still constructs.
    gwp_tx_wind_per_mw: float = 0.0
    gwp_tx_solar_per_mwp: float = 0.0
    # kg CO2e per kg of hydrogen leaked from the tank. See H2_GWP100.
    gwp_h2_leaked_per_kg: float = H2_GWP100
    # Electrolyser stacks, charged by replacement like the fuel cell's (user, 26 Oct
    # 2026; electrolysers.py). gwp_ely is then the balance of plant alone, per MW per
    # year; gwp_ely_stack_per_mw is one stack per MW, charged on ely_stack_units =
    # max(cap_ely / calendar years, running MWh / duty hours). Defaulted to zero so a
    # Tech written before the split, whose gwp_ely is the whole unit, is unchanged.
    gwp_ely_stack_per_mw: float = 0.0
    # Their cost: NESO's variable opex (stack replacement and water) per kg made,
    # so running the electrolyser hard costs something in cost as in carbon.
    # Defaulted to zero, which is the model before 28 Oct 2026.
    cost_ely_variable_per_kg: float = 0.0
    # Share of cap_tank the fuel cell can draw: a fuel-cell feed needs a minimum
    # pressure, so the last of the gas stays in the vessel. Both objectives pay for
    # cap_tank, so both pay for it. 1.0 is the model before 4 Nov 2026.
    tank_usable_fraction: float = 1.0
    # The HH locational TNUoS tariff, GBP per MW of Triad demand per year. It is
    # charged on triad_mw, the most the site imports in any Triad-candidate step,
    # not on cap_grid, so a battery covering the winter evening peak saves it.
    # cost_grid_per_mw_year then carries only the charges that really follow the
    # connection (DUoS capacity, connection capital). Zero is the model before
    # 28 Oct 2026, when the tariff sat inside cost_grid_per_mw_year.
    cost_grid_triad_per_mw_year: float = 0.0
    ely_stack_calendar_years: float = 25.0 / 3.0
    ely_stack_duty_hours: float = 50_000.0
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
    # The containerised LV → 20 kV step-ups of the battery (per MW of PCS,
    # cap_batt_p) and the fuel cell (per MW of cap_fc): Jasper 2026's unit on
    # the IEA PVPS composition, amortised over the asset's own life (15 y
    # battery; the fuel cell's BoP calendar life). Carbon only, like the
    # generation step-ups. Defaulted so a Tech written before them constructs.
    gwp_tx_batt_per_mw: float = 0.0
    gwp_tx_fc_per_mw: float = 0.0
    # Their losses (conversion_losses.container_stepup): no-load on installed
    # MW every step — the fuel cell's unit is kept energised on standby — and
    # load loss as a share of the power through them, already at the ASSUMED
    # energy-weighted loading. The battery's applies both ways.
    loss_batt_noload: float = 0.0
    loss_batt_load: float = 0.0
    loss_fc_noload: float = 0.0
    loss_fc_load: float = 0.0
    # The cable from the network to the site, kg CO2e per year: the line's
    # per-km score over the real route, two circuits, over the asset's life
    # (grid_connection.py). A constant with one price list — it is charged
    # whenever the grid is on — and a term on the switches with options
    # (ConnectionOption.gwp_fixed_per_year). Zero is the model before 30 Oct
    # 2026, when the cable was priced in money and free in carbon.
    gwp_grid_fixed_per_year: float = 0.0
    # The price lists the connection may be on (ConnectionOption), or None:
    # with None, or with the grid off, the model is the single-price-list one
    # exactly — cap_grid priced by cost_grid_per_mw_year and
    # cost_grid_fixed_per_year, imports by the one series. COST_PLAN §1.11.
    connection_options: tuple | None = None
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
    # Steps that could hold a Triad (network_charges.triad_window). None means
    # every step, so the winter-peak charge falls on peak import.
    triad_window: np.ndarray | None = None
    # One import series per voltage group when the model chooses its price
    # list (COST_PLAN §1.11): {group: {"price_per_mwh": array, "gwp_per_mwh":
    # array}}. grid_price_per_mwh / grid_gwp_per_mwh above are then the
    # reference group's (the price list the pre-solve rule would have picked).
    grid_groups: dict | None = None

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
    """Load-loss shares of delivered power for this window: wind, solar, grid,
    battery and fuel cell.

    A step-up's load loss is quadratic in its loading x. Linearised as
    ``loss_at_full · x_eff · p`` with ``x_eff = Σcf² / Σcf``, the energy-weighted
    loading of the availability profile, it is exact in energy terms when the
    unit carries that profile (curtailment lowers the true loading, so this
    errs slightly high). From the window's own capacity factors, so it follows
    the site and the resampling. The grid intake, the battery and the fuel
    cell have no profile — their loading is a solve outcome — so theirs arrive
    already at an ASSUMED loading (conversion_losses.py).
    """
    def x_eff(cf):
        cf = np.asarray(cf, dtype=float)
        tot = cf.sum()
        return float((cf * cf).sum() / tot) if tot > 0 else 0.0
    return {"wind": tech.loss_wind_load_at_full * x_eff(series.cf_wind),
            "solar": tech.loss_solar_load_at_full * x_eff(series.cf_solar),
            "grid": tech.loss_grid_load,
            "battery": tech.loss_batt_load,
            "fc": tech.loss_fc_load}


def build_model(series: Series, assets: Assets, tech: Tech, *,
                objective: str = "cost",
                gwp_limit: float | None = None,
                cost_limit: float | None = None,
                relax_switches: bool = False,
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

    def cap(flag, name, upper=inf, lower=0.0):
        return m.add_variables(lower=(lower if flag else 0.0),
                               upper=(upper if flag else 0.0), name=name)

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
        "cap_grid": cap(assets.grid, "cap_grid", grid_upper,
                        min(assets.grid_floor_mw, grid_upper)),
        # Demand in the Triad window: >= import in every candidate step (below).
        "triad_mw": cap(assets.grid, "triad_mw"),
        # 1 while the grid is on: carries the connection's fixed carbon (the
        # cable) as a term, since linopy refuses a constant in an objective.
        "grid_on": m.add_variables(lower=1.0 if assets.grid else 0.0, upper=1.0 if assets.grid else 0.0,
                                   name="grid_on"),
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
    # electrolyser stack replacements, the same rule
    V["ely_stack_units"] = m.add_variables(lower=0.0, name="ely_stack_units")

    cf_w, cf_s = series_da(series.cf_wind), series_da(series.cf_solar)
    lf = loss_factors(series, tech)

    # --- (1) energy balance, one node -----------------------------------
    # Imports arrive through the site's intake transformer, which keeps a
    # share of them; the battery's discharge and the fuel cell's output arrive
    # through their own container step-ups, and the battery's charge is drawn
    # through the same unit, grossed up; every installed transformer draws its
    # no-load loss at the node, whether or not anything flows (the fuel cell's
    # stays energised on standby). conversion_losses.py.
    m.add_constraints(
        V["p_wind"] + V["p_offshore"] + V["p_solar"]
        + (1.0 - lf["battery"]) * V["dis"] + (1.0 - lf["fc"]) * V["p_fc"]
        + (1.0 - lf["grid"]) * V["imp"] + V["unserved"]
        - V["ch"] / (1.0 - lf["battery"]) - V["p_ely"] - V["exp"]
        - tech.loss_wind_noload * (V["cap_wind"] + V["cap_offshore"])
        - tech.loss_solar_noload * V["cap_solar"]
        - tech.loss_grid_noload * V["cap_grid"]
        - tech.loss_batt_noload * V["cap_batt_p"]
        - tech.loss_fc_noload * V["cap_fc"] == demand, name="balance")

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
    m.add_constraints(V["tank"] - tech.tank_usable_fraction * V["cap_tank"] <= 0, name="tank_cap")

    # --- (9) grid --------------------------------------------------------
    m.add_constraints(V["imp"] - V["cap_grid"] <= 0, name="import_cap")
    window = (np.ones(n, dtype=bool) if series.triad_window is None
              else np.asarray(series.triad_window, dtype=bool))
    if window.any():
        m.add_constraints(V["imp"].isel(t=np.flatnonzero(window)) - V["triad_mw"] <= 0,
                          name="triad_demand")
    if assets.grid and assets.allow_export:
        m.add_constraints(V["exp"] - V["cap_grid"] <= 0, name="export_cap")

    # --- (9b) the price list, chosen with the connection (COST_PLAN §1.11) --
    # One switch per option, exactly one on; a connection per option held
    # inside its size range while on and at zero while off; cap_grid is their
    # sum. Imports are split by voltage group, each group's import limited by
    # the connections built in it, so each MWh pays that voltage's losses,
    # unit rates and delivered carbon. The switches are the only integers in
    # the model; with no options nothing here exists.
    opts = connection_options_of(tech) if assets.grid else None
    group_da = None
    if opts is not None:
        from functools import reduce
        import operator
        if not series.grid_groups:
            raise ValueError("the Tech carries connection options but the Series has no grid_groups: "
                             "build both with dc_inputs.build_series / build_tech in the same mode")
        missing = sorted({o.group for o in opts} - set(series.grid_groups))
        if missing:
            raise ValueError(f"connection options use voltage groups the Series lacks: {missing}")
        for i, o in enumerate(opts):
            if not (np.isfinite(o.ceiling_mw) and o.ceiling_mw >= o.floor_mw >= 0.0):
                raise ValueError(f"connection option {o.key!r} needs 0 <= floor <= a finite ceiling, "
                                 f"got {o.floor_mw}..{o.ceiling_mw}")
            # relax_switches (4 Nov 2026, the cheap run's pruning pass): the
            # on/off switch may take any value between 0 and 1, so the problem
            # is a linear programme again. Meaningless as a design — a site
            # "40 % on one list" — but a list with no share here is one the
            # whole-number solve would almost never pick; dc_pareto.prune_options.
            V[f"on_{i}"] = (m.add_variables(lower=0.0, upper=1.0, name=f"on_{i}") if relax_switches
                            else m.add_variables(binary=True, name=f"on_{i}"))
            V[f"cap_conn_{i}"] = m.add_variables(lower=0.0, name=f"cap_conn_{i}")
            m.add_constraints(V[f"cap_conn_{i}"] - o.floor_mw * V[f"on_{i}"] >= 0, name=f"option_floor_{i}")
            m.add_constraints(V[f"cap_conn_{i}"] - o.ceiling_mw * V[f"on_{i}"] <= 0, name=f"option_ceiling_{i}")
        m.add_constraints(reduce(operator.add, [V[f"on_{i}"] for i in range(len(opts))]) == 1,
                          name="one_price_list")
        m.add_constraints(V["cap_grid"] - reduce(operator.add, [V[f"cap_conn_{i}"] for i in range(len(opts))]) == 0,
                          name="cap_grid_is_the_chosen_connection")
        group_da = {}
        for g in sorted({o.group for o in opts}):
            gv = group_import_var(g)
            V[gv] = flow(True, gv)
            members = [V[f"cap_conn_{i}"] for i, o in enumerate(opts) if o.group == g]
            m.add_constraints(V[gv] - reduce(operator.add, members) <= 0, name=f"import_cap_{gv}")
            group_da[g] = (series_da(series.grid_groups[g]["price_per_mwh"]),
                           series_da(series.grid_groups[g]["gwp_per_mwh"]))
        m.add_constraints(V["imp"] - reduce(operator.add, [V[group_import_var(g)] for g in group_da]) == 0,
                          name="imports_by_voltage_group")

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

    # --- electrolyser stack replacements: max(calendar, duty), exactly ----
    ely_mwh = (V["p_ely"] * dt).sum() * series.annual_scale
    m.add_constraints(
        V["ely_stack_units"] - V["cap_ely"] / tech.ely_stack_calendar_years >= 0,
        name="ely_stack_calendar")
    m.add_constraints(
        V["ely_stack_units"] - ely_mwh / tech.ely_stack_duty_hours >= 0, name="ely_stack_duty")

    # --- strategies ------------------------------------------------------
    apply_strategy(m, V, series, assets, ely_strategy, islanded_baseload_uses_cf_floor,
                   tech=tech)

    # --- objectives ------------------------------------------------------
    # One definition, shared with contributions() and myopic.evaluate, so a
    # term added here cannot be missing from the breakdown or the bracket.
    terms = objective_terms(V, series, tech,
                            price=series_da(series.grid_price_per_mwh),
                            ci=series_da(series.grid_gwp_per_mwh),
                            group_series=group_da)
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
        # cost and gwp already pinned by epsilon constraints. cap_grid carries
        # only a small embodied term in gwp (grid_connection.py, 138 kg/MW/yr)
        # and, at a site where the connection charge is zero — a transmission
        # connection in a floored TNUoS zone — nothing in cost, so neither
        # objective has much preference between connections, and the reported
        # size is whichever vertex the solver stopped at. Minimising it directly
        # is the only thing that makes the number mean "the connection this
        # build actually needs".
        m.add_objective(1.0 * V["cap_grid"])
    else:
        raise ValueError(
            f"objective must be 'cost', 'gwp' or 'connection', got {objective!r}")

    return m, V, {"cost": cost, "gwp": gwp,
                  "cost_const": cost_const, "gwp_const": gwp_const,
                  "options": opts}


def option_quantities(q: dict, tech: Tech, series: Series, option: int | None = None) -> dict:
    """``q`` (a dispatch's numbers: ``cap_grid``, ``imp``) with the price-list
    quantities the option terms read: one switch on, that option's connection
    equal to ``cap_grid``, and every import through its voltage group.

    ``option`` is the index to switch on; None takes the cheapest option whose
    size range holds ``cap_grid``, at that connection — what a merit-order
    operator would contract for the connection it has. Returns ``q`` unchanged
    when the Tech has no options.
    """
    opts = connection_options_of(tech)
    if opts is None:
        return q
    cap = float(q.get("cap_grid", 0.0))
    if option is None:
        fits = [(o.cost_fixed_per_year + o.cost_per_mw_year * cap, i) for i, o in enumerate(opts)
                if o.floor_mw - 1e-6 <= cap <= o.ceiling_mw + 1e-6]
        if not fits:         # nothing holds this connection: the nearest range by distance
            fits = [(min(abs(cap - o.floor_mw), abs(cap - o.ceiling_mw)), i) for i, o in enumerate(opts)]
        option = min(fits)[1]
    out = dict(q)
    imp = np.asarray(q.get("imp", np.zeros(series.n)), dtype=float)
    for i, o in enumerate(opts):
        out[f"on_{i}"] = 1.0 if i == option else 0.0
        out[f"cap_conn_{i}"] = cap if i == option else 0.0
    for g in {o.group for o in opts}:
        out[group_import_var(g)] = imp if g == opts[option].group else np.zeros_like(imp)
    return out


def group_import_var(group: str) -> str:
    """The LP variable carrying one voltage group's imports (``imp_33kV``)."""
    import re
    return "imp_" + re.sub(r"\W", "", group)


def chosen_option(q, options) -> tuple[int, "ConnectionOption"] | None:
    """Which option a solution switched on: ``(index, option)``, or None.
    ``q`` is the variables (solved) or ``solution_quantities``' numbers."""
    if not options:
        return None
    best, best_v = None, -1.0
    for i, o in enumerate(options):
        v = q.get(f"on_{i}") if isinstance(q, dict) else None
        if v is None:
            return None
        v = float(v.solution) if hasattr(v, "solution") else float(v)
        if v > best_v:
            best, best_v = i, v
    return (best, options[best]) if best is not None and best_v > 0.5 else None


def objective_terms(q, series: Series, tech: Tech, *, price, ci, group_series=None) -> dict:
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

    With connection options on the Tech (COST_PLAN §1.11) the grid's four
    terms are written over the options and the voltage groups instead:
    capital per MW on each option's own connection, the fixed charges on its
    switch, and energy and carbon per group on that group's import series
    (``group_series``: {group: (price, ci)}, in whichever form ``q`` is in;
    taken from ``series.grid_groups`` when not given).
    """
    dt, scale = series.dt_hours, series.annual_scale
    # The options are in play only when the quantities carry their switches:
    # an islanded build (grid off) has none, and a merit-order dispatch adds
    # them with option_quantities.
    opts = connection_options_of(tech)
    if opts is not None and not (isinstance(q, dict) and dict.__contains__(q, "on_0")):
        opts = None
    if opts is not None and group_series is None:
        group_series = {g: (np.asarray(d["price_per_mwh"], dtype=float), np.asarray(d["gwp_per_mwh"], dtype=float))
                        for g, d in (series.grid_groups or {}).items()}
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
        "battery cells and container": tech.gwp_batt_e * q["cap_batt_e"],
        "battery power conversion": tech.gwp_batt_p * q["cap_batt_p"],
        "electrolyser": tech.gwp_ely * q["cap_ely"],
        "electrolyser stack replacements": tech.gwp_ely_stack_per_mw * q.get("ely_stack_units", 0.0),
        "H2 tank": tech.gwp_tank * q["cap_tank"],
        "fuel cell stack replacements": tech.gwp_fc_stack_per_mw * q["fc_stack_units"],
        "fuel cell BoP replacements": tech.gwp_fc_bop_per_mw * q["fc_bop_units"],
        # The connection is a built asset like any other. Without this term a
        # carbon-only solve cannot see cap_grid at all, and — once a
        # transmission-connected site in a floored TNUoS zone pays nothing per
        # MW either — neither objective can, leaving its size to the solver's
        # stopping vertex. See grid_connection.py.
        "grid connection": (tech.gwp_grid_per_mw * q["cap_grid"] if opts is None else
                            _sum((tech.gwp_grid_per_mw if o.gwp_per_mw_year is None else o.gwp_per_mw_year)
                                 * q[f"cap_conn_{i}"] for i, o in enumerate(opts))),
        # Step-up transformers, on capacity rather than output: a transformer is
        # sized to the peak MVA it must pass and does not care how many hours a
        # year that happens. Solar is charged per MWp against an AC-rated asset,
        # which is why its coefficient already carries the DC:AC ratio. Their
        # own lines rather than folded into wind and solar, so the provenance
        # (Leng's bill of materials, IEA PVPS's unit) and the audit's life check
        # stay visible; CHAINS puts each back with its technology for reporting.
        "wind step-up transformers": tech.gwp_tx_wind_per_mw * (q["cap_wind"] + q["cap_offshore"]),
        "solar step-up transformers": tech.gwp_tx_solar_per_mwp * q["cap_solar"],
        # The battery's and fuel cell's own LV → 20 kV units, on the inverter
        # rating each container carries (Jasper 2026's unit, transformers.py).
        "battery step-up transformers": tech.gwp_tx_batt_per_mw * q["cap_batt_p"],
        "fuel cell step-up transformers": tech.gwp_tx_fc_per_mw * q["cap_fc"],
    }
    # The cable to the connection substation: on grid_on (1 while the grid is
    # on, a fixed variable so linopy takes it) with one price list, on the
    # switches once the list is chosen. Scored without grid_on (a merit-order
    # dispatch) it is on whenever there is a connection.
    gwp_embodied["grid connection cable"] = (
        tech.gwp_grid_fixed_per_year * q.get("grid_on", 1.0 if _positive(q.get("cap_grid", 0.0)) else 0.0)
        if opts is None else
        _sum(o.gwp_fixed_per_year * q[f"on_{i}"] for i, o in enumerate(opts)))
    gwp_operational = {
        "grid import": (scale * (ci * q["imp"] * dt).sum() if opts is None else
                        _sum(scale * (group_series[g][1] * q[group_import_var(g)] * dt).sum()
                             for g in sorted({o.group for o in opts}))),
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
        "grid connection": (tech.cost_grid_per_mw_year * q["cap_grid"] if opts is None else
                            _sum(o.cost_per_mw_year * q[f"cap_conn_{i}"] for i, o in enumerate(opts))),
        "grid winter-peak charge": tech.cost_grid_triad_per_mw_year * q.get("triad_mw", 0.0),
    }
    if opts is not None:
        # A constant in the single-price-list model (objective_constants); a
        # term on the switches once the price list is chosen.
        cost_capital["grid connection fixed charges"] = _sum(
            o.cost_fixed_per_year * q[f"on_{i}"] for i, o in enumerate(opts))
    cost_operational = {
        "grid energy + network": (scale * (price * q["imp"] * dt).sum() if opts is None else
                                  _sum(scale * (group_series[g][0] * q[group_import_var(g)] * dt).sum()
                                       for g in sorted({o.group for o in opts}))),
        buy_1: scale * (tech.bought_h2_gbp_per_kg * q["h2_buy"]).sum(),
        buy_2: scale * (tech.bought_h2_2_gbp_per_kg * q["h2_buy_2"]).sum(),
        "electrolyser stacks and water": scale * (tech.cost_ely_variable_per_kg
                                                  * kg_per_mwh_in * q["p_ely"] * dt).sum(),
        "unserved (VoLL)": scale * (VOLL_GBP_PER_MWH * q["unserved"] * dt).sum(),
        "export credit": -scale * (price * q["exp"] * dt).sum(),
    }
    return {"gwp_embodied": gwp_embodied, "gwp_operational": gwp_operational,
            "cost_capital": cost_capital, "cost_operational": cost_operational}


# Which objective terms belong to which technology's chain — how a traditional
# LCA would group them on the way to that technology's functional unit. The LP
# keeps them as separate terms because they scale with different things (a
# step-up with capacity, consumables with output); this is the view that puts
# the electrical infrastructure and the consumables back with their technology
# for reporting. Every term key must appear in exactly one chain, or
# ``chains()`` raises — so a new term cannot fall outside the view unnoticed.
CHAINS = {
    "wind": {"wind", "offshore wind", "wind step-up transformers"},
    "solar": {"solar", "solar step-up transformers"},
    "grid": {"grid import", "grid energy + network", "grid connection", "connection fixed",
             "grid connection fixed charges", "grid connection cable", "grid winter-peak charge",
             "export credit"},
    "battery": {"battery", "battery cells and container", "battery power conversion",
                "battery step-up transformers"},
    "electrolyser": {"electrolyser", "electrolyser stack replacements", "electrolyser consumables",
                     "electrolyser stacks and water"},
    "hydrogen tank": {"H2 tank", "H2 leaked from tank"},
    "fuel cell": {"fuel cell", "fuel cell stack replacements", "fuel cell BoP replacements",
                  "fuel cell maintenance", "fuel cell step-up transformers"},
    "unserved load": {"unserved (VoLL)"},
}
CHAIN_PREFIXES = {"bought hydrogen": "bought H2"}       # colour-named keys


def chains(terms: dict, side: str) -> dict:
    """``{chain: {term: value}}`` for one side, "gwp" or "cost", of labelled terms.

    ``terms`` is what ``objective_terms``/``score`` return. Group names are
    folded away: a chain holds its capital and its operational lines together,
    which is the point.
    """
    groups = [k for k in terms if k.startswith(side)]
    out = {c: {} for c in list(CHAINS) + list(CHAIN_PREFIXES)}
    for g in groups:
        for k, v in terms[g].items():
            chain = next((c for c, keys in CHAINS.items() if k in keys), None)
            if chain is None:
                chain = next((c for c, pre in CHAIN_PREFIXES.items() if k.startswith(pre)), None)
            if chain is None:
                raise KeyError(f"objective term {k!r} belongs to no chain; add it to dc_model.CHAINS")
            out[chain][k] = v
    return {c: d for c, d in out.items() if d}


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
    # With connection options the fixed charge is a term on the switches
    # ("grid connection fixed charges" in objective_terms), not a constant.
    cost_const = (tech.cost_grid_fixed_per_year
                  if grid and connection_options_of(tech) is None else 0.0)
    gwp_const = (tech.dc_fixed_gwp_per_year
                 + tech.dc_other_gwp_per_mwh
                 * float(series.demand_mw.sum() * series.dt_hours) * series.annual_scale)
    return cost_const, gwp_const


def _total(*groups):
    """Sum labelled terms. ``sum()`` would start from int 0, which a linopy
    expression accepts but a reader should not have to wonder about."""
    return _sum(v for g in groups for v in g.values())


def _positive(x) -> bool:
    """Whether a plain number is positive; a symbol or expression counts as on."""
    try:
        return float(x) > 0.0
    except (TypeError, ValueError):
        return True


def _sum(items):
    """Sum linopy expressions, arrays or floats without a leading int 0."""
    from functools import reduce
    import operator
    items = list(items)
    return reduce(operator.add, items) if items else 0.0


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


# The branch-and-bound gap when the model carries the price-list switches:
# HiGHS stops at 0.01 % by default, which is £1,000 a year on a £10 m site and
# enough to break the frontier's tie-breaks (dc_pareto.LEX_TOL is 1e-6).
MIP_REL_GAP = 1e-7
# The cheap run's gap (4 Nov 2026): the solver stops once no design can beat
# the one in hand by more than 0.1 % of the bill, instead of proving it to one
# part in ten million. The returned cost is within 0.1 % of the best; the
# design can differ where two sit within 0.1 % of each other. Not for the
# checks that compare a switched answer to a forced one to 1e-5.
LOOSE_MIP_REL_GAP = 1e-3


def solve(m, solver="highs", **kw):
    import logging
    logging.getLogger("linopy").setLevel(logging.ERROR)
    if solver == "highs" and len(m.binaries):
        kw.setdefault("mip_rel_gap", MIP_REL_GAP)
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

def facility_terms(tech: Tech, demand_mwh: float) -> dict:
    """The data centre's own carbon, by driver, for a year of ``demand_mwh``.

    Constant across architectures, so it is held out of the LP (see
    ``objective_constants``) and reported here. The LCA map reads its terms
    from this function as it reads ``objective_terms``.
    """
    return {"data centre, IT capacity": tech.dc_fixed_gwp_per_year,
            "data centre, cooling consumables": tech.dc_other_gwp_per_mwh * demand_mwh}


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
    facility = facility_terms(tech, mwh)
    return {
        "gwp_embodied": terms["gwp_embodied"],
        "gwp_operational": terms["gwp_operational"],
        "gwp_facility": facility,
        "cost_capital": terms["cost_capital"],
        "cost_operational": terms["cost_operational"],
        # The same numbers grouped by technology, each with its own
        # infrastructure and consumables — the traditional LCA view.
        "gwp_chains": {**chains(terms, "gwp"), "facility": facility},
        "cost_chains": chains(terms, "cost"),
        "demand_MWh_per_year": mwh,
        "totals": totals(obj),
        # A connection sitting on its band's floor is one a cheaper band would
        # probably serve. Not re-solved automatically: re-running with the
        # ceiling just below the floor is the user's call (CONNECTION_TIER_PLAN).
        # With connection options the band is chosen, so the floor is the chosen
        # option's and sitting on it means the next band down was dearer.
        "grid_floor": grid_floor_status(V, assets, obj.get("options")),
        "connection": connection_status(V, obj.get("options")),
    }


def grid_floor_status(V, assets, options=None) -> dict:
    """Whether the built connection sits on its band's floor."""
    floor = assets.grid_floor_mw if assets.grid else 0.0
    ceiling = assets.grid_limit_mw
    ch = chosen_option(V, options)
    if ch is not None:
        floor, ceiling = ch[1].floor_mw, ch[1].ceiling_mw
    built = float(V["cap_grid"].solution)
    return {"floor_mw": floor, "cap_grid_mw": built,
            "binding": floor > 0 and built <= floor * (1 + 1e-6),
            "ceiling_mw": ceiling,
            "ceiling_binding": ceiling is not None and np.isfinite(ceiling) and built >= ceiling * (1 - 1e-6)}


def connection_status(V, options) -> dict | None:
    """The price list a solved model chose, as plain values (None without options)."""
    ch = chosen_option(V, options)
    if ch is None:
        return None
    i, o = ch
    return {"index": i, "key": o.key, "group": o.group, "floor_mw": o.floor_mw, "ceiling_mw": o.ceiling_mw,
            "cap_mw": float(V[f"cap_conn_{i}"].solution), **{k: v for k, v in o.info.items()}}


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
    for k in V:                               # imports by voltage group, when the price list is chosen
        if k.startswith("imp_"):
            df[k] = V[k].solution.values
    df.insert(0, "demand", series.demand_mw)
    df["grid_gwp_per_mwh"] = series.grid_gwp_per_mwh
    df["price_per_mwh"] = series.grid_price_per_mwh
    lf = loss_factors(series, tech) if tech is not None else {"wind": 0.0, "solar": 0.0}
    df["curtailed"] = ((1.0 - lf["wind"]) * series.cf_wind
                       * (float(V["cap_wind"].solution) + float(V["cap_offshore"].solution))
                       + (1.0 - lf["solar"]) * series.cf_solar * float(V["cap_solar"].solution)
                       - df.p_wind - df.p_offshore - df.p_solar)
    return df
