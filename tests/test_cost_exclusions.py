"""The cost side's cut-off register: rules 1 and 2, and the estimates it says are carried."""
import pandas as pd
import pytest

from optimisation import cost_exclusions as X
from optimisation import h2_capex as hc, levies


class _Coefficients:
    """The central coefficients the register tests against."""
    cost_batt_e = 16_508.0
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
    assert set(added) == {"cost_batt_e", "cost_fc"}


def test_every_status_and_kind_is_known():
    for f in X.REGISTER:
        assert f.kind in ("cutoff", "boundary")
        assert f.status in ("excluded", "included_estimate", "open", "boundary")
        assert f.basis
