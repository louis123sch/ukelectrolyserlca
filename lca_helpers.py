"""
=============================================================================
Shared LCA / Brightway helpers — the Brightway project, the GB grid-mix
scoring used by ``optimisation/grid_build.py``, the LCA calls the coefficient
modules make, and the Renewables.ninja client ``profiles.py`` uses.
=============================================================================

Settings come from ``dc_config``. Typical use:

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

import dc_config as cfg


# =============================================================================
# Module-level Brightway handles, populated by setup_brightway()
# =============================================================================
ei = None       # ecoinvent database
bio = None      # biosphere database
fg_db = None    # foreground database
method = None   # IPCC GWP100 method tuple


# =============================================================================
# Composite GB electricity definitions (grid_build.py)
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

# Foreground codes for each hydrogen process.
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
            "Set RUN_BUILD_FOREGROUND_DATABASE=True in dc_config, or run the "
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


def get_candidate_pool(query, database=None, max_results=100):
    """Same search ordering as ``show_candidates`` — used for batch candidate selection."""
    database = database or ei
    return list(database.search(query))[:max_results]


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


# =============================================================================
# Renewables.ninja client (profiles.py)
# =============================================================================


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

    Token: the explicit argument, else ``RENEWABLES_NINJA_TOKEN`` from the
    environment or this repo's gitignored ``.env``.
    """
    if requests is None:
        raise ImportError("The 'requests' package is required for Renewables.ninja.")

    if token is None:
        try:
            from dotenv import load_dotenv
            load_dotenv(Path(__file__).with_name(".env"))
        except Exception:
            pass
        token = os.getenv("RENEWABLES_NINJA_TOKEN")
    if not token:
        raise RuntimeError(
            "No Renewables.ninja token. Put RENEWABLES_NINJA_TOKEN=... in .env "
            "at the repo root, or set it in the environment.")

    token = str(token).strip()
    if token.lower().startswith("token "):
        token = token[6:].strip()
    if token.lower().startswith("bearer "):
        token = token[7:].strip()

    if not token:
        raise ValueError("Renewables.ninja token is empty.")

    session = requests.session()
    session.headers.update({"Authorization": "Token " + token})
    return session


