"""The fixes from the REopt comparison (20 Nov 2026; Claude outputs/reopt_cost_comparison.md).

1. Solar's cost per MWh sees the discount-weighted ageing (profiles.solar_discounted_ageing_factor).
2. An islanded build holds spare power in every step (dc_model build_model (10b)).
3. The solar array's other losses are a series knob (dc_inputs.build_series(pv_system_loss=)).
4. Each Pareto point reports its battery's solved cycles beside the oversizing's assumed 180.
5. The carbon-price point does not price the engines' burned CO2 twice.

Only toy models are solved here (a few days, hourly), as in test_connection_choice.
"""
from __future__ import annotations

import inspect
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from optimisation import dc_model as M              # noqa: E402
from optimisation import dc_pareto as P             # noqa: E402
from optimisation import profiles                    # noqa: E402

pytest.importorskip("linopy")
from test_connection_choice import _tech            # noqa: E402

DT, N = 1.0, 3 * 24


def _series(demand=10.0):
    hours = np.arange(N) * DT
    idx = pd.date_range("2025-01-06", periods=N, freq="h")
    return M.Series(index=idx, dt_hours=DT, demand_mw=np.full(N, demand),
                    cf_wind=np.clip(0.4 + 0.35 * np.sin(hours / 9), 0, 1),
                    cf_solar=np.clip(0.5 * np.sin(np.pi * ((hours % 24) - 6) / 12), 0, 1),
                    grid_gwp_per_mwh=np.full(N, 200.0), grid_price_per_mwh=np.full(N, 90.0))


ISLAND = M.Assets(grid=False, wind=True, solar=True, battery=True, gas_engine=True)
RESERVE = dict(reserve_load_fraction=0.10, reserve_wind_fraction=0.50, reserve_solar_fraction=0.25)


# --- 1. solar ageing on the cost side -----------------------------------------
def test_discounted_ageing_factor():
    plain = profiles.SOLAR_LIFE_AVERAGE_FACTOR
    assert plain == pytest.approx(0.8705)
    disc = profiles.solar_discounted_ageing_factor(plain, 0.076)
    assert disc == pytest.approx(0.92542, abs=1e-4)
    # the discounted mean is above the plain one and falls toward it as the rate falls
    assert profiles.solar_discounted_ageing_factor(plain, 0.0) == pytest.approx(plain)
    assert plain < profiles.solar_discounted_ageing_factor(plain, 0.05) < disc
    # no ageing in the series, no correction
    assert profiles.solar_discounted_ageing_factor(1.0, 0.076) == 1.0


def test_build_tech_scales_solar_cost_by_plain_over_discounted():
    from optimisation import dc_inputs as I
    src = inspect.getsource(I.build_tech)
    assert "solar_discounted_ageing_factor" in src
    assert "solar_cost * to26 * solar_age_corr" in src


# --- 2. spare power off grid ----------------------------------------------------
def _names(m):
    return set(m.constraints)


def test_reserve_only_off_grid_and_only_when_asked():
    s = _series()
    m, _, _ = M.build_model(s, ISLAND, _tech(**RESERVE), objective="cost")
    assert {"reserve_battery_power", "reserve_battery_energy"} <= _names(m)
    m, _, _ = M.build_model(s, ISLAND, _tech(), objective="cost")          # fractions default to zero
    assert not {"reserve_battery_power", "reserve_battery_energy"} & _names(m)
    m, _, _ = M.build_model(s, M.Assets(grid=True, wind=True, battery=True), _tech(**RESERVE), objective="cost")
    assert not {"reserve_battery_power", "reserve_battery_energy"} & _names(m)


def _sol(V, k):
    v = V[k].solution
    return np.asarray(v, dtype=float) if v.ndim else float(v)


