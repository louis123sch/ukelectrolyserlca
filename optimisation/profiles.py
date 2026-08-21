"""
Time-series inputs for the sizing optimiser — wind, solar, grid, price.
=============================================================================

Everything the dispatch needs, on one half-hourly index, for a chosen location
and date range:

    wind_cf      capacity factor, Renewables.ninja, per kW installed
    solar_cf     capacity factor, Renewables.ninja PV, per kWp installed
    grid_kgco2e_per_kwh   half-hourly GB grid intensity
    price_GBP_per_MWh     half-hourly Elexon wholesale price

Renewables.ninja rate-limits aggressively, so every fetch is cached to disk
under ``optimisation_outputs/profile_cache/`` and keyed on its own arguments.
Deleting a cache file is the way to force a refetch.

Grid and price come from the CSVs the existing pipeline already writes
(``3.1.custom_grid_carbon_intensity_api.ipynb`` and ``5.prices.ipynb``) rather
than re-implementing those clients here. If the requested window is not
covered by what has been written, this module says so rather than silently
returning a shorter series.

Every number is listed in ``SOURCES.md`` alongside its provenance grade.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
CACHE_DIR = ROOT / "optimisation_outputs" / "profile_cache"
GRID_DIR = ROOT / "custom_grid_lca_outputs"
PRICE_DIR = ROOT / "price_outputs"

NINJA_BASE = "https://www.renewables.ninja/api/"
SLICE_MINUTES = 30


def _cache_path(kind: str, args: dict) -> Path:
    key = hashlib.sha1(json.dumps(args, sort_keys=True).encode()).hexdigest()[:16]
    return CACHE_DIR / f"{kind}_{key}.csv"


def _cached(kind: str, args: dict, fetch):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = _cache_path(kind, args)
    if path.exists():
        df = pd.read_csv(path, parse_dates=["time"]).set_index("time")
        return df, True
    df = fetch()
    df.to_csv(path, index_label="time")
    return df, False


def fetch_wind_cf(lat, lon, start, end, turbine="Vestas V90 2000",
                  hub_height_m=80.0, dataset="merra2", token=None):
    """Hourly onshore wind capacity factor at a site. Cached."""
    args = {"lat": round(float(lat), 4), "lon": round(float(lon), 4),
            "start": str(start), "end": str(end), "turbine": turbine,
            "height": float(hub_height_m), "dataset": dataset}

    def _fetch():
        import lca_helpers as H
        session = H.create_ninja_session(token)
        data, _meta, _a = H.fetch_ninja_wind(
            session=session, lat=lat, lon=lon, date_from=str(start),
            date_to=str(end), capacity_kw=1000.0, height_m=hub_height_m,
            turbine=turbine, dataset=dataset)
        return data[["wind_capacity_factor"]].rename(
            columns={"wind_capacity_factor": "wind_cf"})

    df, hit = _cached("wind", args, _fetch)
    return df, hit


def fetch_solar_cf(lat, lon, start, end, tilt=35.0, azim=180.0,
                   system_loss=0.10, tracking=0, dataset="merra2", token=None):
    """Hourly PV capacity factor at a site, per kWp. Cached.

    Renewables.ninja's PV endpoint, the counterpart to the wind one
    ``lca_helpers`` already wraps. Defaults are a fixed south-facing array at
    35 degrees, which is a conventional GB utility-scale choice.
    """
    args = {"lat": round(float(lat), 4), "lon": round(float(lon), 4),
            "start": str(start), "end": str(end), "tilt": float(tilt),
            "azim": float(azim), "loss": float(system_loss),
            "tracking": int(tracking), "dataset": dataset}

    def _fetch():
        import lca_helpers as H
        session = H.create_ninja_session(token)
        r = session.get(NINJA_BASE + "data/pv", timeout=180, params={
            "lat": lat, "lon": lon, "date_from": str(start), "date_to": str(end),
            "dataset": dataset, "capacity": 1.0, "system_loss": system_loss,
            "tracking": tracking, "tilt": tilt, "azim": azim, "format": "json"})
        if not r.ok:
            raise RuntimeError(
                f"Renewables.ninja PV request failed ({r.status_code}). "
                f"{(r.text or '')[:400]}")
        payload = r.json()
        data = pd.DataFrame.from_dict(payload["data"], orient="index")
        # The PV endpoint keys its data by epoch milliseconds where the wind
        # endpoint uses ISO strings, so accept either rather than assuming.
        idx = pd.Series(data.index.astype(str))
        if idx.str.fullmatch(r"\d{10,}").all():
            data.index = pd.to_datetime(idx.astype("int64"), unit="ms").values
        else:
            data.index = pd.to_datetime(data.index)
        data.index.name = "time"
        col = "electricity" if "electricity" in data.columns else data.columns[0]
        # capacity=1.0 kWp, so electricity is already the capacity factor
        return data[[col]].rename(columns={col: "solar_cf"})

    df, hit = _cached("solar", args, _fetch)
    return df, hit


def _best_covering(folder: Path, pattern: str, time_col: str, start, end):
    """Pick the written CSV that covers the requested window best.

    Newest-file-wins is the wrong rule here: the pipeline leaves behind runs of
    many different lengths, and a recent two-month run should not beat a full
    year when a full year was asked for. Files are ranked by how much of the
    requested window they actually contain.
    """
    lo, hi = pd.Timestamp(start), pd.Timestamp(end)
    best, best_rank, index = None, None, {}
    for path in folder.glob(pattern):
        try:
            times = pd.read_csv(path, usecols=[time_col],
                                parse_dates=[time_col])[time_col].sort_values()
        except Exception:
            continue
        if times.empty:
            continue
        covered = times[(times >= lo) & (times <= hi)]
        # A dispatch carries battery state between steps, so the series must be
        # chronological and evenly spaced. The pipeline also writes
        # "representative day" files, which are sampled, not contiguous - using
        # one here would silently teleport the battery across time gaps.
        gaps = covered.diff().dropna().dt.total_seconds() / 60.0
        # Real half-hourly series carry the odd API dropout - the 2025 grid
        # file has three, the largest 9 hours - so demanding perfection would
        # reject valid data. A sampled "representative days" file, by contrast,
        # jumps weeks at a time. Test for that shape instead.
        regular = float((gaps <= SLICE_MINUTES + 1).mean()) if len(gaps) else 0.0
        contiguous = bool(len(gaps)) and regular >= 0.98 and gaps.max() <= 24 * 60
        index[path.name] = (times.min(), times.max(), len(covered), contiguous)
        rank = (contiguous, len(covered))
        if best_rank is None or rank > best_rank:
            best, best_rank = path, rank
    if best is not None and best_rank is not None and not best_rank[0]:
        raise ValueError(
            f"No contiguous half-hourly series found in {folder.name} for "
            f"{lo:%Y-%m-%d}..{hi:%Y-%m-%d}. The closest match is sampled "
            "(a 'representative days' file), which cannot be used for a "
            "dispatch with battery state. Run the pipeline over a continuous "
            "date range first.\n  " + "\n  ".join(
                f"{n}: {a:%Y-%m-%d} to {b:%Y-%m-%d}, {c} slices in window, "
                f"{'contiguous' if k else 'SAMPLED'}"
                for n, (a, b, c, k) in sorted(index.items())))
    return best, index


def load_grid_and_price(start, end):
    """Half-hourly GB grid intensity and wholesale price for the window."""
    gpath, gindex = _best_covering(
        GRID_DIR, "custom_grid_lca_carbon_api_*.csv", "datetime", start, end)
    if gpath is None:
        raise FileNotFoundError(
            "No Carbon Intensity API output found in custom_grid_lca_outputs/. "
            "Run 3.1.custom_grid_carbon_intensity_api.ipynb (or the Setup LCA "
            "page) for the period you want first.")
    grid = pd.read_csv(gpath, parse_dates=["datetime"]).rename(
        columns={"datetime": "time",
                 "custom_electricity_score": "grid_kgco2e_per_kwh"})
    grid = grid[["time", "grid_kgco2e_per_kwh"]]

    ppath, _pindex = _best_covering(
        PRICE_DIR, "elexon_market_index_clean_*.csv", "DATETIME", start, end)
    if ppath is None:
        raise FileNotFoundError(
            "No Elexon price output found in price_outputs/. Run 5.prices.ipynb.")
    price = pd.read_csv(ppath, parse_dates=["DATETIME"]).rename(
        columns={"DATETIME": "time"})[["time", "price_GBP_per_MWh"]]

    df = grid.merge(price, on="time", how="inner").sort_values("time")
    df = df.dropna(subset=["grid_kgco2e_per_kwh", "price_GBP_per_MWh"])

    lo, hi = pd.Timestamp(start), pd.Timestamp(end)
    window = df[(df.time >= lo) & (df.time <= hi)]
    if window.empty:
        raise ValueError(
            f"No grid/price data between {lo:%Y-%m-%d} and {hi:%Y-%m-%d}. "
            f"Available: {df.time.min():%Y-%m-%d} to {df.time.max():%Y-%m-%d} "
            f"(from {gpath.name}).")
    coverage = (window.time.max() - window.time.min()).total_seconds() / 3600.0
    requested = (hi - lo).total_seconds() / 3600.0
    if requested > 0 and coverage < 0.95 * requested:
        raise ValueError(
            f"Grid/price data covers only {coverage/24:.0f} of the "
            f"{requested/24:.0f} days requested "
            f"({window.time.min():%Y-%m-%d} to {window.time.max():%Y-%m-%d}). "
            "Extend the run in notebook 3.1 / 5, or shorten the window.\n"
            "Grid files available:\n  " + "\n  ".join(
                f"{n}: {a:%Y-%m-%d} to {b:%Y-%m-%d}"
                for n, (a, b, _c, _k) in sorted(gindex.items())))
    return window.set_index("time"), gpath.name, ppath.name


def build(lat, lon, start, end, *, turbine="Vestas V90 2000",
          hub_height_m=80.0, tilt=35.0, azim=180.0, token=None):
    """Everything the dispatch needs, aligned on one half-hourly index.

    Renewables.ninja is hourly; the grid and price series are half-hourly. The
    hourly capacity factors are forward-filled onto the half-hourly index,
    matching ``lca_helpers.align_wind_to_grid_timeslices``'s default.
    """
    grid, gname, pname = load_grid_and_price(start, end)
    wind, wind_hit = fetch_wind_cf(lat, lon, start, end, turbine, hub_height_m,
                                   token=token)
    solar, solar_hit = fetch_solar_cf(lat, lon, start, end, tilt, azim,
                                      token=token)

    idx = grid.index
    out = grid.copy()
    for frame, col in ((wind, "wind_cf"), (solar, "solar_cf")):
        series = frame[col]
        series.index = pd.to_datetime(series.index).tz_localize(None)
        out[col] = series.reindex(idx.union(series.index)).ffill().reindex(idx)

    out = out.dropna(subset=["wind_cf", "solar_cf"])
    if out.empty:
        raise ValueError("Wind/solar and grid series do not overlap in time.")

    steps = pd.Series(out.index).diff().dropna().dt.total_seconds() / 60.0
    gap_slices = int(((steps - SLICE_MINUTES) / SLICE_MINUTES).clip(lower=0).sum())

    meta = {
        "grid_file": gname, "price_file": pname,
        "missing_slices": gap_slices,
        "largest_gap_hours": float(steps.max() / 60.0) if len(steps) else 0.0,
        "wind_cached": wind_hit, "solar_cached": solar_hit,
        "slices": len(out), "slice_hours": SLICE_MINUTES / 60.0,
        "start": out.index.min(), "end": out.index.max(),
        "mean_wind_cf": float(out.wind_cf.mean()),
        "mean_solar_cf": float(out.solar_cf.mean()),
        "mean_grid_kgco2e_per_kwh": float(out.grid_kgco2e_per_kwh.mean()),
        "mean_price_GBP_per_MWh": float(out.price_GBP_per_MWh.mean()),
    }
    return out, meta


if __name__ == "__main__":
    import dashboard_config as cfg
    df, meta = build(cfg.WIND_LAT, cfg.WIND_LON, "2025-01-01", "2025-03-31")
    print(json.dumps({k: (str(v) if isinstance(v, pd.Timestamp) else v)
                      for k, v in meta.items()}, indent=2))
    print(df.head())
