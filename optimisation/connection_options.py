"""
Every price list a site could be on: the options the optimiser chooses between
(COST_PLAN §1.11, 30 Oct 2026).
=============================================================================

Until 30 Oct 2026 ``dc_inputs.build_series`` picked one price list before
solving — national grid or local network, a voltage, a charging band — from
1.43x the load, and held the connection the LP builds inside that band. The
guess came from the largest connection the site could have, not the one it
builds: the band floor bound in 29 of 42 chain runs, and a 150 MW IT site was
put on the national grid when the local network was £6.5–11.5 m a year
cheaper in all six areas tried.

This module lists every price list the site could be on instead. Each
**option** is one (tier, voltage, charging band) at one substation, with

- its **size range** ``floor_mw``–``ceiling_mw``: the band's edges
  (``network_charges.band_floor_mw`` and the band tables), the area's
  published size-to-voltage rule as the *floor* (a higher voltage is always
  allowed, a lower one never), the company's largest connection on top of the
  local network, and the option's **cap** (below);
- its **substation**: route length, published room and its basis and date;
- its **charges**: the fixed and per-MW use-of-system charges for that band
  and tier (``network_charges.import_charges``), site-specific where the
  substation has a named price node; the build cost is added per option by
  ``dc_inputs.build_tech`` (it needs the cost case);
- its **voltage group**, which names the import series it shares
  (``dc_inputs`` makes one £/MWh and one kg/MWh series per group: losses, unit
  rates and delivered carbon differ by voltage, not by band).

``dc_model`` gives each option an on/off switch, exactly one on, and a
connection of its own inside its range; the sum is ``cap_grid``.

Two modes, decided 30 Oct 2026 (``MODES``)
------------------------------------------
``"room"`` (the default). Each option is capped by **today's published room**
at its own substation at that voltage, as the company publishes it
(``demand_headroom_mw``). Room is a limit, not a flag: an option with no room
cannot be chosen however cheap, and where nothing near has much room the
model builds a small connection and makes the rest on site. Three further
decisions of the same day: a substation that publishes **no figure is
skipped** for the nearest at that voltage that does publish one (its longer
cable priced; the blanks passed over are listed); where the nearest with a
figure has **less room than the load**, the next substation at that voltage
with room for the load is a **second option** at its own cable length; and
the **voltage is chosen too**, the published rule being the floor.

``"cap"``. Every option is capped at one figure that ignores room: 1.43x the
load (``sites.CONNECTION_HEADROOM_ASSUMED``) or a cap the caller enters
(``Site.connection_limit_mw``, the page's cap box). Room is reported beside
the result and plays no part. For "I have an offer for X MW".

``"single"``. The model as it stood before 30 Oct 2026: one price list from
the ceiling, no switches. Kept for the forced runs that check the switched
answer (``scripts/run_both_tiers.py``) and for anyone who wants the old
behaviour.

In both switched modes the 1.43x figure no longer decides the price list.
``Site.transmission_connected`` and ``Site.tdr_band`` still override: they
keep only the options on that tier or in that band. A ``connection_limit_mw``
on the site is the cap mode with that cap.

What is *not* chosen
--------------------
Between 11 kV and the voltages above, the published size rule decides: a
connection no bigger than the area's 11 kV limit is an 11 kV one (the band
floor in ``network_charges.band_floor_mw``), so the choice of voltage runs
from 33 kV up. The national grid option starts at the company's largest
local connection (the tier rule of ``network_charges``), so a 150 MW IT
site's choice is a 132 kV local connection up to that top against a national
grid connection above it, which is what the both-ways run of 29 Oct 2026
compared. The charging bands at one voltage share that voltage's unit rates
(those of the band the load itself falls in); where an area's 33/132 kV unit
rates differ by band (the area-median fallback), that is an approximation
recorded in ASSUMPTIONS.md.

Run:  python optimisation/connection_options.py
"""
from __future__ import annotations

import math
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from optimisation import network_charges as nc, sites, substations as S   # noqa: E402

MODES = ("room", "cap", "single")


class ConnectionUnavailable(ValueError):
    """No price list survives: nothing in reach has room (room mode) or
    nothing in reach exists (cap mode). Raised by ``dc_inputs.build_series``
    rather than inventing a connection; the page answers it with "run
    islanded?". ``dropped`` lists what was looked at and why it fell."""

    def __init__(self, message: str, dropped: list[dict]):
        super().__init__(message)
        self.dropped = dropped
DEFAULT_MODE = "room"
TOL_MW = 1e-9
# The import series an option shares: one per voltage.
GROUPS = ("11 kV", "33 kV", "132 kV", "transmission")


