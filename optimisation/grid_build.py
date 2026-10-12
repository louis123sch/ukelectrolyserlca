"""
Grid and price series for a region and window — built in Python, on demand.
=============================================================================

The optimiser needs two half-hourly series for every run: grid carbon for the
site's Carbon Intensity region, and the GB wholesale price. ``profiles.py``
reads them from ``custom_grid_lca_outputs/`` and ``price_outputs/``; when a
window is missing, ``sites.ensure_grid_series`` calls this module to make it.

This replaces the notebook route (``1.dashboard_lca_adaptive`` → ``3.1`` →
``5.prices``, run through nbconvert after patching the config file on disk).
The science is unchanged — it is the same API calls, the same fuel-to-ecoinvent
mapping and the same closed-form score — but it now takes the region and dates
as arguments, so nothing on disk is edited to ask for a build.

Grid carbon, per half-hour
--------------------------
1. The Carbon Intensity API's regional endpoint gives the generation mix
   (% gas, wind, nuclear, imports, ...) for each half-hour. Its own
   ``intensity`` figure is kept as ``carbon_intensity`` for reference only:
   it counts direct combustion, not life cycle.
2. Each fuel maps to one ecoinvent GB electricity-production activity
   (``lca_helpers.TECH_SPECS``, picked by ``dc_config.GRID_CANDIDATE_INDEX``),
   scored once per build for GWP100. Those per-kWh scores are life cycle:
   plant construction, fuel supply chain and combustion. Wind and imports are
   split across sub-technologies by ``lca_helpers`` fixed weights.
3. ``custom_electricity_score`` = Σ share × (1 + market loss share) × score.
   That column is what the LP reads (``profiles.load_grid_and_price``).

Output file names and columns match what notebook 3.1 wrote, minus its
per-hydrogen-technology columns, so every series already on disk still reads.

Every series is UTC
--------------------
Grid, price (Elexon ``startTime``) and weather (Renewables.ninja) are all
stored as naive UTC timestamps, and a requested window is read as UTC. The
grid series used to be London local time, which put intraday carbon an hour
out of step with price and weather for seven months of the year. Files are
marked with a ``clock`` column; ``profiles.py`` ignores grid files without it,
so a series in the old basis is rebuilt rather than silently used. Anything
defined on the UK clock (DUoS time bands) converts from UTC itself.

Run:  python -m optimisation.grid_build 13 2025-06-02 2025-06-09
"""
from __future__ import annotations

import functools
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
GRID_DIR = ROOT / "custom_grid_lca_outputs"
PRICE_DIR = ROOT / "price_outputs"
API_CACHE_DIR = ROOT / "carbon_intensity_api_cache"

CARBON_API_BASE = "https://api.carbonintensity.org.uk"
CLOCK = "UTC"                             # written to every grid file; see above
CARBON_API_MAX_DAYS_PER_REQUEST = 13      # the API refuses longer ranges
CARBON_API_REQUEST_SLEEP_S = 0.05
CI_FUELS = ["gas", "coal", "biomass", "nuclear", "hydro", "imports", "other",
            "wind", "solar", "storage"]
# API fuel -> the row key lca_helpers.TECH_SPECS scores it under. Wind and
# imports are split into sub-technologies inside custom_electricity_score_for_row.
FUEL_TO_ROW_KEY = {"gas": "GAS", "coal": "COAL", "biomass": "BIOMASS",
                   "nuclear": "NUCLEAR", "hydro": "HYDRO", "imports": "IMPORTS",
                   "other": "OTHER", "wind": "WIND", "solar": "SOLAR",
                   "storage": "STORAGE"}

ELEXON_API_BASE = "https://data.elexon.co.uk/bmrs/api/v1"
ELEXON_PROVIDER = "APXMIDP"
ELEXON_FALLBACK_PROVIDER = "N2EXMIDP"
ELEXON_CHUNK_DAYS = 7
ELEXON_REQUEST_SLEEP_S = 0.15
ELEXON_TIMEOUT_S = 60

HTTP_ATTEMPTS = 3


# -----------------------------------------------------------------------------
# HTTP
# -----------------------------------------------------------------------------
def _get_json(url, params=None, timeout=45):
    """GET with a few retries. A dropped connection mid-build used to kill the
    notebook process and lose the window; retrying the one request is enough."""
    last = None
    for attempt in range(HTTP_ATTEMPTS):
        try:
            r = requests.get(url, params=params, timeout=timeout,
                             headers={"Accept": "application/json"})
            if r.status_code == 200:
                return r.json()
            last = RuntimeError(f"HTTP {r.status_code} from {r.url}: {r.text[:300]}")
            if r.status_code < 500 and r.status_code != 429:
                break                           # a client error will not improve
        except requests.RequestException as exc:
            last = exc
        time.sleep(2.0 * (attempt + 1))
    raise RuntimeError(f"GET {url} failed after {HTTP_ATTEMPTS} attempts: {last}")


