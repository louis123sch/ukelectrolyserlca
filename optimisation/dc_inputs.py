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
from optimisation import h2_leakage as h2_leak
from optimisation import price_base as P
from optimisation import trace as T

# CEPA for DESNZ (2025), Table E.1: hydrogen electrolyser 10.10 % pre-tax real.
# Was an unsourced 6 % until 4 Nov 2026 (evening).
DISCOUNT_RATE = 0.101
ELECTROLYSER_BUILD_YEARS = 3    # BEIS Hydrogen Production Costs 2021 annex: construction period 3 years


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



# The unusual-year warning (9 Nov 2026). The reference is the 2025 run year's
# wholesale mean (Elexon market index, 1 Jan - 29 Dec 2025, as on the cost map),
# taken to 2026 pounds; a window more than this share away from it is flagged.
WHOLESALE_REFERENCE_2025_GBP_PER_MWH = 79.82
WHOLESALE_WARN_FRACTION = 0.25


def run_warnings(index: pd.DatetimeIndex, wholesale_2026: np.ndarray) -> list[str]:
    """Plain-language warnings about the window itself, for every run's summary."""
    from optimisation import levies
    from optimisation import network_charges as nc
    out = []
    ref = WHOLESALE_REFERENCE_2025_GBP_PER_MWH * P.FACTOR_2025_TO_2026
    mean = float(np.mean(wholesale_2026))
    gap = mean / ref - 1.0
    if abs(gap) > WHOLESALE_WARN_FRACTION:
        years = sorted({int(y) for y in index.year})
        span = f"{years[0]}" if len(years) == 1 else f"{years[0]}-{years[-1]}"
        out.append(
            f"Unusual price year: wholesale electricity in {span} averages £{mean:,.0f}/MWh in 2026 pounds, "
            f"{abs(gap):.0%} {'above' if gap > 0 else 'below'} 2025's £{ref:,.0f}. Prices are only inflated, not "
            f"adjusted, so this run {'favours on-site supply and storage' if gap > 0 else 'favours the grid'} "
            "more than an ordinary year would.")
    if not (np.asarray(levies.cm_window(index)).any() or np.asarray(nc.triad_window(index)).any()):
        out.append(
            "No winter evenings in this window: the Capacity Market levy and the national winter-peak charge "
            "fall only on weekday evenings from November to February, so this run never pays them and "
            "undervalues anything that cuts winter-evening imports (batteries, fuel cells).")
    return out


