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
DC_CACHE = OUT_DIR / "dc_facility_decomposition_v2_cache.json"

from optimisation import dc_model, sites

DISCOUNT_RATE = 0.06        # as sizing.Electrolyser; see ASSUMPTIONS.md


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
    import dashboard_config as cfg
    from optimisation import baseline_grid as bg

    H.setup_brightway()
    method = bg.gwp_method()
    _dc, groups, kwh = bg.decompose_data_centre_by_driver(method)
    years = float(cfg.DC_OPERATION_YEARS)
    pue_ref = float(cfg.DC_REFERENCE_PUE)

    facility_mw = kwh / years / dc_model.HOURS_PER_YEAR / 1000.0
    reference_it_mw = facility_mw / pue_ref
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
                 pue: float = 1.15, token: str | None = None,
                 connection_headroom: float | None = None,
                 auto_build: bool = True, on_progress=None) -> dc_model.Series:
    """Aligned half-hourly inputs for one site and window.

    ``site`` is anything ``sites.get`` accepts — a ``Site``, a ``(lat, lon)``
    pair, a ``"lat,lon"`` string, or a preset name. Coordinates are the real
    interface; presets are shortcuts.

    ``auto_build`` builds the grid series if none covers the window yet, rather
    than raising — see ``profiles.load_grid_and_price``. On by default, so any
    window at any GB coordinate just works; the wait only happens when
    something is genuinely missing. ``on_progress`` takes a one-line notice
    before that wait.
    """
    from optimisation import network_charges as nc
    from optimisation import profiles

    site = sites.get(site)
    # tilt/azimuth are left unset so profiles.fetch_solar_cf takes them from
    # dashboard_config. Before this, they were hard-coded defaults in that
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
        conn_mw, site.transmission_connected)
    tdr_band, tdr_note = site.tdr_band, ""
    if tdr_band is None:
        tdr_band, tdr_note = nc.tdr_band_for(
            conn_mw, annual_mwh, transmission_connected=transmission)
    charges = nc.import_charges(index, zone_no=site.tnuos_zone, tdr_band=tdr_band,
                                transmission_connected=transmission)
    price = df["price_GBP_per_MWh"].to_numpy() + \
        charges["volumetric_GBP_per_MWh"].to_numpy()

    series = dc_model.Series(
        index=index,
        dt_hours=float(meta["slice_hours"]),
        demand_mw=np.full(len(index), size_mw_it * pue),
        cf_wind=df["wind_cf"].to_numpy(),
        cf_solar=df["solar_cf"].to_numpy(),
        grid_gwp_per_mwh=df["grid_kgco2e_per_kwh"].to_numpy() * 1000.0,
        grid_price_per_mwh=price,
    )
    meta["network_charges"] = charges["components"]
    meta["capacity_GBP_per_MW_year"] = charges["capacity_GBP_per_MW_year"]
    meta["fixed_GBP_per_year"] = charges["fixed_GBP_per_year"]
    meta["tdr_band"] = tdr_band
    meta["tdr_band_note"] = tdr_note
    meta["connection_limit_mw"] = conn_mw
    meta["connection_limit_note"] = conn_note
    meta["connection_headroom"] = (
        connection_headroom if connection_headroom is not None
        else sites.CONNECTION_HEADROOM_ASSUMED)
    meta["transmission_connected"] = transmission
    meta["connection_tier_note"] = tier_note
    meta["site"] = site.key
    meta["site_name"] = site.name
    meta["lat"], meta["lon"] = site.lat, site.lon
    meta["carbon_api_region"] = site.carbon_api_region
    meta["tnuos_zone"] = site.tnuos_zone
    return series, meta


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
    )


