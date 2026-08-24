"""Guards on the capacity-shaped LCA coefficients.

These are the assertions that make the decomposition trustworthy rather than
merely plausible. Each module's own ``check_*`` function is the real test; this
file runs them under pytest and adds the cross-module invariants no single
module can see.

They run against the JSON caches the modules write, so they need no Brightway
connection — but a cache is only as good as the run that produced it. Refresh
with ``python optimisation/<module>.py`` after rebuilding the foreground.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from optimisation import coefficients, electrolysers, fuel_cell, h2_storage


def _cached(module):
    if not module.CACHE_PATH.exists():
        pytest.skip(f"{module.CACHE_PATH.name} not built — "
                    f"run `python optimisation/{module.__name__.split('.')[-1]}.py` first")


# =============================================================================
# Electrolysers
# =============================================================================
def test_electrolyser_rating_is_defensible():
    """The 1 MW rating is derived, so all three inventories must agree on it."""
    _cached(electrolysers)
    assert "OK" in electrolysers.check_rating(electrolysers.decompose_all())


def test_electrolyser_decomposition_reconstructs():
    """Capital per MW + consumables must rebuild the foreground's own figure."""
    _cached(electrolysers)
    assert "OK" in electrolysers.check_reconstruction(electrolysers.decompose_all())


def test_electrolyser_capital_is_most_of_the_non_electricity_burden():
    """A sanity floor: if capital were a rounding error the module would be pointless."""
    _cached(electrolysers)
    for r in electrolysers.decompose_all():
        share = r["capital_kgco2e_per_kg_h2"] / r["foreground_fixed_kgco2e_per_kg"]
        assert 0.0 < share <= 1.0, f"{r['technology']}: capital share {share:.3f}"


def test_restating_at_the_foregrounds_own_cf_is_a_no_op():
    """Restated at Hermesmann's own utilisation, the burden must not move."""
    _cached(electrolysers)
    for r in electrolysers.decompose_all():
        back = electrolysers.restate(r, r["implied_capacity_factor"])
        assert back["ratio_to_foreground"] == pytest.approx(1.0, rel=1e-6)


def test_lower_utilisation_raises_the_per_kg_burden():
    """The whole point of the module, as an ordering property."""
    _cached(electrolysers)
    for r in electrolysers.decompose_all():
        low = electrolysers.restate(r, 0.20)["capital_kgco2e_per_kg_h2"]
        high = electrolysers.restate(r, 0.90)["capital_kgco2e_per_kg_h2"]
        assert low > high * 4, f"{r['technology']}: {low:.4f} vs {high:.4f}"


def test_double_count_guard_fires():
    """Charging capital per MW and using the foreground's fixed figure is refused."""
    electrolysers.assert_no_double_count(True, False)     # optimiser's convention
    electrolysers.assert_no_double_count(False, True)     # sizing.py's convention
    with pytest.raises(AssertionError, match="Double count"):
        electrolysers.assert_no_double_count(True, True)


# =============================================================================
# Fuel cell
# =============================================================================
def test_fuel_cell_decomposition_reconstructs():
    _cached(fuel_cell)
    assert "OK" in fuel_cell.check_reconstruction(fuel_cell.decompose())


def test_fuel_cell_collapses_onto_the_foreground_at_full_duty():
    """At 8,760 h/yr, per-MW-on-a-duty-life and per-kWh are the same statement."""
    _cached(fuel_cell)
    assert "OK" in fuel_cell.check_full_duty(fuel_cell.decompose())


def test_fuel_cell_excludes_its_own_hydrogen():
    """The LP supplies hydrogen; leaving the inventory's input in double-counts fuel."""
    _cached(fuel_cell)
    d = fuel_cell.decompose()
    assert d["_per_kwh"]["fuel"] > 1.0, "the fuel term should dominate the raw inventory"
    non_fuel = d["_foreground_total_per_kWh"] - d["_per_kwh"]["fuel"]
    rebuilt = (d["stack_kgco2e_per_MW"] / 1000.0 / d["stack_lifetime_hours"]
               + d["bop_kgco2e_per_MW"] / 1000.0 / d["bop_duty_lifetime_hours"]
               + d["maintenance_kgco2e_per_MWh"] / 1000.0)
    assert rebuilt == pytest.approx(non_fuel, rel=1e-6)


