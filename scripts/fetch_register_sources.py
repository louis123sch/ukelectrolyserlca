"""Fetch every portal dataset the substation register reads, by id, and stamp
each with the portal's own modified date (COST_PLAN §1.10 R1, 30 Oct 2026).

    python scripts/fetch_register_sources.py [--only key,key] [--force] [--list] [--dry-run]
                                             [--sources "<OneDrive>/DC optimiser/connection sources"]

Writes ``<sources>/3 DUoS/site-specific EHV charges/api/<key>.<csv|json|xlsx>``
and ``api/manifest.json`` — one entry per dataset: portal, dataset id, the
portal's modified date, when it was fetched, rows and bytes. A dataset whose
portal date has not moved since the last fetch is skipped (``--force``
refetches). The register builder reads the files through the manifest
(``build_substation_register.api_file``), so a rebuild after a fetch carries
each row's ``headroom_as_of`` from the portal, not from the day of the run.

Portals and keys (all in the gitignored ``.env``; never written here):
  UKPN_API_KEY, NPG_API_KEY, ENWL_API_KEY, SPEN_API_KEY  opendatasoft portals,
      header ``Authorization: Apikey <key>``; CSV export with a comma delimiter
  NGED_API_KEY  National Grid's CKAN (connecteddata.nationalgrid.co.uk),
      header ``Authorization: <key>`` on the catalogue and the download
  (none)        SSEN's CKAN (ckan-prod.sse.datopian.com) needs no key
A company whose key is missing is skipped with a message, not an error.

What is *not* fetched here, and stays as the hand-pulled files of 29 Oct 2026
in the same folder: OpenStreetMap extracts (Overpass, slow and not a dataset),
SSEN's heatmap GeoJSONs and substation locations (their map application, not
the CKAN), NGED's CIM network models and LTDS tabular tables, and the DCUSA
models. Those are the name-and-location layer; the capacity layer is all here.
"""
from __future__ import annotations

import argparse
import datetime as dt
import io
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import requests

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCES = Path.home() / "OneDrive - Imperial College London" / "DC optimiser" / "connection sources"
UA = {"User-Agent": "ukdclca-research-fetch/1.0 (research; contact via repository)"}

ODS = {   # opendatasoft portals: company -> (base url, .env key name)
    "UKPN": ("https://ukpowernetworks.opendatasoft.com", "UKPN_API_KEY"),
    "NPG": ("https://northernpowergrid.opendatasoft.com", "NPG_API_KEY"),
    "ENWL": ("https://electricitynorthwest.opendatasoft.com", "ENWL_API_KEY"),
    "SPEN": ("https://spenergynetworks.opendatasoft.com", "SPEN_API_KEY"),
}
CKAN = {  # CKAN portals: company -> (base url, .env key name or None)
    "NGED": ("https://connecteddata.nationalgrid.co.uk", "NGED_API_KEY"),
    "SSEN": ("https://ckan-prod.sse.datopian.com", None),
}


@dataclass(frozen=True)
class Source:
    key: str            # file stem under api/, and the manifest key
    company: str        # UKPN, NPG, ENWL, SPEN, NGED, SSEN
    kind: str           # "ods" (CSV export), "ods_query" (records, paged), "ckan" (one resource)
    dataset: str        # opendatasoft dataset id, or CKAN package name
    used_for: str       # which plan step reads it
    resource: str | None = None     # CKAN: regex on the resource name
    params: dict = field(default_factory=dict)  # ods: where/select/group_by
    ext: str = "csv"
    note: str = ""


