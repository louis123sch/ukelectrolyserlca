"""Levies, losses and connection capital, pinned to the documents they come from
(OneDrive "DC optimiser/connection sources", folders 3, 4 and 5). Each expected
value is written as the document states it, so a changed constant fails here."""
import pathlib
import sys

import pandas as pd
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from optimisation import connection_cost as cc, levies as lv


# --- levies, FY2026/27 --------------------------------------------------------
def test_ro_is_obligation_times_buyout():
    """Ofgem 2026-27: 0.472 ROCs/MWh, £69.34 per ROC."""
    assert lv.flat_components()["RO"] == pytest.approx(0.472 * 69.34)


def test_fit_is_the_mean_of_fund_over_net_supply():
    """Ofgem FIT Quarterly Reports 62-65, fund / (supply - EII exempt)."""
    by_quarter = [540_865_854.37 / (58_141_564 - 3_272_541),
                  432_300_086.74 / (67_525_489 - 3_211_180),
                  358_081_232.287 / (70_354_600 - 3_230_872),
                  556_039_966.19 / (59_217_531 - 3_293_227)]
    assert lv.fit_gbp_per_mwh() == pytest.approx(sum(by_quarter) / 4)


def test_cfd_is_day_weighted_with_its_in_period_adjustments():
    """EMRS Key Figures 2026/27 §3: 10.260; 10.559 then 2.068 from 17 Aug;
    5.529 (adjusted) from 1 Oct; 2.979 from 1 Jan; plus £0.1463 operational."""
    days = {10.260: 91, 10.559: 47, 2.068: 45, 5.529: 92, 2.979: 90}
    expected = sum(r * d for r, d in days.items()) / sum(days.values()) + 0.1463
    assert lv.cfd_gbp_per_mwh() == pytest.approx(expected)


def test_capacity_market_is_charge_over_winter_peak_demand():
    """EMRS Key Figures 2026/27 §9 and §12 (Delivery Year 2026/27)."""
    assert lv.cm_gbp_per_mwh_in_window() == pytest.approx(3_474_489_734.79 / 11_291_571.95)


def test_aahedc_and_ccl():
    """NESO AAHEDC 2026-27 Schedule 1: 0.044269 p/kWh. GOV.UK CCL: £0.00801/kWh."""
    c = lv.flat_components()
    assert c["AAHEDC"] == pytest.approx(0.44269)
    assert c["CCL"] == pytest.approx(8.01)
    assert lv.ccl_gbp_per_mwh(True) == pytest.approx(8.01 * 0.08)


@pytest.mark.parametrize("when, period", [
    ("2026-01-07 17:00", 1),     # Wednesday, Jan, 16:00-20:00 UK: winter peak
    ("2026-01-07 09:00", 3),     # winter shoulder
    ("2026-03-04 12:00", 3),     # March weekdays 07:00-20:00: winter shoulder
    ("2026-07-01 11:00", 2),     # 12:00 BST, Jun-Aug weekday: summer peak
    ("2026-07-01 03:00", 4),     # night
    ("2026-01-10 17:00", 5),     # Saturday: other
])
def test_llf_periods_follow_lpn_annex_5(when, period):
    assert lv.llf_period(pd.DatetimeIndex([when]))[0] == period


def test_losses_are_llf_times_tlm():
    """LPN Annex 5 '132kV generic' night 1.002, HV network winter peak 1.036;
    offtaking TLM = 1 + London's (zone 3) winter TLF 0.0312 + TLMO- 0.011."""
    s = lv.loss_series(pd.DatetimeIndex(["2026-01-07 03:00"]), "132 kV", 13)
    assert s.iloc[0] == pytest.approx(1.002 * (1 + 0.0312 + 0.011))
    s = lv.loss_series(pd.DatetimeIndex(["2026-01-07 17:00"]), "11 kV", 13)
    assert s.iloc[0] == pytest.approx(1.036 * (1 + 0.0312 + 0.011))


@pytest.mark.parametrize("region, when, tlf", [
    (1, "2027-01-06 12:00", -0.0493),   # North Scotland, winter: the most negative
    (1, "2026-07-01 12:00", -0.0197),   # North Scotland, summer ("-0.02 ... to -0.05", p. 9)
    (11, "2027-01-06 12:00", 0.0323),   # South West, winter: the largest
    (13, "2026-07-01 12:00", 0.0176),   # London, summer: "marginally the largest"
    (3, "2027-03-03 12:00", 0.0),       # North West, spring: under 0.001
])
def test_tlm_is_one_plus_zonal_tlf_plus_tlmo(region, when, tlf):
    """Elexon TLF Analysis Report 2026/27, pp. 7-9; TLMO- assumed 0.011."""
    t = lv.tlm_series(pd.DatetimeIndex([when]), region).iloc[0]
    assert t == pytest.approx(1 + tlf + lv.TLMO_OFFTAKING_ASSUMED)


def test_tlf_rankings_match_the_reports_text():
    """p. 9: spring positives in order 11, 3, 5, 10, 8, 2, 9, 4, 1; negatives
    12, 6, 13, 14; winter largest for 12 of 14 zones (not 4 and 7)."""
    t = lv.TLF_ZONE_2026_27
    pos = [11, 3, 5, 10, 8, 2, 9, 4, 1]
    assert all(t[a][0] >= t[b][0] for a, b in zip(pos, pos[1:])) and all(t[z][0] > 0 for z in pos)
    neg = [12, 6, 13, 14]
    assert all(t[a][0] > t[b][0] for a, b in zip(neg, neg[1:])) and all(t[z][0] < 0 for z in neg)
    winter_largest = [z for z in t if abs(t[z][3]) == max(abs(v) for v in t[z])]
    assert sorted(set(t) - set(winter_largest)) == [4, 7]


# --- connection capital, NGED South Wales June 2026 ---------------------------
def test_132kv_substation_per_mw_and_cable():
    c = cc.capital("132 kV", "central")
    assert c["per_MW_GBP"] == pytest.approx((1_700_792 + 2_790_945) / 2 / 60.0)
    assert c["fixed_GBP"] == pytest.approx(2 * (126_845 + 1_960 * 3_171))


def test_33kv_uses_the_primary_substation_and_33kv_cable():
    c = cc.capital("33 kV", "low")
    assert c["per_MW_GBP"] == pytest.approx(1_359_279 / 29.0)
    assert c["fixed_GBP"] == pytest.approx(2 * (9_068 + 1_970 * 221))


def test_11kv_has_no_transformer_substation_only_a_switchboard():
    c = cc.capital("11 kV", "high")
    assert c["per_MW_GBP"] == 0.0
    assert c["fixed_GBP"] == pytest.approx(2 * (12_324 + 1_980 * 261) + 40_708)


def test_transmission_is_priced_on_the_132kv_rows():
    t = cc.connection_costs(1, True, connection_voltage="transmission")
    d = cc.connection_costs(1, False, connection_voltage="132 kV")
    assert t["per_MW_GBP"] == d["per_MW_GBP"] and t["fixed_GBP"] == d["fixed_GBP"]
    assert t["annual_factor"] > d["annual_factor"]          # TRC on the transmission tier