def group_var(group: str) -> str:
    """The LP variable name of a voltage group's import flow (``imp_33kV``)."""
    return "imp_" + re.sub(r"\W", "", group)


def size_ranges(region: int, annual_mwh: float) -> list[dict]:
    """Every (tier, voltage, band) the area's rules allow, with its size range in MW.

    The floor is the band's floor (one kVA above the boundary, and for an EHV
    band at least the area's 11 kV limit); the ceiling is the band's top or
    the voltage's largest size, whichever is lower. The national grid band is
    set by annual consumption, so it is one band with no top.
    """
    r = nc.area_rule(region)
    scot = region in nc.SCOTTISH_CI_REGIONS
    volt_top = {"11 kV": r.max_11kv - (0.0 if r.max_11kv_inclusive else nc.BAND_FLOOR_STEP_MW),
                "33 kV": r.dno_max if scot else r.max_33kv, "132 kV": r.dno_max}
    out = []
    for v in (("11 kV", "33 kV") if scot else ("11 kV", "33 kV", "132 kV")):
        table = nc.HV_BAND_KVA if v == "11 kV" else nc.EHV_BAND_KVA
        for top_kva, band in table:
            lo = nc.band_floor_mw(False, band, region)
            hi = min(top_kva / 1000.0, volt_top[v])
            if lo <= hi + TOL_MW:
                out.append({"transmission": False, "voltage": v, "band": band,
                            "floor_mw": lo, "ceiling_mw": hi})
    t_band, _ = nc.tdr_band_for(r.dno_max + 1.0, annual_mwh, region=region, transmission_connected=True)
    out.append({"transmission": True, "voltage": "transmission", "band": t_band,
                "floor_mw": nc.band_floor_mw(True, t_band, region), "ceiling_mw": math.inf})
    return out


def _point_from_connection_point(p: dict) -> dict:
    """``substations.connection_point``'s answer as an option point (cap mode: the nearest)."""
    if not p.get("found"):
        return {"substation": None, "company": None, "level": None, "straight_km": None, "route_km": None,
                "room_mw": None, "headroom_basis": None, "headroom_as_of": None, "which": "none in reach",
                "skipped": [], "note": p.get("note", "")}
    return {"substation": p["substation"], "company": p["company"], "level": p["level"],
            "straight_km": p["straight_km"], "route_km": p["route_km"],
            "room_mw": p["nearest_headroom_mw"], "headroom_status": p["headroom_status"],
            "headroom_basis": p["headroom_basis"], "headroom_as_of": p["headroom_as_of"],
            "contracted_mw": p["nearest_contracted_mw"],
            "room_net_of_contracted_mw": p["nearest_headroom_net_of_contracted_mw"],
            "which": "nearest", "skipped": [], "note": p.get("note", "")}


def option_table(site, load_mw: float, annual_mwh: float, *, mode: str = DEFAULT_MODE,
                 cap_mw: float | None = None) -> tuple[list[dict], list[dict]]:
    """``(options, dropped)`` for a site: every price list it could be on.

    ``load_mw`` is the flat facility load; in room mode it is also what "room
    for the load" means when the next substation is added. ``cap_mw`` is the
    cap mode's one figure (required there; ignored in room mode).
    """
    if mode not in MODES:
        raise ValueError(f"connection mode must be one of {MODES}, got {mode!r}")
    if mode == "cap" and (cap_mw is None or not cap_mw > 0):
        raise ValueError("the cap mode needs a positive cap_mw")
    region = site.carbon_api_region
    rows = size_ranges(region, annual_mwh)
    if site.transmission_connected is not None:
        rows = [r for r in rows if r["transmission"] == bool(site.transmission_connected)]
    if site.tdr_band is not None:
        pinned = str(site.tdr_band)
        if pinned.startswith("T-Demand"):
            rows = [dict(r, band=pinned) for r in rows if r["transmission"]]
        else:
            rows = [r for r in rows if r["band"] == pinned]
    if getattr(site, "connection_substation", None):
        return _pinned_options(site, rows, load_mw, mode, cap_mw)
    options, dropped = [], []
    for r in rows:
        v = r["voltage"]
        reach = S.REACH_KM[v]
        if mode == "room":
            points = S.room_points(site.lat, site.lon, v, load_mw, region)
            if not points:
                dropped.append(dict(r, why=f"no {v} substation within {reach:g} km publishes a room figure"))
                continue
        else:
            cp = S.connection_point(site.lat, site.lon, v, cap_mw, region, within_km=reach)
            if not cp.get("found"):
                dropped.append(dict(r, why=f"no {v} substation within {reach:g} km"))
                continue
            points = [_point_from_connection_point(cp)]
        for p in points:
            ceiling = r["ceiling_mw"]
            if mode == "room":
                ceiling = min(ceiling, float(p["room_mw"]))
                if ceiling <= TOL_MW:
                    dropped.append(dict(r, **{k: p.get(k) for k in ("substation", "room_mw", "which")},
                                        why=f"no room: {p.get('substation')} publishes {p['room_mw']:,.1f} MW"))
                    continue
            else:
                ceiling = min(ceiling, float(cap_mw))
            if ceiling < r["floor_mw"] - TOL_MW:
                dropped.append(dict(r, **{k: p.get(k) for k in ("substation", "room_mw", "which")},
                                    why=(f"{'room' if mode == 'room' else 'the cap'} {ceiling:,.1f} MW is below the "
                                         f"band's floor {r['floor_mw']:,.3f} MW")))
                continue
            tier = "national grid" if r["transmission"] else "local network"
            options.append({
                **r, "ceiling_mw": float(ceiling), "tier": tier, "group": v, "mode": mode,
                "cap_basis": ("published room at the substation" if mode == "room" else
                              ("the site's connection limit" if site.connection_limit_mw is not None else
                               f"{cap_mw:,.1f} MW cap")),
                "point": p,
                "key": f"{tier} | {v} | {r['band']} | {p.get('substation') or 'no substation placed'}"
                       + (" | next with room" if p.get("which") == "next with room" else ""),
                "delivery_voltage": nc.delivery_voltage(r["transmission"], r["band"]),
            })
    return options, dropped


