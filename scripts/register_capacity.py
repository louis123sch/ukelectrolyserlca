"""The register's capacity layer (COST_PLAN §1.10 R2-R4, 30 Oct 2026): each
company's standard capacity datasets, read from the files
``scripts/fetch_register_sources.py`` stamped, laid over the builder's
name-and-location layer.

Location plus headroom is the backbone (decision of 30 Oct 2026); a name is
used only to join a company's own datasets to its own site list, and a site
id (functional location, mRID, substation number) before a name wherever one
is published. Every capacity row carries:

    demand_headroom_mw           room for new demand today, as the company publishes it
    headroom_basis               what that figure is: "firm capacity minus maximum demand",
                                 "headroom on connected demand", ...
    headroom_as_of               the portal's modified date for the dataset it came from
    source_dataset               the portal dataset id
    firm_mva, max_demand_mw      the two the headroom is usually the difference of
    demand_contracted_mw         demand agreed but not yet connected, where published
    headroom_net_of_contracted_mw  room after what is agreed (NGED publish it; elsewhere derived)
    constraint                   the company's red/amber/green for demand

Three more tables come out of the same files: ``headroom_by_year`` (R3, the
companies' scenario headroom to 2050), ``connection_queue`` (R3, agreed and
energised demand connections by substation) and ``grid_supply_points`` (R4,
import limits and headroom at the transmission interface). The transmission
layer of ``substations.csv`` takes its capacity from the nearest grid supply
point record.
"""
from __future__ import annotations

import collections
import json
import math
import re
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

CAP_COLS = ["firm_mva", "max_demand_mw", "demand_headroom_mw", "demand_contracted_mw",
            "headroom_net_of_contracted_mw", "constraint", "headroom_basis", "headroom_as_of", "source_dataset"]
TEXT_COLS = ("constraint", "headroom_basis", "headroom_as_of", "source_dataset", "overlay")
MATCH_KM = 0.3          # a capacity row this close to a site row of the same level is the same substation
GSP_MATCH_KM = 3.0      # a 275/400 kV OpenStreetMap substation this close to a grid supply point record takes its capacity
UKPN_REGION = {"EPN": 10, "LPN": 13, "SPN": 14, "Eastern Power Networks (EPN)": 10,
               "London Power Networks (LPN)": 13, "South Eastern Power Networks (SPN)": 14}
NPG_REGION = {"NPgN": 4, "NPgY": 5, "Northeast": 4, "Yorkshire": 5}
NGED_REGION = {"East Midlands": 9, "West Midlands": 8, "South Wales": 7, "South West": 11}
# the companies' own central scenario, used where one headroom per year is wanted (ASSUMED choice)
CENTRAL_SCENARIO = {"UKPN": "Holistic Transition", "Northern Powergrid": "DFES 2026 - Holistic Transition",
                    "ENWL": "1 - BEST VIEW", "SSEN": "HT"}


# =============================================================================
# helpers
# =============================================================================
def _B():
    """The builder's name helpers (lazy: the builder imports this module)."""
    import sys
    root = Path(__file__).resolve().parent.parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from scripts import build_substation_register as B
    return B


def norm(s) -> str:
    return _B().norm(s)


def api_folder(src: Path) -> Path:
    return src / "3 DUoS" / "site-specific EHV charges" / "api"


def manifest(src: Path) -> dict:
    p = api_folder(src) / "manifest.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def api_file(src: Path, key: str) -> Path | None:
    m = manifest(src).get(key)
    if not m:
        return None
    p = api_folder(src) / m["file"]
    return p if p.exists() else None


def as_of(src: Path, key: str) -> str | None:
    m = manifest(src).get(key)
    return m["modified"] if m else None


def read_csv(src: Path, key: str, **kw) -> pd.DataFrame | None:
    p = api_file(src, key)
    if p is None:
        return None
    return pd.read_csv(p, encoding="utf-8-sig", low_memory=False, **kw)


def latlon(series: pd.Series) -> tuple[pd.Series, pd.Series]:
    """An opendatasoft geo point exported as "lat, lon" -> two float series."""
    parts = series.astype(str).str.extract(r"(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)")
    return pd.to_numeric(parts[0], errors="coerce"), pd.to_numeric(parts[1], errors="coerce")


def num(x) -> pd.Series:
    return pd.to_numeric(x, errors="coerce")


