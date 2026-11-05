"""Invariants of the data centre LP.

These run on a synthetic two-week series rather than the cached year, so they
need no Renewables.ninja call, no Brightway connection and no network API — and
they finish in seconds. The point is the *structure* of the model: that energy
balances, that storage is cyclic and bounded, that hydrogen mass is conserved,
that the strategies actually bind, and that the Pareto ordering holds. Whether
the coefficients are right is tested in test_coefficients.py.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from optimisation import dc_model as M

pytest.importorskip("linopy")

DT = 0.5
N = 14 * 24 * 2          # two weeks, half-hourly


@pytest.fixture(scope="module")
def series():
    rng = np.random.default_rng(7)
    idx = pd.date_range("2025-01-01", periods=N, freq="30min")
    hours = np.arange(N) * DT
    return M.Series(
        index=idx, dt_hours=DT,
        demand_mw=np.full(N, 7.31),
        cf_wind=np.clip(0.35 + 0.3 * np.sin(hours / 37) + 0.1 * rng.standard_normal(N), 0, 1),
        cf_solar=np.clip(0.5 * np.sin(np.pi * ((hours % 24) - 6) / 12), 0, 1),
        grid_gwp_per_mwh=250 + 120 * np.sin(hours / 11) + 20 * rng.standard_normal(N),
        grid_price_per_mwh=95 + 40 * np.sin(hours / 13) + 10 * rng.standard_normal(N),
    )


@pytest.fixture(scope="module")
def tech():
    # Today's central coefficients (London, 6.36 MW IT, 14 Oct 2026), so the
    # synthetic solves exercise the magnitudes the study actually uses. Network
    # charges and bought hydrogen are the synthetic ones.
    return M.Tech(
        gwp_wind=19_244, gwp_offshore=26_408, gwp_solar=23_561,
        gwp_batt_p=2_124, gwp_batt_e=7_241,
        gwp_ely=10_435, gwp_tank=63.8,
        gwp_fc_bop_per_mw=44_325, gwp_fc_stack_per_mw=97_431,
        gwp_fc_maint_per_mwh=0.0032,
        gwp_grid_per_mw=137.7,
        # BoP annuity net of its calendar replacement, which cost_fc_bop_per_mw
        # charges. Central case of h2_capex.fuel_cell_costs.
        cost_fc_stack_per_mw=308_698.0, cost_fc_bop_per_mw=1_486_089.0,
        fc_bop_calendar_years=20.0, fc_bop_duty_hours=80_000.0,
        fc_stack_calendar_years=10.0, fc_stack_duty_hours=30_000.0,
        cost_wind=147_073, cost_offshore=419_201, cost_solar=48_368,
        cost_batt_p=34_903, cost_batt_e=11_634,
        cost_ely=212_511, cost_tank=64.6, cost_fc=99_842,
        cost_grid_per_mw_year=40_949, cost_grid_fixed_per_year=271_192,
        ely_kwh_per_kg=54.0, ely_variable_gwp_per_kg=0.1072,
        tank_compression_kwh_per_kg=0.0, tank_leakage_per_hour=0.0,
        batt_rte=0.88, batt_leakage_per_hour=0.0,
        fc_kg_h2_per_mwh=63.164,
        bought_h2_gbp_per_kg=3.0, bought_h2_gwp_per_kg=10.0,
        dc_fixed_gwp_per_year=999_453, dc_other_gwp_per_mwh=1.809,
        horizon_years=25.0,
    )


def _solve(series, tech, assets, **kw):
    m, V, obj = M.build_model(series, assets, tech, **kw)
    M.solve(m)
    return V, obj


ALL = M.Assets(grid=True, wind=True, solar=True, battery=True, electrolyser=True,
               tank=True, fuel_cell=True, buy_h2=True, grid_limit_mw=None)


# =============================================================================
# Physics
# =============================================================================
def test_energy_balance_closes(series, tech):
    V, _ = _solve(series, tech, ALL, objective="cost")
    g = lambda k: V[k].solution.values
    residual = (g("p_wind") + g("p_offshore") + g("p_solar") + g("dis") + g("p_fc")
                + g("imp") + g("unserved") - g("ch") - g("p_ely") - g("exp")
                - series.demand_mw)
    assert np.abs(residual).max() < 1e-6, f"max residual {np.abs(residual).max():.2e}"


def test_storage_stays_within_capacity(series, tech):
    V, _ = _solve(series, tech, ALL, objective="gwp")
    for level, cap in (("soc", "cap_batt_e"), ("tank", "cap_tank")):
        x = V[level].solution.values
        c = float(V[cap].solution)
        assert x.min() > -1e-6, f"{level} went negative"
        assert x.max() <= c + 1e-6, f"{level} exceeded {cap}"


def test_both_stores_are_cyclic(series, tech):
    """roll(t=1) wraps T-1 into 0, so the store cannot free-ride on ending empty."""
    V, _ = _solve(series, tech, ALL, objective="cost")
    eta = np.sqrt(tech.batt_rte)
    soc = V["soc"].solution.values
    ch, dis = V["ch"].solution.values, V["dis"].solution.values
    implied = soc[-1] + DT * (eta * ch[0] - dis[0] / eta)
    assert soc[0] == pytest.approx(implied, abs=1e-6)


def test_hydrogen_mass_is_conserved(series, tech):
    V, _ = _solve(series, tech, ALL, objective="cost")
    tank = V["tank"].solution.values
    made = 1000.0 / tech.ely_kwh_per_kg * DT * V["p_ely"].solution.values
    bought = V["h2_buy"].solution.values
    used = V["h2_fc"].solution.values
    implied = np.roll(tank, 1) + made + bought - used
    assert np.abs(tank - implied).max() < 1e-6


def test_fuel_cell_fuel_matches_its_output(series, tech):
    V, _ = _solve(series, tech, ALL, objective="cost")
    lhs = V["h2_fc"].solution.values
    rhs = tech.fc_kg_h2_per_mwh * DT * V["p_fc"].solution.values
    assert np.abs(lhs - rhs).max() < 1e-6


def test_reliability_is_respected(series, tech):
    V, _ = _solve(series, tech, ALL, objective="cost", unserved_fraction=0.0)
    assert V["unserved"].solution.values.sum() * DT < 1e-6


def test_grid_import_respects_the_connection_limit(series, tech):
    capped = M.Assets(grid=True, wind=True, solar=True, battery=True,
                      grid_limit_mw=3.0)
    V, _ = _solve(series, tech, capped, objective="cost")
    assert V["imp"].solution.values.max() <= 3.0 + 1e-6
    assert float(V["cap_grid"].solution) <= 3.0 + 1e-6


def test_locked_assets_stay_at_zero(series, tech):
    """An architecture is a set of bounds; a locked asset must not appear."""
    grid_only = M.Assets(grid=True, grid_limit_mw=None)
    V, _ = _solve(series, tech, grid_only, objective="cost")
    for k in ("cap_wind", "cap_solar", "cap_batt_p", "cap_ely", "cap_tank", "cap_fc"):
        assert abs(float(V[k].solution)) < 1e-9, f"{k} was built in grid_only"


# =============================================================================
# Objectives
# =============================================================================
def test_constants_are_excluded_from_the_objective_but_not_the_total(series, tech):
    """Reading the raw objective would understate both totals."""
    m, V, obj = M.build_model(series, ALL, tech, objective="cost")
    M.solve(m)
    tot = M.totals(obj)
    assert tot["cost_const_GBP_per_year"] == tech.cost_grid_fixed_per_year
    # The facility's IT-driven part plus its energy-driven part on gross demand.
    mwh = float(series.demand_mw.sum() * DT) * series.annual_scale
    assert tot["gwp_const_kgco2e_per_year"] == pytest.approx(
        tech.dc_fixed_gwp_per_year + tech.dc_other_gwp_per_mwh * mwh, rel=1e-12)
    assert tech.dc_other_gwp_per_mwh > 0          # or the line above tests nothing
    assert tot["cost_GBP_per_year"] > float(obj["cost"].solution)


def test_major_hazard_compliance_is_a_constant_of_a_build_allowed_a_tank(series, tech):
    """In the total and the breakdown, never in the objective, and netted off a
    cost limit so a tie-break cannot spend it. No tank allowed, no charge."""
    from dataclasses import replace
    charged = replace(tech, cost_major_hazard_per_year=56_000.0)
    with_tank = ALL
    m0, V0, obj0 = M.build_model(series, with_tank, tech, objective="cost")
    M.solve(m0)
    m1, V1, obj1 = M.build_model(series, with_tank, charged, objective="cost")
    M.solve(m1)
    t0, t1 = M.totals(obj0), M.totals(obj1)
    assert t1["cost_GBP_per_year"] == pytest.approx(t0["cost_GBP_per_year"] + 56_000.0, rel=1e-9)
    assert float(V1["cap_tank"].solution) == pytest.approx(float(V0["cap_tank"].solution), rel=1e-6, abs=1e-6)
    c = M.contributions(V1, obj1, series, charged, with_tank)
    assert c["cost_operational"]["major-hazard compliance"] == 56_000.0
    assert c["cost_operational"]["connection fixed"] == tech.cost_grid_fixed_per_year
    assert "major-hazard compliance" in c["cost_chains"]["hydrogen tank"]
    # Held at its own total, the build is unmoved: the charge bought no slack.
    m2, V2, obj2 = M.build_model(series, with_tank, charged, objective="gwp",
                                 cost_limit=t1["cost_GBP_per_year"] * (1 + 1e-9))
    M.solve(m2)
    assert M.totals(obj2)["cost_GBP_per_year"] <= t1["cost_GBP_per_year"] * (1 + 1e-6)
    no_tank = M.Assets(grid=True)
    _, _, obj3 = M.build_model(series, no_tank, charged, objective="cost")
    assert obj3["cost_const"] == tech.cost_grid_fixed_per_year


def test_the_battery_duration_cap_binds_only_when_asked(series, tech):
    from dataclasses import replace
    a = M.Assets(grid=False, wind=True, solar=True, battery=True, grid_limit_mw=0.0)
    m0, _, _ = M.build_model(series, a, tech, objective="cost", unserved_fraction=1.0)
    assert "batt_duration" not in m0.constraints
    m1, V, _ = M.build_model(series, a, replace(tech, batt_max_duration_hours=2.0), objective="cost", unserved_fraction=1.0)
    M.solve(m1)
    assert float(V["cap_batt_e"].solution) <= 2.0 * float(V["cap_batt_p"].solution) + 1e-6


def test_the_connection_is_held_inside_its_band(series, tech):
    """floor <= cap_grid: a grid-only build cannot drop to a cheaper band than
    the one its charges were read for, and says so when the floor binds."""
    a = M.Assets(grid=True, grid_limit_mw=40.0, grid_floor_mw=21.5)
    m, V, obj = M.build_model(series, a, tech, objective="cost")
    M.solve(m)
    assert float(V["cap_grid"].solution) == pytest.approx(21.5, rel=1e-6)
    assert M.contributions(V, obj, series, tech, a)["grid_floor"]["binding"]


def test_an_islanded_build_ignores_the_floor(series, tech):
    a = M.Assets(grid=False, wind=True, solar=True, battery=True,
                 grid_limit_mw=0.0, grid_floor_mw=21.5)
    m, V, obj = M.build_model(series, a, tech, objective="cost", unserved_fraction=1.0)
    M.solve(m)
    assert float(V["cap_grid"].solution) == 0.0
    assert not M.contributions(V, obj, series, tech, a)["grid_floor"]["binding"]


def test_islanded_builds_pay_no_grid_fixed_charge(series, tech):
    """The fixed connection charge belongs to the connection; no grid, no charge."""
    a = M.Assets(grid=False, wind=True, solar=True, battery=True, grid_limit_mw=0.0)
    m, V, obj = M.build_model(series, a, tech, objective="cost", unserved_fraction=1.0)
    M.solve(m)
    assert M.totals(obj)["cost_const_GBP_per_year"] == 0.0
    assert M.contributions(V, obj, series, tech, a)["cost_operational"]["connection fixed"] == 0.0


def test_min_gwp_is_cleaner_and_min_cost_is_cheaper(series, tech):
    """If this fails the Pareto code is wrong. Non-negotiable."""
    _, cheap = _solve(series, tech, ALL, objective="cost")
    _, clean = _solve(series, tech, ALL, objective="gwp")
    c, g = M.totals(cheap), M.totals(clean)
    assert g["gwp_kgco2e_per_year"] <= c["gwp_kgco2e_per_year"] + 1e-3
    assert c["cost_GBP_per_year"] <= g["cost_GBP_per_year"] + 1e-3


def test_epsilon_constraint_binds(series, tech):
    _, cheap = _solve(series, tech, ALL, objective="cost")
    _, clean = _solve(series, tech, ALL, objective="gwp")
    hi = M.totals(cheap)["gwp_kgco2e_per_year"]
    lo = M.totals(clean)["gwp_kgco2e_per_year"]
    if hi - lo < 1e-6:
        pytest.skip("front is degenerate on this synthetic series")
    limit = lo + 0.5 * (hi - lo)
    _, mid = _solve(series, tech, ALL, objective="cost", gwp_limit=limit)
    assert M.totals(mid)["gwp_kgco2e_per_year"] <= limit + 1e-3


# =============================================================================
# Strategies
# =============================================================================
def test_baseload_forces_a_high_capacity_factor(series, tech):
    a = M.Assets(grid=True, electrolyser=True, tank=True, fuel_cell=True,
                 grid_limit_mw=None)
    m, V, _ = M.build_model(series, a, tech, objective="cost", ely_strategy="baseload")
    # Forced: on this series a cost solve builds no electrolyser, and a test
    # that skips whenever that happens never tests the floor at all.
    m.add_constraints(V["cap_ely"] >= 1.0, name="force_ely")
    M.solve(m)
    cap = float(V["cap_ely"].solution)
    cf = V["p_ely"].solution.values.sum() * DT / (cap * series.hours)
    assert cf >= 0.85 - 1e-3, f"baseload CF floor not binding: {cf:.3f}"


def test_surplus_only_caps_the_electrolyser_at_leftover_generation(series, tech):
    """flexible, islanded: the data centre gets first claim on renewable output.

    Asserted over the window rather than per step. The per-step form is
    infeasible rather than binding when generation falls short — see
    dc_model.apply_strategy — so the window form is what the model states and
    what this checks.
    """
    a = M.Assets(grid=False, wind=True, solar=True, electrolyser=True,
                 tank=True, fuel_cell=True, grid_limit_mw=0.0)
    V, _ = _solve(series, tech, a, objective="cost", ely_strategy="flexible",
                  unserved_fraction=1.0)
    ely = V["p_ely"].solution.values.sum() * DT
    # Available, not dispatched — curtailment is implicit, so measuring against
    # p_wind would let the constraint be satisfied by generating less.
    available = (series.cf_wind * float(V["cap_wind"].solution)
                 + series.cf_solar * float(V["cap_solar"].solution)
                 + series.cf_wind * float(V["cap_offshore"].solution)).sum() * DT
    served = series.demand_mw.sum() * DT - V["unserved"].solution.values.sum() * DT
    assert ely <= available - served + 1e-6, (
        f"electrolyser took {ely:.3f} MWh against {available - served:.3f} MWh "
        "of available surplus")


def test_surplus_only_stays_feasible_when_generation_falls_short(series, tech):
    """The bug this formulation exists to avoid: a negative bound on p_ely >= 0."""
    a = M.Assets(grid=False, wind=True, solar=True, electrolyser=True,
                 tank=True, fuel_cell=True, grid_limit_mw=0.0)
    V, _ = _solve(series, tech, a, objective="cost", ely_strategy="flexible",
                  unserved_fraction=1.0)
    assert V["p_ely"].solution.values.min() >= -1e-6


def test_unknown_strategy_is_refused(series, tech):
    with pytest.raises(ValueError, match="Unknown electrolyser strategy"):
        _solve(series, tech, ALL, objective="cost", ely_strategy="whatever")


# =============================================================================
# Fuel cell replacement rule
# =============================================================================
# A grid held below demand makes the fuel cell run flat out on bought hydrogen
# (duty binds); an unlimited grid with a forced 1 MW fuel cell leaves it idle
# (calendar binds). Both are forced, so neither case can quietly skip.
DUTY_FC = M.Assets(grid=True, fuel_cell=True, buy_h2=True, grid_limit_mw=5.0)
IDLE_FC = M.Assets(grid=True, fuel_cell=True, buy_h2=True, grid_limit_mw=None)


def _solve_fc(series, tech, assets, objective):
    m, V, obj = M.build_model(series, assets, tech, objective=objective)
    m.add_constraints(V["cap_fc"] >= 1.0, name="force_fc")
    M.solve(m)
    return V, obj


@pytest.mark.parametrize("assets, binding", [(DUTY_FC, "duty"), (IDLE_FC, "calendar")])
@pytest.mark.parametrize("objective", ["gwp", "cost"])
def test_fuel_cell_replacement_counts_take_the_binding_limit(series, tech, assets,
                                                             binding, objective):
    V, _ = _solve_fc(series, tech, assets, objective)
    cap = float(V["cap_fc"].solution)
    mwh = V["p_fc"].solution.values.sum() * DT * series.annual_scale
    for units, calendar, duty in (
            (V["fc_bop_units"], tech.fc_bop_calendar_years, tech.fc_bop_duty_hours),
            (V["fc_stack_units"], tech.fc_stack_calendar_years, tech.fc_stack_duty_hours)):
        u = float(units.solution)
        assert u >= cap / calendar - 1e-6
        assert u >= mwh / duty - 1e-6
        assert u == pytest.approx(max(cap / calendar, mwh / duty), rel=1e-6)
        assert (mwh / duty > cap / calendar) == (binding == "duty")


def test_bop_duty_replacements_reach_the_cost_objective(series, tech):
    """Reviewer point 1: above 2,400 h/yr BoP wear was charged in carbon only."""
    V, obj = _solve_fc(series, tech, DUTY_FC, "cost")
    cap = float(V["cap_fc"].solution)
    bop = float(V["fc_bop_units"].solution)
    assert bop > cap / tech.fc_bop_calendar_years * 1.5, "BoP duty should bind here"
    line = M.contributions(V, obj, series, tech, DUTY_FC)["cost_capital"]["fuel cell"]
    calendar_only = cap * (tech.cost_fc + tech.cost_fc_bop_per_mw / tech.fc_bop_calendar_years
                           + tech.cost_fc_stack_per_mw / tech.fc_stack_calendar_years)
    assert line == pytest.approx(
        tech.cost_fc * cap + tech.cost_fc_bop_per_mw * bop
        + tech.cost_fc_stack_per_mw * float(V["fc_stack_units"].solution), rel=1e-9)
    assert line > calendar_only * 1.2


def test_calendar_bound_fuel_cell_cost_equals_the_annuity(series, tech):
    """An idle fuel cell costs exactly what the old calendar annuity said."""
    V, obj = _solve_fc(series, tech, IDLE_FC, "gwp")
    cap = float(V["cap_fc"].solution)
    line = M.contributions(V, obj, series, tech, IDLE_FC)["cost_capital"]["fuel cell"]
    assert line == pytest.approx(
        cap * (tech.cost_fc + tech.cost_fc_bop_per_mw / tech.fc_bop_calendar_years
               + tech.cost_fc_stack_per_mw / tech.fc_stack_calendar_years), rel=1e-6)


def test_both_objectives_charge_every_replacement_variable(series, tech):
    """Pooled, charging the stack alone passed the audit; each must appear in both."""
    from optimisation import audit
    m, V, obj = M.build_model(series, ALL, tech, objective="cost")
    cost = audit._coeff_by_variable(m, obj["cost"])
    gwp = audit._coeff_by_variable(m, obj["gwp"])
    for v in ("fc_bop_units", "fc_stack_units"):
        assert cost.get(v, 0.0) > 0, f"{v} missing from cost"
        assert gwp.get(v, 0.0) > 0, f"{v} missing from gwp"


def test_stack_calendar_life_is_not_the_horizon(series, tech):
    """The horizon used to set the stack's calendar rate and nothing else."""
    from dataclasses import replace
    _, a = _solve_fc(series, replace(tech, horizon_years=10.0), IDLE_FC, "gwp")
    _, b = _solve_fc(series, replace(tech, horizon_years=50.0), IDLE_FC, "gwp")
    assert M.totals(a)["gwp_kgco2e_per_year"] == pytest.approx(
        M.totals(b)["gwp_kgco2e_per_year"], rel=1e-9)


