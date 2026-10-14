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


def test_fuel_cell_bop_is_a_hydrogen_unit_not_a_micro_chp():
    """Live values, not identities. The ecoinvent natural-gas micro-CHP gave a BoP
    of 469 t/MW and 3.1 kg/MWh of reformer upkeep; the 14 Oct rebuild (Usai 2021
    loops + inverter + container) is ~44 t/MW with almost no maintenance."""
    _cached(fuel_cell)
    d = fuel_cell.decompose()
    assert 30_000 < d["bop_kgco2e_per_MW"] < 60_000, d["bop_kgco2e_per_MW"]
    assert d["maintenance_kgco2e_per_MWh"] < 0.1
    assert d["bop_duty_lifetime_hours"] == 80_000 and d["stack_lifetime_hours"] == 30_000


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


def test_fuel_cell_bop_cost_increment_tracks_the_exact_annuity():
    """The LP's calendar-anchored BoP increment against the exact CRF.

    A·(CRF(L) + o − 1/L) + A·h/H must equal A·(CRF(L) + o) when calendar binds
    and stay within 2 % of A·(CRF(H/h) + o) when duty does. REVIEW_RESPONSE_PLAN §1.
    """
    from optimisation import h2_capex as hc
    _cached(fuel_cell)
    d = fuel_cell.decompose()
    r, L, H = hc.FC_DISCOUNT_RATE, fuel_cell.BOP_CALENDAR_LIFETIME_YEARS, d["bop_duty_lifetime_hours"]
    costs = hc.fuel_cell_costs()
    for _, row in costs.iterrows():
        A, o = row.bop_GBP_per_MW, row.fixed_opex_frac
        for h in (100, 1000, H / L, 3000, 4000, 6000, 8760):
            lp = row.annual_GBP_per_MW_year + A * max(1.0 / L, h / H)
            exact = A * (hc.capital_recovery_factor(r, min(L, H / h)) + o)
            if h <= H / L:
                assert lp == pytest.approx(exact, rel=1e-9)
            else:
                assert lp == pytest.approx(exact, rel=0.02), f"{row.case} at {h} h"


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

    The old dashboard_config.WIND_LAT/WIND_LON was a field near St Albans — region 10,
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


# --- bought hydrogen carries the seller's trailer compression --------------
# The tank balance takes ``h2_buy`` at coefficient 1.0 while self-produced
# hydrogen pays ``h2_storage.compression_kwh_per_kg`` to enter the same vessel.
# These guard the term that closed that asymmetry.

def test_every_bought_colour_pays_trailer_compression():
    from optimisation import h2_prices as hp
    for colour in hp.INVENTORY:
        kwh = hp.bought_h2_compression_kwh_per_kg(colour)
        assert kwh > 0.0, f"{colour} pays no compression"
        assert hp.bought_h2_compression_kgco2e_per_kg(colour) > 0.0
        assert hp.bought_h2_compression_gbp_per_kg(colour) > 0.0


def test_compression_is_charged_in_both_objectives():
    """Carbon without cost is the study's standing one-directional bias."""
    from optimisation import h2_prices as hp
    for colour in hp.INVENTORY:
        carbon = hp.bought_h2_compression_kgco2e_per_kg(colour)
        cost = hp.bought_h2_compression_gbp_per_kg(colour)
        assert (carbon > 0) == (cost > 0), (
            f"{colour} is charged compression in one objective and not the "
            f"other — see audit.py and DATA_GAPS.md")


def test_green_compressor_never_runs_on_grid_carbon():
    """A plant behind a renewable meter cannot compress on grid power.

    This is the same incoherence ``GREEN_H2_ELECTRICITY_BASES`` exists to
    remove, and the reason DATA_GAPS' pre-fix ~0.761 kg/kg estimate was 33x
    too high.
    """
    from optimisation import h2_prices as hp
    for share in (0.0, 0.5, 1.0):
        I = hp.bought_h2_compression_gco2e_per_kwh("green", grid_share=share)
        assert I < 0.1 * hp.ECOINVENT_GB_LV_GCO2E_PER_KWH, (
            f"green compressor at grid_share={share} draws {I:.1f} g/kWh — "
            f"that is grid carbon on a renewable commodity")
    # fossil colours take the grid their own activities link to: the study's
    # own GB grid since 14 Oct, not ecoinvent's 2018 market
    for colour in ("grey", "blue", "turquoise"):
        assert (hp.bought_h2_compression_gco2e_per_kwh(colour)
                == hp.FOSSIL_SELLER_GRID_GCO2E_PER_KWH)
        assert hp.FOSSIL_SELLER_GRID_GCO2E_PER_KWH < 0.6 * hp.ECOINVENT_GB_LV_GCO2E_PER_KWH