def os_gridref(ref: str) -> tuple[float, float]:
    """An Ordnance Survey grid reference ("SZ 04270 95141") -> easting, northing in metres."""
    s = re.sub(r"\s+", "", str(ref)).upper()
    m = re.match(r"^([HJNOST])([A-HJ-Z])(\d+)$", s)
    if not m or len(m.group(3)) % 2:
        return math.nan, math.nan
    a, b, digits = m.group(1), m.group(2), m.group(3)
    L = "ABCDEFGHJKLMNOPQRSTUVWXYZ"
    i, j = L.index(a), L.index(b)
    e100 = ((i - 2) % 5) * 5 + (j % 5)
    n100 = (19 - (i // 5) * 5) - (j // 5)
    half = len(digits) // 2
    scale = 10 ** (5 - half)
    return e100 * 100000 + int(digits[:half]) * scale, n100 * 100000 + int(digits[half:]) * scale


def gridref_to_latlon(ref) -> tuple[float, float]:
    e, n = os_gridref(ref)
    if not (math.isfinite(e) and math.isfinite(n)):
        return math.nan, math.nan
    return _B().bng_to_wgs84(e, n)


def _std_level(level) -> str | None:
    from optimisation import substations as S
    return S.level_of(level)


# =============================================================================
# capacity rows per company (standard columns; ``priority`` 1 is the preferred source)
# =============================================================================
def _rows(**cols) -> pd.DataFrame:
    d = pd.DataFrame(cols)
    for c in ["site_id", "name", "level", "lat", "lon"] + CAP_COLS:
        if c not in d:
            d[c] = np.nan
    return d


def ukpn_level_from_name(name) -> str | None:
    """UKPN names a grid site's sides by voltage ("Ipswich Grid 11kV", "Ipswich
    Grid 33kV"): the 33 kV side is the bulk supply point, the 11 kV side the
    132/11 kV grid site (whose board is a primary). A name that does not say
    "Grid" or "BSP" is left unlevelled (None: joined by name at any level, as
    London's "Aberdeen Pl B 11kV" is both a grid site and its board)."""
    n = str(name)
    if re.search(r"\bGRID\b|\bBSP\b", n, re.I):
        return _B().ukpn_level("Grid Substation", n)
    return None


def ukpn_capacity(src: Path) -> pd.DataFrame:
    out = []
    h = read_csv(src, "ukpn_heatmap")
    if h is not None:
        acc = num(h.get("loadconnectionoffersacceptedcapacity"))
        out.append(_rows(
            company="UKPN", region=h.area.map(UKPN_REGION), name=h["name"], level=h["type"],
            lat=num(h.latitude), lon=num(h.longitude), firm_mva=num(h.demandfirmcapacity),
            max_demand_mw=num(h.demandmaximum), demand_headroom_mw=num(h.demandavailablecapacity),
            demand_contracted_mw=acc, constraint=h.demandconstraint.astype(str).str.title(),
            headroom_basis="LTDS capacity heatmap: available demand capacity (firm capacity minus maximum demand); "
                           "contracted = connection offers accepted",
            headroom_as_of=as_of(src, "ukpn_heatmap"), source_dataset="ukpn-capacity-heatmap", priority=1))
    t = read_csv(src, "ukpn_table3a")
    if t is not None:
        t = t[(t.season == "Winter") & (t.year == "25-26")]
        firm, peak = num(t.firm_capacity_mw), num(t.maximum_demand_24_25_mw)
        out.append(_rows(
            company="UKPN", region=t.licencearea.map(UKPN_REGION), site_id=t.functional_location, name=t.substation,
            level=[ukpn_level_from_name(n) for n in t.substation],
            firm_mva=firm, max_demand_mw=peak, demand_headroom_mw=firm - peak,
            headroom_basis="LTDS Table 3a: firm capacity minus observed winter maximum demand 2024/25 "
                           "(a grid site's 11 kV and 33 kV sides are separate rows)",
            headroom_as_of=as_of(src, "ukpn_table3a"), source_dataset="ltds-table-3a-load-data-observed-transposed",
            priority=2))
    g = read_csv(src, "ukpn_grid_areas", usecols=lambda c: c != "geo_shape")
    if g is not None:
        g = g[g.grid_site_floc.notna()]
        lat, lon = latlon(g.geo_point_2d)
        firm, dem = num(g.firmcapacitywinter), num(g.demand)
        out.append(_rows(
            company="UKPN", region=g.dno.map(UKPN_REGION), site_id=g.grid_site_floc, name=g.grid_site,
            level=[ukpn_level_from_name(n) for n in g.grid_site],
            firm_mva=firm, max_demand_mw=dem, demand_headroom_mw=firm - dem,
            constraint=g.demandrag.astype(str).str.extract(r"^(\w+)")[0],
            headroom_basis="grid substation distribution areas: winter firm capacity minus demand",
            headroom_as_of=as_of(src, "ukpn_grid_areas"), source_dataset="ukpn-grid-postcode-area", priority=3))
    return pd.concat(out, ignore_index=True) if out else _rows()


def npg_capacity(src: Path) -> pd.DataFrame:
    h = read_csv(src, "npg_heatmap")
    if h is None:
        return _rows()
    head, contracted = num(h.demandavailablecapacity), num(h.demandcontractedcapacity)
    return _rows(
        company="Northern Powergrid", region=h.area.map(NPG_REGION), site_id=h.mrid, name=h["name"], level=h["type"],
        lat=num(h.latitude), lon=num(h.longitude), firm_mva=num(h.demandfirmcapacity), max_demand_mw=num(h.demandmaximum),
        demand_headroom_mw=head, demand_contracted_mw=contracted, headroom_net_of_contracted_mw=head - contracted,
        constraint=h.demandconstraint.astype(str).str.title(),
        headroom_basis="LTDS capacity heatmap: available demand capacity (firm capacity minus maximum demand); "
                       "contracted demand published",
        headroom_as_of=as_of(src, "npg_heatmap"), source_dataset="ltds-capacity-heatmap", priority=1)


def enwl_capacity(src: Path) -> pd.DataFrame:
    out = []
    for key, col in (("enwl_pry_heatmap", "pry_number"), ("enwl_bsp_heatmap", "bsp_number")):
        h = read_csv(src, key, usecols=lambda c: c != "geo_shape")
        if h is None:
            continue
        out.append(_rows(
            company="ENWL", region=3, site_id=h[col].astype(str), demand_headroom_mw=num(h.demand_headroom_firm_mw),
            headroom_basis="capacity heatmap: firm demand headroom (non-firm published separately)",
            headroom_as_of=as_of(src, key), source_dataset=key.replace("_", "-"), priority=1))
    return pd.concat(out, ignore_index=True) if out else _rows()


def spen_capacity(src: Path) -> pd.DataFrame:
    out = []
    for key, region in (("spen_heatmap_spd", 2), ("spen_heatmap_spm", 6)):
        h = read_csv(src, key)
        if h is None:
            continue
        lat = num(h["lat"]) if "lat" in h else num(h.latitude)
        lon = num(h["lon"]) if "lon" in h else num(h.longitude)
        name = h.site_name.fillna(h["name"]) if "site_name" in h else h["name"]
        acc = num(h["loadconnectionoffersacceptedcapacity"]) if "loadconnectionoffersacceptedcapacity" in h else np.nan
        out.append(_rows(
            company="SPEN", region=region, name=name, level=h["type"], lat=lat, lon=lon,
            firm_mva=num(h.demandfirmcapacity), max_demand_mw=num(h.demandmaximum),
            demand_headroom_mw=num(h.demandavailablecapacity), demand_contracted_mw=acc,
            constraint=h.demandconstraint.astype(str).str.title(),
            headroom_basis="capacity heatmap: available demand capacity (firm capacity minus maximum demand); "
                           "contracted = connection offers accepted",
            headroom_as_of=as_of(src, key), source_dataset=key.replace("_", "-").replace("spen-heatmap", "distribution-capacity-heatmaps"),
            priority=1))
    return pd.concat(out, ignore_index=True) if out else _rows()


def nged_capacity(src: Path) -> pd.DataFrame:
    out = []
    n = read_csv(src, "nged_nom")
    if n is not None:
        n = n[n["type"].isin(["Primary", "BSP"])]
        conn, contr = num(n.demandConnectedHeadroomMW), num(n.demandContractedHeadroomMW)
        out.append(_rows(
            company="NGED", region=n.area.map(NGED_REGION), site_id=n.substationNumber.astype(str), name=n["name"],
            level=n["type"], lat=num(n.latitude), lon=num(n.longitude),
            demand_headroom_mw=conn, demand_contracted_mw=conn - contr, headroom_net_of_contracted_mw=contr,
            constraint=n.demandConnectedRAG.astype(str).str.title(),
            headroom_basis="Network Opportunity Map: demand headroom on connected demand; net of contracted published",
            headroom_as_of=as_of(src, "nged_nom"), source_dataset="network-opportunity-map-headroom", priority=1))
    for key, region in (("nged_heatmap_em", 9), ("nged_heatmap_wm", 8), ("nged_heatmap_sw", 7), ("nged_heatmap_swest", 11)):
        p = api_file(src, key)
        if p is None:
            continue
        h = pd.DataFrame(json.load(open(p, encoding="utf-8")))
        out.append(_rows(
            company="NGED", region=region, site_id=h.get("mRID"), name=h["name"], level=h["type"],
            lat=num(h.latitude), lon=num(h.longitude), firm_mva=num(h.demandFirmCapacity),
            max_demand_mw=num(h.demandMaximum), demand_headroom_mw=num(h.demandAvailableCapacity),
            demand_contracted_mw=num(h.get("loadConnectionOffersAcceptedCapacity")),
            constraint=h.demandConstraint.astype(str).str.title(),
            headroom_basis="LTDS capacity heatmap: available demand capacity (firm capacity minus maximum demand)",
            headroom_as_of=as_of(src, key), source_dataset="ltds-capacity-heatmap", priority=2))
    return pd.concat(out, ignore_index=True) if out else _rows()


def ssen_geojson_rows(src: Path) -> pd.DataFrame:
    """SSEN's heatmap export (their map application, May 2026): every feature with
    its contracted demand summed from the Demands list."""
    E = src / "3 DUoS" / "site-specific EHV charges"
    rows = []
    for region, area in ((1, "North Scotland"), (12, "Southern England")):
        f = E / f"SSEN {area} LTDS capacity heatmap, named sites (May 2026).geojson"
        if not f.exists():
            continue
        for ft in json.load(open(f, encoding="utf-8"))["features"]:
            p = ft["properties"]
            contracted = sum((d.get("demandContractedCapacity") or 0.0) for d in (p.get("Demands") or []))
            rows.append({"region": region, "site_id": p.get("mRID"), "name": p["name"], "level": p["type"],
                         "lat": p["latitude"], "lon": p["longitude"], "firm_mva": p.get("demandFirmCapacity"),
                         "max_demand_mw": p.get("demandMaximum"), "demand_headroom_mw": p.get("demandAvailableCapacity"),
                         "demand_contracted_mw": contracted if p.get("Demands") else np.nan,
                         "constraint": p.get("demandConstraint")})
    return pd.DataFrame(rows)


def nameplate_firm_mva(text) -> float:
    """"2 x 240MVA (Shared with UKPN)" -> the N-1 firm capacity, 240; "2 x 15 / 30MVA" -> 15
    (the lower rating is the continuous one); a single transformer has no firm capacity (0)."""
    m = re.search(r"(\d+)\s*[xX]\s*([\d.]+)(?:\s*/\s*([\d.]+))?\s*MVA", str(text))
    if not m:
        return math.nan
    n, rating = int(m.group(1)), float(m.group(2))
    return max(n - 1, 0) * rating


def ssen_dashboard(src: Path) -> pd.DataFrame | None:
    """SSEN's Headroom Dashboard Data (CKAN, no key; March 2026): every primary,
    BSP and GSP with coordinates, nameplate ratings, observed and contracted
    demand, the company's estimated demand headroom (primaries and BSPs), RAG."""
    d = read_csv(src, "ssen_headroom_dashboard")
    if d is None:
        return None
    d.columns = [c.strip() for c in d.columns]
    d["region"] = d["Map / License Area"].astype(str).str.contains("SHEPD|Scotland").map({True: 1, False: 12})
    d["contracted_mw"] = num(d["Contracted Demand Excl BESS (MVA)"]).fillna(0) + num(d["Contracted BESS Demand (MVA)"]).fillna(0)
    d.loc[d["Contracted Demand Excl BESS (MVA)"].isna() & d["Contracted BESS Demand (MVA)"].isna(), "contracted_mw"] = np.nan
    d["firm_n1_mva"] = d["Transformer Nameplate Ratings"].map(nameplate_firm_mva)
    return d


def ssen_capacity(src: Path) -> pd.DataFrame:
    out = []
    d = ssen_dashboard(src)
    if d is not None:
        d = d[d["Substation Type"].isin(["Primary", "BSP"])]
        head = num(d["Estimated Demand Headroom (MVA)"])
        out.append(_rows(
            company="SSEN", region=d.region, site_id=d.AssetID, name=d.Substation, level=d["Substation Type"],
            lat=num(d["Location Latitude"]), lon=num(d["Location Longitude"]), firm_mva=d.firm_n1_mva,
            max_demand_mw=num(d["Maximum Observed Gross Demand (MVA)"]), demand_headroom_mw=head,
            demand_contracted_mw=d.contracted_mw, headroom_net_of_contracted_mw=head - d.contracted_mw,
            constraint=d["Substation Demand RAG Status"].astype(str).str.title(),
            headroom_basis="Headroom Dashboard: SSEN's estimated demand headroom (MVA); contracted demand published; "
                           "firm = N-1 nameplate",
            headroom_as_of=as_of(src, "ssen_headroom_dashboard"), source_dataset="generation-availability-and-network-capacity",
            priority=1))
    if d is not None:
        gg = ssen_dashboard(src)
        gg = gg[gg["Substation Type"] == "GSP"]
        peak = num(gg["Maximum Observed Gross Demand (MVA)"])
        out.append(_rows(
            company="SSEN", region=gg.region, site_id=gg.AssetID, name=gg.Substation, level="GSP",
            lat=num(gg["Location Latitude"]), lon=num(gg["Location Longitude"]), firm_mva=gg.firm_n1_mva,
            max_demand_mw=peak, demand_headroom_mw=gg.firm_n1_mva - peak, demand_contracted_mw=gg.contracted_mw,
            headroom_net_of_contracted_mw=gg.firm_n1_mva - peak - gg.contracted_mw,
            constraint=gg["Substation Demand RAG Status"].astype(str).str.title(),
            headroom_basis="derived: N-1 nameplate rating minus maximum observed demand (SSEN publish no GSP headroom; "
                           "the dashboard's RAG and contracted demand are theirs)",
            headroom_as_of=as_of(src, "ssen_headroom_dashboard"), source_dataset="generation-availability-and-network-capacity",
            priority=1))
    g = ssen_geojson_rows(src)
    if len(g):
        head = num(g.demand_headroom_mw)
        out.append(_rows(
            company="SSEN", region=g.region, site_id=g.site_id, name=g["name"], level=g.level, lat=g.lat, lon=g.lon,
            firm_mva=num(g.firm_mva), max_demand_mw=num(g.max_demand_mw), demand_headroom_mw=head,
            demand_contracted_mw=num(g.demand_contracted_mw), headroom_net_of_contracted_mw=head - num(g.demand_contracted_mw),
            constraint=g.constraint.astype(str).str.title(),
            headroom_basis="LTDS capacity heatmap (map export): available demand capacity; contracted demand published",
            headroom_as_of="2026-05", source_dataset="ssen capacity heatmap export (May 2026)", priority=2))
    return pd.concat(out, ignore_index=True) if out else _rows()


READERS = {"UKPN": ukpn_capacity, "Northern Powergrid": npg_capacity, "ENWL": enwl_capacity,
           "SPEN": spen_capacity, "NGED": nged_capacity, "SSEN": ssen_capacity}


# =============================================================================
# overlay
# =============================================================================
def _compatible(a, b) -> bool:
    return a is None or b is None or a == b


def overlay(sites: pd.DataFrame, cap: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Lay one company's capacity rows over its site rows.

    Match, in order: the same ``site_id``; the same normalised name at a
    compatible level; the nearest site row within ``MATCH_KM`` at a compatible
    level. A capacity row that matches nothing becomes a site row of its own
    (``overlay == "appended"``) — a substation the company's capacity data
    knows and its site list did not. Capacity columns are filled by priority
    and never overwritten by a lower one. Returns the rows and a tally."""
    s = sites.copy()
    for c in CAP_COLS + ["overlay"]:
        s[c] = pd.Series(np.nan, index=s.index, dtype=object if c in TEXT_COLS else float)
    s["_lvl"] = s.level.map(_std_level)
    s["_key"] = s["name"].map(norm)
    by_id = collections.defaultdict(list)
    for k, i in zip(s.index, s.get("site_id", pd.Series(index=s.index, dtype=object))):
        if pd.notna(i) and str(i) not in ("", "nan"):
            by_id[str(i)].append(k)
    by_name = collections.defaultdict(list)
    for k, (key, lvl) in zip(s.index, zip(s._key, s._lvl)):
        if key:
            by_name[key].append((k, lvl))
    placed = s.dropna(subset=["lat", "lon"])
    tree = cKDTree(np.c_[placed.lat, placed.lon * 0.6]) if len(placed) else None
    tally = collections.Counter()
    appended = []
    filled = set()
    cap = cap.sort_values("priority", kind="stable")
    for r in cap.itertuples(index=False):
        lvl = _std_level(r.level) if isinstance(r.level, str) else None
        hits = []
        sid = str(r.site_id) if pd.notna(r.site_id) and str(r.site_id) not in ("", "nan") else None
        if sid and sid in by_id:
            same = [k for k in by_id[sid] if _compatible(lvl, s.at[k, "_lvl"])]
            if same:
                hits = same, "id"
        if not hits and isinstance(r.name, str):
            cands = [k for k, l in by_name.get(norm(r.name), []) if _compatible(lvl, l)]
            if cands:
                hits = cands, "name"
        if not hits and tree is not None and pd.notna(r.lat) and pd.notna(r.lon):
            d, i = tree.query([r.lat, r.lon * 0.6], k=min(5, len(placed)))
            for dist, idx in zip(np.atleast_1d(d), np.atleast_1d(i)):
                if dist * 111.0 > MATCH_KM:
                    break
                k = placed.index[idx]
                if _compatible(lvl, s.at[k, "_lvl"]):
                    hits = [k], "near"; break
        hit = None
        if hits:
            hits, how = hits
            hit = hits[0]
        if hit is None:
            if pd.isna(r.lat) or pd.isna(r.lon) or not isinstance(r.name, str) or lvl is None:
                tally["unplaceable"] += 1
                continue
            appended.append({"region": r.region, "company": r.company, "name": r.name, "level": r.level,
                             "voltage_kv": np.nan, "lat": r.lat, "lon": r.lon, "site_id": sid,
                             "source": f"{r.source_dataset} (capacity row not in the site list)", "overlay": "appended",
                             **{c: getattr(r, c) for c in CAP_COLS}})
            tally["appended"] += 1
            continue
        for hit in hits:
            if hit in filled and pd.notna(s.at[hit, "demand_headroom_mw"]):
                # a lower-priority row: fill only what is still blank
                for c in ("firm_mva", "max_demand_mw", "demand_contracted_mw", "constraint"):
                    if pd.isna(s.at[hit, c]) and pd.notna(getattr(r, c)):
                        s.at[hit, c] = getattr(r, c)
                tally["filled gaps"] += 1
                continue
            for c in CAP_COLS:
                v = getattr(r, c)
                if pd.notna(v) or c in ("headroom_basis", "headroom_as_of", "source_dataset"):
                    s.at[hit, c] = v
            s.at[hit, "overlay"] = how
            filled.add(hit)
            tally[how] += 1
    # rows sharing a site id are one site (UKPN lists a 132/11 kV grid site and
    # its 11 kV board under one functional location): the unfilled takes the filled
    for sid, ks in by_id.items():
        have = [k for k in ks if pd.notna(s.at[k, "demand_headroom_mw"])]
        want = [k for k in ks if pd.isna(s.at[k, "demand_headroom_mw"])]
        if have and want:
            src_k = have[0]
            for k in want:
                for c in CAP_COLS:
                    s.at[k, c] = s.at[src_k, c]
                s.at[k, "headroom_basis"] = f"{s.at[src_k, 'headroom_basis']} (shared with the site's other row, same id)"
                s.at[k, "overlay"] = "shared id"
                tally["shared id"] += 1
    out = pd.concat([s, pd.DataFrame(appended)], ignore_index=True) if appended else s
    # duplicates: a site-list row with no capacity within MATCH_KM of a row with
    # capacity at the same level is the same substation under another name
    # (Northern Powergrid's EHV site list, NGED's location list) — dropped
    done = out[out.demand_headroom_mw.notna()].dropna(subset=["lat", "lon"])
    todo = out[out.demand_headroom_mw.isna()].dropna(subset=["lat", "lon"])
    if len(done) and len(todo):
        t2 = cKDTree(np.c_[done.lat, done.lon * 0.6])
        d, i = t2.query(np.c_[todo.lat, todo.lon * 0.6])
        same = (d * 111.0 <= MATCH_KM) & (done.iloc[i]["_lvl"].to_numpy() == todo["_lvl"].to_numpy())
        drop = todo.index[same]
        tally["duplicates dropped"] = int(len(drop))
        out = out.drop(index=drop)
    # the same substation filled twice under two names at one location and level
    # (NGED's "Derby South 33kV S Stn" and "Derby South 132/33kV"): keep the first
    key = out.assign(_la=out.lat.round(4), _lo=out.lon.round(4))
    dup = key.demand_headroom_mw.notna() & key.duplicated(subset=["_lvl", "_la", "_lo"], keep="first") & key.lat.notna()
    tally["same-location rows dropped"] = int(dup.sum())
    out = out[~dup.to_numpy()]
    return out.drop(columns=["_lvl", "_key"]).reset_index(drop=True), dict(tally)


def keep_builder_values(S: pd.DataFrame) -> pd.DataFrame:
    """Copy the builder's own capacity figures into ``builder_*`` columns on rows
    that do not have them yet (fresh rows; rows kept from disk already do)."""
    S = S.copy()
    for c, b in (("firm_mva", "builder_firm_mva"), ("demand_headroom_mw", "builder_headroom_mw"), ("source", "builder_source")):
        if b not in S:
            S[b] = S[c]
        else:
            fresh = S["_fresh"] if "_fresh" in S else S[b].isna() & S[c].notna() & S.get("overlay", pd.Series(np.nan, index=S.index)).isna()
            S.loc[fresh, b] = S.loc[fresh, c]
    return S.drop(columns=[c for c in ("_fresh",) if c in S])


def apply(S: pd.DataFrame, src: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """The full register with the capacity layer laid over it, plus a per-company tally.

    Idempotent: the builder's own capacity figures are kept in ``builder_*``
    columns and rows appended by an earlier overlay are dropped first, so a
    partial rebuild (``--only``) can lay the layer over rows kept from disk."""
    S = S.copy()
    if "overlay" in S:
        S = S[S.overlay != "appended"].copy()
    S = keep_builder_values(S)
    S["firm_mva"], S["demand_headroom_mw"], S["source"] = S.builder_firm_mva, S.builder_headroom_mw, S.builder_source
    if "site_id" not in S:
        S["site_id"] = np.nan
    parts, tallies = [], []
    for company, grp in S.groupby("company", sort=False, dropna=False):
        reader = READERS.get(company)
        if reader is None:
            g = grp.copy()
            for c in CAP_COLS + ["overlay"]:
                g[c] = pd.Series(np.nan, index=g.index, dtype=object if c in TEXT_COLS else float)
            parts.append(g)
            continue
        cap = reader(src)
        g, tally = overlay(grp, cap)
        legacy = g.demand_headroom_mw.isna() & g.builder_headroom_mw.notna()
        if legacy.any():
            g.loc[legacy, "demand_headroom_mw"] = g.loc[legacy, "builder_headroom_mw"].astype(float)
            g.loc[legacy, "firm_mva"] = g.loc[legacy, "builder_firm_mva"].astype(float)
            g.loc[legacy, "headroom_basis"] = "builder: " + g.loc[legacy, "builder_source"].astype(str) + " (derived or hand-pulled, 29 Oct 2026)"
            g.loc[legacy, "headroom_as_of"] = "2026-10-29"
            g.loc[legacy, "source_dataset"] = "builder (hand-pulled file)"
            g.loc[legacy, "overlay"] = "legacy"
        tally["legacy"] = int(legacy.sum())
        tally["company"], tally["rows"], tally["with_headroom"] = company, len(g), int(g.demand_headroom_mw.notna().sum())
        parts.append(g); tallies.append(tally)
        print(f"  capacity {company:<19} {tally}")
    out = pd.concat(parts, ignore_index=True)
    return out, pd.DataFrame(tallies)


# =============================================================================
# R3: headroom by year, and the connection queue
# =============================================================================
def headroom_by_year(src: Path) -> pd.DataFrame:
    """Long table: company, region, site_id, name, level, lat, lon, scenario,
    central (bool), year, headroom_mw, basis, as_of, source_dataset."""
    out = []
    u = read_csv(src, "ukpn_nshr")
    if u is not None:
        u = u[u.physical_level.isin(["PRIMARY", "GRID"])]
        lat, lon = latlon(u.spatial_coordinates)
        out.append(pd.DataFrame({
            "company": "UKPN", "region": u.licencearea.map(UKPN_REGION), "site_id": u.sitefunctionallocation,
            "name": u.substation_name, "level": u.physical_level.map({"PRIMARY": "Primary", "GRID": "Grid Substation"}),
            "lat": lat, "lon": lon, "scenario": u.scenario, "year": num(u.year.astype(str).str[:4]),
            "headroom_mw": num(u.headroom_mw), "basis": "DFES Network Scenario Headroom Report: demand headroom MW",
            "as_of": as_of(src, "ukpn_nshr"), "source_dataset": "ukpn-dfes-network-headroom-report"}))
    n = read_csv(src, "npg_ndp_headroom")
    if n is not None:
        years = [c for c in n.columns if c.startswith("demand_headroom_capacity_mw_")]
        lat, lon = latlon(n.geo_point_2d)
        m = n.assign(lat=lat, lon=lon).melt(
            id_vars=["licence_area", "substation_name", "bulk_supply_point_or_primary", "scenario_name", "lat", "lon"],
            value_vars=years, var_name="year", value_name="headroom_mw")
        out.append(pd.DataFrame({
            "company": "Northern Powergrid", "region": m.licence_area.map(NPG_REGION), "site_id": np.nan,
            "name": m.substation_name, "level": m.bulk_supply_point_or_primary.map({"Primary": "Primary", "Supply Point": "BSP"}),
            "lat": m.lat, "lon": m.lon, "scenario": m.scenario_name, "year": num(m.year.str[-4:]),
            "headroom_mw": num(m.headroom_mw), "basis": "Network Development Plan: thermal demand headroom MW",
            "as_of": as_of(src, "npg_ndp_headroom"), "source_dataset": "npg_ndp_demand_headroom"}))
    e = read_csv(src, "enwl_ndp_headroom")
    if e is not None:
        e = e.dropna(subset=["year", "scenario"])
        lat, lon = latlon(e.geopoint)
        out.append(pd.DataFrame({
            "company": "ENWL", "region": 3, "site_id": e.group_number.astype(str), "name": e.group_number.astype(str),
            "level": e.group.map({"PRIMARY": "PRY", "BSP": "BSP", "BULK SUPPLY POINT": "BSP"}),
            "lat": lat, "lon": lon, "scenario": e.scenario, "year": num(e.year),
            "headroom_mw": num(e.firm_headroom_mva), "basis": "Network Development Plan: firm demand headroom MVA (polygon centroid, not the site)",
            "as_of": as_of(src, "enwl_ndp_headroom"), "source_dataset": "ndp-pry-bsp-headroom"}))
    for key, region, sheets in (("ssen_nshr_sepd", 12, (("Primary Headroom Demand", "Primary"), ("BSP Headroom Demand", "BSP"))),
                                ("ssen_nshr_shepd", 1, (("Primary Headroom Dem", "Primary"),))):
        p = api_file(src, key)
        if p is None:
            continue
        for sheet, level in sheets:
            t, contracted = _ssen_nshr_sheet(p, sheet, level)
            if t is None:
                continue
            t["company"], t["region"], t["as_of"], t["source_dataset"] = "SSEN", region, as_of(src, key), key.replace("_", "-")
            out.append(t)
    if not out:
        return pd.DataFrame()
    d = pd.concat(out, ignore_index=True).dropna(subset=["year", "headroom_mw"])
    d["year"] = d.year.astype(int)
    d["central"] = d.scenario == d.company.map(CENTRAL_SCENARIO)
    return d


def _ssen_nshr_sheet(path: Path, sheet: str, level: str):
    """One Network Scenario Headroom Report sheet -> (long headroom table, contracted demand per site).
    Two header rows (labels, then years); each site's first row (scenario MINIMUM
    HEADROOM) carries its grid reference and outstanding contracted demand."""
    import openpyxl
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    if sheet not in wb.sheetnames:
        return None, None
    rows = list(wb[sheet].iter_rows(values_only=True))
    hdr, years = rows[0], rows[1]
    labels = [str(x or "").replace("\n", " ").strip() for x in hdr]
    def col(pat):
        return next((i for i, l in enumerate(labels) if re.search(pat, l, re.I)), None)
    c_gsp, c_bsp, c_pri, c_scn = col(r"^Grid Supply Point"), col(r"^Bulk Supply Point"), col(r"^Primary Substation"), col(r"^Scenario")
    c_ref, c_con, c_head = col(r"Grid Reference"), col(r"Outstanding Contracted Demand"), col(r"Demand Headroom Winter")
    c_name = c_pri if level == "Primary" else c_bsp
    if c_name is None or c_head is None or c_scn is None:
        return None, None
    year_cols = [(i, int(str(y)[:4])) for i, y in enumerate(years) if i >= c_head and str(y)[:4].isdigit()]
    out, contracted, cur = [], {}, None
    for r in rows[2:]:
        name = r[c_name] if c_name < len(r) else None
        scn = r[c_scn] if c_scn < len(r) else None
        if name is None or scn is None:
            continue
        name = str(name).strip()
        if c_ref is not None and r[c_ref]:
            lat, lon = gridref_to_latlon(r[c_ref])
            cur = (name, lat, lon, r[c_con] if c_con is not None else None,
                   r[c_gsp] if c_gsp is not None else None)
            contracted[name] = {"lat": lat, "lon": lon, "contracted_mw": pd.to_numeric(cur[3], errors="coerce"), "gsp": cur[4]}
        loc = contracted.get(name, {})
        for i, y in year_cols:
            v = pd.to_numeric(r[i], errors="coerce") if i < len(r) else np.nan
            out.append({"site_id": np.nan, "name": name, "level": level, "lat": loc.get("lat"), "lon": loc.get("lon"),
                        "scenario": str(scn).strip(), "year": y, "headroom_mw": v,
                        "basis": "Network Scenario Headroom Report: winter demand headroom MVA"})
    return pd.DataFrame(out), contracted


def ssen_contracted(src: Path) -> pd.DataFrame:
    """Outstanding contracted demand per SSEN primary and BSP from the 2026 headroom reports."""
    rows = []
    for key, region, sheets in (("ssen_nshr_sepd", 12, (("Primary Headroom Demand", "Primary"), ("BSP Headroom Demand", "BSP"))),
                                ("ssen_nshr_shepd", 1, (("Primary Headroom Dem", "Primary"),))):
        p = api_file(src, key)
        if p is None:
            continue
        for sheet, level in sheets:
            _, c = _ssen_nshr_sheet(p, sheet, level)
            for name, v in (c or {}).items():
                rows.append({"company": "SSEN", "region": region, "name": name, "level": level, "lat": v["lat"], "lon": v["lon"],
                             "demand_mw": v["contracted_mw"], "status": "contracted, not yet connected", "projects": np.nan,
                             "voltage_kv": np.nan, "site_id": np.nan, "as_of": as_of(src, key), "source_dataset": key.replace("_", "-")})
    return pd.DataFrame(rows)


def connection_queue(src: Path) -> pd.DataFrame:
    """Demand connections agreed or energised, by substation (long)."""
    out = []
    q = read_csv(src, "nged_demand_queue")
    if q is not None:
        g = q.groupby(["Region", "Substation Name", "BSP Name", "GSP Name", "Voltage", "Application Status"], dropna=False).agg(
            demand_mw=("Import (kW)", lambda s: num(s).sum() / 1000.0), projects=("Import (kW)", "size")).reset_index()
        out.append(pd.DataFrame({
            "company": "NGED", "region": g.Region.map(NGED_REGION), "site_id": np.nan, "name": g["Substation Name"],
            "level": np.nan, "parent_bsp": g["BSP Name"], "parent_gsp": g["GSP Name"],
            "voltage_kv": num(g.Voltage.astype(str).str.extract(r"(\d+)")[0]),
            "status": g["Application Status"].map({"Contracted": "contracted, not yet connected", "Energised": "energised"}),
            "demand_mw": g.demand_mw, "projects": g.projects, "lat": np.nan, "lon": np.nan,
            "as_of": as_of(src, "nged_demand_queue"), "source_dataset": "demand-data"}))
    t = read_csv(src, "ukpn_table6")
    if t is not None:
        lat, lon = latlon(t.spatial_coordinates)
        out.append(pd.DataFrame({
            "company": "UKPN", "region": t.licencearea.map(UKPN_REGION), "site_id": t.sitefunctionallocation, "name": t.substation,
            "level": np.nan, "parent_bsp": np.nan, "parent_gsp": t.gridsupplypoint, "voltage_kv": num(t.proposed_connection_voltage_kv),
            "status": t.status_of_connection, "demand_mw": num(t.demand_numbers_received_total_capacity),
            "projects": num(t.demand_numbers_received_total_number), "lat": lat, "lon": lon,
            "as_of": as_of(src, "ukpn_table6"), "source_dataset": "ukpn-ltds-table-6-interest-connections"}))
    n = read_csv(src, "npg_table8", usecols=lambda c: c != "geo_shape")
    if n is not None:
        lat, lon = latlon(n.geo_point_2d)
        out.append(pd.DataFrame({
            "company": "Northern Powergrid", "region": n.licence_area.map(NPG_REGION), "site_id": np.nan,
            "name": n.primary_substation.fillna(n.supply_point), "level": n.substation_class, "parent_bsp": n.supply_point,
            "parent_gsp": n.grid_supply_point, "voltage_kv": num(n.proposed_connection), "status": n["type"].map(
                {"Accepted": "offer accepted", "Quoted": "offer made", "Budget": "budget estimate"}),
            "demand_mw": num(n.total_demand_capacity_kva) / 1000.0, "projects": num(n.total_demand_number),
            "lat": lat, "lon": lon, "as_of": as_of(src, "npg_table8"), "source_dataset": "ltds-appendix-8"}))
    s = ssen_contracted(src)
    if len(s):
        out.append(s)
    if not out:
        return pd.DataFrame()
    d = pd.concat(out, ignore_index=True)
    return d[d.demand_mw.notna() & (d.demand_mw != 0)].reset_index(drop=True)


# =============================================================================
# R4: grid supply points
# =============================================================================
GSP_COLS = ["company", "region", "name", "lat", "lon", "located_by", "import_limit_winter_mw", "import_limit_summer_mw",
            "firm_mva", "max_demand_mw", "connected_mw", "accepted_mw", "demand_headroom_mw", "headroom_basis",
            "headroom_as_of", "source_dataset", "note"]
_GSP_NOISE = re.compile(r"\b(S\.?G\.?P\.?|SGP|GSP|SUBSTATION|132\s*KV|400\s*KV|275\s*KV|SGT\d*|\d+&\d+|\d+)\b", re.I)


def gsp_key(name) -> str:
    s = re.sub(r"\(.*?\)", " ", str(name))
    return norm(_GSP_NOISE.sub(" ", s))


def _locate_gsps(frame: pd.DataFrame, osm_tx: pd.DataFrame, children: pd.DataFrame | None) -> pd.DataFrame:
    """Give GSP records a location: an OpenStreetMap 275/400 kV substation of the
    same name, else the centroid of the substations the company lists under it."""
    osm = {gsp_key(n): (la, lo) for n, la, lo in zip(osm_tx["name"], osm_tx.lat, osm_tx.lon)}
    cent = {}
    if children is not None and len(children):
        for k, g in children.groupby("gsp_key"):
            cent[k] = (g.lat.mean(), g.lon.mean())
    lat, lon, how = [], [], []
    for n, la0, lo0 in zip(frame["name"], frame.get("lat", pd.Series(np.nan, index=frame.index)),
                           frame.get("lon", pd.Series(np.nan, index=frame.index))):
        if pd.notna(la0) and pd.notna(lo0):
            lat.append(la0); lon.append(lo0); how.append("published"); continue
        k = gsp_key(n)
        if k in osm:
            lat.append(osm[k][0]); lon.append(osm[k][1]); how.append("OpenStreetMap name")
        elif k in cent:
            lat.append(cent[k][0]); lon.append(cent[k][1]); how.append("centroid of its substations")
        else:
            lat.append(np.nan); lon.append(np.nan); how.append("not located")
    return frame.assign(lat=lat, lon=lon, located_by=how)


def grid_supply_points(src: Path, S: pd.DataFrame, osm_tx: pd.DataFrame) -> pd.DataFrame:
    """One row per grid supply point record with whatever capacity figure its company publishes."""
    out = []
    # Northern Powergrid: heatmap GSP rows
    h = read_csv(src, "npg_heatmap")
    if h is not None:
        g = h[h["type"] == "GSP"]
        out.append(pd.DataFrame({
            "company": "Northern Powergrid", "region": g.area.map(NPG_REGION), "name": g["name"], "lat": num(g.latitude), "lon": num(g.longitude),
            "firm_mva": num(g.demandfirmcapacity), "max_demand_mw": num(g.demandmaximum),
            "demand_headroom_mw": num(g.demandavailablecapacity), "accepted_mw": num(g.demandcontractedcapacity),
            "headroom_basis": "LTDS capacity heatmap: available demand capacity at the GSP", "headroom_as_of": as_of(src, "npg_heatmap"),
            "source_dataset": "ltds-capacity-heatmap"}))
    # SSEN: the dashboard's GSP rows (nameplate, peak, contracted, RAG) + approved import limits
    d = ssen_dashboard(src)
    g = None
    if d is not None:
        d = d[d["Substation Type"] == "GSP"]
        g = pd.DataFrame({"region": d.region, "name": d.Substation, "lat": num(d["Location Latitude"]), "lon": num(d["Location Longitude"]),
                          "max_demand_mw": num(d["Maximum Observed Gross Demand (MVA)"]), "demand_contracted_mw": d.contracted_mw,
                          "firm_n1": d.firm_n1_mva, "rag": d["Substation Demand RAG Status"],
                          "note": "nameplate " + d["Transformer Nameplate Ratings"].astype(str) + "; technical limits agreed: "
                                  + d["Technical Limits Agreed at GSP"].astype(str)})
        src_name, when = "ssen headroom dashboard", as_of(src, "ssen_headroom_dashboard")
    else:
        gj = ssen_geojson_rows(src)
        if len(gj):
            g = gj[gj.level == "GSP"].assign(firm_n1=np.nan, rag=lambda x: x.constraint, note="")
            src_name, when = "ssen capacity heatmap export", "2026-05"
    if g is not None and len(g):
        lim = read_csv(src, "ssen_gsp_limits")
        g = g.copy(); g["gsp_key"] = g["name"].map(gsp_key)
        w = s = None
        if lim is not None:
            lim = lim.assign(gsp_key=lim.GSP.map(gsp_key), imp=-num(lim.Import_limit))
            w = lim[lim.Scenario.str.lower().str.startswith("winter")].drop_duplicates("gsp_key").set_index("gsp_key").imp
            s = lim[lim.Scenario.str.lower().str.startswith("summer")].drop_duplicates("gsp_key").set_index("gsp_key").imp
        wl = g.gsp_key.map(w) if w is not None else pd.Series(np.nan, index=g.index)
        sl = g.gsp_key.map(s) if s is not None else pd.Series(np.nan, index=g.index)
        peak = num(g.max_demand_mw)
        firm = wl.fillna(g.firm_n1)
        head = firm - peak
        out.append(pd.DataFrame({
            "company": "SSEN", "region": g.region, "name": g["name"], "lat": g.lat, "lon": g.lon,
            "import_limit_winter_mw": wl, "import_limit_summer_mw": sl, "firm_mva": firm, "max_demand_mw": peak,
            "accepted_mw": num(g.demand_contracted_mw), "demand_headroom_mw": head,
            "headroom_basis": np.where(pd.notna(wl), "approved winter import limit minus maximum observed demand",
                                       np.where(pd.notna(g.firm_n1), "N-1 nameplate rating minus maximum observed demand (derived; no limit published)",
                                                "no import limit or nameplate published; maximum demand only")),
            "note": g.note.astype(str) + "; RAG " + g.rag.astype(str),
            "headroom_as_of": when, "source_dataset": f"technicallimits + {src_name}"}))
    # SP Energy Networks: Single Digital View import limits, located by name or centroid
    o = read_csv(src, "spen_gsp_overview")
    if o is not None:
        o = o[o.level == "GSP"].copy()
        wl, sl = num(o.gsp_technical_import_limit_winter_mw).abs(), num(o.gsp_technical_import_limit_summer_solar_max_mw).abs()
        children = []
        for key in ("spen_heatmap_spd", "spen_heatmap_spm"):
            hm = read_csv(src, key)
            if hm is not None and "gsp" in hm:
                la = num(hm["lat"]) if "lat" in hm else num(hm.latitude); lo = num(hm["lon"]) if "lon" in hm else num(hm.longitude)
                children.append(pd.DataFrame({"gsp_key": hm.gsp.map(gsp_key), "lat": la, "lon": lo}))
        f = pd.DataFrame({
            "company": "SPEN", "region": o.license.map({"SPD": 2, "SPM": 6}), "name": o.substation,
            "import_limit_winter_mw": wl, "import_limit_summer_mw": sl, "firm_mva": wl,
            "demand_headroom_mw": np.nan,
            "headroom_basis": np.where(pd.notna(wl), "technical import limit published; no GSP demand published, so no headroom",
                                       "no technical import limit published (" + o.td_boundary_capacity_notes.astype(str) + ")"),
            "note": "reinforcement " + o.transmission_reinforcement_expected_completion_date.astype(str),
            "headroom_as_of": as_of(src, "spen_gsp_overview"), "source_dataset": "gsp-overview"})
        out.append(_locate_gsps(f, osm_tx, pd.concat(children) if children else None))
    # Electricity North West: GSP heatmap by number, located from the register's GSP rows
    e = read_csv(src, "enwl_gsp_heatmap", usecols=lambda c: c != "geo_shape")
    if e is not None:
        e = e[e.gsp_number.astype(str).str.fullmatch(r"[\d_]+")].copy()
        reg = S[(S.company == "ENWL") & (S.level.astype(str).str.upper() == "GSP")]
        loc = {str(i): (n, la, lo) for i, n, la, lo in zip(reg.get("site_id", []), reg["name"], reg.lat, reg.lon)}
        rows = []
        for r in e.itertuples(index=False):
            parts = str(r.gsp_number).split("_")
            hit = next((loc[p] for p in parts if p in loc), None)
            rows.append({"company": "ENWL", "region": 3, "name": hit[0] if hit else f"GSP {r.gsp_number}",
                         "lat": hit[1] if hit else np.nan, "lon": hit[2] if hit else np.nan,
                         "connected_mw": num(pd.Series([r.connected_mw]))[0], "accepted_mw": num(pd.Series([r.accepted_mw]))[0],
                         "demand_headroom_mw": num(pd.Series([r.materiality_headroom_mw]))[0],
                         "note": f"awaiting transmission impact assessment {r.awaiting_tia_mw} MW",
                         "headroom_basis": "GSP heatmap: materiality headroom after connected and accepted demand",
                         "headroom_as_of": as_of(src, "enwl_gsp_heatmap"), "source_dataset": "enwl-gsp-heatmap"})
        f = pd.DataFrame(rows)
        f["located_by"] = np.where(f.lat.notna(), "published", "not located")
        out.append(f)
    # UK Power Networks: connection point peak per GSP (no limit published)
    gi = read_csv(src, "ukpn_gsp_insights")
    if gi is not None:
        yr = sorted(gi.regulatory_year.dropna().unique())
        cur = [y for y in yr if str(y).startswith("2025")] or yr[-1:]
        g = gi[(gi.dataset == "Conn Pt Pk") & (gi.units.str.startswith("Active")) & (gi.regulatory_year.isin(cur))]
        g = g.groupby("gsp", as_index=False).value.max()
        hm = read_csv(src, "ukpn_heatmap")
        children = pd.DataFrame({"gsp_key": hm.gsp.map(gsp_key), "lat": num(hm.latitude), "lon": num(hm.longitude)}) if hm is not None else None
        pts = read_csv(src, "ukpn_gsps", usecols=lambda c: c != "geo_shape")      # UKPN's own GSP list, located
        loc = {}
        if pts is not None:
            la, lo = latlon(pts.geo_point_2d)
            loc = {gsp_key(n): (a, b, r) for n, a, b, r in zip(pts.grid_supply_point, la, lo, pts.dno.map(UKPN_REGION))}
        names = sorted(set(g.gsp) | set(pts.grid_supply_point) if pts is not None else set(g.gsp))
        peak = g.set_index("gsp").value
        f = pd.DataFrame({"company": "UKPN", "name": names})
        f["region"] = [loc.get(gsp_key(n), (np.nan, np.nan, np.nan))[2] for n in names]
        # UKPN's GSP point is its supply area's centroid, not the substation: the
        # OpenStreetMap 275/400 kV site of that name comes first, the centroid second
        if loc:
            children = pd.DataFrame({"gsp_key": list(loc), "lat": [v[0] for v in loc.values()], "lon": [v[1] for v in loc.values()]})
        f["max_demand_mw"] = [num(pd.Series([peak.get(n)]))[0] for n in names]
        f["demand_headroom_mw"] = np.nan
        f["headroom_basis"] = f"GSP insights: connection point peak {cur[0] if cur else ''}; no import limit published"
        f["headroom_as_of"] = as_of(src, "ukpn_gsp_insights")
        f["source_dataset"] = "ukpn-grid-supply-points + ukpn-gsp-insights"
        out.append(_locate_gsps(f, osm_tx, children))
    # National Grid: the GSPs its Network Opportunity Map names; location only
    n = read_csv(src, "nged_nom", usecols=["type", "area", "GSP", "latitude", "longitude"])
    if n is not None:
        n = n[n["type"].isin(["Primary", "BSP"]) & n.GSP.notna()]
        g = n.groupby("GSP", as_index=False).agg(region=("area", lambda s: NGED_REGION.get(s.mode().iat[0])))
        children = pd.DataFrame({"gsp_key": n.GSP.map(gsp_key), "lat": num(n.latitude), "lon": num(n.longitude)})
        f = pd.DataFrame({"company": "NGED", "region": g.region, "name": g.GSP, "demand_headroom_mw": np.nan,
                          "headroom_basis": "no GSP capacity published by NGED (location only)",
                          "headroom_as_of": as_of(src, "nged_nom"), "source_dataset": "network-opportunity-map-headroom"})
        out.append(_locate_gsps(f, osm_tx, children))
    if not out:
        return pd.DataFrame(columns=GSP_COLS)
    d = pd.concat(out, ignore_index=True)
    for c in GSP_COLS:
        if c not in d:
            d[c] = np.nan
    d["located_by"] = d.located_by.fillna("published")
    return d[GSP_COLS]


def transmission_capacity(tx: pd.DataFrame, gsps: pd.DataFrame) -> pd.DataFrame:
    """Give each 275/400 kV OpenStreetMap substation the capacity of the nearest
    grid supply point record within ``GSP_MATCH_KM``."""
    tx = tx.copy()
    for c in CAP_COLS + ["gsp_record", "overlay"]:
        tx[c] = pd.Series(np.nan, index=tx.index, dtype=object)
    g = gsps.dropna(subset=["lat", "lon"])
    g = g[g.demand_headroom_mw.notna() | g.firm_mva.notna() | g.max_demand_mw.notna()]
    if g.empty or tx.empty:
        return tx
    tree = cKDTree(np.c_[g.lat, g.lon * 0.6])
    d, i = tree.query(np.c_[tx.lat, tx.lon * 0.6])
    ok = d * 111.0 <= GSP_MATCH_KM
    hit = g.iloc[i[ok]]
    for c in ("firm_mva", "max_demand_mw", "demand_headroom_mw", "headroom_basis", "headroom_as_of", "source_dataset"):
        tx.loc[ok, c] = hit[c].to_numpy()
    tx.loc[ok, "demand_contracted_mw"] = hit.accepted_mw.to_numpy()
    tx.loc[ok, "gsp_record"] = (hit.company + ": " + hit["name"].astype(str)).to_numpy()
    tx.loc[ok, "overlay"] = "gsp record"
    return tx
