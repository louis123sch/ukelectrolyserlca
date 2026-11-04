"""
Policy levies and losses on imported electricity — what a supplier passes through.
=============================================================================

Until 28 Oct 2026 the import price was wholesale + BSUoS + DUoS and nothing
else. A half-hourly industrial site also pays, through its supplier, the costs
of the low-carbon support schemes and the Climate Change Levy, and buys the
energy lost between the grid and its meter. Leaving them out flattered imports
against every on-site asset.

Two shapes, as in ``network_charges``:

| levy | basis | shape |
|---|---|---|
| RO, FiT, CfD, AAHEDC, Nuclear RAB, CCL | £/MWh supplied | flat — one adder |
| Capacity Market | £/MWh in 16:00-19:00 on working days, Nov-Feb | time-shaped, like DUoS red |

The CM levy is the one that matters for the comparison. It falls on exactly the
winter-evening peak that a battery or fuel cell can cover, so folding it into a
flat adder would hide what storage is worth.

One tariff year: 2026/27
------------------------
Every figure is FY2026/27 (``LEVY_FY``), the same year as every network charge
(``network_charges.TARIFF_FY``), applied to whatever window is solved. Moved
from 2025/26 on 28 Oct 2026. Every number below is stored as the document states
it — a rate, or the totals a rate is divided from — and the arithmetic is done
here, so each £/MWh can be traced back. Documents are in OneDrive "DC optimiser/
connection sources/5 levies and losses" unless noted.

RO      Ofgem, *RO buy-out price and mutualisation threshold and ceilings 2026
        to 2027* (data page): buy-out £69.34 per ROC; obligation 0.472 ROCs per
        MWh supplied in England, Wales and Scotland. £/MWh = product.
FiT     Ofgem, *FIT Quarterly Report* Issues 62-65: the levelisation fund and
        the supply less EII-exempt supply for each quarter. Ofgem publishes no
        rate; £/MWh = fund / (supply - exempt) per quarter, then their mean.
        The four latest published quarters (Jul 2025 - Jun 2026): only quarter
        1 of 2026/27 (Issue 65) is out, and a rolling year keeps the seasonal
        mix that a single quarter would bias.
CfD     EMR Settlement, *Key Figures for Payments in 2026/27* §1 and §3:
        interim levy rates by period, in-period adjustments included, day-
        weighted over the year; plus the £0.1463/MWh operational costs levy.
CM      Same document, §9 and §12: Delivery Year 2026/27 total annual capacity
        payments £3,474,489,734.79 over 11,291,571.95 MWh of Total Gross Demand
        for Periods of High Demand, "4 p.m. to 7 p.m. on any working day in
        November, December, January or February". £/MWh in window = division.
Nuclear Same document, §5 and §7: interim levy rate by quarter, day-weighted;
RAB     plus the £0.0063/MWh operational costs levy.
AAHEDC  NESO, *AAHEDC Final Tariff and Charging Statement 2026-27*, Schedule 1:
        Total Scheme Energy Consumption Tariff 0.044269 p/kWh.
CCL     GOV.UK, *Climate Change Levy rates*: electricity £0.00801/kWh from
        1 April 2026; 92 % discount under a Climate Change Agreement, for which
        data centres are eligible. Whether a site holds one is ASSUMED
        (``CCL_UNDER_CCA``).

Losses
------
The supplier buys the metered volume grossed up for distribution losses (the
line loss factor, LLF) and transmission losses (the transmission loss
multiplier, TLM). Applied to the energy bought (wholesale) and to BSUoS, which
is charged on loss-adjusted volumes; not to DUoS or the levies, which are on
metered supply.

LLF     Each area's *Schedule of charges and other tables 2026/27*, "Annex 5
        LLFs": generic demand LLFs by metered voltage, in the area's own time
        periods (``duos_areas.LLF``, ``LLF_PERIOD_RULES``). TRANSCRIBED. A site
        takes its own area's row for its connection voltage
        (``network_charges.connection_voltage``); a transmission site has no
        distribution loss. NGED publish theirs separately (``duos_areas.LLF_FILES``).
        Until 29 Oct 2026 London's table was used for every site.
TLM     offtaking TLM = 1 + TLF(zone, season) + TLMO- (Elexon, *Guidance
        document for Transmission Loss Factors* v1.0, Jan 2026; BSC
        Modification P350, zonal since 1 April 2018).
        TLF     the Adjusted Seasonal Zonal TLFs for BSC Year 2026/27 (the
                TLFA-I009 values used in the TLM), READ FROM THE CHARTS in
                Elexon, *Analysis Reporting for TLFs - BSC Year 2026/27* V1.0
                (April 2026), pp. 7-8: bar heights measured in pixels against
                the labelled gridlines (about +/-0.0005). Every ranking and
                range stated in the report's text (p. 9) holds for the values
                read. ``TLF_ZONE_2026_27``. The exact file is on the Elexon
                Portal (login; down on 29 Oct 2026): replace when it is back.
        TLMO-   ASSUMED 0.011: the offtaking share in the guidance's worked
                example ("TLM of 1.011", 55 % of 2 % losses, before zonal
                TLFs). It is set per settlement period from metered data.
        Until 29 Oct 2026 the TLM was a flat 1.011 for every site; until 28
        Oct 2026 losses were the carbon side's ecoinvent factor (x1.0338).

Supplier margin, since 4 Nov 2026: unpublished for a site this size, so an
estimate, the CMA's 2.0 % on industrial and commercial supply of DESNZ's price to
extra large consumers (cost_exclusions.py: it fails the 1 % test if left out).

Not charged: the ESC and EMR settlement-cost levies (negligible per MWh) and the
Green Gas Levy (gas only).
A data centre is not an Energy Intensive Industry, so no EII exemption applies.

Run:  python optimisation/levies.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from optimisation import trace as T  # noqa: E402

LEVY_FY = 2027                       # FY2026/27, as network_charges.TARIFF_FY

RO_ROC_PER_MWH = 0.472
RO_BUYOUT_GBP_PER_ROC = 69.34

# (Issue, quarter, levelisation fund £, supply MWh, EII-exempt supply MWh)
FIT_QUARTERS = (
    (62, "Jul-Sep 2025", 540_865_854.37, 58_141_564, 3_272_541),
    (63, "Oct-Dec 2025", 432_300_086.74, 67_525_489, 3_211_180),
    (64, "Jan-Mar 2026", 358_081_232.287, 70_354_600, 3_230_872),
    (65, "Apr-Jun 2026", 556_039_966.19, 59_217_531, 3_293_227),
)

# (first day, £/MWh) — each rate holds until the next row's first day. The
# in-period adjustments are the "Adjusted Rate" column, from their effective date.
CFD_ILR = (("2026-04-01", 10.260), ("2026-07-01", 10.559), ("2026-08-17", 2.068),
           ("2026-10-01", 5.529), ("2027-01-01", 2.979))
CFD_OPERATIONAL_GBP_PER_MWH = 0.1463

NUCLEAR_RAB_ILR = (("2026-04-01", 4.683), ("2026-07-01", 4.488),
                   ("2026-10-01", 3.754), ("2027-01-01", 3.676))
NUCLEAR_RAB_OPERATIONAL_GBP_PER_MWH = 0.0063

SUPPLIER_EBIT_MARGIN = 0.020                    # CMA 2015, Table 1, industrial and commercial, FY09-13
EXTRA_LARGE_PRICE_GBP_PER_MWH = 209.27          # DESNZ table 3.4.1, annual, 2025, electricity, extra large, excl. CCL
CM_SUPPLIER_CHARGE_GBP = 3_474_489_734.79       # Delivery Year 2026/27
CM_PEAK_DEMAND_MWH = 11_291_571.95
CM_MONTHS = (11, 12, 1, 2)
CM_HOURS = (16, 19)
# SIMPLIFIED: working days are taken as Monday-Friday; GB bank holidays in the
# window (Christmas, New Year) are charged too. They are 5-6 of ~85 days.
CM_BANK_HOLIDAYS_IGNORED = True

AAHEDC_P_PER_KWH = 0.044269

CCL_MAIN_GBP_PER_KWH = 0.00801
CCA_DISCOUNT = 0.92
CCL_UNDER_CCA = False                # ASSUMED: no Climate Change Agreement

# Offtaking share of transmission losses (TLMO-), 2026/27, by season (spring,
# summer, autumn, winter): Elexon's Estimated Transmission Loss Adjustment
# values, approved for use from 1 April 2026. Indicative, for reporting; the
# settlement figures sit behind the BSC Portal. Was an assumed flat 0.011
# until 4 Nov 2026 (evening).
TLMO_OFFTAKING_2026_27 = (0.00948, 0.01068, 0.00991, 0.00671)
# Adjusted Seasonal Zonal TLFs, BSC Year 2026/27, by Elexon TLF zone (= GSP
# group): (spring, summer, autumn, winter). Read to five decimals from Elexon's
# public interactive TLF report on 4 Nov 2026 (zone and season filters, the
# "TLF Value" card); until then read from the analysis report's charts, every
# value within 0.0005 of these. Spring is 1 Apr - 31 May and 1 - 31 Mar;
# summer Jun-Aug; autumn Sep-Nov; winter Dec-Feb.
TLF_ZONE_2026_27 = {
    1: (0.00490, 0.00440, 0.00831, 0.01150),       # _A Eastern
    2: (0.00902, 0.00667, 0.00923, 0.01210),       # _B East Midlands
    3: (0.01816, 0.01760, 0.02240, 0.03071),       # _C London
    4: (0.00715, 0.00148, 0.00246, 0.00206),       # _D Merseyside and North Wales
    5: (0.01692, 0.01335, 0.01639, 0.02151),       # _E Midlands
    6: (-0.00882, -0.00755, -0.01052, -0.01243),   # _F Northern
    7: (0.00005, -0.00448, -0.00502, -0.00364),    # _G North Western
    8: (0.01607, 0.01547, 0.02139, 0.03020),       # _H Southern
    9: (0.00851, 0.00878, 0.01309, 0.02235),       # _J South Eastern
    10: (0.01629, 0.01677, 0.01642, 0.02508),      # _K South Wales
    11: (0.01818, 0.01731, 0.02287, 0.03191),      # _L South Western
    12: (-0.00124, -0.00330, -0.00429, -0.00509),  # _M Yorkshire
    13: (-0.01192, -0.00664, -0.00993, -0.01641),  # _N South Scotland
    14: (-0.03234, -0.02004, -0.03045, -0.04943),  # _P North Scotland
}
# CI region -> Elexon TLF zone (both are GSP groups; report p. 5)
CI_REGION_TO_TLF_ZONE = {1: 14, 2: 13, 3: 7, 4: 6, 5: 12, 6: 4, 7: 10, 8: 5, 9: 2,
                         10: 1, 11: 11, 12: 8, 13: 3, 14: 9}
_TLF_SEASON = {3: 0, 4: 0, 5: 0, 6: 1, 7: 1, 8: 1, 9: 2, 10: 2, 11: 2, 12: 3, 1: 3, 2: 3}


def _fy_end() -> pd.Timestamp:
    return pd.Timestamp(LEVY_FY, 4, 1)


def _day_weighted(periods) -> float:
    starts = [pd.Timestamp(d) for d, _ in periods] + [_fy_end()]
    days = np.diff([s.value for s in starts]) / 86_400e9
    rates = np.array([r for _, r in periods])
    return float((rates * days).sum() / days.sum())


def fit_gbp_per_mwh() -> float:
    """Mean over the quarters of levelisation fund / (supply - exempt)."""
    return float(np.mean([fund / (supply - exempt)
                          for _, _, fund, supply, exempt in FIT_QUARTERS]))


def cfd_gbp_per_mwh() -> float:
    return _day_weighted(CFD_ILR) + CFD_OPERATIONAL_GBP_PER_MWH


def nuclear_rab_gbp_per_mwh() -> float:
    return _day_weighted(NUCLEAR_RAB_ILR) + NUCLEAR_RAB_OPERATIONAL_GBP_PER_MWH


def ccl_gbp_per_mwh(under_cca: bool | None = None) -> float:
    cca = CCL_UNDER_CCA if under_cca is None else under_cca
    return CCL_MAIN_GBP_PER_KWH * 1000.0 * ((1.0 - CCA_DISCOUNT) if cca else 1.0)


def flat_components(under_cca: bool | None = None) -> dict:
    """Every flat £/MWh levy, by name."""
    return {
        "RO": RO_ROC_PER_MWH * RO_BUYOUT_GBP_PER_ROC,
        "FiT": fit_gbp_per_mwh(),
        "CfD": cfd_gbp_per_mwh(),
        "AAHEDC": AAHEDC_P_PER_KWH * 10.0,
        "Nuclear RAB": nuclear_rab_gbp_per_mwh(),
        "CCL": ccl_gbp_per_mwh(under_cca),
        "Supplier margin": SUPPLIER_EBIT_MARGIN * EXTRA_LARGE_PRICE_GBP_PER_MWH,
    }


def cm_gbp_per_mwh_in_window() -> float:
    return CM_SUPPLIER_CHARGE_GBP / CM_PEAK_DEMAND_MWH


def _uk_clock(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    clock = pd.DatetimeIndex(index)
    return (clock.tz_localize("UTC") if clock.tz is None else clock).tz_convert("Europe/London")


def cm_window(index: pd.DatetimeIndex) -> pd.Series:
    """True in the CM charging window. Read on the UK clock, as the DUoS bands
    are — the study's series are naive UTC."""
    clock = _uk_clock(index)
    on = ((clock.dayofweek < 5) & clock.month.isin(CM_MONTHS)
          & (clock.hour >= CM_HOURS[0]) & (clock.hour < CM_HOURS[1]))
    return pd.Series(on, index=index, name="cm_window")


