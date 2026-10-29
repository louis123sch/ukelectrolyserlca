"""
The substation register, read for a site: nearest substation at the connection
voltage, cable route length, spare capacity, and the price node.
=============================================================================

The register is built by ``scripts/build_substation_register.py`` from every
DNO's open data (OneDrive ``connection sources/3 DUoS/site-specific EHV
charges``) into ``optimisation_outputs/substation_register/``:

    substations.csv   10,829 substations: company, level, coordinates, firm
                      capacity and available demand headroom where published
    price_nodes.csv   8,432 "Nodal prices" rows from the 2026/27 schedules,
                      located by name, place or code (column ``how``)

Until 29 Oct 2026 every site was 2 km from its substation
(``connection_cost.ROUTE_KM``) and no substation had a capacity.

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
ASSUMED = ("ROUTE_FACTOR_ASSUMED",)

_LEVEL = {
    "primary": {"pry", "primary", "primary substation", "primary site"},
    "bulk": {"bsp", "bulk supply point", "grid", "grid substation", "ehv switching station"},
    "gsp": {"gsp", "grid supply point", "super grid substation", "132kv switching station"},
    "transmission": {"transmission"},
}
VOLTAGE_LEVELS = {"11 kV": ("primary",), "33 kV": ("bulk",), "132 kV": ("bulk", "gsp"),
                  "transmission": ("transmission",)}


def level_of(raw) -> str | None:
    s = str(raw).strip().lower()
    for lvl, names in _LEVEL.items():
        if s in names:
            return lvl
    return None


@lru_cache(maxsize=1)
def substations() -> pd.DataFrame:
    s = pd.read_csv(REGISTER / "substations.csv", low_memory=False)
    s["level_std"] = s["level"].map(level_of)
    s = s.dropna(subset=["lat", "lon", "level_std"]).reset_index(drop=True)
    s["demand_headroom_mw"] = pd.to_numeric(s["demand_headroom_mw"], errors="coerce")
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
    s = s[s.level_std.isin(VOLTAGE_LEVELS[voltage])]
    if region is not None and voltage != "transmission":
        s = s[s.region == region]
    d = km(lat, lon, s.lat.to_numpy(), s.lon.to_numpy())
    out = s.assign(straight_km=d).sort_values("straight_km")
    return out[out.straight_km <= within_km].reset_index(drop=True)


def connection_point(lat: float, lon: float, voltage: str, conn_mw: float,
                     region: int | None = None, shortfall_route: str = "upgrade") -> dict:
    """The substation the site connects to, its cable route, and the spare-capacity check."""
    if shortfall_route not in ("upgrade", "next"):
        raise ValueError("shortfall_route must be 'upgrade' or 'next'")
    c = candidates(lat, lon, voltage, region)
    if c.empty:
        return {"found": False, "voltage": voltage, "route_km": None, "straight_km": None,
                "note": f"no {voltage} substation in the register within {SEARCH_KM:g} km"}
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


def nearest_price_node(lat: float, lon: float, region: int, voltage_kv: float,
                       group: str | None = None) -> dict | None:
    """The located price node nearest the site at this voltage (COST_PLAN §1.9:
    the nearest node beats distance-weighting; stay inside the site's group
    when one is known and the nearest node is outside it)."""
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
