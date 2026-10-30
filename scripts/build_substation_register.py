"""Build the substation register: every licence area's price nodes ("Nodal
prices" in its 2026/27 schedule of charges) tied to a location, and every
substation with its location and published spare capacity.

    python -I scripts/build_substation_register.py ["<OneDrive>/DC optimiser/connection sources"]

Writes optimisation_outputs/substation_register/{price_nodes,substations,
summary,grid_supply_points,connection_queue,capacity_coverage}.csv and
headroom_by_year.csv.gz. Nothing is fetched here: the name-and-location layer
reads the hand-pulled files of 29 Oct 2026 in the OneDrive folder `3 DUoS`,
and the capacity layer (`scripts/register_capacity.py`, since 30 Oct 2026)
reads the portal datasets `scripts/fetch_register_sources.py` stamped into
its `api/` folder — run that first to refresh. OpenStreetMap data is
© OpenStreetMap contributors, ODbL — the `how` column marks every row it
placed.

How a price node is located, in order (column `how`):
  name   the company's own data names the node's substation (or group)
  place  the node's place name, found in OpenStreetMap and snapped to the
         nearest substation of the right level (tested on known nodes)
  group  the node's 132 kV / BSP group, placed at its located members
  code   a code no published file decodes, read as an abbreviation of a
         substation name (about 90 % right where it answers, measured on
         NGED's known codes) — the least certain placement
  none   not located
Customer and generator nodes (a solar farm, a steelworks) are kept but
flagged `customer`: a new site does not connect at them.
"""
from __future__ import annotations

import collections
import io
import json
import math
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import openpyxl
import pandas as pd
from scipy.spatial import cKDTree

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import register_capacity as C   # noqa: E402  (the capacity layer, R2-R4)
OUT = ROOT / "optimisation_outputs" / "substation_register"
DEFAULT_SOURCES = Path.home() / "OneDrive - Imperial College London" / "DC optimiser" / "connection sources"

FILES = {   # CI region -> schedule workbook (as optimisation.duos_areas.FILES)
    1: "SSEN North Scotland 2026-27 v1.2.xlsx", 2: "SPEN South Scotland 2026-27 v0.6.xlsx",
    3: "ENWL North West 2026-27 v1.1.xlsx", 4: "Northern Powergrid North East 2026-27 v0.2.xlsx",
    5: "Northern Powergrid Yorkshire 2026-27 v0.2.xlsx", 6: "SPEN North Wales and Merseyside 2026-27 v0.5.xlsx",
    7: "NGED South Wales 2026-27 v0.1.xlsx", 8: "NGED West Midlands 2026-27 v0.1.xlsx",
    9: "NGED East Midlands 2026-27 v0.1.xlsx", 10: "UKPN East 2026-27 v1.7.xlsx",
    11: "NGED South West 2026-27 v0.1.xlsx", 12: "SSEN Southern England 2026-27 v1.2.xlsx",
    13: "UKPN London Power Networks Schedule of charges and other tables 2026-27 v1.3.xlsx",
    14: "UKPN South East 2026-27 v1.4.xlsx",
}
F = "(fetched 2026-10-29)"

# =============================================================================
# helpers
# =============================================================================
ABBR = {"ST": "STREET", "RD": "ROAD", "LN": "LANE", "AVE": "AVENUE", "PK": "PARK", "STN": "STATION", "SQ": "SQUARE",
        "GN": "GREEN", "BR": "BRIDGE", "WKS": "WORKS", "DV": "DRIVE", "N": "NORTH", "S": "SOUTH", "E": "EAST",
        "W": "WEST", "GT": "GREAT", "LT": "LITTLE"}
DROP = (r"\b(BSP|GSP|PRIMARY|GRID|SUPER GRID|SUBSTATION|S STN|S/S|SWITCHING STATION|SWS|LOCAL|NO\s*\d+|T\d+|"
        r"GT\d+[A-Z]?|SGT\d+|MAIN\s*[\d/&]*|RESERVE\s*[\d/&]*|BB\d*|EX)\b")
CUSTOMER = re.compile(
    r"\b(PV|SOLAR|WIND|WINDFARM|WF|WT|BESS|BATTERY|STORAGE|ESS|STOR|CHP|GEN|GENERATION|BIOMASS|LANDFILL|HYDRO|EFW|"
    r"ENERGY PARK|POWER STATION|FARM|FM|ANM|LTD|PLC|STEEL|STEELWORKS|PAPER|PLASTICS|GYPSUM|ZENECA|DISTILLERY|"
    r"REFINERY|AIRPORT|HOSPITAL|UNIVERSITY|JAGUAR|LANDROVER|VAUXHALL|ROLLS ROYCE|GKN|BICC|CHLOR|WATERWORKS|"
    r"INTERCONNECTOR|CEMENT|CASCEM|BNFL\w*|SELLAFIELD|GLAXO\w*|KELLOGS|PIRELL?I|BAE\w*|BBC|MIRROR|SAPPI|IDNO|UU|NWW|"
    r"IOM|KIELDE\w*|VICKERS|TRIGEN|UNIMAN|MANAIR|PPG|TENAX|IGGE\w*|BOWATE\w*|JOHMAT|SCOTT|MEDIA CITY|MEDIAC|BRITGA|"
    r"BRITGY|NATSAV|MJHNHS|MITECH|MODSPA|SPADIN|DISTIS|WALNEY|ROBIN RIGG|LAMBWF|HYNDWF|KIRKWF|ROBINR|BGC)\b", re.I)
DIRECTION = re.compile(r"^(S\.?E\.?|S\.?W\.?|N\.?E\.?|N\.?W\.?|N\.|S\.|E\.|W\.|NORTH|SOUTH|EAST|WEST)\s+", re.I)


def words(name) -> list[str]:
    s = re.sub(r"\b(\d+(/\d+)*\s*KV|KV|BSP|GSP|GRID|PRIMARY|SUBSTATION|S STN|S/S|TEE|T|MAIN\d*|RESERVE\d*|"
               r"SWITCHING STATION|\d+)\b", " ", str(name).upper())
    return [w for w in re.split(r"[^A-Z]+", s) if w]


