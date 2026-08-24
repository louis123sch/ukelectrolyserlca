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


# =============================================================================
# Network charges and hydrogen-chain costs
# =============================================================================
def test_network_charges_split_capacity_from_volumetric():
    """Collapsing everything to £/MWh would erase the trade being studied."""
    import pandas as pd
    from optimisation import network_charges as nc
    idx = pd.date_range("2025-01-01", "2025-12-29", freq="30min")
    ch = nc.import_charges(idx, zone_no=12, tdr_band="EHV2")
    assert ch["capacity_GBP_per_MW_year"] > 0
    assert ch["fixed_GBP_per_year"] > 0
    assert (ch["volumetric_GBP_per_MWh"] > 0).all()


def test_tnuos_is_zonal_and_scotland_is_floored_to_zero():
    """The locational signal is the study's headline; assert it exists."""
    from optimisation import network_charges as nc
    hh, _ = nc.tnuos_hh_demand()
    by_zone = hh.set_index("zone_name").tariff_GBP_per_kW
    assert by_zone["Northern Scotland"] == pytest.approx(0.0)
    assert by_zone["London"] > 5.0
    assert by_zone.max() - by_zone.min() > 5.0


def test_duos_red_band_is_winter_weekday_evening_only():
    import pandas as pd
    from optimisation import network_charges as nc
    idx = pd.date_range("2025-01-01", "2025-12-29", freq="30min")
    band = nc.duos_band(idx)
    red = idx[band == "red"]
    assert set(red.month) <= set(nc.DUOS_RED_MONTHS)
    assert (red.dayofweek < 5).all()
    assert red.hour.min() >= nc.DUOS_RED_HOURS[0]
    assert red.hour.max() < nc.DUOS_RED_HOURS[1]


def test_bsuos_covers_the_study_window():
    import pandas as pd
    from optimisation import network_charges as nc
    idx = pd.date_range("2025-01-01", "2025-12-29", freq="30min")
    s = nc.bsuos_series(idx)
    assert s.notna().all() and (s > 0).all()
    assert s.nunique() > 1, "BSUoS changes half-yearly; a constant means a lookup bug"


def test_h2_capex_cases_are_ordered_and_every_assumption_is_noted():
    from optimisation import h2_capex as hc
    assert "OK" in hc.check(hc.fuel_cell_costs(), hc.tank_costs(), hc.electrolyser_costs())


def test_soec_cost_is_flagged_as_having_no_source():
    """SOEC carbon results are sound; SOEC cost results are not. Keep that visible."""
    from optimisation import h2_capex as hc
    soec = hc.electrolyser_costs()
    soec = soec[soec.asset == "electrolyser_soec"]
    assert (soec.grade == "assumed").all()
    assert soec.note.str.contains("NO SOURCE").all()


# =============================================================================
# Site resolution
# =============================================================================
def test_tnuos_zone_mapping_is_a_bijection_and_matches_the_presets():
    """The CI-region -> TNUoS-zone table is hand-built, so it needs a check.

    The three original presets were set from published sources before the table
    existed, so they are an independent check on it rather than a restatement.
    """
    from optimisation import sites
    assert "OK" in sites.check_zone_mapping()


def test_site_accepts_coordinates_in_every_form():
    """Coordinates are the interface; presets are shortcuts."""
    from optimisation import sites
    lat, lon = 51.5074, -0.1278
    a = sites.get(f"{lat},{lon}")
    b = sites.get((lat, lon))
    c = sites.resolve(lat, lon)
    assert a.carbon_api_region == b.carbon_api_region == c.carbon_api_region
    assert a.tnuos_zone == b.tnuos_zone == c.tnuos_zone
    assert sites.get(a) is a


def test_central_london_resolves_to_region_13_zone_12():
    """A fixed point: the cached grid series is region 13, so this must match."""
    from optimisation import sites
    s = sites.resolve(51.5074, -0.1278)
    assert s.carbon_api_region == 13
    assert s.tnuos_zone == 12


def test_the_repos_own_wind_coordinate_is_not_london():
    """Regression on a pre-existing inconsistency, so it cannot quietly return.

    dashboard_config.WIND_LAT/WIND_LON is a field near St Albans — region 10,
    TNUoS zone 9 — while every cached grid series is region 13. The study as it
    stood paired London's grid intensity and London's £7.41/kW tariff with a
    Hertfordshire wind site. Nothing warned about it because nothing connected
    the wind coordinate to the grid region.
    """
    from optimisation import sites
    s = sites.resolve(51.7320, -0.3711)
    assert s.carbon_api_region == 10, "St Albans is East England, not London"
    assert s.tnuos_zone == 9


def test_grid_region_guard_refuses_a_mismatched_series():
    from optimisation import sites
    s = sites.resolve(57.48, -4.22)          # Northern Scotland, region 1
    with pytest.raises(ValueError, match="Carbon Intensity region 1"):
        sites.require_grid_region(
            s, "custom_grid_lca_carbon_api_regional_auto_r13_cheap_2025.csv")
    assert sites.require_grid_region(
        s, "custom_grid_lca_carbon_api_regional_auto_r1_cheap_2025.csv")


def test_connection_limit_defaults_to_unconstrained():
    """An invented limit would be the most decision-relevant unsourced number."""
    from optimisation import sites
    assert sites.resolve(51.5074, -0.1278).connection_limit_mw is None