def test_compression_uses_the_same_thermodynamics_as_self_production():
    from optimisation import h2_prices as hp, h2_storage as h2s
    assert hp.bought_h2_compression_kwh_per_kg("green") == pytest.approx(
        h2s.compression_kwh_per_kg(30.0, hp.BOUGHT_H2_TRAILER_PRESSURE_BAR))


def test_green_outlet_pressure_tracks_the_electrolyser_module():
    """Not restated, so the seller's PEM and the buyer's cannot drift apart."""
    from optimisation import h2_prices as hp, electrolysers as ely
    assert (hp.bought_h2_production_pressure_bar("green")
            == ely.DELIVERY_PRESSURE_BAR["PEM operation"])


def test_assumed_outlet_pressures_are_declared():
    from optimisation import h2_prices as hp
    assert hp.BOUGHT_H2_PRODUCTION_PRESSURE_ASSUMED == set(
        hp.BOUGHT_H2_PRODUCTION_PRESSURE_BAR), (
        "every hardcoded outlet pressure is unsourced and must say so")


def test_compression_moves_blue_far_more_than_green():
    """The finding that inverted DATA_GAPS' expectation.

    Green buys renewable power for its compressor, so the term is ~2 % of its
    production burden. Blue buys grid power — the study's 2025 GB grid at
    142 g/kWh since 14 Oct, so ~0.21 kg/kg (it was 0.45 on ecoinvent's 311 g
    low-voltage market) — still ten times green's.
    """
    from optimisation import h2_prices as hp
    green = hp.bought_h2_compression_kgco2e_per_kg("green", grid_share=0.5)
    blue = hp.bought_h2_compression_kgco2e_per_kg("blue")
    assert green < 0.05 and 0.15 < blue < 0.30
    assert blue > 8 * green


# =============================================================================
# Generation step-up transformers
# =============================================================================
def test_transformer_coefficient_round_trips():
    from optimisation import transformers as tx
    _cached(tx)
    assert "OK" in tx.check()


def test_transformer_mass_is_the_leng_bill_of_materials():
    """The transcribed numbers, guarded against drift.

    Wind is the fifty S11-2200/35 box transformers on Leng's 100 MW Gaoyou
    farm — 282,343 kg for 100 MW — read from the foreground activity
    optimiser_lca/stepup_transformers.py builds, not assembled here.
    """
    import dc_config as cfg
    from optimiser_lca import stepup_transformers as inv, registry as R
    from optimisation import transformers as tx
    _cached(tx)
    d = tx.decompose()
    assert sum(inv.TX_LENG_BOX_KG.values()) == pytest.approx(282_343.0, abs=1.0)
    assert d["wind"]["kg_per_MW"] == pytest.approx(2823.43, abs=0.01)
    assert d["wind"]["database"] == R.TRANSFORMER_DB
    assert d["wind"]["kgco2e_per_MW_year"] == pytest.approx(
        d["wind"]["kgco2e_per_MW"] / cfg.TX_ASSET_LIFE_YEARS)


def test_the_site_collects_where_the_data_centre_draws():
    """Turbines are LOW voltage and the data centre is MEDIUM, so the step-up
    is compulsory; collecting outside the data centre's band would leave an
    uncharged transformation in the chain."""
    from optimisation import transformers as tx
    _cached(tx)
    d = tx.decompose()
    lo, hi = d["medium_voltage_band_kV"]
    assert d["turbine_terminal_V"] < lo * 1000.0, "turbines must be low voltage"
    assert lo <= d["site_collection_kV"] <= hi