def test_offshore_wind_is_out_of_scope():
    """All sites are on land; there is no offshore profile to run it on."""
    from optimisation import dc_architectures as A
    assert not A.architecture("res_h2_grid", offshore=True).offshore_wind
    assert not A.custom({"offshore_wind": True, "grid": True}, offshore=True).offshore_wind


def test_export_is_refused_until_it_is_modelled(series, tech):
    a = M.Assets(grid=True, allow_export=True)
    with pytest.raises(NotImplementedError, match="Export"):
        M.build_model(series, a, tech)


def test_surplus_only_is_measured_against_available_not_dispatched_generation(series, tech):
    """Regression: the constraint must not be satisfiable by curtailing.

    Curtailment is implicit — p_wind <= cf x cap is an inequality — so writing
    surplus-only against dispatched p_wind makes it self-referential: the LP
    satisfies it by generating less, which starves the electrolyser and drives
    the model to oversize generation instead of building storage. On the real
    2025 London series the broken form built 1,152 MW of wind and no hydrogen
    chain at all for a 7.31 MW load.

    The observable signature is that `flexible` and `free` diverge wildly in an
    islanded architecture. They should very nearly coincide there: with no grid
    and no battery, giving the data centre first claim on renewable output is
    close to what an unconstrained LP does anyway.
    """
    a = M.Assets(grid=False, wind=True, solar=True, electrolyser=True,
                 tank=True, fuel_cell=True, grid_limit_mw=0.0)
    _, flex = _solve(series, tech, a, objective="cost", ely_strategy="flexible",
                     unserved_fraction=0.02)
    _, free = _solve(series, tech, a, objective="cost", ely_strategy="free",
                     unserved_fraction=0.02)
    f, g = M.totals(flex)["cost_GBP_per_year"], M.totals(free)["cost_GBP_per_year"]
    assert f >= g - 1.0, "a constrained strategy cannot beat the free one"
    assert f <= g * 1.5, (
        f"flexible £{f/1e6:.2f}m against free £{g/1e6:.2f}m — surplus-only is "
        "over-binding, most likely measured against dispatched generation")