def _subseq_score(code: str, ws: list[str]):
    letters = "".join(ws)
    if not letters or code[0] != letters[0]:
        return None
    i, used = 0, []
    for ch in code:
        j = letters.find(ch, i)
        if j < 0:
            return None
        used.append(j); i = j + 1
    return len(code) / (used[-1] - used[0] + 1)


def _prefix_concat(code: str, ws: list[str]) -> bool:
    if not code:
        return True
    if not ws:
        return False
    return any(code[:k] == ws[0][:k] and _prefix_concat(code[k:], ws[1:]) for k in range(1, min(len(ws[0]), len(code)) + 1))


def decode_code(code: str, pool: dict):
    """A 4-6 letter substation code -> the one name in ``pool`` ({key: display}) it
    abbreviates, or None. Two readings: word prefixes (GTCLIF = GreaT CLIFton) and
    letters in order (CDHR = ColDHaRbour), accepted only when unique or clearly
    ahead. On NGED's 22,590 known code-name pairs (29 Oct 2026): about 90 % right
    where it answers, answering for about half. Every row it places is `how=code`."""
    code = code.upper()
    ws = {k: words(v) for k, v in pool.items()}
    pre = [k for k, w in ws.items() if w and _prefix_concat(code, w)]
    sub = sorted(((s, k) for k, w in ws.items() if w and (s := _subseq_score(code, w))), reverse=True)
    a = pre[0] if len(pre) == 1 else None
    b = sub[0][1] if sub and sub[0][0] >= 0.5 and (len(sub) == 1 or sub[0][0] - sub[1][0] >= 0.15) else None
    if a and b and a != b:
        return None
    return a or b


def label_variants(lab: str) -> list[str]:
    """Keys to try for a price-node label, most specific first."""
    s = str(lab)
    out = [norm(s), norm(DIRECTION.sub("", s)), norm(re.sub(r"\b(MAIN|RESERVE|M|R)(?![A-Z])\s*[\d/&\s]*", " ", s)),
           norm(re.sub(r"\(.*?\)", " ", s))]
    for part in re.split(r"\s*[-/(]\s*", s):
        out.append(norm(part))
    if s.split():
        out.append(norm(s.split()[0]))
    seen, keep = set(), []
    for k in out:
        if k and k not in seen:
            seen.add(k); keep.append(k)
    return keep


def norm(s) -> str:
    s = str(s).upper().replace("KV", " KV")
    s = re.sub(r"\((.*?)\)", r" \1 ", s)
    s = re.sub(r"\d+(\.\d+)?(\s*/\s*\d+(\.\d+)?)*\s*KV\b", " ", s)
    s = re.sub(DROP, " ", s)
    words = [ABBR.get(w, w) for w in re.split(r"[^A-Z]+", s) if w]
    if len(words) > 1 and len(words[-1]) == 1:          # busbar letter: DUNBAR A -> DUNBAR
        words = words[:-1]
    return "".join(words)


def group_key(s) -> frozenset:
    """A group label ("Bromborough - Rock Ferry", "A GT3 / B GT2") -> its members."""
    t = re.sub(r"\s+[A-Z](\s*[&/]\s*[A-Z])+$", "", str(s).upper()).replace("'", "")
    t = t.replace(" AND ", " / ").replace("&", " / ")
    return frozenset(p for p in (norm(x) for x in re.split(r"\s*/\s*|\s+-\s*|\s*-\s+|,", t)) if p)


def bng_to_wgs84(e, n):
    """OS National Grid (OSGB36) easting/northing -> WGS84 lat, lon (Helmert, ~5 m).
    A blank or non-numeric grid reference gives (nan, nan)."""
    try:
        e, n = float(e), float(n)
    except (TypeError, ValueError):
        return math.nan, math.nan
    if not (math.isfinite(e) and math.isfinite(n)):
        return math.nan, math.nan
    a, b, F0 = 6377563.396, 6356256.909, 0.9996012717
    lat0, lon0, N0, E0 = math.radians(49), math.radians(-2), -100000, 400000
    e2 = 1 - b * b / (a * a); nn = (a - b) / (a + b)
    lat, M = lat0, 0.0
    for _ in range(100):
        lat = (n - N0 - M) / (a * F0) + lat
        M = b * F0 * ((1 + nn + 5 / 4 * nn ** 2 + 5 / 4 * nn ** 3) * (lat - lat0)
                      - (3 * nn + 3 * nn ** 2 + 21 / 8 * nn ** 3) * math.sin(lat - lat0) * math.cos(lat + lat0)
                      + (15 / 8 * nn ** 2 + 15 / 8 * nn ** 3) * math.sin(2 * (lat - lat0)) * math.cos(2 * (lat + lat0))
                      - 35 / 24 * nn ** 3 * math.sin(3 * (lat - lat0)) * math.cos(3 * (lat + lat0)))
        if abs(n - N0 - M) < 1e-5:
            break
    s, c, t = math.sin(lat), math.cos(lat), math.tan(lat)
    nu = a * F0 / math.sqrt(1 - e2 * s * s); rho = a * F0 * (1 - e2) / (1 - e2 * s * s) ** 1.5; eta2 = nu / rho - 1
    VII = t / (2 * rho * nu); VIII = t / (24 * rho * nu ** 3) * (5 + 3 * t * t + eta2 - 9 * t * t * eta2)
    IX = t / (720 * rho * nu ** 5) * (61 + 90 * t * t + 45 * t ** 4)
    X = 1 / (c * nu); XI = 1 / (c * 6 * nu ** 3) * (nu / rho + 2 * t * t)
    XII = 1 / (c * 120 * nu ** 5) * (5 + 28 * t * t + 24 * t ** 4)
    XIIA = 1 / (c * 5040 * nu ** 7) * (61 + 662 * t * t + 1320 * t ** 4 + 720 * t ** 6)
    dE = e - E0
    lat1 = lat - VII * dE ** 2 + VIII * dE ** 4 - IX * dE ** 6
    lon1 = lon0 + X * dE - XI * dE ** 3 + XII * dE ** 5 - XIIA * dE ** 7
    # OSGB36 -> WGS84 (Helmert)
    nu = a / math.sqrt(1 - e2 * math.sin(lat1) ** 2)
    x = nu * math.cos(lat1) * math.cos(lon1); y = nu * math.cos(lat1) * math.sin(lon1); z = (1 - e2) * nu * math.sin(lat1)
    tx, ty, tz, sc = 446.448, -125.157, 542.060, -20.4894e-6
    rx, ry, rz = (math.radians(v / 3600) for v in (0.1502, 0.2470, 0.8421))
    x2 = tx + (1 + sc) * x - rz * y + ry * z; y2 = ty + rz * x + (1 + sc) * y - rx * z; z2 = tz - ry * x + rx * y + (1 + sc) * z
    a2, b2 = 6378137.000, 6356752.3142; e22 = 1 - b2 * b2 / (a2 * a2); p = math.hypot(x2, y2)
    la = math.atan2(z2, p * (1 - e22))
    for _ in range(10):
        nu2 = a2 / math.sqrt(1 - e22 * math.sin(la) ** 2); la = math.atan2(z2 + e22 * nu2 * math.sin(la), p)
    return math.degrees(la), math.degrees(math.atan2(y2, x2))


