"""
Generation cost and technical assumptions — DESNZ/Arup 2024.
=============================================================================

Single source of truth for onshore wind, offshore wind and solar PV costs,
transcribed from the two DESNZ/Arup "Cost of Electricity Report Update 2024"
reports. Every value transcribed here is in **2023 real prices**; the coefficient
``annual_cost`` hands the LP is in 2025 pounds (``price_base``).

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
* The report's hurdle rates (5.8 / 6.2 / 5.0 %, pre-tax real) are kept for
  its LCOE cross-check. The coefficient itself is annualised at CEPA's 2025
  rates for DESNZ (``CEPA_HURDLE_RATE``), the one method the study applies to
  every asset - see ``DISCOUNT_RATE_OVERRIDE`` to impose a single rate.
* "low/medium/high" are the report's own scenario labels. This module exposes
  them as low/central/high to match ``dc_config.COST_CASE``.

Every number in this module is listed in ``SOURCES.md`` alongside its
source and provenance grade (transcribed / derived / assumed).

The onshore wind block was transcribed independently a second time by the
(since retired) ``5.prices.ipynb``, into ``price_outputs/static_cost_assumptions.csv``.
That file is kept as a frozen cross-check: ``check_against_price_outputs()``
asserts the two transcriptions agree.
"""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from optimisation import price_base as P  # noqa: E402
from optimisation import trace as T  # noqa: E402
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
# instead of the rates below. None = use CEPA's.
DISCOUNT_RATE_OVERRIDE = None

# The rate the LP's coefficient is annualised at, since 4 Nov 2026 (evening):
# CEPA for DESNZ, hurdle rate estimates for electricity sector technologies
# (2025), Table E.1, pre-tax real, 50 % gearing. The report's own hurdle rates
# (5.8 / 6.2 / 5.0 %) are kept for the LCOE cross-check only.
CEPA_HURDLE_RATE = {"onshore_wind": 0.076, "solar_pv": 0.076, "offshore_wind": 0.089}


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
    # Outside the report's LCOE and opex; asked separately (§3.8). Low and high
    # are the published range, central the average. §5.8.1 and §5.8.2.
    ("land",                  "kGBP_per_MW_year",   9.0,   19.5,    36.0),
    ("business_rates",        "kGBP_per_MW_year",  10.0,   12.0,    24.0),
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
    # §6.8.1 per acre of land, so SOLAR_ACRES_PER_MWP turns it into a coefficient;
    # §6.8.2 per MW, read here as per MWp.
    ("land_per_acre",         "kGBP_per_acre_year", 0.8,    1.0,     1.0),
    ("business_rates",        "kGBP_per_MWp_year",  1.0,    1.8,     2.5),
]

# DESNZ, Land utilised by solar PV (Dec 2024): new sites about 4 acres per MW, read
# here as per MWp; existing sites 5.6. The planning database's consented median is
# 1.6 ha/MW, the same figure.
SOLAR_ACRES_PER_MWP = 4.0

# The report's prices are real 2023 (see the module docstring).
PRICE_YEAR = 2023

# Plant behind the data centre's meter, with export refused, pays no generator's
# network charges (OBJECTIVE_AUDIT.md §3.1). Offshore keeps its line: its export
# system is recovered through it (report footnote 6).
BEHIND_THE_METER = ("onshore_wind", "solar_pv")

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
    """Annualise a capital sum over its life. Mirrors dc_config's."""
    rate = float(rate)
    lifetime_years = float(lifetime_years)
    if lifetime_years <= 0:
        raise ValueError("lifetime_years must be positive")
    if rate == 0:
        return 1.0 / lifetime_years
    return rate * (1.0 + rate) ** lifetime_years / ((1.0 + rate) ** lifetime_years - 1.0)


def building_finance_factor(rate, build_years):
    """Capital at the end of the build per £1 spent, evenly over ``build_years``
    and carrying the hurdle rate from mid-year. With it, the annuity reproduces
    the report's own LCOE (``annualised_table``), which spreads spend over the
    build."""
    rate, years = float(rate), int(round(float(build_years)))
    return sum((1.0 + rate) ** (years - i - 0.5) for i in range(years)) / years


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
SOURCE_KEY = {"onshore_wind": "desnz_arup_2024_onshore_solar", "solar_pv": "desnz_arup_2024_onshore_solar",
              "offshore_wind": "desnz_arup_2024_offshore"}


