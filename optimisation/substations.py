"""
The substation register, read for a site: nearest substation at the connection
voltage, cable route length, spare capacity, and the price node.
=============================================================================

The register is built by ``scripts/build_substation_register.py`` from every
DNO's open data (OneDrive ``connection sources/3 DUoS/site-specific EHV
charges``) into ``optimisation_outputs/substation_register/``:

    substations.csv   every substation: company, level, coordinates, and since
                      30 Oct 2026 the capacity layer (COST_PLAN §1.10 R2):
                      ``demand_headroom_mw`` with ``headroom_basis`` (what the
                      figure is), ``headroom_as_of`` (the portal's date) and
                      ``source_dataset``; ``firm_mva``, ``max_demand_mw``,
                      ``demand_contracted_mw``, ``headroom_net_of_contracted_mw``,
                      ``constraint`` where the company publishes them
    grid_supply_points.csv  R4: import limits, peaks and headroom at the
                      transmission interface; the transmission layer above
                      takes its capacity from the nearest record
    headroom_by_year.csv.gz R3: the companies' scenario headroom to 2050
    connection_queue.csv    R3: demand agreed or energised, by substation
    price_nodes.csv   "Nodal prices" rows from the 2026/27 schedules, located
                      by name, place or code (column ``how``)

Until 29 Oct 2026 every site was 2 km from its substation
(``connection_cost.ROUTE_KM``) and no substation had a capacity. Until 30 Oct
2026 the capacity was the weakest dataset each company had (rating minus peak
for UKPN and SP Energy Networks, partial heatmaps elsewhere).

Which substations a connection voltage reaches
----------------------------------------------
| voltage | level in the register | what it is |
|---|---|---|
| 11 kV | primary | the 33/11 kV substation whose 11 kV board the site joins |
| 33 kV | bulk | the 132/33 kV bulk supply point, or a 33 kV switching station |
| 132 kV | bulk, gsp | the 132 kV side of a bulk supply point, a 132 kV switching station or a grid supply point |
| transmission | transmission | a 275/400 kV substation (OpenStreetMap, ODbL) |

Cable route
-----------
Straight-line distance times ``ROUTE_FACTOR_ASSUMED``. No UK figure for how
much longer a cable route is than the straight line was found (COST_PLAN
§1.9 B); 1.3 is ASSUMED and flagged. The distance is a lower bound.

Spare capacity (COST_PLAN §1.9 C, decided 29 Oct 2026)
------------------------------------------------------
If the nearest substation's published demand headroom is below the
connection, the shortfall is flagged and both ways round it are reported: the
next substation in reach with room (a longer cable), or reinforcement at the
first choice. Under the Access SCR (Ofgem, 3 May 2022) a demand customer
pays reinforcement only above the £1,720/kVA High Cost Cap, so below the cap
its cost is the wait, not money. ``shortfall_route`` picks which the model
builds: "upgrade" (the nearest, default) or "next". A substation with no
published headroom is "unknown", never "room".
"""
from __future__ import annotations

import math
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
REGISTER = ROOT / "optimisation_outputs" / "substation_register"

ROUTE_FACTOR_ASSUMED = 1.3          # cable route / straight line, ASSUMED
HIGH_COST_CAP_GBP_PER_KVA = 1720.0  # Access SCR, demand reinforcement
SEARCH_KM = 60.0                    # how far "in reach" extends
MIN_PUBLISHED_SHARE = 0.5           # of substations in reach that must publish a headroom before the
#                                     register overrules the published voltage rule (ASSUMED threshold)
# How far a connection at each voltage is realistically run to reach a
# substation with room (COST_PLAN §1.11, 30 Oct 2026): beyond this the
# engineering answer is the next voltage up, not a longer cable. Rules of
# thumb, ASSUMED; the single-price-list model keeps SEARCH_KM.
REACH_KM = {"11 kV": 5.0, "33 kV": 15.0, "132 kV": 40.0, "transmission": SEARCH_KM}
ASSUMED = ("ROUTE_FACTOR_ASSUMED", "MIN_PUBLISHED_SHARE", "REACH_KM")