def km(a, b):
    la1, lo1 = map(math.radians, a); la2, lo2 = map(math.radians, b)
    return 6371 * 2 * math.asin(math.sqrt(math.sin((la2 - la1) / 2) ** 2
                                          + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2))


class Snap:
    """Nearest substation of a set of levels, on lat/lon."""
    def __init__(self, subs: pd.DataFrame):
        self.t = subs.dropna(subset=["lat", "lon"]).reset_index(drop=True)
        self.tree = cKDTree(np.c_[self.t.lat.to_numpy(), self.t.lon.to_numpy() * 0.6]) if len(self.t) else None

    def __call__(self, lat, lon):
        _, i = self.tree.query([lat, lon * 0.6])
        return self.t.iloc[i]


def nodal_rows(sources: Path, region: int):
    """The schedule's "Nodal prices" rows: id, label, level, parent, local, remote."""
    d = sources / "3 DUoS"
    f = d / "2026-27 schedules" / FILES[region]
    f = f if f.exists() else d / FILES[region]
    rows = list(openpyxl.load_workbook(f, read_only=True, data_only=True)["Nodal prices"].iter_rows(values_only=True))
    h = next(i for i, r in enumerate(rows) if r and r[0] in ("Node/Zone ID", "Location name/ID"))
    num = lambda x: float(x) if isinstance(x, (int, float)) else 0.0
    for r in rows[h + 1:]:
        if r and r[0] is not None and str(r[0]).strip():
            yield {"node_id": str(r[0]).strip(), "label": r[1], "local": num(r[2]), "remote": num(r[3]),
                   "raw2": r[2] if len(r) > 2 else None}


def osm_places(path: Path):
    """name key -> [(lat, lon, name), ...]"""
    out = collections.defaultdict(list)
    for e in json.load(open(path, encoding="utf-8"))["elements"]:
        c = e.get("center") or {"lat": e.get("lat"), "lon": e.get("lon")}
        nm = e.get("tags", {}).get("name")
        if nm and c.get("lat") is not None:
            out[norm(nm)].append((c["lat"], c["lon"], nm))
    return out


def node(region, n, voltage, lat=None, lon=None, how="none", matched=None, group=None, kind="network"):
    return {"region": region, "node_id": n["node_id"], "label": n["label"] if n["label"] is not None else "",
            "voltage_kv": voltage, "local_GBP_per_kVA": n["local"], "remote_GBP_per_kVA": n["remote"],
            "kind": kind, "how": how, "matched": matched, "group": group, "lat": lat, "lon": lon}


def kv_of(text):
    m = re.search(r"(\d+(?:\.\d+)?)\s*kV", str(text), re.I)
    return float(m.group(1)) if m else None


# =============================================================================
# per company
# =============================================================================
def ukpn_secondary_kv(name: str) -> float | None:
    """The lower voltage a UKPN site name states: 'ARA GRID 132/11kV' -> 11,
    'FINSBURY MARKET B 33KV' -> 33, 'ISLINGTON 132KV' -> 132 (no lower side
    named), 'NEASDEN BSP' -> None."""
    m = re.search(r"(\d+)\s*/\s*(\d+(?:\.\d+)?)\s*kV", str(name), re.I)
    if m:
        return float(m.group(2))
    m = re.search(r"(\d+(?:\.\d+)?)\s*KV\b", str(name), re.I)
    return float(m.group(1)) if m else None


def ukpn_level(sitetype: str, name: str) -> str:
    """UKPN calls every 132 kV-fed site a "Grid Substation", but London's are
    often 132/11 kV with no 33 kV at all (found 29 Oct 2026: a 132 kV
    connection resolved to "LEICESTER SQ 11KV"). Split them by the lower
    voltage the name states: 132/33 (or 66) stays a grid substation (bulk,
    33 kV reachable); 132/11 (or 22, 20, 6.6) is a 132/11 kV grid site (the
    132 kV side reachable, its 11 kV board as a primary — see ``ukpn``); a
    bare "132KV" name is a 132 kV switching site. Unnamed voltage: bulk."""
    if str(sitetype).strip().lower() != "grid substation":
        return sitetype
    kv = ukpn_secondary_kv(name)
    if kv == 132:
        return "132kV Switching Station"
    if kv is None or kv >= 33:
        return "Grid Substation"
    return "Grid Substation 132/11kV"


