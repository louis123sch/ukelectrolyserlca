"""The gas engines (13 Nov 2026, docs/GAS_ENGINE_PLAN.md).

What the earlier technology builds taught, held here:
* every government figure is pinned to the table it was read from;
* the inventory's carbon balance closes and its ecoinvent picks are exact identities;
* the scored total sits in a plausible band and agrees with DESNZ's 2026 conversion factors;
* every transport line is accounted for: the trips to site are taken back out, the upstream ones stay;
* the LP charges the same replacement physics in cost and carbon, and the engines are off by default;
* the levy-agreement switch cannot reach the engines' gas.
The Brightway tests skip where the project or the database is absent.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from optimisation import dc_architectures as A  # noqa: E402
from optimisation import dc_model as M  # noqa: E402
from optimisation import gas_engine as ge  # noqa: E402
from optimiser_lca import gas_engine as gl  # noqa: E402


# =============================================================================
# The government figures, as read (DESNZ 2026 unabated gas study, Option 5)
# =============================================================================
def test_desnz_2026_figures_are_the_tables():
    assert ge.CAPEX_GBP_PER_KW == {"low": 450.0, "central": 529.0, "high": 609.0}           # Table 3.25
    assert ge.DEV_EXCL_LAND_GBP_PER_KW["low"] == 8.9 and ge.DEV_EXCL_LAND_GBP_PER_KW["high"] == 12.2   # Table 5.4
    assert ge.DEV_EXCL_LAND_GBP_PER_KW["central"] == pytest.approx(10.55)                    # midpoint (user)
    assert ge.FIXED_FEE_GBP_PER_MW_YEAR == {"low": 12_400.0, "central": 14_630.0, "high": 16_820.0}   # Table 3.27
    assert ge.VARIABLE_500H_GBP_PER_MWH == {"low": 5.72, "central": 6.73, "high": 7.74}     # Table 3.27
    assert ge.VARIABLE_1500H_GBP_PER_MWH == {"low": 3.45, "central": 4.06, "high": 4.67}    # Table 3.28
    assert ge.INSURANCE_FRAC_OF_CAPITAL == {"low": 0.003, "central": 0.004, "high": 0.005}
    assert ge.BUILD_YEARS == {"low": 0.4, "central": 1.0, "high": 1.3}                       # Table 3.23
    assert ge.CALENDAR_YEARS == 25.0 and ge.PRICE_YEAR == 2024
    assert gl.GE_ETA_NET_LHV == 0.446                                                         # Table 3.24
    assert ge.DISCOUNT_RATE == 0.089                     # CEPA 2025 Table E.1, gas generation - unabated


@pytest.mark.parametrize("case", ge.CASES)
def test_the_variable_fee_split_reproduces_both_rows(case):
    fixed, per_mwh = ge.variable_fee_split(case)
    for hours, row in ((500.0, ge.VARIABLE_500H_GBP_PER_MWH), (1500.0, ge.VARIABLE_1500H_GBP_PER_MWH)):
        assert (fixed + per_mwh * hours) / hours == pytest.approx(row[case], rel=1e-12)
    assert fixed > 0 and per_mwh > 0


def test_cost_cases_are_ordered_and_the_annuity_nets_the_calendar_replacement():
    df = ge.costs().set_index("case")
    for col in ("capital_GBP_per_MW", "annual_GBP_per_MW_year", "maintenance_GBP_per_MWh"):
        assert df.loc["low", col] < df.loc["central", col] < df.loc["high", col]
    c = df.loc["central"]
    # at the calendar floor the LP's two capital terms give back the annuity with its build finance, plus opex
    from optimisation import tech_costs as tc
    annuity = c.capital_GBP_per_MW * tc.building_finance_factor(0.089, 1.0) * tc.capital_recovery_factor(0.089, 25.0)
    opex = c.annual_GBP_per_MW_year + c.capital_GBP_per_MW / 25.0 - annuity
    assert 16_000 < opex < 23_000            # fixed fee, the variable fee's fixed part, insurance and rates


def test_the_engines_gas_has_no_levy_and_the_agreement_switch_cannot_reach_it():
    from optimisation import dc_inputs as I, levies
    for case in ("low", "central", "high"):
        site = I.site_gas_gbp_per_mwh(ccl_under_cca=False, gas_price_case=case)
        assert I.engine_gas_gbp_per_mwh(case) == pytest.approx(site - levies.ccl_gas_gbp_per_mwh(False))
        site_cca = I.site_gas_gbp_per_mwh(ccl_under_cca=True, gas_price_case=case)
        assert I.engine_gas_gbp_per_mwh(case) == pytest.approx(site_cca - levies.ccl_gas_gbp_per_mwh(True))


# =============================================================================
# The inventory (no Brightway)
# =============================================================================
def test_the_inventory_checks_pass():
    assert gl.check().startswith("OK")


def test_carbon_balance_and_the_reason_for_replacing_the_datasets_co2():
    gas_c = gl.GE_GAS_M3_PER_KWH * gl.GAS_KG_PER_M3 * gl.GAS_FOSSIL_C_PER_KG
    out_c = (gl.GE_CO2_KG_PER_KWH / gl.CO2_PER_KG_C + gl.GE_PER_KWH["ch4"] * gl.M_C / gl.M_CH4
             + gl.GE_PER_KWH["co"] * gl.M_C / gl.M_CO)
    assert out_c == pytest.approx(gas_c, rel=1e-12)
    assert gl.LB_CO2_PER_MJ / gl.LB_GAS_M3_PER_MJ > 1.05 * gl.GAS_KG_PER_M3 * gl.GAS_FOSSIL_C_PER_KG * gl.CO2_PER_KG_C
    assert gl.GE_GAS_M3_PER_KWH * 1000 == pytest.approx(224.2, abs=0.1)
    assert gl.GE_GAS_MWH_HHV_PER_MWH == pytest.approx(2.491, abs=0.002)


def test_every_pick_is_an_exact_identity_with_its_product():
    for k, p in gl.processes.items():
        assert p.identity is not None and len(p.identity) == 3, k
    assert gl.processes["gas_hp_gb"].identity == ("market for natural gas, high pressure", "GB",
                                                   "natural gas, high pressure")
    for k, f in gl.flows.items():
        assert f.identity[1] == ("air", "urban air close to ground"), k


def test_only_the_engine_methane_line_is_kept_and_the_heat_parts_are_out():
    assert gl.LB_PER_MJ["ch4"] == 2.974689273071042e-05            # "estimate based on different references"
    assert gl.LB_CH4_NETWORK_PER_MJ not in gl.LB_PER_MJ.values()   # "losses ... low pressure network"
    keys = {k for a in gl.activities for k, *_ in a.technosphere}
    assert "chp_common" in keys and "chp_elec" in keys
    assert not any("heat only" in p.identity[0] for p in gl.processes.values())


def test_maintenance_moves_whole_from_per_mw_to_per_running_hour():
    plant = {k: amt for k, amt, *_ in gl.PLANT.technosphere}
    maint = {k: amt for k, amt, *_ in gl.MAINT.technosphere}
    assert plant["chp_maint"] == -gl.CHP_MAINT_PER_SET
    # the same 2.89 maintenance per set, now over the set's 100,000 h at 1 MW
    assert maint["chp_maint"] * gl.GE_SET_KW * gl.GE_UNIT_LIFE_H == pytest.approx(gl.CHP_MAINT_PER_SET)
    # its car trips leave with it, once: not again on the plant
    assert maint["car_rer"] == pytest.approx(-maint["chp_maint"] * gl.CAR_KM_MAINT)
    assert plant["car_rer"] == pytest.approx(-gl.CHP_CONSTRUCTION_PER_SET * (gl.CAR_KM_CONSTRUCTION
                                                                           + gl.CAR_KM_STARTUP))


def test_hall_is_the_orc_units_500_m2_per_3_mw():
    assert gl.GE_HALL_M2_PER_MW == pytest.approx(500.0 / 3.0)


# =============================================================================
# The model
# =============================================================================
def test_off_in_every_named_architecture_and_last_in_the_flags():
    assert A.ASSET_FLAGS[-1] == "gas_engine"
    for name in ("grid_only", "grid_battery", "grid_res_battery", "grid_h2", "grid_h2_bought",
                 "res_h2", "res_h2_grid"):
        assert A.architecture(name).gas_engine is False
    assert A.custom({"grid": True, "gas_engine": True}).gas_engine is True
    assert M.Assets().gas_engine is False


def test_every_engine_field_is_required():
    import dataclasses
    required = {f.name for f in dataclasses.fields(M.Tech) if f.default is dataclasses.MISSING}
    assert {"gwp_ge_per_mw", "gwp_ge_running_per_mwh", "gwp_ge_maint_per_mwh", "ge_calendar_years",
            "ge_duty_hours", "cost_ge", "cost_ge_per_mw", "cost_ge_gas_per_mwh", "cost_ge_carbon_per_mwh",
            "cost_ge_maint_per_mwh"} <= required


def test_every_engine_term_is_in_one_chain():
    names = M.CHAINS["gas engines"]
    assert {"gas engines", "gas burned", "gas engine maintenance", "gas", "gas carbon price",
            "gas engine running maintenance"} == names
    for chain, keys in M.CHAINS.items():
        if chain != "gas engines":
            assert not (keys & names), chain


@pytest.fixture(scope="module")
def setup():
    pytest.importorskip("linopy")
    sys.path.insert(0, str(ROOT / "tests"))
    from test_connection_choice import _tech       # the study's central coefficients, engines included
    from test_dc_model import DT, N
    rng = np.random.default_rng(3)
    hours = np.arange(N) * DT
    series = M.Series(index=pd.date_range("2025-01-01", periods=N, freq="30min"), dt_hours=DT,
                      demand_mw=np.full(N, 7.31),
                      cf_wind=np.clip(0.35 + 0.3 * np.sin(hours / 37) + 0.1 * rng.standard_normal(N), 0, 1),
                      cf_solar=np.clip(0.5 * np.sin(np.pi * ((hours % 24) - 6) / 12), 0, 1),
                      grid_gwp_per_mwh=250 + 120 * np.sin(hours / 11),
                      grid_price_per_mwh=200 + 40 * np.sin(hours / 13))
    return series, _tech()


def test_cheap_gas_power_is_built_and_runs_on_duty_when_it_runs_hard(setup):
    series, tech = setup
    m, V, obj = M.build_model(series, M.Assets(grid=True, gas_engine=True), tech, objective="cost")
    M.solve(m)
    cap = float(V["cap_ge"].solution)
    mwh = float(V["p_ge"].solution.sum()) * series.dt_hours * series.annual_scale
    units = float(V["ge_units"].solution)
    assert cap > 1.0                                      # ~£115/MWh against a ~£200 grid: it is built
    assert units == pytest.approx(max(cap / 25.0, mwh / 100_000.0), rel=1e-6)
    assert mwh / cap > 4_000.0                            # baseload here, so the duty term binds
    assert units == pytest.approx(mwh / 100_000.0, rel=1e-6)


def test_the_engines_carbon_is_on_both_sides_and_the_balance_closes(setup):
    series, tech = setup
    m, V, obj = M.build_model(series, M.Assets(grid=True, gas_engine=True), tech, objective="cost")
    M.solve(m)
    q = M.solution_quantities(V)
    terms = M.score(q, series, tech)
    assert terms["gwp_operational"]["gas burned"] > 0 and terms["gwp_embodied"]["gas engines"] > 0
    assert terms["cost_operational"]["gas"] > 0 and terms["cost_operational"]["gas carbon price"] > 0
    assert terms["cost_capital"]["gas engines"] > 0
    g = lambda k: q[k]
    residual = g("p_ge") + g("imp") + g("unserved") - g("exp") - series.demand_mw
    assert np.abs(residual).max() < 1e-6


# =============================================================================
# With Brightway
# =============================================================================
def _db_or_skip():
    bd = pytest.importorskip("bw2data")
    import dc_config as cfg
    from optimiser_lca import registry as R
    if cfg.PROJECT_NAME not in bd.projects:
        pytest.skip("Brightway project not present on this machine")
    bd.projects.set_current(cfg.PROJECT_NAME)
    if R.GAS_ENGINE_DB not in bd.databases:
        pytest.skip("gas engine foreground not built — python -m optimiser_lca.build gas_engine")
    return bd


def test_scored_total_is_in_band_and_agrees_with_desnz_2026_factors():
    _db_or_skip()
    d = ge.decompose()
    assert 500.0 < d["running_kgco2e_per_MWh"] < 650.0
    # DESNZ GHG conversion factors 2026: natural gas (100 % mineral) 0.18442 kg CO2e/kWh gross burning,
    # 0.03021 well-to-tank. A check, not an input: AR5 against this study's IPCC 2021.
    gross_mwh = d["gas_MWh_HHV_per_MWh"]
    assert d["co2_kg_per_MWh"] == pytest.approx(gross_mwh * 184.42, rel=0.05)
    assert d["running_parts_kgco2e_per_MWh"]["gas supply chain"] == pytest.approx(gross_mwh * 30.21, rel=0.15)
    assert 0.5 < d["maintenance_kgco2e_per_MWh"] < 1.0
    assert 200_000 < d["plant_kgco2e_per_MW"] < 300_000


def test_reconciliation_ends_on_the_running_activity():
    """ecoinvent's engine as published, then each edit, recorded when the coefficients were scored.

    13 Nov 2026: the first version picked the lean-burn engine by name and location only, and ecoinvent has
    a heat and an electricity activity under both, so it scored 8.7 kg/m3 instead of 2.5 whenever the
    database iterated the other one first. It now pins the product; this test holds the recorded rows."""
    _db_or_skip()
    d = ge.decompose()
    rows = d["reconciliation_kgco2e_per_m3"]
    assert rows[-1][1] == pytest.approx(d["running_kgco2e_per_MWh"] / d["gas_m3_per_MWh"], rel=2e-3)
    assert rows[0][0].startswith("ecoinvent lean-burn engine, as published")
    assert rows[0][1] == pytest.approx(3.09, abs=0.05)
    assert rows[0][1] > rows[-1][1]          # each edit is shown; together they lower the published figure


def test_transport_lines_are_accounted_for():
    """Every 'transport' input within two steps of the engine's activities: the trips to site net to zero,
    and what is left sits inside production or market datasets (upstream)."""
    bd = _db_or_skip()
    from optimiser_lca import registry as R
    to_site = ("construction work, heat and power co-generation unit, 160kW electrical",
               "start-up, heat and power co-generation unit, 160kW electrical",
               "maintenance, heat and power co-generation unit, 160kW electrical")
    leftover = []
    for code in (R.GE_PLANT, R.GE_MAINT):
        net = 0.0                                             # km of car trips to site left in, per unit
        act = bd.get_activity((R.GAS_ENGINE_DB, code))
        for e in act.technosphere():
            a1, amt1 = e.input, float(e["amount"])
            if a1["name"] == "market for transport, passenger car":
                net += amt1                                   # our negative rows
                continue
            for e2 in a1.technosphere():
                a2, amt2 = e2.input, float(e2["amount"]) * amt1
                if a2["name"] in to_site:
                    for e3 in a2.technosphere():
                        if e3.input["name"] == "market for transport, passenger car":
                            net += float(e3["amount"]) * amt2
                elif a1["name"] in to_site and a2["name"] == "market for transport, passenger car":
                    net += amt2
                elif "transport" in a2["name"]:
                    leftover.append((a1["name"], a2["name"]))
                else:
                    for e3 in a2.technosphere():
                        if "transport" in e3.input["name"]:
                            leftover.append((a2["name"], e3.input["name"]))
        assert net == pytest.approx(0.0, abs=1e-6), f"{code}: trips to site not netted out: {net:.6g} km"
    for parent, child in leftover:
        assert "production" in parent or parent.startswith("market"), (parent, child)
