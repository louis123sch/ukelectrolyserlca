"""The optimiser chooses the price list (COST_PLAN §1.11, 30 Oct 2026).

Toy series and hand-built options, so the answer is known before the solve:
exactly one switch on, the connection inside the chosen option's range,
imports in the chosen voltage group only, and a single option reproducing the
single-price-list model to the pound. The real option table (register,
charges) is tested in test_connection_options.py.
"""
from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from optimisation import dc_model as M              # noqa: E402
from optimisation import dc_pareto as P             # noqa: E402

pytest.importorskip("linopy")

DT, N = 1.0, 7 * 24          # a week, hourly


def _series(demand=7.31, groups=None):
    rng = np.random.default_rng(3)
    idx = pd.date_range("2025-06-02", periods=N, freq="h")
    hours = np.arange(N) * DT
    price = 95 + 40 * np.sin(hours / 13) + 10 * rng.standard_normal(N)
    ci = 250 + 120 * np.sin(hours / 11) + 20 * rng.standard_normal(N)
    return M.Series(
        index=idx, dt_hours=DT, demand_mw=np.full(N, demand),
        cf_wind=np.clip(0.35 + 0.3 * np.sin(hours / 37) + 0.1 * rng.standard_normal(N), 0, 1),
        cf_solar=np.clip(0.5 * np.sin(np.pi * ((hours % 24) - 6) / 12), 0, 1),
        grid_gwp_per_mwh=ci, grid_price_per_mwh=price,
        grid_groups=groups and {g: {"price_per_mwh": price * f, "gwp_per_mwh": ci * c}
                                for g, (f, c) in groups.items()},
    )


def _tech(**kw):
    base = dict(
        gwp_wind=19_244, gwp_offshore=26_408, gwp_solar=23_561, gwp_batt_p=2_124, gwp_batt_e=7_241,
        gwp_ely=10_435, gwp_tank=63.8, gwp_fc_bop_per_mw=44_325, gwp_fc_stack_per_mw=97_431,
        gwp_fc_maint_per_mwh=0.0032, gwp_grid_per_mw=137.7,
        cost_fc_stack_per_mw=308_698.0, cost_fc_bop_per_mw=1_486_089.0,
        fc_bop_calendar_years=20.0, fc_bop_duty_hours=80_000.0,
        fc_stack_calendar_years=10.0, fc_stack_duty_hours=30_000.0,
        cost_wind=147_073, cost_offshore=419_201, cost_solar=48_368,
        cost_batt_p=34_903, cost_batt_e=11_634, cost_ely=212_511, cost_tank=64.6, cost_fc=99_842,
        cost_grid_per_mw_year=40_949, cost_grid_fixed_per_year=271_192,
        ely_kwh_per_kg=54.0, ely_variable_gwp_per_kg=0.1072, tank_compression_kwh_per_kg=0.0,
        tank_leakage_per_hour=0.0, batt_rte=0.88, batt_leakage_per_hour=0.0, fc_kg_h2_per_mwh=63.164,
        bought_h2_gbp_per_kg=3.0, bought_h2_gwp_per_kg=10.0,
        dc_fixed_gwp_per_year=999_453, dc_other_gwp_per_mwh=1.809, horizon_years=25.0,
    )
    base.update(kw)
    return M.Tech(**base)


def _opt(key, group, floor, ceiling, per_mw, fixed, gwp=137.7, **info):
    return M.ConnectionOption(key=key, group=group, floor_mw=floor, ceiling_mw=ceiling,
                              cost_per_mw_year=per_mw, cost_fixed_per_year=fixed,
                              gwp_per_mw_year=gwp, info=info)


# A cheap small option (an 11 kV one) and a dear large one (33 kV), on two
# import series: the 33 kV one buys 2 % cheaper energy, 1 % cleaner.
SMALL = _opt("small", "11 kV", 0.0, 5.0, 10_000.0, 100_000.0, tier="local network", band="HV4")
LARGE = _opt("large", "33 kV", 5.001, 20.0, 50_000.0, 500_000.0, tier="local network", band="EHV2")
GROUPS = {"11 kV": (1.0, 1.0), "33 kV": (0.98, 0.99)}