def test_buying_hydrogen_without_a_price_is_refused(series, tech):
    """Regression: an unpriced colour let the LP buy free, zero-carbon hydrogen.

    Scenario 21 had buy_h2 enabled and no colour set, so bought_h2_gbp_per_kg
    was 0. It returned the best result in the whole matrix — £2.83 m/yr and
    24 g/kWh — entirely on free hydrogen. A silent zero is the worst kind of
    wrong input: it produces a plausible, headline-grabbing answer.
    """
    import dataclasses
    free_h2 = dataclasses.replace(tech, bought_h2_gbp_per_kg=0.0)
    a = M.Assets(grid=True, fuel_cell=True, buy_h2=True, grid_limit_mw=None)
    with pytest.raises(ValueError, match="no colour was priced"):
        M.build_model(series, a, free_h2, objective="cost")


# =============================================================================
# Generation step-up transformers
# =============================================================================
def _window(days, phase=0.0, seed=7):
    """A synthetic series of a given length and season.

    ``phase`` shifts the wind pattern so a short window can be windy or calm,
    which is what makes the LP build a genuinely different amount of wind.
    """
    n = int(days * 24 / DT)
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2025-01-01", periods=n, freq="30min")
    hours = np.arange(n) * DT
    return M.Series(
        index=idx, dt_hours=DT,
        demand_mw=np.full(n, 7.31),
        cf_wind=np.clip(0.35 + 0.3 * np.sin(hours / 37 + phase)
                        + 0.1 * rng.standard_normal(n), 0, 1),
        cf_solar=np.clip(0.5 * np.sin(np.pi * ((hours % 24) - 6) / 12), 0, 1),
        grid_gwp_per_mwh=250 + 120 * np.sin(hours / 11) + 20 * rng.standard_normal(n),
        grid_price_per_mwh=95 + 40 * np.sin(hours / 13) + 10 * rng.standard_normal(n),
    )