def llf_period(index: pd.DatetimeIndex, region: int = 13) -> np.ndarray:
    """The area's LLF time period for every step (UK clock); see
    ``duos_areas.LLF_PERIOD_RULES``."""
    from optimisation import duos_areas
    return duos_areas.llf_period(index, region)


def tlm_series(index: pd.DatetimeIndex, region: int) -> pd.Series:
    """Offtaking TLM for every step: 1 + the zone's TLF for the season + TLMO-."""
    tlf = np.asarray(TLF_ZONE_2026_27[CI_REGION_TO_TLF_ZONE[region]])
    tlmo = np.asarray(TLMO_OFFTAKING_2026_27)
    season = np.vectorize(_TLF_SEASON.get)(np.asarray(_uk_clock(index).month))
    return pd.Series(1.0 + tlf[season] + tlmo[season], index=index, name="tlm")


def loss_series(index: pd.DatetimeIndex, connection_voltage: str, region: int) -> pd.Series:
    """Energy bought per MWh metered: the area's LLF for the connection voltage
    and period, times the zone's offtaking TLM for the season."""
    from optimisation import duos_areas
    llf = duos_areas.llf_series(index, region, connection_voltage).to_numpy()
    tlm = tlm_series(index, region).to_numpy()
    if T.active():
        k = f"cost.losses.r{region}.{connection_voltage}"
        zone = CI_REGION_TO_TLF_ZONE[region]
        llf_src = (f"llf_file.{region}" if region in duos_areas.LLF_FILES else f"duos_schedule.{region}")
        T.cost(f"{k}.llf_mean", float(llf.mean()), "multiplier",
               f"Line loss factor, {duos_areas.AREA_NAMES[region]}, {connection_voltage}: mean over the window",
               grade="transcribed" if connection_voltage != "transmission" else "derived",
               cites=[] if connection_voltage == "transmission" else
               [(llf_src, f"Annex 5, generic demand LLFs, {connection_voltage} row, by time period")],
               note="1.0 for a transmission site: no distribution loss")
        T.cost("cost.losses.tlmo_offtaking", float(np.mean(TLMO_OFFTAKING_2026_27)), "fraction",
               "Offtaking share of transmission losses (TLMO-), Elexon's 2026/27 estimates by season, mean of the four",
               grade="transcribed", inputs={s: v for s, v in zip(("spring", "summer", "autumn", "winter"),
                                                                 TLMO_OFFTAKING_2026_27)},
               cites=[("elexon_etlmo_2026_27", "ETLMOj- by season, approved for use from 1 April 2026")],
               note="Indicative values for reporting; the settlement figures are behind the BSC Portal")
        T.cost(f"cost.losses.tlm_zone{zone}_mean", float(tlm.mean()), "multiplier",
               f"Transmission loss multiplier, TLF zone {zone}: 1 + seasonal zonal TLF + seasonal TLMO-, mean over the window",
               uses=["cost.losses.tlmo_offtaking"],
               cites=[("elexon_tlf_public_report", f"TLF Value card, zone {zone}, BSC year 26-27: "
                                                   f"{', '.join(f'{v:+.5f}' for v in TLF_ZONE_2026_27[zone])} "
                                                   "(spring, summer, autumn, winter)")])
        T.cost(f"{k}.mean", float((llf * tlm).mean()), "multiplier",
               f"Energy bought per MWh metered at {connection_voltage}: LLF x TLM, mean over the window",
               uses=[f"{k}.llf_mean", f"cost.losses.tlm_zone{zone}_mean"],
               note="The product is taken half-hour by half-hour; its mean is not the product of the means")
    return pd.Series(llf * tlm, index=index, name="loss_gross_up")