def test_wind_no_longer_scores_ecoinvents_electronics_transformer():
    """ecoinvent's transformer datasets are 280 g and 30 g electronic parts by
    its own comments, so wind must read the foreground bill instead. Solar
    still does not, and that is registered rather than fixed."""
    from optimisation import transformers as tx
    _cached(tx)
    d = tx.decompose()
    assert tx.LEGACY_ACTIVITY not in str(d["wind"])
    assert d["solar_legacy"]["activity"] == tx.LEGACY_ACTIVITY


def test_transformer_is_a_small_share_of_the_generation_it_connects():
    """A step-up is real but minor — a coefficient near wind's is a unit error."""
    from optimisation import transformers as tx
    _cached(tx)
    wind_per_mw_year = 19_244.0        # renewables.py, onshore, central case
    share = tx.kgco2e_per_mw_year("onshore_wind") / wind_per_mw_year
    assert 0.001 < share < 0.05, f"transformer is {share:.1%} of wind"


def test_transformer_is_absent_from_the_cost_objective():
    """Deliberate, not an omission: DESNZ/Arup capex already reaches the point
    of connection, so a £/MW transformer charge would double count."""
    import dataclasses
    from optimisation import dc_model as M
    names = {f.name for f in dataclasses.fields(M.Tech)}
    assert {"gwp_tx_wind_per_mw", "gwp_tx_solar_per_mwp"} <= names
    assert not {n for n in names if n.startswith("cost_tx")}


# =============================================================================
# Utility-scale PV basis — Smith et al. 2024, rescored on ecoinvent apos
# =============================================================================
# The default solar basis used to be a 3 kWp ROOFTOP system, and nothing in this
# suite noticed when it was swapped for a utility-scale one. These tests exist
# so the next change to it cannot pass silently.

def test_solar_default_basis_is_the_utility_scale_foreground():
    """`cap_solar` is a utility-scale MWp and must be priced as one."""
    from optimisation import renewables as R
    assert R.SOLAR_EMBODIED_BASIS == "smith_2024_upv_fixed_tilt"
    spec = R.SOLAR_EMBODIED_BASES[R.SOLAR_EMBODIED_BASIS]
    # Built, not transcribed: a foreground activity is scored in THIS project,
    # so the answer is ecoinvent 3.9.1 apos by construction rather than
    # inherited from another background and system model.
    assert spec.get("foreground"), "the default basis must be a foreground build"
    assert spec["gco2e_per_kwh"] is None
    # The rooftop basis stays selectable, to reproduce runs from before this.
    assert "iea_pvps_2023_mono_si" in R.SOLAR_EMBODIED_BASES


def test_solar_capital_is_build_plus_prorated_om():
    """Capital = one-off build + O&M prorated from its 30-year reference.

    The prorating cancels in the LP — annual = capital/life = build/life +
    om30/30 — but it must still be arithmetically right, because it moves the
    per-kWh columns that get quoted.
    """
    from optimisation import renewables as R
    if not R.UPV_CACHE_PATH.exists():
        pytest.skip("upv_decomposition_cache.json not built — run "
                    "`python -m optimiser_lca.build upv` then renewables.py")
    d = R.upv_decompose()
    life = 38.0
    expected = (d["capital_kgco2e_per_MWp"]
                + d["om30_kgco2e_per_MWp"] * life / d["om_reference_years"])
    got = R.solar_capital_kgco2e_per_mw("smith_2024_upv_fixed_tilt", 0.0,
                                        lifetime_years=life)
    assert got == pytest.approx(expected)
    # O&M is a real but minor term; a wildly different split means the
    # foreground was rebuilt wrong.
    assert 0.005 < d["om30_kgco2e_per_MWp"] / d["capital_kgco2e_per_MWp"] < 0.10


def test_solar_is_full_scope_and_not_capital_only():
    """The foreground carries its own installation and O&M.

    ``capital_only`` adds ecoinvent's non-capital residual back on top. Doing
    that here would double count, because this basis already includes those
    stages — unlike the raw ecoinvent basis, which genuinely is capital-only.
    """
    from optimisation import renewables as R
    df = R.apply_case(R.decompose_all(), "central",
                      solar_basis="smith_2024_upv_fixed_tilt")
    row = df[df.technology == "solar_pv"].iloc[0]
    assert row["capital_only"] is False or row["capital_only"] == False  # noqa: E712
    assert row["embodied_basis"] == "smith_2024_upv_fixed_tilt"
    # DESNZ/Arup central: 12.2 % net load factor over 38 years.
    assert row["study_load_factor"] == pytest.approx(0.122)
    assert row["study_lifetime_years"] == pytest.approx(38.0)


