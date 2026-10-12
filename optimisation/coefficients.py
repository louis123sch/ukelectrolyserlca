"""
One table: what a unit of every asset costs in carbon.
=============================================================================

The data-centre optimiser must never import Brightway. Brightway is slow and
stateful; the LP is built and solved hundreds of times across a scenario matrix.
So there is a build step between them, and this is it: every capacity-shaped
embodied-carbon coefficient in the study, assembled from the modules that derive
them and written to ``optimisation_outputs/tech_lca_coefficients.csv``.

Nothing is computed here. Each number comes from the module that owns it and
prints its own cross-checks:

| assets | module | shape |
|---|---|---|
| onshore wind, offshore wind, solar PV | ``renewables.py`` | per MW installed |
| battery power and energy | ``battery.py`` | per MW and per MWh |
| AE / PEM / SOEC electrolysers | ``electrolysers.py`` | per MW installed |
| PEM fuel cell stack and BoP | ``fuel_cell.py`` | per MW, replaced on max(calendar, duty) |
| H2 storage, both designs | ``h2_storage.py`` | per kg of capacity |

Reading the table
-----------------
Every row carries the capacity unit its capital figure is per, and the two
lifetimes that decide how fast it is charged:

``calendar_lifetime_years``   the asset is replaced this often regardless of use
``duty_lifetime_hours``       the asset is replaced this often if run flat out

Where both are present the replacement rate is
``max(1/calendar_years, full_load_hours_per_year/duty_hours)`` — a maximum of two
linear functions, which an LP represents exactly. Where ``duty_lifetime_hours``
is blank the asset only ages. ``throughput_kgco2e_per_MWh`` covers burdens that
scale purely with output and never with capacity, such as fuel cell maintenance.

``variable_kgco2e_per_unit`` is the non-capital, non-electricity burden per unit
of the asset's own output — kg CO2e per kg H2 for an electrolyser. It is
**not** interchangeable with the foreground's own per-kg figure, which bundles
capital in; see ``electrolysers.assert_no_double_count``.

Grades follow ``SOURCES.md``: transcribed / derived / assumed.

Run:  python optimisation/coefficients.py
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
OUT_DIR = ROOT / "optimisation_outputs"
CSV_PATH = OUT_DIR / "tech_lca_coefficients.csv"

COLUMNS = [
    "asset", "capacity_unit", "capital_kgco2e_per_capacity_unit",
    "calendar_lifetime_years", "duty_lifetime_hours",
    "variable_kgco2e_per_unit", "variable_output_unit",
    "throughput_kgco2e_per_MWh", "source", "grade", "note",
]


def _row(asset, capacity_unit, capital, calendar=None, duty=None,
         variable=None, variable_unit=None, throughput=None,
         source="", grade="derived", note=""):
    return {
        "asset": asset, "capacity_unit": capacity_unit,
        "capital_kgco2e_per_capacity_unit": capital,
        "calendar_lifetime_years": calendar, "duty_lifetime_hours": duty,
        "variable_kgco2e_per_unit": variable, "variable_output_unit": variable_unit,
        "throughput_kgco2e_per_MWh": throughput,
        "source": source, "grade": grade, "note": note,
    }


def build(cost_case: str = "central") -> pd.DataFrame:
    from optimisation import battery as batt
    from optimisation import electrolysers as ely
    from optimisation import fuel_cell as fc
    from optimisation import h2_storage as h2s
    from optimisation import renewables as ren

    rows = []

    # --- generation -----------------------------------------------------
    ren_df = ren.build(cost_case)
    ren_src = "ecoinvent 3.9.1 apos capital exchange, decomposed; DESNZ/Arup 2024 lifetime"
    for _, r in ren_df.iterrows():
        solar = r["technology"] == "solar_pv"
        rows.append(_row(
            r["technology"], "MW" if "wind" in r["technology"] else "MWp",
            r["capital_kgco2e_per_MW"], calendar=r["study_lifetime_years"],
            # Non-capital consumables (lubricating oil, water) ecoinvent
            # reports per kWh, not per MW - blank where capital is already
            # full-scope (solar's default IEA basis), so wind/offshore is not
            # capital-only against a full-scope solar figure. See renewables.py.
            throughput=(r["residual_per_kWh"] * 1000.0 if r["capital_only"] else None),
            source=(f"{r['embodied_basis_label']}; DESNZ/Arup 2024 lifetime"
                    if solar else ren_src),
            grade="derived",
            note=("solar is not scored on ecoinvent — its GB activity is a 2008 plant. "
                  f"Basis: {r['embodied_basis']}. See SOURCES.md" if solar else "")))

    # --- battery --------------------------------------------------------
    be = batt.embodied_components()
    b_src = "ecoinvent 3.9.1 apos (LFP pack, 500 kW inverter); Modo Energy asset life"
    rows.append(_row("battery_power", "MW", be["power_kgco2e_per_kW"] * 1000.0,
                     calendar=batt.ASSET_LIFE_YEARS, source=b_src, grade="derived",
                     note="power conversion system"))
    rows.append(_row("battery_energy", "MWh", be["energy_kgco2e_per_kWh"] * 1000.0,
                     calendar=batt.ASSET_LIFE_YEARS, source=b_src, grade="derived",
                     note="LFP pack; container/racking/HVAC still missing — see DATA_GAPS.md"))

    # --- electrolysers --------------------------------------------------
    e_src = "Hermesmann et al. capital good, decomposed; NESO 25 y plant life"
    for r in ely.decompose_all():
        rows.append(_row(
            "electrolyser_" + r["technology"].split()[0].lower(), "MW",
            r["capital_kgco2e_per_MW"], calendar=ely.PLANT_LIFETIME_YEARS,
            variable=r["variable_kgco2e_per_kg"], variable_unit="kg H2",
            source=e_src, grade="derived",
            note=f"{r['kwh_per_kg']:.1f} kWh/kg; capital was amortised at "
                 f"{r['implied_capacity_factor']:.0%} CF in the foreground; no stack/BoP split"))

    # --- fuel cell ------------------------------------------------------
    d = fc.decompose()
    rows.append(_row("fuel_cell_bop", "MW", d["bop_kgco2e_per_MW"],
                     calendar=d["bop_calendar_lifetime_years"],
                     duty=d["bop_duty_lifetime_hours"],
                     source="ecoinvent 3.9.1 2 kW PEMFC net of stack; DOE 2020 duty life",
                     grade="assumed",
                     note="calendar life ASSUMED — no public figure; see DATA_GAPS.md"))
    rows.append(_row("fuel_cell_stack", "MW", d["stack_kgco2e_per_MW"],
                     duty=d["stack_lifetime_hours"],
                     source="Babatunde et al. 2024 Table S1; stack life their §3.4",
                     grade="derived",
                     note="calendar life taken as the study horizon, i.e. at least one stack"))
    rows.append(_row("fuel_cell_maintenance", "MW", 0.0,
                     throughput=d["maintenance_kgco2e_per_MWh"],
                     source="ecoinvent 3.9.1 PEMFC maintenance, net of bundled stack",
                     grade="derived", note="pure throughput term"))

    # --- hydrogen storage -----------------------------------------------
    for r in h2s.decompose():
        rows.append(_row(
            "h2_tank_" + r["design"], "kg H2", r["kgco2e_per_kg_capacity"],
            calendar=r["lifetime_years"],
            source="Gandiglio et al. 2022 Table 3" if r["is_as_built"]
                   else "derived from a ~1 wt% Type I cylinder",
            grade="transcribed" if r["is_as_built"] else "assumed",
            note=f"{r['compression_kwh_per_kg']:.1f} kWh/kg charging compression; "
                 f"standing loss {r['leakage_frac_per_hour']:.4g}/h ASSUMED"))

    return pd.DataFrame(rows, columns=COLUMNS)


def check(df: pd.DataFrame):
    """Structural guards — the table is read by code that cannot see Brightway."""
    problems = []
    if df["asset"].duplicated().any():
        problems.append("duplicate asset names: "
                        + ", ".join(df.loc[df["asset"].duplicated(), "asset"]))
    for _, r in df.iterrows():
        if pd.isna(r["capital_kgco2e_per_capacity_unit"]):
            problems.append(f"{r['asset']}: no capital figure")
        elif r["capital_kgco2e_per_capacity_unit"] < 0:
            problems.append(f"{r['asset']}: negative capital figure")
        if pd.isna(r["calendar_lifetime_years"]) and pd.isna(r["duty_lifetime_hours"]) \
                and not r["throughput_kgco2e_per_MWh"]:
            problems.append(f"{r['asset']}: neither a lifetime nor a throughput term — "
                            "nothing tells the optimiser how fast to charge it")
        if not r["source"]:
            problems.append(f"{r['asset']}: no source recorded")
        if r["grade"] not in ("transcribed", "derived", "assumed"):
            problems.append(f"{r['asset']}: grade {r['grade']!r} is not a SOURCES.md grade")
    if problems:
        raise AssertionError("coefficient table failed:\n  " + "\n  ".join(problems))
    return f"OK — {len(df)} assets, every one sourced, graded and chargeable"


def run(cost_case: str = "central"):
    df = build(cost_case)
    print("=" * 108)
    print(f"TECHNOLOGY LCA COEFFICIENTS — everything the optimiser needs, "
          f"no Brightway  (cost case: {cost_case})")
    print("=" * 108)
    print(check(df))

    print()
    print(f"  {'asset':<26}{'per':>6}{'capital kg CO2e':>18}{'calendar y':>12}"
          f"{'duty h':>10}{'grade':>12}")
    for _, r in df.iterrows():
        cal = f"{r['calendar_lifetime_years']:.0f}" if pd.notna(r["calendar_lifetime_years"]) else "-"
        duty = f"{r['duty_lifetime_hours']:,.0f}" if pd.notna(r["duty_lifetime_hours"]) else "-"
        print(f"  {r['asset']:<26}{r['capacity_unit']:>6}"
              f"{r['capital_kgco2e_per_capacity_unit']:>18,.0f}{cal:>12}{duty:>10}"
              f"{r['grade']:>12}")

    assumed = df[df.grade == "assumed"]
    if len(assumed):
        print(f"\n  {len(assumed)} row(s) graded ASSUMED — every result touching them "
              "must say so:")
        for _, r in assumed.iterrows():
            print(f"    {r['asset']:<26}{r['note']}")

    OUT_DIR.mkdir(exist_ok=True)
    out = df.copy()
    out.attrs.clear()
    # Explicit utf-8: Python on Windows defaults this handle to cp1252, which
    # writes an em-dash in a note as 0x97 and makes load()'s read_csv — which
    # defaults to utf-8 — fail on the file this function just wrote.
    with CSV_PATH.open("w", encoding="utf-8") as fh:
        fh.write(f"# built_at,{datetime.now(timezone.utc).isoformat(timespec='seconds')}\n")
        fh.write(f"# cost_case,{cost_case}\n")
        out.to_csv(fh, index=False)
    print(f"\nWrote:\n  {CSV_PATH.relative_to(ROOT)}")
    return df


def load() -> pd.DataFrame:
    """Read the built table. The optimiser's entry point — never touches Brightway."""
    if not CSV_PATH.exists():
        raise FileNotFoundError(
            f"{CSV_PATH.relative_to(ROOT)} has not been built. Run "
            "`python optimisation/coefficients.py` in the brightway environment first.")
    return pd.read_csv(CSV_PATH, comment="#")


if __name__ == "__main__":
    run()
