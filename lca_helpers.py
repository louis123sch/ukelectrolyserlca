"""
=============================================================================
Shared LCA / Brightway helpers — used by every split notebook.
=============================================================================

All settings come from dashboard_config (the master dashboard). This module
contains every helper function from the original synthesis notebook with no
duplicates.

Typical use in a notebook:

    from dashboard_config import *
    import lca_helpers as H
    ei, bio, fg_db, method = H.setup_brightway()

After setup, helpers can be called with or without explicit Brightway handles
(they fall back to the module-level handles populated by setup_brightway()).
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import uuid
from io import StringIO
from pathlib import Path

import numpy as np
import pandas as pd

import bw2calc as bc
import bw2data as bd
import bw2io as bi

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None

import dashboard_config as cfg


# =============================================================================
# Module-level Brightway handles, populated by setup_brightway()
# =============================================================================
ei = None       # ecoinvent database
bio = None      # biosphere database
fg_db = None    # foreground database
method = None   # IPCC GWP100 method tuple


# =============================================================================
# Composite electricity definitions (shared by grid + wind/grid notebooks)
# =============================================================================
WIND_GROUP_WEIGHTS = {
    "WIND_GT3_ONSHORE": 0.006725107846 / 0.157504068947,
    "WIND_13_OFFSHORE": 0.05505783324  / 0.157504068947,
    "WIND_13_ONSHORE":  0.095721127861 / 0.157504068947,
}

IMPORT_GROUP_WEIGHTS = {
    "IMPORTS_FR": 0.050547023864 / 0.080275563773,
    "IMPORTS_IE": 0.005823079527 / 0.080275563773,
    "IMPORTS_NL": 0.023905460382 / 0.080275563773,
}

TECH_SPECS = {
    "GAS":              {"row_key": "GAS",      "query": "electricity production, natural gas, combined cycle GB"},
    "COAL":             {"row_key": "COAL",     "query": "electricity production, hard coal GB"},
    "NUCLEAR":          {"row_key": "NUCLEAR",  "query": "electricity production, nuclear GB"},
    "WIND_GT3_ONSHORE": {"row_key": "WIND",     "query": "electricity production, wind, >3MW turbine, onshore GB"},
    "WIND_13_OFFSHORE": {"row_key": "WIND",     "query": "electricity production, wind, 1-3MW turbine, offshore GB"},
    "WIND_13_ONSHORE":  {"row_key": "WIND",     "query": "electricity production, wind, 1-3MW turbine, onshore GB"},
    "WIND_EMB":         {"row_key": "WIND_EMB", "query": "electricity production, wind, <1MW turbine, onshore GB"},
    "HYDRO":            {"row_key": "HYDRO",    "query": "electricity production, hydro, run-of-river GB"},
    "IMPORTS_FR":       {"row_key": "IMPORTS",  "query": "import from FR"},
    "IMPORTS_IE":       {"row_key": "IMPORTS",  "query": "import from IE"},
    "IMPORTS_NL":       {"row_key": "IMPORTS",  "query": "import from NL"},
    "BIOMASS":          {"row_key": "BIOMASS",  "query": "electricity high voltage GB heat and power co-generation, wood chips, 6667 kW, state-of-the-art 2014"},
    "OTHER":            {"row_key": "OTHER",    "query": "electricity production, oil GB"},
    "SOLAR":            {"row_key": "SOLAR",    "query": "Electricity, low voltage GB electricity production, photovoltaic, 570kWp open ground installation, multi-Si"},
    "STORAGE":          {"row_key": "STORAGE",  "query": "electricity production, hydro, pumped storage GB"},
}

SIMPLE_TECH_KEYS = [
    "GAS", "COAL", "NUCLEAR", "WIND_EMB", "HYDRO",
    "BIOMASS", "OTHER", "SOLAR", "STORAGE",
]
WIND_COMPONENT_KEYS   = ["WIND_GT3_ONSHORE", "WIND_13_OFFSHORE", "WIND_13_ONSHORE"]
IMPORT_COMPONENT_KEYS = ["IMPORTS_FR", "IMPORTS_IE", "IMPORTS_NL"]

FUEL_COLS = [
    "GAS", "COAL", "NUCLEAR", "WIND", "WIND_EMB",
    "HYDRO", "IMPORTS", "BIOMASS", "OTHER", "SOLAR", "STORAGE",
]

# Foreground codes for each hydrogen process (used by every LCA notebook).
H2_CODES = {
    "SMR":            "smr_hermesmann_1kg_h2",
    "SMR-CCS":        "smr_ccs_hermesmann_1kg_h2",
    "AE operation":   "ae_op_hermesmann_1kg_h2",
    "PEM operation":  "pem_op_hermesmann_1kg_h2",
    "SOEC operation": "soec_op_hermesmann_1kg_h2",
    "MP-E":           "mp_e_1kg_h2",
}
ELECTROLYSER_CODES = {
    "AE operation":   "ae_op_hermesmann_1kg_h2",
    "PEM operation":  "pem_op_hermesmann_1kg_h2",
    "SOEC operation": "soec_op_hermesmann_1kg_h2",
}

TECH_COLOURS = {
    "SMR":            "#e07b39",
    "SMR-CCS":        "#a3c4bc",
    "AE operation":   "#4c72b0",
    "PEM operation":  "#55a868",
    "SOEC operation": "#c44e52",
    "MP-E":           "#8172b2",
}


# =============================================================================
# Brightway project setup
# =============================================================================
def find_database_name(must_contain, prefer=None):
    """Find a Brightway database name containing all the given substrings."""
    names = [str(x) for x in bd.databases]
    must_contain_l = [s.lower() for s in must_contain]
    matches = [n for n in names if all(s in n.lower() for s in must_contain_l)]
    if prefer:
        pref_l = prefer.lower()
        preferred = [m for m in matches if pref_l in m.lower()]
        if preferred:
            return preferred[0]
    if not matches:
        raise ValueError(f"No database found containing: {must_contain}. Available: {names}")
    return matches[0]


def _select_gwp_method():
    """Pick IPCC 2021 GWP100 if available, else any IPCC GWP/climate-change method."""
    gwp_methods = [
        m for m in bd.methods
        if "IPCC" in str(m) and ("GWP" in str(m) or "climate change" in str(m).lower())
    ]
    preferred = [
        m for m in gwp_methods
        if "2021" in str(m) and ("GWP100" in str(m).replace(" ", "") or "GWP 100" in str(m))
    ]
    if not gwp_methods:
        raise ValueError("No IPCC GWP/climate change method found in this Brightway project.")
    return preferred[0] if preferred else gwp_methods[0]


def setup_brightway():
    """Set the active project, find ecoinvent + biosphere + foreground + GWP method.

    Populates module-level globals ``ei``, ``bio``, ``fg_db``, ``method`` and
    returns them in that order. Safe to call from any notebook.
    """
    global ei, bio, fg_db, method

    bd.projects.set_current(cfg.PROJECT_NAME)
    print("Current Brightway project:", bd.projects.current)

    if cfg.RUN_IMPORT_ECOINVENT:
        from getpass import getpass
        username = input("ecoinvent username: ")
        password = getpass("ecoinvent password: ")
        bi.import_ecoinvent_release(
            version=cfg.ECOINVENT_VERSION,
            system_model=cfg.SYSTEM_MODEL,
            username=username,
            password=password,
        )

    ei_name  = find_database_name(["ecoinvent", cfg.SYSTEM_MODEL])
    bio_name = find_database_name(["biosphere"])

    ei  = bd.Database(ei_name)
    bio = bd.Database(bio_name)
    print("Using ecoinvent database:", ei_name)
    print("Using biosphere database:", bio_name)

    if cfg.FOREGROUND_DB in bd.databases:
        fg_db = bd.Database(cfg.FOREGROUND_DB)
        print("Using foreground database:", cfg.FOREGROUND_DB)
    elif cfg.RUN_BUILD_FOREGROUND_DATABASE:
        print("Foreground database will be created by the foreground notebook:", cfg.FOREGROUND_DB)
        fg_db = None
    else:
        raise ValueError(
            f"Foreground database {cfg.FOREGROUND_DB!r} was not found. "
            "Set RUN_BUILD_FOREGROUND_DATABASE=True in dashboard_config, or run the "
            "tech_lca_foreground notebook first."
        )

    method = _select_gwp_method()
    print("Using LCIA method:", method)

    return ei, bio, fg_db, method


def refresh_foreground():
    """Reload the foreground database handle after writing/recreating it."""
    global fg_db
    fg_db = bd.Database(cfg.FOREGROUND_DB)
    return fg_db


# =============================================================================
# Generic foreground discovery — lets the app work with any foreground
# database in the project (the built-in "hydrogen foreground" plus anything
# written by the AI-LCA extractor), not just the hardcoded H2_CODES map.
# =============================================================================
def list_foreground_databases():
    """Every database in the current project except ecoinvent/biosphere sources.

    These are candidate "foreground" databases: the built-in ``hydrogen
    foreground`` plus any database the AI-LCA paper extractor has written.
    """
    skip_markers = ("biosphere",) + tuple(s.lower() for s in [cfg.SYSTEM_MODEL, "ecoinvent"])
    names = []
    for name in bd.databases:
        low = str(name).lower()
        if any(marker in low for marker in skip_markers):
            continue
        names.append(str(name))
    return sorted(names)


def list_process_activities(db_name):
    """List process-type activities in ``db_name`` as plain dicts for UI display.

    Each row is annotated with ``has_electricity_input`` (from
    :func:`is_any_electricity_exchange`) so callers can flag which processes
    the grid/wind pipelines can actually swap electricity for.
    """
    db = bd.Database(db_name)
    rows = []
    for act in db:
        # bw2data 4.x tags ordinary activities "process" or "processwithreferenceproduct"
        # depending on how they were created; internal helper artifacts this app
        # creates itself (temp electricity-mix/wind-source activities) are left
        # untyped (type is None), so excluding None filters those out here.
        act_type = str(act.get("type") or "").lower()
        if "process" not in act_type:
            continue
        try:
            has_elec = any(is_any_electricity_exchange(exc) for exc in act.technosphere())
        except Exception:
            has_elec = False
        rows.append({
            "database": db_name,
            "code": act["code"],
            "name": act.get("name", ""),
            "reference_product": act.get("reference product", ""),
            "unit": act.get("unit", ""),
            "has_electricity_input": has_elec,
        })
    return sorted(rows, key=lambda r: r["name"])


def resolve_tech_activity(label, tech_source_overrides=None, foreground_db=None):
    """Resolve a technology label to a Brightway activity.

    Priority: an explicit ``(database, code)`` entry in
    ``tech_source_overrides`` (e.g. one built from the Setup-LCA page's
    foreground picker), then the built-in ``H2_CODES``/``ELECTROLYSER_CODES``
    lookup in ``foreground_db`` (defaults to ``cfg.FOREGROUND_DB``), which
    preserves every existing notebook's default behaviour unchanged.
    """
    overrides = tech_source_overrides or {}
    if label in overrides:
        db_name, code = overrides[label]
        return bd.get_activity((db_name, code))

    foreground_db = foreground_db or cfg.FOREGROUND_DB
    code = H2_CODES.get(label) or ELECTROLYSER_CODES.get(label)
    if code is None:
        raise ValueError(
            f"Unknown technology label {label!r}. Pass it via tech_source_overrides "
            "as {{label: (database_name, code)}}, or add it to H2_CODES/ELECTROLYSER_CODES."
        )
    return bd.get_activity((foreground_db, code))


# =============================================================================
# CSV loading and timeslice selection
# =============================================================================
def resolve_csv_path(csv_path=None):
    """Resolve the GB grid CSV from a few common locations."""
    csv_path = csv_path or cfg.CSV_PATH
    candidates = [
        Path(csv_path),
        Path.cwd() / csv_path,
        Path.cwd().parent / csv_path,
        Path("/mnt/data") / Path(csv_path).name,
    ]
    for p in candidates:
        if p.exists():
            return p
    raise FileNotFoundError(
        f"Could not find {csv_path!r}. Put it beside the notebooks or edit "
        "CSV_PATH in dashboard_config.py."
    )


def load_grid_csv(csv_path=None):
    """Load and lightly validate the National Grid ESO half-hourly CSV."""
    p = resolve_csv_path(csv_path)
    out = pd.read_csv(p)
    if "DATETIME" not in out.columns:
        raise ValueError("CSV must contain a DATETIME column.")
    out["DATETIME"] = pd.to_datetime(out["DATETIME"])
    out = out.sort_values("DATETIME").reset_index(drop=True)

    if "GENERATION" not in out.columns:
        present = [c for c in FUEL_COLS if c in out.columns]
        if not present:
            raise ValueError("CSV needs either GENERATION or fuel columns such as GAS/WIND/SOLAR.")
        out["GENERATION"] = out[present].sum(axis=1)

    for col in FUEL_COLS:
        if col in out.columns and col + "_perc" not in out.columns:
            out[col + "_perc"] = np.where(
                out["GENERATION"].astype(float) != 0,
                100.0 * out[col].astype(float) / out["GENERATION"].astype(float),
                0.0,
            )

    print(f"Loaded {len(out):,} rows from {p}")
    print(f"Date range: {out['DATETIME'].min()} → {out['DATETIME'].max()}")
    return out


# =============================================================================
# Seasonal wind-contribution helpers (representative-day selection)
# =============================================================================
_MONTH_TO_SEASON = {
    12: "Winter", 1: "Winter", 2: "Winter",
    3: "Spring", 4: "Spring", 5: "Spring",
    6: "Summer", 7: "Summer", 8: "Summer",
    9: "Autumn", 10: "Autumn", 11: "Autumn",
}
SEASON_ORDER = ["Winter", "Spring", "Summer", "Autumn"]
WIND_CONTRIBUTION_COLS = ["WIND", "WIND_EMB"]


def daily_wind_table(df, year=None, wind_cols=None):
    """Aggregate half-hourly rows to a daily wind-contribution table.

    Returns ``(daily, wind_cols)`` where ``daily`` is indexed by date and has
    columns ``wind`` (summed MW), ``gen`` (summed GENERATION), ``wind_pct``
    (100 * wind / gen) and ``season``.
    """
    wind_cols = [c for c in (wind_cols or WIND_CONTRIBUTION_COLS) if c in df.columns]
    if not wind_cols:
        raise ValueError(
            f"None of the wind columns {wind_cols or WIND_CONTRIBUTION_COLS} are in the CSV."
        )
    d = df.copy()
    d["DATETIME"] = pd.to_datetime(d["DATETIME"])
    if year is not None:
        d = d[d["DATETIME"].dt.year == int(year)]
    if d.empty:
        raise ValueError(f"No rows for year {year} in the CSV.")
    d["_DATE"] = d["DATETIME"].dt.normalize()
    g = d.groupby("_DATE")
    daily = pd.DataFrame({
        "wind": g[wind_cols].sum().sum(axis=1),
        "gen": g["GENERATION"].sum(),
    })
    daily["wind_pct"] = np.where(
        daily["gen"].astype(float) != 0,
        100.0 * daily["wind"] / daily["gen"],
        np.nan,
    )
    daily["season"] = daily.index.month.map(_MONTH_TO_SEASON)
    return daily, wind_cols


def seasonal_wind_summary(df, year, wind_cols=None, decile=0.10):
    """Per-season average / top-decile / bottom-decile wind days for one year.

    Returns ``(summary, daily)``. ``summary`` maps season -> dict with the
    seasonal average wind %, the representative (closest) day, and the same for
    the top/bottom ``decile`` buckets. ``daily`` is the table from
    :func:`daily_wind_table`.
    """
    daily, _ = daily_wind_table(df, year, wind_cols)

    def _closest(frame, target):
        idx = (frame["wind_pct"] - target).abs().idxmin()
        return pd.Timestamp(idx).normalize(), float(frame.loc[idx, "wind_pct"])

    summary = {}
    for season in SEASON_ORDER:
        s = (
            daily[daily["season"] == season]
            .dropna(subset=["wind_pct"])
            .sort_values("wind_pct")
        )
        if s.empty:
            continue
        n = len(s)
        avg = float(s["wind_pct"].mean())
        avg_day, avg_val = _closest(s, avg)
        k = max(1, int(np.ceil(n * decile)))
        bottom, top = s.head(k), s.tail(k)
        bot_avg, top_avg = float(bottom["wind_pct"].mean()), float(top["wind_pct"].mean())
        bot_day, bot_val = _closest(bottom, bot_avg)
        top_day, top_val = _closest(top, top_avg)
        summary[season] = {
            "n_days": n,
            "season_avg_pct": avg,
            "rep_day": avg_day, "rep_day_pct": avg_val,
            "top10_n": k, "top10_avg_pct": top_avg,
            "top10_rep_day": top_day, "top10_rep_day_pct": top_val,
            "bottom10_n": k, "bottom10_avg_pct": bot_avg,
            "bottom10_rep_day": bot_day, "bottom10_rep_day_pct": bot_val,
        }
    return summary, daily


def representative_wind_days(df, year, wind_cols=None, decile=0.10):
    """Flat list of the (up to) 12 representative wind days for one year.

    Three per season (average-wind, top-decile, bottom-decile). Each entry is a
    dict with ``date`` (normalised Timestamp), ``season``, ``kind`` and
    ``target_pct`` (the bucket average the day represents).
    """
    summary, _ = seasonal_wind_summary(df, year, wind_cols, decile)
    days = []
    for season in SEASON_ORDER:
        info = summary.get(season)
        if not info:
            continue
        days.append({"date": info["rep_day"], "season": season,
                     "kind": "avg", "target_pct": info["season_avg_pct"]})
        days.append({"date": info["top10_rep_day"], "season": season,
                     "kind": "top10", "target_pct": info["top10_avg_pct"]})
        days.append({"date": info["bottom10_rep_day"], "season": season,
                     "kind": "bottom10", "target_pct": info["bottom10_avg_pct"]})
    return days


def build_daily_average_rows(df, reps):
    """Return all half-hourly timeslices for each representative day, tagged by season/kind.

    For every day in ``reps`` (output of :func:`representative_wind_days`), returns
    all 48 half-hourly rows with columns preserved, and adds ``REP_SEASON`` / ``REP_KIND``
    tags. Returns a DataFrame of up to 48 rows per day (576 for 12 days).
    """
    d = df.copy()
    d["DATETIME"] = pd.to_datetime(d["DATETIME"])
    d["_DATE"] = d["DATETIME"].dt.normalize()
    rows = []
    for meta in reps:
        day = pd.Timestamp(meta["date"]).normalize()
        sub = d[d["_DATE"] == day].copy()
        if sub.empty:
            continue
        sub["REP_SEASON"] = meta["season"]
        sub["REP_KIND"] = meta["kind"]
        rows.append(sub)
    return pd.concat(rows, ignore_index=True).reset_index(drop=True) if rows else pd.DataFrame()


def select_grid_rows(df):
    """Return (run_rows, label) based on the grid-time mode from the dashboard."""
    if cfg.GRID_TIME_MODE == "single":
        target_dt = pd.Timestamp(cfg.GRID_SINGLE_DATETIME)
        idx = (df["DATETIME"] - target_dt).abs().idxmin()
        selected = df.loc[[idx]].copy().reset_index(drop=True)
        label = str(selected.iloc[0]["DATETIME"])
    elif cfg.GRID_TIME_MODE == "range":
        ts_start = pd.Timestamp(cfg.GRID_RANGE_START)
        ts_end   = pd.Timestamp(cfg.GRID_RANGE_END)
        if ts_end < ts_start:
            raise ValueError("GRID_RANGE_END must be >= GRID_RANGE_START")
        mask = (df["DATETIME"] >= ts_start) & (df["DATETIME"] <= ts_end)
        selected = df[mask].copy().reset_index(drop=True)
        if selected.empty:
            raise ValueError("No rows found in selected grid range. Check GRID_RANGE_START/GRID_RANGE_END.")
        label = f"{selected.iloc[0]['DATETIME']} -> {selected.iloc[-1]['DATETIME']}"
    elif cfg.GRID_TIME_MODE == "year_average":
        year = int(getattr(cfg, "GRID_YEAR", pd.Timestamp(cfg.GRID_SINGLE_DATETIME).year))
        reps = representative_wind_days(
            df, year,
            wind_cols=getattr(cfg, "GRID_WIND_COLS", None),
            decile=float(getattr(cfg, "GRID_REP_DECILE", 0.10)),
        )
        if not reps:
            raise ValueError(f"No representative wind days found for year {year}.")
        selected = build_daily_average_rows(df, reps)
        if selected.empty:
            raise ValueError(f"No rows found for the representative days in year {year}.")
        label = f"year{year}_representative_{len(selected)}days"
    else:
        raise ValueError("GRID_TIME_MODE must be 'single', 'range' or 'year_average'")
    return selected, label


# =============================================================================
# Candidate-lookup helpers
# =============================================================================
def show_candidates(query, database=None, max_results=100):
    """Print and return the first ``max_results`` ecoinvent search hits for ``query``."""
    database = database or ei
    results = list(database.search(query))[:max_results]
    for i, act in enumerate(results):
        print(
            f"  {i:>3} | name: {act.get('name')}"
            f" | ref: {act.get('reference product')}"
            f" | unit: {act.get('unit')}"
            f" | loc: {act.get('location')}"
        )
    return results


def pick_candidate(query, index=0, database=None, max_results=100):
    """Print candidates and return the one at ``index`` (raising if missing)."""
    database = database or ei
    results = show_candidates(query, database=database, max_results=max_results)
    if not results:
        raise ValueError(f"No candidates found for query: {query!r}")
    picked = results[index]
    print(f"\n  → Selected [{index}]: {picked.get('name')} | {picked.get('location')}")
    return picked


def show_biosphere_candidates(query, max_results=100):
    results = list(bio.search(query))[:max_results]
    for i, flow in enumerate(results):
        print(
            f"  {i:>3} | name: {flow.get('name')}"
            f" | unit: {flow.get('unit')}"
            f" | categories: {flow.get('categories')}"
        )
    return results


def pick_biosphere_candidate(query, index=0, max_results=100):
    results = show_biosphere_candidates(query, max_results=max_results)
    if not results:
        raise ValueError(f"No biosphere candidates found for query: {query}")
    picked = results[index]
    print("\nPicked:", picked)
    return picked


def get_candidate_pool(query, database=None, max_results=100):
    """Same search ordering as ``show_candidates`` — used for batch candidate selection."""
    database = database or ei
    return list(database.search(query))[:max_results]


def select_candidate_activities(csv_row, candidate_index_dict, tech_specs=None,
                                database=None, max_results=100):
    """Select ecoinvent activities for one CSV timeslice, skipping shares <= 0.

    ``candidate_index_dict`` is the {component_key: int} dict defined in the
    notebook (e.g. ``GRID_CANDIDATE_INDEX``).
    """
    tech_specs = tech_specs or TECH_SPECS
    if candidate_index_dict is None:
        raise ValueError("candidate_index_dict is required (e.g. GRID_CANDIDATE_INDEX from the notebook).")
    database = database or ei

    selected = {}
    for tech_key, spec in tech_specs.items():
        share = float(csv_row.get(spec["row_key"] + "_perc", 0) or 0)
        if share <= 0:
            continue
        pool = get_candidate_pool(spec["query"], database=database, max_results=max_results)
        idx = int(candidate_index_dict.get(tech_key, 0))
        if not pool:
            print(f"  ⚠ {tech_key:<18} no candidates for {spec['query']!r}")
            continue
        if idx >= len(pool):
            print(f"  ⚠ {tech_key:<18} candidate_index {idx} out of range ({len(pool)} candidates)")
            continue
        selected[tech_key] = pool[idx]
    return selected


def select_all_candidate_activities(candidate_index_dict, tech_specs=None,
                                    database=None, max_results=100):
    """Pick one ecoinvent process per TECH_SPECS entry, ignoring whether shares are zero."""
    tech_specs = tech_specs or TECH_SPECS
    if candidate_index_dict is None:
        raise ValueError("candidate_index_dict is required (e.g. GRID_CANDIDATE_INDEX from the notebook).")
    database = database or ei

    selected = {}
    for tech_key, spec in tech_specs.items():
        pool = get_candidate_pool(spec["query"], database=database, max_results=max_results)
        idx = int(candidate_index_dict.get(tech_key, 0))
        if not pool:
            print(f"  ⚠ {tech_key:<18} no candidates for {spec['query']!r}")
            continue
        if idx >= len(pool):
            print(f"  ⚠ {tech_key:<18} candidate_index {idx} out of range ({len(pool)} candidates)")
            continue
        selected[tech_key] = pool[idx]
    return selected


# =============================================================================
# Template-driven candidate display & resolution (foreground + grid notebooks)
# =============================================================================
def show_template_candidates(template, title="Template", database=None, max_results=100):
    """Print ecoinvent candidates for every {key: {query, candidate_index}} entry.

    ``template`` is a dict like:
        {"electricity": {"query": "market for electricity ...", "candidate_index": 19}, ...}
    Use this in the notebook (toggled by SHOW_*_ECOINVENT_CANDIDATES) so you
    can see the candidate list and edit indexes in-place.
    """
    database = database or ei
    print(f"\n{'=' * 70}\n  {title}\n{'=' * 70}")
    for key, spec in template.items():
        idx = int(spec.get("candidate_index", 0))
        print(f"\n{'─' * 70}")
        print(f"  {key}  —  query: {spec['query']!r}  (picked: candidate #{idx})")
        pool = get_candidate_pool(spec["query"], database=database, max_results=max_results)
        if not pool:
            print("  ⚠  no candidates")
            continue
        for i, act in enumerate(pool):
            marker = "  ←" if i == idx else ""
            print(f"  {i:>3} | {act.get('name')} | ref: {act.get('reference product')}"
                  f" | unit: {act.get('unit')} | loc: {act.get('location')}{marker}")
        if idx >= len(pool):
            print(f"  ⚠  candidate_index {idx} out of range ({len(pool)} candidates)")


def resolve_template(template, database=None, verbose=True, max_results=100):
    """Return a {key: ecoinvent activity} dict for a {key: {query, candidate_index}} template.

    Skips entries whose candidate_index is out of range and prints a warning.
    """
    database = database or ei
    out = {}
    for key, spec in template.items():
        idx = int(spec.get("candidate_index", 0))
        pool = get_candidate_pool(spec["query"], database=database, max_results=max_results)
        if not pool:
            print(f"  ⚠ {key:<22} no candidates for {spec['query']!r}")
            continue
        if idx >= len(pool):
            print(f"  ⚠ {key:<22} candidate_index {idx} out of range ({len(pool)})")
            continue
        out[key] = pool[idx]
        if verbose:
            act = pool[idx]
            print(f"  {key:<22} → {act.get('name')} | {act.get('location')} | unit: {act.get('unit')}")
    return out


def show_biosphere_template_candidates(template, title="Biosphere template", max_results=50):
    """Print biosphere candidates for every {key: {query, candidate_index, categories?}} entry."""
    print(f"\n{'=' * 70}\n  {title}\n{'=' * 70}")
    for key, spec in template.items():
        idx = int(spec.get("candidate_index", 0))
        cats = spec.get("categories")
        print(f"\n{'─' * 70}")
        print(f"  {key}  —  query: {spec['query']!r}  (picked: #{idx})  categories filter: {cats}")
        results = list(bio.search(spec["query"]))[:max_results]
        results = filter_biosphere(results, spec)
        if not results:
            print("  ⚠  no biosphere flows")
            continue
        for i, flow in enumerate(results):
            marker = "  ←" if i == idx else ""
            print(f"  {i:>3} | {flow.get('name')} | unit: {flow.get('unit')}"
                  f" | categories: {flow.get('categories')}{marker}")


def resolve_biosphere_template(template, max_results=50, verbose=True):
    """Return a {key: biosphere flow} dict for a {key: {query, candidate_index, ...}} template.

    Entries with ``required: True`` raise if not found; others are returned as None.
    """
    out = {}
    for key, spec in template.items():
        flow = _resolve_biosphere_flow(
            query=spec["query"],
            categories=spec.get("categories"),
            candidate_index=int(spec.get("candidate_index", 0)),
            max_results=int(spec.get("max_results", max_results)),
        )
        if flow is None:
            if spec.get("required"):
                raise ValueError(f"Required biosphere flow {key!r} not found for query {spec['query']!r}.")
            if verbose:
                print(f"  {key:<22} → (not found, optional — skipped)")
            out[key] = None
        else:
            out[key] = flow
            if verbose:
                print(f"  {key:<22} → {flow.get('name')} {tuple(flow.get('categories') or ())}")
    return out


# =============================================================================
# Filter helpers for grid infrastructure / biosphere candidate cells
# =============================================================================
def filter_pool(pool, spec):
    contains = spec.get("name_contains")
    if contains:
        needles = [contains] if isinstance(contains, str) else list(contains)
        pool = [a for a in pool if all(n.lower() in (a.get("name") or "").lower() for n in needles)]
    excludes = spec.get("name_excludes")
    if excludes:
        stop = [excludes] if isinstance(excludes, str) else list(excludes)
        pool = [a for a in pool if not any(s.lower() in (a.get("name") or "").lower() for s in stop)]
    return pool


def filter_biosphere(pool, spec):
    cats = spec.get("categories")
    if cats:
        prefix = tuple(cats)
        filtered = [f for f in pool if tuple(f.get("categories") or ())[: len(prefix)] == prefix]
        if filtered:
            return filtered
    return pool


def _resolve_biosphere_flow(query, categories=None, candidate_index=0, max_results=50):
    results = list(bio.search(query))[:max_results]
    if categories:
        wanted = tuple(categories)
        filtered = []
        for r in results:
            r_cats = r.get("categories") or ()
            if not isinstance(r_cats, tuple):
                r_cats = tuple(r_cats)
            if r_cats[: len(wanted)] == wanted:
                filtered.append(r)
        results = filtered or results
    if not results:
        return None
    idx = int(candidate_index)
    if idx >= len(results):
        return None
    return results[idx]


# =============================================================================
# Custom GB electricity activity builder
# =============================================================================
def build_custom_electricity_activity(csv_row, selected_processes, fg_database=None,
                                      infrastructure=None, emissions=None, verbose=True):
    """Build a custom GB electricity-mix foreground activity for one timeslice.

    ``infrastructure`` and ``emissions`` are the dicts defined at the top of
    the notebook (e.g. ``GRID_INFRASTRUCTURE`` / ``GRID_EMISSIONS``). Pass
    empty dicts to skip the constant non-energy inputs.
    """
    fg_database = fg_database or fg_db
    infrastructure = {} if infrastructure is None else infrastructure
    emissions = {} if emissions is None else emissions
    ts_label = str(csv_row["DATETIME"]).replace(" ", "T")
    activity_name = f"electricity market, GB custom mix ({ts_label})"
    activity_code = f"custom_gb_elec_mix_{ts_label}"

    for existing in [a for a in fg_database if a.get("code") == activity_code]:
        existing.delete()
        if verbose:
            print(f"Deleted previous version: {activity_name!r}")

    new_act = fg_database.new_activity(
        code=activity_code,
        name=activity_name,
        unit="kilowatt hour",
        location="GB",
        comment=(
            f"Custom GB electricity market from NESO data. Timestamp: {ts_label}. "
            f"Carbon intensity: {csv_row.get('CARBON_INTENSITY', 'n/a')} g CO2eq/kWh. "
            f"Voltage level intentionally ignored when used as electrolyser input."
        ),
    )
    new_act.save()
    new_act.new_exchange(input=new_act, amount=1.0, type="production", unit="kilowatt hour").save()

    if verbose:
        print(f"\nBuilding: {activity_name!r}")
        print(f"{'Technology':<22} {'Amount':>10}   Process")
        print("─" * 86)

    for tech_key in SIMPLE_TECH_KEYS:
        if tech_key not in selected_processes:
            continue
        spec = TECH_SPECS[tech_key]
        base = float(csv_row.get(spec["row_key"] + "_perc", 0) or 0) / 100.0
        amount = base * cfg.MARKET_LOSS_FACTOR
        if amount <= 0:
            continue
        activity = selected_processes[tech_key]
        new_act.new_exchange(
            input=activity, amount=amount, type="technosphere", unit="kilowatt hour",
            comment=f"{tech_key}: {amount:.6f} of the GB custom mix at {ts_label}, "
                    f"including {cfg.MARKET_LOSS_FACTOR:.12f} loss factor",
        ).save()
        if verbose:
            print(f"  {tech_key:<22} {amount:>10.6f}   {activity.get('name')} [{activity.get('location')}]")

    wind_total = float(csv_row.get("WIND_perc", 0) or 0) / 100.0
    if wind_total > 0:
        for tech_key in WIND_COMPONENT_KEYS:
            if tech_key not in selected_processes:
                continue
            amount = wind_total * WIND_GROUP_WEIGHTS[tech_key] * cfg.MARKET_LOSS_FACTOR
            activity = selected_processes[tech_key]
            new_act.new_exchange(
                input=activity, amount=amount, type="technosphere", unit="kilowatt hour",
                comment=f"WIND composite: {tech_key} at {ts_label}, loss factor {cfg.MARKET_LOSS_FACTOR:.12f}",
            ).save()
            if verbose:
                print(f"  {'WIND / ' + tech_key:<22} {amount:>10.6f}   "
                      f"{activity.get('name')} [{activity.get('location')}]")

    imports_total = float(csv_row.get("IMPORTS_perc", 0) or 0) / 100.0
    if imports_total > 0:
        for tech_key in IMPORT_COMPONENT_KEYS:
            if tech_key not in selected_processes:
                continue
            amount = imports_total * IMPORT_GROUP_WEIGHTS[tech_key] * cfg.MARKET_LOSS_FACTOR
            activity = selected_processes[tech_key]
            new_act.new_exchange(
                input=activity, amount=amount, type="technosphere", unit="kilowatt hour",
                comment=f"IMPORTS composite: {tech_key} at {ts_label}, loss factor {cfg.MARKET_LOSS_FACTOR:.12f}",
            ).save()
            if verbose:
                print(f"  {'IMPORTS / ' + tech_key:<22} {amount:>10.6f}   "
                      f"{activity.get('name')} [{activity.get('location')}]")

    if verbose:
        print(f"  {'LOSS FACTOR APPLIED':<22} {cfg.MARKET_LOSS_FACTOR:>10.6f}   "
              f"all generation/import exchanges multiplied")

    # Constant non-energy inputs from the notebook templates
    if infrastructure or emissions:
        if verbose:
            print(f"  {'NON-ENERGY INPUTS':<22} {'':>10}   (constant per kWh)")

    for infra_key, spec in infrastructure.items():
        amount = float(spec.get("amount", 0) or 0)
        if amount <= 0:
            continue
        pool = filter_pool(
            get_candidate_pool(spec["query"], database=ei,
                               max_results=int(spec.get("max_results", 100))),
            spec,
        )
        idx = int(spec.get("candidate_index", 0))
        if not pool:
            print(f"  ⚠ infra / {infra_key:<14} no candidate for {spec['query']!r}")
            continue
        if idx >= len(pool):
            print(f"  ⚠ infra / {infra_key:<14} candidate_index {idx} out of range ({len(pool)})")
            continue
        infra_act = pool[idx]
        new_act.new_exchange(
            input=infra_act, amount=amount, type="technosphere",
            unit=spec.get("unit", infra_act.get("unit", "")),
            comment=f"INFRASTRUCTURE: {infra_key} (constant per kWh)",
        ).save()
        if verbose:
            print(f"  {'infra / ' + infra_key:<22} {amount:>10.3e}   "
                  f"{infra_act.get('name')} [{infra_act.get('location')}]")

    for emis_key, spec in emissions.items():
        amount = float(spec.get("amount", 0) or 0)
        if amount <= 0:
            continue
        flow = _resolve_biosphere_flow(
            query=spec["query"],
            categories=spec.get("categories"),
            candidate_index=int(spec.get("candidate_index", 0)),
            max_results=int(spec.get("max_results", 50)),
        )
        if flow is None:
            print(f"  ⚠ emis  / {emis_key:<14} no biosphere flow for {spec['query']!r}")
            continue
        new_act.new_exchange(
            input=flow, amount=amount, type="biosphere",
            unit=spec.get("unit", flow.get("unit", "")),
            comment=f"DIRECT EMISSION: {emis_key} (constant per kWh)",
        ).save()
        if verbose:
            cats = flow.get("categories") or ()
            print(f"  {'emis  / ' + emis_key:<22} {amount:>10.3e}   "
                  f"{flow.get('name')} {tuple(cats)}")

    new_act.save()
    if verbose:
        print(f"\n✓ Activity created in '{cfg.FOREGROUND_DB}'")
    return new_act


def build_custom_grid_electricity_activity(csv_row, selected_processes, fg_database=None,
                                           infrastructure=None, emissions=None, verbose=False):
    """Verbose-toggling wrapper around build_custom_electricity_activity."""
    if verbose:
        return build_custom_electricity_activity(
            csv_row, selected_processes, fg_database,
            infrastructure=infrastructure, emissions=emissions, verbose=True,
        )
    with contextlib.redirect_stdout(io.StringIO()):
        return build_custom_electricity_activity(
            csv_row, selected_processes, fg_database,
            infrastructure=infrastructure, emissions=emissions, verbose=False,
        )


# =============================================================================
# LCA core helpers (single definition — no per-section duplicates)
# =============================================================================
def is_any_electricity_exchange(exc):
    """True for direct technosphere kWh exchanges whose input is electricity."""
    if exc["type"] != "technosphere":
        return False
    inp = exc.input
    name = (inp.get("name") or "").lower()
    ref = (inp.get("reference product") or "").lower()
    unit = (inp.get("unit") or exc.get("unit") or "").lower()
    return unit == "kilowatt hour" and ("electricity" in name or "electricity" in ref)


def preview_electricity_replacements(activity):
    matches = []
    for exc in activity.technosphere():
        if is_any_electricity_exchange(exc):
            inp = exc.input
            matches.append(exc)
            print(
                f"  TIME-VARYING: {exc['amount']} {exc.get('unit', inp.get('unit', '?'))}"
                f" | {inp.get('name')} [{inp.get('location')}]"
                f" | ref: {inp.get('reference product')}"
            )
    if not matches:
        print("  ⚠ No direct electricity exchanges found; this technology will be fixed over time.")
    return matches


def run_lca_score(activity, method_=None, amount=1.0):
    method_ = method_ or method
    try:
        fu, data_objs, _ = bd.prepare_lca_inputs({activity: amount}, method=method_)
        lca = bc.LCA(demand=fu, data_objs=data_objs)
    except Exception:
        lca = bc.LCA({activity: amount}, method_)
    lca.lci()
    lca.lcia()
    return float(lca.score)


def direct_electricity_kwh(activity):
    return sum(float(exc["amount"]) for exc in activity.technosphere()
               if is_any_electricity_exchange(exc))


def _new_temp_activity(code_prefix, activity, fg_database=None):
    fg_database = fg_database or fg_db
    temp_code = f"_tmp_{code_prefix}_{activity['code']}_{uuid.uuid4().hex[:8]}"[:240]
    for old in [a for a in fg_database if a.get("code") == temp_code]:
        old.delete()
    tmp = fg_database.new_activity(
        code=temp_code,
        name=f"[TEMP {code_prefix}] {activity['name']}",
        unit=activity.get("unit", "kilogram"),
        location=activity.get("location", "GLO"),
    )
    tmp.save()
    return tmp


def run_lca_with_custom_elec(activity, custom_elec_act, method_=None, fg_database=None):
    """Replace every direct electricity exchange with ``custom_elec_act`` and run LCA."""
    method_ = method_ or method
    tmp = _new_temp_activity("lca", activity, fg_database)
    substituted = 0
    try:
        for exc in activity.exchanges():
            if exc["type"] == "production":
                new_inp = tmp
            elif is_any_electricity_exchange(exc):
                new_inp = custom_elec_act
                substituted += 1
            else:
                new_inp = exc.input
            tmp.new_exchange(
                input=new_inp, amount=exc["amount"], type=exc["type"],
                unit=exc.get("unit", ""), comment=exc.get("comment", ""),
            ).save()
        score = run_lca_score(tmp, method_, amount=1.0)
    finally:
        try:
            tmp.delete()
        except Exception:
            pass
    return score, substituted


def run_non_electricity_lca(activity, method_=None, fg_database=None):
    """LCA of ``activity`` with direct electricity exchanges removed."""
    method_ = method_ or method
    tmp = _new_temp_activity("nonelec", activity, fg_database)
    removed_kwh = 0.0
    removed_count = 0
    try:
        for exc in list(activity.exchanges()):
            if exc["type"] == "production":
                new_input = tmp
            elif is_any_electricity_exchange(exc):
                removed_kwh += float(exc["amount"])
                removed_count += 1
                continue
            else:
                new_input = exc.input
            tmp.new_exchange(
                input=new_input, amount=exc["amount"], type=exc["type"],
                unit=exc.get("unit", ""), comment=exc.get("comment", ""),
            ).save()
        score = run_lca_score(tmp, method_, amount=1.0)
    finally:
        try:
            tmp.delete()
        except Exception:
            pass
    return score, removed_kwh, removed_count


def calculate_source_lca_scores(selected_generation_processes, method_=None):
    method_ = method_ or method
    scores = {}
    print("Electricity source scores, one-off Brightway LCAs")
    print("------------------------------------------------")
    for tech_key, act in selected_generation_processes.items():
        try:
            score = run_lca_score(act, method_, amount=1.0)
            scores[tech_key] = score
            print(f"  {tech_key:<18} {score:>12.6f} kg CO2eq/kWh | "
                  f"{act.get('name')} [{act.get('location')}]")
        except Exception as e:
            print(f"  ⚠ {tech_key:<18} failed ({type(e).__name__}: {e})")
    return scores


def custom_electricity_score_for_row(csv_row, source_scores):
    """Closed-form custom GB electricity score (kg CO2eq/kWh) for one row."""
    score = 0.0
    amount_sum = 0.0
    lf = cfg.MARKET_LOSS_FACTOR

    for tech_key in SIMPLE_TECH_KEYS:
        if tech_key not in source_scores:
            continue
        spec = TECH_SPECS[tech_key]
        share = float(csv_row.get(spec["row_key"] + "_perc", 0) or 0) / 100.0
        if share <= 0:
            continue
        amount = share * lf
        score += amount * source_scores[tech_key]
        amount_sum += amount

    wind_total = float(csv_row.get("WIND_perc", 0) or 0) / 100.0
    if wind_total > 0:
        for tech_key in WIND_COMPONENT_KEYS:
            if tech_key not in source_scores:
                continue
            amount = wind_total * WIND_GROUP_WEIGHTS[tech_key] * lf
            score += amount * source_scores[tech_key]
            amount_sum += amount

    imports_total = float(csv_row.get("IMPORTS_perc", 0) or 0) / 100.0
    if imports_total > 0:
        for tech_key in IMPORT_COMPONENT_KEYS:
            if tech_key not in source_scores:
                continue
            amount = imports_total * IMPORT_GROUP_WEIGHTS[tech_key] * lf
            score += amount * source_scores[tech_key]
            amount_sum += amount

    return score, amount_sum


def decompose_technology_scores(tech_activities, method_=None, fg_database=None):
    """For each H2 tech, compute fixed non-electricity score + direct electricity kWh."""
    method_ = method_ or method
    decomposition = {}
    print("Technology decomposition, one-off Brightway LCAs")
    print("------------------------------------------------")
    for label, act in tech_activities.items():
        print(f"\n{label}:")
        preview_electricity_replacements(act)
        non_elec_score, elec_kwh, n_sub = run_non_electricity_lca(act, method_, fg_database)
        decomposition[label] = {
            "non_electricity_score": non_elec_score,
            "electricity_kwh": elec_kwh,
            "n_elec_substitutions": n_sub,
        }
        print(f"  non-electricity score : {non_elec_score:.6f} kg CO2eq/kg H2")
        print(f"  direct electricity    : {elec_kwh:.6f} kWh/kg H2")
        print(f"  electricity exchanges : {n_sub}")
    return decomposition


# =============================================================================
# Wind/grid LCA helpers (used by the wind_power notebook)
# =============================================================================
def run_lca_with_split_electricity(activity, wind_elec_act, grid_elec_act,
                                   wind_fraction, grid_fraction, method_=None,
                                   temp_suffix="", fg_database=None):
    """Blended: split each direct electricity exchange into wind + grid fractions."""
    method_ = method_ or method
    fg_database = fg_database or fg_db

    wind_fraction = float(wind_fraction)
    grid_fraction = float(grid_fraction)
    if wind_fraction < -1e-9 or grid_fraction < -1e-9:
        raise ValueError("wind_fraction and grid_fraction must be non-negative.")
    if abs((wind_fraction + grid_fraction) - 1.0) > 1e-6:
        raise ValueError(f"wind+grid fractions must equal 1. Got {wind_fraction + grid_fraction}")

    suffix = temp_suffix.replace(" ", "_").replace(":", "-")
    temp_code = f"_tmp_blended_lca_{activity['code']}_{suffix}"[:240]
    for old in [a for a in fg_database if a.get("code") == temp_code]:
        old.delete()
    tmp = fg_database.new_activity(
        code=temp_code,
        name=f"[TEMP blended] {activity['name']}",
        unit=activity.get("unit", "kilogram"),
        location=activity.get("location", "GLO"),
    )
    tmp.save()

    split_count = 0
    total_direct_kwh = 0.0
    try:
        for exc in activity.exchanges():
            if exc["type"] == "production":
                tmp.new_exchange(
                    input=tmp, amount=exc["amount"], type=exc["type"],
                    unit=exc.get("unit", ""), comment=exc.get("comment", ""),
                ).save()
            elif is_any_electricity_exchange(exc):
                split_count += 1
                original = float(exc["amount"])
                total_direct_kwh += original
                if wind_fraction > 0:
                    tmp.new_exchange(
                        input=wind_elec_act, amount=original * wind_fraction,
                        type="technosphere", unit="kilowatt hour",
                        comment=f"Blended split: {wind_fraction:.6f} wind of {original:.6g} kWh.",
                    ).save()
                if grid_fraction > 0:
                    tmp.new_exchange(
                        input=grid_elec_act, amount=original * grid_fraction,
                        type="technosphere", unit="kilowatt hour",
                        comment=f"Blended split: {grid_fraction:.6f} grid of {original:.6g} kWh.",
                    ).save()
            else:
                tmp.new_exchange(
                    input=exc.input, amount=exc["amount"], type=exc["type"],
                    unit=exc.get("unit", ""), comment=exc.get("comment", ""),
                ).save()
        score = run_lca_score(tmp, method_, amount=1.0)
    finally:
        try:
            tmp.delete()
        except Exception:
            pass
    return score, split_count, total_direct_kwh


def run_lca_with_replacement_electricity(activity, replacement_elec_act,
                                         method_=None, temp_suffix="", fg_database=None):
    """Switching: fully replace each direct electricity exchange with one process."""
    method_ = method_ or method
    fg_database = fg_database or fg_db

    suffix = temp_suffix.replace(" ", "_").replace(":", "-")
    temp_code = f"_tmp_switching_lca_{activity['code']}_{suffix}"[:240]
    for old in [a for a in fg_database if a.get("code") == temp_code]:
        old.delete()
    tmp = fg_database.new_activity(
        code=temp_code,
        name=f"[TEMP switching] {activity['name']}",
        unit=activity.get("unit", "kilogram"),
        location=activity.get("location", "GLO"),
    )
    tmp.save()

    substituted = 0
    try:
        for exc in activity.exchanges():
            if exc["type"] == "production":
                new_input = tmp
            elif is_any_electricity_exchange(exc):
                new_input = replacement_elec_act
                substituted += 1
            else:
                new_input = exc.input
            tmp.new_exchange(
                input=new_input, amount=exc["amount"], type=exc["type"],
                unit=exc.get("unit", ""), comment=exc.get("comment", ""),
            ).save()
        score = run_lca_score(tmp, method_, amount=1.0)
    finally:
        try:
            tmp.delete()
        except Exception:
            pass
    return score, substituted


def build_wind_electricity_activity(wind_background_activity, fg_database=None):
    """Create the foreground wind electricity process (1 kWh from one wind background)."""
    fg_database = fg_database or fg_db
    activity_code = "direct_wind_electricity_1kwh"
    activity_name = "electricity, wind turbine source, wind/grid electrolyser"

    for existing in [a for a in fg_database if a.get("code") == activity_code]:
        existing.delete()

    wind_act = fg_database.new_activity(
        code=activity_code,
        name=activity_name,
        unit="kilowatt hour",
        location="GB",
        comment=(
            "Foreground wind electricity process for the wind/grid electrolyser model. "
            "Used for the wind fraction (blended) or full wind supply (switching) of the "
            "electrolyser electricity input."
        ),
    )
    wind_act.save()
    wind_act.new_exchange(input=wind_act, amount=1.0, type="production", unit="kilowatt hour").save()
    wind_act.new_exchange(
        input=wind_background_activity, amount=1.0, type="technosphere", unit="kilowatt hour",
        comment="1 kWh direct wind electricity from selected ecoinvent wind process.",
    ).save()
    wind_act.save()
    return wind_act


def align_wind_to_grid_timeslices(wind_df, grid_rows, method="ffill"):
    """Align hourly wind power onto half-hour grid rows; compute blended + switching cols."""
    target_index = pd.DatetimeIndex(pd.to_datetime(grid_rows["DATETIME"]))
    wind = wind_df["wind_power_kw"].copy()
    wind.index = pd.DatetimeIndex(pd.to_datetime(wind.index))
    if wind.index.tz is not None:
        wind.index = wind.index.tz_convert(None)

    combined_index = wind.index.union(target_index).sort_values()
    if method == "ffill":
        aligned = wind.reindex(combined_index).ffill().reindex(target_index)
    elif method == "linear":
        aligned = wind.reindex(combined_index).interpolate(method="time").reindex(target_index)
    else:
        raise ValueError("method must be 'ffill' or 'linear'")

    out = grid_rows.copy()
    out["wind_power_kw"]         = aligned.to_numpy()
    out["wind_power_mw"]         = out["wind_power_kw"] / 1000.0
    out["electrolyser_power_kw"] = cfg.ELECTROLYSER_CAPACITY_KW

    if out["wind_power_kw"].isna().any():
        missing = out[out["wind_power_kw"].isna()][["DATETIME"]]
        raise ValueError(
            "Some LCA timeslices did not receive wind power values. "
            "Check date coverage and timezones.\n"
            f"Missing rows:\n{missing.to_string(index=False)}"
        )

    out["wind_fraction"]    = (out["wind_power_kw"] / cfg.ELECTROLYSER_CAPACITY_KW).clip(0, 1)
    out["grid_fraction"]    = 1.0 - out["wind_fraction"]
    out["wind_used_kw"]     = out["wind_fraction"] * cfg.ELECTROLYSER_CAPACITY_KW
    out["grid_topup_kw"]    = out["grid_fraction"] * cfg.ELECTROLYSER_CAPACITY_KW
    out["surplus_wind_kw"]  = (out["wind_power_kw"] - cfg.ELECTROLYSER_CAPACITY_KW).clip(lower=0)

    if not np.allclose(out["wind_fraction"] + out["grid_fraction"], 1.0):
        raise ValueError("Wind and grid fractions do not sum to 1 for every slice.")

    out["minimum_required_wind_kw"] = cfg.MIN_WIND_POWER_KW
    out["wind_above_minimum"]       = out["wind_power_kw"] >= cfg.MIN_WIND_POWER_KW
    out["electricity_source"]       = np.where(out["wind_above_minimum"], "wind", "grid")
    return out


def fetch_ninja_wind(session, lat, lon, date_from, date_to, capacity_kw, height_m,
                     turbine, dataset="merra2",
                     api_base="https://www.renewables.ninja/api/"):
    """Fetch hourly wind power from the Renewables.ninja API (official-style)."""
    url = api_base + "data/wind"
    args = {
        "lat": lat, "lon": lon, "date_from": date_from, "date_to": date_to,
        "dataset": dataset, "capacity": capacity_kw, "height": height_m,
        "turbine": turbine, "format": "json",
    }
    r = session.get(url, params=args, timeout=180)
    print("Status:", r.status_code)
    print("URL:", r.url)
    if not r.ok:
        body_preview = (r.text or "")[:2000]
        print(body_preview)
        if r.status_code in (401, 403):
            raise RuntimeError(
                "Renewables.ninja authentication failed "
                f"(status {r.status_code}). "
                "Check your API token (or quota) and retry. "
                f"Response: {body_preview}"
            )
        raise RuntimeError(
            f"Renewables.ninja request failed with status {r.status_code}. "
            f"Response: {body_preview}"
        )

    parsed = json.loads(r.text)
    data = pd.read_json(StringIO(json.dumps(parsed["data"])), orient="index")
    metadata = parsed.get("metadata", {})

    data.index = pd.to_datetime(data.index)
    data.index.name = "time"
    if "electricity" in data.columns:
        data = data.rename(columns={"electricity": "wind_power_kw"})
    if "wind_power_kw" not in data.columns:
        raise ValueError(f"Expected 'electricity'/'wind_power_kw'; got {list(data.columns)}")
    data["wind_power_mw"]        = data["wind_power_kw"] / 1000.0
    data["wind_capacity_factor"] = data["wind_power_kw"] / float(capacity_kw)
    return data, metadata, args


def create_ninja_session(token=None):
    """Create an authenticated Renewables.ninja session.

    Token source priority: explicit argument, environment variable,
    then interactive prompt.
    """
    if requests is None:
        raise ImportError("The 'requests' package is required for the wind notebook.")

    from getpass import getpass

    token_source = "argument"
    if token is None:
        # Priority: dashboard_config setting → env var → interactive prompt.
        cfg_token = getattr(cfg, "NINJA_API_TOKEN", "") or ""
        if cfg_token.strip():
            token = cfg_token.strip()
            token_source = "dashboard_config"
        else:
            token = os.getenv("RENEWABLES_NINJA_TOKEN")
            token_source = "environment"

    if not token:
        token_source = "prompt"
        prompt_fn = getpass if cfg.USE_GETPASS else input
        try:
            token = prompt_fn("Paste your Renewables.ninja API token: ")
        except EOFError as exc:
            raise RuntimeError(
                "Could not read token interactively. "
                "Set NINJA_API_TOKEN in dashboard_config.py or set the "
                "RENEWABLES_NINJA_TOKEN environment variable."
            ) from exc

    token = str(token).strip()
    if token.lower().startswith("token "):
        token = token[6:].strip()
    if token.lower().startswith("bearer "):
        token = token[7:].strip()

    if not token:
        raise ValueError(
            "Renewables.ninja token is empty. Set RENEWABLES_NINJA_TOKEN or provide a token when prompted."
        )

    # Keep the token available for subsequent cells in the same kernel session.
    os.environ["RENEWABLES_NINJA_TOKEN"] = token

    session = requests.session()
    session.headers.update({"Authorization": "Token " + token})
    print(
        "Renewables.ninja session created.",
        f"Source: {token_source}; token length: {len(token)}"
    )
    return session


# =============================================================================
# Monte Carlo uncertainty analysis (non-electricity foreground exchanges)
# =============================================================================
# Uncertainty is scoped to a technology's own non-electricity exchanges (materials,
# infrastructure, direct emissions, ...), never the electricity exchange itself —
# the grid/wind pipelines already model electricity's own real-world variability via
# the Carbon Intensity API / Renewables.ninja timeseries, so mixing a second,
# independent uncertainty source onto the same exchange would double-count it.
# Deterministic base score + electricity contribution stay exactly as computed by
# the grid/wind notebooks; Monte Carlo only perturbs the non-electricity remainder.
def list_activity_exchanges(activity):
    """Non-production, non-electricity exchanges of ``activity``, for an uncertainty picker.

    Flags exchanges that already carry a Brightway/stats_arrays triangular
    distribution (uncertainty type 5) — e.g. written by the Add Foreground
    page/notebook 1 from a paper-stated range — so the UI can pre-fill from it.
    """
    rows = []
    for exc in activity.exchanges():
        if exc["type"] == "production" or is_any_electricity_exchange(exc):
            continue
        inp = exc.input
        rows.append({
            "name": inp.get("name", ""),
            "amount": float(exc["amount"]),
            "unit": exc.get("unit") or inp.get("unit", ""),
            "exchange_type": exc["type"],
            "has_uncertainty": exc.get("uncertainty type") == 5,
            "uncertainty_lower": exc.get("minimum"),
            "uncertainty_upper": exc.get("maximum"),
        })
    return rows


def run_monte_carlo_non_electricity(activity, uncertain_rows, n_iterations, method_=None,
                                     fg_database=None, seed=None):
    """Monte Carlo over ``activity``'s non-electricity exchanges using triangular uncertainty.

    ``uncertain_rows``: list of ``{"name": <exchange input name to match>, "lower": float,
    "mode": float, "upper": float}``. Rows whose name doesn't match any non-electricity
    exchange on ``activity`` are ignored. Matched exchanges use ``mode`` as their amount
    (overriding the activity's own value, so the table is the single source of truth for
    a run) with a stats_arrays TriangularUncertainty (type 5) distribution attached;
    unmatched exchanges keep their real deterministic amount.

    Uses Brightway's native Monte Carlo (``bc.LCA(..., use_distributions=True)``) — the
    same mechanism a written foreground activity's own stored uncertainty already works
    with, so behaviour is identical whether the range came from a paper extraction or was
    typed directly into the Setup LCA page.

    Returns ``(deterministic_non_electricity_score, samples)`` where ``samples`` is an
    ``(n_iterations,)`` numpy array. ``deterministic_non_electricity_score`` uses every
    row's ``mode`` with no randomness — callers combine it with the activity's already-
    computed electricity contribution to get a full deterministic anchor for the samples.
    """
    import numpy as np

    method_ = method_ or method
    fg_database = fg_database or fg_db
    by_name = {
        r["name"]: r for r in uncertain_rows
        if r.get("name") and r.get("lower") is not None and r.get("mode") is not None and r.get("upper") is not None
    }

    tmp = _new_temp_activity("mc", activity, fg_database)
    try:
        for exc in activity.exchanges():
            if exc["type"] == "production":
                tmp.new_exchange(input=tmp, amount=exc["amount"], type="production").save()
                continue
            if is_any_electricity_exchange(exc):
                continue
            spec = by_name.get(exc.input.get("name", ""))
            amount = float(spec["mode"]) if spec else exc["amount"]
            new_exc = tmp.new_exchange(
                input=exc.input, amount=amount, type=exc["type"],
                unit=exc.get("unit", ""), comment=exc.get("comment", ""),
            )
            if spec:
                new_exc["uncertainty type"] = 5
                new_exc["minimum"] = float(spec["lower"])
                new_exc["maximum"] = float(spec["upper"])
                new_exc["loc"] = amount
            new_exc.save()

        deterministic_score = run_lca_score(tmp, method_, amount=1.0)

        if not by_name:
            return deterministic_score, np.full(n_iterations, deterministic_score)

        fu, data_objs, _ = bd.prepare_lca_inputs({tmp: 1.0}, method=method_)
        mc_kwargs = {"demand": fu, "data_objs": data_objs, "use_distributions": True}
        if seed is not None:
            mc_kwargs["seed_override"] = seed
        lca = bc.LCA(**mc_kwargs)
        lca.lci()
        lca.lcia()
        samples = np.empty(n_iterations)
        for i in range(n_iterations):
            next(lca)
            samples[i] = lca.score
        return deterministic_score, samples
    finally:
        try:
            tmp.delete()
        except Exception:
            pass


# =============================================================================
# LCIA method search — for matching a paper's stated method (free text, e.g.
# "IPCC 2021 GWP100") to a real Brightway method tuple.
# =============================================================================
def find_methods(query, limit=10):
    """Keyword-search bd.methods, best match first.

    Every query word must appear somewhere in the method tuple for it to be
    considered at all; among those, shorter total tuple text (fewer extra
    sub-category qualifiers like "land use" or "no LT") ranks higher, so a
    plain "climate change" / "GWP100" match outranks a narrower sub-indicator
    that happens to contain the same words.
    """
    words = [w.lower() for w in str(query).split() if w]
    if not words:
        return []
    scored = []
    for m in bd.methods:
        text = " ".join(str(x) for x in m).lower()
        if not all(w in text for w in words):
            continue
        scored.append((sum(text.count(w) for w in words), -len(text), m))
    scored.sort(reverse=True)
    return [m for _, _, m in scored[:limit]]
