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
DC_CACHE = OUT_DIR / "dc_facility_decomposition_cache.json"

from optimisation import dc_model, sites

DISCOUNT_RATE = 0.06        # as sizing.Electrolyser; see ASSUMPTIONS.md


def data_centre_coefficients(refresh: bool = False) -> dict:
    """The facility's own burden: fixed per year, plus non-electricity per MWh.

    Constant across every architecture — the same building is being powered
    each way — so it shifts every result by the same amount and never changes a
    ranking. Reported separately for exactly that reason.
    """
    if DC_CACHE.exists() and not refresh:
        try:
            return json.loads(DC_CACHE.read_text())
        except Exception:
            pass
    import bw2data as bd
    import lca_helpers as H
    import dashboard_config as cfg
    from optimisation import baseline_grid as bg

    H.setup_brightway()
    method = bg.gwp_method()
    _dc, fixed, kwh, _n = bg.decompose_data_centre(method)
    years = float(cfg.DC_OPERATION_YEARS)
    out = {
        "fixed_kgco2e_over_life": fixed,
        "electricity_kwh_over_life": kwh,
        "operation_years": years,
        "reference_mw": kwh / years / dc_model.HOURS_PER_YEAR / 1000.0,
        "fixed_kgco2e_per_year": fixed / years,
    }
    OUT_DIR.mkdir(exist_ok=True)
    DC_CACHE.write_text(json.dumps(out, indent=2))
    return out


def build_series(site, start: str, end: str, size_mw_it: float,
                 pue: float = 1.15, token: str | None = None) -> dc_model.Series:
    """Aligned half-hourly inputs for one site and window.

    ``site`` is anything ``sites.get`` accepts — a ``Site``, a ``(lat, lon)``
    pair, a ``"lat,lon"`` string, or a preset name. Coordinates are the real
    interface; presets are shortcuts.
    """
    from optimisation import network_charges as nc
    from optimisation import profiles

    site = sites.get(site)
    df, meta = profiles.build(site.lat, site.lon, start, end, token=token)
    sites.require_grid_region(site, meta["grid_file"])

    index = pd.DatetimeIndex(df.index)
    charges = nc.import_charges(index, zone_no=site.tnuos_zone, tdr_band=site.tdr_band)
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
               size_mw_it: float = 7.31, pue: float = 1.15) -> dc_model.Tech:
    """Resolve every coefficient the LP needs. Touches Brightway only via caches."""
    import dashboard_config as cfg
    from optimisation import battery as batt
    from optimisation import electrolysers as ely
    from optimisation import fuel_cell as fc
    from optimisation import h2_capex as hc
    from optimisation import h2_prices
    from optimisation import h2_storage as h2s
    from optimisation import renewables as ren
    from optimisation import tech_costs as tc

    # The guard this whole design exists to make explicit.
    ely.assert_no_double_count(uses_capital_per_mw=True, uses_foreground_fixed=False)

    tank_design = tank_design or cfg.TANK_DESIGN
    emb = ren.apply_case(ren.decompose_all(), cost_case).set_index("technology")
    ann = tc.annualised_table()

    def gen_cost(asset):
        r = ann[(ann.asset == asset) & (ann.case == cost_case)].iloc[0]
        return float(r.total_annual_cost_GBP_per_MW_year)

    def gen_gwp(asset):
        r = emb.loc[asset]
        return float(r.capital_kgco2e_per_MW / r.study_lifetime_years)

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

    # bought hydrogen
    h2_price = h2_gwp = 0.0
    if h2_colour:
        rec = pd.read_csv(OUT_DIR / "h2_prices_recommended.csv")
        row = rec[rec.colour == h2_colour]
        if row.empty:
            raise ValueError(f"Unknown H2 colour {h2_colour!r}. "
                             f"Available: {sorted(rec.colour.unique())}")
        h2_price = float(row.iloc[0][cost_case])
        h2_gwp = _bought_h2_gwp(row.iloc[0].activity_code)

    dc = data_centre_coefficients()
    scale_dc = (size_mw_it * pue) / dc["reference_mw"]

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
        cost_grid_per_mw_year=meta["capacity_GBP_per_MW_year"],
        cost_grid_fixed_per_year=meta["fixed_GBP_per_year"],
        ely_kwh_per_kg=ely_row["kwh_per_kg"],
        ely_variable_gwp_per_kg=ely_row["variable_kgco2e_per_kg"],
        tank_compression_kwh_per_kg=tank_row["compression_kwh_per_kg"],
        tank_leakage_per_hour=tank_row["leakage_frac_per_hour"],
        batt_rte=batt.ROUND_TRIP_EFFICIENCY,
        batt_leakage_per_hour=getattr(batt, "STANDING_LOSS_PER_HOUR", 0.0),
        fc_kg_h2_per_mwh=d["h2_kg_per_MWh"],
        bought_h2_gbp_per_kg=h2_price, bought_h2_gwp_per_kg=h2_gwp,
        dc_fixed_gwp_per_year=dc["fixed_kgco2e_per_year"] * scale_dc,
        dc_other_gwp_per_mwh=0.0,
        horizon_years=horizon_years,
        labels={"site": getattr(site, "key", site), "ely_tech": ely_tech, "tank_design": tank_design,
                "h2_colour": h2_colour, "cost_case": cost_case},
    )


_H2_GWP_CACHE = OUT_DIR / "bought_h2_gwp_cache.json"


def _bought_h2_gwp(activity_code: str) -> float:
    """kg CO2e per kg of purchased hydrogen, from its own foreground activity."""
    cache = {}
    if _H2_GWP_CACHE.exists():
        try:
            cache = json.loads(_H2_GWP_CACHE.read_text())
        except Exception:
            pass
    if activity_code in cache:
        return cache[activity_code]
    import bw2data as bd
    import lca_helpers as H
    from optimisation import baseline_grid as bg
    H.setup_brightway()
    act = bd.get_activity(("hydrogen foreground", activity_code))
    score = H.run_lca_score(act, bg.gwp_method())
    cache[activity_code] = score
    OUT_DIR.mkdir(exist_ok=True)
    _H2_GWP_CACHE.write_text(json.dumps(cache, indent=2))
    return score


if __name__ == "__main__":
    dc = data_centre_coefficients()
    print("Data centre facility, from its own foreground:")
    print(f"  reference load        {dc['reference_mw']:.3f} MW continuous")
    print(f"  fixed burden          {dc['fixed_kgco2e_per_year'] / 1000:,.0f} t CO2e/yr")
    print(f"  lifetime electricity  {dc['electricity_kwh_over_life'] / 1e9:.2f} TWh "
          f"over {dc['operation_years']:.0f} y")