def test_utility_scale_beats_rooftop_on_bos_but_not_on_the_module():
    """The saving is the balance of system, and the module gets WORSE.

    This is the finding that makes the rebuild defensible rather than a
    convenient reduction: a 3 kWp roof amortises its inverter, cabling and
    mounting over 3 kW rather than megawatts, so its BOS per kWp is far larger —
    while the module rises, partly because APOS charges secondary aluminium a
    share of primary production where recycled-content allocation does not.
    """
    from optimisation import renewables as R
    rows = R.decompose_all()
    util = R.apply_case(rows, "central", solar_basis="smith_2024_upv_fixed_tilt")
    roof = R.apply_case(rows, "central", solar_basis="iea_pvps_2023_mono_si")
    u = util[util.technology == "solar_pv"].iloc[0]["capital_kgco2e_per_MW"]
    r = roof[roof.technology == "solar_pv"].iloc[0]["capital_kgco2e_per_MW"]
    assert u < r, "utility-scale should be the lower of the two per MWp"
    # ...but not by a suspicious margin. A large drop would mean whole stages
    # went missing rather than the BOS being amortised over more capacity.
    assert 0.75 < u / r < 0.95


def test_solar_module_reproduces_smiths_published_epeat_result():
    """The transcription's end-to-end check, and the reason to trust it.

    Smith states his average-import module sits ABOVE the 630 kg CO2e/kW EPEAT
    low-carbon threshold. Rebuilding his inventory on a DIFFERENT system model
    (apos, where he published cut-off) reproduces that. If this fails, the
    transcription or the chain wiring has drifted.
    """
    from optimiser_lca import registry, upv
    bd = pytest.importorskip("bw2data")
    try:
        act = bd.get_activity((registry.SOLAR_DB, registry.UPV_MODULE))
    except Exception:
        pytest.skip("solar foreground not built in this Brightway project")
    import lca_helpers as H
    from optimisation import renewables as R
    per_m2 = H.run_lca_score(act, R._gwp_method(bd))
    per_kwdc = per_m2 / (upv.UPV_PV_W_PER_M2 / 1000.0)
    assert per_kwdc > 630.0, (
        f"module is {per_kwdc:,.0f} kg CO2e/kWdc; Smith reports his "
        "average-import module above the 630 EPEAT threshold")
    assert per_kwdc < 900.0, "implausibly high — check the chain links"


def test_soec_electric_boiler_moves_heat_onto_electricity():
    """The electric boiler swaps the gas row's burden for kWh, and nothing else."""
    _cached(electrolysers)
    rows = {r["technology"]: r for r in electrolysers.decompose_all()}
    soec = rows["SOEC operation"]
    gas = electrolysers.with_heat_source(soec, "gas_boiler")
    ele = electrolysers.with_heat_source(soec, "electric_boiler")
    assert gas["kwh_per_kg"] == soec["kwh_per_kg"]
    assert gas["variable_kgco2e_per_kg"] == soec["variable_kgco2e_per_kg"]
    heat_mj, heat_score = next((a, s) for n, a, s in soec["_consumables"] if "heat" in n)
    added = heat_mj / 3.6 / electrolysers.ELECTRIC_BOILER_EFFICIENCY
    assert ele["kwh_per_kg"] == pytest.approx(soec["kwh_per_kg"] + added)
    assert ele["heat_kwh_electric_per_kg"] == pytest.approx(added)
    assert ele["variable_kgco2e_per_kg"] == pytest.approx(
        soec["variable_kgco2e_per_kg"] - heat_score)
    # Water is all that is left once the heat is off the books.
    assert 0 < ele["variable_kgco2e_per_kg"] < 0.3
    assert ele["capital_kgco2e_per_MW"] == soec["capital_kgco2e_per_MW"]
    # Not a choice for the other technologies.
    pem = rows["PEM operation"]
    assert electrolysers.with_heat_source(pem, "electric_boiler")["kwh_per_kg"] == pem["kwh_per_kg"]
    with pytest.raises(ValueError):
        electrolysers.with_heat_source(soec, "heat_pump")


