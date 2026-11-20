"""The fixes from the Rozzi, Viole and Terlouw comparisons (docs/COMPARISON_FIXES_PLAN.md,
20 Nov 2026): electrolyser stacks charged in cost, the 2026 build, solar ageing, three
new x0.5/x1.5 tests, the split coefficient table and the battery cycling warning.

No solving. ``build_tech`` reads the decomposition caches, as tests/test_coefficients.py does.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from optimisation import electrolysers, fuel_cell, h2_storage  # noqa: E402
from optimisation import h2_capex as hc  # noqa: E402
from optimisation import trace as T  # noqa: E402

SITE = "51.2,0.0"           # East Grinstead, the study's test site (never London)
_NO_NETWORK = {"capacity_GBP_per_MW_year": 0.0, "fixed_GBP_per_year": 0.0}
HOURS_HIGH = 6_185.0        # the islanded lowest-cost design's electrolyser


def _cached():
    for module in (electrolysers, fuel_cell, h2_storage):
        if not module.CACHE_PATH.exists():
            pytest.skip(f"{module.CACHE_PATH.name} not built")


def _tech(**kw):
    _cached()
    from optimisation import dc_inputs as I
    return I.build_tech(SITE, _NO_NETWORK, **kw)


def _units(tech, hours):
    """Stacks bought per MW a year: max(calendar, running hours), as dc_model."""
    return max(1.0 / tech.ely_stack_calendar_years, hours / tech.ely_stack_duty_hours)


# =============================================================================
# 1. Electrolyser stacks charged in cost
# =============================================================================
def test_stack_shares_are_the_danish_sheets():
    assert hc.ely_stack_cost_fraction("pem") == pytest.approx(311.96 / 1765.27, rel=1e-4)
    assert hc.ely_stack_cost_fraction("ae") == pytest.approx(177.31 / 1254.04, rel=1e-4)
    assert hc.ely_stack_cost_fraction("soec") == pytest.approx(387.73 / 2959.14, rel=1e-4)


@pytest.mark.parametrize("ely_tech", ["PEM operation", "AE operation", "SOEC operation"])
def test_stacks_lasting_the_plant_life_cost_exactly_what_the_whole_unit_did(ely_tech):
    """With the stack replaced on its calendar life, the split charge is the old
    whole-unit annuity to the penny: the stack share only moves money between the
    capacity term and the replacement term."""
    split = _tech(ely_tech=ely_tech)
    with T.pushed("cost.electrolyser.stack_cost_fraction", 0.0) as hits:
        whole = _tech(ely_tech=ely_tech)
    assert hits and all(hits)
    assert whole.cost_ely_stack_per_mw == 0.0
    at_calendar = split.cost_ely + split.cost_ely_stack_per_mw / split.ely_stack_calendar_years
    assert at_calendar == pytest.approx(whole.cost_ely, rel=1e-12)


def test_a_hard_run_membrane_electrolyser_pays_for_its_extra_stacks():
    """About +GBP 29k per MW a year at 6,185 h (Danish 17.7 %, 50,000 h, 2026 build),
    +9 % on the line; nothing extra below 2,000 h a year."""
    t = _tech(ely_tech="PEM operation")
    base = t.cost_ely + t.cost_ely_stack_per_mw * _units(t, 0.0)
    extra = t.cost_ely_stack_per_mw * (_units(t, HOURS_HIGH) - _units(t, 0.0))
    assert extra == pytest.approx(29_300, rel=0.03)
    assert extra / base == pytest.approx(0.091, abs=0.005)
    assert _units(t, 2_000.0) == _units(t, 0.0)


def test_solid_oxide_stacks_are_charged_once():
    """Its per-kg figure is NESO's 0.9 % rule on its own price (water and consumables),
    no longer the BEIS annex's annuitised stack, which is now on ely_stack_units."""
    ec = hc.electrolyser_costs()
    r = ec[(ec.asset == "electrolyser_soec") & (ec.case == "central")].iloc[0]
    rule = r.capex_GBP_per_kWe * hc.SOE_KWH_IN_PER_KWH_H2 * 0.009 / 7_884.0 * hc.H2_HHV_KWH_PER_KG
    assert r.variable_opex_GBP_per_kg == pytest.approx(rule, rel=1e-12)
    assert r.variable_opex_GBP_per_kg < 0.3            # the annex's stack was ~0.51
    t = _tech(ely_tech="SOEC operation")
    assert t.cost_ely_stack_per_mw > 0


def test_neso_per_kg_figure_is_its_own_0_9_percent_rule():
    """The portal's per-kWh figure is 0.9 % of capital per kW of hydrogen over 7,884 h:
    what reading it as water and consumables rests on."""
    df = hc.neso_table(2025)
    r = df[(df.technology == "PEM") & (df.scenario == "Central")].iloc[0]
    assert r.variable_opex_GBP_per_kWh_H2_HHV == pytest.approx(r.capex_GBP_per_kW_H2_HHV * 0.009 / 7_884.0, rel=1e-4)


def test_electrolyser_stack_term_is_in_the_objective():
    from optimisation import dc_model
    assert "electrolyser water and consumables" in dc_model.CHAINS["electrolyser"]
    assert "electrolyser stacks and water" in dc_model.CHAINS["electrolyser"]   # saved runs