_LEVEL = {
    "primary": {"pry", "primary", "primary substation", "primary site"},
    "bulk": {"bsp", "bulk supply point", "supply point", "grid", "grid substation", "ehv switching station"},
    # UKPN's 132/11 kV grid sites (London): a 132 kV side, no 33 kV; their
    # 11 kV boards are listed again as primaries by the builder
    "gsp": {"gsp", "grid supply point", "super grid substation", "132kv switching station",
            "grid substation 132/11kv"},
    "transmission": {"transmission"},
}
VOLTAGE_LEVELS = {"11 kV": ("primary",), "33 kV": ("bulk",), "132 kV": ("bulk", "gsp"),
                  "transmission": ("transmission",)}
# In Scotland 132 kV is transmission, so a 33 kV connection runs to the
# 132/33 kV grid supply point itself (SHEPD lists them as GSPs).
SCOTTISH_REGIONS = (1, 2)
DISTRIBUTION_VOLTAGES = ("11 kV", "33 kV", "132 kV")


def levels_for(voltage: str, region: int | None) -> tuple[str, ...]:
    if voltage == "33 kV" and region in SCOTTISH_REGIONS:
        return ("bulk", "gsp")
    return VOLTAGE_LEVELS[voltage]


def level_of(raw) -> str | None:
    s = str(raw).strip().lower()
    for lvl, names in _LEVEL.items():
        if s in names:
            return lvl
    return None


CAPACITY_COLS = ("firm_mva", "max_demand_mw", "demand_headroom_mw", "demand_contracted_mw",
                 "headroom_net_of_contracted_mw")


@lru_cache(maxsize=1)
def substations() -> pd.DataFrame:
    s = pd.read_csv(REGISTER / "substations.csv", low_memory=False)
    s["level_std"] = s["level"].map(level_of)
    s = s.dropna(subset=["lat", "lon", "level_std"]).reset_index(drop=True)
    for c in CAPACITY_COLS:
        s[c] = pd.to_numeric(s[c], errors="coerce") if c in s else np.nan
    for c in ("headroom_basis", "headroom_as_of", "source_dataset", "constraint", "site_id"):
        if c not in s:
            s[c] = np.nan
    return s


@lru_cache(maxsize=1)
def grid_supply_points() -> pd.DataFrame:
    p = REGISTER / "grid_supply_points.csv"
    return pd.read_csv(p, low_memory=False) if p.exists() else pd.DataFrame()


@lru_cache(maxsize=1)
def headroom_by_year() -> pd.DataFrame:
    p = REGISTER / "headroom_by_year.csv.gz"
    return pd.read_csv(p, low_memory=False) if p.exists() else pd.DataFrame()


@lru_cache(maxsize=1)
def connection_queue() -> pd.DataFrame:
    p = REGISTER / "connection_queue.csv"
    return pd.read_csv(p, low_memory=False) if p.exists() else pd.DataFrame()


def _name_key(s) -> str:
    """A company's own name for a substation, as a join key between its datasets."""
    import re
    t = re.sub(r"\d+(\.\d+)?\s*/?\s*(\d+(\.\d+)?)?\s*KV", " ", str(s).upper())
    t = re.sub(r"\b(PRIMARY|BSP|GSP|GRID|SUBSTATION|S/S|LOCAL|MAIN|T\d|SGT\d*|\d+)\b", " ", t)
    return "".join(re.findall(r"[A-Z]+", t))