def test_reserve_is_held_in_every_step_and_costs_something():
    s = _series()
    m0, V0, o0 = M.build_model(s, ISLAND, _tech(), objective="cost")
    M.solve(m0)
    t = _tech(**RESERVE)
    m1, V1, o1 = M.build_model(s, ISLAND, t, objective="cost")
    M.solve(m1)
    assert M.totals(o1)["cost_GBP_per_year"] >= M.totals(o0)["cost_GBP_per_year"] - 1e-6

    lf = M.loss_factors(s, t)
    eta = np.sqrt(t.batt_rte)
    g = {k: _sol(V1, k) for k in ("cap_ge", "p_ge", "cap_wind", "p_wind", "cap_solar", "p_solar",
                                  "cap_batt_p", "dis", "ch", "soc", "cap_fc", "p_fc", "p_ely")}
    spill_w = (1 - lf["wind"]) * s.cf_wind * g["cap_wind"] - g["p_wind"]
    spill_s = (1 - lf["solar"]) * s.cf_solar * g["cap_solar"] - g["p_solar"]
    keep = 1 - lf["battery"]
    batt = np.minimum(keep * (g["cap_batt_p"] - g["dis"]), keep * (eta * g["soc"] / t.reserve_battery_hours - g["dis"]))
    provided = ((1 - lf["fc"]) * (g["cap_fc"] - g["p_fc"]) + (g["cap_ge"] - g["p_ge"]) + g["p_ely"]
                + 0.5 * spill_w + 0.75 * spill_s + g["ch"] / keep + batt)
    required = 0.10 * s.demand_mw + 0.50 * g["p_wind"] + 0.25 * g["p_solar"]
    assert np.all(provided >= required - 1e-5)


# --- 3. solar losses as a series knob --------------------------------------------
def test_pv_system_loss_is_a_series_knob():
    from optimisation import dc_inputs as I
    from optimisation import sensitivity as S
    assert "pv_system_loss" in inspect.signature(I.build_series).parameters
    assert "pv_system_loss" in S.SERIES_KNOBS
    assert S.SHAKY_KNOBS["pv_system_loss"] == [0.05, 0.15]


def test_reserve_pushes_dropped_on_grid_cases():
    from optimisation import sensitivity as S
    pushes = {p for v in S.shaky_variants(S.CASES["norfolk_grid_green"]) for p in [v.get("push", "")]}
    assert not any(p.startswith("reserve.") for p in pushes)
    pushes = {v.get("push", "") for v in S.shaky_variants(S.CASES["islanded_h2"])}
    assert {"reserve.load_fraction*0.5", "reserve.wind_fraction*1.5"} <= pushes


# --- 4. battery cycles reported -------------------------------------------------
def test_battery_cycles_column():
    from optimisation import battery
    out = P._battery_cycles({"cap_batt_e": 100.0, "cap_batt_p_MWh_per_year": 18_000.0})
    assert out["batt_cycles_per_year"] == pytest.approx(180.0)
    assert out["batt_cycles_assumed"] == battery.CYCLES_PER_YEAR_IN_USE
    assert np.isnan(P._battery_cycles({"cap_batt_e": 0.0, "cap_batt_p_MWh_per_year": 0.0})["batt_cycles_per_year"])


# --- 5. carbon-price point --------------------------------------------------------
def test_carbon_price_point_does_not_price_engine_co2_twice():
    lam = P._carbon_price_gbp_per_kg()
    # B and C differ only in that C's extra carbon is engine CO2 already priced in its cost
    df = pd.DataFrame({
        "cost_GBP_per_year": [100e6, 60e6, 50e6],
        "gwp_kgco2e_per_year": [0.0, 400e3 / lam, 500e3 / lam],
        "ge_co2_carbon_priced_kg_per_year": [0.0, 0.0, 450e3 / lam],
    })
    # pricing all of it: A 100, B 60.4, C 50.5 -> C; netting C's priced tonnes: C 50.05 -> C still,
    # so make C's cost sit between the two readings
    df.loc[2, "cost_GBP_per_year"] = 60.2e6
    with_net = P.special_points(df, degenerate=False)["carbon_price"]
    assert with_net["cost_GBP_per_year"] == pytest.approx(60.2e6)        # C: 60.2 + 0.05 < B: 60.4
    df_old = df.drop(columns="ge_co2_carbon_priced_kg_per_year")
    without = P.special_points(df_old, degenerate=False)["carbon_price"]
    assert without["cost_GBP_per_year"] == pytest.approx(60e6)            # B: 60.4 < C: 60.7