def build_series(site, start: str, end: str, size_mw_it: float,
                 pue: float | None = None, token: str | None = None,
                 connection_headroom: float | None = None,
                 auto_build: bool = True, on_progress=None,
                 wind_net_factor: float | None = None,
                 solar_ageing_factor: float | None = None,
                 ccl_under_cca: bool | None = None,
                 shortfall_route: str = "upgrade",
                 connection_mode: str | None = None,
                 grid: bool = True,
                 network_charges_scale: float | None = None) -> dc_model.Series:
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

    ``solar_ageing_factor`` scales ninja's year-one solar output to its mean over
    the panel's life; defaults to ``profiles.SOLAR_LIFE_AVERAGE_FACTOR`` (0.870,
    0.7 %/yr over 38 years). Pass 1.0 to reproduce runs before 20 Nov 2026.

    ``ccl_under_cca`` says whether the site holds a Climate Change Agreement
    (92 % off the CCL); defaults to ``levies.CCL_UNDER_CCA``.

    ``connection_mode`` (COST_PLAN §1.11, since 30 Oct 2026) is how the grid
    connection's price list is chosen: ``"room"`` (the default) and ``"cap"``
    list every price list the site could be on — tier, voltage, charging band,
    substation — and let the LP choose among them with the connection size,
    each option capped by the published room at its substation (room) or by
    the 1.43x ceiling or the site's connection limit (cap); ``"single"`` fixes
    one price list from the ceiling before solving, the model as it stood
    before. See ``connection_options``. A site with ``connection_limit_mw``
    set is in the cap mode with that cap. The series then carries one import
    price and carbon series per voltage group (``Series.grid_groups``), and
    ``meta["connection_options"]`` the table ``build_tech`` turns into
    ``Tech.connection_options``. When no price list survives — nothing within
    reach has room — it raises ``connection_options.ConnectionUnavailable``
    rather than inventing a connection; ``grid=False`` (an islanded
    architecture) skips the options altogether.

    ``network_charges_scale`` multiplies the yearly network charges for a sweep
    (``optimisation/sensitivity.py``; the supervisor's +/-50 % test of 4 Nov
    2026): the per-MW charges (national locational and local capacity), the
    fixed charges (national residual and local fixed) and the local network's
    per-MWh unit rates inside the import price. The balancing charge, losses
    and levies are not scaled. It sits here, not in ``build_tech``, because the
    per-MWh part is in the series; the meta then carries every scaled figure,
    so ``build_tech`` cannot apply half of it. None keeps the published charges.
    """
    from optimisation import connection_options as CO
    from optimisation import network_charges as nc
    from optimisation import profiles
    import dc_config as cfg

    mode_requested = CO.DEFAULT_MODE if connection_mode is None else str(connection_mode)
    if mode_requested not in CO.MODES:
        raise ValueError(f"connection_mode must be one of {CO.MODES}, got {connection_mode!r}")
    mode = mode_requested
    ncs = 1.0 if network_charges_scale is None else float(network_charges_scale)
    if not (np.isfinite(ncs) and ncs >= 0.0):
        raise ValueError(f"network_charges_scale must be a non-negative number, got {network_charges_scale!r}")

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
    # The window's wholesale prices in 2026 pounds (price_base, 9 Nov 2026): each
    # step by its own year's factor. Plain inflation, nothing else: an unusual
    # year stays unusual, and the warning below says so.
    wholesale_raw = df["price_GBP_per_MWh"].to_numpy(dtype=float)
    _f = {int(y): P.factor_to_2026(int(y)) for y in np.unique(index.year)}
    df = df.copy()
    df["price_GBP_per_MWh"] = wholesale_raw * np.array([_f[int(y)] for y in index.year])
    warnings = run_warnings(index, df["price_GBP_per_MWh"].to_numpy())
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
        if mode == "room":          # decided 30 Oct 2026: a connection limit is the cap mode with that cap
            mode = "cap"
    transmission, tier_note = nc.is_transmission_connected(
        conn_mw, site.carbon_api_region, site.transmission_connected)
    tdr_band, tdr_note = site.tdr_band, ""
    if tdr_band is None:
        tdr_band, tdr_note = nc.tdr_band_for(
            conn_mw, annual_mwh, region=site.carbon_api_region,
            transmission_connected=transmission, site=(site.lat, site.lon))
    # The tier and band are read from the ceiling, so the connection the LP
    # builds is held inside that band: floor <= cap_grid <= ceiling. Otherwise a
    # site charged as EHV4 or T-Demand4 could build a connection that belongs to
    # a cheaper band (CONNECTION_TIER_PLAN.md step 2).
    conn_floor = min(nc.band_floor_mw(transmission, tdr_band, site.carbon_api_region),
                     conn_mw)
    # The voltage: the area's published rule as the floor, the area's own
    # substation capacities above it (a 33 kV site with no room in reach
    # connects at 132 kV) — since 29 Oct 2026, with the site's coordinates.
    conn_voltage, voltage_note = nc.connection_voltage_detail(
        conn_mw, site.carbon_api_region, transmission, site=(site.lat, site.lon))
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
    duos_ref = charges["duos_GBP_per_MWh"].to_numpy() * ncs
    price = ((df["price_GBP_per_MWh"].to_numpy() + charges["bsuos_GBP_per_MWh"].to_numpy()) * loss
             + duos_ref
             + lev["levies_GBP_per_MWh"].to_numpy())
    if T.active():
        T.cost("cost.wholesale.mean_per_MWh", float(wholesale_raw.mean()), "GBP per MWh",
               f"Wholesale electricity price, mean over {start} to {end}, in each year's own money",
               grade="transcribed",
               cites=[("elexon_market_index", f"provider APXMIDP, half-hourly, {start} to {end}")],
               note="Real prices for the solved window, not a forecast")
        year_keys = sorted({k for y in _f for k in P.record_to_2026(y)})
        T.cost("cost.wholesale.mean_per_MWh_2026", float(df["price_GBP_per_MWh"].mean()), "GBP per MWh",
               f"Wholesale electricity price, mean over {start} to {end}, in 2026 pounds",
               uses=["cost.wholesale.mean_per_MWh", *year_keys],
               inputs={str(y): f for y, f in _f.items()},
               note="Each half-hour by its own year's factor; plain inflation only")
        _trace_price("cost.import_price.reference", df["price_GBP_per_MWh"].to_numpy(),
                     charges["bsuos_GBP_per_MWh"].to_numpy(), loss, duos_ref,
                     lev["levies_GBP_per_MWh"].to_numpy(), price,
                     f"cost.losses.r{site.carbon_api_region}.{conn_voltage}", charges["components"]["trace"]["duos"],
                     f"The import price on the single price list the load's size gives ({conn_voltage}, {tdr_band})")
    grid_gwp = grid_lca.delivered(df["grid_generation_kgco2e_per_kwh"].to_numpy(), voltage)

    # Every price list the site could be on, and one import series per
    # voltage group (COST_PLAN §1.11). The reference above — the single choice
    # the ceiling would have made — stays in the meta for callers and reports;
    # the LP chooses among the options. One option alone is that option as
    # the single price list: the model is then today's exactly.
    options, dropped, groups, option_note = [], [], None, ""
    if not grid:
        option_note = "islanded run: no grid connection, so no price list"
    elif mode != "single":
        options, dropped = CO.option_table(site, load_mw, annual_mwh, mode=mode, cap_mw=conn_mw)
        if not options:
            raise CO.ConnectionUnavailable(CO.no_room_message(site, load_mw, dropped, mode), dropped)
        else:
            duos_by_key = CO.with_charges(options, index, site)
            wholesale_plus_bsuos = df["price_GBP_per_MWh"].to_numpy() + charges["bsuos_GBP_per_MWh"].to_numpy()
            groups = {}
            for g in sorted({o["group"] for o in options}):
                rep = CO.representative(options, g, load_mw)
                loss_g = levies.loss_series(index, g, site.carbon_api_region).to_numpy()
                duos_g = duos_by_key[rep["key"]].to_numpy() * ncs
                price_g = (wholesale_plus_bsuos * loss_g + duos_g
                           + lev["levies_GBP_per_MWh"].to_numpy())
                if T.active():
                    _trace_price(f"cost.import_price.group.{g}", df["price_GBP_per_MWh"].to_numpy(),
                                 charges["bsuos_GBP_per_MWh"].to_numpy(), loss_g,
                                 duos_g, lev["levies_GBP_per_MWh"].to_numpy(), price_g,
                                 f"cost.losses.r{site.carbon_api_region}.{g}", rep["network_charges"]["trace"]["duos"],
                                 f"The import price every {g} price list pays: unit rates of {rep['key']}")
                gwp_g = grid_lca.delivered(df["grid_generation_kgco2e_per_kwh"].to_numpy(), rep["delivery_voltage"])
                groups[g] = {"price_per_mwh": price_g, "gwp_per_mwh": gwp_g * 1000.0,
                             "representative": rep["key"], "delivery_voltage": rep["delivery_voltage"],
                             "loss_gross_up_mean": float(np.mean(loss_g)),
                             "duos_mean_GBP_per_MWh": float(np.mean(duos_g)),
                             "price_mean_GBP_per_MWh": float(np.mean(price_g)),
                             "gwp_mean_kgco2e_per_kwh": float(np.mean(gwp_g))}
        if len(options) == 1:
            # The one survivor is the price list: fold it into the reference so
            # the model is the single-price-list one on that list.
            o = options[0]
            transmission, tier_note = o["transmission"], f"the one option in the {mode} mode"
            tdr_band, tdr_note = o["band"], tier_note
            conn_voltage, voltage_note = o["voltage"], tier_note
            conn_floor, conn_mw = o["floor_mw"], o["ceiling_mw"]
            conn_note = f"{o['cap_basis']} ({mode} mode)"
            conn_point = {"found": o["point"].get("substation") is not None, "voltage": o["voltage"],
                          "connection_mw": conn_mw, **o["point"],
                          "headroom_status": o["point"].get("headroom_status"),
                          "nearest_headroom_mw": o["point"].get("room_mw")}
            charges["capacity_GBP_per_MW_year"] = o["capacity_GBP_per_MW_year"]
            charges["fixed_GBP_per_year"] = o["fixed_GBP_per_year"]
            charges["components"] = o["network_charges"]
            voltage = o["delivery_voltage"]
            g = groups[o["group"]]
            price, grid_gwp = g["price_per_mwh"], g["gwp_per_mwh"] / 1000.0
            loss = np.full(len(index), g["loss_gross_up_mean"])
    ref_key = CO.reference_key(options, transmission, conn_voltage, tdr_band) if len(options) > 1 else None
    if len(options) > 1:
        # The Series' one price and carbon series are the reference group's,
        # for reports that read a single series (the dispatch frame's price
        # column); the LP charges each group its own.
        ref_group = conn_voltage if conn_voltage in groups else sorted(groups)[0]
        price, grid_gwp = groups[ref_group]["price_per_mwh"], groups[ref_group]["gwp_per_mwh"] / 1000.0
    if T.active():
        _trace_grid(df, grid_gwp, voltage, site, start, end, meta, groups)

    net = profiles.WIND_NET_FACTOR if wind_net_factor is None else float(wind_net_factor)
    if not 0.5 <= net <= 1.0:
        raise ValueError(f"wind_net_factor must be in [0.5, 1.0], got {net!r}")
    solar_age = T.step("solar.life_average_output_factor",
                       profiles.SOLAR_LIFE_AVERAGE_FACTOR if solar_ageing_factor is None else float(solar_ageing_factor),
                       "fraction of year-one output", "Solar output averaged over the panel's life: 1 - d (L - 1) / 2",
                       grade="derived",
                       inputs={"degradation_per_year": profiles.SOLAR_DEGRADATION_PER_YEAR,
                               "life_years": profiles.SOLAR_AGEING_LIFE_YEARS},
                       source="Smith et al. 2024 Table 3, 0.7 %/yr degradation; DESNZ/Arup 2024 38-year life",
                       note="Undiscounted, at the central life for every cost case. Wind is not aged (user, 20 Nov 2026)")
    if not 0.5 <= solar_age <= 1.0:
        raise ValueError(f"solar_ageing_factor must be in [0.5, 1.0], got {solar_age!r}")
    series = dc_model.Series(
        index=index,
        dt_hours=float(meta["slice_hours"]),
        demand_mw=np.full(len(index), size_mw_it * pue),
        cf_wind=df["wind_cf"].to_numpy() * net,
        cf_solar=df["solar_cf"].to_numpy() * solar_age,
        grid_gwp_per_mwh=grid_gwp * 1000.0,
        grid_price_per_mwh=price,
        triad_window=nc.triad_window(index),
        grid_groups=({g: {"price_per_mwh": d["price_per_mwh"], "gwp_per_mwh": d["gwp_per_mwh"]}
                      for g, d in groups.items()} if len(options) > 1 else None),
    )
    meta["warnings"] = warnings
    meta["price_base"] = f"real {P.TARGET_YEAR} pounds"
    meta["wholesale_mean_GBP_per_MWh_2026"] = float(df["price_GBP_per_MWh"].mean())
    meta["ccl_under_cca"] = lev["components"]["ccl_under_cca"]
    meta["network_charges"] = _scaled_network_charges(charges["components"], ncs)
    meta["network_charges_scale"] = ncs
    meta["levies"] = {**lev["components"], "loss_gross_up_mean": float(np.mean(loss)),
                      "connection_voltage": conn_voltage}
    meta["capacity_GBP_per_MW_year"] = charges["capacity_GBP_per_MW_year"] * ncs
    meta["fixed_GBP_per_year"] = charges["fixed_GBP_per_year"] * ncs
    meta["tdr_band"] = tdr_band
    meta["tdr_band_note"] = tdr_note
    # With more than one option the limit and floor the callers hand the LP
    # are the widest of the options' ranges, so they bind nothing: each option
    # carries its own. The chosen option's are in every frontier row.
    meta["connection_limit_mw"] = max(o["ceiling_mw"] for o in options) if len(options) > 1 else conn_mw
    meta["connection_limit_note"] = conn_note
    meta["connection_floor_mw"] = min(o["floor_mw"] for o in options) if len(options) > 1 else conn_floor
    meta["connection_site"] = CO.fixed_route(site, conn_point) if isinstance(conn_point, dict) else conn_point
    meta["connection_mode"] = mode
    meta["connection_mode_requested"] = mode_requested
    pinned = bool(getattr(site, "connection_substation", None))
    meta["connection_chosen_by"] = ("none (islanded)" if not grid else
                                    "user (substation picked), band by the optimiser" if pinned and len(options) > 1 else
                                    "user (substation picked)" if pinned else
                                    "optimiser" if len(options) > 1 else
                                    "rule")
    meta["connection_options"] = [_option_record(o, ncs) for o in options]
    meta["connection_options_dropped"] = [{k: (None if isinstance(v, float) and not np.isfinite(v) else v)
                                           for k, v in d.items()} for d in dropped]
    meta["connection_options_note"] = option_note
    meta["connection_reference"] = {"key": ref_key, "transmission": transmission, "voltage": conn_voltage,
                                    "band": tdr_band, "ceiling_mw": conn_mw, "floor_mw": conn_floor}
    meta["connection_groups"] = ({g: {k: v for k, v in d.items() if k not in ("price_per_mwh", "gwp_per_mwh")}
                                  for g, d in groups.items()} if groups else {})
    # Whether the room figures behind the options are behind what the
    # companies publish (substations.freshness: one metadata call per dataset,
    # cached a day; never a failure). Recorded on every run that read room.
    meta["register_freshness"] = substations.freshness() if (mode == "room" and grid) else None
    meta["connection_headroom"] = (
        connection_headroom if connection_headroom is not None
        else sites.CONNECTION_HEADROOM_ASSUMED)
    meta["transmission_connected"] = transmission
    meta["connection_voltage"] = conn_voltage
    meta["connection_voltage_note"] = voltage_note
    meta["connection_tier_note"] = tier_note
    meta["grid_delivery_voltage"] = voltage
    meta["wind_net_factor"] = net
    meta["mean_wind_cf_net"] = float(np.mean(series.cf_wind))
    meta["solar_ageing_factor"] = float(solar_age)
    meta["mean_solar_cf_aged"] = float(np.mean(series.cf_solar))
    meta["mean_grid_delivered_kgco2e_per_kwh"] = float(grid_gwp.mean())
    meta["site"] = site.key
    meta["site_name"] = site.name
    meta["lat"], meta["lon"] = site.lat, site.lon
    meta["carbon_api_region"] = site.carbon_api_region
    meta["tnuos_zone"] = site.tnuos_zone
    return series, meta


def _trace_price(key, wholesale, bsuos, loss, duos, levies, price, loss_key, duos_key, title):
    """Record one import price series as its four parts, each the window mean of
    what it adds per MWh metered, so the parts add back to the price's mean."""
    parts = {"energy": (wholesale * loss, "Wholesale energy, grossed up for losses",
                        ["cost.wholesale.mean_per_MWh_2026", f"{loss_key}.mean"]),
             "balancing": (bsuos * loss, "Balancing charge, grossed up for losses",
                           ["cost.bsuos.mean_per_MWh", f"{loss_key}.mean"]),
             "local_network": (duos, "Local network unit charges (none on the national grid)",
                               [f"{duos_key}.unit_mean_per_MWh"] if duos_key else []),
             "levies": (levies, "Policy levies on metered imports", ["cost.levy.mean_per_MWh"])}
    for name, (series, what, uses) in parts.items():
        T.cost(f"{key}.{name}", float(np.mean(series)), "GBP per MWh", f"{what}: mean over the window",
               uses=uses, **({} if uses else {"grade": "derived", "note": "Zero: a transmission site pays no "
                                                                         "local network charges"}))
    T.cost(f"{key}.mean", float(np.mean(price)), "GBP per MWh", f"{title}: mean over the window",
           uses=[f"{key}.{n}" for n in parts],
           note="Each half-hour: (wholesale + balancing) x losses + local unit charge + levies. The LP charges "
                "the half-hourly series; the map shows means")