def with_year_headroom(year: int, scenario: str | None = None) -> pd.DataFrame:
    """``substations()`` with ``headroom_year_mw``: the company's scenario demand
    headroom in ``year`` (R3), joined to each substation by its id, then its
    name, then the nearest location within 300 m of the same company. Rows the
    forward view does not cover keep NaN. ``scenario`` None takes each
    company's central scenario (``register_capacity.CENTRAL_SCENARIO``)."""
    s = substations().copy()
    h = headroom_by_year()
    s["headroom_year_mw"] = np.nan
    s["headroom_year_scenario"] = pd.Series(np.nan, index=s.index, dtype=object)
    if h.empty:
        return s
    h = h[h.year == int(year)]
    h = h[h.central] if scenario is None else h[h.scenario == scenario]
    if h.empty:
        return s
    from scipy.spatial import cKDTree
    for company, hc in h.groupby("company"):
        idx = s.index[s.company == company]
        if not len(idx):
            continue
        by_id = {str(i): v for i, v in zip(hc.site_id, hc.headroom_mw) if pd.notna(i)}
        by_name = {_name_key(n): v for n, v in zip(hc["name"], hc.headroom_mw) if isinstance(n, str)}
        scn = {str(i): sc for i, sc in zip(hc.site_id, hc.scenario)} | {_name_key(n): sc for n, sc in zip(hc["name"], hc.scenario)}
        placed = hc.dropna(subset=["lat", "lon"])
        tree = cKDTree(np.c_[placed.lat, placed.lon * 0.6]) if len(placed) else None
        for k in idx:
            sid = str(s.at[k, "site_id"]) if pd.notna(s.at[k, "site_id"]) else None
            key = _name_key(s.at[k, "name"])
            if sid and sid in by_id:
                s.at[k, "headroom_year_mw"], s.at[k, "headroom_year_scenario"] = by_id[sid], scn[sid]
            elif key in by_name:
                s.at[k, "headroom_year_mw"], s.at[k, "headroom_year_scenario"] = by_name[key], scn[key]
            elif tree is not None:
                d, i = tree.query([s.at[k, "lat"], s.at[k, "lon"] * 0.6])
                if d * 111.0 <= 0.3:
                    r = placed.iloc[i]
                    s.at[k, "headroom_year_mw"], s.at[k, "headroom_year_scenario"] = r.headroom_mw, r.scenario
    return s


@lru_cache(maxsize=1)
def price_nodes() -> pd.DataFrame:
    n = pd.read_csv(REGISTER / "price_nodes.csv", low_memory=False)
    return n.dropna(subset=["lat", "lon"]).reset_index(drop=True)


def km(lat1, lon1, lat2, lon2):
    la1, lo1, la2, lo2 = map(np.radians, (lat1, lon1, lat2, lon2))
    a = np.sin((la2 - la1) / 2) ** 2 + np.cos(la1) * np.cos(la2) * np.sin((lo2 - lo1) / 2) ** 2
    return 6371.0 * 2 * np.arcsin(np.sqrt(a))


def candidates(lat: float, lon: float, voltage: str, region: int | None = None,
               within_km: float = SEARCH_KM) -> pd.DataFrame:
    """Substations the connection could run to, nearest first, with straight-line km."""
    if voltage not in VOLTAGE_LEVELS:
        raise ValueError(f"no substation level for voltage {voltage!r}")
    s = substations()
    s = s[s.level_std.isin(levels_for(voltage, region))]
    if region is not None and voltage != "transmission":
        s = s[s.region == region]
    d = km(lat, lon, s.lat.to_numpy(), s.lon.to_numpy())
    out = s.assign(straight_km=d).sort_values("straight_km")
    return out[out.straight_km <= within_km].reset_index(drop=True)


