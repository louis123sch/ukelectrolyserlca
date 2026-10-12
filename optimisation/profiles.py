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

Grid and price come from the CSVs ``grid_build.py`` writes, rather than
fetching inside this module, so a window is built once and reused. If the requested window is not
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


def fetch_solar_cf(lat, lon, start, end, tilt=None, azim=None,
                   system_loss=None, tracking=None, dataset="merra2", token=None):
    """Hourly PV capacity factor at a site, per kWp. Cached.

    Renewables.ninja's PV endpoint, the counterpart to the wind one
    ``lca_helpers`` already wraps.

    The array geometry comes from ``dc_config`` rather than from this
    signature. It used to be four hard-coded defaults here — tilt 35, azimuth
    180, 10 % loss, no tracking — which ``dc_inputs.build_series`` never passed,
    so the data centre model silently took them and could not override them.
    They were also absent from ASSUMPTIONS.md, and 35 degrees was described here
    as "a conventional GB utility-scale choice", which it is not: GB
    utility-scale is 20-25 degrees, and 35 is closer to a domestic roof pitch.

    ``cfg.PV_TILT_DEG`` is 20 degrees, matching the pile-driven table whose
    embodied carbon ``renewables.py`` charges — so the plant being paid for and
    the plant being generated from are the same one. Tilt is part of the cache
    key, so changing it fetches fresh series rather than reusing the old ones.
    """
    import dc_config as cfg
    tilt = cfg.PV_TILT_DEG if tilt is None else tilt
    azim = cfg.PV_AZIMUTH_DEG if azim is None else azim
    system_loss = cfg.PV_SYSTEM_LOSS if system_loss is None else system_loss
    tracking = cfg.PV_TRACKING if tracking is None else tracking
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


def grid_file_is_utc(path: Path) -> bool:
    """Is this grid series on the UTC clock that price and weather use?

    Files written before the clock fix are London local time and carry no
    ``clock`` column. They are skipped rather than used, so a window that only
    they cover is rebuilt instead of being an hour out of step all summer.
    """
    try:
        head = pd.read_csv(path, nrows=1)
    except Exception:
        return False
    return "clock" in head.columns and str(head["clock"].iloc[0]) == "UTC"


def _series_index(folder: Path, pattern: str, time_col: str, start, end):
    """Every written CSV that matches, with how much of the window it holds.

    ``{name: (first, last, slices_in_window, contiguous)}``. Newest-file-wins is
    the wrong rule for picking between these: the pipeline leaves behind runs of
    many different lengths, and a recent two-month run should not beat a full
    year when a full year was asked for. So the choice is made on coverage of
    the requested window, by ``_best_covering`` below.
    """
    lo, hi = pd.Timestamp(start), pd.Timestamp(end)
    index = {}
    # Sorted, because the rank in _best_covering can tie and glob order is
    # filesystem order. Measured: for the June 2025 week both the full-year
    # Elexon export and the "576 representative days" export cover the window
    # with 337 contiguous slices, so the pair ties and whichever the filesystem
    # yielded first won. Their values are identical there, so nothing was wrong
    # — but which file a run used was not reproducible, and a future pair that
    # disagreed would be picked between silently.
    for path in sorted(folder.glob(pattern)):
        if folder == GRID_DIR and not grid_file_is_utc(path):
            continue
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
    return index


def describe_files(index: dict) -> str:
    """The available files, one per line, and what each one is for this window."""
    return "\n  ".join(
        f"{n}: {a:%Y-%m-%d} to {b:%Y-%m-%d}, {c} slices in window, "
        + ("contiguous" if k else "SAMPLED" if c else "no overlap with window")
        for n, (a, b, c, k) in sorted(index.items()))