# =============================================================================
# 2. The 2026 build
# =============================================================================
def test_membrane_and_alkaline_are_priced_as_built_in_2026():
    ec = hc.electrolyser_costs()
    c = ec[ec.case == "central"].set_index("asset")
    assert c.loc["electrolyser_pem", "capex_GBP_per_kWe"] == pytest.approx(2010 + (1580 - 2010) / 5)
    assert c.loc["electrolyser_ae", "capex_GBP_per_kWe"] == pytest.approx(1740 + (1450 - 1740) / 5)
    assert bool(c.loc["electrolyser_pem", "interpolated"]) and bool(c.loc["electrolyser_ae", "interpolated"])
    # solid oxide unchanged: NESO H.02's own 2026 column
    assert c.loc["electrolyser_soec", "capex_GBP_per_kWe"] == pytest.approx(4923.845 / 0.95885, rel=1e-3)


def test_neso_table_returns_its_own_rows_for_a_published_year():
    df = hc.neso_table(2030)
    assert not df.interpolated.any()
    assert float(df[(df.technology == "PEM") & (df.scenario == "Central")].iloc[0].capex_GBP_per_kWe) == 1580


# =============================================================================
# 3. Solar ageing
# =============================================================================
def test_solar_life_average_factor():
    from optimisation import profiles
    assert profiles.SOLAR_LIFE_AVERAGE_FACTOR == pytest.approx(1 - 0.007 * 37 / 2)
    assert profiles.SOLAR_LIFE_AVERAGE_FACTOR == pytest.approx(0.8705)


def test_solar_output_is_aged_and_wind_is_not():
    import numpy as np
    from optimisation import dc_inputs as I, profiles
    try:
        a, _ = I.build_series(SITE, "2025-06-01", "2025-06-08", 100.0, solar_ageing_factor=1.0)
        b, meta = I.build_series(SITE, "2025-06-01", "2025-06-08", 100.0)
    except Exception as e:                                   # no cached week and no network
        pytest.skip(f"series not available here: {e!r}"[:200])
    assert np.allclose(b.cf_solar, a.cf_solar * profiles.SOLAR_LIFE_AVERAGE_FACTOR)
    assert np.array_equal(a.cf_wind, b.cf_wind)
    assert meta["solar_ageing_factor"] == pytest.approx(profiles.SOLAR_LIFE_AVERAGE_FACTOR)


def test_solar_cost_and_carbon_per_mw_do_not_move():
    """Ageing acts on output only: per MWp the price and carbon are as before, so per
    unit delivered both rise by 1 / 0.8705."""
    t = _tech()
    with T.pushed("solar.life_average_output_factor", 0.5):
        u = _tech()
    assert (t.cost_solar, t.gwp_solar) == (u.cost_solar, u.gwp_solar)


# =============================================================================
# 4. The new x0.5 / x1.5 tests
# =============================================================================
NEW_PUSHES = ("cost.electrolyser.stack_cost_fraction", "cost.h2_tank.capex_per_kg",
              "cost.fuel_cell.maintenance_per_kW_year")


def test_new_pushes_are_in_the_screened_list():
    from optimisation import sensitivity as S
    for k in NEW_PUSHES:
        for f in (0.5, 1.5):
            assert f"{k}*{f}" in S.SHAKY_KNOBS["push"]


@pytest.mark.parametrize("key,field", [("cost.electrolyser.stack_cost_fraction", "cost_ely_stack_per_mw"),
                                       ("cost.h2_tank.capex_per_kg", "cost_tank"),
                                       ("cost.fuel_cell.maintenance_per_kW_year", "cost_fc")])
def test_each_new_push_moves_its_figure(key, field):
    t = _tech()
    for f in (0.5, 1.5):
        with T.pushed(key, f) as hits:
            u = _tech()
        assert hits and all(hits), f"{key} is not recorded where the cost is made"
        assert (getattr(u, field) < getattr(t, field)) if f < 1 else (getattr(u, field) > getattr(t, field))
    if field == "cost_ely_stack_per_mw":
        with T.pushed(key, 0.5):
            assert _tech().cost_ely_stack_per_mw == pytest.approx(0.5 * t.cost_ely_stack_per_mw, rel=1e-12)


# =============================================================================
# 5. The coefficient table and the battery cycling warning
# =============================================================================
def test_coefficient_table_rows_add_up_to_what_the_optimiser_charges():
    _cached()
    from optimisation import coefficients
    df = coefficients.build().set_index("asset")
    assert "three stacks" not in " ".join(df.note.astype(str))
    t = _tech(ely_tech="PEM operation")
    plant, stack = df.loc["electrolyser_pem"], df.loc["electrolyser_pem_stack"]
    share = t.gwp_ely_stack_per_mw / stack.capital_kgco2e_per_capacity_unit     # stack's share of cap_ely
    assert t.gwp_ely == pytest.approx(plant.capital_kgco2e_per_capacity_unit / plant.calendar_lifetime_years * share,
                                      rel=1e-9)
    assert stack.duty_lifetime_hours == t.ely_stack_duty_hours
    assert stack.calendar_lifetime_years == t.ely_stack_calendar_years


def test_battery_cycles_per_year():
    from optimisation import audit
    assert audit.battery_cycles_per_year(100.0, 10.0, 8_760.0) == pytest.approx(10.0)
    assert audit.battery_cycles_per_year(10.0, 10.0, 876.0) == pytest.approx(10.0)
    assert audit.battery_cycles_per_year(10.0, 0.0, 876.0) == 0.0


@pytest.mark.parametrize("cycles,severity,word", [(180.0, "ok", "near"), (400.0, "warn", "assumed"),
                                                  (700.0, "warn", "over its life")])
def test_battery_cycling_warning(cycles, severity, word):
    from optimisation import audit
    before = len(audit.FINDINGS)
    audit.check_battery_cycles(cycles)
    f = audit.FINDINGS[before]
    del audit.FINDINGS[before:]
    assert f.severity == severity and word in f.what