def _scaled_network_charges(components: dict, scale: float) -> dict:
    """The charge breakdown at ``build_series``'s ``network_charges_scale``. The
    balancing charge is not a network charge and stays as it is."""
    if scale == 1.0:
        return components
    keys = ("tnuos_locational_GBP_per_MW_year", "duos_capacity_GBP_per_MW_year", "tnuos_tdr_GBP_per_year",
            "duos_fixed_GBP_per_year", "duos_mean_GBP_per_MWh")
    return {**components, **{k: components[k] * scale for k in keys}}


def _option_record(o: dict, network_charges_scale: float = 1.0) -> dict:
    """One connection option as plain values for the meta (JSON-safe; no series)."""
    p = o["point"]
    return {
        "key": o["key"], "tier": o["tier"], "transmission": bool(o["transmission"]), "voltage": o["voltage"],
        "band": o["band"], "group": o["group"], "floor_mw": float(o["floor_mw"]), "ceiling_mw": float(o["ceiling_mw"]),
        "cap_basis": o["cap_basis"], "mode": o["mode"], "delivery_voltage": o["delivery_voltage"],
        "substation": p.get("substation"), "company": p.get("company"), "level": p.get("level"),
        "straight_km": p.get("straight_km"), "route_km": p.get("route_km"), "which": p.get("which"),
        "room_mw": p.get("room_mw"), "headroom_status": p.get("headroom_status"),
        "headroom_basis": p.get("headroom_basis"), "headroom_as_of": p.get("headroom_as_of"),
        "contracted_mw": p.get("contracted_mw"), "room_net_of_contracted_mw": p.get("room_net_of_contracted_mw"),
        "skipped": list(p.get("skipped") or []), "point_note": p.get("note", ""),
        "capacity_GBP_per_MW_year": o["capacity_GBP_per_MW_year"] * network_charges_scale,
        "fixed_GBP_per_year": o["fixed_GBP_per_year"] * network_charges_scale,
        "network_charges": _scaled_network_charges(o["network_charges"], network_charges_scale),
    }


def _trace_grid(df, grid_gwp, voltage, site, start, end, meta, groups=None):
    """Record how the LP's half-hourly grid carbon is made (``optimisation.trace``).
    The series is shown by its mean over the window; the LP charges it half-hour
    by half-hour. With the price list chosen in the LP (``groups``) each voltage
    group's delivered series is recorded too."""
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
    for g, gd in (groups or {}).items():
        dv = gd["delivery_voltage"]
        if dv != voltage:
            d = grid_lca.delivery(dv)
            chain = [T.ecoinvent(m, "GB") for v, m, _t in grid_lca._CHAIN[:grid_lca.VOLTAGES.index(dv) + 1]]
            T.step(f"grid.delivery.{dv}", d["gross_up"], "kWh generated per kWh delivered",
                   f"Losses down to {dv} voltage, from ecoinvent's GB voltage chain",
                   uses=chain, inputs={"network_gco2e_per_kwh": d["network_gco2e_per_kwh"]}, grade="derived",
                   note="The network's own embodied carbon is added per kWh delivered; "
                        "optimiser_lca.grid.check_delivery re-derives both from the live database.")
        T.step(f"grid.delivered_mean.{g.replace(' ', '')}", gd["gwp_mean_kgco2e_per_kwh"],
               "kg CO2e per kWh delivered, mean of the window",
               f"Grid carbon delivered to a {g} connection ({dv} voltage): the series the LP charges "
               f"imports through that voltage group (COST_PLAN §1.11)",
               uses=["grid.generation_mean", f"grid.delivery.{dv}"], grade="derived",
               note="One import series per voltage group when the LP chooses the price list; the "
                    "reference group's is grid.delivered_mean.")


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
        grid_groups=(None if not series.grid_groups else
                     {g: {k: mean(v) for k, v in d.items()} for g, d in series.grid_groups.items()}),
    )



# The gas price range (9 Nov 2026): the wholesale part of every gas price the
# model pays directly, x this. DESNZ's own 2026 low and high over its central
# (Fossil fuel price assumptions 2025: 52 / 85 / 143 p/therm), about 0.61 and
# 1.68 — a published range, wide and lopsided as gas is. Was +/-25 % (ours) until
# the same evening. The site's levy on top is not scaled.
def _gas_multipliers() -> dict:
    from optimisation import h2_prices
    return {c: h2_prices.gas_case_ratio(c) for c in ("low", "central", "high")}


GAS_PRICE_MULTIPLIER = _gas_multipliers()
GAS_PRICE_DEFAULT = "central"


def site_gas_gbp_per_mwh(ccl_under_cca: bool | None = None, gas_price_case: str | None = None,
                         record: bool = False) -> float:
    """Gas delivered to a large site, GBP per MWh (HHV), in 2026 pounds.

    DESNZ's 2025 price for large users includes the Climate Change Levy at the
    rate in force all through 2025. It comes out; the rest goes to 2026 pounds,
    moves from 2025's gas market to DESNZ's central view of 2026 (85 over 94
    p/therm, real), and takes the gas price case; and the 2026/27 levy goes back
    on, less the agreement discount if the site holds one."""
    from optimisation import electrolysers as ely
    from optimisation import h2_prices
    from optimisation import levies
    case = GAS_PRICE_DEFAULT if gas_price_case is None else str(gas_price_case)
    mult = GAS_PRICE_MULTIPLIER[case]
    to_2026_market = h2_prices.gas_gbp_per_mwh(2026) / h2_prices.gas_gbp_per_mwh(2025)
    levy_2025 = levies.CCL_GAS_2025_GBP_PER_KWH * 1000.0
    levy_now = levies.ccl_gas_gbp_per_mwh(ccl_under_cca)
    value = ((ely.LARGE_SITE_GAS_GBP_PER_MWH - levy_2025) * P.FACTOR_2025_TO_2026 * to_2026_market * mult
             + levy_now)
    if record and T.active():
        _record_gas_base(case, mult, to_2026_market, levy_2025)
        T.cost("cost.levy.CCL_gas", levy_now, "GBP per MWh", "Climate Change Levy on the site's gas, 2026/27",
               uses=["cost.levy.CCL_under_agreement"],
               cites=[("govuk_ccl_rates", f"gas, £{levies.CCL_GAS_GBP_PER_KWH}/kWh from 1 April 2026; "
                                          f"{levies.CCA_GAS_DISCOUNT:.0%} off under an agreement")])
        T.cost("cost.gas_price_per_MWh", value, "GBP per MWh (HHV)",
               "Gas delivered to the site in 2026 pounds: the 2025 price less its levy, inflated and "
               "scaled by the gas case, plus the 2026/27 levy",
               uses=["cost.gas.delivered_2025", "cost.gas.levy_in_2025_price", P.KEY_2025_TO_2026,
                     "cost.gas.market_2026_over_2025", "cost.gas.price_case_multiplier", "cost.levy.CCL_gas"])
    return value


def _record_gas_base(case: str, mult: float, to_2026_market: float, levy_2025: float) -> None:
    """The steps every gas price here shares: DESNZ's 2025 large-site price, its levy, the market move, the case."""
    from optimisation import electrolysers as ely
    T.cost("cost.gas.delivered_2025", ely.LARGE_SITE_GAS_GBP_PER_MWH, "GBP per MWh (HHV)",
           "Gas delivered to a large site, including the levy, 2025", grade="transcribed",
           cites=[("desnz_nondomestic_prices", "table 3.4.2, annual, 2025, gas, large, 4.149 p/kWh")])
    T.cost("cost.gas.levy_in_2025_price", levy_2025, "GBP per MWh",
           "Climate Change Levy on gas in force all through 2025", grade="transcribed",
           cites=[("govuk_ccl_rates", "gas, rates from 1 April 2024 and 1 April 2025: £0.00775/kWh")],
           note="Taken at the full rate: DESNZ's average does not say how many buyers held an agreement")
    T.cost("cost.gas.market_2026_over_2025", to_2026_market, "multiplier",
           "DESNZ's central NBP gas, 2026 over 2025 (real)", grade="derived",
           cites=[("desnz_fossil_fuel_prices_2025", "sheet Gas, case B: 85 p/therm 2026, 94 p/therm 2025")])
    T.cost("cost.gas.price_case_multiplier", mult, "multiplier",
           f"Gas price case: {case}, DESNZ's 2026 case over its central", grade="derived",
           cites=[("desnz_fossil_fuel_prices_2025", "sheet Gas, 2026: A 52, B 85, C 143 p/therm")])


def engine_gas_gbp_per_mwh(gas_price_case: str | None = None, record: bool = False) -> float:
    """Gas for the site's gas engines, GBP per MWh (HHV), in 2026 pounds.

    The site gas price (``site_gas_gbp_per_mwh``) without the Climate Change Levy: gas supplied to a
    generating station of 2 MW or more, auto-generators included, is exempt from the main rates
    and liable to carbon price support instead (HMRC Excise Notice CCL1/6, §4.1, §6), which the
    engines pay inside the carbon price (``build_tech``). Its own function, so the levy-agreement
    switch (``ccl_under_cca``) cannot touch it."""
    from optimisation import electrolysers as ely
    from optimisation import h2_prices
    from optimisation import levies
    case = GAS_PRICE_DEFAULT if gas_price_case is None else str(gas_price_case)
    to_2026_market = h2_prices.gas_gbp_per_mwh(2026) / h2_prices.gas_gbp_per_mwh(2025)
    levy_2025 = levies.CCL_GAS_2025_GBP_PER_KWH * 1000.0
    value = ((ely.LARGE_SITE_GAS_GBP_PER_MWH - levy_2025) * P.FACTOR_2025_TO_2026 * to_2026_market
             * GAS_PRICE_MULTIPLIER[case])
    if record and T.active():
        # only the shared steps: the site's levied price is not the engines', and recording it here
        # would put a levy no term uses on the cost map (and clash with a levy-agreement run's)
        _record_gas_base(case, GAS_PRICE_MULTIPLIER[case], to_2026_market, levy_2025)
        T.cost("cost.gas_engine.gas_per_MWh_HHV", value, "GBP per MWh (HHV)",
               "Gas for the engines in 2026 pounds: the site price without the Climate Change Levy",
               uses=["cost.gas.delivered_2025", "cost.gas.levy_in_2025_price", P.KEY_2025_TO_2026,
                     "cost.gas.market_2026_over_2025", "cost.gas.price_case_multiplier"],
               cites=[("hmrc_ccl16", "§4.1, gas to a generating station of 2 MW or more, auto-generators "
                                     "included: exempt from the main rates, liable to carbon price support")])
    return value