def _pinned_options(site, rows: list[dict], load_mw: float, mode: str, cap_mw: float | None):
    """The one option at the substation the user picked (connection wizard,
    4 Nov 2026): the size ranges at that voltage, capped at its published room
    (room mode) or at the size the user typed (cap mode, via the site's
    connection limit), folded to the one band the load falls in — or the
    largest that fits — so the run is the single-price-list model at the old
    speed; with ``Site.connection_band_optimised`` every band at that voltage
    stays an option and the optimiser picks the band with the size. Nothing at
    all when the room is zero or unpublished and no size was typed: the page
    then asks for one."""
    v = str(site.connection_substation_voltage or "")
    if v not in S.VOLTAGE_LEVELS:
        raise ValueError(f"connection_substation_voltage must be one of {tuple(S.VOLTAGE_LEVELS)}, got {v!r}")
    p = S.pinned_point(site.lat, site.lon, v, site.connection_substation, site.carbon_api_region)
    rows = [r for r in rows if r["voltage"] == v]
    if p is None:
        return [], [dict(r, why=f"no {v} substation named {site.connection_substation!r} in the register near the site")
                    for r in rows]
    options, dropped = [], []
    for r in rows:
        if mode == "room":
            if p["room_mw"] is None or p["room_mw"] <= TOL_MW:
                dropped.append(dict(r, substation=p["substation"], room_mw=p["room_mw"], which=p["which"],
                                    why=(f"no room: {p['substation']} publishes "
                                         + ("no figure" if p["room_mw"] is None else f"{p['room_mw']:,.1f} MW")
                                         + " - set your own size to connect here anyway")))
                continue
            ceiling = min(r["ceiling_mw"], float(p["room_mw"]))
        else:
            ceiling = min(r["ceiling_mw"], float(cap_mw))
        if ceiling < r["floor_mw"] - TOL_MW:
            dropped.append(dict(r, substation=p["substation"], room_mw=p["room_mw"], which=p["which"],
                                why=(f"{'room' if mode == 'room' else 'the size set'} {ceiling:,.1f} MW is below the "
                                     f"band's floor {r['floor_mw']:,.3f} MW")))
            continue
        tier = "national grid" if r["transmission"] else "local network"
        above = mode != "room" and p["room_mw"] is not None and float(cap_mw) > p["room_mw"] + TOL_MW
        options.append({
            **r, "ceiling_mw": float(ceiling), "tier": tier, "group": v, "mode": mode,
            "cap_basis": ("published room at the substation picked" if mode == "room" else
                          f"the size set at the substation picked ({float(cap_mw):,.1f} MW"
                          + (", above its published room" if above else "") + ")"),
            "point": dict(p, headroom_status=(None if p["room_mw"] is None else
                                              ("room" if p["room_mw"] >= ceiling - TOL_MW else "shortfall"))),
            "key": f"{tier} | {v} | {r['band']} | {p['substation']} | picked",
            "delivery_voltage": nc.delivery_voltage(r["transmission"], r["band"]),
        })
    if len(options) > 1 and not getattr(site, "connection_band_optimised", False):
        keep = representative(options, v, load_mw)
        dropped.extend(dict(o, why=f"folded: the band the load falls in is {keep['band']}")
                       for o in options if o is not keep)
        options = [keep]
    return options, dropped


