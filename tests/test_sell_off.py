"""Terlouw's sell-off for assets that outlive the data centre (25 Nov 2026).

docs/SELL_OFF_PLAN.md, optimisation/lives.py. Wind (35 y), solar (38 y) and the
grid connection (40 y) are repaid over the data centre's 25 years and sold at
the end for 75 % of their remaining straight-line value, discounted to today.
Nothing else moves. No solve: coefficients only, at East Grinstead (site 23).
"""
from __future__ import annotations

import sys
from dataclasses import fields
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import dc_config as cfg                                     # noqa: E402
from optimisation import connection_cost as cc              # noqa: E402
from optimisation import lives as L                         # noqa: E402
from optimisation import tech_costs as tc                   # noqa: E402

H = 25.0


# --- Terlouw et al.'s own functions, copied from OPTIMES (opt_lca_functions.py) -------------------
# Copyright (c) 2024, Tom Terlouw. BSD 3-Clause License: redistribution and use in source and
# binary forms, with or without modification, are permitted provided that the copyright notice,
# this list of conditions and the following disclaimer are retained. THIS SOFTWARE IS PROVIDED BY
# THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES ARE
# DISCLAIMED. Copied unchanged except for whitespace and comments, as the reference this
# module must reproduce.
def terlouw_calc_crf(r, lt):
    return (r * (1 + r) ** lt) / ((1 + r) ** lt - 1)


def terlouw_rep_annual_int(unit_inv_cost, lt, r, ry, rep_factor=0.75):
    c_rep_total = 0
    unit_inv_cost = rep_factor * unit_inv_cost
    if ry > lt:
        rest = 1 - (lt / ry)
        crf = terlouw_calc_crf(r, lt)
        c_rep_a = crf * ((unit_inv_cost * rest) / ((1 + r) ** lt))
        c_rep_total -= c_rep_a
    elif ry < lt:
        replacement_times = (lt / ry)
        counter_ry = ry
        crf = terlouw_calc_crf(r, lt)
        for _ in range(int(replacement_times)):
            c_rep_a = crf * (unit_inv_cost / ((1 + r) ** ry))
            c_rep_total += c_rep_a
            ry += counter_ry
        rest = 1 - (replacement_times % 1)
        c_rep_a = crf * ((unit_inv_cost * rest) / ((1 + r) ** lt))
        c_rep_total -= c_rep_a
    else:
        c_rep_total = 0
    return c_rep_total
# ------------------------------------------------------------------------------------------------


def _outliving_assets():
    """(name, rate, own life) of every asset the rule acts on, every cost case."""
    out = []
    for tech in ("onshore_wind", "solar_pv"):
        for case in tc.CASES:
            a = tc.annual_cost(tech, case)
            out.append((f"{tech} {case}", a["discount_rate"], a["lifetime_years"]))
    for region in (1, 2, 14):
        out.append((f"connection r{region}", cc.RATE_OF_RETURN.get(region, cc.RATE_OF_RETURN_DEFAULT),
                    cc.ASSET_LIFE_YEARS))
    return out


@pytest.mark.parametrize("name,rate,life", _outliving_assets())
def test_matches_terlouws_code(name, rate, life):
    """Our factor = his 25-year repayment plus his replacement function, to 1e-12."""
    ours = L.sell_off_factor(rate, life, H, 0.75)
    his = terlouw_calc_crf(rate, H) + terlouw_rep_annual_int(1.0, H, rate, life, rep_factor=0.75)
    assert ours == pytest.approx(his, rel=1e-12)


def test_settings_are_terlouws():
    assert cfg.SELL_OFF is True
    assert cfg.RESALE_SHARE == 0.75
    assert cfg.DC_OPERATION_YEARS == 25
    assert cfg.TANK_LIFETIME_YEARS == cfg.DC_OPERATION_YEARS


def test_traced_factor_is_the_plain_one():
    """What the cost modules charge is the same formula."""
    for tech in ("onshore_wind", "solar_pv"):
        a = tc.annual_cost(tech, "central")
        assert a["repayment_factor"] == pytest.approx(
            L.sell_off_factor(a["discount_rate"], a["lifetime_years"], H, 0.75), rel=1e-12)
        assert a["project_years"] == H
    r = cc.RATE_OF_RETURN_DEFAULT
    f = cc.annual_factor(14, False)
    assert f == pytest.approx(L.sell_off_factor(r, 40.0, H, 0.75) + cc.MAINTENANCE_FRAC, rel=1e-12)