SOURCES: list[Source] = [
    # --- UK Power Networks --------------------------------------------------
    Source("ukpn_sites", "UKPN", "ods", "grid-and-primary-sites", "names and levels (builder)",
           note="every grid and primary site with its coordinates, type and voltage"),
    Source("ukpn_heatmap", "UKPN", "ods", "ukpn-capacity-heatmap", "R2 capacity",
           note="LTDS capacity heatmap: 967 primaries, firm capacity, maximum demand, available capacity, RAG"),
    Source("ukpn_grid_areas", "UKPN", "ods", "ukpn-grid-postcode-area", "R2 capacity",
           note="177 grid substations: winter/summer firm capacity, demand, RAG"),
    Source("ukpn_table3a", "UKPN", "ods", "ltds-table-3a-load-data-observed-transposed", "R2 capacity",
           note="LTDS Table 3a: firm capacity and observed peak per substation, season and year"),
    Source("ukpn_nshr", "UKPN", "ods", "ukpn-dfes-network-headroom-report", "R3 headroom by year",
           params={"where": 'category="Demand Headroom"'},
           note="Network Scenario Headroom Report: demand headroom MW by grid and primary substation, scenario and year"),
    Source("ukpn_table6", "UKPN", "ods", "ukpn-ltds-table-6-interest-connections", "R3 queue",
           note="LTDS Table 6: connection interest and offers by substation"),
    Source("ukpn_gsps", "UKPN", "ods", "ukpn-grid-supply-points", "R4 grid supply points (locations)",
           note="UKPN's grid supply points with their functional locations and supply areas (centroid as geo_point_2d)"),
    Source("ukpn_gsp_insights", "UKPN", "ods", "ukpn-gsp-insights", "R4 grid supply points",
           note="per grid supply point: GB peak, connection point peak, access period, by year"),
    # --- Northern Powergrid ---------------------------------------------------
    Source("npg_heatmap", "NPG", "ods", "ltds-capacity-heatmap", "R2 capacity, R4 (GSP rows)",
           note="LTDS capacity heatmap: 670 sites incl. 41 grid supply points; firm, maximum, contracted, available"),
    Source("npg_ehv_sites", "NPG", "ods", "ltds_ehv_sites", "names and levels (builder)"),
    Source("npg_ndp_headroom", "NPG", "ods", "npg_ndp_demand_headroom", "R3 headroom by year",
           note="Network Development Plan: demand headroom MW 2026-2050 by scenario, every BSP and primary"),
    Source("npg_table8", "NPG", "ods", "ltds-appendix-8", "R3 queue",
           note="LTDS Appendix 8: interest in connections by primary (demand kVA)"),
    # --- Electricity North West ----------------------------------------------
    Source("enwl_substations", "ENWL", "ods", "enwl-substation", "names and levels (builder)"),
    Source("enwl_ecr_1mw", "ENWL", "ods", "enwl-embedded-capacity-register-2-1mw-and-above", "names (builder)"),
    Source("enwl_ecr_sub1mw", "ENWL", "ods", "enwl-embedded-capacity-register-1-under-1mw", "names (builder)"),
    Source("enwl_pry_heatmap", "ENWL", "ods", "enwl-pry-heatmap", "R2 capacity"),
    Source("enwl_bsp_heatmap", "ENWL", "ods", "enwl-bsp-heatmap", "R2 capacity"),
    Source("enwl_gsp_heatmap", "ENWL", "ods", "enwl-gsp-heatmap", "R4 grid supply points",
           note="20 GSPs: connected, accepted, materiality headroom, awaiting assessment MW"),
    Source("enwl_ndp_headroom", "ENWL", "ods", "ndp-pry-bsp-headroom", "R3 headroom by year",
           note="firm and non-firm headroom MVA by primary and BSP, scenario and year"),
    # --- SP Energy Networks ----------------------------------------------------
    Source("spen_heatmap_spd", "SPEN", "ods", "distribution-capacity-heatmaps-spd", "R2 capacity",
           note="standard capacity heatmap, South Scotland: 390 primaries"),
    Source("spen_heatmap_spm", "SPEN", "ods", "distribution-capacity-heatmaps-spm", "R2 capacity",
           note="standard capacity heatmap, Manweb: 724 primaries + 147 BSPs"),
    Source("spen_gsp_overview", "SPEN", "ods", "gsp-overview", "R4 grid supply points",
           params={"where": 'level="GSP"',
                   "select": "substation, license, level, gsp_technical_import_limit_winter_mw, "
                             "gsp_technical_import_limit_summer_solar_max_mw, gsp_technical_import_limit_summer_solar_min_mw, "
                             "gsp_technical_export_limit_mw, td_boundary_capacity_notes, "
                             "transmission_reinforcement_expected_completion_date, associated_psps, count(*) as generator_rows",
                   "group_by": "substation, license, level, gsp_technical_import_limit_winter_mw, "
                               "gsp_technical_import_limit_summer_solar_max_mw, gsp_technical_import_limit_summer_solar_min_mw, "
                               "gsp_technical_export_limit_mw, td_boundary_capacity_notes, "
                               "transmission_reinforcement_expected_completion_date, associated_psps"},
           note="Single Digital View: technical import limits per GSP (the 247k generator rows collapsed to one per GSP)"),
    Source("spen_dg_spd_grid", "SPEN", "ods", "distributed-generation-sp-distribution-heat-maps-spd-grid-substations", "names (builder)"),
    Source("spen_dg_spd_primary", "SPEN", "ods", "distributed-generation-sp-distribution-heat-maps-spd-primary-substations", "names (builder)"),
    Source("spen_dg_spm_grid", "SPEN", "ods", "distributed-generation-sp-manweb-heat-maps-spm-grid-substations", "names (builder)"),
    Source("spen_dg_spm_primary", "SPEN", "ods", "distributed-generation-sp-manweb-heat-maps-spm-primary-substations", "names (builder)"),
    Source("spen_spd_codes", "SPEN", "ods", "spd-ltds-appendix-7-substation-abbreviation-codes-table-7", "names (builder)"),
    Source("spen_spm_fault_132", "SPEN", "ods", "spm-ltds-appendix-4-fault-levels-table-4-132kv-3ph", "names (builder)"),
    # --- National Grid Electricity Distribution --------------------------------
    Source("nged_nom", "NGED", "ckan", "network-opportunity-map-headroom", "R2 capacity, R3 contracted",
           resource=r"^Network Opportunity Map Headroom$",
           note="every primary and BSP: connected and contracted demand headroom MW with RAGs, coordinates"),
    Source("nged_demand_queue", "NGED", "ckan", "demand-data", "R3 queue", resource=r"^Demand Data$",
           note="every demand project above 1 MW: substation, voltage, import kW, status, dates"),
    Source("nged_heatmap_em", "NGED", "ckan", "ltds-capacity-heatmap", "R2 capacity (firm minus peak)",
           resource=r"East Midlands", ext="json"),
    Source("nged_heatmap_wm", "NGED", "ckan", "ltds-capacity-heatmap", "R2 capacity (firm minus peak)",
           resource=r"West Midlands", ext="json"),
    Source("nged_heatmap_sw", "NGED", "ckan", "ltds-capacity-heatmap", "R2 capacity (firm minus peak)",
           resource=r"South Wales", ext="json"),
    Source("nged_heatmap_swest", "NGED", "ckan", "ltds-capacity-heatmap", "R2 capacity (firm minus peak)",
           resource=r"South West", ext="json"),
    # --- SSEN -----------------------------------------------------------------
    Source("ssen_headroom_dashboard", "SSEN", "ckan", "generation-availability-and-network-capacity", "R2 capacity, R3 contracted, R4 GSPs",
           resource=r"^Headroom Dashboard Data", ext="csv",
           note="every SSEN primary, BSP and GSP: coordinates, nameplate ratings, observed demand, contracted demand "
                "(incl. BESS separately), estimated demand headroom, RAG, constraint, reinforcement works and dates"),
    Source("ssen_gsp_limits", "SSEN", "ckan", "technicallimits", "R4 grid supply points",
           resource=r"\(CSV\)", note="approved import and export limits per GSP, winter and summer"),
    Source("ssen_nshr_sepd", "SSEN", "ckan", "sepd_network_development_report", "R3 headroom by year",
           resource=r"^SEPD Network Scenario Headroom Report 2026$", ext="xlsx"),
    Source("ssen_nshr_shepd", "SSEN", "ckan", "shepd_network_development_report", "R3 headroom by year",
           resource=r"^SHEPD Network Scenario Headroom Report 2026$", ext="xlsx"),
    Source("ssen_queue", "SSEN", "ckan", "ssen-connections-reform-queue", "R3 queue",
           resource=r"^SSEN Connections Reform Queue$", ext="xlsx"),
]
BY_KEY = {s.key: s for s in SOURCES}
assert len(BY_KEY) == len(SOURCES), "duplicate source keys"


