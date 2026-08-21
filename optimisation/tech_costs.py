"""
Generation cost and technical assumptions — DESNZ/Arup 2024.
=============================================================================

Single source of truth for onshore wind, offshore wind and solar PV costs,
transcribed from the two DESNZ/Arup "Cost of Electricity Report Update 2024"
reports. All values are **2023 real prices**.

Sources
-------
onshore wind, solar PV
    DESNZ / Ove Arup & Partners, "Renewable Energy Generation Cost and
    Technical Assumptions - Onshore Wind and Solar PV, Cost of Electricity
    Report Update 2024", ref 299867-00, Final, 14 July 2025.
    Onshore wind = Table 3 (p.6); Solar PV (>5MW) = Table 4 (p.7);
    LCOE = Table 5 (p.8).

offshore wind
    DESNZ / Ove Arup & Partners, "Renewable Energy Generation Cost and
    Technical Assumptions - Offshore Wind, Cost of Electricity Report Update
    2024", Final, 24 July 2025. Table 3 (p.6); LCOE = Table 4 (p.7).

Notes on the numbers
--------------------
* Solar PV costs are per **kWp / MWp** (peak DC), not per MW AC. Anything that
  converts a PV build decision into MW AC has to apply its own DC:AC ratio.
* Offshore wind infrastructure cost **excludes** OFTO transmission assets;
  those are recovered through TNUoS inside the opex line instead (report
  footnote 6). Do not add a separate transmission capex on top.
* Hurdle rates differ by technology (5.8 / 6.2 / 5.0 %) and are pre-tax real.
  They are the report's own financing assumption, not necessarily the WACC
  this study should use - see ``DISCOUNT_RATE_OVERRIDE``.
* "low/medium/high" are the report's own scenario labels. This module exposes
  them as low/central/high to match ``dashboard_config.COST_CASE``.

Every number in this module is listed in ``SOURCES.md`` alongside its
source and provenance grade (transcribed / derived / assumed).

The onshore wind block duplicates values already written by
``5.prices.ipynb`` into ``price_outputs/static_cost_assumptions.csv``.
``check_against_price_outputs()`` asserts the two agree, so they cannot
silently drift apart.
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PRICE_DIR = ROOT / "price_outputs"
OUT_DIR = ROOT / "optimisation_outputs"

ONSHORE_SOLAR_SOURCE = (
    "DESNZ/Arup 2024 Onshore Wind and Solar PV cost report (ref 299867-00, "
    "Final 14 July 2025)"
)
OFFSHORE_SOURCE = (
    "DESNZ/Arup 2024 Offshore Wind cost report (Final 24 July 2025)"
)

# Set to a number to use one project-wide discount rate for every technology
# instead of each report's own hurdle rate. None = use the report hurdle rates.
DISCOUNT_RATE_OVERRIDE = None


# (parameter, unit, low, central, high)
ONSHORE_WIND = [
    ("predevelopment_capex",  "GBP_per_kW",        36.0,   81.0,   199.0),
    ("construction_capex",    "GBP_per_kW",       963.0, 1204.0,  1603.0),
    ("infrastructure_capex",  "GBP_per_kW",       242.0,  303.0,   403.0),
    ("total_capex",           "GBP_per_kW",      1241.0, 1588.0,  2205.0),
    ("insurance",             "kGBP_per_MW_year",   2.2,    3.6,     4.4),
    ("connection_and_uos",    "kGBP_per_MW_year",   0.4,   17.0,    45.3),
    ("om",                    "kGBP_per_MW_year",  14.8,   19.5,    22.8),
    ("total_opex",            "kGBP_per_MW_year",  17.4,   40.1,    72.4),
    ("net_load_factor",       "fraction",         0.330,  0.381,   0.413),
    ("operating_lifetime",    "years",             25.0,   35.0,    40.0),
    ("hurdle_rate",           "fraction",         0.058,  0.058,   0.058),
    ("predevelopment_period", "years",              5.0,    8.0,    13.0),
    ("construction_period",   "years",              1.0,    2.0,     3.0),
    ("reported_lcoe",         "GBP_per_MWh",       27.2,   45.8,    90.6),
]

OFFSHORE_WIND = [
    ("predevelopment_capex",  "GBP_per_kW",       104.0,  216.0,   308.0),
    ("construction_capex",    "GBP_per_kW",      2415.0, 2823.0,  3101.0),
    ("infrastructure_capex",  "GBP_per_kW",       802.0,  937.0,  1030.0),
    ("total_capex",           "GBP_per_kW",      3321.0, 3976.0,  4439.0),
    ("insurance",             "kGBP_per_MW_year",   8.0,    8.6,     9.7),
    ("connection_and_uos",    "kGBP_per_MW_year",  35.3,   83.4,   132.9),
    ("om",                    "kGBP_per_MW_year",  30.5,   46.5,    64.6),
    ("total_opex",            "kGBP_per_MW_year",  73.7,  138.5,   207.2),
    ("net_load_factor",       "fraction",         0.460,  0.505,   0.561),
    ("operating_lifetime",    "years",             35.0,   35.0,    35.0),
    ("hurdle_rate",           "fraction",         0.062,  0.062,   0.062),
    ("predevelopment_period", "years",              7.0,    7.0,    15.0),
    ("construction_period",   "years",              4.0,    5.0,     5.0),
    ("reported_lcoe",         "GBP_per_MWh",       55.4,   88.5,   124.0),
]

# Per kWp / MWp of peak DC capacity, not MW AC.
SOLAR_PV = [
    ("predevelopment_capex",  "GBP_per_kWp",       12.0,   24.0,    59.0),
    ("construction_capex",    "GBP_per_kWp",      423.0,  522.0,   601.0),
    ("infrastructure_capex",  "GBP_per_kWp",       91.0,  112.0,   129.0),
    ("total_capex",           "GBP_per_kWp",      526.0,  659.0,   788.0),
    ("insurance",             "kGBP_per_MWp_year",  0.8,    1.6,     2.7),
    ("connection_and_uos",    "kGBP_per_MWp_year",  1.1,    1.6,     2.0),
    ("om",                    "kGBP_per_MWp_year",  4.5,    6.1,     7.6),
    ("total_opex",            "kGBP_per_MWp_year",  6.5,    9.3,    12.3),
    ("net_load_factor",       "fraction",         0.115,  0.122,   0.145),
    ("operating_lifetime",    "years",             35.0,   38.0,    40.0),
    ("hurdle_rate",           "fraction",         0.050,  0.050,   0.050),
    ("predevelopment_period", "years",              1.0,    3.0,     4.0),
    ("construction_period",   "years",              1.0,    1.0,     1.0),
    ("reported_lcoe",         "GBP_per_MWh",       30.3,   46.5,    65.2),
]

TECHNOLOGIES = {
    "onshore_wind":  (ONSHORE_WIND,  ONSHORE_SOLAR_SOURCE,
                      "Table 3, p.6"),
    "offshore_wind": (OFFSHORE_WIND, OFFSHORE_SOURCE,
                      "Table 3, p.6; infrastructure excludes OFTO "
                      "(recovered via TNUoS in opex)"),
    "solar_pv":      (SOLAR_PV,      ONSHORE_SOLAR_SOURCE,
                      "Table 4, p.7; >5MW; per kWp/MWp peak DC"),
}

CASES = ("low", "central", "high")


def capital_recovery_factor(rate, lifetime_years):
    """Annualise a capital sum over its life. Mirrors dashboard_config's."""
    rate = float(rate)
    lifetime_years = float(lifetime_years)
    if lifetime_years <= 0:
        raise ValueError("lifetime_years must be positive")
    if rate == 0:
        return 1.0 / lifetime_years
    return rate * (1.0 + rate) ** lifetime_years / ((1.0 + rate) ** lifetime_years - 1.0)


