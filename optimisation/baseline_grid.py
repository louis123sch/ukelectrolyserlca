"""
Baseline 1 — data centre on the GB grid.
=============================================================================

The Zhang et al. data centre is authored against ``market for electricity,
medium voltage [US-SERC]``. This replaces that with the half-hourly GB grid
mix already produced by ``3.1.custom_grid_carbon_intensity_api.ipynb`` (the
Carbon Intensity API path), and prices the same electricity at the Elexon
half-hourly wholesale price from ``5.prices.ipynb``.

The data centre is assumed to run flat at 100%. That is not a new assumption:
the foreground's own 1.60e9 kWh over 25 years is 7,306 kW continuous, which is
where ``dashboard_config.SYS_DC_DEMAND_MW = 7.31`` came from.

Emissions are computed as ``fixed + sum_t(kWh_t * EF_t)`` rather than by
re-solving the LCI per slice. That decomposition is exact — validated against
a full Brightway swap to within 1e-4 % — and it is what lets an optimiser
treat the LCA as linear coefficients instead of calling Brightway in its
inner loop.

Every number in this module is listed in ``SOURCES.md`` alongside its
source and provenance grade (transcribed / derived / assumed).

Run from the project root with the ``brightway`` environment:

    python optimisation/baseline_grid.py
"""
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import bw2data as bd

import lca_helpers as H
from dashboard_config import DC_FOREGROUND_DB, DC_OPERATION_YEARS

DC_CODE = "dc_zhang_virginia_baseline_25y"

# Cached full-year outputs of the existing pipeline. Both are half-hourly and
# cover 2025-01-01 to 2025-12-29.
#
#   GRID_CSV  — written by 3.1.custom_grid_carbon_intensity_api.ipynb from the
#               NESO Carbon Intensity API, regional scope, region 13 (London),
#               resolved from WIND_LAT/WIND_LON. Its custom_electricity_score
#               column is kg CO2e per kWh delivered, already carrying
#               dashboard_config.MARKET_LOSS_SHARE.
#   PRICE_CSV — written by 5.prices.ipynb from Elexon BMRS Market Index Data,
#               provider APXMIDP (N2EXMIDP is the documented fallback).
GRID_CSV = ROOT / "custom_grid_lca_outputs" / (
    "custom_grid_lca_carbon_api_regional_auto_r13_cheap_"
    "2025-01-01T00-00-00T_to_T2025-12-29T00-00-00.csv"
)
PRICE_CSV = ROOT / "price_outputs" / (
    "elexon_market_index_clean_2025-01-01_00-00-00_->_2025-12-29_00-00-00.csv"
)
OUT_DIR = ROOT / "optimisation_outputs"

HOURS_PER_YEAR = 8760.0


def gwp_method():
    """IPCC 2021 GWP100, excluding the 'no LT' variant."""
    return next(
        m for m in bd.methods
        if m[1] == "IPCC 2021" and m[2] == "climate change"
        and "GWP100" in str(m) and "no LT" not in str(m)
    )


def decompose_data_centre(method):
    """Split the data centre into a fixed burden and its electricity demand.

    Returns (fixed_kgco2e_over_life, electricity_kwh_over_life, n_exchanges).
    Every electricity exchange is swept up, including the construction and
    demolition ones — together 0.006 % of the total, and GB-appropriate anyway
    once the facility is notionally sited in GB.
    """
    dc = bd.get_activity((DC_FOREGROUND_DB, DC_CODE))
    fixed, kwh, n = H.run_non_electricity_lca(dc, method)
    return dc, fixed, kwh, n


def load_grid_and_prices():
    """Half-hourly GB grid emission factor joined to the Elexon price."""
    grid = pd.read_csv(GRID_CSV, parse_dates=["datetime"])
    grid = grid.rename(columns={
        "datetime": "DATETIME",
        "custom_electricity_score": "grid_kgco2e_per_kwh",
    })
    keep = ["DATETIME", "grid_kgco2e_per_kwh", "carbon_intensity",
            "api_region_name", "WIND_perc", "GAS_perc"]
    grid = grid[[c for c in keep if c in grid.columns]]

    price = pd.read_csv(PRICE_CSV, parse_dates=["DATETIME"])
    price = price[["DATETIME", "price_GBP_per_MWh"]]

    df = grid.merge(price, on="DATETIME", how="inner").sort_values("DATETIME")
    df = df.dropna(subset=["grid_kgco2e_per_kwh", "price_GBP_per_MWh"])
    return df.reset_index(drop=True)


def slice_hours(df):
    """Slice duration read from the timestamps, not hardcoded."""
    diffs = df["DATETIME"].diff().dropna().dt.total_seconds() / 3600.0
    return float(diffs.median()) if len(diffs) else 0.5