def ukpn(src: Path):
    E = src / "3 DUoS" / "site-specific EHV charges"
    s = pd.read_csv(E / "UKPN grid and primary sites (fetched 2026-10-29).csv", encoding="utf-8-sig")
    s[["lat", "lon"]] = s.spatial_coordinates.str.split(",", expand=True).astype(float)
    area = {"Eastern Power Networks (EPN)": 10, "London Power Networks (LPN)": 13, "South Eastern Power Networks (SPN)": 14}
    level = [ukpn_level(t, n) for t, n in zip(s.sitetype, s.sitename)]
    subs = pd.DataFrame({"region": s.licencearea.map(area), "company": "UKPN", "name": s.sitename,
                         "level": level, "voltage_kv": s.sitevoltage, "lat": s.lat, "lon": s.lon,
                         "site_id": s.sitefunctionallocation,
                         "firm_mva": s.transratingwinter,
                         "demand_headroom_mw": pd.to_numeric(s.transratingwinter, errors="coerce") - pd.to_numeric(s.maxdemandwinter, errors="coerce"),
                         "source": "UKPN grid and primary sites"})
    # a 132/11 kV grid site's 11 kV board is a primary for an 11 kV connection
    board = subs[subs.level == "Grid Substation 132/11kV"].copy()
    board["level"], board["voltage_kv"] = "Primary Substation", 11
    board["source"] = "UKPN grid and primary sites (11 kV board of a 132/11 kV grid site)"
    subs = pd.concat([subs, board], ignore_index=True)
    nodes = []
    for region in (10, 13, 14):
        sub = subs[subs.region == region]
        idx = collections.defaultdict(list)
        for r in sub.itertuples(): idx[norm(r.name)].append(r)
        rows = list(nodal_rows(src, region))
        # node codes are a 4-letter site code + a voltage digit (ABBE31 = Abberton 33 kV):
        # learn digit -> kV from the labelled nodes, site code -> location from the matched ones
        digit_kv = collections.defaultdict(collections.Counter)
        for n in rows:
            m = re.match(r"^[A-Z0-9&_]{4}(\d)", n["node_id"]); v = kv_of(n["label"])
            if m and v: digit_kv[m.group(1)][v] += 1
        digit_kv = {d: c.most_common(1)[0][0] for d, c in digit_kv.items()}
        site_loc = {}
        for n in rows:
            hit = idx.get(norm(n["label"]))
            if hit: site_loc.setdefault(n["node_id"][:4], hit[0])
        for n in rows:
            m = re.match(r"^[A-Z0-9&_]{4}(\d)", n["node_id"])
            v = kv_of(n["label"]) or (digit_kv.get(m.group(1)) if m else None)
            hit = idx.get(norm(n["label"]))
            anon = bool(re.match(r"^(EPN|LPN|SPN)\s+\d+$", str(n["label"]).strip()))   # anonymised customer node
            kind = "customer" if anon or CUSTOMER.search(str(n["label"])) else "network"
            if hit:
                nodes.append(node(region, n, v, hit[0].lat, hit[0].lon, "name", hit[0].name, kind=kind))
            elif n["node_id"][:4] in site_loc:
                r = site_loc[n["node_id"][:4]]
                nodes.append(node(region, n, v, r.lat, r.lon, "group", r.name, n["node_id"][:4], kind))
            else:
                nodes.append(node(region, n, v, kind=kind))
    return subs, nodes


def npg(src: Path):
    E = src / "3 DUoS" / "site-specific EHV charges"
    s = pd.read_csv(E / f"Northern Powergrid LTDS EHV sites, both areas {F}.csv", encoding="utf-8-sig")
    s[["lat", "lon"]] = s.geo_point_2d.str.split(",", expand=True).astype(float)
    hm = pd.read_csv(E / f"Northern Powergrid LTDS capacity heatmap, named sites {F}.csv", encoding="utf-8-sig", low_memory=False)
    hm["region"] = hm.area.map({"NPgN": 4, "NPgY": 5})
    subs = pd.concat([
        pd.DataFrame({"region": hm.region, "company": "Northern Powergrid", "name": hm["name"], "level": hm["type"],
                      "voltage_kv": hm.voltages, "lat": hm.latitude, "lon": hm.longitude, "site_id": hm.mrid,
                      "firm_mva": hm.demandfirmcapacity, "demand_headroom_mw": hm.demandavailablecapacity,
                      "source": "Northern Powergrid LTDS capacity heatmap"}),
        pd.DataFrame({"region": np.nan, "company": "Northern Powergrid", "name": s.site_name, "level": s.site_purpose,
                      "voltage_kv": np.nan, "lat": s.lat, "lon": s.lon, "firm_mva": np.nan, "demand_headroom_mw": np.nan,
                      "site_id": s.asset_number,
                      "source": "Northern Powergrid LTDS EHV sites"})])
    idx = collections.defaultdict(list)
    for r in subs.itertuples(): idx[norm(r.name)].append(r)
    nodes = []
    for region in (4, 5):
        for n in nodal_rows(src, region):
            grp = n["label"]                                # the node's geographic (BSP) group
            hit = idx.get(norm(grp))
            kind = "customer" if CUSTOMER.search(n["node_id"]) else "network"
            if hit:
                nodes.append(node(region, n, None, hit[0].lat, hit[0].lon, "group", hit[0].name, grp, kind))
            else:
                nodes.append(node(region, n, None, group=grp, kind=kind))
    subs.loc[subs.region.isna(), "region"] = subs.loc[subs.region.isna()].apply(
        lambda r: 4 if r.lat > 54.45 else 5, axis=1)
    return subs, nodes


def ssen(src: Path):
    E = src / "3 DUoS" / "site-specific EHV charges"
    rows = []
    for region, area in ((1, "North Scotland"), (12, "Southern England")):
        for f in json.load(open(E / f"SSEN {area} LTDS capacity heatmap, named sites (May 2026).geojson", encoding="utf-8"))["features"]:
            p = f["properties"]
            rows.append({"region": region, "company": "SSEN", "name": p["name"], "level": p["type"], "site_id": p.get("mRID"),
                         "voltage_kv": "-".join(str(int(v)) for v in (p.get("voltages") or [])), "lat": p["latitude"],
                         "lon": p["longitude"], "firm_mva": p.get("demandFirmCapacity"),
                         "demand_headroom_mw": p.get("demandAvailableCapacity"), "source": "SSEN LTDS capacity heatmap"})
    subs = pd.DataFrame(rows)
    codes = pd.read_csv(E / "SSEN substation locations, both areas (2026-10-26, fetched 2026-10-29).csv",
                        encoding="utf-8-sig", encoding_errors="replace", low_memory=False)
    codes = codes[(codes.status == "Existing") & codes.type.isin(["Primary", "Grid/Bulk Supply pt", "Supergrid", "Switching Station"])]
    code_xy = {(o, str(c).strip().upper()): (x, y) for o, c, x, y in zip(codes.owner_name, codes.number, codes.location_x_m, codes.location_y_m)}
    idx = collections.defaultdict(list)
    for r in subs.itertuples(): idx[(r.region, norm(r.name))].append(r)
    nodes = []
    for region, owner in ((1, "SHEPD"), (12, "SEPD")):
        for n in nodal_rows(src, region):
            lab = str(n["label"])
            m = re.match(r"^(?:GSP:|BSP:)?([A-Z]{4})[A-Z0-9\-#_]*\s+(\d+\.\d+)$", lab.strip())
            if m:
                v = float(m.group(2)); xy = code_xy.get((owner, m.group(1)))
                if xy:
                    la, lo = bng_to_wgs84(*xy); nodes.append(node(region, n, v, la, lo, "name", m.group(1)))
                else:
                    nodes.append(node(region, n, v))
            else:
                hit = idx.get((region, norm(lab)))
                if hit:
                    nodes.append(node(region, n, 33.0, hit[0].lat, hit[0].lon, "name", hit[0].name))
                else:
                    nodes.append(node(region, n, 33.0, kind="customer" if CUSTOMER.search(lab) else "network"))
    return subs, nodes