def _best_covering(folder: Path, pattern: str, time_col: str, start, end):
    """Pick the written CSV that covers the requested window best.

    Returns ``(path, index)``, with ``path`` None when nothing written reaches
    into the window at all — a different problem from "the best match is
    sampled", and one the caller can fix by building the window. Those two used
    to be reported as the same thing, so a region whose only cached file was a
    different month was reported as a representative-days file: you went looking
    for a sampling problem that was not there. A sampled best match still raises
    here, because it would silently teleport the battery across time gaps.
    """
    index = _series_index(folder, pattern, time_col, start, end)
    reaching = {n: v for n, v in index.items() if v[2]}
    if not reaching:
        return None, index
    # Break a tie on total series length, preferring the broader export: a file
    # that also covers the rest of the year is a plain date-range run, while a
    # short one is more likely to be a sampled or partial artefact. Name last,
    # so the choice is fully determined.
    best = max(reaching, key=lambda n: (reaching[n][3], reaching[n][2],
                                        reaching[n][1] - reaching[n][0], n))
    if not reaching[best][3]:
        lo, hi = pd.Timestamp(start), pd.Timestamp(end)
        raise ValueError(
            f"No contiguous half-hourly series found in {folder.name} for "
            f"{lo:%Y-%m-%d}..{hi:%Y-%m-%d}. The closest match is sampled "
            "(a 'representative days' file), which cannot be used for a "
            "dispatch with battery state. Run the pipeline over a continuous "
            "date range first.\n  " + describe_files(index))
    return folder / best, index


def _build_hint(carbon_api_region, start, end) -> str:
    """The exact command that makes this window exist, dates and all."""
    region = carbon_api_region if carbon_api_region is not None else "<region>"
    return (
        f"\n\nBuild it:\n"
        f"    python -c \"from optimisation import sites; "
        f"sites.ensure_grid_series({region}, '{start}', '{end}')\"\n"
        "(or just run the optimiser: it builds a missing window itself). It scores "
        "the GB fuel mix against ecoinvent for every half-hour.")


def _autobuild(start, end, carbon_api_region, on_progress=None):
    if carbon_api_region is None:
        # Not a failure worth stopping a run over: without a region there is
        # nothing to build, and the loader's own error already says so if the
        # window turns out to be missing.
        return
    from optimisation import sites
    sites.ensure_grid_series(carbon_api_region, start, end,
                             on_progress=on_progress)


def grid_pattern_for(carbon_api_region: int | None) -> str:
    return ("custom_grid_lca_carbon_api_*.csv" if carbon_api_region is None
            else f"custom_grid_lca_carbon_api_*_r{carbon_api_region}_*.csv")


def window_status(start, end, *, carbon_api_region: int | None = None) -> dict:
    """What is on disk for this window, before anything commits to a run.

    ``{"grid_ok", "price_ok", "ok", "grid_file", "price_file", "grid_index",
    "price_index"}``. "Is there a file for this region" is not the question a
    caller needs answered — a region whose only cached series is one week of
    June is not ready for a January window, and answering the easy question is
    why that mismatch was only discovered by the run failing minutes later.
    The test here is the one ``load_grid_and_price`` applies: a contiguous
    series spanning at least 95 % of the window asked for.
    """
    out = {"grid_ok": False, "price_ok": False, "grid_file": None,
           "price_file": None, "grid_index": {}, "price_index": {}, "detail": ""}
    lo, hi = pd.Timestamp(start), pd.Timestamp(end)
    for key, folder, pattern, col in (
            ("grid", GRID_DIR, grid_pattern_for(carbon_api_region), "datetime"),
            ("price", PRICE_DIR, "elexon_market_index_clean_*.csv", "DATETIME")):
        index = _series_index(folder, pattern, col, start, end)
        out[f"{key}_index"] = index
        good = {n: v for n, v in index.items() if v[3]}
        if not good:
            continue
        name = max(good, key=lambda n: (good[n][2], good[n][1] - good[n][0], n))
        first, last, _slices, _k = good[name]
        span = (min(last, hi) - max(first, lo)).total_seconds()
        asked = (hi - lo).total_seconds()
        if asked <= 0 or span >= 0.95 * asked:
            out[f"{key}_ok"], out[f"{key}_file"] = True, name
    out["ok"] = out["grid_ok"] and out["price_ok"]
    missing = [k for k in ("grid", "price") if not out[f"{k}_ok"]]
    out["detail"] = (
        "" if not missing else
        f"{' and '.join(missing)} data does not cover "
        f"{lo:%Y-%m-%d}..{hi:%Y-%m-%d}")
    return out