def no_room_message(site, load_mw: float, dropped: list[dict], mode: str) -> str:
    """The one-paragraph answer when no price list survives."""
    if getattr(site, "connection_substation", None):
        p = next((d for d in dropped if d.get("substation")), None)
        room = (p or {}).get("room_mw")
        return (f"No room published at {site.connection_substation} ({site.connection_substation_voltage}) for a "
                f"{load_mw:,.1f} MW load at {getattr(site, 'name', site)}: it publishes "
                + ("no figure" if room is None else f"{room:,.1f} MW")
                + ". Set your own connection size to connect here anyway (which assumes the company provides it), "
                  "pick another substation, or run the site islanded.")
    by_v = {}
    for d in dropped:
        by_v.setdefault(d["voltage"], d["why"])
    where = "; ".join(f"{v}: {why}" for v, why in by_v.items())
    return (f"No room found nearby for a {load_mw:,.1f} MW load at {getattr(site, 'name', site)} "
            f"({mode} mode). At every voltage the substations within reach are full, publish no figure, "
            f"or do not exist ({where}). The run was not given a connection it does not have: "
            "run the site islanded (no grid), move it, widen the reach (substations.REACH_KM), "
            "or use the cap mode to ignore room.")


def with_charges(options: list[dict], index: pd.DatetimeIndex, site, duos_case: str = "central") -> dict:
    """Add each option's use-of-system charges in place; return its DUoS £/MWh
    series by option key (kept out of the option dict, which is written to JSON)."""
    series = {}
    for o in options:
        ch = nc.import_charges(index, zone_no=site.tnuos_zone, tdr_band=o["band"],
                               transmission_connected=o["transmission"], duos_case=duos_case,
                               site=(site.lat, site.lon), connection_voltage=o["voltage"])
        o["capacity_GBP_per_MW_year"] = ch["capacity_GBP_per_MW_year"]
        o["fixed_GBP_per_year"] = ch["fixed_GBP_per_year"]
        o["network_charges"] = ch["components"]
        series[o["key"]] = ch["duos_GBP_per_MWh"]
    return series


def representative(options: list[dict], group: str, load_mw: float) -> dict:
    """The option whose unit rates a voltage group's import series takes: the
    one whose size range holds the load, else the one with the most room."""
    ing = [o for o in options if o["group"] == group]
    holds = [o for o in ing if o["floor_mw"] - TOL_MW <= load_mw <= o["ceiling_mw"] + TOL_MW]
    pool = holds or ing
    return max(pool, key=lambda o: o["ceiling_mw"])


def reference_key(options: list[dict], transmission: bool, voltage: str, band: str) -> str | None:
    """The option today's single choice corresponds to, if it survived."""
    for o in options:
        if o["transmission"] == transmission and o["voltage"] == voltage and o["band"] == band:
            return o["key"]
    return None


def describe(options: list[dict], dropped: list[dict] = ()) -> str:
    lines = []
    for o in options:
        p = o["point"]
        lines.append(f"  {o['tier']:<14} {o['voltage']:<13} {o['band']:<10} {o['floor_mw']:>8.3f}-{o['ceiling_mw']:>8.1f} MW  "
                     f"{(p.get('substation') or '-')[:36]:<36} {p.get('route_km') or 0:5.1f} km  "
                     f"room {p.get('room_mw') if p.get('room_mw') is not None else '?'}  {p.get('which')}"
                     + (f"  (skipped {len(p['skipped'])} without a figure)" if p.get("skipped") else ""))
    for d in dropped:
        lines.append(f"  dropped {d['tier'] if 'tier' in d else ('national grid' if d['transmission'] else 'local network'):<14} "
                     f"{d['voltage']:<13} {d['band']:<10} {d['why']}")
    return "\n".join(lines)


if __name__ == "__main__":
    for name, lat, lon, mw_it in (("London", 51.5074, -0.1278, 150.0), ("Manchester", 53.48, -2.24, 60.0),
                                  ("Inverness", 57.48, -4.22, 5.0)):
        site = sites.resolve(lat, lon, name=name)
        load = mw_it * 1.2
        for mode in ("room", "cap"):
            cap = sites.max_connection_mw(load)[0] if mode == "cap" else None
            opts, drop = option_table(site, load, load * 8760.0, mode=mode, cap_mw=cap)
            print(f"\n{name}, {mw_it:g} MW IT ({load:,.0f} MW load), {mode} mode: {len(opts)} options")
            print(describe(opts, drop))