def annual_cost(tech: str, case: str) -> dict:
    """One technology's annualised £/MW/y in one case (per MWp for solar),
    each number recorded for the cost map (``trace.cost``)."""
    params, source, note = TECHNOLOGIES[tech]
    inv = INVERSE_CASE[case]
    per = "MWp" if tech == "solar_pv" else "MW"
    table = note.split(";")[0]
    cite = lambda row, c: [(SOURCE_KEY[tech], f"{table}, {row}, {c} case")]    # noqa: E731
    capex_per_kw = T.cost(f"cost.{tech}.capex_per_kW", _value(params, "total_capex", case),
                          "GBP per kWp" if tech == "solar_pv" else "GBP per kW",
                          "Total capital (pre-development, construction, infrastructure)",
                          grade="transcribed", cites=cite("total capex", case))
    opex_kgbp = T.cost(f"cost.{tech}.opex_per_MW_year", _value(params, "total_opex", case),
                       f"thousand GBP per {per} per year",
                       "Total yearly operating cost (insurance, connection and use of system, O&M)",
                       grade="transcribed", cites=cite("total opex", case))
    life = T.cost(f"cost.{tech}.lifetime_years", _value(params, "operating_lifetime", inv), "years",
                  "Operating life (the report pairs low cost with the high life)",
                  grade="transcribed", cites=cite("operating lifetime", inv))
    report_rate = T.cost(f"cost.{tech}.report_hurdle_rate", _value(params, "hurdle_rate", case), "fraction per year",
                         "The report's own hurdle rate, pre-tax real: the LCOE cross-check's", grade="transcribed",
                         cites=cite("hurdle rate", case))
    if DISCOUNT_RATE_OVERRIDE is not None:
        rate = T.cost(f"cost.{tech}.discount_rate", DISCOUNT_RATE_OVERRIDE, "fraction per year",
                      "One project-wide discount rate (DISCOUNT_RATE_OVERRIDE)", grade="assumed")
    else:
        rate = T.cost(f"cost.{tech}.discount_rate", CEPA_HURDLE_RATE[tech], "fraction per year",
                      "The rate the coefficient is annualised at: CEPA's whole-life hurdle rate, pre-tax real",
                      grade="transcribed", cites=[("cepa_hurdle_rates_2025", f"Table E.1, {tech.replace('_', ' ')}")])

    capex_per_mw = capex_per_kw * 1000.0
    opex_per_mw = opex_kgbp * 1000.0
    crf = T.cost(f"cost.{tech}.crf", capital_recovery_factor(rate, life), "per year",
                 "Capital recovery factor: the yearly repayment of £1 over the life at the rate",
                 uses=[f"cost.{tech}.discount_rate", f"cost.{tech}.lifetime_years"])
    # Onshore and solar only: it brings them within 1 % of the report's LCOE, and
    # takes offshore (out of scope, already 7 % above it) further away.
    finance = 1.0
    finance_uses = []
    build_years = _value(params, "construction_period", case)
    if tech in BEHIND_THE_METER:
        T.cost(f"cost.{tech}.construction_years", build_years, "years",
               "Construction period", grade="transcribed", cites=cite("construction period", case))
        finance = T.cost(f"cost.{tech}.building_finance_factor", building_finance_factor(rate, build_years), "multiplier",
                         "Capital carried at the rate over the build",
                         uses=[f"cost.{tech}.discount_rate", f"cost.{tech}.construction_years"])
        finance_uses = [f"cost.{tech}.building_finance_factor"]
    ann_capex = capex_per_mw * finance * crf
    # The report's own basis, at its own rate, kept for its LCOE cross-check
    report_finance = building_finance_factor(report_rate, build_years) if tech in BEHIND_THE_METER else 1.0
    published_annual = capex_per_mw * report_finance * capital_recovery_factor(report_rate, life) + opex_per_mw

    site_kgbp = 0.0
    site_uses = []
    if tech in BEHIND_THE_METER:
        uos = T.cost(f"cost.{tech}.own_network_charges", _value(params, "connection_and_uos", case),
                     f"thousand GBP per {per} per year",
                     "The generator's own connection and use-of-system line, taken out: plant behind the meter, "
                     "export refused", grade="transcribed", cites=cite("connection and UoS", case))
        site_kgbp -= uos
        site_uses.append(f"cost.{tech}.own_network_charges")
    if tech == "onshore_wind":
        site_kgbp += T.cost(f"cost.{tech}.land", _value(params, "land", case), f"thousand GBP per {per} per year",
                            "Land rent, outside the report's opex", grade="transcribed",
                            cites=[(SOURCE_KEY[tech], f"§5.8.1, {case}")],
                            note="Mostly Scottish sites, by the report's own account")
        site_uses.append(f"cost.{tech}.land")
    elif tech == "solar_pv":
        per_acre = T.cost(f"cost.{tech}.land_per_acre", _value(params, "land_per_acre", case),
                          "thousand GBP per acre per year", "Land rent, outside the report's opex",
                          grade="transcribed", cites=[(SOURCE_KEY[tech], f"§6.8.1, {case}")])
        acres = T.cost(f"cost.{tech}.acres_per_MWp", SOLAR_ACRES_PER_MWP, "acres per MWp", "Land taken per MWp",
                       grade="transcribed", cites=[("desnz_solar_land_2024", "p. 2, new sites, about 4 acres per MW")])
        site_kgbp += T.cost(f"cost.{tech}.land", per_acre * acres, f"thousand GBP per {per} per year",
                            "Land rent per MWp", uses=[f"cost.{tech}.land_per_acre", f"cost.{tech}.acres_per_MWp"])
        site_uses.append(f"cost.{tech}.land")
    if tech in BEHIND_THE_METER:
        section = "§5.8.2" if tech == "onshore_wind" else "§6.8.2"
        site_kgbp += T.cost(f"cost.{tech}.business_rates", _value(params, "business_rates", case),
                            f"thousand GBP per {per} per year", "Property and business rates, outside the report's opex",
                            grade="transcribed", cites=[(SOURCE_KEY[tech], f"{section}, {case}")])
        site_uses.append(f"cost.{tech}.business_rates")

    inflate = P.to_2025(PRICE_YEAR)
    total_annual = T.cost(f"cost.{tech}.annual_per_{per}", (ann_capex + opex_per_mw + site_kgbp * 1000.0) * inflate,
                          f"GBP per {per} per year",
                          "Capital repaid yearly plus the operating cost, on this site's scope, in 2025 pounds",
                          uses=[f"cost.{tech}.capex_per_kW", *finance_uses, f"cost.{tech}.crf",
                                f"cost.{tech}.opex_per_MW_year", f"price_base.{PRICE_YEAR}_to_2025", *site_uses])
    mwh_per_mw_yr = 8760.0 * _value(params, "net_load_factor", inv)
    return {"capex_GBP_per_MW": capex_per_mw, "opex_GBP_per_MW_year": opex_per_mw, "lifetime_years": life,
            "discount_rate": rate, "crf": crf, "annualised_capex_GBP_per_MW_year": ann_capex,
            "published_basis_annual_GBP_per_MW_year": published_annual,
            "total_annual_cost_GBP_per_MW_year": total_annual,
            "net_load_factor": _value(params, "net_load_factor", inv), "MWh_per_MW_year": mwh_per_mw_yr,
            "source": source, "trace_key": f"cost.{tech}.annual_per_{per}"}