def _carbon_api_get(endpoint: str):
    """Carbon Intensity API GET, cached on disk by endpoint.

    The cache key is the notebook's, byte for byte, so responses it saved are
    reused rather than fetched again.
    """
    API_CACHE_DIR.mkdir(exist_ok=True)
    digest = hashlib.sha256(endpoint.encode("utf-8")).hexdigest()[:24]
    safe = endpoint.strip("/").replace("/", "__").replace(":", "-")
    path = API_CACHE_DIR / f"{digest}_{safe}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    payload = _get_json(CARBON_API_BASE + endpoint)
    if isinstance(payload, dict) and payload.get("error"):
        raise RuntimeError(f"Carbon Intensity API error: {payload['error']}")
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    time.sleep(CARBON_API_REQUEST_SLEEP_S)
    return payload


# -----------------------------------------------------------------------------
# Time
# -----------------------------------------------------------------------------
def _utc(value) -> pd.Timestamp:
    """A naive datetime is UTC; return it tz-aware."""
    ts = pd.Timestamp(value)
    return ts.tz_convert("UTC") if ts.tzinfo is not None else ts.tz_localize("UTC")


def _api_z(ts: pd.Timestamp) -> str:
    return ts.tz_convert("UTC").strftime("%Y-%m-%dT%H:%MZ")


def _chunks(start, end_inclusive):
    """UTC request windows. ``end_inclusive`` is a half-hour start."""
    cur, stop = _utc(start), _utc(end_inclusive) + pd.Timedelta(minutes=30)
    step = pd.Timedelta(days=CARBON_API_MAX_DAYS_PER_REQUEST)
    while cur < stop:
        nxt = min(cur + step, stop)
        yield cur, nxt
        cur = nxt


def window_label(start, end) -> str:
    """``"<start> -> <end>"``, the label both output file names derive from."""
    return f"{start} -> {end}"


def grid_csv_name(region: int, start, end) -> str:
    safe = window_label(start, end).replace(" ", "T").replace(":", "-").replace("->", "_to_")
    return f"custom_grid_lca_carbon_api_regional_auto_r{int(region)}_cheap_{safe}.csv"


def price_csv_names(start, end) -> tuple[str, str]:
    """(raw, clean). Windows rejects < > : " / \\ | ? * in a filename outright,
    so "->" maps to "to" and the rest is a backstop."""
    safe = window_label(start, end).replace("->", "to").replace(" ", "_").replace(":", "-")
    for bad in r'<>:"/\|?*':
        safe = safe.replace(bad, "-")
    return (f"elexon_market_index_raw_{safe}.csv",
            f"elexon_market_index_clean_{safe}.csv")


# -----------------------------------------------------------------------------
# Carbon Intensity API -> generation mix
# -----------------------------------------------------------------------------
def _records(payload, region: int):
    """The half-hour records for ``region`` out of either response shape."""
    data = payload.get("data", []) if isinstance(payload, dict) else []
    if isinstance(data, dict):          # sometimes a bare region object
        data = [data]
    if not data:
        return [], None
    first = data[0]
    if isinstance(first, dict) and isinstance(first.get("data"), list):
        return first["data"], first.get("shortname")
    out, name = [], None                # per-timeslice shape, regions nested
    for ts in data:
        for reg in ts.get("regions", []) or []:
            if int(reg.get("regionid", -1)) == int(region):
                out.append({"from": ts.get("from"), "to": ts.get("to"),
                            "intensity": reg.get("intensity"),
                            "generationmix": reg.get("generationmix")})
                name = reg.get("shortname") or name
                break
    return out, name