def test_transformer_term_is_per_year_whatever_the_window(tech):
    """The coefficient is an annual capital charge, so it must not move with
    how long a window the LP was solved over.

    Everything operational in ``gwp`` is multiplied by ``series.annual_scale``
    and everything capital is not. That is the whole mechanism, and it is one
    edit away from being wrong in either direction — a term moved inside the
    scaled block would read 26x high on a two-week window and 122x high on a
    three-day one. Solved across four window lengths and two seasons, the
    charge per MW built must come out identical every time.
    """
    import dataclasses
    COEF_W, COEF_S = 278.7, 184.2
    t2 = dataclasses.replace(tech, gwp_tx_wind_per_mw=COEF_W,
                             gwp_tx_solar_per_mwp=COEF_S)
    assets = M.Assets(grid=True, wind=True, solar=True)

    built, implied = [], []
    for days, phase in ((3, 0.0), (7, 0.0), (14, 0.0), (28, 0.0), (14, np.pi)):
        s = _window(days, phase)
        scale = s.annual_scale
        assert scale > 1.5, "window is not shorter than a year, so nothing is tested"

        V, obj = _solve(s, t2, assets, objective="gwp")
        cap_w = float(V["cap_wind"].solution) + float(V["cap_offshore"].solution)
        cap_s = float(V["cap_solar"].solution)
        e = M.contributions(V, obj, s, t2, assets)["gwp_embodied"]
        row = e["wind step-up transformers"] + e["solar step-up transformers"]
        expected = COEF_W * cap_w + COEF_S * cap_s

        # It is the annual charge on what was built...
        assert row == pytest.approx(expected, rel=1e-9), (
            f"{days}d window: the term is not coefficient x capacity")
        # ...and emphatically not the window total grossed up to a year, which
        # is what it would be if the term were moved inside the scaled block.
        assert abs(row - scale * expected) > 1e-6, (
            f"{days}d window: the term has been annualised a second time "
            f"(scale={scale:.1f})")

        built.append(cap_w)
        # Net of solar, the charge per MW of wind must be the coefficient
        # itself — in every window, whatever got built.
        implied.append((row - COEF_S * cap_s) / cap_w if cap_w > 1e-9 else np.nan)

    assert max(built) > 1e-6, "no window built wind, so the test proves nothing"
    # The windows must genuinely differ, or invariance is vacuous.
    assert max(built) / min(built) > 1.05, (
        f"every window built the same wind ({built}) — this cannot detect a "
        "window-dependent charge")
    assert implied == pytest.approx([COEF_W] * len(implied), rel=1e-9), (
        f"the per-MW charge moved with the window: {implied}")


