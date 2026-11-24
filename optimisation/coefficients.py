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
| onshore wind, solar PV | ``renewables.py`` | per MW installed |
| battery power and energy | ``battery.py`` | per MW and per MWh (energy with its end-of-life oversize) |
| AE / PEM / SOEC electrolysers | ``electrolysers.py`` | plant per MW over its life; stack per MW replaced |
| PEM fuel cell stack and BoP | ``fuel_cell.py`` | per MW, replaced on max(calendar, duty) |
| Gas engines | ``gas_engine.py`` | per MW, replaced on max(calendar, duty); running per MWh |
| H2 storage, every design | ``h2_storage.py`` | per kg of capacity |
| step-up transformers (wind, solar, battery, fuel cell) | ``transformers.py`` | per MW over the asset's life |
| grid connection and its line | ``grid_connection.py`` | per MW, and per km of route per circuit |

``cutoff_estimate_kgco2e_per_capacity_unit`` is what the cut-off register
carries on top of the row in the default model (``dc_inputs.with_cutoff``), in
the row's own unit. Capital plus that, over the calendar life, is what
``dc_inputs.build_tech`` charges per year (20 Nov 2026: the table used to leave
out the battery oversize, the transformers, the connection and these estimates).
The optimiser does not read this table; ``dc_runner`` and the maps fingerprint it.

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
    "throughput_kgco2e_per_MWh", "cutoff_estimate_kgco2e_per_capacity_unit",
    "source", "grade", "note",
]

# Which table rows each coefficient's cut-off estimates land on
# (dc_inputs.CUTOFF_FIELD names the coefficient; dc_inputs.with_cutoff adds them).
# Prefixes match every row that starts with them (all electrolyser plant rows,
# all tank designs). The facility's estimate has no row: the facility is not here.
CUTOFF_ROWS = {
    "gwp_tx_wind_per_mw": ("wind_stepup_transformer",),
    "gwp_tx_solar_per_mwp": ("solar_stepup_transformer",),
    "gwp_tx_batt_per_mw": ("battery_stepup_transformer",),
    "gwp_batt_e": ("battery_energy",),
    "gwp_ely": ("electrolyser_ae", "electrolyser_pem", "electrolyser_soec"),
    "gwp_tank": ("h2_tank_",),
    "gwp_tx_fc_per_mw": ("fuel_cell_stepup_transformer",),
    "gwp_grid_per_mw": ("grid_connection",),
    "gwp_ge_per_mw": ("gas_engine",),
}
# Coefficients the LP charges per unit replaced rather than per year: their
# estimate is already per capacity unit.
_PER_REPLACEMENT = {"gwp_ge_per_mw"}


def _row(asset, capacity_unit, capital, calendar=None, duty=None,
         variable=None, variable_unit=None, throughput=None,
         source="", grade="derived", note=""):
    return {
        "asset": asset, "capacity_unit": capacity_unit,
        "capital_kgco2e_per_capacity_unit": capital,
        "calendar_lifetime_years": calendar, "duty_lifetime_hours": duty,
        "variable_kgco2e_per_unit": variable, "variable_output_unit": variable_unit,
        "throughput_kgco2e_per_MWh": throughput,
        "cutoff_estimate_kgco2e_per_capacity_unit": 0.0,
        "source": source, "grade": grade, "note": note,
    }