def _solve(series, tech, assets, **kw):
    m, V, obj = M.build_model(series, assets, tech, **kw)
    M.solve(m)
    return V, obj


def test_exactly_one_switch_is_on_and_the_connection_sits_inside_it():
    s = _series(7.31, GROUPS)
    t = _tech(connection_options=(SMALL, LARGE))
    V, obj = _solve(s, t, M.Assets(grid=True), objective="cost")
    on = [float(V[f"on_{i}"].solution) for i in range(2)]
    assert sum(on) == pytest.approx(1.0) and on[1] == pytest.approx(1.0)      # 7.31 MW does not fit the small one
    cap = float(V["cap_grid"].solution)
    assert LARGE.floor_mw - 1e-6 <= cap <= LARGE.ceiling_mw + 1e-6
    assert float(V["cap_conn_0"].solution) == pytest.approx(0.0, abs=1e-6)
    assert float(V["cap_conn_1"].solution) == pytest.approx(cap, rel=1e-6)
    # imports flow through the chosen group only, and add up to imp
    imp33 = V[M.group_import_var("33 kV")].solution.values
    imp11 = V[M.group_import_var("11 kV")].solution.values
    assert np.allclose(imp11, 0.0, atol=1e-6) and np.allclose(imp33, V["imp"].solution.values, atol=1e-6)
    st = M.connection_status(V, obj["options"])
    assert st["key"] == "large" and st["band"] == "EHV2"


def test_a_small_load_takes_the_cheap_small_option():
    s = _series(4.0, GROUPS)
    t = _tech(connection_options=(SMALL, LARGE))
    V, obj = _solve(s, t, M.Assets(grid=True), objective="cost")
    assert M.connection_status(V, obj["options"])["key"] == "small"


def test_with_a_battery_the_model_may_shrink_into_the_cheaper_option():
    """7.31 MW flat with a battery allowed: the small option caps imports at 5 MW,
    which no battery can bridge on a flat load (it would have to charge from
    the same 5 MW), so the large one is still chosen — but a cheaper, lower
    fixed charge must win where the range allows it."""
    s = _series(6.0, GROUPS)
    cheap_large = replace(LARGE, cost_fixed_per_year=50_000.0, cost_per_mw_year=5_000.0)
    t = _tech(connection_options=(SMALL, cheap_large))
    V, obj = _solve(s, t, M.Assets(grid=True, battery=True), objective="cost")
    assert M.connection_status(V, obj["options"])["key"] == "large"


def test_a_single_option_reproduces_the_single_price_list_model():
    """One option whose charges are the Tech's scalar ones, on the same series:
    the two models must agree to solver tolerance on cost, carbon and build."""
    s1 = _series(7.31)
    t1 = _tech()
    a1 = M.Assets(grid=True, wind=True, solar=True, battery=True, grid_limit_mw=10.45, grid_floor_mw=2.001)
    V1, o1 = _solve(s1, t1, a1, objective="cost")
    one = _opt("only", "11 kV", 2.001, 10.45, t1.cost_grid_per_mw_year, t1.cost_grid_fixed_per_year,
               gwp=t1.gwp_grid_per_mw)
    s2 = _series(7.31, {"11 kV": (1.0, 1.0)})
    t2 = _tech(connection_options=(one,))
    V2, o2 = _solve(s2, t2, M.Assets(grid=True, wind=True, solar=True, battery=True), objective="cost")
    tot1, tot2 = M.totals(o1), M.totals(o2)
    assert tot2["cost_GBP_per_year"] == pytest.approx(tot1["cost_GBP_per_year"], rel=1e-6)
    assert tot2["gwp_kgco2e_per_year"] == pytest.approx(tot1["gwp_kgco2e_per_year"], rel=1e-5)
    assert float(V2["cap_grid"].solution) == pytest.approx(float(V1["cap_grid"].solution), rel=1e-4)
    # the fixed charge moved from the constant to a term, and the totals still agree
    assert o1["cost_const"] == t1.cost_grid_fixed_per_year and o2["cost_const"] == 0.0
    c2 = M.contributions(V2, o2, s2, t2, M.Assets(grid=True, wind=True, solar=True, battery=True))
    assert c2["cost_capital"]["grid connection fixed charges"] == pytest.approx(t1.cost_grid_fixed_per_year)
    assert c2["connection"]["key"] == "only"