def _bought_gas_adjustment(colour: str, gas_price_case: str, h2_prices) -> tuple[float, list]:
    """GBP per kg (2025 pounds) the gas price case adds to a bought colour built
    from gas at the FES price (grey, turquoise), and the keys it was recorded on.
    Zero for every other colour, and in the central case."""
    mult = GAS_PRICE_MULTIPLIER[gas_price_case]
    inv = h2_prices.INVENTORY.get(colour, {})
    if mult == 1.0 or colour not in ("grey", "turquoise") or not inv.get("gas_m3_per_kg"):
        return 0.0, []
    gas_mwh = inv["gas_m3_per_kg"] * h2_prices.GAS_KWH_HHV_PER_M3 / 1000.0
    adj = gas_mwh * h2_prices.gas_gbp_per_mwh() * (mult - 1.0)
    key = f"cost.bought_h2.{colour}.gas_case_adjustment"
    T.cost(key, adj, "GBP per kg H2", f"Gas price case on the seller's gas ({gas_price_case})", grade="derived",
           inputs={"gas_MWh_per_kg": gas_mwh, "DESNZ_gas_2026_GBP_per_MWh_in_2025_GBP": h2_prices.gas_gbp_per_mwh(),
                   "multiplier": mult},
           cites=[("desnz_fossil_fuel_prices_2025", "sheet Gas, 2026, case B")],
           note="The plant-gate price already carries this gas at the central price; this is the difference")
    return adj, [key]


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
               ely_stack_calendar_years: float | None = None,
               fc_bop_calendar_years: float | None = None,
               fc_kw_per_container: float | None = None,
               batt_usable_fraction: float | None = None,
               wind_life_extension: str | None = None,
               fc_stack_basis: str | None = None,
               batt_cell_basis: str | None = None,
               batt_tx_x_eff: float | None = None,
               fc_tx_x_eff: float | None = None,
               fc_tx_energised: bool | None = None,
               cutoff: str | None = None,
               connection_build_scale: float | None = None,
               cost_cutoff: str | None = None,
               fc_stack_duty_hours: float | None = None,
               generator_connection_out: bool = False,
               tank_insurance_frac: float | None = None,
               batt_max_duration_hours: float | None = None,
               ccl_under_cca: bool | None = None,
               gas_price_case: str | None = None) -> dc_model.Tech:
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
    ``h2_prices.GREEN_H2_GRID_SHARE`` (0.7 since 11 Nov 2026, from the first
    allocation round's projects). It blends the two green rows and their delivery
    burdens, since both are renewable and differ only in how the electricity
    reaches the seller's electrolyser. Both rows carry the same price since
    11 Nov 2026 (the first round's strike price), so it moves carbon only.

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
    ``battery.STANDING_LOSS_PER_HOUR`` (self-discharge) and the tank design's
    ``leakage_frac_per_hour``; DATA_GAPS.md records each one's source and band.
    The two push in opposite directions in the hydrogen-versus-battery seasonal
    contest. A %/day figure converts as ``pct / 100 / 24``.

    ``ely_stack_calendar_years`` overrides the electrolyser stack's calendar
    floor (``electrolysers.STACK_CALENDAR_YEARS``, one stack per plant life since
    19 Nov 2026); ``electrolysers.STACK_CALENDAR_YEARS_THREE_STACKS`` is the
    earlier three-stack rule, kept as a named sensitivity.

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

    ``connection_build_scale`` multiplies the grid connection's one-off build
    cost for a sweep (the annuity on the substation, cable and switchgear from
    ``connection_cost``, per MW and fixed, on every price list). The carbon of
    the connection is not touched. The yearly network charges have their own
    knob, ``build_series(network_charges_scale=)``, which ``labels`` also
    records from the meta. None keeps the published prices.

    ``fc_stack_duty_hours``, ``generator_connection_out`` and
    ``tank_insurance_frac`` exist to sweep (``sensitivity.ASSUMPTION_KNOBS``):
    the stack's life in running hours; wind and solar with
    ``tech_costs.GENERATOR_CONNECTION_SHARE`` of their capital taken out; and a
    yearly fraction of the tank's capital on top of its running cost.
    ``batt_max_duration_hours`` caps the battery's energy on its power, for the
    same sweep; None leaves it free.

    ``ccl_under_cca`` (9 Nov 2026) says whether the site holds a Climate Change
    Agreement; here it takes the gas discount (89 %) off the gas the site buys
    for solid-oxide heat, as ``build_series`` takes the electricity one (92 %)
    off imports. Pass the same value to both. None keeps
    ``levies.CCL_UNDER_CCA``.

    ``gas_price_case`` (9 Nov 2026) is "low", "central" or "high": the wholesale
    part of every gas price the model pays directly x ``GAS_PRICE_MULTIPLIER``
    (DESNZ's 2026 low and high over central, about 0.61 / 1 / 1.68) — the site's gas for solid-oxide heat, and the gas behind
    bought grey and turquoise hydrogen. Bought blue is NESO's own cost with its
    own gas inside, and is not moved. The levy on the site's gas is not moved
    either. None is "central".
    """
    # Validated before anything is loaded, so a bad sweep value fails at once
    # rather than after the caches (and Brightway) have been read.
    _standing_loss(batt_standing_loss_per_hour, "batt_standing_loss_per_hour")
    _standing_loss(tank_leakage_per_hour, "tank_leakage_per_hour")
    for name, v in (("fc_stack_calendar_years", fc_stack_calendar_years),
                    ("ely_stack_calendar_years", ely_stack_calendar_years),
                    ("fc_bop_calendar_years", fc_bop_calendar_years),
                    ("fc_kw_per_container", fc_kw_per_container),
                    ("fc_stack_duty_hours", fc_stack_duty_hours),
                    ("batt_max_duration_hours", batt_max_duration_hours)):
        if v is not None and not (np.isfinite(v) and v > 0):
            raise ValueError(f"{name} must be a positive number, got {v!r}")
    build_scale = 1.0 if connection_build_scale is None else float(connection_build_scale)
    if not (np.isfinite(build_scale) and build_scale >= 0.0):
        raise ValueError(f"connection_build_scale must be a non-negative number, got {connection_build_scale!r}")
    if batt_usable_fraction is not None and not 0.5 <= batt_usable_fraction <= 1.0:
        raise ValueError(f"batt_usable_fraction must be in [0.5, 1.0], "
                         f"got {batt_usable_fraction!r}")
    gas_case = GAS_PRICE_DEFAULT if gas_price_case is None else str(gas_price_case)
    if gas_case not in GAS_PRICE_MULTIPLIER:
        raise ValueError(f"gas_price_case must be one of {tuple(GAS_PRICE_MULTIPLIER)}, got {gas_price_case!r}")

    # Every pound the LP charges is a 2026 pound (price_base). The coefficient
    # modules work in 2025 pounds; their figures take the one factor here.
    # Network charges, levies and connection prices are 2026/27 already.
    to26, k26 = P.to_2026(), [P.KEY_2025_TO_2026]
    from optimisation import levies as levies_mod

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
    def gen_cost(asset):
        c = tc.annual_cost(asset, cost_case)
        out = tc.GENERATOR_CONNECTION_SHARE.get(asset, 0.0) if generator_connection_out else 0.0
        return float(c["total_annual_cost_GBP_per_MW_year"] - out * c["annualised_capex_2025_GBP_per_MW_year"])

    def gen_gwp(asset):
        r = emb.loc[asset]
        # Capital annuity plus, for wind, the non-capital residual
        # ecoinvent reports per kWh - see renewables.apply_case.
        return float(r.annual_kgco2e_per_MW)

    # battery
    bcost = batt.annual_costs(cost_case)
    be = batt.embodied_components(usable_fraction=batt_usable_fraction,
                                  cell_basis=batt_cell_basis)
    # Sized to still hold cap_batt_e in year 15 (12 Nov 2026): energy only, cost and carbon.
    batt_oversize = batt.end_of_life_oversize()
    # Insurance on the electrolyser and tank (12 Nov 2026), at onshore wind's ratio to
    # capital, as the fuel cell and battery carry it. The sweep's tank_insurance_frac
    # (insurance and rates together) replaces the tank's when given.
    _ins_cite = [("desnz_arup_2024_onshore_solar", "Table 3, insurance over total capex, central")]
    # Business rates at solar's ratio on both, since 12 Nov 2026 (user; h2_capex.rates_frac).
    h2_rates = hc.rates_frac()
    ely_ins = T.cost("cost.electrolyser.insurance_frac", hc.INSURANCE_FRAC_OF_CAPITAL, "fraction of capital per year",
                     "Electrolyser insurance, at onshore wind's ratio to capital", grade="proxy", cites=_ins_cite) \
        + h2_rates
    tank_ins = T.cost("cost.h2_tank.insurance_frac",
                      hc.INSURANCE_FRAC_OF_CAPITAL if tank_insurance_frac is None else float(tank_insurance_frac),
                      "fraction of capital per year", "Tank insurance, at onshore wind's ratio to capital",
                      grade="proxy", cites=_ins_cite) \
        + (h2_rates if tank_insurance_frac is None else 0.0)    # the sweep's figure is insurance and rates together

    # electrolyser
    ely_row = ely.with_heat_source(
        next(r for r in ely.decompose_all() if r["technology"] == ely_tech), soec_heat)
    ely_key = ely_tech.split()[0].lower()
    ec = pd.Series(hc.electrolyser_cost(ely_key, cost_case))
    ek = f"cost.electrolyser_{ely_key}"
    rate_e = T.cost("cost.electrolyser.discount_rate", DISCOUNT_RATE, "fraction per year",
                    "The electrolyser's discount rate: CEPA's hurdle rate for hydrogen electrolysers",
                    grade="transcribed", cites=[("cepa_hurdle_rates_2025", "Table E.1, hydrogen electrolyser, 10.10 %")])
    crf_e = T.cost(f"{ek}.crf", batt.capital_recovery_factor(rate_e, float(ec.lifetime_years)), "per year",
                   "Capital recovery factor over the plant life", uses=["cost.electrolyser.discount_rate",
                                                                        f"{ek}.lifetime_years"])
    build_e = T.cost("cost.electrolyser.construction_years", ELECTROLYSER_BUILD_YEARS, "years", "Construction period",
                     grade="transcribed", cites=[("beis_h2_costs_2021", "Technical and cost assumptions, construction "
                                                                         "period 3 years, every electrolyser")])
    finance_e = T.cost(f"{ek}.building_finance_factor", tc.building_finance_factor(rate_e, build_e), "multiplier",
                       "Capital carried at the rate over the build",
                       uses=["cost.electrolyser.discount_rate", "cost.electrolyser.construction_years"])
    # Stacks charged per replacement in cost as in carbon (20 Nov 2026, user): the
    # stack's share of the installed price from the Danish Energy Agency's sheets,
    # bought on ely_stack_units = max(calendar, running hours). Named stack_cost_frac:
    # stack_share below is the stack's share of the electrolyser's electricity.
    stack_cost_frac = T.cost("cost.electrolyser.stack_cost_fraction", hc.ely_stack_cost_fraction(ely_key),
                             "fraction of capital", "Stack share of the installed electrolyser price",
                             grade="derived", uses=[f"{ek}.dea_stack_EUR_per_kWe", f"{ek}.dea_investment_EUR_per_kWe"],
                             note="Rozzi et al. 2024's 35 % of equipment is about 21 % installed; tested at x0.5/x1.5")
    # SOEC's heat in the gas_boiler scenario is bought fuel. In electric_boiler it
    # is already in kwh_per_kg, paid at the hour's price; other types pass neither.
    heat_gbp_per_kg, heat_uses = 0.0, []
    heat_gas_kwh = ely.gas_boiler_fuel_kwh_per_kg(ely_row)
    if heat_gas_kwh:
        fuel = T.cost(f"{ek}.heat_fuel_kwh_per_kg", heat_gas_kwh, "kWh of gas (HHV) per kg H2",
                      "Gas burned for the external heat", grade="derived",
                      cites=[("element_energy_2018", "p. 95, auxiliary boiler efficiency 95 % (HHV)")],
                      inputs={"boiler_efficiency": ely.GAS_BOILER_EFFICIENCY})
        gas = site_gas_gbp_per_mwh(ccl_under_cca, gas_case, record=True)
        heat_gbp_per_kg = T.cost(f"{ek}.heat_per_kg", fuel * gas / 1000.0, "GBP per kg H2", "Bought heat per kg made",
                                 uses=[f"{ek}.heat_fuel_kwh_per_kg", "cost.gas_price_per_MWh"])
        heat_uses = [f"{ek}.heat_per_kg"]

    # grid: the HH locational tariff, split out to be charged on Triad demand
    tnuos_hh = float((meta.get("network_charges") or {}).get("tnuos_locational_GBP_per_MW_year", 0.0))
    net_trace = (meta.get("network_charges") or {}).get("trace") or {}

    # grid connection capital
    from optimisation import connection_cost
    conn = connection_cost.connection_costs(sites.get(site).carbon_api_region,
                                            bool(meta.get("transmission_connected", False)),
                                            cost_case,
                                            connection_voltage=meta.get("connection_voltage"),
                                            route_km=(meta.get("connection_site") or {}).get("route_km"))
    conn = {**conn, "per_MW_year_GBP": conn["per_MW_year_GBP"] * build_scale,
            "fixed_per_year_GBP": conn["fixed_per_year_GBP"] * build_scale}

    # tank
    tank_row = h2s.traced(next(r for r in h2s.decompose() if r["design"] == tank_design))
    tkc = pd.Series(hc.tank_cost(cost_case))

    # fuel cell
    d = fc.decompose()
    if ("bop_container_kgco2e_per_MW" not in d
            or "stack_kgco2e_per_MW_gramc_2025" not in d):  # a cache from before the split
        d = fc.decompose(refresh=True)
    fc_bop_years = float(fc_bop_calendar_years or d["bop_calendar_lifetime_years"])
    fc_stack_years = float(fc_stack_calendar_years or d["stack_calendar_lifetime_years"])
    ely_stack_years = float(ely_stack_calendar_years or ely.STACK_CALENDAR_YEARS)
    ely_stack_life = T.cost("cost.electrolyser.stack_life_years", ely_stack_years, "years",
                            "Stack calendar life, the same the carbon side replaces it on: the floor of one "
                            "stack per plant life", grade="derived", note="electrolysers.STACK_CALENDAR_YEARS")
    crf_es = T.cost(f"{ek}.stack_crf", batt.capital_recovery_factor(rate_e, ely_stack_life), "per year",
                    "Capital recovery factor over the stack's calendar life",
                    uses=["cost.electrolyser.discount_rate", "cost.electrolyser.stack_life_years"])
    fc_kw_box = float(fc_kw_per_container or d["bop_kw_per_container"])
    gwp_fc_bop = T.step("fuel_cell.bop_per_MW_charged",
                        (d["bop_kgco2e_per_MW"] - d["bop_container_kgco2e_per_MW"]
                         + d["bop_container_kgco2e_per_MW"] * d["bop_kw_per_container"] / fc_kw_box),
                        "kg CO2e per MW", "Balance of plant per MW, its container rescaled to "
                        f"{fc_kw_box:g} kW per container",
                        uses=["fuel_cell.bop_per_MW", "fuel_cell.bop_container_per_MW"],
                        inputs={"kW_per_container": fc_kw_box}, grade="assumed")
    fcr = pd.Series(hc.fuel_cell_cost(cost_case, bop_calendar_years=fc_bop_years,
                                      stack_calendar_years=fc_stack_years))

    # gas engines (gas_engine.py, docs/GAS_ENGINE_PLAN.md)
    from optimisation import gas_engine as ge
    from optimisation import h2_prices as _hp
    from optimiser_lca import gas_engine as ge_inv
    gd = ge.decompose()
    gcr = pd.Series(ge.cost(cost_case))
    ge_gas = engine_gas_gbp_per_mwh(gas_case, record=True)
    ge_gas_mwh = T.step("gas_engine.gas_MWh_HHV_per_MWh", ge_inv.GE_GAS_MWH_HHV_PER_MWH, "MWh of gas (HHV) per MWh",
                        "Gas burned per MWh made, on the gas bill's (gross) basis: 44.6 % net efficiency and "
                        "ecoinvent's GB gas at 36.0 MJ/m3 net, 40.0 gross", grade="derived")
    carbon_t = T.cost("cost.carbon_price.gb_total_2026", _hp.carbon_gbp_per_t_2026(), "GBP per t CO2 (2026)",
                      "NESO's GB total carbon price for 2026: UK ETS plus carbon price support", grade="derived",
                      cites=[("neso_tyo_2026_workbook", "CP2 base case, GB total carbon price 2026 EUR 80.94/t; "
                                                        "CP1 2026 GBP 1 = EUR 1.12")])
    ge_co2_t = T.cost("cost.gas_engine.co2_t_per_MWh",
                      ge_inv.GE_GAS_C_KG_PER_KWH * ge_inv.CO2_PER_KG_C, "t CO2 per MWh",
                      "CO2 the carbon price falls on: all the gas's fossil carbon, as the trading scheme counts it",
                      grade="derived", note="Oxidation factor 1; ~0.4 % above the inventory's CO2, which nets the "
                                            "carbon leaving as methane and carbon monoxide")

    T.cost("cost.unserved.voll_per_MWh", dc_model.VOLL_GBP_PER_MWH, "GBP per MWh",
           "Value of lost load: the penalty on a MWh of demand left unserved", grade="assumed",
           note="dc_model.VOLL_GBP_PER_MWH. Not a market number: large enough that shortfall is a last resort; "
                "at the default zero allowance the reliability constraint is hard")

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
        elec = T.cost(f"cost.bought_h2.{colour}.producer_electricity_price",
                      h2_prices.PRODUCER_ELEC_GBP_PER_MWH[cost_case], "GBP per MWh",
                      "What the seller pays for the electricity that compresses it onto a trailer", grade="assumed",
                      note="h2_prices.PRODUCER_ELEC_GBP_PER_MWH; the compressor's capital is not charged (a floor)")
        compression_gbp = T.cost(
            f"cost.bought_h2.{colour}.compression_per_kg",
            h2_prices.bought_h2_compression_gbp_per_kg(colour, cost_case), "GBP per kg H2",
            "Trailer compression, electricity only", uses=[f"cost.bought_h2.{colour}.producer_electricity_price"],
            inputs={"kWh_per_kg": h2_prices.bought_h2_compression_kwh_per_kg(colour), "GBP_per_MWh": elec})

        def plant_gate(r):
            """The recommended-table price of one row, recorded with where it came from."""
            slug = "_".join(str(r.variant).replace(",", "").split())
            src = str(r.central_source)
            key = f"cost.bought_h2.{colour}.{slug}.plant_gate"
            if src.startswith("DESNZ HAR1"):
                # green since 11 Nov 2026: the first allocation round's strike price
                strike = T.cost(f"cost.bought_h2.{colour}.har1_strike_per_MWh", h2_prices.HAR1_STRIKE_GBP_PER_MWH_HHV,
                                "GBP per MWh H2 (HHV)", "First hydrogen allocation round, weighted average strike "
                                f"price, {h2_prices.HAR1_PRICE_YEAR} prices", grade="transcribed",
                                cites=[("desnz_har2_cost_challenge_2025", "'a weighted average strike price of "
                                        "241 £/MWh H2 (HHV)', footnote 1 'In 2023 real prices'")],
                                note="What the producer is guaranteed, return on capital included; one figure "
                                     "for both sellers and every cost case")
                infl = P.to_2025(h2_prices.HAR1_PRICE_YEAR)
                return T.cost(key, float(r[cost_case]), "GBP per kg H2",
                              f"Bought {colour} hydrogen at the plant gate: {r.variant}, 2025 pounds",
                              grade="derived",
                              uses=[f"cost.bought_h2.{colour}.har1_strike_per_MWh",
                                    f"price_base.{h2_prices.HAR1_PRICE_YEAR}_to_2025"],
                              inputs={"GBP_per_MWh_HHV": strike, "kWh_HHV_per_kg": h2_prices.H2_HHV_KWH_PER_KG,
                                      "to_2025": infl},
                              note=f"{src}. Previously: {r.corroboration}"), key
            if src.startswith("BEIS"):
                # blue since 11 Nov 2026: converted from £/MWh HHV in 2020 prices
                return T.cost(key, float(r[cost_case]), "GBP per kg H2",
                              f"Bought {colour} hydrogen at the plant gate: {r.variant}, 2025 pounds",
                              grade="derived",
                              cites=[("beis_h2_costs_2021", f"sheet 2025_R, SMR with CCUS 300MW, total LCOH, "
                                                            f"Industrial LRVC ({cost_case.capitalize()})")],
                              uses=[f"price_base.{h2_prices.BEIS_H2_PRICE_YEAR}_to_2025"],
                              inputs={"GBP_per_MWh_HHV": h2_prices.BEIS_SMR_CCS_GBP_PER_MWH_HHV[cost_case],
                                      "kWh_HHV_per_kg": h2_prices.H2_HHV_KWH_PER_KG,
                                      "to_2025": P.to_2025(h2_prices.BEIS_H2_PRICE_YEAR)},
                              note=f"{src}. Previously: {r.corroboration}"), key
            cites = [("eho_uk_2025", f"{src}; the {cost_case} column of optimisation_outputs/"
                                     "h2_prices_recommended.csv")] if src.startswith("EHO") else []
            return T.cost(key, float(r[cost_case]), "GBP per kg H2",
                          f"Bought {colour} hydrogen at the plant gate: {r.variant}",
                          grade="transcribed" if cites else "derived", cites=cites,
                          note=f"{src}. Range check: {r.corroboration}"), key
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
            share = T.cost(f"cost.bought_h2.{colour}.grid_share", h2_prices._resolve_grid_share(green_h2_grid_share),
                           "fraction", "Share of the green hydrogen bought from grid-connected electrolysers",
                           grade="derived",
                           cites=[("desnz_har1_successful_2023", "the signed projects and their capacities"),
                                  ("desnz_h2_update_july_2025", "p. 19: 'most of these projects aim to use long term "
                                                                "power purchase agreements'")],
                           note="h2_prices.GREEN_H2_GRID_SHARE unless the run sets it: 0.35 confirmed to 0.73 by "
                                "capacity across the first round's ten signed projects, each project's power "
                                "arrangement from its own material")
            behind = row[row.variant != grid_variant].iloc[0]
            delivered = row[row.variant == grid_variant].iloc[0]
            (p_behind, k_behind), (p_grid, k_grid) = plant_gate(behind), plant_gate(delivered)
            return (T.cost(f"cost.bought_h2.{colour}.delivered",
                           ((1.0 - share) * p_behind + share * p_grid + compression_gbp) * to26, "GBP per kg H2",
                           f"Bought {colour} hydrogen delivered to the tank: the two sellers by share, plus "
                           "compression, in 2026 pounds",
                           uses=[k_behind, k_grid, f"cost.bought_h2.{colour}.grid_share",
                                 f"cost.bought_h2.{colour}.compression_per_kg", *k26]),
                    _bought_h2_gwp(behind.activity_code, green_h2_basis,
                                   grid_share=share),
                    f"{1.0 - share:.0%} behind the meter / "
                    f"{share:.0%} grid-connected")
        # One row: either a colour with a single variant, or green pinned to
        # one of its two by an explicit variant.
        one = row.iloc[0]
        p_one, k_one = plant_gate(one)
        gas_adj, gas_uses = _bought_gas_adjustment(colour, gas_case, h2_prices)
        return (T.cost(f"cost.bought_h2.{colour}.delivered", (p_one + gas_adj + compression_gbp) * to26,
                       "GBP per kg H2",
                       f"Bought {colour} hydrogen delivered to the tank: plant gate plus compression, in 2026 pounds",
                       uses=[k_one, *gas_uses, f"cost.bought_h2.{colour}.compression_per_kg", *k26]),
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

    def cstep(field, value, unit, title, uses=(), **kw):
        """``step`` for a cost coefficient: on the cost map, not the LCA map."""
        return T.cost(f"coefficient.{field}", value, unit, title, uses=uses, depth=1, **kw)


    tech = dc_model.Tech(
        gwp_wind=step("gwp_wind", gen_gwp("onshore_wind"), "kg CO2e per MW per year",
                      "Onshore wind, per MW built", ["onshore_wind.annual_per_MW"]),
        gwp_solar=step("gwp_solar", gen_gwp("solar_pv"), "kg CO2e per MWp per year",
                       "Solar PV, per MWp built", ["solar_pv.annual_per_MW"]),
        gwp_batt_p=step("gwp_batt_p", be["power_kgco2e_per_kW"] * 1000.0 / batt.ASSET_LIFE_YEARS,
                        "kg CO2e per MW per year", "Battery power conversion, per MW, over the battery's life",
                        ["battery.pcs_per_kW"], inputs={"asset_life_years": batt.ASSET_LIFE_YEARS}),
        gwp_batt_e=step("gwp_batt_e", be["energy_kgco2e_per_kWh"] * 1000.0 / batt.ASSET_LIFE_YEARS
                        * batt_oversize,
                        "kg CO2e per MWh per year", "Battery cells, racks and container, per usable MWh "
                        "needed at end of life, over the battery's life",
                        ["battery.energy_per_usable_kWh", "battery.end_of_life_oversize"],
                        inputs={"asset_life_years": batt.ASSET_LIFE_YEARS}),
        # The balance of plant once over the plant's life; the stacks by replacement
        # (gwp_ely_stack_per_mw x ely_stack_units, dc_model): at least the first stack
        # over the plant's life, more by running hours (one-stack floor, 19 Nov 2026).
        gwp_ely=step("gwp_ely", ely_row["plant_kgco2e_per_MW"] / ely.PLANT_LIFETIME_YEARS * stack_share,
                     "kg CO2e per MW per year", f"{ely_tech.split()[0]} electrolyser balance of plant, "
                     "per MW of cap_ely, over the plant's life",
                     [f"{eb}.plant_per_MW", "electrolyser.stack_share"],
                     inputs={"plant_lifetime_years": ely.PLANT_LIFETIME_YEARS}),
        gwp_ely_stack_per_mw=step("gwp_ely_stack_per_mw", ely_row["stack_kgco2e_per_MW"] * stack_share,
                                  "kg CO2e per MW replaced", f"One {ely_tech.split()[0]} stack per MW "
                                  "of cap_ely, charged per replacement (max of calendar and duty)",
                                  [f"{eb}.stack_per_MW", "electrolyser.stack_share"],
                                  inputs={"calendar_years": ely_stack_years,
                                          "duty_hours": ely.STACK_DUTY_HOURS}),
        ely_stack_calendar_years=ely_stack_years,
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
        gwp_ge_per_mw=step("gwp_ge_per_mw", gd["plant_kgco2e_per_MW"], "kg CO2e per MW replaced",
                           "Gas engine plant (engines, generators, controls, pads, hall), per replacement "
                           "(max of calendar and duty)", ["gas_engine.plant_per_MW"],
                           inputs={"calendar_years": ge.CALENDAR_YEARS, "duty_hours": gd["duty_hours"]}),
        gwp_ge_running_per_mwh=step("gwp_ge_running_per_mwh", gd["running_kgco2e_per_MWh"], "kg CO2e per MWh",
                                    "Gas engines running: British gas's supply chain, burning, exhaust and oil, "
                                    "per MWh made", ["gas_engine.running_per_MWh"]),
        gwp_ge_maint_per_mwh=step("gwp_ge_maint_per_mwh", gd["maintenance_kgco2e_per_MWh"], "kg CO2e per MWh",
                                  "Gas engine maintenance, per MWh made", ["gas_engine.maintenance_per_MWh"]),
        ge_calendar_years=ge.CALENDAR_YEARS,
        ge_duty_hours=gd["duty_hours"],
        gwp_grid_per_mw=step("gwp_grid_per_mw", gc.kgco2e_per_mw_year(), "kg CO2e per MW per year",
                             "Grid connection, per MW of cap_grid", ["grid_connection.per_MW_year"]),
        # The cable to the connection substation over its real route (the
        # single price list's; each option carries its own below), two
        # circuits, per year. Charged in money since 29 Oct 2026 and in carbon
        # only since 30 Oct: before that an option with a long cable was dearer
        # and carbon-free.
        gwp_grid_fixed_per_year=step(
            "gwp_grid_fixed_per_year",
            gc.line_kgco2e_per_km_year() * connection_cost.CIRCUITS * conn["route_km"],
            "kg CO2e per year", f"The cable to the network substation: {conn['route_km']:.1f} km route, "
            f"{connection_cost.CIRCUITS} circuits, over the line's life",
            ["grid_connection.line_per_km_year"],
            inputs={"route_km": conn["route_km"], "circuits": connection_cost.CIRCUITS}, grade="proxy"),
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
        fc_stack_duty_hours=float(fc_stack_duty_hours or d["stack_lifetime_hours"]),
        batt_max_duration_hours=float(batt_max_duration_hours or np.inf),
        cost_wind=cstep("cost_wind", gen_cost("onshore_wind") * to26, "GBP per MW per year", "Onshore wind, per MW built",
                        ["cost.onshore_wind.annual_per_MW", *k26]),
        cost_solar=cstep("cost_solar", gen_cost("solar_pv") * to26, "GBP per MWp per year", "Solar PV, per MWp built",
                         ["cost.solar_pv.annual_per_MWp", *k26]),
        cost_batt_p=cstep("cost_batt_p", bcost["power_GBP_per_MW_year"] * to26, "GBP per MW per year",
                          "Battery power conversion, per MW", ["cost.battery.power_per_kW", "cost.battery.crf",
                                                               "cost.battery.fixed_opex_per_kW_year", *k26]),
        cost_batt_e=cstep("cost_batt_e", bcost["energy_GBP_per_MWh_year"] * to26 * batt_oversize,
                          "GBP per MWh per year",
                          "Battery energy capacity, per MWh needed at end of life",
                          ["cost.battery.energy_per_kWh", "cost.battery.crf",
                           "cost.battery.fixed_opex_per_kWh_year", "battery.end_of_life_oversize", *k26]),
        # Split like the fuel cell (20 Nov 2026): the plant's annuity, the stack's annuity
        # less its calendar replacement, fixed opex, insurance and rates on capacity;
        # cost_ely_stack_per_mw then buys each stack on ely_stack_units. With the stack
        # replaced on its calendar life this is exactly the old whole-unit annuity.
        cost_ely=cstep("cost_ely", (float(ec.capex_GBP_per_kWe) * 1000.0
                                    * ((1.0 - stack_cost_frac) * finance_e * crf_e
                                       + stack_cost_frac * (finance_e * crf_es - 1.0 / ely_stack_life)
                                       + float(ec.fixed_opex_frac) + ely_ins)
                                    * stack_share) * to26, "GBP per MW per year",
                       f"{ely_tech.split()[0]} electrolyser, per MW of cap_ely: capital recovery (carrying the build's "
                       "finance), less the stack's calendar replacement, fixed opex and insurance, on the stack's "
                       "share of the input",
                       [f"{ek}.capex_per_kWe", f"{ek}.crf", f"{ek}.stack_crf", f"{ek}.building_finance_factor",
                        "cost.electrolyser.stack_cost_fraction", "cost.electrolyser.stack_life_years",
                        f"{ek}.fixed_opex_frac", "cost.electrolyser.insurance_frac", "cost.hydrogen_plant.rates_frac",
                        "electrolyser.stack_share", *k26]),
        cost_ely_stack_per_mw=cstep("cost_ely_stack_per_mw", float(ec.capex_GBP_per_kWe) * 1000.0 * stack_cost_frac
                                    * stack_share * to26, "GBP per MW replaced",
                                    f"One {ely_tech.split()[0]} stack per MW of cap_ely, charged per replacement "
                                    "(max of calendar and duty), as the carbon side",
                                    [f"{ek}.capex_per_kWe", "cost.electrolyser.stack_cost_fraction",
                                     "electrolyser.stack_share", *k26]),
        # Water and consumables per kg made, and SOEC's gas-raised heat. The water and
        # consumables in 2026 pounds; the heat is already (heat_gbp_per_kg)
        cost_ely_variable_per_kg=cstep("cost_ely_variable_per_kg",
                                       float(ec.variable_opex_GBP_per_kg) * to26 + heat_gbp_per_kg,
                                       "GBP per kg H2", "Electrolyser water, consumables and bought heat, per kg made",
                                       [f"{ek}.variable_opex_per_kg", *k26, *heat_uses]),
        cost_tank=cstep("cost_tank", (float(tkc.annual_GBP_per_kg_year)
                                      + float(tkc.capex_GBP_per_kg_capacity) * tank_ins) * to26,
                        "GBP per kg of capacity per year",
                        "Hydrogen tank, per kg it holds, with insurance and rates",
                        ["cost.h2_tank.annual_per_kg", "cost.h2_tank.insurance_frac",
                         "cost.hydrogen_plant.rates_frac", *k26]),
        cost_major_hazard_per_year=cstep("cost_major_hazard_per_year",
                                         float(hc.major_hazard_cost(cost_case)["annual_GBP_per_site_year"]) * to26,
                                         "GBP per year", "Major-hazard compliance, at upper tier, on a build allowed a tank",
                                         ["cost.major_hazard.annual_per_site", *k26]),
        cost_fc=cstep("cost_fc", float(fcr.annual_GBP_per_MW_year) * to26, "GBP per MW per year",
                      "Fuel cell balance of plant and stack, per MW, net of their calendar replacements",
                      ["cost.fuel_cell.annual_per_MW", *k26]),
        cost_fc_stack_per_mw=cstep("cost_fc_stack_per_mw", float(fcr.stack_GBP_per_MW) * to26, "GBP per MW replaced",
                                   "Fuel cell stack, per replacement", ["cost.fuel_cell.stack_per_MW", *k26]),
        cost_fc_bop_per_mw=cstep("cost_fc_bop_per_mw", float(fcr.bop_GBP_per_MW) * to26, "GBP per MW replaced",
                                 "Fuel cell balance of plant, per replacement", ["cost.fuel_cell.bop_per_MW", *k26]),
        cost_ge=cstep("cost_ge", float(gcr.annual_GBP_per_MW_year) * to26, "GBP per MW per year",
                      "Gas engines, per MW: capital recovery and fixed opex, net of the calendar replacement",
                      ["cost.gas_engine.annual_per_MW", *k26]),
        cost_ge_per_mw=cstep("cost_ge_per_mw", float(gcr.capital_GBP_per_MW) * to26, "GBP per MW replaced",
                             "Gas engines, capital and development per replacement",
                             ["cost.gas_engine.capital_per_MW", *k26]),
        cost_ge_gas_per_mwh=cstep("cost_ge_gas_per_mwh", ge_gas * ge_gas_mwh, "GBP per MWh made",
                                  "Gas for the engines, per MWh made",
                                  ["cost.gas_engine.gas_per_MWh_HHV", "gas_engine.gas_MWh_HHV_per_MWh"]),
        cost_ge_carbon_per_mwh=cstep("cost_ge_carbon_per_mwh", carbon_t * ge_co2_t, "GBP per MWh made",
                                     "The carbon price on the engines' CO2, per MWh made",
                                     ["cost.carbon_price.gb_total_2026", "cost.gas_engine.co2_t_per_MWh"]),
        cost_ge_maint_per_mwh=cstep("cost_ge_maint_per_mwh", float(gcr.maintenance_GBP_per_MWh) * to26,
                                    "GBP per MWh made", "Gas engine running maintenance, per MWh made",
                                    ["cost.gas_engine.maintenance_per_MWh", *k26]),
        # Use of system (network_charges) plus the connection's own capital
        # (connection_cost), the same per-MW / fixed split as the carbon side.
        # The HH locational TNUoS tariff comes out of the per-MW charge and is
        # charged on Triad demand instead (cost_grid_triad_per_mw_year).
        cost_grid_per_mw_year=cstep("cost_grid_per_mw_year", (meta["capacity_GBP_per_MW_year"] - tnuos_hh
                                                              + conn["per_MW_year_GBP"]),
                                    "GBP per MW per year", "Grid connection per MW of cap_grid: local capacity "
                                    "charge and the connection's build cost (single price list)",
                                    _known(net_trace.get("network") and net_trace["network"] + ".capacity_per_MW_year",
                                           net_trace.get("tnuos"), conn.get("trace_per_MW_year"))),
        cost_grid_triad_per_mw_year=cstep("cost_grid_triad_per_mw_year", tnuos_hh, "GBP per MW per year",
                                          "National grid locational charge, on winter-peak (Triad) demand",
                                          _known(net_trace.get("tnuos"))),
        cost_grid_fixed_per_year=cstep("cost_grid_fixed_per_year",
                                       meta["fixed_GBP_per_year"] + conn["fixed_per_year_GBP"], "GBP per year",
                                       "Grid connection per year: residual and fixed network charges and the cable",
                                       _known(net_trace.get("network") and net_trace["network"] + ".fixed_per_year",
                                              conn.get("trace_fixed_per_year"))),
        ely_kwh_per_kg=step("ely_kwh_per_kg", ely_row["kwh_per_kg"], "kWh per kg H2",
                            "Electrolyser electricity per kg made", [f"{eb}.kwh_per_kg"]),
        # Since 12 Nov 2026 with the hydrogen leaked at the electrolyser and the fuel cell (h2_leakage.py).
        ely_variable_gwp_per_kg=step("ely_variable_gwp_per_kg",
                                     ely_row["variable_kgco2e_per_kg"] + h2_leak.electrolyser_per_kg(),
                                     "kg CO2e per kg H2", "Electrolyser consumables per kg made, with leaks",
                                     [f"{eb}.variable_per_kg", "h2_leakage.electrolyser_per_kg"]),
        tank_compression_kwh_per_kg=step("tank_compression_kwh_per_kg", compression_kwh, "kWh per kg H2",
                                         "Compression into the tank, per kg", ["tank.compression_kwh_per_kg"]),
        tank_leakage_per_hour=step("tank_leakage_per_hour", tank_row["leakage_frac_per_hour"],
                                   "fraction of stock per hour", "Tank standing loss",
                                   [f"tank.{tank_design}.leakage_per_hour"]),
        tank_usable_fraction=step("tank_usable_fraction", h2s.usable_fraction(tank_design), "fraction of capacity",
                                  "Share of the tank the fuel cell can draw, above its minimum feed pressure",
                                  inputs={"min_pressure_bar": h2s.TANK_MIN_PRESSURE_BAR}, grade="derived",
                                  source="Marocco et al. 2021, Table 5: 3 bar minimum"),
        batt_rte=batt.ROUND_TRIP_EFFICIENCY,
        batt_leakage_per_hour=step("batt_leakage_per_hour", batt.STANDING_LOSS_PER_HOUR,
                                   "fraction of stock per hour", "Battery self-discharge",
                                   inputs={"hours_to_80_percent": batt.SELF_DISCHARGE_HOURS_TO_80_PCT}, grade="derived",
                                   source="Mott MacDonald for BEIS 2018, Table 5, p. 44"),
        fc_kg_h2_per_mwh=d["h2_kg_per_MWh"],
        bought_h2_gbp_per_kg=cstep("bought_h2_gbp_per_kg", h2_price, "GBP per kg H2",
                                   f"Bought hydrogen ({h2_colour or 'none'}), delivered to the tank",
                                   [f"cost.bought_h2.{h2_colour}.delivered"] if h2_colour else [],
                                   **({} if h2_colour else {"grade": "assumed", "note": "No hydrogen bought"})),
        # Since 12 Nov 2026 with the hydrogen leaked making, trucking and burning it (h2_leakage.py).
        bought_h2_gwp_per_kg=step("bought_h2_gwp_per_kg", h2_gwp + h2_leak.bought_per_kg(h2_colour),
                                  "kg CO2e per kg H2",
                                  f"Bought hydrogen ({h2_colour or 'none'}), delivered to the tank, with leaks",
                                  [*b1, *([f"h2_leakage.bought_{h2_colour}_per_kg"] if h2_colour else [])]),
        bought_h2_2_gbp_per_kg=cstep("bought_h2_2_gbp_per_kg", h2_price_2, "GBP per kg H2",
                                     f"Second bought colour ({h2_colour_2 or 'none'}), delivered to the tank",
                                     [f"cost.bought_h2.{h2_colour_2}.delivered"] if h2_colour_2 else [],
                                     **({} if h2_colour_2 else {"grade": "assumed",
                                                                "note": "No second colour bought"})),
        bought_h2_2_gwp_per_kg=step("bought_h2_2_gwp_per_kg", h2_gwp_2 + h2_leak.bought_per_kg(h2_colour_2),
                                    "kg CO2e per kg H2",
                                    f"Second bought colour ({h2_colour_2 or 'none'}), delivered to the tank, with leaks",
                                    [*b2, *([f"h2_leakage.bought_{h2_colour_2}_per_kg"] if h2_colour_2 else [])]),
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
                "connection_build_scale": build_scale,
                "network_charges_scale": float(meta.get("network_charges_scale", 1.0)),
                "gas_price_case": gas_case,
                "ccl_under_cca_gas": (levies_mod.CCL_UNDER_CCA if ccl_under_cca is None else bool(ccl_under_cca)),
                "price_base": f"real {P.TARGET_YEAR} pounds",
                "green_h2_grid_share": (
                    h2_prices._resolve_grid_share(green_h2_grid_share)
                    if "green" in (h2_colour, h2_colour_2) else None)},
    )
    # Transformer conversion losses, on the units the capital terms above
    # already charge.
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
    tech = with_cutoff(tech, cutoff)
    if cost_cutoff not in (None, "upper"):
        raise ValueError(f"cost_cutoff must be None or 'upper', got {cost_cutoff!r}")
    if cost_cutoff == "upper":       # rule 3 of optimisation/cost_exclusions.py
        from dataclasses import replace
        from optimisation import cost_exclusions
        tech = replace(tech, **{f: getattr(tech, f) + v for f, v in cost_exclusions.upper_additions().items()},
                       labels={**(tech.labels or {}), "cost_cutoff": "upper"})
    return with_connection_options(tech, meta, sites.get(site).carbon_api_region, cost_case, tnuos_hh, build_scale)


def _known(*keys) -> list:
    """The trace keys that exist: a build from a hand-made meta (the LCA map's
    zero charges) has no network steps to point at."""
    return [k for k in keys if k]


def with_connection_options(tech: dc_model.Tech, meta: dict, region: int, cost_case: str,
                            tnuos_hh: float | None = None, build_scale: float = 1.0) -> dc_model.Tech:
    """``tech`` with ``connection_options`` from ``meta["connection_options"]``
    (COST_PLAN §1.11): each option's use-of-system charges from the series
    build plus its own build cost — the area's price list at the option's
    voltage over its own cable route (``connection_cost``). One option or none
    leaves the Tech as it is: the single-price-list model.

    The per-MW term is the DUoS capacity charge and the connection capital per
    MW; the zonal HH TNUoS tariff is the same for every option and stays on
    the winter-peak demand (``cost_grid_triad_per_mw_year``). The fixed term
    is the TDR, the DUoS fixed charge and the cable and switchgear.
    ``build_scale`` is ``build_tech``'s ``connection_build_scale``.
    """
    from dataclasses import replace
    import re
    from optimisation import connection_cost
    opts = meta.get("connection_options") or []
    if len(opts) < 2:
        return tech
    if tnuos_hh is None:
        tnuos_hh = float((meta.get("network_charges") or {}).get("tnuos_locational_GBP_per_MW_year", 0.0))
    from optimisation import grid_connection as gc
    line_per_km_year = gc.line_kgco2e_per_km_year()
    out = []
    for o in opts:
        ck = connection_cost.connection_costs(region, bool(o["transmission"]), cost_case,
                                              connection_voltage=o["voltage"], route_km=o.get("route_km"))
        ck = {**ck, "per_MW_year_GBP": ck["per_MW_year_GBP"] * build_scale,
              "fixed_per_year_GBP": ck["fixed_per_year_GBP"] * build_scale}
        slug = re.sub(r"\W+", "_", o["key"]).strip("_")
        nt = (o.get("network_charges") or {}).get("trace") or {}
        per_mw = T.cost(f"connection.{slug}.cost_per_MW_year",
                        o["capacity_GBP_per_MW_year"] - tnuos_hh + ck["per_MW_year_GBP"],
                        "GBP per MW per year",
                        f"Connection option {o['key']}: DUoS capacity charge and connection capital per MW",
                        inputs={"capacity_GBP_per_MW_year": o["capacity_GBP_per_MW_year"],
                                "tnuos_hh_on_triad": tnuos_hh, "build_per_MW_year": ck["per_MW_year_GBP"],
                                "floor_mw": o["floor_mw"], "ceiling_mw": o["ceiling_mw"]},
                        uses=_known(nt.get("network") and nt["network"] + ".capacity_per_MW_year",
                                    nt.get("tnuos"), ck.get("trace_per_MW_year")),
                        grade="derived", source="network_charges.import_charges; connection_cost.connection_costs",
                        note=f"{o['cap_basis']}; {o.get('which')} substation {o.get('substation')} at "
                             f"{(o.get('route_km') or connection_cost.ROUTE_KM):.1f} km")
        fixed = T.cost(f"connection.{slug}.cost_fixed_per_year",
                       o["fixed_GBP_per_year"] + ck["fixed_per_year_GBP"], "GBP per year",
                       f"Connection option {o['key']}: TDR, DUoS fixed charge, cable and switchgear",
                       inputs={"fixed_GBP_per_year": o["fixed_GBP_per_year"], "build_fixed_per_year": ck["fixed_per_year_GBP"],
                               "route_km": ck["route_km"]}, grade="derived",
                       uses=_known(nt.get("network") and nt["network"] + ".fixed_per_year",
                                   ck.get("trace_fixed_per_year")),
                       source="network_charges.import_charges; connection_cost.connection_costs")
        line = T.step(f"connection.{slug}.gwp_fixed_per_year",
                      line_per_km_year * connection_cost.CIRCUITS * ck["route_km"], "kg CO2e per year",
                      f"Connection option {o['key']}: the cable over its own route, two circuits, per year",
                      uses=["grid_connection.line_per_km_year"],
                      inputs={"route_km": ck["route_km"], "circuits": connection_cost.CIRCUITS}, grade="proxy")
        out.append(dc_model.ConnectionOption(
            key=o["key"], group=o["group"], floor_mw=float(o["floor_mw"]), ceiling_mw=float(o["ceiling_mw"]),
            cost_per_mw_year=float(per_mw), cost_fixed_per_year=float(fixed), gwp_per_mw_year=None,
            gwp_fixed_per_year=float(line),
            info={k: o.get(k) for k in ("tier", "transmission", "voltage", "band", "substation", "company", "level",
                                        "route_km", "straight_km", "which", "room_mw", "headroom_status",
                                        "headroom_basis", "headroom_as_of", "cap_basis", "skipped", "delivery_voltage")}
            | {"build_per_MW_year_GBP": ck["per_MW_year_GBP"], "build_fixed_per_year_GBP": ck["fixed_per_year_GBP"],
               "build_route_km": ck["route_km"], "price_list": ck["price_list"], "stand_in": ck["stand_in"],
               "use_of_system_capacity_GBP_per_MW_year": o["capacity_GBP_per_MW_year"],
               "use_of_system_fixed_GBP_per_year": o["fixed_GBP_per_year"]}))
    return replace(tech, connection_options=tuple(out),
                   labels={**(tech.labels or {}), "connection_mode": meta.get("connection_mode"),
                           "connection_options": len(out)})


# Which coefficient each technology's cut-off estimates land on: the per-year
# term the LP charges per unit of the asset, as CUTOFF_RULE_PLAN.md's
# denominator table has it. Battery flows split by side.
CUTOFF_FIELD = {
    ("wind", None): "gwp_tx_wind_per_mw", ("solar", None): "gwp_tx_solar_per_mwp",
    ("battery", "power"): "gwp_tx_batt_per_mw", ("battery", "energy"): "gwp_batt_e",
    ("electrolyser", None): "gwp_ely", ("hydrogen tank", None): "gwp_tank",
    ("fuel cell", None): "gwp_tx_fc_per_mw", ("grid connection", None): "gwp_grid_per_mw",
    ("gas engine", None): "gwp_ge_per_mw",     # per MW replaced, as the register's gas engine entries
    ("facility", None): "dc_fixed_gwp_per_year",
}
CUTOFF_MODES = (None, "central", "upper", "none")


def parse_cutoff(mode):
    """``"upper:<key>|<key>"`` -> ``("upper", {keys})``; any other mode -> ``(mode, None)``.

    A key is a coefficient field (``gwp_batt_e``) or an exclusion's flow name:
    rule 3 one group or one item at a time (11 Nov 2026), to find which
    still-excluded flows move a design. Flow names hold commas, so keys are
    split on ``|``."""
    if isinstance(mode, str) and mode.startswith("upper:"):
        keys = {k.strip() for k in mode[len("upper:"):].split("|") if k.strip()}
        if not keys:
            raise ValueError(f"cutoff {mode!r}: no field or flow named after 'upper:'")
        return "upper", keys
    return mode, None


def with_cutoff(tech: dc_model.Tech, mode: str | None = None) -> dc_model.Tech:
    """``tech`` with the cut-off register's estimates added onto its coefficients.

    None or "central": every ``included_estimate`` entry at its central estimate.
    "upper": those, plus every still-excluded ``cutoff`` entry at its upper
    estimate (rule 3). "upper:<key>|<key>": the same, but only the still-excluded
    entries whose coefficient field or flow name is one of the keys. "none":
    nothing added. The additions are recorded in ``labels["cutoff"]`` and
    ``labels["cutoff_added"]`` (kg per coefficient).
    """
    from dataclasses import replace
    from optimiser_lca import exclusions as X
    base, only = parse_cutoff(mode)
    if base not in CUTOFF_MODES:
        raise ValueError(f"cutoff must be one of {CUTOFF_MODES} or 'upper:<field or flow>', got {mode!r}")

    def picked(e) -> bool:
        return only is None or CUTOFF_FIELD[(e.technology, e.side)] in only or e.flow in only

    if only is not None:
        known = {k for e in X.REGISTER if e.kind == "cutoff" and e.status == "excluded"
                 for k in (CUTOFF_FIELD[(e.technology, e.side)], e.flow)}
        if only - known:
            raise ValueError(f"cutoff {mode!r}: no still-excluded flow or field named {sorted(only - known)}")
    added: dict[str, float] = {}
    if base != "none":
        for e in X.REGISTER:
            if e.kind == "boundary":
                continue
            if e.status == "included_estimate":            # a failed cut-off, or a sourced figure carried whole
                est = e.estimate("central")
            elif e.kind == "cutoff" and e.status == "excluded" and base == "upper" and picked(e):
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
                          or (base == "upper" and e.kind == "cutoff" and e.status == "excluded"
                              and picked(e)))]
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