def _record_levies(flat: dict, cm: pd.Series, series: pd.Series, under_cca: bool | None):
    """Each levy for the cost map, with the document it was read from."""
    fy = f"{LEVY_FY - 1}/{str(LEVY_FY)[2:]}"
    cca = CCL_UNDER_CCA if under_cca is None else under_cca
    T.cost("cost.levy.RO", flat["RO"], "GBP per MWh", "Renewables Obligation: ROCs per MWh x buy-out price",
           grade="derived", inputs={"ROC_per_MWh": RO_ROC_PER_MWH, "GBP_per_ROC": RO_BUYOUT_GBP_PER_ROC},
           cites=[("ofgem_ro_2026_27", f"{fy}: buy-out £{RO_BUYOUT_GBP_PER_ROC} per ROC, obligation "
                                       f"{RO_ROC_PER_MWH} ROCs per MWh")])
    T.cost("cost.levy.FiT", flat["FiT"], "GBP per MWh",
           "Feed-in Tariff levelisation: fund / (supply - exempt supply), mean of four quarters", grade="derived",
           cites=[("ofgem_fit_quarterly", "Issues " + ", ".join(str(q[0]) for q in FIT_QUARTERS))],
           inputs={q[1]: q[2] / (q[3] - q[4]) for q in FIT_QUARTERS})
    T.cost("cost.levy.CfD", flat["CfD"], "GBP per MWh",
           "Contracts for Difference: interim levy rates day-weighted over the year, plus the operational levy",
           grade="derived", inputs={"operational_GBP_per_MWh": CFD_OPERATIONAL_GBP_PER_MWH},
           cites=[("emr_key_figures_2026_27", "§1 and §3, interim levy rates and in-period adjustments")])
    T.cost("cost.levy.AAHEDC", flat["AAHEDC"], "GBP per MWh",
           "Highlands and Islands distribution subsidy (AAHEDC): p/kWh x 10", grade="transcribed",
           cites=[("neso_aahedc_2026_27", f"Schedule 1: {AAHEDC_P_PER_KWH} p/kWh")])
    T.cost("cost.levy.Nuclear_RAB", flat["Nuclear RAB"], "GBP per MWh",
           "Nuclear funding (RAB): interim levy rates day-weighted, plus the operational levy", grade="derived",
           inputs={"operational_GBP_per_MWh": NUCLEAR_RAB_OPERATIONAL_GBP_PER_MWH},
           cites=[("emr_key_figures_2026_27", "§5 and §7")])
    T.cost("cost.levy.CCL_under_agreement", float(cca), "yes (1) / no (0)",
           "Whether the site holds a Climate Change Agreement (92 % off the levy)", grade="assumed",
           note="levies.CCL_UNDER_CCA: data centres are eligible; whether this one holds one is not known")
    T.cost("cost.levy.CCL", flat["CCL"], "GBP per MWh", "Climate Change Levy on electricity",
           uses=["cost.levy.CCL_under_agreement"],
           cites=[("govuk_ccl_rates", f"£{CCL_MAIN_GBP_PER_KWH}/kWh from 1 April 2026; {CCA_DISCOUNT:.0%} off "
                                      "under an agreement")])
    T.cost("cost.levy.CM_in_window", cm_gbp_per_mwh_in_window(), "GBP per MWh",
           "Capacity Market: total payments / peak-period demand, charged 4-7 pm on working days, Nov-Feb",
           grade="derived", inputs={"payments_GBP": CM_SUPPLIER_CHARGE_GBP, "peak_demand_MWh": CM_PEAK_DEMAND_MWH},
           cites=[("emr_key_figures_2026_27", "§9 and §12, Delivery Year 2026/27")],
           note="Working days taken as Monday-Friday: the window's bank holidays are charged too")
    T.cost("cost.levy.CM_mean", float(cm.mean()), "GBP per MWh",
           "Capacity Market, mean over the window on a flat load", uses=["cost.levy.CM_in_window"],
           inputs={"share_of_half_hours_in_window": float((cm > 0).mean())})
    T.cost("cost.levy.supplier_margin", flat["Supplier margin"], "GBP per MWh",
           "Supplier margin: an estimate that fails the 1 % test if left out", grade="proxy",
           inputs={"ebit_margin": SUPPLIER_EBIT_MARGIN, "price_GBP_per_MWh": EXTRA_LARGE_PRICE_GBP_PER_MWH},
           cites=[("cma_retail_profitability_2015", "Table 1, industrial and commercial, 2.0 %, FY09-13"),
                  ("desnz_nondomestic_prices", "table 3.4.1, annual, 2025, electricity, extra large")])
    T.cost("cost.levy.mean_per_MWh", float(series.mean()), "GBP per MWh",
           "Every policy levy and the supplier margin on metered imports, mean over the window",
           uses=["cost.levy.RO", "cost.levy.FiT", "cost.levy.CfD", "cost.levy.AAHEDC", "cost.levy.Nuclear_RAB",
                 "cost.levy.CCL", "cost.levy.supplier_margin", "cost.levy.CM_mean"])