def enwl(src: Path):
    E = src / "3 DUoS" / "site-specific EHV charges"
    s = pd.read_csv(E / f"ENWL substations, all levels {F}.csv", encoding="utf-8-sig", low_memory=False)
    s["number"] = s["number"].astype(str)
    s[["lat", "lon"]] = s.geopoint.str.split(",", expand=True).astype(float)
    ehv = s[s.group.isin(["PRY", "BSP", "GSP"])].copy()
    # names: the embedded capacity registers give "NAME (number)" for primaries, BSP/GSP names by location
    ecr = pd.concat([pd.read_csv(E / f"ENWL {f} {F}.csv", encoding="utf-8-sig", low_memory=False)
                     for f in ("enwl-embedded-capacity-register-2-1mw-and-above", "enwl-embedded-capacity-register-1-under-1mw")])
    xs = [c for c in ecr.columns if c.startswith("location_x")]; ys = [c for c in ecr.columns if c.startswith("location_y")]
    ecr["x"] = pd.to_numeric(ecr[xs].bfill(axis=1).iloc[:, 0], errors="coerce")
    ecr["y"] = pd.to_numeric(ecr[ys].bfill(axis=1).iloc[:, 0], errors="coerce")
    names = {}
    for v in ecr["primary"].dropna().astype(str):
        m = re.match(r"^(.*?)\s*\((\d{6})\)\s*$", v.strip())
        if m: names.setdefault(m.group(2), m.group(1).strip())
    dist = s[s.group.isin(["DISTRIBUTION", "NETWORK", "PRY"])].dropna(subset=["x", "y"])
    ok = ecr.dropna(subset=["x", "y"])
    _, ii = cKDTree(dist[["x", "y"]].to_numpy(float)).query(ok[["x", "y"]].to_numpy(float))
    near = dist.iloc[ii]
    for col, alias in (("bulk_supply_point", "dso_bsp_number_alias"), ("grid_supply_point", "dso_gsp_number_alias")):
        votes = collections.defaultdict(collections.Counter)
        for nm, num in zip(ok[col].astype(str), near[alias].astype(str)):
            if nm not in ("-", "nan") and num.isdigit(): votes[num][nm.strip()] += 1
        for num, c in votes.items():
            nm, k = c.most_common(1)[0]
            if k >= 2 and k / sum(c.values()) >= 0.6: names.setdefault(num, nm)
    ehv["name"] = ehv.number.map(names)
    cap = pd.concat([pd.read_csv(E / "capacity" / f"ENWL enwl-{k}-heatmap {F}.csv", encoding="utf-8-sig", low_memory=False)
                     .rename(columns={f"{k}_number": "number"}) for k in ("pry", "bsp")])
    cap["number"] = cap["number"].astype(str)
    ehv = ehv.merge(cap[["number", "demand_headroom_firm_mw"]], on="number", how="left")
    subs = pd.DataFrame({"region": 3, "company": "ENWL", "name": ehv.name.fillna(ehv.number), "level": ehv.group,
                         "voltage_kv": ehv.infeed_voltage, "lat": ehv.lat, "lon": ehv.lon, "firm_mva": np.nan, "site_id": ehv.number,
                         "demand_headroom_mw": ehv.demand_headroom_firm_mw, "source": "ENWL substations + registers + heatmaps"})
    known = collections.defaultdict(list)
    for r in ehv.dropna(subset=["name"]).itertuples(): known[norm(r.name)].append(r)
    places = osm_places(E / f"OpenStreetMap North West named places, substations and industrial sites {F}.json")
    level = {33: ("BSP", "PRY"), 132: ("GSP", "BSP"), 11: ("PRY",), 6.6: ("PRY",)}
    snaps = {v: Snap(ehv[ehv.group.isin(g)]) for v, g in level.items()}
    place_pool = {k: v[0][2] for k, v in places.items()}
    known_pool = {k: v[0].name for k, v in known.items()}
    nodes = []
    for n in nodal_rows(src, 3):
        m = re.search(r"_(\d+(?:\.\d+)?)_", n["node_id"]); v = float(m.group(1)) if m else None
        lab = str(n["label"]).strip()
        if CUSTOMER.search(lab):
            nodes.append(node(3, n, v, kind="customer")); continue
        cands = label_variants(lab)
        how = None
        if re.fullmatch(r"[A-Z]{5,6}", lab):                     # a truncation code: BILSBO, GTCLIF
            pick = decode_code(lab, known_pool) or decode_code(lab, place_pool)
            if pick:
                cands = [norm(pick)] + cands; how = "code"
        done = False
        for k in cands:
            if k in known:
                r = known[k][0]; nodes.append(node(3, n, v, r.lat, r.lon, how or "name", r.name)); done = True; break
        if not done and v in snaps:
            for k in cands:
                if places.get(k):
                    sn = snaps[v]; best = min(places[k], key=lambda c: sn.tree.query([c[0], c[1] * 0.6])[0])
                    t = sn(best[0], best[1]); nodes.append(node(3, n, v, t.lat, t.lon, how or "place", t["name"])); done = True; break
        if not done:
            nodes.append(node(3, n, v))
    return subs, nodes