def test_central_build_cost_moves_as_planned():
    """Against repaying each over its own life: wind +6.1 %, solar +7.1 %, connection +11.6 %."""
    for tech, rise in (("onshore_wind", 0.0613), ("solar_pv", 0.0712)):
        new = tc.annual_cost(tech, "central")
        with L.setting(sell_off=False):
            old = tc.annual_cost(tech, "central")
        assert new["annualised_capex_GBP_per_MW_year"] / old["annualised_capex_GBP_per_MW_year"] - 1 == \
            pytest.approx(rise, abs=5e-4)
        # Running costs, land and rates do not move.
        assert (new["total_annual_cost_GBP_per_MW_year"] - new["annualised_capex_2025_GBP_per_MW_year"]) == \
            pytest.approx(old["total_annual_cost_GBP_per_MW_year"] - old["annualised_capex_2025_GBP_per_MW_year"])
    new = cc.annual_factor(14, False) - cc.MAINTENANCE_FRAC
    with L.setting(sell_off=False):
        old = cc.annual_factor(14, False) - cc.MAINTENANCE_FRAC
    assert new / old - 1 == pytest.approx(0.116, abs=5e-4)


def test_old_rule_is_the_own_life_repayment():
    """sell_off=False gives exactly the rule before 25 Nov 2026."""
    with L.setting(sell_off=False):
        for tech in ("onshore_wind", "solar_pv"):
            for case in tc.CASES:
                a = tc.annual_cost(tech, case)
                assert a["repayment_factor"] == a["crf"]
                assert a["crf"] == tc.capital_recovery_factor(a["discount_rate"], a["lifetime_years"])
        r = cc.RATE_OF_RETURN_DEFAULT
        assert cc.annual_factor(14, True) == cc.crf(r, 40.0) + cc.MAINTENANCE_FRAC + cc.TRC_FRAC


def test_limits():
    r, life = 0.076, 35.0
    # Nothing back: a plain 25-year repayment.
    assert L.sell_off_factor(r, life, H, 0.0) == pytest.approx(L.capital_recovery_factor(r, H))
    # The whole remaining value back.
    assert L.sell_off_factor(r, life, H, 1.0) == pytest.approx(
        L.capital_recovery_factor(r, H) * (1 - (life - H) / life * (1 + r) ** -H))
    # An asset of 25 years or less is not touched.
    for short in (25.0, 15.0, 10.0):
        assert L.sell_off_factor(r, short, H, 0.75) == L.capital_recovery_factor(r, short)
    # Wind's high cost case is a 25-year life: no sell-off.
    a = tc.annual_cost("onshore_wind", "high")
    assert a["lifetime_years"] == 25.0 and a["repayment_factor"] == a["crf"]
    with pytest.raises(ValueError):
        with L.setting(resale_share=-0.1):
            pass


def test_resale_share_push_moves_all_three():
    from optimisation import trace as T
    base_w = tc.annual_cost("onshore_wind", "central")["repayment_factor"]
    base_c = cc.annual_factor(14, False)
    with T.pushed(L.SHARE_KEY, 0.5) as hits:
        w = tc.annual_cost("onshore_wind", "central")["repayment_factor"]
        c = cc.annual_factor(14, False)
    assert any(hits)
    r = tc.annual_cost("onshore_wind", "central")["discount_rate"]
    assert w == pytest.approx(L.sell_off_factor(r, 35.0, H, 0.375), rel=1e-12)
    assert w > base_w and c > base_c


def _east_grinstead():
    from optimisation import sites
    return sites.resolve(51.2, 0.0, name="East Grinstead", carbon_api_region=14, connection_route_km=2.0)


_NO_NETWORK = {"capacity_GBP_per_MW_year": 0.0, "fixed_GBP_per_year": 0.0}
# What the rule may move: wind, solar and the grid connection's own capital, in cost only.
MAY_MOVE = {"cost_wind", "cost_solar", "cost_grid_per_mw_year", "cost_grid_fixed_per_year", "labels",
            "connection_options"}


@pytest.fixture(scope="module")
def both_rules():
    from optimisation import dc_inputs as I
    site = _east_grinstead()
    return I.build_tech(site, _NO_NETWORK), I.build_tech(site, _NO_NETWORK, sell_off=False)


def test_only_wind_solar_and_the_connection_move(both_rules):
    new, old = both_rules
    moved = {f.name for f in fields(new)
             if f.name not in ("labels",) and getattr(new, f.name) != getattr(old, f.name)}
    assert moved <= MAY_MOVE, moved - MAY_MOVE
    assert {"cost_wind", "cost_solar", "cost_grid_per_mw_year"} <= moved
    # Every carbon coefficient is identical.
    for f in fields(new):
        if f.name.startswith("gwp_"):
            assert getattr(new, f.name) == getattr(old, f.name), f.name
    assert new.cost_wind / old.cost_wind - 1 == pytest.approx(0.044, abs=2e-3)
    assert new.cost_solar / old.cost_solar - 1 == pytest.approx(0.057, abs=2e-3)


def test_the_setting_is_recorded(both_rules):
    new, old = both_rules
    assert new.labels["sell_off"] is True and new.labels["resale_share"] == 0.75
    assert new.labels["sell_off_project_years"] == 25.0
    assert old.labels["sell_off"] is False and old.labels["resale_share"] is None


def test_audit_lives_agree():
    from optimisation import audit
    audit.check_lifetime_agreement()