def annualised_table():
    """Annualised £/MW/y and an LCOE cross-check against the report's own.

    Capacity is per MW for wind and per MWp for solar.

    The report's low/high scenarios do **not** pair like with like. From p.7:
    low costs are combined with the *high* net load factor and *high*
    operating lifetime (a bigger, longer-lived project generates more), and
    the high-cost scenario takes the low values. ``INVERSE_CASE`` reproduces
    that pairing, which is what makes the LCOE cross-check meaningful.

    The cross-check is on the report's own basis: its prices and scope, the
    annuity carrying the build's finance. The residual ``lcoe_delta_pct`` is what
    is left against the DESNZ LCOE calculator, which also places pre-development
    spend and generation year by year. The coefficient the LP charges differs
    from this basis by design: 2025 pounds, land and rates in, own network
    charges out (``annual_cost``).
    """
    rows = []
    with T.quiet():
        for tech, (params, source, note) in TECHNOLOGIES.items():
            for case in CASES:
                a = annual_cost(tech, case)
                lcoe = a["published_basis_annual_GBP_per_MW_year"] / a["MWh_per_MW_year"]
                reported = _value(params, "reported_lcoe", case)
                rows.append({
                    "asset": tech, "case": case,
                    "technical_case": INVERSE_CASE[case],
                    **{k: a[k] for k in ("capex_GBP_per_MW", "opex_GBP_per_MW_year", "lifetime_years",
                                         "discount_rate", "crf", "annualised_capex_GBP_per_MW_year",
                                         "total_annual_cost_GBP_per_MW_year", "net_load_factor",
                                         "MWh_per_MW_year")},
                    "lcoe_GBP_per_MWh": lcoe,
                    "reported_lcoe_GBP_per_MWh": reported,
                    "lcoe_delta_pct": 100.0 * (lcoe / reported - 1.0),
                    "source": source,
                })
    return pd.DataFrame(rows)


def check_against_price_outputs():
    """Assert the onshore wind rows agree with the frozen second transcription."""
    path = PRICE_DIR / "static_cost_assumptions.csv"
    if not path.exists():
        return f"skipped — {path.name} not found"
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
                mismatches.append(f"{p}/{case}: static_cost_assumptions={a} vs PDF={b}")
    if mismatches:
        raise AssertionError(
            "onshore wind costs disagree with price_outputs/:\n  "
            + "\n  ".join(mismatches)
        )
    n = len(set(existing["parameter"]) & set(mine.index))
    return f"OK — {n} onshore wind parameters match static_cost_assumptions.csv exactly"


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
    print("LCOE cross-check — annuity with build finance, report's basis, vs the report's own calculator")
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