def connection_point(lat: float, lon: float, voltage: str, conn_mw: float,
                     region: int | None = None, shortfall_route: str = "upgrade",
                     within_km: float = SEARCH_KM) -> dict:
    """The substation the site connects to, its cable route, and the spare-capacity check."""
    if shortfall_route not in ("upgrade", "next"):
        raise ValueError("shortfall_route must be 'upgrade' or 'next'")
    c = candidates(lat, lon, voltage, region, within_km)
    if c.empty:
        return {"found": False, "voltage": voltage, "route_km": None, "straight_km": None,
                "note": f"no {voltage} substation in the register within {within_km:g} km"}
    first = c.iloc[0]
    head = first.demand_headroom_mw
    status = "unknown" if pd.isna(head) else ("room" if head >= conn_mw else "shortfall")
    nxt = c[c.demand_headroom_mw >= conn_mw]
    nxt = nxt.iloc[0] if len(nxt) else None
    chosen = nxt if (shortfall_route == "next" and status == "shortfall" and nxt is not None) else first
    out = {
        "found": True, "voltage": voltage, "connection_mw": conn_mw,
        "substation": chosen["name"], "company": chosen.company, "level": chosen.level_std,
        "straight_km": float(chosen.straight_km), "route_km": float(chosen.straight_km * ROUTE_FACTOR_ASSUMED),
        "route_factor_assumed": ROUTE_FACTOR_ASSUMED,
        "nearest": first["name"], "nearest_straight_km": float(first.straight_km),
        "nearest_headroom_mw": None if pd.isna(head) else float(head), "headroom_status": status,
        "headroom_basis": None if pd.isna(first.get("headroom_basis", np.nan)) else str(first["headroom_basis"]),
        "headroom_as_of": None if pd.isna(first.get("headroom_as_of", np.nan)) else str(first["headroom_as_of"]),
        "nearest_contracted_mw": None if pd.isna(first.get("demand_contracted_mw", np.nan)) else float(first["demand_contracted_mw"]),
        "nearest_headroom_net_of_contracted_mw": (None if pd.isna(first.get("headroom_net_of_contracted_mw", np.nan))
                                                  else float(first["headroom_net_of_contracted_mw"])),
        "shortfall_route": shortfall_route,
        "next_with_room": None if nxt is None else nxt["name"],
        "next_with_room_straight_km": None if nxt is None else float(nxt.straight_km),
        "next_with_room_route_km": None if nxt is None else float(nxt.straight_km * ROUTE_FACTOR_ASSUMED),
    }
    if status == "shortfall":
        out["note"] = (f"{first['name']} has {head:,.0f} MW of demand headroom against a {conn_mw:,.0f} MW connection: "
                       f"reinforcement at the customer's cost only above £{HIGH_COST_CAP_GBP_PER_KVA:,.0f}/kVA (Access SCR), "
                       + (f"or {nxt['name']} with room at {nxt.straight_km:.1f} km" if nxt is not None else
                          f"and no substation with room within {SEARCH_KM:g} km"))
    elif status == "unknown":
        out["note"] = f"{first['name']}: no published demand headroom"
    return out


def room_points(lat: float, lon: float, voltage: str, need_mw: float,
                region: int | None = None, within_km: float | None = None) -> list[dict]:
    """The substations an option at this voltage can run to in the optimiser's
    room mode (COST_PLAN §1.11, decided 30 Oct 2026): the nearest that
    *publishes* a room figure — substations with none are skipped and listed —
    and, where its room is below ``need_mw`` (the load), the next one at this
    voltage with room for it, as a second point at its own cable length. Both
    within ``REACH_KM`` for the voltage (``within_km`` overrides). Empty when
    nothing in reach publishes a figure. A published room of zero is a figure:
    the point is returned and the option table drops it as no room."""
    c = candidates(lat, lon, voltage, region, REACH_KM[voltage] if within_km is None else within_km)
    known = c.dropna(subset=["demand_headroom_mw"])
    if known.empty:
        return []

    def point(row, which, skipped):
        return {"substation": row["name"], "company": row.company, "level": row.level_std,
                "straight_km": float(row.straight_km),
                "route_km": float(row.straight_km * ROUTE_FACTOR_ASSUMED),
                "room_mw": float(row.demand_headroom_mw),
                "headroom_status": "room" if row.demand_headroom_mw >= need_mw else "shortfall",
                "headroom_basis": None if pd.isna(row.get("headroom_basis", np.nan)) else str(row["headroom_basis"]),
                "headroom_as_of": None if pd.isna(row.get("headroom_as_of", np.nan)) else str(row["headroom_as_of"]),
                "contracted_mw": None if pd.isna(row.get("demand_contracted_mw", np.nan)) else float(row["demand_contracted_mw"]),
                "room_net_of_contracted_mw": (None if pd.isna(row.get("headroom_net_of_contracted_mw", np.nan))
                                              else float(row["headroom_net_of_contracted_mw"])),
                "which": which, "skipped": list(skipped)}

    first = known.iloc[0]
    skipped = c[c.straight_km < first.straight_km]["name"].tolist()
    out = [point(first, "nearest with a published figure", skipped)]
    if first.demand_headroom_mw < need_mw:
        nxt = known[known.demand_headroom_mw >= need_mw]
        if len(nxt):
            out.append(point(nxt.iloc[0], "next with room", []))
    return out