def import_levies(index: pd.DatetimeIndex, under_cca: bool | None = None) -> dict:
    """The levy part of the import price: a £/MWh series on metered imports,
    and its parts for reporting."""
    flat = flat_components(under_cca)
    cm = cm_window(index).astype(float) * cm_gbp_per_mwh_in_window()
    series = (sum(flat.values()) + cm).rename("levies_GBP_per_MWh")
    if T.active():
        _record_levies(flat, cm, series, under_cca)
    return {"levies_GBP_per_MWh": series,
            "components": {**{f"{k}_GBP_per_MWh": v for k, v in flat.items()},
                           "CM_GBP_per_MWh_in_window": cm_gbp_per_mwh_in_window(),
                           "CM_mean_GBP_per_MWh": float(cm.mean()),
                           "flat_GBP_per_MWh": sum(flat.values()),
                           "ccl_under_cca": CCL_UNDER_CCA if under_cca is None else under_cca,
                           "levy_fy": LEVY_FY}}


if __name__ == "__main__":
    idx = pd.date_range("2025-01-01", "2025-12-29", freq="30min")
    lv = import_levies(idx)
    c = lv["components"]
    print("=" * 72)
    print(f"IMPORT LEVIES — FY{LEVY_FY - 1}/{str(LEVY_FY)[2:]}, £/MWh metered")
    print("=" * 72)
    for k in ("RO", "FiT", "CfD", "AAHEDC", "Nuclear RAB", "CCL"):
        print(f"  {k:<14}{c[k + '_GBP_per_MWh']:>8.2f}")
    print(f"  {'flat total':<14}{c['flat_GBP_per_MWh']:>8.2f}")
    print(f"  {'CM, in window':<14}{c['CM_GBP_per_MWh_in_window']:>8.2f}"
          f"   ({cm_window(idx).mean():.1%} of half-hours; {c['CM_mean_GBP_per_MWh']:.2f} on a flat load)")
    print(f"  {'mean, flat load':<14}{lv['levies_GBP_per_MWh'].mean():>8.2f}")
    print("\n  FiT by quarter: " + ", ".join(
        f"{q} {fund / (s - e):.2f}" for _, q, fund, s, e in FIT_QUARTERS))
    from optimisation import duos_areas
    for r in sorted(duos_areas.FILES):
        parts = []
        for v in ("11 kV", "33 kV", "132 kV"):
            try:
                parts.append(f"{v} x{loss_series(idx, v, r).mean():.4f}")
            except ValueError:
                parts.append(f"{v} —")
        flag = " (ASSUMED)" if r in duos_areas.LLF_ASSUMED_REGIONS else ""
        print(f"  Losses, {duos_areas.AREA_NAMES[r][:34]:<34} " + "  ".join(parts) + flag
              + f"   (TLM mean x{tlm_series(idx, r).mean():.4f})")
    print(f"  CCL under a CCA would be {ccl_gbp_per_mwh(True):.2f} rather than "
          f"{ccl_gbp_per_mwh(False):.2f} (CCL_UNDER_CCA = {CCL_UNDER_CCA}).")
