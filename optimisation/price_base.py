"""
One price base: real 2026 pounds, reached through 2025.
=============================================================================

The model answers "what should I build on this site, going forward", so every
pound the LP charges is a 2026 pound (decided 9 Nov 2026). Two steps get there:

1. ``to_2025`` brings a source's own year to 2025, the base FES 2025 reports in
   ("adjusted using the GDP deflator", FES 2025 Economics Assumptions, Costing
   Assumptions, row 78). The coefficient modules (tech_costs, battery,
   h2_capex, h2_prices, ...) all work in 2025 pounds, and their figures and
   tests stay there.
2. ``to_2026`` is the one factor from 2025 to 2026 pounds. ``dc_inputs`` applies
   it where the LP's coefficients are made, to everything that is in 2025
   pounds: the assets, bought hydrogen, gas, and the run window's wholesale
   prices (each year's own factor, ``factor_to_2026``). The 2026/27 network
   charges, levies and the 2026 connection price lists are already 2026 money
   and are not touched.

Sources: ONS, Gross domestic product at market prices: Implied deflator: SA,
series YBGB, 2024 = 100, release of 30 Sep 2026 (outturn, to 2025). Live at
www.ons.gov.uk/economy/grossdomesticproductgdp/timeseries/ybgb/qna/data, and
``scripts/check_price_base.py`` compares these constants with it. The series is
revised at each release, so a figure quoted here moves slightly with the next.
2025 to 2026: HM Treasury, *GDP deflators at market prices, and money GDP:
October 2026 (Budget)*, calendar-year column, 2026 per cent change, the OBR's
October 2026 forecast (calendar 2026 is not yet outturn). Replace with the ONS
outturn once 2026 is complete.

Run:  python scripts/check_price_base.py
"""
from __future__ import annotations

from optimisation import trace as T

BASE_YEAR = 2025                     # the coefficient modules' common year
TARGET_YEAR = 2026                   # what the LP charges in
GDP_DEFLATOR = {2013: 73.7, 2014: 74.8, 2015: 75.2, 2016: 76.5, 2017: 77.7, 2018: 79.2, 2019: 81.1, 2020: 84.9,
                2021: 85.7, 2022: 90.6, 2023: 96.3, 2024: 100.0, 2025: 103.6}
# HM Treasury GDP deflators, Budget October 2026: calendar 2026, per cent change on
# 2025, as printed (OBR October 2026 EFO forecast). A forecast, not outturn.
GROWTH_2025_TO_2026 = 0.02960715861888752

# Foreign figures are inflated in their own currency, then converted at the FES
# 2025 Data Workbook's 2025 cross-rates, the one table every conversion in the
# study traces to (£1 = €1.17; $1 = €0.913).
EUR_PER_GBP_2025 = 1.17
USD_PER_GBP_2025 = 1.17 / 0.913
# World Bank, GDP deflator (base year varies by country), NY.GDP.DEFL.ZS, United
# States, fetched 4 Nov 2026 from api.worldbank.org (2020 = 100).
US_GDP_DEFLATOR = {2019: 98.7, 2020: 100.0, 2021: 104.6, 2022: 112.0, 2023: 116.1, 2024: 119.0, 2025: 122.4}
# Eurostat nama_10_gdp, euro area (EA20), price index PD15_EUR (2015 = 100),
# fetched 4 Nov 2026 from the Eurostat dissemination API.
EURO_AREA_GDP_DEFLATOR = {2015: 100.0, 2016: 100.875, 2017: 102.009, 2018: 103.537, 2019: 105.271, 2020: 107.183,
                          2021: 109.389, 2022: 114.963, 2023: 122.176, 2024: 125.756, 2025: 128.705}


def usd_to_gbp_2025(value_usd: float, year: int) -> float:
    """US dollars of ``year`` to 2025 pounds, unrecorded."""
    return value_usd * US_GDP_DEFLATOR[BASE_YEAR] / US_GDP_DEFLATOR[year] / USD_PER_GBP_2025


def eur_to_gbp_2025(value_eur: float, year: int) -> float:
    """Euros of ``year`` to 2025 pounds, unrecorded."""
    return value_eur * EURO_AREA_GDP_DEFLATOR[BASE_YEAR] / EURO_AREA_GDP_DEFLATOR[year] / EUR_PER_GBP_2025