def run():
    ei, bio, fg_db, _default_method = H.setup_brightway()
    method = gwp_method()
    print("Method:", method)

    dc, fixed_life, kwh_life, n_exc = decompose_data_centre(method)
    years = float(DC_OPERATION_YEARS)
    dc_power_kw = kwh_life / (years * HOURS_PER_YEAR)

    print()
    print("=" * 78)
    print("DATA CENTRE — decomposition")
    print("=" * 78)
    print(f"{'activity':<34}{dc['name']}")
    print(f"{'operating life':<34}{years:,.0f} y")
    print(f"{'electricity over life':<34}{kwh_life:>18,.0f} kWh   ({n_exc} exchanges)")
    print(f"{'flat continuous draw':<34}{dc_power_kw:>18,.0f} kW")
    print(f"{'fixed (non-electricity)':<34}{fixed_life/1e3:>18,.0f} t CO2e over life")
    print(f"{'  annualised':<34}{fixed_life/1e3/years:>18,.0f} t CO2e / y")

    df = load_grid_and_prices()
    dt_h = slice_hours(df)
    window_h = len(df) * dt_h
    scale_to_year = HOURS_PER_YEAR / window_h

    df["kwh"] = dc_power_kw * dt_h
    df["kgco2e"] = df["kwh"] * df["grid_kgco2e_per_kwh"]
    df["cost_gbp"] = df["kwh"] / 1000.0 * df["price_GBP_per_MWh"]

    kwh_window = df["kwh"].sum()
    op_t_window = df["kgco2e"].sum() / 1e3
    cost_window = df["cost_gbp"].sum()

    op_t_yr = op_t_window * scale_to_year
    cost_yr = cost_window * scale_to_year
    kwh_yr = kwh_window * scale_to_year
    emb_t_yr = fixed_life / 1e3 / years
    total_t_yr = op_t_yr + emb_t_yr

    ef_mean = df["grid_kgco2e_per_kwh"].mean()
    ef_load_wtd = df["kgco2e"].sum() / df["kwh"].sum()   # equal under flat load

    print()
    print("=" * 78)
    print(f"GB GRID — {df.DATETIME.min():%Y-%m-%d} to {df.DATETIME.max():%Y-%m-%d}"
          f"  ({len(df):,} slices x {dt_h:g} h = {window_h/24:,.0f} days)")
    print("=" * 78)
    region = df["api_region_name"].iloc[0] if "api_region_name" in df else "?"
    print(f"{'region':<34}{region}")
    print(f"{'grid factor, mean':<34}{ef_mean:>18.4f} kg CO2e/kWh")
    print(f"{'grid factor, min / max':<34}{df.grid_kgco2e_per_kwh.min():>9.4f} /"
          f"{df.grid_kgco2e_per_kwh.max():>8.4f} kg CO2e/kWh")
    print(f"{'wholesale price, mean':<34}{df.price_GBP_per_MWh.mean():>18.2f} GBP/MWh")
    print(f"{'  min / max':<34}{df.price_GBP_per_MWh.min():>9.2f} /"
          f"{df.price_GBP_per_MWh.max():>8.2f} GBP/MWh")

    print()
    print("=" * 78)
    print("BASELINE 1 — data centre on GB grid, flat 100 % load, annualised")
    print("=" * 78)
    print(f"{'electricity':<34}{kwh_yr/1e6:>18,.1f} GWh / y")
    print(f"{'operational emissions':<34}{op_t_yr:>18,.0f} t CO2e / y")
    print(f"{'embodied (amortised)':<34}{emb_t_yr:>18,.0f} t CO2e / y")
    print(f"{'TOTAL':<34}{total_t_yr:>18,.0f} t CO2e / y")
    print(f"{'  carbon intensity':<34}{total_t_yr*1e6/kwh_yr:>18,.0f} g CO2e / kWh IT")
    print(f"{'electricity cost':<34}{cost_yr/1e6:>18,.2f} MGBP / y")
    print(f"{'  effective price':<34}{cost_yr/(kwh_yr/1000):>18,.2f} GBP/MWh")

    # Reference: the same facility as authored, on US-SERC.
    serc = [a for a in ei if a["name"] == "market for electricity, medium voltage"
            and a["location"] == "US-SERC"][0]
    ef_serc = H.run_lca_score(serc, method)
    serc_t_yr = (fixed_life + kwh_life * ef_serc) / 1e3 / years
    print()
    print(f"{'reference: as-authored US-SERC':<34}{serc_t_yr:>18,.0f} t CO2e / y"
          f"   ({ef_serc:.4f} kg CO2e/kWh)")
    print(f"{'GB vs US-SERC':<34}{100*(total_t_yr/serc_t_yr - 1):>18,.1f} %")

    OUT_DIR.mkdir(exist_ok=True)
    slices_path = OUT_DIR / "baseline1_grid_slices_2025.csv"
    df.to_csv(slices_path, index=False)

    summary = pd.DataFrame([{
        "option": "1_grid_only_GB",
        "description": "Data centre on GB grid, flat 100% load, no on-site generation",
        "window_start": df.DATETIME.min(),
        "window_end": df.DATETIME.max(),
        "slices": len(df),
        "slice_hours": dt_h,
        "dc_power_kw": dc_power_kw,
        "dc_electricity_GWh_yr": kwh_yr / 1e6,
        "operational_tco2e_yr": op_t_yr,
        "embodied_tco2e_yr": emb_t_yr,
        "total_tco2e_yr": total_t_yr,
        "gco2e_per_kwh": total_t_yr * 1e6 / kwh_yr,
        "electricity_cost_MGBP_yr": cost_yr / 1e6,
        "effective_price_GBP_per_MWh": cost_yr / (kwh_yr / 1000),
        "grid_factor_mean_kgco2e_per_kwh": ef_mean,
        "reference_us_serc_tco2e_yr": serc_t_yr,
    }])
    summary_path = OUT_DIR / "option_summary.csv"
    summary.to_csv(summary_path, index=False)

    print()
    print("Wrote:")
    print(" ", slices_path.relative_to(ROOT))
    print(" ", summary_path.relative_to(ROOT))
    return summary


if __name__ == "__main__":
    run()