def build_tech(site, meta: dict, *, ely_tech: str = "PEM operation",
               tank_design: str | None = None, h2_colour: str | None = None,
               cost_case: str = "central", horizon_years: float = 25.0,
               size_mw_it: float = 100.0, pue: float = 1.15,
               solar_basis: str | None = None, h2_variant: str | None = None,
               green_h2_basis: str | None = None,
               green_h2_grid_share: float | None = None,
               h2_colour_2: str | None = None,
               h2_variant_2: str | None = None) -> dc_model.Tech:
    """Resolve every coefficient the LP needs. Touches Brightway only via caches.

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
    """
    import dashboard_config as cfg
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

    tank_design = tank_design or cfg.TANK_DESIGN
    solar_basis = solar_basis or ren.SOLAR_EMBODIED_BASIS
    green_h2_basis = green_h2_basis or h2_prices.GREEN_H2_ELECTRICITY_BASIS
    emb = ren.apply_case(ren.decompose_all(), cost_case,
                         solar_basis=solar_basis).set_index("technology")
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
    be = batt.embodied_components()

    # electrolyser
    ely_row = next(r for r in ely.decompose_all() if r["technology"] == ely_tech)
    ely_costs = hc.electrolyser_costs()
    key = "electrolyser_" + ely_tech.split()[0].lower()
    ec = ely_costs[(ely_costs.asset == key) & (ely_costs.case == cost_case)].iloc[0]
    crf_e = batt.capital_recovery_factor(DISCOUNT_RATE, float(ec.lifetime_years))

    # tank
    tank_row = next(r for r in h2s.decompose() if r["design"] == tank_design)
    tk = hc.tank_costs()
    tkc = tk[tk.case == cost_case].iloc[0]

    # fuel cell
    d = fc.decompose()
    fcc = hc.fuel_cell_costs()
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

    dc = data_centre_coefficients()
    # PUE reaches the facility only through demand, which the energy-driven part
    # is charged against. The IT-driven part must not move with it.
    scale_it = size_mw_it / dc["reference_it_mw"]

    return dc_model.Tech(
        gwp_wind=gen_gwp("onshore_wind"), gwp_offshore=gen_gwp("offshore_wind"),
        gwp_solar=gen_gwp("solar_pv"),
        gwp_batt_p=be["power_kgco2e_per_kW"] * 1000.0 / batt.ASSET_LIFE_YEARS,
        gwp_batt_e=be["energy_kgco2e_per_kWh"] * 1000.0 / batt.ASSET_LIFE_YEARS,
        gwp_ely=ely_row["capital_kgco2e_per_MW"] / ely.PLANT_LIFETIME_YEARS,
        gwp_tank=tank_row["kgco2e_per_kg_capacity_year"],
        gwp_fc_bop_per_mw=d["bop_kgco2e_per_MW"],
        gwp_fc_stack_per_mw=d["stack_kgco2e_per_MW"],
        gwp_fc_maint_per_mwh=d["maintenance_kgco2e_per_MWh"],
        gwp_grid_per_mw=gc.kgco2e_per_mw_year(),
        # The step-up between generator terminals and the site collection
        # network — 690 V (LOW) up to medium voltage, which is where the data
        # centre draws. Wind is the real per-turbine units from Leng's bill of
        # materials, built as a foreground activity in notebook 2; solar is
        # still the old invented plant-rated unit on ecoinvent's electronics
        # transformer. The two are NOT on one basis: see transformers.py.
        gwp_tx_wind_per_mw=tx.kgco2e_per_mw_year("onshore_wind"),
        gwp_tx_solar_per_mwp=tx.kgco2e_per_mw_year("solar_pv"),
        fc_bop_calendar_years=d["bop_calendar_lifetime_years"],
        fc_bop_duty_hours=d["bop_duty_lifetime_hours"],
        fc_stack_duty_hours=d["stack_lifetime_hours"],
        cost_wind=gen_cost("onshore_wind"), cost_offshore=gen_cost("offshore_wind"),
        cost_solar=gen_cost("solar_pv"),
        cost_batt_p=bc["power_GBP_per_kW"] * 1000.0 * annuity_b,
        cost_batt_e=bc["energy_GBP_per_kWh"] * 1000.0 * annuity_b,
        cost_ely=float(ec.capex_GBP_per_kWe) * 1000.0 * (crf_e + float(ec.fixed_opex_frac)),
        cost_tank=float(tkc.annual_GBP_per_kg_year),
        cost_fc=float(fcr.annual_GBP_per_MW_year),
        cost_fc_stack_per_mw=float(fcr.stack_GBP_per_MW),
        cost_grid_per_mw_year=meta["capacity_GBP_per_MW_year"],
        cost_grid_fixed_per_year=meta["fixed_GBP_per_year"],
        ely_kwh_per_kg=ely_row["kwh_per_kg"],
        ely_variable_gwp_per_kg=ely_row["variable_kgco2e_per_kg"],
        # From the electrolyser that actually feeds this tank, not from the
        # tank's pressure alone. h2_storage cannot know which technology was
        # chosen; this is the only place that does.
        tank_compression_kwh_per_kg=h2s.compression_kwh_per_kg(
            ely.DELIVERY_PRESSURE_BAR[ely_tech], tank_row["pressure_bar"]),
        tank_leakage_per_hour=tank_row["leakage_frac_per_hour"],
        batt_rte=batt.ROUND_TRIP_EFFICIENCY,
        batt_leakage_per_hour=batt.STANDING_LOSS_PER_HOUR,
        fc_kg_h2_per_mwh=d["h2_kg_per_MWh"],
        bought_h2_gbp_per_kg=h2_price, bought_h2_gwp_per_kg=h2_gwp,
        bought_h2_2_gbp_per_kg=h2_price_2, bought_h2_2_gwp_per_kg=h2_gwp_2,
        dc_fixed_gwp_per_year=dc["it_kgco2e_per_year"] * scale_it,
        dc_other_gwp_per_mwh=dc["energy_kgco2e_per_mwh"],
        horizon_years=horizon_years,
        labels={"site": getattr(site, "key", site), "ely_tech": ely_tech, "tank_design": tank_design,
                "h2_colour": h2_colour, "cost_case": cost_case, "solar_basis": solar_basis,
                "h2_variant": h2_variant, "green_h2_basis": green_h2_basis,
                "h2_colour_2": h2_colour_2, "h2_variant_2": h2_variant_2,
                "green_h2_grid_share": (
                    h2_prices._resolve_grid_share(green_h2_grid_share)
                    if "green" in (h2_colour, h2_colour_2) else None)},
    )


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
        return (h2_prices.green_h2_gwp_per_kg(green_basis, grid_share=grid_share)
                + compression)

    cache = {}
    if _H2_GWP_CACHE.exists():
        try:
            cache = json.loads(_H2_GWP_CACHE.read_text(encoding="utf-8"))
        except Exception:
            pass
    if activity_code in cache:
        return cache[activity_code] + compression
    import bw2data as bd
    import lca_helpers as H
    from optimisation import baseline_grid as bg
    H.setup_brightway()
    act = bd.get_activity(("hydrogen foreground", activity_code))
    score = H.run_lca_score(act, bg.gwp_method())
    cache[activity_code] = score
    OUT_DIR.mkdir(exist_ok=True)
    _H2_GWP_CACHE.write_text(json.dumps(cache, indent=2), encoding="utf-8")
    return score + compression


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