# =============================================================================
# Sweep overrides on build_tech (CARBON_PLAN.md 1.2)
# =============================================================================
_NO_NETWORK = {"capacity_GBP_per_MW_year": 0.0, "fixed_GBP_per_year": 0.0}


def test_fuel_cell_container_is_scored_separately():
    _cached(fuel_cell)
    d = fuel_cell.decompose()
    # 3.7 of the BoP's 44 t/MW, at one 20 ft container per MW.
    assert d["bop_kw_per_container"] == 1000.0
    assert 0.05 < d["bop_container_kgco2e_per_MW"] / d["bop_kgco2e_per_MW"] < 0.15


def test_sweep_overrides_reach_the_tech():
    _cached(fuel_cell)
    from optimisation import battery
    from optimisation import dc_inputs as I
    base = I.build_tech("london", _NO_NETWORK)
    d = fuel_cell.decompose()
    t = I.build_tech("london", _NO_NETWORK, fc_stack_calendar_years=5.0,
                     fc_bop_calendar_years=15.0, fc_kw_per_container=500.0,
                     batt_usable_fraction=0.80)
    assert (t.fc_stack_calendar_years, t.fc_bop_calendar_years) == (5.0, 15.0)
    # Half a container per MW more: the container term doubles, nothing else moves.
    assert t.gwp_fc_bop_per_mw - base.gwp_fc_bop_per_mw == pytest.approx(
        d["bop_container_kgco2e_per_MW"], rel=1e-9)
    assert t.gwp_batt_e == pytest.approx(
        base.gwp_batt_e * battery.USABLE_FRACTION / 0.80, rel=1e-9)
    # The BoP life moves the cost annuity too, not just the carbon count.
    assert t.cost_fc != pytest.approx(base.cost_fc, rel=1e-6)
    assert t.labels["fc_kw_per_container"] == 500.0
    # Defaults reproduce the module constants.
    assert base.gwp_fc_bop_per_mw == pytest.approx(d["bop_kgco2e_per_MW"], rel=1e-12)
    assert base.fc_stack_calendar_years == fuel_cell.STACK_CALENDAR_LIFETIME_YEARS


@pytest.mark.parametrize("kw,bad", [("fc_stack_calendar_years", 0.0),
                                    ("fc_bop_calendar_years", -5.0),
                                    ("fc_kw_per_container", float("nan")),
                                    ("batt_usable_fraction", 1.2)])
def test_bad_sweep_override_is_refused_before_loading(kw, bad):
    from optimisation import dc_inputs as I
    with pytest.raises(ValueError, match=kw):
        I.build_tech("london", {}, **{kw: bad})


def test_sensitivity_variant_lists():
    from optimisation import sensitivity as S
    v = S.one_at_a_time({"a": [1, None, 2], "b": [3]})
    assert v == [{}, {"a": 1}, {"a": 2}, {"b": 3}]
    assert S.grid({"a": [1, 2], "b": [3, 4]}) == [
        {"a": 1, "b": 3}, {"a": 1, "b": 4}, {"a": 2, "b": 3}, {"a": 2, "b": 4}]



# =============================================================================
# Gas-route carbon balance and the study grid (CARBON_PLAN 3.4-3.6)
# =============================================================================
def test_gas_routes_close_their_carbon_balance():
    from optimiser_lca import hydrogen as h
    # ecoinvent's own GB high-pressure gas: ~2.0 kg CO2 per m3 burned
    assert h.GAS_CO2_KG_PER_M3 == pytest.approx(1.9956, rel=1e-4)
    smr_out = 9.0 + h.SMR_CO2_CLOSURE
    ccs_out = 0.99 + h.SMR_CCS_CO2_CLOSURE + h.CO2_CAPTURED_PER_KG_H2
    assert smr_out == pytest.approx(4.85 * h.GAS_CO2_KG_PER_M3, rel=1e-12)
    assert ccs_out == pytest.approx(5.33 * h.GAS_CO2_KG_PER_M3, rel=1e-12)
    assert 0 < h.SMR_CO2_CLOSURE < h.SMR_CCS_CO2_CLOSURE