def substation_list(lat: float, lon: float, region: int | None = None,
                    reach: dict | None = None) -> pd.DataFrame:
    """Every substation within reach of the site at each voltage, nearest
    first within a voltage: the list the page's connection wizard shows (4 Nov
    2026). ``has_figure`` says the company publishes a room figure for it,
    ``has_room`` that the figure is above zero. Reach is REACH_KM per voltage."""
    reach = dict(REACH_KM, **(reach or {}))
    cols = ["voltage", "substation", "company", "level", "straight_km", "route_km", "room_mw",
            "has_figure", "has_room", "headroom_basis", "headroom_as_of", "reach_km"]
    frames = []
    for v in VOLTAGE_LEVELS:
        if v not in reach:
            continue
        c = candidates(lat, lon, v, region, within_km=float(reach[v]))
        if c.empty:
            continue
        head = pd.to_numeric(c["demand_headroom_mw"], errors="coerce")
        frames.append(pd.DataFrame({
            "voltage": v, "substation": c["name"].astype(str), "company": c["company"],
            "level": c["level_std"], "straight_km": c["straight_km"].astype(float),
            "route_km": c["straight_km"].astype(float) * ROUTE_FACTOR_ASSUMED,
            "room_mw": head, "has_figure": head.notna(), "has_room": head.fillna(0.0) > 0.0,
            "headroom_basis": c["headroom_basis"] if "headroom_basis" in c else None,
            "headroom_as_of": c["headroom_as_of"] if "headroom_as_of" in c else None,
            "reach_km": float(reach[v]),
        }))
    if not frames:
        return pd.DataFrame(columns=cols)
    return pd.concat(frames, ignore_index=True)[cols]


def pinned_point(lat: float, lon: float, voltage: str, name: str, region: int | None = None) -> dict | None:
    """The option point for a substation the user picked by name at a voltage
    (the nearest row of that name, within the register's search radius), or
    None when the register has no such substation at that voltage."""
    c = candidates(lat, lon, voltage, region, within_km=SEARCH_KM)
    c = c[c["name"].astype(str) == str(name)]
    if c.empty:
        return None
    row = c.iloc[0]
    head = row.get("demand_headroom_mw", np.nan)
    return {"substation": str(row["name"]), "company": row.company, "level": row.level_std,
            "straight_km": float(row.straight_km), "route_km": float(row.straight_km * ROUTE_FACTOR_ASSUMED),
            "room_mw": None if pd.isna(head) else float(head),
            "headroom_basis": None if pd.isna(row.get("headroom_basis", np.nan)) else str(row["headroom_basis"]),
            "headroom_as_of": None if pd.isna(row.get("headroom_as_of", np.nan)) else str(row["headroom_as_of"]),
            "which": "picked by the user", "skipped": []}


def voltage_with_room(lat: float, lon: float, rule_voltage: str, conn_mw: float,
                      region: int) -> tuple[str, str]:
    """The connection voltage once the area's own substation capacities are
    read: the lowest distribution voltage, from the published rule's up, at
    which a substation in reach has room for the connection.

    The DNO's published rule (``network_charges.connection_voltage``) is the
    floor — a design standard that will not put 20 MVA on an 11 kV board is
    not overruled by a primary with room. Above it the register decides: when
    every substation in reach at that voltage that publishes its headroom is
    short, the connection goes up a voltage (a 33 kV shortfall everywhere is a
    132 kV offer in practice). Where no substation in reach publishes a
    headroom the rule stands, and so it does where fewer than
    ``MIN_PUBLISHED_SHARE`` of them do (2 of London's 117 bulk supply points
    publish one: too few to say the area is full). 132 kV is never stepped
    over — above the DNO's top the tier rule has already made the site
    transmission-connected — and in Scotland 33 kV is the top. Returns
    ``(voltage, note)``.
    """
    top = "33 kV" if region in SCOTTISH_REGIONS else "132 kV"
    order = DISTRIBUTION_VOLTAGES[DISTRIBUTION_VOLTAGES.index(rule_voltage):
                                  DISTRIBUTION_VOLTAGES.index(top) + 1]
    steps = []
    for v in order:
        c = candidates(lat, lon, v, region)
        known = c.dropna(subset=["demand_headroom_mw"])
        room = int((known.demand_headroom_mw >= conn_mw).sum()) if len(known) else 0
        enough_known = len(c) > 0 and len(known) / len(c) >= MIN_PUBLISHED_SHARE
        if v == top or c.empty or not enough_known or room:
            why = ("the published rule" if v == rule_voltage and not steps else "stepped up from " + ", ".join(steps))
            if c.empty:
                why += f"; no {v} substation in the register within {SEARCH_KM:g} km"
            elif not enough_known:
                why += (f"; only {len(known)} of {len(c)} {v} substations in reach publish a headroom "
                        f"(under the {MIN_PUBLISHED_SHARE:.0%} needed to overrule the rule)")
            elif not room:
                why += "; the area's top distribution voltage, with no room published in reach"
            else:
                why += (f"; {room} of {len(known)} {v} substations with a published headroom in reach "
                        f"have room for {conn_mw:,.0f} MW")
            return v, why
        steps.append(f"{v} ({len(known)} of {len(c)} in reach publish a headroom, "
                     f"largest {known.demand_headroom_mw.max():,.0f} MW)")
    raise AssertionError("unreachable")       # the top voltage always returns