def test_step_up_transformers_are_charged_on_capacity(series, tech):
    """The term must reach the objective and scale with MW, not with MWh.

    Constructed on a modified Tech rather than the shared fixture so the rest
    of this file keeps testing the model it was written against.
    """
    import dataclasses
    t2 = dataclasses.replace(tech, gwp_tx_wind_per_mw=230.2,
                             gwp_tx_solar_per_mwp=184.2)
    assets = M.Assets(grid=True, wind=True, solar=True)
    V, obj = _solve(series, t2, assets, objective="gwp")

    built = float(V["cap_wind"].solution)
    assert built > 1e-6, "min-GWP built no wind, so the test proves nothing"

    e = M.contributions(V, obj, series, t2, assets)["gwp_embodied"]
    row = e["wind step-up transformers"] + e["solar step-up transformers"]
    expected = (230.2 * (built + float(V["cap_offshore"].solution))
                + 184.2 * float(V["cap_solar"].solution))
    assert abs(row - expected) < 1e-6

    # And it is genuinely in the objective, not only in the report: the same
    # build costed with a zero coefficient is cleaner by exactly this much.
    t0 = dataclasses.replace(tech, gwp_tx_wind_per_mw=0.0, gwp_tx_solar_per_mwp=0.0)
    _, obj0 = _solve(series, t0, assets, objective="gwp")
    assert M.totals(obj)["gwp_kgco2e_per_year"] > M.totals(obj0)["gwp_kgco2e_per_year"]


def test_wind_and_solar_are_both_on_real_transformer_bills():
    """The gap this used to guard is closed: both are now real inventories.

    Wind carries the per-turbine step-ups from Leng's bill of materials; solar
    carries the inverter-station units from IEA PVPS T12-33:2026. This test
    replaces one that asserted solar was still on an invented plant-rated unit
    scaled off ecoinvent's 280 g electronics dataset — that basis survives only
    to reproduce pre-2026 runs, and must never be what the LP charges.
    """
    from optimiser_lca import stepup_transformers as inv, registry as R
    from optimisation import transformers as tx
    if not tx.CACHE_PATH.exists():
        pytest.skip("transformer_decomposition_cache.json not built — "
                    "run `python optimisation/transformers.py` first")
    d = tx.decompose()
    wind = tx.kgco2e_per_mw_year("onshore_wind")
    solar = tx.kgco2e_per_mw_year("solar_pv")
    s = d["solar"]

    # Both read the foreground; neither is a scaled dataset.
    assert d["wind"]["code"] == tx.WIND_CODE
    assert s["code"] == tx.SOLAR_CODE
    assert s["database"] == R.TRANSFORMER_DB
    # The unit over its life, plus Smith A15's replacements per year (since 21 Oct 2026).
    assert solar == pytest.approx(s["kgco2e_per_MWp"] / d["asset_life_years"]
                                  + s["replacement_kgco2e_per_MWp_30y"] / s["replacement_reference_years"])

    # ...and specifically NOT the invented unit, which is what used to be here.
    legacy = (d["solar_legacy"]["kgco2e_per_MVA"] * tx.SOLAR_MVA_PER_MWP
              / d["asset_life_years"])
    assert solar != pytest.approx(legacy)

    # The unit must be wound for the voltage the site actually collects at,
    # stepping up from the inverter's low-voltage terminals. This is the whole
    # reason it is the right transformer for this chain.
    assert s["primary_kV"] == pytest.approx(d["site_collection_kV"])
    lo, _hi = d["medium_voltage_band_kV"]
    assert s["secondary_kV"] < lo

    # The count is read off the reference plant, not derived from a DC/AC ratio.
    assert s["units_per_MWp"] == pytest.approx(
        s["units_per_plant"] / s["reference_plant_MWp"])

    # The transcribed bill must still rebuild IEA PVPS's own stated unit mass.
    # This is the guard on the hardboard unit correction: the workbook cell
    # reads "36.96 m3" for a 36.96 kg row, so the bill sums to 5,670.0 against
    # the report's "approximately 5,680" (within 0.5 %, 21 Oct 2026).
    bill = sum(s["materials_kg_per_unit"].values()) + inv.UPV_TX_FIBREBOARD_KG
    assert bill == pytest.approx(5_670.0, abs=0.01)
    assert abs(bill - inv.UPV_TX_STATED_TOTAL_KG) <= inv.UPV_TX_TOTAL_TOLERANCE * inv.UPV_TX_STATED_TOTAL_KG

    # Two independent sources for step-ups of comparable rating should land in
    # the same place. Solar carries factory energy that wind does not, so it is
    # the higher of the two, but only just.
    assert 0.8 < solar / wind < 1.5


# =============================================================================
# Storage standing-loss overrides (the sweep hooks). No LP is solved.
# =============================================================================
def test_storage_loss_overrides_reach_the_tech(tech):
    from optimisation import dc_inputs as I
    out = I.with_storage_losses(tech, batt_standing_loss_per_hour=1e-4,
                                tank_leakage_per_hour=2e-5)
    assert out.batt_leakage_per_hour == pytest.approx(1e-4)
    assert out.tank_leakage_per_hour == pytest.approx(2e-5)
    # Recorded, so a result says which point of the band it was solved at...
    assert out.labels["batt_standing_loss_per_hour"] == pytest.approx(1e-4)
    assert out.labels["tank_leakage_per_hour"] == pytest.approx(2e-5)
    # ...and the shared fixture is not mutated underneath the other tests.
    assert tech.batt_leakage_per_hour == 0.0 and tech.tank_leakage_per_hour == 0.0
    # One override leaves the other store alone.
    only_tank = I.with_storage_losses(tech, tank_leakage_per_hour=3e-6)
    assert only_tank.batt_leakage_per_hour == tech.batt_leakage_per_hour
    assert only_tank.tank_leakage_per_hour == pytest.approx(3e-6)