def nged(src: Path):
    E = src / "3 DUoS" / "site-specific EHV charges"
    AREAS = {9: ("East Midlands", "east-midlands", "em", None), 8: ("West Midlands", "west-midlands", "wm", None),
             7: ("South Wales", "south-wales", "sw", "South Wales"), 11: ("South West", "south-west", "swest", "South West")}
    locs = pd.read_csv(E / f"NGED substation locations, all levels {F}.csv", encoding="utf-8-sig", encoding_errors="replace")
    nodes_tab = pd.read_csv(E / f"NGED LTDS tabular {F}" / "nged_ltds-tabular-model_ltds-attachment-8-node.csv",
                            encoding="utf-8-sig", encoding_errors="replace", low_memory=False)
    by5 = {}
    for r in nodes_tab.itertuples(): by5.setdefault(str(r.Code)[:5], (str(r.Name), str(r._4)))
    LEVEL = {132: ("Bulk Supply Point", "Super Grid Substation", "132kv Switching Station", "BSP"),
             33: ("Primary Substation", "Bulk Supply Point", "Ehv Switching Station", "Primary", "BSP")}
    all_subs, out = [], []
    for region, (area, capkey, osmkey, zone) in AREAS.items():
        cap = pd.DataFrame([{"region": region, "company": "NGED", "name": f["name"], "level": f["type"], "site_id": f.get("mRID"),
                             "voltage_kv": f.get("voltages"), "lat": f["latitude"], "lon": f["longitude"],
                             "firm_mva": f.get("demandFirmCapacity"), "demand_headroom_mw": f.get("demandAvailableCapacity"),
                             "source": "NGED LTDS capacity heatmap"}
                            for f in json.load(open(E / "capacity" / f"NGED LTDS capacity heatmap {capkey} (July 2026, fetched 2026-10-29).json", encoding="utf-8"))])
        box = (cap.lat.min() - 0.3, cap.lat.max() + 0.3, cap.lon.min() - 0.3, cap.lon.max() + 0.3)
        extra = locs[locs.Latitude.between(box[0], box[1]) & locs.Longitude.between(box[2], box[3])]
        extra = pd.DataFrame({"region": region, "company": "NGED", "name": extra["Substation Name"], "level": extra["Substation Type"],
                              "voltage_kv": np.nan, "lat": extra.Latitude, "lon": extra.Longitude, "firm_mva": np.nan,
                              "demand_headroom_mw": np.nan, "source": "NGED substation locations"})
        loc = pd.concat([cap, extra]); all_subs.append(cap); all_subs.append(extra)
        named = collections.defaultdict(list)
        for r in loc.itertuples(): named[norm(r.name)].append(r)
        snaps = {v: Snap(loc[loc.level.isin(t)]) for v, t in LEVEL.items()}
        places = osm_places(E / f"OpenStreetMap NGED {osmkey} named places, substations and industrial sites {F}.json")
        codes = cim_codes(E, zone) if zone else {}
        network_pool = {k: v[0].name for k, v in named.items() if not CUSTOMER.search(str(v[0].name))}
        for n in nodal_rows(src, region):
            raw = n["node_id"]
            if raw.startswith("_NO NAME"):
                out.append(node(region, n, None)); continue
            grp = None; how_code = None
            if zone:
                m = re.match(r"([A-Z]{4})(\d)", raw); v = {"1": 132.0, "3": 33.0}.get(m.group(2)) if m else None
                base = codes.get(raw); hit = by5.get(raw[:5])
                if hit: base = base or hit[0]; grp = hit[1]
                gen = bool(re.match(r"[A-Z]{4}\dG$", raw))
                if base is None and m and not gen:                 # a code no published file decodes
                    base = decode_code(m.group(1), network_pool); how_code = "code" if base else None
            else:
                parts = [p for p in raw.split("_") if p.strip()]
                v = 33.0 if len(parts) > 1 else (132.0 if "132" in raw else None)
                base = parts[-1] if parts else raw; grp = parts[0] if len(parts) > 1 else None; gen = False
            if gen or (base and CUSTOMER.search(str(base))):
                out.append(node(region, n, v, kind="customer", matched=base)); continue
            k = norm(base) if base else None
            if k and named.get(k):
                r = named[k][0]; out.append(node(region, n, v, r.lat, r.lon, how_code or "name", r.name, grp))
            elif k and v in snaps and places.get(k):
                sn = snaps[v]; best = min(places[k], key=lambda c: sn.tree.query([c[0], c[1] * 0.6])[0])
                t = sn(best[0], best[1]); out.append(node(region, n, v, t.lat, t.lon, "place", t["name"], grp))
            elif grp and named.get(norm(grp)):
                r = named[norm(grp)][0]; out.append(node(region, n, v, r.lat, r.lon, "group", r.name, grp))
            else:
                out.append(node(region, n, v, matched=base, group=grp))
    return pd.concat(all_subs), out


def cim_codes(E: Path, zone: str) -> dict:
    """Busbar/node code -> substation name, from NGED's existing and 2026/27 LTDS network models."""
    NS = "{http://iec.ch/TC57/CIM100#}"; RID = "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}ID"
    RES = "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource"
    name, parent, kind = {}, {}, {}
    with zipfile.ZipFile(E / f"NGED LTDS network model {zone} 2026-01 {F}.zip") as outer:
        for inner in [x for x in outer.namelist() if "SystemCapacity" in x and x.endswith(".zip")]:
            with zipfile.ZipFile(io.BytesIO(outer.read(inner))) as zz:
                root = ET.fromstring(zz.read([x for x in zz.namelist() if x.endswith("EQ.xml")][0]))
            for e in root:
                i = e.get(RID)
                if not i: continue
                kind[i] = e.tag.split("}")[1]
                nm = e.find(NS + "IdentifiedObject.name")
                if nm is not None: name[i] = nm.text
                for p in ("ConnectivityNode.ConnectivityNodeContainer", "VoltageLevel.Substation", "Equipment.EquipmentContainer"):
                    x = e.find(NS + p)
                    if x is not None: parent[i] = x.get(RES).lstrip("#")
    out = {}
    for i, k in kind.items():
        if k in ("ConnectivityNode", "BusbarSection") and i in name:
            p = parent.get(i)
            while p and kind.get(p) not in ("Substation", None): p = parent.get(p)
            if p and kind.get(p) == "Substation": out.setdefault(name[i], name.get(p))
    return out