# =============================================================================
def api_dir(sources: Path) -> Path:
    return sources / "3 DUoS" / "site-specific EHV charges" / "api"


def load_keys() -> dict:
    """The portal keys from the environment or ``.env`` (never printed)."""
    try:
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")
    except ImportError:
        pass
    return {k: os.environ.get(k) for k in {v[1] for v in ODS.values()} | {v[1] for v in CKAN.values() if v[1]}}


def read_manifest(folder: Path) -> dict:
    p = folder / "manifest.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {}


def write_manifest(folder: Path, m: dict):
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "manifest.json").write_text(json.dumps(m, indent=1, sort_keys=True), encoding="utf-8")


def _get(url, headers, timeout=300, **kw):
    for attempt in range(3):
        try:
            r = requests.get(url, headers={**UA, **headers}, timeout=timeout, **kw)
            if r.status_code == 429:
                time.sleep(10 * (attempt + 1)); continue
            return r
        except requests.RequestException:
            if attempt == 2:
                raise
            time.sleep(5 * (attempt + 1))
    return r


# --- opendatasoft -------------------------------------------------------------
def ods_meta(base: str, key: str, dataset: str) -> dict:
    r = _get(f"{base}/api/explore/v2.1/catalog/datasets/{dataset}", {"Authorization": f"Apikey {key}"}, timeout=60)
    r.raise_for_status()
    m = r.json().get("metas", {}).get("default", {})
    return {"modified": str(m.get("modified") or "")[:10], "rows_portal": m.get("records_count"),
            "title": m.get("title"), "url": f"{base}/explore/dataset/{dataset}/"}


