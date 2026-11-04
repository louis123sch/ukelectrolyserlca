"""
One price base: real 2025 pounds.
=============================================================================

Cost figures arrive in their source's own year. ``to_2025`` is the one factor
that brings them to 2025, the base FES 2025 reports in ("adjusted using the GDP
deflator", FES 2025 Economics Assumptions, Costing Assumptions, row 78).

Source: ONS, Gross domestic product at market prices: Implied deflator: SA,
series YBGB, 2024 = 100, release of 30 Sep 2026. Live at
www.ons.gov.uk/economy/grossdomesticproductgdp/timeseries/ybgb/qna/data, and
``scripts/check_price_base.py`` compares these constants with it. The series is
revised at each release, so a figure quoted here moves slightly with the next.

Run:  python scripts/check_price_base.py
"""
from __future__ import annotations

from optimisation import trace as T

BASE_YEAR = 2025
GDP_DEFLATOR = {2015: 75.2, 2016: 76.5, 2017: 77.7, 2018: 79.2, 2019: 81.1, 2020: 84.9,
                2021: 85.7, 2022: 90.6, 2023: 96.3, 2024: 100.0, 2025: 103.6}


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