def record_fx() -> None:
    """The two cross-rates, recorded once for the cost map."""
    T.cost("fx.eur_per_gbp_2025", EUR_PER_GBP_2025, "€ per £", "2025 cross-rate, £ to €",
           grade="transcribed", cites=[("fes_2025_workbook", "cross-rates, 2025: £1 = €1.17")])
    T.cost("fx.usd_per_gbp_2025", USD_PER_GBP_2025, "US $ per £", "2025 cross-rate, £ to US $",
           grade="transcribed", cites=[("fes_2025_workbook", "cross-rates, 2025: £1 = €1.17, $1 = €0.913")])


def record_foreign(currency: str, year: int) -> str:
    """Record one foreign deflator step and return its key."""
    if currency == "usd":
        key = f"price_base.usd_{year}_to_{BASE_YEAR}"
        T.cost(key, US_GDP_DEFLATOR[BASE_YEAR] / US_GDP_DEFLATOR[year], "multiplier",
               f"US GDP deflator, {year} dollars to {BASE_YEAR} dollars", grade="derived",
               cites=[("worldbank_us_gdp_deflator", f"NY.GDP.DEFL.ZS, {year} and {BASE_YEAR}")])
    elif currency == "eur":
        key = f"price_base.eur_{year}_to_{BASE_YEAR}"
        T.cost(key, EURO_AREA_GDP_DEFLATOR[BASE_YEAR] / EURO_AREA_GDP_DEFLATOR[year], "multiplier",
               f"Euro-area GDP deflator, {year} euros to {BASE_YEAR} euros", grade="derived",
               cites=[("eurostat_ea_gdp_deflator", f"nama_10_gdp, EA20, PD15_EUR, {year} and {BASE_YEAR}")])
    else:
        raise ValueError(f"currency must be 'usd' or 'eur', got {currency!r}")
    return key


def factor(year: int) -> float:
    """The multiplier from ``year``'s pounds to 2025's, unrecorded."""
    if year not in GDP_DEFLATOR:
        raise KeyError(f"no GDP deflator for {year}; held {min(GDP_DEFLATOR)}-{max(GDP_DEFLATOR)}")
    return GDP_DEFLATOR[BASE_YEAR] / GDP_DEFLATOR[year]


def to_2025(year: int) -> float:
    """``factor`` recorded for the cost map."""
    return T.cost(f"price_base.{year}_to_{BASE_YEAR}", factor(year), "multiplier",
                  f"GDP deflator, {year} pounds to {BASE_YEAR} pounds", grade="derived",
                  cites=[("ons_gdp_deflator", f"series YBGB, {year} and {BASE_YEAR}")],
                  inputs={str(year): GDP_DEFLATOR[year], str(BASE_YEAR): GDP_DEFLATOR[BASE_YEAR]})


FACTOR_2025_TO_2026 = 1.0 + GROWTH_2025_TO_2026
KEY_2025_TO_2026 = f"price_base.{BASE_YEAR}_to_{TARGET_YEAR}"


def to_2026() -> float:
    """2025 pounds to 2026 pounds, recorded for the cost map; returns the multiplier."""
    return T.cost(KEY_2025_TO_2026, FACTOR_2025_TO_2026, "multiplier",
                  f"GDP deflator, {BASE_YEAR} pounds to {TARGET_YEAR} pounds: the price base every pound the "
                  "model charges is in", grade="transcribed",
                  cites=[("hmt_gdp_deflators_oct_2026", "calendar years, 2026, per cent change on previous year: "
                                                        f"{GROWTH_2025_TO_2026 * 100:.4f} %")],
                  note="The OBR's October 2026 forecast for calendar 2026: a forecast, not outturn")


def factor_to_2026(year: int) -> float:
    """The multiplier from ``year``'s pounds to 2026's, unrecorded. 2026 is 1."""
    if year == TARGET_YEAR:
        return 1.0
    if year > TARGET_YEAR:
        raise KeyError(f"no deflator for {year}: the price base is {TARGET_YEAR}")
    return factor(year) * FACTOR_2025_TO_2026


def record_to_2026(year: int) -> list[str]:
    """Record the steps from ``year``'s pounds to 2026's and return their keys."""
    if year == TARGET_YEAR:
        return []
    keys = []
    if year != BASE_YEAR:
        to_2025(year)
        keys.append(f"price_base.{year}_to_{BASE_YEAR}")
    to_2026()
    return keys + [KEY_2025_TO_2026]