def ods_export(base: str, key: str, s: Source) -> bytes:
    params = {"delimiter": ",", "use_labels": "false", **s.params}
    r = _get(f"{base}/api/explore/v2.1/catalog/datasets/{s.dataset}/exports/csv", {"Authorization": f"Apikey {key}"},
             params=params, timeout=900)
    r.raise_for_status()
    return r.content


def ods_query(base: str, key: str, s: Source) -> bytes:
    """Paged ``records`` call (for a group_by that collapses a huge table) -> CSV bytes."""
    import csv
    rows, off = [], 0
    while True:
        r = _get(f"{base}/api/explore/v2.1/catalog/datasets/{s.dataset}/records", {"Authorization": f"Apikey {key}"},
                 params={**s.params, "limit": 100, "offset": off}, timeout=180)
        r.raise_for_status()
        js = r.json()
        page = js.get("results", [])
        rows += page
        off += 100
        # a group_by query reports no total_count: page until a short page
        if len(page) < 100 or (js.get("total_count") and off >= js["total_count"]):
            break
    buf = io.StringIO()
    if rows:
        w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    return buf.getvalue().encode("utf-8")


# --- CKAN -----------------------------------------------------------------------
def ckan_resource(base: str, key: str | None, s: Source) -> tuple[dict, dict]:
    h = {"Authorization": key} if key else {}
    r = _get(f"{base}/api/3/action/package_show", h, params={"id": s.dataset}, timeout=60)
    r.raise_for_status()
    pkg = r.json()["result"]
    hits = [x for x in pkg["resources"] if re.search(s.resource, str(x.get("name") or ""))]
    if s.ext:
        typed = [x for x in hits if str(x.get("format", "")).lower() == s.ext.lower()
                 or str(x.get("url", "")).lower().endswith("." + s.ext.lower())]
        hits = typed or hits
    if len(hits) != 1:
        raise LookupError(f"{s.key}: {len(hits)} resources match {s.resource!r} in {s.dataset}: "
                          f"{[x.get('name') for x in hits]}")
    res = hits[0]
    meta = {"modified": str(res.get("last_modified") or res.get("created") or pkg.get("metadata_modified") or "")[:10],
            "title": f"{pkg.get('title')} / {res.get('name')}", "url": res.get("url"),
            "package_modified": str(pkg.get("metadata_modified") or "")[:10]}
    return res, meta


def ckan_download(base: str, key: str | None, res: dict) -> bytes:
    h = {"Authorization": key} if key else {}
    r = _get(res["url"], h, timeout=900)
    r.raise_for_status()
    return r.content