def test_contributions_and_chains_add_up_with_options():
    s = _series(7.31, GROUPS)
    t = _tech(connection_options=(SMALL, LARGE))
    a = M.Assets(grid=True, wind=True, solar=True, battery=True)
    V, obj = _solve(s, t, a, objective="cost")
    c = M.contributions(V, obj, s, t, a)
    tot = c["totals"]
    cost = sum(c["cost_capital"].values()) + sum(c["cost_operational"].values())
    gwp = sum(c["gwp_embodied"].values()) + sum(c["gwp_operational"].values()) + sum(c["gwp_facility"].values())
    assert cost == pytest.approx(tot["cost_GBP_per_year"], rel=1e-6)
    assert gwp == pytest.approx(tot["gwp_kgco2e_per_year"], rel=1e-6)
    assert "grid connection fixed charges" in c["cost_chains"]["grid"]


def test_the_frontier_reports_the_option_chosen_at_every_point():
    s = _series(7.31, GROUPS)
    t = _tech(connection_options=(SMALL, LARGE))
    r = P.front(s, M.Assets(grid=True, wind=True, solar=True, battery=True), t, points=3)
    for name in ("min_cost", "min_gwp", "knee"):
        assert r[name]["connection_option"] in ("small", "large")
        assert r[name]["connection_floor_mw"] - 1e-6 <= r[name]["cap_grid"] <= r[name]["connection_ceiling_mw"] + 1e-6
    assert "connection_option" in r["front"].columns


def test_options_need_a_finite_ceiling_and_matching_groups():
    s = _series(7.31, GROUPS)
    bad = _opt("open", "33 kV", 0.0, float("inf"), 1.0, 1.0)
    with pytest.raises(ValueError, match="finite ceiling"):
        M.build_model(s, M.Assets(grid=True), _tech(connection_options=(bad,)))
    orphan = _opt("orphan", "132 kV", 0.0, 10.0, 1.0, 1.0)
    with pytest.raises(ValueError, match="voltage groups"):
        M.build_model(s, M.Assets(grid=True), _tech(connection_options=(orphan,)))
    with pytest.raises(ValueError, match="grid_groups"):
        M.build_model(_series(7.31), M.Assets(grid=True), _tech(connection_options=(SMALL,)))


def test_an_islanded_build_ignores_the_options():
    s = _series(7.31, GROUPS)
    t = _tech(connection_options=(SMALL, LARGE))
    a = M.Assets(grid=False, wind=True, solar=True, battery=True, grid_limit_mw=0.0)
    m, V, obj = M.build_model(s, a, t, objective="cost", unserved_fraction=1.0)
    assert obj["options"] is None and "on_0" not in V


def test_the_price_spread_threshold_moves_a_site_with_options():
    """A wider spread must reach the series the objective reads: it pays a battery
    to arbitrage, so the best cost falls. It used to stay put to the pound."""
    from optimisation import thresholds as T
    s = _series(7.31, GROUPS)
    t = _tech(connection_options=(SMALL, LARGE))
    a = M.Assets(grid=True, battery=True)
    cost = {}
    for k in (1.0, 4.0):
        t_k, s_k = T.apply(T.KNOBS["price_spread"], k, t, s)
        V, obj = _solve(s_k, t_k, a, objective="cost")
        cost[k] = M.totals(obj)["cost_GBP_per_year"]
    assert cost[4.0] < 0.999 * cost[1.0]