def long_table():
    """Every parameter, every technology, every case — one tidy row each."""
    rows = []
    for tech, (params, source, note) in TECHNOLOGIES.items():
        for parameter, unit, low, central, high in params:
            rows.append({
                "asset": tech, "parameter": parameter, "unit": unit,
                "low": low, "central": central, "high": high,
                "source": source, "notes": note,
            })
    return pd.DataFrame(rows)


def _value(params, parameter, case):
    idx = {"low": 2, "central": 3, "high": 4}[case]
    for row in params:
        if row[0] == parameter:
            return row[idx]
    raise KeyError(parameter)


INVERSE_CASE = {"low": "high", "central": "central", "high": "low"}


def annualised_table():
    """Annualised £/MW/y and an LCOE cross-check against the report's own.

    Capacity is per MW for wind and per MWp for solar.

    The report's low/high scenarios do **not** pair like with like. From p.7:
    low costs are combined with the *high* net load factor and *high*
    operating lifetime (a bigger, longer-lived project generates more), and
    the high-cost scenario takes the low values. ``INVERSE_CASE`` reproduces
    that pairing, which is what makes the LCOE cross-check meaningful.

    The residual ``lcoe_delta_pct`` is methodological: this is a plain CRF
    annuity over the operating life, whereas the report uses the DESNZ LCOE
    calculator, which also spreads pre-development and construction spend
    across the build period and discounts it. It is not a transcription error.
    """
    rows = []
    for tech, (params, source, note) in TECHNOLOGIES.items():
        for case in CASES:
            inv = INVERSE_CASE[case]
            capex_per_kw = _value(params, "total_capex", case)
            opex_kgbp = _value(params, "total_opex", case)
            life = _value(params, "operating_lifetime", inv)
            lf = _value(params, "net_load_factor", inv)
            rate = (DISCOUNT_RATE_OVERRIDE if DISCOUNT_RATE_OVERRIDE is not None
                    else _value(params, "hurdle_rate", case))

            capex_per_mw = capex_per_kw * 1000.0
            opex_per_mw = opex_kgbp * 1000.0
            crf = capital_recovery_factor(rate, life)
            ann_capex = capex_per_mw * crf
            total_annual = ann_capex + opex_per_mw
            mwh_per_mw_yr = 8760.0 * lf
            lcoe = total_annual / mwh_per_mw_yr
            reported = _value(params, "reported_lcoe", case)

            rows.append({
                "asset": tech, "case": case,
                "technical_case": inv,
                "capex_GBP_per_MW": capex_per_mw,
                "opex_GBP_per_MW_year": opex_per_mw,
                "lifetime_years": life,
                "discount_rate": rate,
                "crf": crf,
                "annualised_capex_GBP_per_MW_year": ann_capex,
                "total_annual_cost_GBP_per_MW_year": total_annual,
                "net_load_factor": lf,
                "MWh_per_MW_year": mwh_per_mw_yr,
                "lcoe_GBP_per_MWh": lcoe,
                "reported_lcoe_GBP_per_MWh": reported,
                "lcoe_delta_pct": 100.0 * (lcoe / reported - 1.0),
                "source": source,
            })
    return pd.DataFrame(rows)