def spen(src: Path):
    E = src / "3 DUoS" / "site-specific EHV charges" / "SPEN"
    rd = lambda n: pd.read_csv(E / f"{n} {F}.csv", encoding="utf-8-sig")
    subs, out = [], []
    for region, tag, co in ((6, "spm", "manweb"), (2, "spd", "distribution")):
        g = rd(f"distributed-generation-sp-{co}-heat-maps-{tag}-grid-substations"); g["level"] = "Grid"
        p = rd(f"distributed-generation-sp-{co}-heat-maps-{tag}-primary-substations"); p["level"] = "Primary"
        both = pd.concat([g, p], ignore_index=True).dropna(subset=["x", "y"])
        ll = [bng_to_wgs84(x, y) for x, y in zip(both.x, both.y)]
        both["lat"] = [a for a, _ in ll]; both["lon"] = [b for _, b in ll]
        subs.append(pd.DataFrame({"region": region, "company": "SPEN", "name": both.substation_name, "level": both.level,
                                  "voltage_kv": both.nominal_voltage_kv, "lat": both.lat, "lon": both.lon,
                                  "firm_mva": both.firm_capacity_mva,
                                  "demand_headroom_mw": pd.to_numeric(both.firm_capacity_mva, errors="coerce") - pd.to_numeric(both.maximum_load_mva, errors="coerce"),
                                  "source": f"SPEN {tag.upper()} heat-map grid and primary substations"}))
        by_name = collections.defaultdict(list)
        for r in both.itertuples(): by_name[norm(r.substation_name)].append((r.lat, r.lon, r.substation_name))
        groups = collections.defaultdict(list)    # group label -> member locations
        for col in [c for c in ("supergrid_group", "grid_group", "primary_group", "grid_supply_point") if c in both]:
            for r in both.dropna(subset=[col]).itertuples():
                groups[group_key(getattr(r, col))].append((r.lat, r.lon))
        if tag == "spm":
            f132 = rd("spm-ltds-appendix-4-fault-levels-table-4-132kv-3ph")
            for r in f132.itertuples():
                for nm in by_name.get(norm(r.substation_name), []):
                    groups[group_key(r.substation_group)].append(nm[:2])
            code2name = {}
        else:
            codes = rd("spd-ltds-appendix-7-substation-abbreviation-codes-table-7")
            code2name = {str(r.code).upper(): r.substation for r in codes.itertuples()}
        for n in nodal_rows(src, region):
            s = n["node_id"]
            lvl = n["label"] if tag == "spm" else None
            m = re.match(r"^(?:BSP:|GSP:)?([A-Z0-9]{4})[A-Z0-9\-#_]*\s+(\d+\.\d+)$", s)
            m2 = re.search(r"([A-Z][A-Z ]{1,4})/([A-Z]{4})[A-Z0-9]?[\-A-Z0-9]?\s*(\d+\.\d+)?", s)
            if tag == "spm":
                v = {1: 132.0, 2: 33.0, 3: 11.0}.get(lvl); name = s
            elif m:
                v = float(m.group(2)); name = code2name.get(m.group(1))
            elif m2:
                vm = re.search(r"(\d+\.\d+)", s); v = float(vm.group(1)) if vm else None; name = code2name.get(m2.group(2))
            else:
                v = 33.0; name = s
            if CUSTOMER.search(s) or (name and CUSTOMER.search(str(name))):
                out.append(node(region, n, v, kind="customer", matched=name)); continue
            loc = None
            if name:
                k = group_key(name)
                if by_name.get(norm(name)):
                    a = by_name[norm(name)][0]; loc = (a[0], a[1], "name", a[2])
                elif groups.get(k):
                    pts = np.array(groups[k]); loc = (pts[:, 0].mean(), pts[:, 1].mean(), "name", name)
                elif k and all(by_name.get(x) for x in k):
                    pts = np.array([by_name[x][0][:2] for x in k]); loc = (pts[:, 0].mean(), pts[:, 1].mean(), "name", name)
            if loc:
                out.append(node(region, n, v, loc[0], loc[1], loc[2], loc[3]))
            else:
                out.append(node(region, n, v, matched=name))
    return pd.concat(subs), out


# =============================================================================
# OpenStreetMap tags a generator's or an interconnector's own 275/400 kV
# substation like any other; no demand customer connects there (found 29 Oct
# 2026: Brighton's nearest "transmission" point was Rampion wind farm's
# onshore substation, 23.9 km away). Excluded by name; "Washway Farm" (a real
# NGET 275 kV substation) survives because "Farm" alone is not in the pattern.
NOT_A_GRID_SUPPLY_POINT = re.compile(
    r"Wind Farm|Offshore|Solar|Power Station|Converter|BESS|Battery|Generat|Flexible|Interconnector", re.I)

BUILDERS = {"ukpn": ukpn, "npg": npg, "ssen": ssen, "enwl": enwl, "nged": nged, "spen": spen}
COMPANY_OF = {"ukpn": ("UKPN",), "npg": ("Northern Powergrid",), "ssen": ("SSEN",), "enwl": ("ENWL",),
              "nged": ("NGED",), "spen": ("SPEN",)}
REGIONS_OF = {"ukpn": (10, 13, 14), "npg": (4, 5), "ssen": (1, 12), "enwl": (3,), "nged": (7, 8, 9, 11), "spen": (2, 6)}


