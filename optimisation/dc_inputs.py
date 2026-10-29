"""
Assembling the LP's inputs — one place, so nothing drifts.
=============================================================================

``dc_model.py`` deliberately knows nothing about Brightway, the NESO API or the
DESNZ tables: it takes a ``Tech`` of resolved coefficients and a ``Series`` of
aligned half-hourly arrays, and builds an LP. This module is the seam that fills
both in, and it is the only place where a coefficient's provenance and its use
meet.

Two rules it enforces
---------------------
**No double counting of electrolyser capital.** ``run_non_electricity_lca``'s
``fixed_kgco2e_per_kg`` already contains the amortised capital good. This module
charges capital per MW, so it must use ``variable_kgco2e_per_kg`` instead, and it
calls ``electrolysers.assert_no_double_count`` to say so out loud.

**Network charges keep their shape.** The volumetric part joins the wholesale
price on ``imp[t]``; the capacity part goes on ``cap_grid``; the connection part
is a fixed annual cost. Collapsing them into one £/MWh would erase the saving a
battery or hydrogen store earns by flattening the import profile.

Run:  python optimisation/dc_inputs.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
OUT_DIR = ROOT / "optimisation_outputs"
# v2: split by driver and net of the standby generator, so a v1 file is not
# merely stale but the wrong shape.
DC_CACHE = OUT_DIR / "dc_facility_decomposition_v3_cache.json"   # v3: IT normalised on 5.38 MW

from optimisation import dc_model, sites
from optimisation import trace as T

DISCOUNT_RATE = 0.06        # ASSUMED, unsourced; one discount-rate policy is a TODO (audit §4)


def data_centre_coefficients(refresh: bool = False) -> dict:
    """The facility's own burden, split by what each part actually scales with.

    Constant across every architecture — the same building is being powered
    each way — so it shifts every result by the same amount and never changes a
    ranking. Reported separately for exactly that reason.

    Two drivers, because they do not move together. Shell, servers and UPS scale
    with **installed IT capacity**; water, water treatment and refrigerant scale
    with **delivered energy** and so follow PUE. Charging both on facility draw,
    as this module used to, shrank the concrete whenever the chiller improved.

    The standby diesel generator is scored and reported but **excluded**: this
    study makes backup a decision variable, so importing it would charge every
    architecture for a machine the optimiser may already have built as a fuel
    cell. See ASSUMPTIONS.md §7.
    """
    if DC_CACHE.exists() and not refresh:
        try:
            return json.loads(DC_CACHE.read_text(encoding="utf-8"))
        except Exception:
            pass
    import lca_helpers as H
    import dc_config as cfg
    from optimisation import baseline_grid as bg

    H.setup_brightway()
    method = bg.gwp_method()
    _dc, groups, kwh = bg.decompose_data_centre_by_driver(method)
    years = float(cfg.DC_OPERATION_YEARS)
    pue_ref = float(cfg.DC_REFERENCE_PUE)

    from optimiser_lca import data_centre as zhang
    facility_mw = kwh / years / dc_model.HOURS_PER_YEAR / 1000.0
    # The IT-driven rows were sized on Zhang's 5.38 MW of IT, not on the 5.219 MW read back
    # from the rounded 1.60e9 kWh (ASSUMPTIONS §2; user, 26 Oct 2026).
    reference_it_mw = zhang.ZHANG_IT_MW
    out = {
        "electricity_kwh_over_life": kwh,
        "operation_years": years,
        "reference_pue": pue_ref,
        "reference_facility_mw": facility_mw,
        "reference_it_mw": reference_it_mw,
        "it_kgco2e_over_life": groups["it"],
        "it_kgco2e_per_year": groups["it"] / years,
        "it_kgco2e_per_mw_it_year": groups["it"] / years / reference_it_mw,
        "energy_kgco2e_over_life": groups["energy"],
        "energy_kgco2e_per_mwh": groups["energy"] / (kwh / 1000.0),
        "backup_kgco2e_per_year_excluded": groups["backup"] / years,
        "charged_kgco2e_per_year_at_reference": (groups["it"] + groups["energy"]) / years,
    }
    OUT_DIR.mkdir(exist_ok=True)
    DC_CACHE.write_text(json.dumps(out, indent=2), encoding="utf-8")
    return out


def build_series(site, start: str, end: str, size_mw_it: float,
                 pue: float | None = None, token: str | None = None,
                 connection_headroom: float | None = None,
                 auto_build: bool = True, on_progress=None,
                 wind_net_factor: float | None = None,
                 ccl_under_cca: bool | None = None,
                 shortfall_route: str = "upgrade") -> dc_model.Series:
    """Aligned half-hourly inputs for one site and window.

    ``site`` is anything ``sites.get`` accepts — a ``Site``, a ``(lat, lon)``
    pair, a ``"lat,lon"`` string, or a preset name. Coordinates are the real
    interface; presets are shortcuts.

    ``auto_build`` builds the grid series if none covers the window yet, rather
    than raising — see ``profiles.load_grid_and_price``. On by default, so any
    window at any GB coordinate just works; the wait only happens when
    something is genuinely missing. ``on_progress`` takes a one-line notice
    before that wait.

    ``wind_net_factor`` turns ninja's single-turbine capacity factor into a
    farm's net one; defaults to ``profiles.WIND_NET_FACTOR`` (0.851). Pass 1.0
    to reproduce runs before 14 Oct 2026.

    ``ccl_under_cca`` says whether the site holds a Climate Change Agreement
    (92 % off the CCL); defaults to ``levies.CCL_UNDER_CCA``.
    """
    from optimisation import network_charges as nc
    from optimisation import profiles
    import dc_config as cfg

    # One default PUE for every entry point that does not choose its own:
    # Zhang's, the facility the inventory describes. It used to be 1.15 here,
    # 1.0 in the CLI and the matrix, 1.2 in audit and 1.5 on the page.
    pue = float(cfg.DC_REFERENCE_PUE) if pue is None else float(pue)
    site = sites.get(site)
    # tilt/azimuth are left unset so profiles.fetch_solar_cf takes them from
    # dc_config. Before this, they were hard-coded defaults in that
    # function's signature that this call never passed, so every data centre run
    # silently used a 35-degree array while the embodied carbon was charged for
    # a 20-degree one.
    df, meta = profiles.build(site.lat, site.lon, start, end, token=token,
                              carbon_api_region=site.carbon_api_region,
                              auto_build=auto_build, on_progress=on_progress)
    sites.require_grid_region(site, meta["grid_file"])

    index = pd.DatetimeIndex(df.index)
    # load -> connection ceiling -> band. The band is read from the agreed
    # capacity, which is the connection, not the load: charging a 300 MW site on
    # its load alone is how it stayed on a 7 MW band. A site that pins its own
    # connection limit keeps it; otherwise the ceiling is derived and used both
    # as the band's basis and as the LP's upper bound on cap_grid.
    load_mw = size_mw_it * pue
    annual_mwh = load_mw * dc_model.HOURS_PER_YEAR
    conn_mw, conn_note = sites.max_connection_mw(load_mw, connection_headroom)
    if site.connection_limit_mw is not None:
        conn_mw, conn_note = float(site.connection_limit_mw), ""
    transmission, tier_note = nc.is_transmission_connected(
        conn_mw, site.carbon_api_region, site.transmission_connected)
    tdr_band, tdr_note = site.tdr_band, ""
    if tdr_band is None:
        tdr_band, tdr_note = nc.tdr_band_for(
            conn_mw, annual_mwh, region=site.carbon_api_region,
            transmission_connected=transmission)
    # The tier and band are read from the ceiling, so the connection the LP
    # builds is held inside that band: floor <= cap_grid <= ceiling. Otherwise a
    # site charged as EHV4 or T-Demand4 could build a connection that belongs to
    # a cheaper band (CONNECTION_TIER_PLAN.md step 2).
    conn_floor = min(nc.band_floor_mw(transmission, tdr_band, site.carbon_api_region),
                     conn_mw)
    conn_voltage = nc.connection_voltage(conn_mw, site.carbon_api_region, transmission)
    # Where the connection runs to (substations.py, since 29 Oct 2026): the
    # nearest substation at the connection voltage, its cable route and its
    # spare capacity — the route prices the cable in connection_cost, and a
    # 33/132 kV site's local network charges are set for its own node.
    from optimisation import substations
    conn_point = substations.connection_point(site.lat, site.lon, conn_voltage, conn_mw,
                                              site.carbon_api_region, shortfall_route)
    charges = nc.import_charges(index, zone_no=site.tnuos_zone, tdr_band=tdr_band,
                                transmission_connected=transmission,
                                site=(site.lat, site.lon), connection_voltage=conn_voltage)
    # Grid carbon is delivered at the site's own voltage: generation, grossed
    # up for losses down to it, plus the network's embodied carbon. The same
    # constants charge a bought-hydrogen seller's grid delivery.
    from optimiser_lca import grid as grid_lca
    from optimisation import levies
    voltage = nc.delivery_voltage(transmission, tdr_band)
    # The import price per MWh metered: the energy and BSUoS the supplier buys,
    # grossed up for losses — the line loss factor of the site's own licence area
    # for its connection voltage and time period, times the offtaking TLM
    # (levies.loss_series) — plus DUoS (the area's own tariff, duos_areas) and the
    # policy levies, which are charged on metered supply. Levies were absent
    # until 28 Oct 2026; losses were the carbon side's ecoinvent factor.
    loss = levies.loss_series(index, conn_voltage, site.carbon_api_region).to_numpy()
    lev = levies.import_levies(index, under_cca=ccl_under_cca)
    price = ((df["price_GBP_per_MWh"].to_numpy() + charges["bsuos_GBP_per_MWh"].to_numpy()) * loss
             + charges["duos_GBP_per_MWh"].to_numpy()
             + lev["levies_GBP_per_MWh"].to_numpy())
    grid_gwp = grid_lca.delivered(df["grid_generation_kgco2e_per_kwh"].to_numpy(), voltage)
    if T.active():
        _trace_grid(df, grid_gwp, voltage, site, start, end, meta)

    net = profiles.WIND_NET_FACTOR if wind_net_factor is None else float(wind_net_factor)
    if not 0.5 <= net <= 1.0:
        raise ValueError(f"wind_net_factor must be in [0.5, 1.0], got {net!r}")
    series = dc_model.Series(
        index=index,
        dt_hours=float(meta["slice_hours"]),
        demand_mw=np.full(len(index), size_mw_it * pue),
        cf_wind=df["wind_cf"].to_numpy() * net,
        cf_solar=df["solar_cf"].to_numpy(),
        grid_gwp_per_mwh=grid_gwp * 1000.0,
        grid_price_per_mwh=price,
        triad_window=nc.triad_window(index),
    )
    meta["network_charges"] = charges["components"]
    meta["levies"] = {**lev["components"], "loss_gross_up_mean": float(np.mean(loss)),
                      "connection_voltage": conn_voltage}
    meta["capacity_GBP_per_MW_year"] = charges["capacity_GBP_per_MW_year"]
    meta["fixed_GBP_per_year"] = charges["fixed_GBP_per_year"]
    meta["tdr_band"] = tdr_band
    meta["tdr_band_note"] = tdr_note
    meta["connection_limit_mw"] = conn_mw
    meta["connection_limit_note"] = conn_note
    meta["connection_floor_mw"] = conn_floor
    meta["connection_site"] = conn_point
    meta["connection_headroom"] = (
        connection_headroom if connection_headroom is not None
        else sites.CONNECTION_HEADROOM_ASSUMED)
    meta["transmission_connected"] = transmission
    meta["connection_voltage"] = nc.connection_voltage(conn_mw, site.carbon_api_region,
                                                       transmission)
    meta["connection_tier_note"] = tier_note
    meta["grid_delivery_voltage"] = voltage
    meta["wind_net_factor"] = net
    meta["mean_wind_cf_net"] = float(np.mean(series.cf_wind))
    meta["mean_grid_delivered_kgco2e_per_kwh"] = float(grid_gwp.mean())
    meta["site"] = site.key
    meta["site_name"] = site.name
    meta["lat"], meta["lon"] = site.lat, site.lon
    meta["carbon_api_region"] = site.carbon_api_region
    meta["tnuos_zone"] = site.tnuos_zone
    return series, meta


def _trace_grid(df, grid_gwp, voltage, site, start, end, meta):
    """Record how the LP's half-hourly grid carbon is made (``optimisation.trace``).
    The series is shown by its mean over the window; the LP charges it half-hour
    by half-hour."""
    from optimiser_lca import grid as grid_lca
    sources = [T.ecoinvent(*p.identity, database=p.database) for p in grid_lca.SOURCES.values()]
    T.step("grid.generation_mean", float(df["grid_generation_kgco2e_per_kwh"].mean()),
           "kg CO2e per kWh generated, mean of the window",
           f"Grid generation intensity, {getattr(site, 'key', site)} {start} to {end}: each "
           "half-hour is the sum over fuels of the region's share times that fuel's score",
           uses=sources, grade="derived", source="NESO Carbon Intensity API regional mix; "
           "optimiser_lca/grid.py SOURCES scored on ecoinvent 3.9.1 apos",
           inputs={"half_hours": len(df), "grid_file": str(meta.get("grid_file", ""))},
           note="Wind is split by ecoinvent's own GB market weights; imports by where they "
                "came from in that half-hour; pumped storage carries its plant plus the "
                "electricity it returns (optimiser_lca/grid.py).")
    d = grid_lca.delivery(voltage)
    chain = [T.ecoinvent(m, "GB") for v, m, _t in grid_lca._CHAIN[:grid_lca.VOLTAGES.index(voltage) + 1]]
    T.step(f"grid.delivery.{voltage}", d["gross_up"], "kWh generated per kWh delivered",
           f"Losses down to {voltage} voltage, from ecoinvent's GB voltage chain",
           uses=chain, inputs={"network_gco2e_per_kwh": d["network_gco2e_per_kwh"]},
           grade="derived", note="The network's own embodied carbon is added per kWh delivered; "
           "optimiser_lca.grid.check_delivery re-derives both from the live database.")
    T.step("grid.delivered_mean", float(grid_gwp.mean()), "kg CO2e per kWh delivered, mean of the window",
           f"Grid carbon delivered at the site's {voltage} voltage: the series the LP charges",
           uses=["grid.generation_mean", f"grid.delivery.{voltage}"], grade="derived",
           note="Shown as the mean; the LP multiplies each half-hour's value by that half-hour's import.")


def resample(series: dc_model.Series, freq_hours: float) -> dc_model.Series:
    """Coarsen a half-hourly series to speed up a solve.

    Averaging is the right reduction for every one of these: demand, capacity
    factors, carbon intensity and price all enter the LP linearly and are all
    energy-weighted over the step. What is lost is *within-step variability* — a
    half-hour of very clean grid inside a dirty hour stops being separately
    addressable — and also the covariance between price, carbon intensity and
    renewable output, which is what actually moves the answer. The net direction
    is not predictable a priori, so it was measured rather than argued.

    Measured on grid_res_battery at the London site over 2025, min-cost:

    ====== ======= ======== ======== =========
    step   slices  solve s  cost     GWP
    ====== ======= ======== ======== =========
    30 min  17,350     31.2  —        —
    1 h      8,675      9.0  -0.14 %  -0.32 %
    2 h      4,337      2.6  -0.20 %  -1.20 %
    ====== ======= ======== ======== =========

    Capacities move by up to 2.2 % at 1 h and 2.7 % at 2 h. **1 h is the sweet
    spot**: 3.5x faster for errors well inside the uncertainty on any input.
    2 h is for exploration only — a 1.2 % carbon error is comparable to the
    differences the study is trying to resolve between options.

    Inter-seasonal chronology is untouched, which is what matters for the tank.
    """
    step = int(round(freq_hours / series.dt_hours))
    if step <= 1:
        return series
    n = (series.n // step) * step
    def mean(a):
        return np.asarray(a[:n], dtype=float).reshape(-1, step).mean(axis=1)
    return dc_model.Series(
        index=series.index[:n:step],
        dt_hours=series.dt_hours * step,
        demand_mw=mean(series.demand_mw),
        cf_wind=mean(series.cf_wind),
        cf_solar=mean(series.cf_solar),
        grid_gwp_per_mwh=mean(series.grid_gwp_per_mwh),
        grid_price_per_mwh=mean(series.grid_price_per_mwh),
        # A coarse step could hold a Triad if any of its half-hours could.
        triad_window=(None if series.triad_window is None else
                      np.asarray(series.triad_window[:n], dtype=bool).reshape(-1, step).any(axis=1)),
    )


def build_tech(site, meta: dict, *, ely_tech: str = "PEM operation",
               tank_design: str | None = None, h2_colour: str | None = None,
               cost_case: str = "central", horizon_years: float = 25.0,
               size_mw_it: float = 100.0, pue: float | None = None,
               solar_basis: str | None = None, h2_variant: str | None = None,
               green_h2_basis: str | None = None,
               green_h2_grid_share: float | None = None,
               h2_colour_2: str | None = None,
               h2_variant_2: str | None = None,
               soec_heat: str | None = None,
               batt_standing_loss_per_hour: float | None = None,
               tank_leakage_per_hour: float | None = None,
               fc_stack_calendar_years: float | None = None,
               fc_bop_calendar_years: float | None = None,
               fc_kw_per_container: float | None = None,
               batt_usable_fraction: float | None = None,
               wind_life_extension: str | None = None,
               fc_stack_basis: str | None = None,
               batt_cell_basis: str | None = None,
               batt_tx_x_eff: float | None = None,
               fc_tx_x_eff: float | None = None,
               fc_tx_energised: bool | None = None,
               cutoff: str | None = None) -> dc_model.Tech:
    """Resolve every coefficient the LP needs. Touches Brightway only via caches.

    ``cutoff`` is the cut-off register's seam (``optimiser_lca/exclusions.py``,
    CUTOFF_RULE_PLAN.md). ``None`` (the default model) adds each
    ``included_estimate`` entry's central estimate onto its technology's
    coefficient — the unsourced flows that failed the 1 % test and are carried
    as estimates until a source replaces them. ``"upper"`` also adds every
    still-excluded entry at its upper estimate (rule 3's design-change run);
    ``"none"`` adds nothing, reproducing the model as it stood before 22 Oct
    2026. What was added, per coefficient, is written into ``labels``.

    ``batt_tx_x_eff`` and ``fc_tx_x_eff`` are the ASSUMED energy-weighted
    loadings of the battery's and fuel cell's container step-ups, and
    ``fc_tx_energised`` whether a standby fuel cell's unit draws its no-load
    loss every hour (it does by default). All three default to
    ``conversion_losses.py`` and are recorded in ``labels``.

    ``pue`` is accepted for symmetry with ``build_series`` and ignored: PUE
    reaches the facility's carbon only through demand, which the series
    carries (the energy-driven part is charged per MWh of it), and the
    IT-driven part scales with ``size_mw_it`` alone.

    ``solar_basis`` selects the inventory behind solar's embodied carbon and
    defaults to ``renewables.SOLAR_EMBODIED_BASIS`` — IEA PVPS rather than
    ecoinvent, whose GB PV activity is a 2008 plant. Pass ``"ecoinvent"`` to
    reproduce results from before that default changed.

    ``green_h2_basis`` selects the electricity the *seller* of bought green
    hydrogen is assumed to run on, and defaults to
    ``h2_prices.GREEN_H2_ELECTRICITY_BASIS`` — ecoinvent's GB onshore wind
    activity. Pass ``"ecoinvent_gb_grid"`` to reproduce results from before that
    default changed. It has no effect on any other colour.

    ``green_h2_grid_share`` is the fraction of bought green hydrogen taken over
    the network rather than from behind a generator's meter, and defaults to
    ``h2_prices.GREEN_H2_GRID_SHARE`` (0.5). It blends the two green price rows
    and their delivery burdens together, since both are renewable and differ only
    in how the electricity reaches the seller's electrolyser.

    ``h2_variant`` pins one row of ``h2_prices_recommended.csv`` instead of
    blending; only green has two. Passing it overrides ``green_h2_grid_share``.

    ``h2_colour_2`` is a second bought colour, priced on its own row and given
    its own LP variable, so a site can hold a cheap dirty contract and an
    expensive clean one at the same time and let the sweep decide the mix. It
    must differ from ``h2_colour``: two streams of one colour are the same
    commodity at the same price, and the split between them would be arbitrary.
    ``h2_variant_2`` pins its row the way ``h2_variant`` pins the first.

    ``soec_heat`` is how SOEC's external heat is raised, one of
    ``electrolysers.SOEC_HEAT_SOURCES``, defaulting to the inventoried gas
    boiler. ``"electric_boiler"`` puts the heat on the site's electricity; see
    ``electrolysers.with_heat_source``. Ignored for AE and PEM.

    ``batt_standing_loss_per_hour`` and ``tank_leakage_per_hour`` override the
    two storage standing losses, as a fraction of the stock lost per *hour*
    held (``dc_model`` multiplies by the step length, so the same number means
    the same thing at half-hourly and hourly resolution). They default to
    ``battery.STANDING_LOSS_PER_HOUR`` and the tank design's
    ``leakage_frac_per_hour``, both zero and ASSUMED. They exist to sweep, not
    to change the defaults: the two push in opposite directions in the
    hydrogen-versus-battery seasonal contest, and DATA_GAPS.md records the band
    the sweep measured. A %/day figure converts as ``pct / 100 / 24``.

    ``fc_stack_calendar_years``, ``fc_bop_calendar_years``,
    ``fc_kw_per_container`` and ``batt_usable_fraction`` override four more
    ASSUMED constants for a sweep (``optimisation/sensitivity.py``): the fuel
    cell's two calendar lives (``fuel_cell.STACK_CALENDAR_LIFETIME_YEARS``,
    ``BOP_CALENDAR_LIFETIME_YEARS``), the kW of fuel cell one container houses
    (``optimiser_lca.fuel_cell.FC_KW_PER_CONTAINER``) and the battery's usable
    share of nameplate (``battery.USABLE_FRACTION``). None keeps the default.
    ``fc_stack_basis`` is one of ``fuel_cell.STACK_BASES``; ``batt_cell_basis``
    one of ``battery.CELL_KGCO2E_PER_KWH``.
    ``wind_life_extension`` is one of ``renewables.WIND_LIFE_EXTENSION_BASES``:
    the parts a 20-y ecoinvent turbine needs to reach this study's life.
    The BoP life moves the cost annuity as well as the carbon replacement
    count; the container count rescales only the container's share of the BoP
    carbon, which ``fuel_cell.decompose`` scores separately, so no inventory is
    rebuilt.
    """
    # Validated before anything is loaded, so a bad sweep value fails at once
    # rather than after the caches (and Brightway) have been read.
    _standing_loss(batt_standing_loss_per_hour, "batt_standing_loss_per_hour")
    _standing_loss(tank_leakage_per_hour, "tank_leakage_per_hour")
    for name, v in (("fc_stack_calendar_years", fc_stack_calendar_years),
                    ("fc_bop_calendar_years", fc_bop_calendar_years),
                    ("fc_kw_per_container", fc_kw_per_container)):
        if v is not None and not (np.isfinite(v) and v > 0):
            raise ValueError(f"{name} must be a positive number, got {v!r}")
    if batt_usable_fraction is not None and not 0.5 <= batt_usable_fraction <= 1.0:
        raise ValueError(f"batt_usable_fraction must be in [0.5, 1.0], "
                         f"got {batt_usable_fraction!r}")

    import dc_config as cfg
    from optimisation import battery as batt
    from optimisation import electrolysers as ely
    from optimisation import fuel_cell as fc
    from optimisation import grid_connection as gc
    from optimisation import h2_capex as hc
    from optimisation import h2_prices
    from optimisation import h2_storage as h2s
    from optimisation import renewables as ren
    from optimisation import transformers as tx
    from optimisation import tech_costs as tc

    # The guard this whole design exists to make explicit. Bought green H2 does
    # use the foreground's fixed figure, and that is not a violation: it charges
    # the *seller's* electrolyser per kg purchased, while capital_kgco2e_per_MW
    # charges the one the LP builds. Different assets, independent LP variables.
    ely.assert_no_double_count(uses_capital_per_mw=True, uses_foreground_fixed=False)

    from optimiser_lca import h2_tank
    tank_design = tank_design or h2_tank.TANK_DESIGN
    solar_basis = solar_basis or ren.SOLAR_EMBODIED_BASIS
    green_h2_basis = green_h2_basis or h2_prices.GREEN_H2_ELECTRICITY_BASIS
    emb = ren.apply_case(ren.decompose_all(), cost_case, solar_basis=solar_basis,
                         wind_life_extension=wind_life_extension).set_index("technology")
    ann = tc.annualised_table()

    def gen_cost(asset):
        r = ann[(ann.asset == asset) & (ann.case == cost_case)].iloc[0]
        return float(r.total_annual_cost_GBP_per_MW_year)

    def gen_gwp(asset):
        r = emb.loc[asset]
        # Capital annuity plus, for wind/offshore, the non-capital residual
        # ecoinvent reports per kWh - see renewables.apply_case.
        return float(r.annual_kgco2e_per_MW)

    # battery
    bc = batt.cost_components()[cost_case]
    crf_b = batt.capital_recovery_factor(batt.WACC_REAL, batt.ASSET_LIFE_YEARS)
    annuity_b = crf_b + batt.FIXED_OPEX_PCT_CAPEX[cost_case]
    be = batt.embodied_components(usable_fraction=batt_usable_fraction,
                                  cell_basis=batt_cell_basis)

    # electrolyser
    ely_row = ely.with_heat_source(
        next(r for r in ely.decompose_all() if r["technology"] == ely_tech), soec_heat)
    ely_costs = hc.electrolyser_costs()
    key = "electrolyser_" + ely_tech.split()[0].lower()
    ec = ely_costs[(ely_costs.asset == key) & (ely_costs.case == cost_case)].iloc[0]
    crf_e = batt.capital_recovery_factor(DISCOUNT_RATE, float(ec.lifetime_years))

    # grid: the HH locational tariff, split out to be charged on Triad demand
    tnuos_hh = float((meta.get("network_charges") or {}).get("tnuos_locational_GBP_per_MW_year", 0.0))

    # grid connection capital
    from optimisation import connection_cost
    conn = connection_cost.connection_costs(sites.get(site).carbon_api_region,
                                            bool(meta.get("transmission_connected", False)),
                                            cost_case,
                                            connection_voltage=meta.get("connection_voltage"),
                                            route_km=(meta.get("connection_site") or {}).get("route_km"))

    # tank
    tank_row = h2s.traced(next(r for r in h2s.decompose() if r["design"] == tank_design))
    tk = hc.tank_costs()
    tkc = tk[tk.case == cost_case].iloc[0]

    # fuel cell
    d = fc.decompose()
    if ("bop_container_kgco2e_per_MW" not in d
            or "stack_kgco2e_per_MW_gramc_2025" not in d):  # a cache from before the split
        d = fc.decompose(refresh=True)
    fc_bop_years = float(fc_bop_calendar_years or d["bop_calendar_lifetime_years"])
    fc_stack_years = float(fc_stack_calendar_years or d["stack_calendar_lifetime_years"])
    fc_kw_box = float(fc_kw_per_container or d["bop_kw_per_container"])
    gwp_fc_bop = T.step("fuel_cell.bop_per_MW_charged",
                        (d["bop_kgco2e_per_MW"] - d["bop_container_kgco2e_per_MW"]
                         + d["bop_container_kgco2e_per_MW"] * d["bop_kw_per_container"] / fc_kw_box),
                        "kg CO2e per MW", "Balance of plant per MW, its container rescaled to "
                        f"{fc_kw_box:g} kW per container",
                        uses=["fuel_cell.bop_per_MW", "fuel_cell.bop_container_per_MW"],
                        inputs={"kW_per_container": fc_kw_box}, grade="assumed")
    fcc = hc.fuel_cell_costs(bop_calendar_years=fc_bop_years)
    fcr = fcc[fcc.case == cost_case].iloc[0]

    # bought hydrogen — one stream per colour bought, priced independently
    def resolve_bought(colour: str | None, variant: str | None):
        """(GBP/kg, kgCO2e/kg, variant label) for one purchased colour.

        Both figures are delivered to the buyer's tank, not plant-gate: the
        seller's trailer compression is added to each, since ``dc_model`` takes
        ``h2_buy`` into the tank at coefficient 1.0 while self-produced hydrogen
        pays its own compression through ``tank_compression_kwh_per_kg``.
        """
        if not colour:
            return 0.0, 0.0, variant
        compression_gbp = h2_prices.bought_h2_compression_gbp_per_kg(
            colour, cost_case)
        rec = pd.read_csv(OUT_DIR / "h2_prices_recommended.csv")
        row = rec[rec.colour == colour]
        if row.empty:
            raise ValueError(f"Unknown H2 colour {colour!r}. "
                             f"Available: {sorted(rec.colour.unique())}")
        if variant is not None:
            row = row[row.variant == variant]
            if row.empty:
                raise ValueError(
                    f"Unknown variant {variant!r} for colour {colour!r}. "
                    f"Available: {sorted(rec[rec.colour == colour].variant)}")
        grid_variant = h2_prices.GREEN_GRID_DELIVERED_VARIANT
        if len(row) > 1 and grid_variant in list(row.variant):
            # Green is bought as a portfolio, not from one plant: some behind a
            # generator's meter, some over the network. Both are renewable, so
            # the share moves price and delivery burden together and nothing
            # else. Previously an undocumented .iloc[0] took the first row and
            # left the second unreachable.
            share = h2_prices._resolve_grid_share(green_h2_grid_share)
            behind = row[row.variant != grid_variant].iloc[0]
            delivered = row[row.variant == grid_variant].iloc[0]
            return (((1.0 - share) * float(behind[cost_case])
                     + share * float(delivered[cost_case])
                     + compression_gbp),
                    _bought_h2_gwp(behind.activity_code, green_h2_basis,
                                   grid_share=share),
                    f"{1.0 - share:.0%} behind the meter / "
                    f"{share:.0%} grid-connected")
        # One row: either a colour with a single variant, or green pinned to
        # one of its two by an explicit variant.
        one = row.iloc[0]
        return (float(one[cost_case]) + compression_gbp,
                _bought_h2_gwp(one.activity_code, green_h2_basis,
                               grid_share=(1.0 if str(one.variant) == grid_variant
                                           else 0.0)),
                str(one.variant))

    h2_price, h2_gwp, h2_variant = resolve_bought(h2_colour, h2_variant)
    h2_price_2, h2_gwp_2, h2_variant_2 = resolve_bought(h2_colour_2, h2_variant_2)
    if h2_colour and h2_colour_2 == h2_colour:
        raise ValueError(
            f"Both bought-hydrogen streams are {h2_colour!r}. Two streams of "
            "the same colour are the same commodity at the same price, so the "
            "split between them is arbitrary and the result says nothing. Pick "
            "two different colours, or leave the second one unset.")

    # From the electrolyser that actually feeds this tank, not from the tank's
    # pressure alone. h2_storage cannot know which technology was chosen; this
    # is the only place that does.
    compression_kwh = T.step(
        "tank.compression_kwh_per_kg",
        h2s.compression_kwh_per_kg(ely.DELIVERY_PRESSURE_BAR[ely_tech], tank_row["pressure_bar"]),
        "kWh per kg H2", f"Compression from the {ely_tech.split()[0]} electrolyser's "
        f"{ely.DELIVERY_PRESSURE_BAR[ely_tech]:g} bar to the tank's {tank_row['pressure_bar']:g} bar",
        inputs={"from_bar": ely.DELIVERY_PRESSURE_BAR[ely_tech], "to_bar": tank_row["pressure_bar"],
                "real_over_isothermal": h2s.COMPRESSION_REAL_OVER_ISOTHERMAL},
        grade="assumed" if ely_tech in ely.DELIVERY_PRESSURE_ASSUMED else "derived",
        source="h2_storage.compression_kwh_per_kg: isothermal minimum scaled to a real multistage machine")
    # cap_ely is the electrolyser's whole electrical input: dc_model divides it
    # by ely_kwh_per_kg + compression. An electric boiler adds to that input but
    # is not stack, so stack carbon and cost per MW go on the stack's share only.
    # The boiler's own capital is not charged (see SOURCES.md).
    ely_input_kwh = ely_row["kwh_per_kg"] + compression_kwh
    stack_share = T.step("electrolyser.stack_share",
                         (ely_input_kwh - ely_row["heat_kwh_electric_per_kg"]) / ely_input_kwh,
                         "fraction of cap_ely", "Share of the electrolyser's electrical input that is "
                         "stack: cap_ely also carries compression and any electric boiler",
                         uses=[f"electrolyser.{ely_tech.split()[0]}.kwh_per_kg", "tank.compression_kwh_per_kg"],
                         inputs={"heat_kwh_electric_per_kg": ely_row["heat_kwh_electric_per_kg"]})

    dc = data_centre_coefficients()
    # PUE reaches the facility only through demand, which the energy-driven part
    # is charged against. The IT-driven part must not move with it.
    scale_it = size_mw_it / dc["reference_it_mw"]
    if T.active():
        from optimiser_lca import registry as R
        facility = T.activity(R.DATA_CENTRE_DB, R.DATA_CENTRE)
        T.step("data_centre.it_per_year", dc["it_kgco2e_per_year"], "kg CO2e per year",
               "The facility's IT-driven burden (shell, servers, UPS) per year of operation",
               uses=[facility], grade="derived", inputs={"reference_it_MW": dc["reference_it_mw"],
                                                          "operation_years": dc["operation_years"]},
               source="Zhang et al. 2025, split by driver (baseline_grid.decompose_data_centre_by_driver)",
               note="The standby genset is scored and left out: backup is a decision variable here.")
        T.step("data_centre.energy_per_MWh", dc["energy_kgco2e_per_mwh"], "kg CO2e per MWh",
               "The facility's energy-driven burden (water, treatment, refrigerant) per MWh delivered",
               uses=[facility], grade="derived")
    eb = f"electrolyser.{ely_tech.split()[0]}"
    b1 = [f"bought_h2.{h2_colour}.delivered"] if h2_colour else []
    b2 = [f"bought_h2.{h2_colour_2}.delivered"] if h2_colour_2 else []

    def step(field, value, unit, title, uses=(), **kw):
        """Record one LP coefficient (``optimisation.trace``) as ``coefficient.<field>``."""
        return T.step(f"coefficient.{field}", value, unit, title, uses=uses, depth=1, **kw)

    tech = dc_model.Tech(
        gwp_wind=step("gwp_wind", gen_gwp("onshore_wind"), "kg CO2e per MW per year",
                      "Onshore wind, per MW built", ["onshore_wind.annual_per_MW"]),
        gwp_offshore=step("gwp_offshore", gen_gwp("offshore_wind"), "kg CO2e per MW per year",
                          "Offshore wind, per MW built", ["offshore_wind.annual_per_MW"]),
        gwp_solar=step("gwp_solar", gen_gwp("solar_pv"), "kg CO2e per MWp per year",
                       "Solar PV, per MWp built", ["solar_pv.annual_per_MW"]),
        gwp_batt_p=step("gwp_batt_p", be["power_kgco2e_per_kW"] * 1000.0 / batt.ASSET_LIFE_YEARS,
                        "kg CO2e per MW per year", "Battery power conversion, per MW, over the battery's life",
                        ["battery.pcs_per_kW"], inputs={"asset_life_years": batt.ASSET_LIFE_YEARS}),
        gwp_batt_e=step("gwp_batt_e", be["energy_kgco2e_per_kWh"] * 1000.0 / batt.ASSET_LIFE_YEARS,
                        "kg CO2e per MWh per year", "Battery cells, racks and container, per usable MWh, "
                        "over the battery's life", ["battery.energy_per_usable_kWh"],
                        inputs={"asset_life_years": batt.ASSET_LIFE_YEARS}),
        # The balance of plant once over the plant's life; the stacks by replacement
        # (gwp_ely_stack_per_mw x ely_stack_units, dc_model). At the calendar floor the
        # two add back to the whole unit over 25 years, as charged before 26 Oct 2026.
        gwp_ely=step("gwp_ely", ely_row["plant_kgco2e_per_MW"] / ely.PLANT_LIFETIME_YEARS * stack_share,
                     "kg CO2e per MW per year", f"{ely_tech.split()[0]} electrolyser balance of plant, "
                     "per MW of cap_ely, over the plant's life",
                     [f"{eb}.plant_per_MW", "electrolyser.stack_share"],
                     inputs={"plant_lifetime_years": ely.PLANT_LIFETIME_YEARS}),
        gwp_ely_stack_per_mw=step("gwp_ely_stack_per_mw", ely_row["stack_kgco2e_per_MW"] * stack_share,
                                  "kg CO2e per MW replaced", f"One {ely_tech.split()[0]} stack per MW "
                                  "of cap_ely, charged per replacement (max of calendar and duty)",
                                  [f"{eb}.stack_per_MW", "electrolyser.stack_share"],
                                  inputs={"calendar_years": ely.STACK_CALENDAR_YEARS,
                                          "duty_hours": ely.STACK_DUTY_HOURS}),
        ely_stack_calendar_years=ely.STACK_CALENDAR_YEARS,
        ely_stack_duty_hours=ely.STACK_DUTY_HOURS,
        gwp_tank=step("gwp_tank", tank_row["kgco2e_per_kg_capacity_year"], "kg CO2e per kg of capacity per year",
                      f"Hydrogen tank ({tank_design}), per kg it holds",
                      [f"tank.{tank_design}.per_kg_capacity_year"]),
        gwp_fc_bop_per_mw=step("gwp_fc_bop_per_mw", gwp_fc_bop, "kg CO2e per MW replaced",
                               "Fuel cell balance of plant, per MW, charged per replacement "
                               "(max of calendar and duty)", ["fuel_cell.bop_per_MW_charged"],
                               inputs={"calendar_years": fc_bop_years,
                                       "duty_hours": d["bop_duty_lifetime_hours"]}),
        gwp_fc_stack_per_mw=step("gwp_fc_stack_per_mw", fc.stack_kgco2e_per_mw(d, fc_stack_basis),
                                 "kg CO2e per MW replaced", "Fuel cell stack, per MW, charged per "
                                 "replacement (max of calendar and duty)", ["fuel_cell.stack_per_MW"],
                                 inputs={"calendar_years": fc_stack_years,
                                         "duty_hours": d["stack_lifetime_hours"]}),
        gwp_fc_maint_per_mwh=step("gwp_fc_maint_per_mwh", d["maintenance_kgco2e_per_MWh"], "kg CO2e per MWh",
                                  "Fuel cell service, per MWh delivered", ["fuel_cell.maintenance_per_MWh"]),
        gwp_grid_per_mw=step("gwp_grid_per_mw", gc.kgco2e_per_mw_year(), "kg CO2e per MW per year",
                             "Grid connection, per MW of cap_grid", ["grid_connection.per_MW_year"]),
        # The step-up between generator terminals and the site collection
        # network — 690 V (LOW) up to medium voltage, which is where the data
        # centre draws. Wind is the real per-turbine units from Leng's bill of
        # materials, solar IEA PVPS T12-33:2026's inverter-station units, both
        # built as foreground activities by optimiser_lca, and each amortised
        # over its generator's life. See transformers.py.
        gwp_tx_wind_per_mw=step("gwp_tx_wind_per_mw", tx.kgco2e_per_mw_year(
            "onshore_wind", life_years=float(emb.loc["onshore_wind"].study_lifetime_years)),
            "kg CO2e per MW per year", "Wind step-up transformers, per MW of wind",
            ["tx.onshore_wind.per_MW_year", "onshore_wind.lifetime_years"]),
        gwp_tx_solar_per_mwp=step("gwp_tx_solar_per_mwp", tx.kgco2e_per_mw_year(
            "solar_pv", life_years=float(emb.loc["solar_pv"].study_lifetime_years)),
            "kg CO2e per MWp per year", "Solar step-up transformers, per MWp of solar",
            ["tx.solar_pv.per_MW_year", "solar_pv.lifetime_years"]),
        # The battery's and fuel cell's containerised LV → 20 kV step-ups
        # (Jasper 2026's unit on the IEA PVPS composition), each over the
        # asset's own life: the battery's 15 y, the fuel cell's BoP calendar
        # life — so a swept BoP life carries its transformer with it.
        gwp_tx_batt_per_mw=step("gwp_tx_batt_per_mw",
                                tx.kgco2e_per_mw_year("battery", life_years=float(batt.ASSET_LIFE_YEARS)),
                                "kg CO2e per MW per year", "Battery step-up transformers, per MW of PCS",
                                ["tx.battery.per_MW_year"]),
        gwp_tx_fc_per_mw=step("gwp_tx_fc_per_mw",
                              tx.kgco2e_per_mw_year("fuel_cell", life_years=float(fc_bop_years)),
                              "kg CO2e per MW per year", "Fuel-cell step-up transformers, per MW of fuel cell",
                              ["tx.fuel_cell.per_MW_year", "fuel_cell.bop_calendar_years"]),
        fc_bop_calendar_years=fc_bop_years,
        fc_bop_duty_hours=d["bop_duty_lifetime_hours"],
        fc_stack_calendar_years=fc_stack_years,
        fc_stack_duty_hours=d["stack_lifetime_hours"],
        cost_wind=gen_cost("onshore_wind"), cost_offshore=gen_cost("offshore_wind"),
        cost_solar=gen_cost("solar_pv"),
        cost_batt_p=bc["power_GBP_per_kW"] * 1000.0 * annuity_b,
        cost_batt_e=bc["energy_GBP_per_kWh"] * 1000.0 * annuity_b,
        cost_ely=(float(ec.capex_GBP_per_kWe) * 1000.0 * (crf_e + float(ec.fixed_opex_frac))
                  * stack_share),
        # NESO's variable opex: stack replacement and water, per kg made
        cost_ely_variable_per_kg=float(ec.variable_opex_GBP_per_kg),
        cost_tank=float(tkc.annual_GBP_per_kg_year),
        cost_fc=float(fcr.annual_GBP_per_MW_year),
        cost_fc_stack_per_mw=float(fcr.stack_GBP_per_MW),
        cost_fc_bop_per_mw=float(fcr.bop_GBP_per_MW),
        # Use of system (network_charges) plus the connection's own capital
        # (connection_cost), the same per-MW / fixed split as the carbon side.
        # The HH locational TNUoS tariff comes out of the per-MW charge and is
        # charged on Triad demand instead (cost_grid_triad_per_mw_year).
        cost_grid_per_mw_year=(meta["capacity_GBP_per_MW_year"] - tnuos_hh
                               + conn["per_MW_year_GBP"]),
        cost_grid_triad_per_mw_year=tnuos_hh,
        cost_grid_fixed_per_year=meta["fixed_GBP_per_year"] + conn["fixed_per_year_GBP"],
        ely_kwh_per_kg=step("ely_kwh_per_kg", ely_row["kwh_per_kg"], "kWh per kg H2",
                            "Electrolyser electricity per kg made", [f"{eb}.kwh_per_kg"]),
        ely_variable_gwp_per_kg=step("ely_variable_gwp_per_kg", ely_row["variable_kgco2e_per_kg"],
                                     "kg CO2e per kg H2", "Electrolyser consumables per kg made",
                                     [f"{eb}.variable_per_kg"]),
        tank_compression_kwh_per_kg=step("tank_compression_kwh_per_kg", compression_kwh, "kWh per kg H2",
                                         "Compression into the tank, per kg", ["tank.compression_kwh_per_kg"]),
        tank_leakage_per_hour=step("tank_leakage_per_hour", tank_row["leakage_frac_per_hour"],
                                   "fraction of stock per hour", "Tank standing loss",
                                   [f"tank.{tank_design}.leakage_per_hour"]),
        batt_rte=batt.ROUND_TRIP_EFFICIENCY,
        batt_leakage_per_hour=batt.STANDING_LOSS_PER_HOUR,
        fc_kg_h2_per_mwh=d["h2_kg_per_MWh"],
        bought_h2_gbp_per_kg=h2_price,
        bought_h2_gwp_per_kg=step("bought_h2_gwp_per_kg", h2_gwp, "kg CO2e per kg H2",
                                  f"Bought hydrogen ({h2_colour or 'none'}), delivered to the tank", b1),
        bought_h2_2_gbp_per_kg=h2_price_2,
        bought_h2_2_gwp_per_kg=step("bought_h2_2_gwp_per_kg", h2_gwp_2, "kg CO2e per kg H2",
                                    f"Second bought colour ({h2_colour_2 or 'none'}), delivered to the tank", b2),
        dc_fixed_gwp_per_year=step("dc_fixed_gwp_per_year", dc["it_kgco2e_per_year"] * scale_it,
                                   "kg CO2e per year", f"The facility's IT-driven burden at {size_mw_it:g} MW IT",
                                   ["data_centre.it_per_year"], inputs={"scale_it": scale_it}),
        dc_other_gwp_per_mwh=step("dc_other_gwp_per_mwh", dc["energy_kgco2e_per_mwh"], "kg CO2e per MWh",
                                  "The facility's energy-driven burden, per MWh of demand",
                                  ["data_centre.energy_per_MWh"]),
        horizon_years=horizon_years,
        labels={"site": getattr(site, "key", site), "ely_tech": ely_tech, "tank_design": tank_design,
                "soec_heat": ely_row["heat_source"],
                "h2_colour": h2_colour, "cost_case": cost_case, "solar_basis": solar_basis,
                "h2_variant": h2_variant, "green_h2_basis": green_h2_basis,
                "h2_colour_2": h2_colour_2, "h2_variant_2": h2_variant_2,
                "fc_stack_calendar_years": fc_stack_years,
                "fc_bop_calendar_years": fc_bop_years,
                "fc_kw_per_container": fc_kw_box,
                "batt_usable_fraction": (batt.USABLE_FRACTION if batt_usable_fraction is None
                                         else float(batt_usable_fraction)),
                "wind_life_extension": wind_life_extension or ren.WIND_LIFE_EXTENSION,
                "fc_stack_basis": fc_stack_basis or fc.STACK_BASIS,
                "batt_cell_basis": batt_cell_basis or batt.CELL_BASIS,
                "green_h2_grid_share": (
                    h2_prices._resolve_grid_share(green_h2_grid_share)
                    if "green" in (h2_colour, h2_colour_2) else None)},
    )
    # Transformer conversion losses, on the units the capital terms above
    # already charge. Offshore shares wind's: it is the same turbine step-up.
    from dataclasses import replace as _replace
    from optimisation import conversion_losses as cl
    lw, ls, lg = cl.stepup("onshore_wind"), cl.stepup("solar_pv"), cl.grid_intake()
    lb = cl.container_stepup("battery", x_eff=batt_tx_x_eff)
    lfc = cl.container_stepup("fuel_cell", x_eff=fc_tx_x_eff, energised=fc_tx_energised)
    tech = _replace(tech,
                    loss_wind_noload=lw["noload_mw_per_mw"],
                    loss_wind_load_at_full=lw["load_loss_per_mw_at_full_loading"],
                    loss_solar_noload=ls["noload_mw_per_mw"],
                    loss_solar_load_at_full=ls["load_loss_per_mw_at_full_loading"],
                    loss_grid_noload=lg["noload_mw_per_mw"],
                    loss_grid_load=lg["load_loss_fraction"],
                    loss_batt_noload=lb["noload_mw_per_mw"],
                    loss_batt_load=lb["load_loss_fraction"],
                    loss_fc_noload=lfc["noload_mw_per_mw"],
                    loss_fc_load=lfc["load_loss_fraction"],
                    labels={**tech.labels, "batt_tx_x_eff": lb["x_eff"],
                            "fc_tx_x_eff": lfc["x_eff"], "fc_tx_energised": lfc["energised"]})
    tech = with_storage_losses(
        tech, batt_standing_loss_per_hour=batt_standing_loss_per_hour,
        tank_leakage_per_hour=tank_leakage_per_hour)
    return with_cutoff(tech, cutoff)


# Which coefficient each technology's cut-off estimates land on: the per-year
# term the LP charges per unit of the asset, as CUTOFF_RULE_PLAN.md's
# denominator table has it. Battery flows split by side.
CUTOFF_FIELD = {
    ("wind", None): "gwp_tx_wind_per_mw", ("solar", None): "gwp_tx_solar_per_mwp",
    ("battery", "power"): "gwp_tx_batt_per_mw", ("battery", "energy"): "gwp_batt_e",
    ("electrolyser", None): "gwp_ely", ("hydrogen tank", None): "gwp_tank",
    ("fuel cell", None): "gwp_tx_fc_per_mw", ("grid connection", None): "gwp_grid_per_mw",
    ("facility", None): "dc_fixed_gwp_per_year",
}
CUTOFF_MODES = (None, "central", "upper", "none")


def with_cutoff(tech: dc_model.Tech, mode: str | None = None) -> dc_model.Tech:
    """``tech`` with the cut-off register's estimates added onto its coefficients.

    None or "central": every ``included_estimate`` entry at its central estimate.
    "upper": those, plus every still-excluded ``cutoff`` entry at its upper
    estimate (rule 3). "none": nothing added. The additions are recorded in
    ``labels["cutoff"]`` and ``labels["cutoff_added"]`` (kg per coefficient).
    """
    from dataclasses import replace
    from optimiser_lca import exclusions as X
    if mode not in CUTOFF_MODES:
        raise ValueError(f"cutoff must be one of {CUTOFF_MODES}, got {mode!r}")
    added: dict[str, float] = {}
    if mode != "none":
        for e in X.REGISTER:
            if e.kind == "boundary":
                continue
            if e.status == "included_estimate":            # a failed cut-off, or a sourced figure carried whole
                est = e.estimate("central")
            elif e.kind == "cutoff" and e.status == "excluded" and mode == "upper":
                est = e.estimate("upper")
            else:
                continue
            if est is None:
                continue
            field = CUTOFF_FIELD[(e.technology, e.side)]
            added[field] = added.get(field, 0.0) + float(est)
    if T.active():
        for f, v in added.items():
            flows = [e.flow for e in X.REGISTER if e.kind != "boundary"
                     and CUTOFF_FIELD.get((e.technology, e.side)) == f
                     and (e.status == "included_estimate"
                          or (mode == "upper" and e.kind == "cutoff" and e.status == "excluded"))]
            T.step(f"cutoff.{f}", v, "same unit as the coefficient",
                   f"Cut-off register estimates carried on {f}", grade="assumed",
                   inputs={"mode": mode or "central", "flows": "; ".join(flows)},
                   source="optimiser_lca/exclusions.py",
                   note="Unsourced flows that failed the 1 % test, carried at their central "
                        "estimate until a source replaces them (CUTOFF_RULE_PLAN.md).")
    new = {f: getattr(tech, f) + v for f, v in added.items()}
    return replace(tech, **new,
                   labels={**(tech.labels or {}), "cutoff": mode or "central",
                           "cutoff_added": {k: round(v, 6) for k, v in added.items()}})


# Ceiling on a storage standing loss, per hour. A loss term is a small leak on
# a store that otherwise holds; at 1 %/h (24 %/day) a store loses over 60 % of
# its contents in four days and is no longer the technology being modelled. It
# also keeps dc_model's keep factor, 1 - loss x dt, far from zero at any step
# length the study uses. ASSUMED as a sanity bound, not a physical limit.
MAX_STANDING_LOSS_PER_HOUR = 0.01


def with_storage_losses(tech: dc_model.Tech, *,
                        batt_standing_loss_per_hour: float | None = None,
                        tank_leakage_per_hour: float | None = None) -> dc_model.Tech:
    """``tech`` with either storage standing loss overridden; None keeps it.

    The seam ``build_tech`` returns through, split out so the override can be
    checked on a hand-built ``Tech`` without the caches and Brightway that
    ``build_tech`` reads. Both values used — defaults included — are written
    into ``labels``, so every result says which point of the band it was
    solved at.
    """
    from dataclasses import replace
    b = _standing_loss(batt_standing_loss_per_hour, "batt_standing_loss_per_hour")
    t = _standing_loss(tank_leakage_per_hour, "tank_leakage_per_hour")
    b = tech.batt_leakage_per_hour if b is None else b
    t = tech.tank_leakage_per_hour if t is None else t
    return replace(tech, batt_leakage_per_hour=b, tank_leakage_per_hour=t,
                   labels={**(tech.labels or {}),
                           "batt_standing_loss_per_hour": b,
                           "tank_leakage_per_hour": t})


def _standing_loss(value: float | None, name: str) -> float | None:
    """Check one storage-loss override. None passes through as "the default"."""
    if value is None:
        return None
    v = float(value)
    if not np.isfinite(v) or v < 0.0:
        raise ValueError(f"{name} must be a non-negative fraction per hour, "
                         f"got {value!r}")
    if v >= MAX_STANDING_LOSS_PER_HOUR:
        raise ValueError(
            f"{name}={v!r} per hour is {v * 24:.0%} per day — not a standing "
            f"loss. It must be below {MAX_STANDING_LOSS_PER_HOUR} per hour; a "
            f"%/day figure converts as pct / 100 / 24.")
    return v


_H2_GWP_CACHE = OUT_DIR / "bought_h2_gwp_cache.json"


def _bought_h2_gwp(activity_code: str, green_basis: str | None = None, *,
                   grid_share: float | None = None) -> float:
    """kg CO2e per kg of purchased hydrogen, delivered to the buyer's tank.

    Two terms.

    **Production**, at the seller's gate. Green is assembled rather than scored
    whole: its activity links 54 kWh/kg to ecoinvent's GB grid market, which is
    the wrong electricity for a commodity defined by being made from renewables
    — see ``h2_prices.GREEN_H2_ELECTRICITY_BASES``. Every other colour is scored
    whole, because a fossil producer really is on the grid its activity links to.

    **Compression** onto the road trailer that brings it here. Self-produced
    hydrogen pays a compression parasitic to enter the tank and bought hydrogen
    paid none, which favoured buying; see
    ``h2_prices.bought_h2_compression_kgco2e_per_kg``. Added outside the cache
    below, because for green it depends on the electricity basis and the grid
    share while the cached production score does not.
    """
    from optimisation import h2_prices

    colour = next((c for c, v in h2_prices.INVENTORY.items()
                   if v["code"] == activity_code), None)
    if colour is None:
        raise ValueError(
            f"No H2 colour maps to activity {activity_code!r}. "
            f"h2_prices.INVENTORY holds {sorted(h2_prices.INVENTORY)}; a new "
            f"colour must be added there so its compression can be charged.")
    compression = h2_prices.bought_h2_compression_kgco2e_per_kg(
        colour, green_basis, grid_share=grid_share)

    if colour == "green":
        return T.step("bought_h2.green.delivered",
                      (h2_prices.green_h2_gwp_per_kg(green_basis, grid_share=grid_share)
                       + compression),
                      "kg CO2e per kg H2", "Bought green hydrogen, delivered: production plus "
                      "trailer compression", uses=["bought_h2.green.production", "bought_h2.green.compression"])

    # Keyed on the inventories that move a fossil score. Until 14 Oct the
    # cache had no fingerprint and outlived two rewrites of the hydrogen
    # foreground, still holding the dead 17.0 green value (audit §3.6).
    import hashlib
    fp = hashlib.sha256(b"".join(
        (ROOT / "optimiser_lca" / f).read_bytes()
        for f in ("hydrogen.py", "gb_grid.py", "grid.py"))).hexdigest()[:12]
    cache = {}
    if _H2_GWP_CACHE.exists():
        try:
            cache = json.loads(_H2_GWP_CACHE.read_text(encoding="utf-8"))
        except Exception:
            pass
    if cache.get("_fingerprint") != fp:
        cache = {"_fingerprint": fp}
    from optimiser_lca.registry import HYDROGEN_DB as _HDB
    ref = T.activity(_HDB, activity_code)
    if activity_code in cache:
        T.step(f"bought_h2.{colour}.production", cache[activity_code], "kg CO2e per kg H2",
               f"Bought {colour} hydrogen at the seller's gate: its activity scored whole",
               uses=[ref], scores=ref, grade="derived")
        return T.step(f"bought_h2.{colour}.delivered", cache[activity_code] + compression,
                      "kg CO2e per kg H2", f"Bought {colour} hydrogen, delivered",
                      uses=[f"bought_h2.{colour}.production", f"bought_h2.{colour}.compression"])
    import bw2data as bd
    import lca_helpers as H
    from optimisation import baseline_grid as bg
    from optimiser_lca.registry import HYDROGEN_DB
    H.setup_brightway()
    act = bd.get_activity((HYDROGEN_DB, activity_code))
    score = H.run_lca_score(act, bg.gwp_method())
    cache[activity_code] = score
    OUT_DIR.mkdir(exist_ok=True)
    _H2_GWP_CACHE.write_text(json.dumps(cache, indent=2), encoding="utf-8")
    T.step(f"bought_h2.{colour}.production", score, "kg CO2e per kg H2",
           f"Bought {colour} hydrogen at the seller's gate: its activity scored whole",
           uses=[ref], scores=ref, grade="derived")
    return T.step(f"bought_h2.{colour}.delivered", score + compression, "kg CO2e per kg H2",
                  f"Bought {colour} hydrogen, delivered",
                  uses=[f"bought_h2.{colour}.production", f"bought_h2.{colour}.compression"])


if __name__ == "__main__":
    dc = data_centre_coefficients()
    print("Data centre facility, from its own foreground:")
    print(f"  reference facility    {dc['reference_facility_mw']:.3f} MW continuous "
          f"at PUE {dc['reference_pue']:.2f}")
    print(f"  reference IT load     {dc['reference_it_mw']:.3f} MW")
    print(f"  IT-driven burden      {dc['it_kgco2e_per_year'] / 1000:,.0f} t CO2e/yr "
          f"({dc['it_kgco2e_per_mw_it_year'] / 1000:,.1f} t per MW IT)")
    print(f"  energy-driven burden  {dc['energy_kgco2e_per_mwh']:.3f} kg CO2e/MWh")
    print(f"  charged at reference  {dc['charged_kgco2e_per_year_at_reference'] / 1000:,.0f} t CO2e/yr")
    print(f"  standby genset        {dc['backup_kgco2e_per_year_excluded'] / 1000:,.0f} t CO2e/yr "
          f"EXCLUDED — backup is a decision variable here")
    print(f"  lifetime electricity  {dc['electricity_kwh_over_life'] / 1e9:.2f} TWh "
          f"over {dc['operation_years']:.0f} y")