def cutoff_central() -> dict[str, float]:
    """The cut-off register's central estimates, summed per LP coefficient, as
    ``dc_inputs.with_cutoff`` adds them in the default (central) model."""
    from optimiser_lca import exclusions as X
    from optimisation.dc_inputs import CUTOFF_FIELD
    added: dict[str, float] = {}
    for e in X.REGISTER:
        if e.kind == "boundary" or e.status != "included_estimate":
            continue
        est = e.estimate("central")
        if est is None:
            continue
        field = CUTOFF_FIELD[(e.technology, e.side)]
        added[field] = added.get(field, 0.0) + float(est)
    return added


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
            # full-scope (solar's default IEA basis), so wind is not
            # capital-only against a full-scope solar figure. See renewables.py.
            throughput=(r["residual_per_kWh"] * 1000.0 if r["capital_only"] else None),
            source=(f"{r['embodied_basis_label']}; DESNZ/Arup 2024 lifetime"
                    if solar else ren_src),
            grade="derived",
            note=("solar is not scored on ecoinvent — its GB activity is a 2008 plant. "
                  f"Basis: {r['embodied_basis']}. See SOURCES.md" if solar else "")))

    # --- battery --------------------------------------------------------
    be = batt.embodied_components()
    b_src = "ecoinvent 3.9.1 apos 500 kW inverter; Modo Energy asset life"
    e_src = ("Jasper et al. 2026 liquid-cooled LFP container + Voß et al. 2025 cell, "
             "on ecoinvent 3.9.1 apos (optimiser_lca/bess.py); Modo Energy asset life"
             if batt.EMBODIED_BASIS == "jasper_voss_2026"
             else "ecoinvent 3.9.1 apos LFP EV pack (legacy); Modo Energy asset life")
    rows.append(_row("battery_power", "MW", be["power_kgco2e_per_kW"] * 1000.0,
                     calendar=batt.ASSET_LIFE_YEARS, source=b_src, grade="derived",
                     note="power conversion system"))
    oversize = batt.end_of_life_oversize()
    rows.append(_row("battery_energy", "MWh", be["energy_kgco2e_per_kWh"] * 1000.0 * oversize,
                     calendar=batt.ASSET_LIFE_YEARS, source=e_src, grade="derived",
                     note=(f"per usable MWh needed at end of life: nameplate / USABLE_FRACTION "
                           f"{batt.USABLE_FRACTION:g}, x {oversize:.3f} for fade by year 15 "
                           "(battery.end_of_life_oversize); cells made in China; power conversion and "
                           "transformer charged on the power side"
                           if batt.EMBODIED_BASIS == "jasper_voss_2026"
                           else f"LFP EV pack, x {oversize:.3f} for fade; no container/racking/HVAC")))

    # --- transformers and the grid connection ---------------------------
    # Charged by the LP per MW per year (dc_inputs.build_tech); shown here as the
    # whole amount per unit of capacity over the life it is spread over, so that
    # capital / calendar life is exactly what the LP charges. Solar's carries
    # Smith A15's transformer replacements over that life too.
    from optimisation import connection_cost
    from optimisation import fuel_cell as fc_mod
    from optimisation import grid_connection as gc
    from optimisation import transformers as tx
    lives = {r["technology"]: float(r["study_lifetime_years"]) for _, r in ren_df.iterrows()}
    fc_bop_life = float(fc_mod.decompose()["bop_calendar_lifetime_years"])
    tx_src = "transformers.py (optimiser_lca/stepup_transformers.py foreground)"
    for asset, tech, unit, life, note in (
            ("wind_stepup_transformer", "onshore_wind", "MW", lives["onshore_wind"],
             "Leng 2026 per-turbine units, per MW of wind, over wind's life"),
            ("solar_stepup_transformer", "solar_pv", "MWp", lives["solar_pv"],
             "IEA PVPS T12-33:2026 inverter-station units plus Smith A15's replacements, per MWp, "
             "over solar's life"),
            ("battery_stepup_transformer", "battery", "MW", float(batt.ASSET_LIFE_YEARS),
             "Jasper 2026 container unit, per MW of power conversion, over the battery's life"),
            ("fuel_cell_stepup_transformer", "fuel_cell", "MW", fc_bop_life,
             "Jasper 2026 container unit, per MW of fuel cell, over the plant's calendar life")):
        rows.append(_row(asset, unit, tx.kgco2e_per_mw_year(tech, life_years=life) * life,
                         calendar=life, source=tx_src, grade="derived", note=note))
    rows.append(_row("grid_connection", "MW", gc.kgco2e_per_mw_year() * gc.ASSET_LIFE_YEARS,
                     calendar=gc.ASSET_LIFE_YEARS,
                     source="grid_connection.py: Leng 2026 100 MVA intake transformer x2 and switchyard civils",
                     grade="derived", note="per MW of connection (cap_grid); 40-year life ASSUMED"))
    rows.append(_row("grid_connection_line", "km", gc.line_kgco2e_per_km_year() * gc.ASSET_LIFE_YEARS,
                     calendar=gc.ASSET_LIFE_YEARS,
                     source="ecoinvent 3.9.1 apos high-voltage transmission network, per km (a proxy)",
                     grade="assumed",
                     note=f"per km of route per circuit; the LP charges {connection_cost.CIRCUITS} circuits x the "
                          "route length, as a fixed yearly term while the connection is on"))

    # --- electrolysers --------------------------------------------------
    # Two rows each since 20 Nov 2026, as the optimiser charges them: the balance of
    # plant once over the plant's life, and one stack per replacement on
    # max(calendar, duty). The old single row read "three stacks per unit life",
    # the 26 Oct - 19 Nov rule, and overstated what is charged 2-2.4x.
    e_src = "Gerloff 2021 capital good (optimiser_lca/hydrogen.py), decomposed; NESO 25 y plant life"
    for r in ely.decompose_all():
        name = "electrolyser_" + r["technology"].split()[0].lower()
        rows.append(_row(
            name, "MW", r["plant_kgco2e_per_MW"], calendar=ely.PLANT_LIFETIME_YEARS,
            variable=r["variable_kgco2e_per_kg"], variable_unit="kg H2",
            source=e_src, grade="derived",
            note=f"balance of plant only, once per plant life; {r['kwh_per_kg']:.1f} kWh/kg. "
                 f"The stacks are the {name}_stack row"))
        rows.append(_row(
            f"{name}_stack", "MW", r["stack_kgco2e_per_MW"],
            calendar=ely.STACK_CALENDAR_YEARS, duty=ely.STACK_DUTY_HOURS,
            source="Gerloff 2021 stack, decomposed; stack life Gerloff §2.1.2 (50,000 h)",
            grade="derived",
            note="one stack per replacement on max(calendar, duty): at least one per plant life, more by running "
                 "hours. Per MW of stack input; the optimiser scales it by the stack's share of cap_ely"))

    # --- fuel cell ------------------------------------------------------
    d = fc.decompose()
    rows.append(_row("fuel_cell_bop", "MW", d["bop_kgco2e_per_MW"],
                     calendar=d["bop_calendar_lifetime_years"],
                     duty=d["bop_duty_lifetime_hours"],
                     source="Usai 2021 loops + 500 kW inverter + container; DOE MW-class duty life",
                     grade="assumed",
                     note="calendar life 20 y ASSUMED (Nedstack-indicative) — sweep 15/20/25 y; see DATA_GAPS.md"))
    rows.append(_row("fuel_cell_stack", "MW", d["stack_kgco2e_per_MW"],
                     calendar=d["stack_calendar_lifetime_years"],
                     duty=d["stack_lifetime_hours"],
                     source="Babatunde et al. 2024 Table S1; stack life their §3.4",
                     grade="assumed",
                     note="calendar life 10 y ASSUMED — sweep 5/10/15 y; stack carbon tested at x0.5/x1.5 "
                          "(since 11 Nov 2026; Gramc 2025 kept, untested); see DATA_GAPS.md"))
    rows.append(_row("fuel_cell_maintenance", "MW", 0.0,
                     throughput=d["maintenance_kgco2e_per_MWh"],
                     source="Usai 2021 air filter + coolant per 8,000 h",
                     grade="derived", note="pure throughput term"))

    # --- gas engines ------------------------------------------------------
    from optimisation import gas_engine as ge
    g = ge.decompose()
    rows.append(_row("gas_engine", "MW", g["plant_kgco2e_per_MW"],
                     calendar=ge.CALENDAR_YEARS, duty=g["duty_hours"],
                     throughput=g["running_kgco2e_per_MWh"] + g["maintenance_kgco2e_per_MWh"],
                     source="ecoinvent 3.9.1 lean-burn 1 MW gas engine set on GB gas; DESNZ 2026 unabated gas study",
                     grade="derived",
                     note="plant incl. a steel hall (ecoinvent ORC unit's 500 m2 per 3 MW, a stand-in); "
                          "throughput is running plus maintenance; docs/GAS_ENGINE_PLAN.md"))

    # --- hydrogen storage -----------------------------------------------
    # Source and grade from each design's own description (optimiser_lca.h2_tank.TANK_DESIGNS):
    # until 20 Nov 2026 they were keyed on is_as_built, which labelled the
    # default bulk vessel "Gandiglio Table 5" and Gandiglio's "a Type I cylinder".
    for r in h2s.decompose():
        desc = str(r.get("note", ""))
        grade = ("transcribed" if desc.startswith("Gandiglio")
                 else "derived" if desc.startswith("DERIVED") else "assumed")
        rows.append(_row(
            "h2_tank_" + r["design"], "kg H2", r["kgco2e_per_kg_capacity"],
            calendar=r["lifetime_years"],
            source=desc or "h2_storage.py",
            grade=grade,
            note=("the default design; " if r["is_as_built"] else "")
                 + f"{r['compression_kwh_per_kg']:.1f} kWh/kg charging compression; "
                 f"standing loss {r['leakage_frac_per_hour']:.4g}/h"
                 + (" ASSUMED" if r["leakage_is_assumed"] else "")))

    df = pd.DataFrame(rows, columns=COLUMNS)

    # --- cut-off register estimates, on the rows the LP adds them to -----
    for field, add in cutoff_central().items():
        targets = CUTOFF_ROWS.get(field, ())
        for i, asset in df["asset"].items():
            if not any(asset == t or (t.endswith("_") and asset.startswith(t)) for t in targets):
                continue
            life = 1.0 if field in _PER_REPLACEMENT else float(df.at[i, "calendar_lifetime_years"])
            df.at[i, "cutoff_estimate_kgco2e_per_capacity_unit"] += add * life
    return df


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