def fetch_mix(region: int, start, end_inclusive) -> pd.DataFrame:
    """Half-hourly generation mix for one region, naive-UTC ``DATETIME``."""
    rows = []
    for lo, hi in _chunks(start, end_inclusive):
        payload = _carbon_api_get(
            f"/regional/intensity/{_api_z(lo)}/{_api_z(hi)}/regionid/{int(region)}")
        recs, name = _records(payload, region)
        for rec in recs:
            from_utc = pd.to_datetime(rec.get("from"), utc=True)
            row = {"DATETIME": from_utc.tz_localize(None),
                   "api_scope": "regional_auto", "api_region_id": int(region),
                   "api_region_name": name}
            for fuel in CI_FUELS:
                row[f"api_{fuel}"] = 0.0
            for item in rec.get("generationmix", []) or []:
                fuel = str(item.get("fuel", "")).strip().lower()
                if fuel:
                    row[f"api_{fuel}"] = float(item.get("perc", 0.0) or 0.0)
            intensity = rec.get("intensity") or {}
            row["carbon_intensity_forecast"] = intensity.get("forecast", np.nan)
            row["carbon_intensity_actual"] = intensity.get("actual", np.nan)
            row["carbon_intensity_index"] = intensity.get("index")
            rows.append(row)
    if not rows:
        raise RuntimeError(f"Carbon Intensity API returned nothing for region {region}, "
                           f"{start} to {end_inclusive}.")
    df = (pd.DataFrame(rows).drop_duplicates("DATETIME")
          .sort_values("DATETIME").reset_index(drop=True))
    lo = _utc(start).tz_localize(None)
    hi = _utc(end_inclusive).tz_localize(None)
    df = df[(df["DATETIME"] >= lo) & (df["DATETIME"] <= hi)].copy()
    if df.empty:
        raise RuntimeError("The API returned records, but none inside the requested window.")
    df["carbon_intensity"] = df["carbon_intensity_actual"].where(
        df["carbon_intensity_actual"].notna(), df["carbon_intensity_forecast"])
    df["api_total_perc"] = df[[f"api_{f}" for f in CI_FUELS]].sum(axis=1)
    return df


# -----------------------------------------------------------------------------
# Generation mix -> kg CO2e per kWh
# -----------------------------------------------------------------------------
@functools.lru_cache(maxsize=1)
def source_scores() -> dict:
    """GWP100 of 1 kWh from each GB generation source, from ecoinvent.

    One small LCA per source, once per process. Requires the Brightway project
    named in ``dc_config.PROJECT_NAME``.
    """
    import dc_config as cfg
    import lca_helpers as H
    _ei, _bio, _fg, method = H.setup_brightway()
    picked = H.select_all_candidate_activities(cfg.GRID_CANDIDATE_INDEX)
    return H.calculate_source_lca_scores(picked, method)


def score_mix(mix: pd.DataFrame, scores: dict | None = None) -> pd.DataFrame:
    """Add the ``*_perc`` share columns and the per-kWh score to a mix frame."""
    import lca_helpers as H
    scores = source_scores() if scores is None else scores
    df = mix.copy()
    for fuel, key in FUEL_TO_ROW_KEY.items():
        df[f"{key}_perc"] = df[f"api_{fuel}"].astype(float)
    df["WIND_EMB_perc"] = 0.0           # the API reports wind as one figure
    out = [H.custom_electricity_score_for_row(row, scores) for _, row in df.iterrows()]
    df["custom_electricity_score"] = [s for s, _ in out]
    df["custom_electricity_input_kwh_per_kwh"] = [a for _, a in out]
    return df


_GRID_COLUMNS = (
    ["datetime", "carbon_intensity", "custom_electricity_score",
     "custom_electricity_input_kwh_per_kwh", "api_scope", "api_region_id",
     "api_region_name", "api_total_perc", "carbon_intensity_forecast",
     "carbon_intensity_actual", "carbon_intensity_index"]
    + [f"api_{f}" for f in CI_FUELS])


def build_grid(region: int, start, end, out_dir: Path | None = None) -> Path:
    """Fetch, score and write the grid series for ``region`` over [start, end].

    ``start``/``end`` are UTC (``"YYYY-MM-DD HH:MM:SS"``), ``end`` inclusive
    at half-hour resolution. Returns the CSV path.
    """
    import lca_helpers as H
    out_dir = Path(out_dir) if out_dir else GRID_DIR
    t0 = time.time()
    mix = fetch_mix(region, start, end)
    print(f"  {len(mix)} half-hours of generation mix for region {region} "
          f"({mix['api_region_name'].iloc[0]}).")
    df = score_mix(mix)
    df = df.rename(columns={"DATETIME": "datetime"})
    cols = _GRID_COLUMNS + [f"{c}_perc" for c in H.FUEL_COLS]
    df = df[cols].copy()
    df["grid_data_source"] = "carbon_api"
    df["clock"] = CLOCK
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / grid_csv_name(region, start, end)
    df.to_csv(path, index=False)
    print(f"  wrote {path.name} — mean {df['custom_electricity_score'].mean()*1000:.0f} "
          f"g CO2e/kWh, {time.time() - t0:.0f} s")
    return path