def main(src: Path, only: list[str] | None = None) -> int:
    """Build the register. ``only`` rebuilds just those companies (and the
    transmission layer, always) and keeps the others' rows from the CSVs on
    disk — the full build takes ~35 min, mostly OpenStreetMap place-snapping.
    ``only=[]`` (``--capacity-only``) rebuilds no company: the name-and-location
    layer is read from disk and only the capacity layer, the grid supply points
    and the R3 tables are redone — about a minute, the step to run after a
    ``fetch_register_sources`` refresh."""
    OUT.mkdir(parents=True, exist_ok=True)
    subs, nodes = [], []
    todo = list(BUILDERS) if only is None else only
    for name in todo:
        s, n = BUILDERS[name](src)
        subs.append(s); nodes += n
        print(f"  {name:<5} {len(s):>6} substations, {len(n):>6} price nodes")
    S = pd.concat(subs, ignore_index=True) if subs else pd.DataFrame()
    S["_fresh"] = True                      # built this run: the capacity layer keeps these values as the builder's
    N = pd.DataFrame(nodes)
    if only is not None:
        old_s = pd.read_csv(OUT / "substations.csv", low_memory=False)
        old_n = pd.read_csv(OUT / "price_nodes.csv", low_memory=False)
        drop_co = {c for k in only for c in COMPANY_OF[k]} | {"transmission (OpenStreetMap)"}
        drop_r = {r for k in only for r in REGIONS_OF[k]}
        S = pd.concat([old_s[~old_s.company.isin(drop_co)].assign(_fresh=False), S], ignore_index=True)
        N = pd.concat([old_n[~old_n.region.isin(drop_r)], N], ignore_index=True)
        print(f"  kept {len(old_s[~old_s.company.isin(drop_co)]):,} substations and "
              f"{len(old_n[~old_n.region.isin(drop_r)]):,} nodes from the register on disk")
    # the capacity layer (R2): each company's standard datasets over its site list
    S, tally = C.apply(S, src)
    # national grid substations (no local price; for distance to a transmission connection)
    osm = pd.read_csv(src / "3 DUoS" / "site-specific EHV charges" / f"OpenStreetMap named substations 33kV and above, GB {F}.csv")
    tx = osm[osm.voltage_v.astype(str).str.contains("400000|275000")]
    gen = tx.name.astype(str).str.contains(NOT_A_GRID_SUPPLY_POINT)
    print(f"  transmission: {len(tx)} OpenStreetMap 275/400 kV substations, {int(gen.sum())} generator or "
          f"interconnector sites excluded")
    tx = tx[~gen]
    tx = pd.DataFrame({"region": np.nan, "company": "transmission (OpenStreetMap)", "name": tx.name,
                       "level": "transmission", "voltage_kv": tx.voltage_v, "lat": tx.lat, "lon": tx.lon,
                       "firm_mva": np.nan, "demand_headroom_mw": np.nan, "source": "OpenStreetMap, ODbL"})
    # grid supply points (R4) and the transmission layer's capacity from them
    gsps = C.grid_supply_points(src, S, tx)
    tx = C.transmission_capacity(tx, gsps)
    print(f"  grid supply points: {len(gsps)} records ({gsps.lat.notna().sum()} located, "
          f"{gsps.demand_headroom_mw.notna().sum()} with a headroom, {gsps.firm_mva.notna().sum()} with a limit or firm capacity); "
          f"{int(tx.gsp_record.notna().sum())} of {len(tx)} transmission substations take a record's capacity")
    S = pd.concat([S, tx], ignore_index=True)
    S.to_csv(OUT / "substations.csv", index=False)
    N.to_csv(OUT / "price_nodes.csv", index=False)
    gsps.to_csv(OUT / "grid_supply_points.csv", index=False)
    # R3: headroom by year and the connection queue
    hby = C.headroom_by_year(src)
    hby.to_csv(OUT / "headroom_by_year.csv.gz", index=False, compression="gzip")   # 278k rows: 56 MB plain
    (OUT / "headroom_by_year.csv").unlink(missing_ok=True)
    queue = C.connection_queue(src)
    queue.to_csv(OUT / "connection_queue.csv", index=False)
    print(f"  headroom by year: {len(hby):,} rows, {hby.groupby('company').size().to_dict() if len(hby) else {}}; "
          f"queue: {len(queue):,} rows")
    # coverage: per area and level, how many substations publish a headroom and how old it is
    from optimisation import substations as SUB
    cov = S.assign(level_std=S.level.map(SUB.level_of)).dropna(subset=["level_std"])
    cov = cov[cov.level_std != "transmission"].groupby(["region", "level_std"]).agg(
        substations=("name", "size"), with_headroom=("demand_headroom_mw", lambda s: int(s.notna().sum())),
        as_of=("headroom_as_of", lambda s: s.dropna().astype(str).min() if s.notna().any() else ""),
        newest=("headroom_as_of", lambda s: s.dropna().astype(str).max() if s.notna().any() else "")).reset_index()
    cov["share"] = (cov.with_headroom / cov.substations).round(3)
    cov.to_csv(OUT / "capacity_coverage.csv", index=False)
    tally.to_csv(OUT / "capacity_overlay.csv", index=False)
    print(cov.pivot(index="region", columns="level_std", values="share").to_string())
    rows = []
    for region in sorted(FILES):
        d = N[(N.region == region) & (N.kind == "network")]
        for v, lab in ((132.0, "132 kV"), (33.0, "33 kV")):
            dv = d[d.voltage_kv == v]
            if len(dv):
                rows.append({"region": region, "voltage": lab, "network_nodes": len(dv),
                             "located": int(dv.lat.notna().sum()), "share": round(dv.lat.notna().mean(), 3),
                             "by_name": int((dv.how == "name").sum()), "by_place": int((dv.how == "place").sum()),
                             "by_group": int((dv.how == "group").sum()),
                             "unlocated_with_price": int(((dv.local_GBP_per_kVA + dv.remote_GBP_per_kVA) != 0)[dv.lat.isna()].sum())})
        dn = d[d.voltage_kv.isna()]
        if len(dn):
            rows.append({"region": region, "voltage": "group-priced", "network_nodes": len(dn), "located": int(dn.lat.notna().sum()),
                         "share": round(dn.lat.notna().mean(), 3), "by_name": int((dn.how == "name").sum()),
                         "by_place": int((dn.how == "place").sum()), "by_group": int((dn.how == "group").sum()),
                         "unlocated_with_price": int(((dn.local_GBP_per_kVA + dn.remote_GBP_per_kVA) != 0)[dn.lat.isna()].sum())})
    summ = pd.DataFrame(rows)
    summ.to_csv(OUT / "summary.csv", index=False)
    print(summ.to_string(index=False))
    return 0


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("src", nargs="?", default=str(DEFAULT_SOURCES))
    ap.add_argument("--only", default=None, help="comma-separated builders to rebuild (ukpn,npg,ssen,enwl,nged,spen); "
                                                 "the rest kept from disk; the transmission layer is always rebuilt")
    ap.add_argument("--capacity-only", action="store_true",
                    help="rebuild no company: redo the capacity layer, grid supply points and R3 tables over the register on disk")
    a = ap.parse_args()
    sys.exit(main(Path(a.src), [] if a.capacity_only else (a.only.split(",") if a.only else None)))