def test_none_keeps_the_default_storage_losses(tech):
    from dataclasses import replace
    from optimisation import dc_inputs as I
    base = replace(tech, batt_leakage_per_hour=3e-5, tank_leakage_per_hour=7e-6)
    out = I.with_storage_losses(base)
    assert out.batt_leakage_per_hour == 3e-5
    assert out.tank_leakage_per_hour == 7e-6
    assert out.labels["batt_standing_loss_per_hour"] == 3e-5
    assert out.labels["tank_leakage_per_hour"] == 7e-6


@pytest.mark.parametrize("kwarg", ["batt_standing_loss_per_hour",
                                   "tank_leakage_per_hour"])
@pytest.mark.parametrize("bad", [-1e-6, float("nan"), float("inf"), 0.01, 0.5])
def test_bad_storage_loss_is_refused(tech, kwarg, bad):
    from optimisation import dc_inputs as I
    with pytest.raises(ValueError):
        I.with_storage_losses(tech, **{kwarg: bad})


def test_build_tech_refuses_a_negative_loss_before_loading_anything():
    # An empty meta would raise KeyError once the coefficients were assembled,
    # so a ValueError here proves the check runs first — no cache, no Brightway.
    from optimisation import dc_inputs as I
    for kwarg in ("batt_standing_loss_per_hour", "tank_leakage_per_hour"):
        with pytest.raises(ValueError, match=kwarg):
            I.build_tech("london", {}, **{kwarg: -1e-4})


def test_shipped_storage_losses_are_zero_and_flagged_assumed():
    # The sweep bounds them; it does not set them. DATA_GAPS.md carries the band.
    from optimisation import battery, h2_storage
    assert battery.STANDING_LOSS_PER_HOUR == 0.0
    assert battery.STANDING_LOSS_IS_ASSUMED
    assert h2_storage.LEAKAGE_FRAC_PER_HOUR == 0.0
    assert h2_storage.LEAKAGE_IS_ASSUMED


# =============================================================================
# One objective: the LP, contributions() and myopic.evaluate agree
# =============================================================================
PARITY = {
    "grid_only": M.Assets(grid=True),
    "grid_res_battery": M.Assets(grid=True, wind=True, solar=True, battery=True),
    "grid_h2": M.Assets(grid=True, electrolyser=True, tank=True, fuel_cell=True),
    "grid_h2_bought": DUTY_FC,
    "all": ALL,
    "islanded": M.Assets(grid=False, wind=True, solar=True, battery=True,
                         electrolyser=True, tank=True, fuel_cell=True,
                         grid_limit_mw=0.0),
}


@pytest.mark.parametrize("objective", ["cost", "gwp"])
@pytest.mark.parametrize("name", list(PARITY))
def test_myopic_scores_the_lp_dispatch_exactly(series, tech, name, objective):
    # Feed the LP's own dispatch to the myopic scorer. Any difference would be
    # a term one side has and the other lacks — which is how myopic drifted
    # (no grid connection carbon, no bought hydrogen) before both read
    # objective_terms.
    from dataclasses import replace
    from optimisation import myopic, network_charges as nc
    # The winter-peak charge on, so the parity covers it (the fixture is January).
    t = replace(tech, batt_leakage_per_hour=2e-5, tank_leakage_per_hour=4e-6,
                cost_grid_per_mw_year=tech.cost_grid_per_mw_year - 7_405.0,
                cost_grid_triad_per_mw_year=7_405.0)
    s = replace(series, triad_window=nc.triad_window(series.index))
    assets = PARITY[name]
    V, obj = _solve(s, t, assets, objective=objective, unserved_fraction=0.01)
    q = M.solution_quantities(V)
    caps = {k: q[k] for k in myopic.CAPACITIES}
    df = pd.DataFrame({k: q[k] for k in myopic.FLOWS}, index=s.index)
    got = myopic.evaluate(df, s, t, caps, grid=assets.grid)
    lp = M.totals(obj)
    # The LP's unit counts sit on max(calendar, duty) only at an optimum where
    # they carry a positive price, which both objectives give them.
    assert got["cost_GBP_per_year"] == pytest.approx(lp["cost_GBP_per_year"], rel=1e-6)
    assert got["gwp_kgco2e_per_year"] == pytest.approx(lp["gwp_kgco2e_per_year"], rel=1e-6)


# =============================================================================
# The national grid's location charge falls on winter-evening demand (Triads)
# =============================================================================
def _triad(series, tech, tariff=7_405.0):
    """The fixture's 7,405 GBP/MW/yr locational tariff moved off cap_grid and
    onto winter-evening demand, charged at ``tariff``."""
    from dataclasses import replace
    from optimisation import network_charges as nc
    return (replace(series, triad_window=nc.triad_window(series.index)),
            replace(tech, cost_grid_per_mw_year=tech.cost_grid_per_mw_year - 7_405.0,
                    cost_grid_triad_per_mw_year=tariff))


def test_a_flat_grid_only_site_pays_the_same_either_way(series, tech):
    """Flat load, no storage: winter-evening demand is the connection, so moving
    the charge off cap_grid changes nothing."""
    s, t = _triad(series, tech)
    grid_only = M.Assets(grid=True)
    _, before = _solve(series, tech, grid_only, objective="cost")
    _, after = _solve(s, t, grid_only, objective="cost")
    assert M.totals(after)["cost_GBP_per_year"] == pytest.approx(
        M.totals(before)["cost_GBP_per_year"], rel=1e-9)


def test_a_battery_can_cut_winter_evening_demand(series, tech):
    """With a large winter-peak tariff, a battery covers the evening window and
    the site is charged on less than its peak import."""
    s, t = _triad(series, tech, tariff=400_000.0)
    V, _ = _solve(s, t, M.Assets(grid=True, battery=True), objective="cost")
    imp = V["imp"].solution.values
    window = s.triad_window
    assert float(V["triad_mw"].solution) == pytest.approx(imp[window].max(), rel=1e-6)
    assert imp[window].max() < imp.max() - 1e-3
    assert float(V["triad_mw"].solution) < float(V["cap_grid"].solution) - 1e-3


def test_an_islanded_build_has_no_winter_peak_demand(series, tech):
    s, t = _triad(series, tech)
    a = M.Assets(grid=False, wind=True, solar=True, battery=True, grid_limit_mw=0.0)
    V, _ = _solve(s, t, a, objective="cost", unserved_fraction=1.0)
    assert float(V["triad_mw"].solution) == 0.0


