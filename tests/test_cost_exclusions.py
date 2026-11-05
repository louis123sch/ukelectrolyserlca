"""The cost side's cut-off register: rules 1 and 2, and the estimates it says are carried."""
import numpy as np
import pandas as pd
import pytest

from optimisation import battery as batt
from optimisation import cost_exclusions as X
from optimisation import h2_capex as hc, levies


class _Coefficients:
    """The central coefficients the register tests against (battery: 4 Nov 2026, evening)."""
    cost_batt_p = 39_312.0
    cost_batt_e = 21_640.0
    cost_ely = 277_000.0
    cost_fc = hc.fuel_cell_cost("central")["annual_GBP_per_MW_year"]
    cost_tank = hc.tank_cost("central")["annual_GBP_per_kg_year"]


def test_what_is_left_out_passes_rules_1_and_2():
    assert X.failures(_Coefficients) == []


def test_a_flow_over_one_percent_is_reported():
    class Small(_Coefficients):
        cost_fc = 100.0
    assert any("fuel cell land" in f for f in X.failures(Small))


def test_included_estimates_would_have_failed_and_are_in_the_coefficients():
    shares = {r["flow"]: r["share"] for r in X.check(_Coefficients)}
    assert shares["tank land"] > X.RULE_1
    assert shares["fuel cell insurance"] > X.RULE_1
    assert hc.FC_INSURANCE_FRAC_OF_CAPITAL * hc.FC_GBP_PER_KW["central"] * 1000.0 == pytest.approx(
        next(f.upper for f in X.REGISTER if f.key == "fuel cell insurance"), rel=1e-3)


def test_supplier_margin_is_carried_in_the_import_price():
    flat = levies.flat_components()
    assert flat["Supplier margin"] == pytest.approx(0.02 * 209.27)
    idx = pd.date_range("2025-06-02", periods=48, freq="30min")
    assert levies.import_levies(idx)["components"]["Supplier margin_GBP_per_MWh"] == pytest.approx(4.1854)


def test_upper_additions_only_touch_flows_still_left_out():
    added = X.upper_additions()
    assert set(added) == {"cost_batt_e", "cost_fc"}      # battery rates are exempt to 2035: upper 0, not added


def test_major_hazard_is_hse_upper_tier_in_2025_pounds():
    got = hc.major_hazard_cost("central")["annual_GBP_per_site_year"]
    crf = hc.capital_recovery_factor(hc.FC_DISCOUNT_RATE, 25.0)
    assert got == pytest.approx((118_000.0 * crf + 27_000.0) * 103.6 / 73.7)
    assert 50_000.0 < got < 60_000.0
    assert hc.major_hazard_cost("low")["annual_GBP_per_site_year"] < got < hc.major_hazard_cost("high")["annual_GBP_per_site_year"]


def test_the_battery_line_holds_past_its_source():
    """Fitted through PNNL's 2 to 10 hours, the line stays near its 24-hour figure and 18 hours between."""
    rows = batt.PNNL_LFP_10MW_2030_USD_PER_KW
    slope, intercept = np.polyfit([2, 4, 10], [rows[2], rows[4], rows[10]], 1)
    assert intercept + slope * 24 == pytest.approx(rows[24], rel=0.02)
    assert intercept + slope * 18 == pytest.approx(rows[10] + (rows[24] - rows[10]) * 8 / 14, rel=0.02)


def test_a_flow_with_no_figure_is_stated_but_adds_nothing_to_rule_3():
    keys = {f.key: f for f in X.REGISTER}
    assert keys["the seller's hydrogen loading compressor"].status == "excluded"
    assert keys["selling power to the grid"].status == "boundary"
    assert keys["the time to get a grid connection"].status == "boundary"
    assert "major-hazard compliance" not in X.upper_additions()


def test_every_status_and_kind_is_known():
    for f in X.REGISTER:
        assert f.kind in ("cutoff", "boundary")
        assert f.status in ("excluded", "included_estimate", "open", "boundary")
        assert f.basis