def test_backup_duty_costs_far_more_than_the_per_kwh_convention():
    """The finding that justifies the split: a backup machine is not nearly free."""
    _cached(fuel_cell)
    d = fuel_cell.decompose()
    cap, hours = 7.31, 100.0
    b = fuel_cell.burden_kgco2e_per_year(cap, cap * hours)
    split = b["bop"] + b["stack"] + b["maintenance"]
    naive = (d["_foreground_total_per_kWh"] - d["_per_kwh"]["fuel"]) * cap * hours * 1000
    assert split > 10 * naive, f"split {split:,.0f} vs per-kWh {naive:,.0f}"
    assert b["stack_binding"] == "calendar" and b["bop_binding"] == "calendar"


def test_fuel_cell_burden_is_monotonic_in_duty():
    _cached(fuel_cell)
    prev = 0.0
    for hours in (100, 500, 2000, 8760):
        b = fuel_cell.burden_kgco2e_per_year(7.31, 7.31 * hours)
        total = b["bop"] + b["stack"] + b["maintenance"]
        assert total > prev, f"burden fell between duties at {hours} h"
        prev = total


# =============================================================================
# Hydrogen storage
# =============================================================================
def test_h2_storage_matches_the_foreground_activity():
    _cached(h2_storage)
    assert "OK" in h2_storage.check_against_brightway(h2_storage.decompose())


def test_both_tank_designs_are_available():
    """The 200 bar design has no Brightway activity but must still be offered."""
    _cached(h2_storage)
    designs = {r["design"] for r in h2_storage.decompose()}
    assert {"gandiglio_28bar", "type1_200bar"} <= designs


def test_higher_pressure_tank_is_lighter_per_kg_stored():
    _cached(h2_storage)
    rows = {r["design"]: r for r in h2_storage.decompose()}
    assert (rows["type1_200bar"]["steel_kg_per_kg_h2"]
            < rows["gandiglio_28bar"]["steel_kg_per_kg_h2"])


# =============================================================================
# The assembled table
# =============================================================================
def test_coefficient_table_is_structurally_sound():
    _cached(electrolysers); _cached(fuel_cell); _cached(h2_storage)
    assert "OK" in coefficients.check(coefficients.build())


def test_coefficient_table_covers_every_optimiser_asset():
    """If an asset the LP can build is missing here, the LP builds it for free."""
    _cached(electrolysers); _cached(fuel_cell); _cached(h2_storage)
    assets = set(coefficients.build()["asset"])
    required = {
        "onshore_wind", "offshore_wind", "solar_pv",
        "battery_power", "battery_energy",
        "electrolyser_ae", "electrolyser_pem", "electrolyser_soec",
        "fuel_cell_bop", "fuel_cell_stack",
        "h2_tank_gandiglio_28bar", "h2_tank_type1_200bar",
    }
    assert required <= assets, f"missing: {sorted(required - assets)}"


def test_written_table_round_trips():
    if not coefficients.CSV_PATH.exists():
        pytest.skip("tech_lca_coefficients.csv not built")
    loaded = coefficients.load()
    assert list(loaded.columns) == coefficients.COLUMNS
    assert "OK" in coefficients.check(loaded)


def test_every_assumed_row_explains_itself():
    """A row graded 'assumed' with no note is an untraceable number."""
    if not coefficients.CSV_PATH.exists():
        pytest.skip("tech_lca_coefficients.csv not built")
    df = coefficients.load()
    for _, r in df[df.grade == "assumed"].iterrows():
        assert isinstance(r["note"], str) and r["note"].strip(), \
            f"{r['asset']} is ASSUMED but carries no note"