def test_resampling_keeps_the_window():
    """An hour is in the window if either of its half-hours is."""
    from optimisation import dc_inputs as I, network_charges as nc
    idx = pd.date_range("2025-01-06", periods=48, freq="30min")      # a Monday
    s = M.Series(index=idx, dt_hours=0.5, demand_mw=np.ones(48), cf_wind=np.zeros(48),
                 cf_solar=np.zeros(48), grid_gwp_per_mwh=np.ones(48),
                 grid_price_per_mwh=np.ones(48), triad_window=nc.triad_window(idx))
    r = I.resample(s, 1.0)
    # the window is 16:30-18:30, so the hours starting 16:00, 17:00 and 18:00
    assert list(r.index[r.triad_window].hour) == [16, 17, 18]


@pytest.mark.parametrize("name", list(PARITY))
def test_contributions_add_up_to_the_totals(series, tech, name):
    V, obj = _solve(series, tech, PARITY[name], objective="cost")
    c = M.contributions(V, obj, series, tech, PARITY[name])
    gwp = sum(sum(c[g].values()) for g in ("gwp_embodied", "gwp_operational", "gwp_facility"))
    cost = sum(sum(c[g].values()) for g in ("cost_capital", "cost_operational"))
    assert gwp == pytest.approx(c["totals"]["gwp_kgco2e_per_year"], rel=1e-9)
    assert cost == pytest.approx(c["totals"]["cost_GBP_per_year"], rel=1e-9)


def test_myopic_buys_hydrogen_when_the_build_may(series, tech):
    from optimisation import myopic
    caps = {"cap_fc": 5.0, "cap_grid": 0.0}
    df = myopic.dispatch(series, tech, caps, buy_h2=True)
    assert df.unserved.sum() < 1e-9 * series.n or df.h2_buy.sum() > 0
    assert df.h2_buy.sum() == pytest.approx(
        (df.p_fc * tech.fc_kg_h2_per_mwh * DT).sum() - 0.0, rel=1e-9)


# =============================================================================
# Unserved load and leaked hydrogen in the carbon objective (CARBON_PLAN 2.1-2.2)
# =============================================================================
def test_carbon_voll_is_voll_at_the_study_carbon_price():
    from optimisation import h2_prices
    assert M.VOLL_CARBON_PRICE_GBP_PER_T == pytest.approx(
        h2_prices.carbon_gbp_per_t(2025), rel=1e-4)
    assert M.VOLL_KGCO2E_PER_MWH == pytest.approx(
        M.VOLL_GBP_PER_MWH / M.VOLL_CARBON_PRICE_GBP_PER_T * 1000.0)


@pytest.mark.parametrize("assets", [ALL, M.Assets(grid=True)], ids=["all", "grid_only"])
def test_min_gwp_does_not_shed_load_to_cut_carbon(series, tech, assets):
    # Before 14 Oct unserved load was carbon-free, so a min-GWP solve with an
    # allowance used every MWh of it, in the dirtiest hours.
    V, _ = _solve(series, tech, assets, objective="gwp", unserved_fraction=0.01)
    assert V["unserved"].solution.values.sum() * DT < 1e-6


def test_intensities_divide_by_served_demand_without_the_penalties():
    r = M.intensities(cost=2e6 + M.VOLL_GBP_PER_MWH * 10, gwp=5e5 + M.VOLL_KGCO2E_PER_MWH * 10,
                      unserved_mwh=10.0, demand_mwh=1010.0)
    assert r["served_MWh_per_year"] == 1000.0
    assert r["cost_GBP_per_MWh"] == pytest.approx(2000.0)
    assert r["gwp_g_per_kWh"] == pytest.approx(500.0)


def test_leaked_hydrogen_is_charged_at_its_gwp(series, tech):
    # Scored on a hand-made dispatch: the synthetic LP has no reason to hold
    # hydrogen, and the parity tests already prove the LP sums these terms.
    from dataclasses import replace
    from optimisation import myopic
    leak = 4e-6
    t = replace(tech, tank_leakage_per_hour=leak)
    q = {k: 0.0 for k in myopic.CAPACITIES}
    q.update({k: np.zeros(series.n) for k in myopic.FLOWS})
    q["fc_bop_units"] = q["fc_stack_units"] = 0.0
    q["tank"] = np.full(series.n, 1_000.0)          # 1 t held all window
    got = M.score(q, series, t)["gwp_operational"]["H2 leaked from tank"]
    kg_leaked = series.annual_scale * leak * DT * 1_000.0 * series.n
    assert got == pytest.approx(kg_leaked * M.H2_GWP100, rel=1e-12)
    assert M.score(q, series, tech)["gwp_operational"]["H2 leaked from tank"] == 0.0


# =============================================================================
# Transformer conversion losses (CARBON_PLAN 2.3)
# =============================================================================
def _lossy(tech):
    from dataclasses import replace
    from optimisation import conversion_losses as cl
    w, s, g = cl.stepup("onshore_wind"), cl.stepup("solar_pv"), cl.grid_intake()
    b, f = cl.container_stepup("battery"), cl.container_stepup("fuel_cell")
    return replace(tech, loss_wind_noload=w["noload_mw_per_mw"],
                   loss_wind_load_at_full=w["load_loss_per_mw_at_full_loading"],
                   loss_solar_noload=s["noload_mw_per_mw"],
                   loss_solar_load_at_full=s["load_loss_per_mw_at_full_loading"],
                   loss_grid_noload=g["noload_mw_per_mw"],
                   loss_grid_load=g["load_loss_fraction"],
                   loss_batt_noload=b["noload_mw_per_mw"], loss_batt_load=b["load_loss_fraction"],
                   loss_fc_noload=f["noload_mw_per_mw"], loss_fc_load=f["load_loss_fraction"])


def test_losses_close_the_balance_and_bind_availability(series, tech):
    t = _lossy(tech)
    V, _ = _solve(series, t, ALL, objective="gwp")
    g = lambda k: V[k].solution.values
    c = lambda k: float(V[k].solution)
    lf = M.loss_factors(series, t)
    assert 0 < lf["wind"] < 0.01 and 0 < lf["solar"] < 0.01 and 0 < lf["grid"] < 0.01
    assert 0 < lf["battery"] < 0.01 and 0 < lf["fc"] < 0.01
    noload = (t.loss_wind_noload * (c("cap_wind") + c("cap_offshore"))
              + t.loss_solar_noload * c("cap_solar") + t.loss_grid_noload * c("cap_grid")
              + t.loss_batt_noload * c("cap_batt_p") + t.loss_fc_noload * c("cap_fc"))
    residual = (g("p_wind") + g("p_solar") + (1 - lf["battery"]) * g("dis") + (1 - lf["fc"]) * g("p_fc")
                + (1 - lf["grid"]) * g("imp") + g("unserved") - g("ch") / (1 - lf["battery"]) - g("p_ely")
                - noload - series.demand_mw)
    assert np.abs(residual).max() < 1e-6
    assert (g("p_wind") <= (1 - lf["wind"]) * series.cf_wind * c("cap_wind") + 1e-6).all()