FRESHNESS = REGISTER / "freshness.json"
FRESHNESS_MAX_AGE_HOURS = 24.0     # how long one check of the portals is trusted
NO_PORTAL_CHECK_ENV = "UKDCLCA_NO_PORTAL_CHECK"


def freshness(max_age_hours: float = FRESHNESS_MAX_AGE_HOURS, *, force: bool = False) -> dict:
    """Is the register behind what the companies publish? (the update check,
    30 Oct 2026, asked for after §1.11.)

    Two things can be behind. The **fetched files** can be older than the
    portals: one metadata call per dataset says when the portal's copy last
    changed (``scripts.fetch_register_sources.check_updates``), compared with
    the date recorded when the file was fetched. And the **register** can be
    older than the fetched files: the manifest written after the register
    was last built. Neither run downloads anything; the answer is cached in
    ``freshness.json`` for ``max_age_hours`` so a run does not pay 39 calls.

    Returns ``{"checked": iso time, "stale": [dataset keys newer on the
    portal], "errors": [...], "skipped": [...], "rebuild_needed": bool,
    "ok": bool, "note": one line}``. Offline, or with the environment
    variable ``UKDCLCA_NO_PORTAL_CHECK`` set, the portals are not asked and
    the note says so; a run never fails on this check.
    """
    import datetime as dt
    import json
    import os
    now = dt.datetime.now(dt.timezone.utc)
    if not force and FRESHNESS.exists():
        try:
            cached = json.loads(FRESHNESS.read_text(encoding="utf-8"))
            age = (now - dt.datetime.fromisoformat(cached["checked"])).total_seconds() / 3600.0
            if age <= max_age_hours:
                return cached
        except Exception:                                         # noqa: BLE001
            pass
    out = {"checked": now.isoformat(timespec="seconds"), "stale": [], "errors": [], "skipped": [],
           "rebuild_needed": False, "ok": True, "note": ""}
    try:
        from scripts import fetch_register_sources as F
        folder = F.api_dir(F.DEFAULT_SOURCES)
        reg = REGISTER / "substations.csv"
        man = folder / "manifest.json"
        if reg.exists() and man.exists() and man.stat().st_mtime > reg.stat().st_mtime + 60:
            out["rebuild_needed"] = True
        if os.environ.get(NO_PORTAL_CHECK_ENV):
            out["skipped"] = ["every portal (" + NO_PORTAL_CHECK_ENV + " set)"]
        else:
            for r in F.check_updates(folder):
                if r["stale"]:
                    out["stale"].append(r["key"])
                elif r["error"]:
                    out["errors"].append(f"{r['key']}: {r['error']}")
                elif r["skipped"]:
                    out["skipped"].append(f"{r['key']}: {r['skipped']}")
    except Exception as exc:                                      # noqa: BLE001
        out["errors"].append(f"check not run: {type(exc).__name__}: {exc}"[:200])
    out["ok"] = not out["stale"] and not out["rebuild_needed"]
    parts = []
    if out["stale"]:
        parts.append(f"{len(out['stale'])} dataset(s) are newer on the portal than the fetched copy "
                     f"({', '.join(out['stale'][:6])}{', ...' if len(out['stale']) > 6 else ''})")
    if out["rebuild_needed"]:
        parts.append("the register was built before the latest fetch")
    if parts:
        parts.append("refresh with: python scripts/fetch_register_sources.py && "
                     "python -I scripts/build_substation_register.py --capacity-only")
    elif not out["errors"] and not out["skipped"]:
        parts.append("the register matches what the companies publish")
    if out["errors"]:
        parts.append(f"{len(out['errors'])} portal(s) could not be checked")
    if out["skipped"]:
        parts.append(f"{len(out['skipped'])} dataset(s) not checked (no key)")
    out["note"] = "; ".join(parts)
    try:
        REGISTER.mkdir(parents=True, exist_ok=True)
        FRESHNESS.write_text(json.dumps(out, indent=1), encoding="utf-8")
    except Exception:                                             # noqa: BLE001
        pass
    return out


