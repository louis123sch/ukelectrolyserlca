"""Everything the LP charges in 2026 pounds, the levy-agreement option, the gas
price range and the run warnings (9 Nov 2026)."""
import numpy as np
import pandas as pd
import pytest

from optimisation import dc_inputs as I
from optimisation import h2_prices, levies
from optimisation import price_base as P

F26 = 1.0296071586188875          # HM Treasury, Budget October 2026: calendar 2026, +2.9607 %


def test_one_factor_from_2025_to_2026():
    assert P.FACTOR_2025_TO_2026 == pytest.approx(F26)
    assert P.factor_to_2026(2026) == 1.0
    assert P.factor_to_2026(2025) == pytest.approx(F26)
    assert P.factor_to_2026(2023) == pytest.approx(103.6 / 96.3 * F26)
    with pytest.raises(KeyError):
        P.factor_to_2026(2027)
    assert P.record_to_2026(2026) == []
    assert P.record_to_2026(2025) == ["price_base.2025_to_2026"]
    assert P.record_to_2026(2022) == ["price_base.2022_to_2025", "price_base.2025_to_2026"]


def test_site_gas_takes_out_the_2025_levy_and_puts_back_this_years():
    commodity_2025 = 41.49 - 7.75
    assert I.site_gas_gbp_per_mwh() == pytest.approx(commodity_2025 * F26 + 8.01)
    # an agreement takes 89 % off the gas levy, not the electricity 92 %
    assert I.site_gas_gbp_per_mwh(True) == pytest.approx(commodity_2025 * F26 + 8.01 * 0.11)
    # the gas case scales the wholesale part only
    assert I.site_gas_gbp_per_mwh(None, "low") == pytest.approx(commodity_2025 * F26 * 0.75 + 8.01)
    assert I.site_gas_gbp_per_mwh(None, "high") == pytest.approx(commodity_2025 * F26 * 1.25 + 8.01)


def test_levy_agreement_on_electricity_and_gas():
    assert levies.ccl_gbp_per_mwh(False) == pytest.approx(8.01)
    assert levies.ccl_gbp_per_mwh(True) == pytest.approx(8.01 * 0.08)
    assert levies.ccl_gas_gbp_per_mwh(False) == pytest.approx(8.01)
    assert levies.ccl_gas_gbp_per_mwh(True) == pytest.approx(8.01 * 0.11)


def test_gas_case_moves_grey_and_turquoise_only():
    for colour in ("grey", "turquoise"):
        gas_mwh = h2_prices.INVENTORY[colour]["gas_m3_per_kg"] * h2_prices.GAS_KWH_HHV_PER_M3 / 1000.0
        adj, keys = I._bought_gas_adjustment(colour, "high", h2_prices)
        assert adj == pytest.approx(gas_mwh * h2_prices.gas_gbp_per_mwh() * 0.25)
        assert keys
        assert I._bought_gas_adjustment(colour, "central", h2_prices) == (0.0, [])
    for colour in ("green", "blue"):
        assert I._bought_gas_adjustment(colour, "high", h2_prices) == (0.0, [])


def test_warnings_flag_an_unusual_year_and_a_window_without_winter_evenings():
    year = pd.date_range("2025-01-01", "2025-12-29", freq="30min")
    ordinary = I.WHOLESALE_REFERENCE_2025_GBP_PER_MWH * F26
    assert I.run_warnings(year, np.full(len(year), ordinary)) == []
    dear = I.run_warnings(year, np.full(len(year), ordinary * 2.0))
    assert len(dear) == 1 and "above" in dear[0] and "on-site" in dear[0]
    cheap = I.run_warnings(year, np.full(len(year), ordinary * 0.6))
    assert len(cheap) == 1 and "below" in cheap[0]
    summer = pd.date_range("2019-06-01", "2019-06-08", freq="30min")
    w = I.run_warnings(summer, np.full(len(summer), ordinary))
    assert len(w) == 1 and "No winter evenings" in w[0]
    january = pd.date_range("2019-01-07", "2019-01-14", freq="30min")
    assert I.run_warnings(january, np.full(len(january), ordinary)) == []


def test_bad_gas_case_is_refused():
    with pytest.raises(ValueError):
        I.build_tech("london", {"capacity_GBP_per_MW_year": 0.0, "fixed_GBP_per_year": 0.0}, gas_price_case="dear")