# -----------------------------------------------------------------------------
# Elexon wholesale price
# -----------------------------------------------------------------------------
def _fetch_elexon(start, end, provider: str) -> pd.DataFrame:
    """Market Index Data in chunks. Naive times are UTC, like everything else."""
    lo = pd.Timestamp(start).tz_localize(None)
    hi = pd.Timestamp(end).tz_localize(None) + pd.Timedelta(minutes=30)
    chunks, cur = [], lo
    while cur <= hi:
        nxt = min(cur + pd.Timedelta(days=ELEXON_CHUNK_DAYS), hi)
        payload = _get_json(f"{ELEXON_API_BASE}/balancing/pricing/market-index",
                            params={"from": cur.strftime("%Y-%m-%dT%H:%MZ"),
                                    "to": nxt.strftime("%Y-%m-%dT%H:%MZ"),
                                    "dataProviders": provider, "format": "json"},
                            timeout=ELEXON_TIMEOUT_S)
        recs = payload.get("data", payload.get("items", [])) if isinstance(payload, dict) else payload
        if recs:
            c = pd.DataFrame(recs)
            c["requested_provider"] = provider
            chunks.append(c)
        cur = nxt + pd.Timedelta(minutes=30)
        time.sleep(ELEXON_REQUEST_SLEEP_S)
    return pd.concat(chunks, ignore_index=True).drop_duplicates() if chunks else pd.DataFrame()


def _first_col(df, names):
    lower = {c.lower(): c for c in df.columns}
    for n in names:
        if n in df.columns:
            return n
        if n.lower() in lower:
            return lower[n.lower()]
    return None


def normalise_elexon(raw: pd.DataFrame) -> pd.DataFrame:
    """Raw response -> ``DATETIME, provider, price_GBP_per_MWh, volume_MWh``."""
    cols = ["DATETIME", "provider", "price_GBP_per_MWh", "volume_MWh"]
    if raw.empty:
        return pd.DataFrame(columns=cols)
    df = raw.copy()
    pcol = _first_col(df, ["dataProvider", "data_provider", "provider", "requested_provider"])
    df["provider"] = df[pcol] if pcol else ELEXON_PROVIDER
    price = _first_col(df, ["price", "marketIndexPrice", "market_index_price", "value"])
    if price is None:
        raise ValueError(f"No Elexon price column. Columns: {list(df.columns)}")
    df["price_GBP_per_MWh"] = pd.to_numeric(df[price], errors="coerce")
    vol = _first_col(df, ["volume", "marketIndexVolume", "market_index_volume"])
    df["volume_MWh"] = pd.to_numeric(df[vol], errors="coerce") if vol else np.nan
    tcol = _first_col(df, ["startTime", "start_time", "datetime", "time", "timestamp"])
    if tcol is not None:
        dt = pd.to_datetime(df[tcol], errors="coerce", utc=True).dt.tz_convert(None)
    else:
        dcol = _first_col(df, ["settlementDate", "settlement_date"])
        scol = _first_col(df, ["settlementPeriod", "settlement_period"])
        if dcol is None or scol is None:
            raise ValueError(f"No Elexon time columns. Columns: {list(df.columns)}")
        # Settlement period 1 starts at UK midnight, so count from that instant
        # in UTC (clock-change days have 46 or 50 periods).
        midnight = (pd.to_datetime(df[dcol], errors="coerce").dt.tz_localize(None)
                    .dt.tz_localize("Europe/London").dt.tz_convert("UTC"))
        dt = (midnight + pd.to_timedelta((pd.to_numeric(df[scol], errors="coerce") - 1) * 30,
                                         unit="m")).dt.tz_localize(None)
    df["DATETIME"] = dt.dt.floor("30min")
    df = df.dropna(subset=["DATETIME", "price_GBP_per_MWh"])[cols]
    df = df.sort_values(["DATETIME", "provider"]).drop_duplicates(["DATETIME", "provider"], keep="last")
    return df.reset_index(drop=True)


def build_prices(start, end, out_dir: Path | None = None) -> Path:
    """Fetch and write GB Market Index prices over [start, end]. GB-wide, so
    one build serves every region. Returns the clean CSV path."""
    out_dir = Path(out_dir) if out_dir else PRICE_DIR
    raw = _fetch_elexon(start, end, ELEXON_PROVIDER)
    if raw.empty and ELEXON_FALLBACK_PROVIDER:
        print(f"  no {ELEXON_PROVIDER} records; trying {ELEXON_FALLBACK_PROVIDER}")
        raw = _fetch_elexon(start, end, ELEXON_FALLBACK_PROVIDER)
    clean = normalise_elexon(raw)
    if clean.empty:
        raise RuntimeError(f"Elexon returned no prices for {start} to {end}.")
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_name, clean_name = price_csv_names(start, end)
    raw.to_csv(out_dir / raw_name, index=False)
    clean.to_csv(out_dir / clean_name, index=False)
    print(f"  wrote {clean_name} — {len(clean)} half-hours, "
          f"mean £{clean['price_GBP_per_MWh'].mean():.1f}/MWh")
    return out_dir / clean_name


if __name__ == "__main__":
    region, lo, hi = int(sys.argv[1]), sys.argv[2], sys.argv[3]
    from optimisation import sites
    sites.ensure_grid_series(region, lo, hi)