def check_against_price_outputs():
    """Assert the onshore wind rows agree with 5.prices.ipynb's own output."""
    path = PRICE_DIR / "static_cost_assumptions.csv"
    if not path.exists():
        return f"skipped — {path.name} not found (run 5.prices.ipynb)"
    existing = pd.read_csv(path)
    existing = existing[existing["asset"] == "onshore_wind"]
    if existing.empty:
        return "skipped — no onshore_wind rows in static_cost_assumptions.csv"

    mine = long_table()
    mine = mine[mine["asset"] == "onshore_wind"].set_index("parameter")
    mismatches = []
    for _, row in existing.iterrows():
        p = row["parameter"]
        if p not in mine.index:
            continue
        for case in CASES:
            a, b = float(row[case]), float(mine.loc[p, case])
            if abs(a - b) > 1e-9:
                mismatches.append(f"{p}/{case}: prices.ipynb={a} vs PDF={b}")
    if mismatches:
        raise AssertionError(
            "onshore wind costs disagree with price_outputs/:\n  "
            + "\n  ".join(mismatches)
        )
    n = len(set(existing["parameter"]) & set(mine.index))
    return f"OK — {n} onshore wind parameters match 5.prices.ipynb exactly"


def run():
    long_df = long_table()
    ann_df = annualised_table()

    print("=" * 88)
    print("DESNZ/Arup 2024 generation cost assumptions (2023 real prices)")
    print("=" * 88)
    print(check_against_price_outputs())

    print()
    print("Headline capex / opex / load factor, central case")
    print("-" * 88)
    print(f"{'technology':<16}{'capex':>14}{'opex':>16}{'LF':>9}{'life':>7}{'rate':>8}")
    print(f"{'':<16}{'GBP/MW':>14}{'GBP/MW/y':>16}{'':>9}{'y':>7}{'':>8}")
    for _, r in ann_df[ann_df.case == "central"].iterrows():
        print(f"{r.asset:<16}{r.capex_GBP_per_MW:>14,.0f}"
              f"{r.opex_GBP_per_MW_year:>16,.0f}{r.net_load_factor:>9.1%}"
              f"{r.lifetime_years:>7.0f}{r.discount_rate:>8.1%}")

    print()
    print("LCOE cross-check — plain CRF annuity vs the report's own calculator")
    print("-" * 88)
    print(f"{'technology':<16}{'case':<9}{'this module':>14}{'report':>10}{'delta':>9}")
    for _, r in ann_df.iterrows():
        print(f"{r.asset:<16}{r.case:<9}{r.lcoe_GBP_per_MWh:>14.1f}"
              f"{r.reported_lcoe_GBP_per_MWh:>10.1f}{r.lcoe_delta_pct:>8.1f}%")

    OUT_DIR.mkdir(exist_ok=True)
    p1 = OUT_DIR / "generation_costs_desnz2024.csv"
    p2 = OUT_DIR / "generation_costs_annualised.csv"
    long_df.to_csv(p1, index=False)
    ann_df.to_csv(p2, index=False)
    print()
    print("Wrote:")
    print(" ", p1.relative_to(ROOT))
    print(" ", p2.relative_to(ROOT))
    return long_df, ann_df


if __name__ == "__main__":
    run()
