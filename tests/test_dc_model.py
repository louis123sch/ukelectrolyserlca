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
    return M.Tech(
        gwp_wind=18_800, gwp_offshore=25_400, gwp_solar=60_600,
        gwp_batt_p=2_124, gwp_batt_e=6_547,
        gwp_ely=10_433, gwp_tank=63.8,
        gwp_fc_bop_per_mw=469_040, gwp_fc_stack_per_mw=97_431,
        gwp_fc_maint_per_mwh=3.11,
        gwp_grid_per_mw=333.5,
        cost_fc_stack_per_mw=308_698.0,
        fc_bop_calendar_years=25.0, fc_bop_duty_hours=60_000.0,
        fc_stack_duty_hours=32_000.0,
        cost_wind=150_000, cost_offshore=230_000, cost_solar=95_000,
        cost_batt_p=30_000, cost_batt_e=10_000,
        cost_ely=220_000, cost_tank=64.6, cost_fc=194_244,
        cost_grid_per_mw_year=40_949, cost_grid_fixed_per_year=271_192,
        ely_kwh_per_kg=54.0, ely_variable_gwp_per_kg=0.1072,
        tank_compression_kwh_per_kg=0.0, tank_leakage_per_hour=0.0,
        batt_rte=0.88, batt_leakage_per_hour=0.0,
        fc_kg_h2_per_mwh=63.164,
        bought_h2_gbp_per_kg=3.0, bought_h2_gwp_per_kg=10.0,
        dc_fixed_gwp_per_year=841_457, dc_other_gwp_per_mwh=0.0,
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
    assert tot["gwp_const_kgco2e_per_year"] == tech.dc_fixed_gwp_per_year
    assert tot["cost_GBP_per_year"] > float(obj["cost"].solution)


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
    V, _ = _solve(series, tech, a, objective="cost", ely_strategy="baseload")
    cap = float(V["cap_ely"].solution)
    if cap < 1e-6:
        pytest.skip("optimiser declined to build an electrolyser at all")
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
def test_fuel_cell_replacement_counts_take_the_binding_limit(series, tech):
    a = M.Assets(grid=True, fuel_cell=True, buy_h2=True, grid_limit_mw=None)
    V, _ = _solve(series, tech, a, objective="gwp")
    cap = float(V["cap_fc"].solution)
    if cap < 1e-6:
        pytest.skip("no fuel cell built")
    mwh = V["p_fc"].solution.values.sum() * DT * series.annual_scale
    for units, calendar, duty in (
            (V["fc_bop_units"], tech.fc_bop_calendar_years, tech.fc_bop_duty_hours),
            (V["fc_stack_units"], tech.horizon_years, tech.fc_stack_duty_hours)):
        u = float(units.solution)
        assert u >= cap / calendar - 1e-6
        assert u >= mwh / duty - 1e-6
        assert u == pytest.approx(max(cap / calendar, mwh / duty), rel=1e-6)


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