def test_gb_grid_shares_match_the_series():
    from optimiser_lca import gb_grid
    assert "OK" in gb_grid.check_against_series()


def test_fossil_routes_take_the_study_grid():
    from optimiser_lca import hydrogen as h, registry as R
    for act in h.activities:
        if act.code in (R.SMR, R.SMR_CCS, R.CCS, R.MP_E):
            assert not any(row[0] == "electricity_hv_gb" for row in act.technosphere), act.code


# =============================================================================
# Wind life extension and net yield; the second stack basis (CARBON_PLAN 3.1-3.2)
# =============================================================================
def test_wind_parts_fraction():
    from optimisation import renewables as r
    assert r.wind_parts_fraction(35, "none") == 0.0
    assert r.wind_parts_fraction(35, "servicing") == pytest.approx(0.07)
    assert r.wind_parts_fraction(35, "servicing_overhaul") == pytest.approx(0.07 + 0.205)
    # within the design life there is no overhaul
    assert r.wind_parts_fraction(25, "servicing_overhaul") == pytest.approx(0.05)
    with pytest.raises(ValueError):
        r.wind_parts_fraction(35, "bogus")


def test_central_wind_restates_above_the_lowest_published_lca():
    from optimisation import renewables as r
    w = r.apply_case(r.decompose_all(), "central").set_index("technology").loc["onshore_wind"]
    # IPCC AR5's lowest published onshore figure is ~7 g CO2e/kWh; a 35-y
    # turbine charged no parts sat at 5.8.
    assert w.restated_kgco2e_per_kWh * 1000 > 7.0
    none = r.apply_case(r.decompose_all(), "central", wind_life_extension="none") \
        .set_index("technology").loc["onshore_wind"]
    assert none.restated_kgco2e_per_kWh * 1000 == pytest.approx(5.77, abs=0.05)


def test_wind_net_factor_is_its_components():
    from optimisation import profiles as p
    prod = 1.0
    for v in p.WIND_NET_COMPONENTS.values():
        prod *= v
    assert p.WIND_NET_FACTOR == pytest.approx(prod)
    assert 0.80 < p.WIND_NET_FACTOR < 0.90           # EWEA's 10-20 % total loss


def test_gramc_stack_is_the_lighter_basis():
    _cached(fuel_cell)
    d = fuel_cell.decompose()
    b = fuel_cell.stack_kgco2e_per_mw(d, "babatunde_2024")
    g = fuel_cell.stack_kgco2e_per_mw(d, "gramc_2025")
    assert fuel_cell.stack_kgco2e_per_mw(d) == b              # the default
    assert 0.3 < g / b < 0.7
    from optimisation import dc_inputs as I
    t = I.build_tech("london", _NO_NETWORK, fc_stack_basis="gramc_2025")
    assert t.gwp_fc_stack_per_mw == pytest.approx(g)


def test_battery_cell_basis_swaps_only_the_cell():
    from optimisation import battery as b
    base = b.embodied_components()["energy_kgco2e_per_kWh"]
    j = b.embodied_components(cell_basis="jasper_fig4_311")["energy_kgco2e_per_kWh"]
    delta = (b.CELL_KGCO2E_PER_KWH["jasper_fig4_311"] - b.CELL_KGCO2E_PER_KWH["voss_cn"])
    assert j - base == pytest.approx(delta / b.USABLE_FRACTION)


def test_facility_charges_the_refrigerant_it_tops_up():
    from optimiser_lca import data_centre as dc
    act = dc.activities[0]
    bought = next(a for k, a, *_ in act.technosphere if k == "refrigerant_r134a")
    leaked = next(a for k, a, *_ in act.biosphere if k == "hfc134a_air")
    assert leaked == bought == 450


def test_tank_carries_its_frame_and_pad():
    from optimisation import h2_storage
    for r in h2_storage.decompose():
        share = r["foundations_kgco2e_per_kg_capacity"] / r["kgco2e_per_kg_capacity"]
        assert 0.05 < share < 0.20, (r["design"], share)