NODE_AT_SUBSTATION_KM = 0.1     # a node this close to the connection substation is that substation's node


def price_node_at(lat: float, lon: float, region: int, voltage_kv: float) -> dict | None:
    """The price node *of the substation the site connects to*, or None.

    Decided 30 Oct 2026 (COST_PLAN §1.10): a site takes a node's price only
    where the schedule's node was matched by name to that very substation
    (``how`` name or group); otherwise the area figure. The place-name and
    code placements and the "nearest placed node" are no longer used for
    pricing. The connection substation is the nearest at this voltage's levels."""
    voltage = {33.0: "33 kV", 132.0: "132 kV"}.get(float(voltage_kv))
    if voltage is None:
        return None
    c = candidates(lat, lon, voltage, region)
    if c.empty:
        return None
    sub = c.iloc[0]
    n = price_nodes()
    n = n[(n.region == region) & (n.kind == "network") & (n.voltage_kv == voltage_kv) & n.how.isin(["name", "group"])]
    if n.empty:
        return None
    d = km(sub.lat, sub.lon, n.lat.to_numpy(), n.lon.to_numpy())
    n = n.assign(at_km=d).sort_values("at_km")
    r = n.iloc[0]
    if r.at_km > NODE_AT_SUBSTATION_KM:
        return None
    return {"node_id": r.node_id, "label": r.label, "how": r.how, "straight_km": float(sub.straight_km),
            "substation": sub["name"], "local_GBP_per_kVA": float(r.local_GBP_per_kVA),
            "remote_GBP_per_kVA": float(r.remote_GBP_per_kVA)}


def nearest_price_node(lat: float, lon: float, region: int, voltage_kv: float,
                       group: str | None = None) -> dict | None:
    """The located price node nearest the site at this voltage — the method of
    29 Oct 2026, kept for the calibration script (``calibrate_ehv_charges``),
    which needs every listed site paired with a node. Pricing a run uses
    ``price_node_at`` since 30 Oct 2026."""
    n = price_nodes()
    n = n[(n.region == region) & (n.kind == "network") & (n.voltage_kv == voltage_kv)]
    if n.empty:
        return None
    d = km(lat, lon, n.lat.to_numpy(), n.lon.to_numpy())
    n = n.assign(straight_km=d).sort_values("straight_km")
    if group and (n.group == group).any() and n.iloc[0].group != group:
        n = n[n.group == group]
    r = n.iloc[0]
    return {"node_id": r.node_id, "label": r.label, "how": r.how, "straight_km": float(r.straight_km),
            "local_GBP_per_kVA": float(r.local_GBP_per_kVA), "remote_GBP_per_kVA": float(r.remote_GBP_per_kVA)}


if __name__ == "__main__":
    for name, lat, lon, v, mw, region in (("London (Docklands)", 51.505, -0.02, "132 kV", 225.0, 13),
                                           ("London", 51.505, -0.02, "33 kV", 75.0, 13),
                                           ("Highland", 57.48, -4.22, "transmission", 675.0, 1),
                                           ("Newport", 51.56, -2.95, "132 kV", 225.0, 7)):
        p = connection_point(lat, lon, v, mw, region)
        print(f"{name:<20} {v:<13} -> {p.get('substation')!s:<32} {p.get('straight_km', 0) or 0:5.1f} km straight, "
              f"route {p.get('route_km', 0) or 0:5.1f} km; headroom {p.get('headroom_status')}; "
              f"{p.get('note', '')}")
    print(f"\n  ASSUMED: {', '.join(ASSUMED)}.")