def load_grid_and_price(start, end, *, carbon_api_region: int | None = None,
                        auto_build: bool = True, on_progress=None):
    """Half-hourly GB grid intensity and wholesale price for the window.

    ``carbon_api_region`` restricts the grid-file search to that region alone.
    Without it, ``_best_covering`` ranks purely on window coverage across
    *every* cached region and has no way to prefer the right one — harmless
    while only one region is ever cached, but once a second region is built
    the window-coverage tie between them is broken by glob order, not by
    which region the site is actually in. Regression: a Highland (region 1)
    site silently resolving to a Exeter (region 11) grid file once both were
    cached, caught only because ``sites.require_grid_region`` happened to be
    checking downstream — this parameter is the actual fix, that check is the
    net. Price is GB-wide, not regional, so it needs no such filter.

    ``auto_build`` builds the window instead of refusing it: it calls
    ``grid_build`` for this region and these dates, then re-reads. On by default — a window nobody has built yet is a wait, not
    an error, the same way wind and solar are already fetched on demand for
    whatever dates are asked for. It builds only what is actually missing, so
    the common case (a window already on disk) costs one directory listing.
    Pass ``auto_build=False`` for a caller that must not block.

    ``on_progress`` is called with a one-line description before anything slow
    starts, so a detached run can say what it is doing rather than going quiet.
    """
    grid_pattern = grid_pattern_for(carbon_api_region)
    if auto_build:
        _autobuild(start, end, carbon_api_region, on_progress)
    gpath, gindex = _best_covering(
        GRID_DIR, grid_pattern, "datetime", start, end)
    if gpath is None:
        lo, hi = pd.Timestamp(start), pd.Timestamp(end)
        region_bit = f" for region {carbon_api_region}" if carbon_api_region else ""
        raise FileNotFoundError(
            f"No Carbon Intensity API output covering {lo:%Y-%m-%d}..{hi:%Y-%m-%d}"
            f" in custom_grid_lca_outputs/{region_bit}."
            + _build_hint(carbon_api_region, start, end)
            + ("\nWhat is there:\n  " + describe_files(gindex) if gindex else ""))
    grid = pd.read_csv(gpath, parse_dates=["datetime"]).rename(
        columns={"datetime": "time",
                 "custom_electricity_score": "grid_kgco2e_per_kwh"})
    grid = grid[["time", "grid_kgco2e_per_kwh"]]

    ppath, _pindex = _best_covering(
        PRICE_DIR, "elexon_market_index_clean_*.csv", "DATETIME", start, end)
    if ppath is None:
        lo, hi = pd.Timestamp(start), pd.Timestamp(end)
        raise FileNotFoundError(
            f"No Elexon price output covering {lo:%Y-%m-%d}..{hi:%Y-%m-%d} in "
            f"price_outputs/."
            + _build_hint(carbon_api_region, start, end)
            + ("\nWhat is there:\n  " + describe_files(_pindex) if _pindex else ""))
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
            "Shorten the window, or build the rest of it."
            + _build_hint(carbon_api_region, start, end)
            + "\nGrid files available:\n  " + describe_files(gindex))
    return window.set_index("time"), gpath.name, ppath.name


def build(lat, lon, start, end, *, turbine="Vestas V90 2000",
          hub_height_m=80.0, tilt=None, azim=None, token=None,
          carbon_api_region: int | None = None, auto_build: bool = True,
          on_progress=None):
    """Everything the dispatch needs, aligned on one half-hourly index.

    Renewables.ninja is hourly; the grid and price series are half-hourly. The
    hourly capacity factors are forward-filled onto the half-hourly index.

    ``carbon_api_region`` should be passed by a caller that has already
    resolved a ``Site`` (it already paid for the lookup and knows the answer).
    Left unset, it is resolved here from ``lat, lon`` so a caller working from
    a raw coordinate still gets the right region's grid file rather than an
    arbitrary one — see ``load_grid_and_price``.

    ``auto_build`` is passed straight through, and defaults to on: build the
    window rather than refuse it. Wind and solar were already built on demand —
    Renewables.ninja is fetched for whatever dates are asked for and cached —
    so this is what makes the grid side behave the same way, for any window, at
    any GB coordinate.
    """
    if carbon_api_region is None:
        from optimisation import sites
        carbon_api_region = sites.resolve(lat, lon).carbon_api_region
    grid, gname, pname = load_grid_and_price(start, end,
                                             carbon_api_region=carbon_api_region,
                                             auto_build=auto_build,
                                             on_progress=on_progress)
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
    df, meta = build(51.5074, -0.1278, "2025-01-01", "2025-03-31")   # London
    print(json.dumps({k: (str(v) if isinstance(v, pd.Timestamp) else v)
                      for k, v in meta.items()}, indent=2))
    print(df.head())