# =============================================================================
def count_rows(data: bytes, ext: str) -> int | None:
    if ext == "csv":
        return max(0, data.count(b"\n") - 1)
    if ext == "json":
        try:
            js = json.loads(data)
            return len(js) if isinstance(js, list) else len(js.get("features", js.get("results", [])))
        except Exception:
            return None
    return None


def fetch(s: Source, keys: dict, folder: Path, manifest: dict, force: bool, dry: bool) -> str:
    """Fetch one source; returns a one-word status."""
    if s.kind in ("ods", "ods_query"):
        base, kname = ODS[s.company]
        key = keys.get(kname)
        if not key:
            return f"skipped (no {kname} in .env)"
        meta = ods_meta(base, key, s.dataset)
    else:
        base, kname = CKAN[s.company]
        key = keys.get(kname) if kname else None
        if kname and not key:
            return f"skipped (no {kname} in .env)"
        res, meta = ckan_resource(base, key, s)
    out = folder / f"{s.key}.{s.ext}"
    old = manifest.get(s.key, {})
    if not force and out.exists() and old.get("modified") == meta["modified"] and meta["modified"]:
        return f"unchanged ({meta['modified']})"
    if dry:
        return f"would fetch ({old.get('modified') or 'never'} -> {meta['modified']})"
    if s.kind == "ods":
        data = ods_export(base, key, s)
    elif s.kind == "ods_query":
        data = ods_query(base, key, s)
    else:
        data = ckan_download(base, key, res)
    folder.mkdir(parents=True, exist_ok=True)
    out.write_bytes(data)
    manifest[s.key] = {
        "company": s.company, "portal": base, "dataset": s.dataset, "resource": s.resource,
        "title": meta.get("title"), "url": meta.get("url"), "params": s.params or None,
        "modified": meta["modified"], "fetched": dt.date.today().isoformat(),
        "rows": count_rows(data, s.ext), "rows_portal": meta.get("rows_portal"), "bytes": len(data),
        "file": out.name, "used_for": s.used_for, "note": s.note,
    }
    write_manifest(folder, manifest)
    return f"fetched ({old.get('modified') or 'new'} -> {meta['modified']}, {len(data) / 1e6:.1f} MB)"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--sources", default=str(DEFAULT_SOURCES))
    ap.add_argument("--only", default=None, help="comma-separated source keys, or company names (UKPN,NGED,...)")
    ap.add_argument("--force", action="store_true", help="refetch even when the portal date has not moved")
    ap.add_argument("--dry-run", action="store_true", help="show what would be fetched")
    ap.add_argument("--list", action="store_true", help="list the sources and the manifest, fetch nothing")
    a = ap.parse_args()
    folder = api_dir(Path(a.sources))
    manifest = read_manifest(folder)
    todo = SOURCES
    if a.only:
        sel = {x.strip() for x in a.only.split(",")}
        todo = [s for s in SOURCES if s.key in sel or s.company in sel]
        unknown = sel - {s.key for s in SOURCES} - {s.company for s in SOURCES}
        if unknown:
            print(f"unknown --only names: {sorted(unknown)}"); return 2
    if a.list:
        print(f"{'key':<22} {'company':<6} {'kind':<9} {'dataset':<58} {'portal date':<11} {'fetched':<11} rows")
        for s in todo:
            m = manifest.get(s.key, {})
            print(f"{s.key:<22} {s.company:<6} {s.kind:<9} {s.dataset[:58]:<58} {m.get('modified') or '-':<11} "
                  f"{m.get('fetched') or '-':<11} {m.get('rows') if m.get('rows') is not None else '-'}")
        return 0
    keys = load_keys()
    print(f"api folder: {folder}")
    bad = 0
    for s in todo:
        t0 = time.time()
        try:
            status = fetch(s, keys, folder, manifest, a.force, a.dry_run)
        except Exception as e:                       # keep going: one portal down must not block the rest
            status = f"FAILED {e!r}"[:160]; bad += 1
        print(f"  {s.key:<22} {s.company:<5} {status:<60} {time.time() - t0:5.1f} s")
    print(f"\n{len(todo)} sources, {bad} failed; manifest at {folder / 'manifest.json'}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