@pytest.mark.parametrize("objective", ["cost", "gwp"])
def test_losses_make_every_build_dearer_and_dirtier(series, tech, objective):
    _, lossless = _solve(series, tech, ALL, objective=objective)
    _, lossy = _solve(series, _lossy(tech), ALL, objective=objective)
    key = {"cost": "cost_GBP_per_year", "gwp": "gwp_kgco2e_per_year"}[objective]
    a, b = M.totals(lossless)[key], M.totals(lossy)[key]
    assert a < b < a * 1.02          # real, and under a couple of per cent


def test_myopic_dispatch_balances_with_losses(series, tech):
    from optimisation import myopic
    t = _lossy(tech)
    caps = {"cap_wind": 10.0, "cap_solar": 5.0, "cap_batt_p": 2.0, "cap_batt_e": 8.0,
            "cap_ely": 1.0, "cap_tank": 60.0, "cap_fc": 1.0, "cap_grid": 8.0}
    df = myopic.dispatch(series, t, caps)    # raises if the balance breaks
    assert df.unserved.sum() < 1e-9
    assert df.dis.sum() > 0 and df.p_fc.sum() > 0, "nothing passed through the container step-ups"


def test_container_step_ups_are_charged_on_inverter_capacity(series, tech):
    """The battery's and fuel cell's LV → 20 kV units: per MW of cap_batt_p and
    cap_fc, annual, not scaled by the window, and inside their chains."""
    import dataclasses
    t = dataclasses.replace(tech, gwp_tx_batt_per_mw=800.0, gwp_tx_fc_per_mw=600.0)
    q = {k: 0.0 for k in ("cap_wind", "cap_offshore", "cap_solar", "cap_batt_e", "cap_ely",
                          "cap_tank", "fc_stack_units", "fc_bop_units", "cap_grid")}
    q.update(cap_batt_p=3.0, cap_fc=2.5)
    for k in ("imp", "h2_buy", "h2_buy_2", "p_ely", "p_fc", "unserved", "tank", "exp"):
        q[k] = np.zeros(series.n)
    e = M.score(q, series, t)["gwp_embodied"]
    assert e["battery step-up transformers"] == pytest.approx(800.0 * 3.0)
    assert e["fuel cell step-up transformers"] == pytest.approx(600.0 * 2.5)
    assert M.score(q, series, tech)["gwp_embodied"]["battery step-up transformers"] == 0.0
    ch = M.chains(M.score(q, series, t), "gwp")
    assert "battery step-up transformers" in ch["battery"]
    assert "fuel cell step-up transformers" in ch["fuel cell"]



def test_chains_cover_every_term_and_sum_to_the_totals(series, tech):
    # The by-technology view regroups the flat terms; nothing may be left
    # outside it, and nothing may be counted twice.
    V, obj = _solve(series, tech, ALL, objective="cost")
    c = M.contributions(V, obj, series, tech, ALL)
    flat = sum(sum(c[g].values()) for g in ("gwp_embodied", "gwp_operational", "gwp_facility"))
    assert sum(sum(d.values()) for d in c["gwp_chains"].values()) == pytest.approx(flat, rel=1e-12)
    flat_c = sum(sum(c[g].values()) for g in ("cost_capital", "cost_operational"))
    assert sum(sum(d.values()) for d in c["cost_chains"].values()) == pytest.approx(flat_c, rel=1e-12)
    # the wind chain holds the turbine and its step-up, nothing else
    assert set(c["gwp_chains"]["wind"]) == {"wind", "offshore wind", "wind step-up transformers"}
    with pytest.raises(KeyError):
        M.chains({"gwp_embodied": {"a new term": 1.0}}, "gwp")


# =============================================================================
# Electrolyser stacks: max(calendar, duty), as the fuel cell (user, 26 Oct 2026)
# =============================================================================
ELY_STACK = dict(gwp_ely=3_257.3, gwp_ely_stack_per_mw=138_248.0,
                 ely_stack_calendar_years=25.0 / 3.0, ely_stack_duty_hours=50_000.0)
ELY_ASSETS = M.Assets(grid=True, electrolyser=True, tank=True, fuel_cell=True, grid_limit_mw=None)


def _solve_ely(series, tech, strategy, objective="gwp"):
    from dataclasses import replace
    t = replace(tech, **ELY_STACK)
    m, V, obj = M.build_model(series, ELY_ASSETS, t, objective=objective, ely_strategy=strategy)
    m.add_constraints(V["cap_ely"] >= 1.0, name="force_ely")
    M.solve(m)
    return V, t


@pytest.mark.parametrize("strategy, binding", [("baseload", "duty"), ("free", "calendar")])
def test_electrolyser_stack_units_take_the_binding_limit(series, tech, strategy, binding):
    V, t = _solve_ely(series, tech, strategy)
    cap = float(V["cap_ely"].solution)
    mwh = V["p_ely"].solution.values.sum() * DT * series.annual_scale
    u = float(V["ely_stack_units"].solution)
    calendar, duty = cap / t.ely_stack_calendar_years, mwh / t.ely_stack_duty_hours
    assert u == pytest.approx(max(calendar, duty), rel=1e-6)
    assert (duty > calendar) == (binding == "duty")


def test_electrolyser_calendar_floor_is_the_old_whole_unit_charge(series, tech):
    """Below ~68 % utilisation the split charges exactly the unit over 25 years, as before."""
    V, t = _solve_ely(series, tech, "free")
    cap = float(V["cap_ely"].solution)
    q = M.solution_quantities(V)
    terms = M.score(q, series, t)["gwp_embodied"]
    whole = (t.gwp_ely + t.gwp_ely_stack_per_mw / t.ely_stack_calendar_years) * cap
    assert terms["electrolyser"] + terms["electrolyser stack replacements"] == pytest.approx(whole, rel=1e-6)
    assert t.gwp_ely + t.gwp_ely_stack_per_mw * 3 / 25.0 == pytest.approx(19_847.1, rel=1e-4)


def test_baseload_electrolyser_pays_for_its_extra_stacks(series, tech):
    """At the 85 % floor a 50,000 h stack is replaced 3.72 times in 25 years, not 3."""
    V, t = _solve_ely(series, tech, "baseload")
    cap = float(V["cap_ely"].solution)
    u = float(V["ely_stack_units"].solution)
    assert u * 25.0 / cap >= 0.85 * 8760 * 25 / 50_000 - 1e-6
    assert u * 25.0 / cap > 3.0
